import asyncio
import json
import os
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image
from mss import mss
from pynput.mouse import Controller, Button
from websockets import serve
from zeroconf import ServiceInfo, Zeroconf


class ScreenProcessor:
    def __init__(self, w=540, h=960):
        self.w, self.h = w, h
        self.thresh = 10
        self.last = np.full((h, w), 15, np.uint8)
        self.resample = getattr(Image, 'Resampling', Image).LANCZOS

        # mode 0/1: 4像素一组 (每组2bit)
        groups_4 = w * h // 4
        self.byte_idx_4 = np.arange(groups_4) // 8
        self.bit_idx_4 = 7 - np.arange(groups_4) % 8
        self.bitmap_len_4 = (groups_4 + 7) // 8

        # mode 2: 8像素一组 (每组1bit)
        groups_8 = w * h // 8
        self.byte_idx_8 = np.arange(groups_8) // 8
        self.bit_idx_8 = 7 - np.arange(groups_8) % 8
        self.bitmap_len_8 = (groups_8 + 7) // 8

        self._work_buffer = np.empty(h * w, np.uint8)
        self._last_buffer = np.empty(h * w, np.uint8)
        # 确保能被8整除（4和8的最小公倍数）
        self._pad_len = -(h * w % -8)
        self.last_lock = threading.Lock()

    def reset_last_to_white(self):
        with self.last_lock:
            self.last = np.full((self.h, self.w), 15, np.uint8)

    def ip(self):
        """优先返回无线网卡的IP地址（设备通常连接同一WiFi网络）"""
        import subprocess
        import re

        # macOS：优先用 en0（通常为 Wi-Fi）的 IP，避免得到 198.18.x（VPN/代理）
        if os.uname().sysname == 'Darwin':
            for iface in ('en0', 'en1', 'en2'):
                try:
                    result = subprocess.run(
                        ['ipconfig', 'getifaddr', iface],
                        capture_output=True, text=True, timeout=1
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        ip = result.stdout.strip()
                        if not ip.startswith('127.'):
                            print(f"[网络] macOS 使用 {iface} IP: {ip}")
                            return ip
                except Exception:
                    continue
            # 若 ipconfig getifaddr 都拿不到，再试 ifconfig
            try:
                result = subprocess.run(
                    ['ifconfig'], capture_output=True, text=True, timeout=2
                )
                for line in result.stdout.splitlines():
                    m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                    if m:
                        addr = m.group(1)
                        if not addr.startswith('127.') and not addr.startswith('169.'):
                            print(f"[网络] macOS ifconfig 使用: {addr}")
                            return addr
            except Exception as e:
                print(f"[网络] macOS 获取IP失败: {e}")

        # Windows：通过 ipconfig 获取所有网卡信息，优先选择无线网卡IP
        try:
            result = subprocess.run(
                ['ipconfig'], capture_output=True, text=True, encoding='gbk', errors='ignore'
            )
            output = result.stdout

            # 按适配器段落分割
            sections = re.split(r'\r?\n(?=\S)', output)
            wifi_ip = None
            fallback_ip = None

            for section in sections:
                # 提取该段落中的 IPv4 地址
                ip_match = re.search(r'IPv4.*?:\s*([\d.]+)', section)
                if not ip_match:
                    continue
                addr = ip_match.group(1)
                if addr.startswith('127.'):
                    continue

                # 判断是否为无线网卡（匹配常见的无线适配器名称关键词）
                header = section.split('\n')[0].lower()
                is_wifi = any(kw in header for kw in [
                    'wi-fi', 'wifi', 'wlan', 'wireless',
                    '无线', '无线局域网'
                ])

                if is_wifi:
                    wifi_ip = addr
                    break  # 找到无线网卡IP即停止
                elif fallback_ip is None:
                    fallback_ip = addr

            if wifi_ip:
                print(f"[网络] 使用无线网卡IP: {wifi_ip}")
                return wifi_ip
            if fallback_ip:
                print(f"[网络] 未找到无线网卡，使用: {fallback_ip}")
                return fallback_ip
        except Exception as e:
            print(f"[网络] ipconfig解析失败: {e}")

        # 最终回退：使用UDP探测法
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"[网络] 回退使用默认路由IP: {ip}")
            return ip
        except:
            return "127.0.0.1"

    def capture(self, region):
        try:
            x0, y0, x1, y1 = region
            if x1 <= x0 or y1 <= y0:
                return None

            with mss() as sct:
                img = sct.grab({
                    "top": y0,
                    "left": x0,
                    "width": x1 - x0,
                    "height": y1 - y0
                })
                arr = np.frombuffer(img.bgra, np.uint8).reshape(img.height, img.width, 4)[..., [2, 1, 0]]

                if (x1 - x0) / (y1 - y0) > 1:
                    arr = np.rot90(arr, k=-1)

                return arr
        except:
            return None

    def quantize(self, img, mode):
        q = np.array(Image.fromarray(img).resize((self.w, self.h), self.resample).convert('L'), np.uint8)
        bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.uint8)
        dither = bayer[np.arange(self.h)[:, None] % 4, np.arange(self.w)[None, :] % 4]

        if mode == 0:
            q64 = q // 4
            out = np.empty_like(q)
            out[q < 100] = 0
            out[(q >= 100) & (q < 180)] = 6
            out[q >= 180] = 15
            return out
        elif mode == 1:
            q32 = q // 8
            out = np.empty_like(q32, np.uint8)
            out[q32 <= 3] = 0
            out[(q32 >= 12) & (q32 <= 13)] = 6
            out[q32 >= 30] = 15

            mask = (q32 > 3) & (q32 < 12)
            out[mask] = np.where((q32[mask] - 3) * 2 > dither[mask], 6, 0)

            mask = (q32 > 13) & (q32 <= 30)
            out[mask] = np.where((q32[mask] - 13) > dither[mask], 15, 6)
            return out
        else:
            q64 = q // 4
            out = np.empty_like(q64, np.uint8)
            out[q64 <= 7] = 0
            out[q64 >= 56] = 15
            mask = (q64 > 7) & (q64 < 56)
            out[mask] = np.where(((q64[mask] - 7) // 3) > dither[mask], 15, 0)
            return out

    def diff(self, cur, mode=0):
        with self.last_lock:
            cur_view = cur.T[::-1]
            last_view = self.last.T[::-1]
            cur_flat = np.frombuffer(cur_view.tobytes(), np.uint8)
            last_flat = np.frombuffer(last_view.tobytes(), np.uint8)

        # 根据mode选择参数
        if mode == 2:
            group_size = 8
            byte_idx = self.byte_idx_8
            bit_idx = self.bit_idx_8
            bitmap_len = self.bitmap_len_8
        else:
            group_size = 4
            byte_idx = self.byte_idx_4
            bit_idx = self.bit_idx_4
            bitmap_len = self.bitmap_len_4

        # 分组比较
        cur_padded = np.pad(cur_flat, (0, self._pad_len))
        last_padded = np.pad(last_flat, (0, self._pad_len))
        cur_g = cur_padded.reshape(-1, group_size)
        last_g = last_padded.reshape(-1, group_size)

        mask = ~np.all(cur_g == last_g, 1)
        cnt = mask.sum()

        # 生成bitmap
        if 0 < cnt < len(mask):
            bmp = np.zeros(bitmap_len, np.uint8)
            np.add.at(bmp, byte_idx[mask], 1 << bit_idx[mask])
            bmp = bmp.tobytes()
        elif cnt == len(mask):
            bmp = b'\xFF' * bitmap_len
        else:
            bmp = b'\x00' * bitmap_len

        # 打包变化数据
        data = b''
        if cnt:
            pixels = cur_g[mask]

            if mode == 2:
                # mode 2: 每个像素1bit，8像素=1字节
                # 像素值只能是0或15，映射到0或1
                bits = (pixels == 15).astype(np.uint8)
                # 每8个bit打包成一个字节
                data = np.packbits(bits.reshape(-1), bitorder='big').tobytes()
            else:
                # mode 0/1: 每个像素2bit，4像素=1字节
                enc = np.zeros_like(pixels, np.uint8)
                enc[pixels == 6] = 1
                enc[pixels == 15] = 2
                data = ((enc[:, 0] << 6) | (enc[:, 1] << 4) |
                        (enc[:, 2] << 2) | enc[:, 3]).tobytes()

        return bmp + data, cnt

    def update_last_frame(self, frame):
        with self.last_lock:
            self.last = frame

    def scale_coords(self, x_client, y_client, region):
        if not region:
            return round(x_client), round(y_client)

        x0, y0, x1, y1 = region
        region_w, region_h = x1 - x0, y1 - y0

        if region_w / region_h > 1:
            screen_x = x0 + y_client * region_w / self.h
            screen_y = y0 + (self.w - 1 - x_client) * region_h / self.w
            return round(screen_x), round(screen_y)

        return round(x0 + x_client * region_w / self.w), round(y0 + y_client * region_h / self.h)


class App:
    def __init__(self):
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

        self.w, self.h, self.scale = 9, 16, 50
        self.target_w, self.target_h = 540, 960
        self.border, self.pad, self.status_h = 6, 5, 30
        self.canvas_w = self.w * self.scale + 2 * self.border
        self.canvas_h = self.h * self.scale + 2 * self.border
        self.host, self.port = "0.0.0.0", 8080

        self.running, self._closing = True, False
        self.client = None
        self.client_started = False
        self.lock = threading.Lock()

        self.proc = ScreenProcessor(self.target_w, self.target_h)
        self.ip = self.proc.ip()
        self.loop = None
        self.mouse = Controller()

        self.capture_lock = threading.Lock()
        self.mode, self.is_capturing = 0, False
        self.monitor_timer = None

        self.processing_lock = threading.Lock()
        self.sender_trigger = threading.Event()
        self._sender_thread = None
        self._pending_frame = None

        self.latest_screen_data = None
        self.latest_quantized = None
        self._monitor_state = {'cnt': 0, 'cur_frame': None}

        self.sender_active = False
        self.sender_stop_event = threading.Event()
        self.ack_event = threading.Event()
        self.last_valid_region = None

        self.fps_timestamps = []
        self.zeroconf = None
        self.mdns_alive = False
        self.mdns_domain = "edcbook_cast.local"
        self.mdns_check_timer = None

        self._init_gui()
        self.gui_queue = queue.Queue()
        self.root.after(100, self._process_queue)
        self.monitor_interval = 0.01
        self._start_server()

    def _init_gui(self):
        self.root = tk.Tk()
        self.root.title("EDCBook Caster 1.0")
        self.root.attributes('-topmost', True)
        # -transparentcolor 仅在 Windows 上支持，macOS 会报错
        if os.name == 'nt':
            self.root.wm_attributes('-transparentcolor', 'white')
        self.root.configure(bg='white')
        self.root.minsize(200, self.status_h + 100)

        self.fps_var = tk.StringVar(value="FPS: 0")
        self.mdns_var = tk.StringVar(value=f"ws://{self.ip}:{self.port}")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.root,
            bg='white',
            highlightbackground='black',
            highlightthickness=self.border
        )
        self.canvas.grid(row=0, column=0, sticky='nsew', padx=self.pad, pady=self.pad)

        status = tk.Frame(self.root, relief=tk.SUNKEN, height=self.status_h)
        status.grid(row=1, column=0, sticky='ew')
        status.grid_propagate(False)

        tk.Label(status, textvariable=self.mdns_var, font=('', 9)).pack(
            side=tk.LEFT, padx=(10, 20), pady=5
        )

        status_right = tk.Frame(status, bg=status.cget('background'))
        status_right.pack(side=tk.RIGHT, padx=(0, 10), pady=5)

        tk.Label(status_right, textvariable=self.fps_var, font=('', 9), width=12, anchor='e').pack(
            side=tk.LEFT, padx=(0, 15)
        )

        self.status_canvas = tk.Canvas(status_right, width=14, height=14,
                                       bg=status.cget('background'), highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT)
        self.status_light = self.status_canvas.create_oval(1, 1, 13, 13, fill='#666666')

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.geometry(
            f"{self.canvas_w + 2 * self.pad}x{self.canvas_h + 2 * self.pad + self.status_h}+100+100"
        )

    def _process_queue(self):
        try:
            while True:
                item = self.gui_queue.get_nowait()
                if not self._closing and item:
                    func, args, kwargs = item[0], item[1] if len(item) > 1 and item[1] is not None else ((),), item[
                        2] if len(item) > 2 else {}
                    if not isinstance(args, tuple):
                        args = (args,)
                    func(*args, **kwargs)
        except queue.Empty:
            pass
        except:
            pass

        if not self._closing:
            self.root.after(100, self._process_queue)

    def region(self):
        if self._closing:
            return self.last_valid_region

        try:
            if self.root.state() == 'iconic':
                return self.last_valid_region
            if self.root.state() != 'normal':
                return None

            x, y = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()

            if w <= 2 * self.border or h <= 2 * self.border:
                return self.last_valid_region

            region = (x + self.border, y + self.border, x + w - self.border, y + h - self.border)
            x0, y0, x1, y1 = region

            if x1 <= x0 or y1 <= y0:
                return self.last_valid_region

            self.last_valid_region = region
            return region
        except:
            return self.last_valid_region

    def _quick_change_count(self, cur, last):
        with self.proc.last_lock:
            last_view = last.T[::-1]
            last_flat = np.frombuffer(last_view.tobytes(), np.uint8)

        cur_flat = np.frombuffer(cur.T[::-1].tobytes(), np.uint8)
        cur_padded = np.pad(cur_flat, (0, self.proc._pad_len))
        last_padded = np.pad(last_flat, (0, self.proc._pad_len))
        cur_g = cur_padded.reshape(-1, 4)
        last_g = last_padded.reshape(-1, 4)

        return (~np.all(cur_g == last_g, 1)).sum()

    def _monitor(self):
        if self._closing:
            return

        if self.processing_lock.locked():
            self._reschedule_monitor()
            return

        try:
            with self.capture_lock:
                if not self.is_capturing:
                    return
                mode = self.mode

            region = self.region()
            if not region:
                return

            img = self.proc.capture(region)
            if img is None:
                return

            q = self.proc.quantize(img, mode)
            if q is None:
                return

            cnt = self._quick_change_count(q, self.proc.last)

            if cnt >= self.proc.thresh:
                self._pending_frame = q
                self.sender_trigger.set()
                print(f"[监控] 变化检测: cnt={cnt}")
            else:
                self._pending_frame = None

        finally:
            self._reschedule_monitor()

    def _reschedule_monitor(self):
        if not self._closing:
            with self.capture_lock:
                if self.is_capturing:
                    self.monitor_timer = threading.Timer(self.monitor_interval, self._monitor)
                    self.monitor_timer.start()

    def _sender_worker(self):
        print("[Sender] 线程启动")

        while not self._closing:
            self.sender_trigger.wait()
            self.sender_trigger.clear()

            if self._closing or not self.is_capturing:
                break

            cur_frame = getattr(self, '_pending_frame', None)
            if cur_frame is None:
                continue

            with self.processing_lock:
                print("[Sender] 处理帧...")
                # 传入当前mode以选择正确的打包方式
                data, cnt = self.proc.diff(cur_frame, self.mode)
                self._send_all(data)
                print(f"[Sender] 发送完成: len={len(data)}, cnt={cnt}")

                self.ack_event.clear()
                # 嵌入式设备可能较慢，超时时间放宽到 2.5 秒
                if not self.ack_event.wait(timeout=2.5):
                    print("[Sender] ACK超时（仍更新last继续发送）")
                # 无论是否收到 ACK 都更新 last，避免卡死；设备不回复 ACK 时仍可投屏
                self.proc.update_last_frame(cur_frame)
                if self.ack_event.is_set():
                    print("[Sender] last帧已更新")

            time.sleep(0.01)

        print("[Sender] 线程退出")

    def _send_all(self, data):
        try:
            with self.lock:
                if self.client:
                    asyncio.run_coroutine_threadsafe(self._send_client(self.client, data), self.loop)
                    self._record_frame_send()
        except:
            pass

    def _record_frame_send(self):
        current_time = time.time()
        self.fps_timestamps.append(current_time)
        cutoff_time = current_time - 3.0
        self.fps_timestamps = [t for t in self.fps_timestamps if t > cutoff_time]

        fps = len(self.fps_timestamps) / 3.0 if len(self.fps_timestamps) > 1 else 0
        self.fps_var.set(f"FPS: {fps:.1f}")

    async def _send_client(self, ws, data):
        try:
            await ws.send(data)
        except:
            await self._remove(ws)

    def start_capture(self, mode=0):
        if self._closing or mode not in [0, 1, 2]:
            return

        with self.capture_lock:
            if self.is_capturing:
                return

            self.mode = mode
            self.is_capturing = True
            self.proc.reset_last_to_white()
            self._pending_frame = None
            self.fps_timestamps.clear()

            if self._sender_thread is None or not self._sender_thread.is_alive():
                self._sender_thread = threading.Thread(target=self._sender_worker, daemon=True)
                self._sender_thread.start()

        print(f"[捕获] 启动，模式={mode}")

        if not self._closing:
            self.monitor_timer = threading.Timer(self.monitor_interval, self._monitor)
            self.monitor_timer.start()

    def stop_capture(self):
        if self._closing:
            return

        with self.capture_lock:
            if not self.is_capturing:
                return

            self.is_capturing = False
            self.sender_stop_event.set()
            self.proc.reset_last_to_white()
            self.fps_timestamps.clear()
            self.fps_var.set("FPS: 0")

            if self.monitor_timer:
                self.monitor_timer.cancel()
                self.monitor_timer = None

        print("[捕获] 停止")

    async def _handle_msg(self, ws, msg):
        try:
            # 兼容客户端发来 bytes（部分设备用二进制发 JSON）
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='ignore')
            if not isinstance(msg, str) or not msg.strip():
                return
            data = json.loads(msg)
            msg_type = data.get('type')

            if msg_type == 'start':
                print(f"[消息] 客户端启动: mode={data.get('mode', 0)}")
                with self.lock:
                    self.client_started = True
                self.gui_queue.put((self.start_capture, data.get('mode', 0), {}))
                self.gui_queue.put((self._update_clients, (), {}))
            elif msg_type == 'stop':
                print("[消息] 客户端停止")
                with self.lock:
                    self.client_started = False
                self.gui_queue.put((self.stop_capture, (), {}))
                self.gui_queue.put((self._update_clients, (), {}))
            elif msg_type == 'ack':
                self.ack_event.set()
            elif msg_type == 'click':
                x = max(0, min(data.get('x', 0), self.target_w - 1))
                y = max(0, min(data.get('y', 0), self.target_h - 1))
                region = self.region()
                if region:
                    x, y = self.proc.scale_coords(x, y, region)
                    self.root.after(5, lambda: self._perform_click(x, y))
            elif msg_type == 'swipe':
                self.root.after(5, lambda: self._perform_scroll(-data.get('dx', 0), data.get('dy', 0)))
            else:
                print(f"[警告] 未知消息: {msg_type}")
        except Exception as e:
            print(f"[错误] 消息处理失败: {e}")

    def _perform_click(self, x, y):
        try:
            self.mouse.position = (x, y)
            self.mouse.click(Button.left, 1)
        except Exception as e:
            print(f"[错误] 点击失败: {e}")

    def _perform_scroll(self, dx, dy):
        try:
            self.mouse.scroll(dx, dy)
        except Exception as e:
            print(f"[错误] 滚动失败: {e}")

    async def _remove(self, ws):
        with self.lock:
            if self.client == ws:
                self.client = None
                self.client_started = False
                if not self._closing:
                    self.gui_queue.put((self._update_clients, (), {}))

        if not self._closing:
            self.gui_queue.put((self.stop_capture, (), {}))
            print("[连接] 客户端断开")

    async def handle(self, ws):
        with self.lock:
            if self.client is not None:
                old_client = self.client
                self.client = None
                self.client_started = False
                try:
                    asyncio.run_coroutine_threadsafe(old_client.close(), self.loop)
                except:
                    pass
                print("[连接] 断开旧客户端")

            self.client = ws
            self.client_started = False
            if not self._closing:
                self.gui_queue.put((self._update_clients, (), {}))

        print("[连接] 新客户端接入")

        try:
            async for message in ws:
                if self._closing:
                    break
                await self._handle_msg(ws, message)
        except Exception as e:
            print(f"[错误] WebSocket异常: {e}")
        finally:
            await self._remove(ws)

    async def serve(self):
        print(f"[服务器] 启动于 {self.host}:{self.port}")
        async with serve(self.handle, self.host, self.port) as server:
            while self.running and not self._closing:
                await asyncio.sleep(0.1)
            server.close()
            await server.wait_closed()
        print("[服务器] 已停止")

    def _start_server(self):
        def run():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self.serve())
            except Exception as e:
                if not self._closing:
                    print(f"[服务器错误] {e}")
            finally:
                try:
                    self.loop.close()
                except:
                    pass

        threading.Thread(target=run, daemon=True).start()
        self._register_mdns()

    def _register_mdns(self):
        try:
            self.zeroconf = Zeroconf()
            service_info = ServiceInfo(
                "_ws._tcp.local.",
                f"{self.mdns_domain}._ws._tcp.local.",
                addresses=[socket.inet_aton(self.ip)],
                port=self.port,
                properties={'path': '/'},
                server=f"{self.mdns_domain}."
            )

            self.zeroconf.register_service(service_info)
            print(f"[mDNS] 注册中: {self.mdns_domain}:{self.port}")

            # 立即验证
            self.root.after(1000, self._verify_mdns)

        except Exception as e:
            self.mdns_alive = False
            self.mdns_var.set(f"ws://{self.ip}:{self.port}")
            print(f"[mDNS] 注册失败: {e}")

    def _verify_mdns(self):
        try:
            # 方法1: 直接查询
            resolver = Zeroconf()
            info = resolver.get_service_info("_ws._tcp.local.", f"{self.mdns_domain}._ws._tcp.local.", timeout=1000)

            if info and self.ip in [socket.inet_ntoa(addr) for addr in info.addresses]:
                self.mdns_alive = True
                self.mdns_var.set(f"ws://{self.mdns_domain}:{self.port}")
                print(f"[mDNS] 验证成功: {self.mdns_domain}:{self.port}")
            else:
                # 方法2: 尝试解析
                try:
                    resolved_ip = socket.gethostbyname(self.mdns_domain)
                    if resolved_ip == self.ip:
                        self.mdns_alive = True
                        self.mdns_var.set(f"ws://{self.mdns_domain}:{self.port}")
                        print(f"[mDNS] 解析验证成功: {self.mdns_domain} -> {resolved_ip}")
                    else:
                        raise Exception(f"IP不匹配: {resolved_ip} != {self.ip}")
                except:
                    raise Exception("无法解析域名")

            resolver.close()

            # 启动定期复检
            if self.mdns_alive:
                self._schedule_mdns_check()

        except Exception as e:
            self.mdns_alive = False
            self.mdns_var.set(f"ws://{self.ip}:{self.port}")
            print(f"[mDNS] 验证失败，使用IP: {e}")

    def _schedule_mdns_check(self):
        if self._closing or not self.mdns_alive:
            return

        try:
            resolver = Zeroconf()
            info = resolver.get_service_info("_ws._tcp.local.", f"{self.mdns_domain}._ws._tcp.local.", timeout=3000)

            if not info or self.ip not in [socket.inet_ntoa(addr) for addr in info.addresses]:
                print("[mDNS] 服务异常，降级到IP")
                self.mdns_alive = False
                self.mdns_var.set(f"ws://{self.ip}:{self.port}")

            resolver.close()
        except:
            pass

        # 30秒后再次检查
        if not self._closing and self.mdns_alive:
            self.mdns_check_timer = threading.Timer(30.0, self._schedule_mdns_check)
            self.mdns_check_timer.start()

    def _update_clients(self):
        with self.lock:
            if not self.client:
                color = '#666666'
            elif self.client_started:
                color = '#00ff00'
            else:
                color = '#ffff00'
            self.status_canvas.itemconfig(self.status_light, fill=color)

    def close(self):
        if self._closing:
            os._exit(0)

        print("\n" + "=" * 50)
        print("[关闭] 正在停止所有组件...")

        self._closing = True

        if self.monitor_timer:
            self.monitor_timer.cancel()

        if self.mdns_check_timer:
            self.mdns_check_timer.cancel()

        self.sender_trigger.set()
        self.stop_capture()
        self.running = False

        if self.zeroconf:
            try:
                self.zeroconf.unregister_all_services()
                self.zeroconf.close()
                print("[mDNS] 服务已注销")
            except:
                pass

        with self.lock:
            if self.client:
                try:
                    asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
                except:
                    pass
                self.client = None
                self.client_started = False

        time.sleep(0.2)
        try:
            self.root.destroy()
        except:
            pass

        print("[关闭] 程序已完全退出")
        print("=" * 50 + "\n")
        os._exit(0)


if __name__ == '__main__':
    print("=" * 50)
    print("屏幕投屏服务器已启动 (单客户端版)")
    print("等待客户端连接...")
    print("=" * 50 + "\n")

    app = App()
    app.root.mainloop()

# pyinstaller --onefile --windowed --name="EDCBook Caster" edcbook_caster.py