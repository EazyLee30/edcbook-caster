# EDCBook Caster

PC 端投屏服务端，将电脑画面实时投到 EDC Book / M5Stack Paper 等墨水屏设备，并支持触控反控电脑。

PC casting server: stream your screen to EDC Book / M5Stack Paper (e-ink) in real time, with touch control to operate the PC.

---

## 固件 / Firmware

**设备端固件**需配合本工具使用。EDC Book 相关固件（含互动投屏）可在以下途径获取：

**Device firmware** is required. EDC Book–related firmware (including interactive casting) can be obtained from:

- **M5Burner**：在 [M5Burner](https://m5burner.m5stack.com/) 中搜索并下载 EDC Book / 梦西游啊游 等固件。  
  Download EDC Book / 梦西游啊游 firmware from [M5Burner](https://m5burner.m5stack.com/).

- **致谢**：互动投屏等功能基于 **梦西游啊游** 大佬的原创固件与协议，本仓库仅提供 PC 端 Caster 工具。  
  **Credits**: Interactive casting is based on the original firmware and protocol by **梦西游啊游**. This repo only provides the PC-side Caster tool.

---

## 功能 / Features

- 实时传输电脑画面到墨水屏 / Real-time screen streaming to e-ink
- 触控反控电脑（点击、滑动）/ Touch control (click, scroll) to operate the PC
- mDNS 发现（`edcbook_cast.local`）/ mDNS discovery
- 支持 Windows（官方）与 macOS（本仓库提供脚本与 DMG 构建）/ Windows (official) and macOS (script + DMG build in this repo)

---

## 使用说明 / Usage

### 前置条件 / Requirements

- 电脑与设备在同一局域网 / PC and device on the same LAN
- 设备已刷写支持互动投屏的固件（见上方「固件」）/ Device flashed with casting firmware (see **Firmware** above)

### 步骤 / Steps

1. 启动本工具，调整窗口中的截图区域（横竖屏均可）。  
   Launch the tool and adjust the capture area in the window (landscape or portrait).

2. 看软件左下角地址：  
   Check the address at the bottom-left:
   - 若为 **edcbook_cast.local**：设备上可直接打开「互动投屏」。  
     If it shows **edcbook_cast.local**, start “Interactive casting” on the device.
   - 若为 **IP 地址**：在设备的「在线配置」里填写该 WS 地址与端口（如 `ws://192.168.x.x:8080`）。  
     If it shows an **IP address**, set the WS address and port in the device’s “Online config” (e.g. `ws://192.168.x.x:8080`).

3. 投屏成功后可用设备触控操作电脑；长按屏幕退出投屏。  
   After casting starts, use the device to control the PC; long-press to exit.

---

## 运行方式 / How to Run

### 方式一：直接运行 / Run from source

```bash
pip install numpy pillow mss pynput websockets zeroconf
python EDCBook_Caster_1.0.py
```

（Windows 下可用 `python`，macOS 下多为 `python3`。  
On Windows use `python`, on macOS usually `python3`.)

### 方式二：macOS 安装包 / macOS app

- **DMG**：在仓库的 [Releases](https://github.com/你的用户名/edcbook-caster/releases) 下载 `EDCBook_Caster_1.0.dmg`，打开后把应用拖入「应用程序」。  
  Download `EDCBook_Caster_1.0.dmg` from Releases and drag the app into Applications.

- **自行构建**：在项目根目录执行  
  Build yourself: run in project root:

```bash
./build_dmg.sh
```

会生成 `EDCBook_Caster_1.0.dmg`。  
This produces `EDCBook_Caster_1.0.dmg`.

### 方式三：Windows

Windows 版由梦西游啊游等提供，本仓库主要维护 macOS 端与源码。  
Windows builds are provided elsewhere; this repo focuses on macOS and source code.

---

## 依赖 / Dependencies

- Python 3.x
- numpy, Pillow, mss, pynput, websockets, zeroconf

---

## 许可证 / License

请遵守梦西游啊游固件与协议的相关说明。本 Caster 工具源码仅供学习与配合 EDC Book 使用。  
Use in accordance with 梦西游啊游’s firmware and protocol terms. This Caster source is for learning and use with EDC Book only.

---

**推送到 GitHub**：在 GitHub 新建仓库（如 `edcbook-caster`）后，将本 README 中「你的用户名」替换为你的 GitHub 用户名，再执行 `git init && git add . && git commit -m "Initial commit" && git remote add origin https://github.com/你的用户名/edcbook-caster.git && git push -u origin main`（若默认分支为 `master` 请改为 `master`）。  
**Publish to GitHub**: Create a new repo (e.g. `edcbook-caster`), replace “你的用户名” in this README with your GitHub username, then run the git commands above (use `master` if that’s your default branch).
