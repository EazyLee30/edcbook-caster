import struct
import os
import freetype
from tqdm import tqdm
from itertools import chain
import multiprocessing
import numpy as np
import time
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os.path
import warnings
import webbrowser
import re

# 忽略libpng警告
warnings.filterwarnings("ignore", category=UserWarning, message="libpng")

# 公共参数配置
FONT_CONFIG = {
    "MIN_FONT_SIZE": 24,  # 最小字体大小
    "MAX_FONT_SIZE": 48,  # 最大字体大小
    "MAX_CHAR_COUNT": 65536,  # 最大字符数
    "MIN_WHITE_THRESHOLD": 16,  # 白色门限最小值
    "MAX_WHITE_THRESHOLD": 92,  # 白色门限最大值
    "MIN_BLACK_THRESHOLD": 159,  # 黑色门限最小值
    "MAX_BLACK_THRESHOLD": 239,  # 黑色门限最大值
}

# 全局变量用于存储进度信息
progress_queue = queue.Queue()
stop_event = threading.Event()

# 语言资源
LANGUAGE_RESOURCES = {
    "zh": {
        "title": "阅读卡片 | 字体生成工具",
        "input_settings": "输入设置",
        "font_file": "字体文件:",
        "browse": "浏览",
        "output_file": "输出文件:",
        "generate_params": "生成参数",
        "font_size": f"字体大小 ({FONT_CONFIG['MIN_FONT_SIZE']}-{FONT_CONFIG['MAX_FONT_SIZE']}):",
        "font_size_desc": f"参数说明：{FONT_CONFIG['MIN_FONT_SIZE']}px最大支持18x19排版，{FONT_CONFIG['MAX_FONT_SIZE']}px最大支持12x13排版。",
        "white_threshold": f"白色门限 ({FONT_CONFIG['MIN_WHITE_THRESHOLD']}-{FONT_CONFIG['MAX_WHITE_THRESHOLD']}):",
        "white_threshold_desc": "参数说明：越小字体显示越平滑，越大字体越锐利并偏白",
        "black_threshold": f"黑色门限 ({FONT_CONFIG['MIN_BLACK_THRESHOLD']}-{FONT_CONFIG['MAX_BLACK_THRESHOLD']}):",
        "black_threshold_desc": "参数说明：越大字体显示越平滑，越小字体越锐利并偏黑",
        "charset_selection": "字符集选择",
        "full_charset": f"字体全量字符集 (上限{FONT_CONFIG['MAX_CHAR_COUNT']})",
        "common_charset": "常用字符集 (中文+西文)",
        "custom_charset": "自定义字符集 (Unicode):",
        "custom_placeholder": "0x0000-0xFFFF, 0x1234",
        "ready": "就绪",
        "generating": "处理中: {}/{} 字符 ({:.1f}%) - 实际生成: {}",
        "generating_no_count": "处理中: {}/{} 字符 ({:.1f}%)",
        "generate_font": "生成字体",
        "cancel": "取消",
        "exit": "退出",
        "author": "作者：梦西游啊游 | 版本：v1.20",
        "website": "更多信息请访问：",
        "website_link": "edcbook.cn",
        "complete_title": "完成",
        "complete_msg": "字体文件生成成功!\n\n总字符数: {}\n实际生成: {}\n文件路径: {}",
        "error_title": "错误",
        "error_font_file": "请选择有效的字体文件",
        "error_output_path": "请指定输出文件路径",
        "error_font_size": f"字体大小必须在{FONT_CONFIG['MIN_FONT_SIZE']}-{FONT_CONFIG['MAX_FONT_SIZE']}范围内",
        "error_white_threshold": f"白色门限必须在{FONT_CONFIG['MIN_WHITE_THRESHOLD']}-{FONT_CONFIG['MAX_WHITE_THRESHOLD']}范围内",
        "error_black_threshold": f"黑色门限必须在{FONT_CONFIG['MIN_BLACK_THRESHOLD']}-{FONT_CONFIG['MAX_BLACK_THRESHOLD']}范围内",
        "error_threshold_order": "黑色门限必须大于白色门限",
        "error_charset": "至少需要选择一个字符集",
        "error_custom_charset": "自定义字符集已选中但未提供字符范围",
        "cancelled": "操作已取消",
        "language_switch": "EN"
    },
    "en": {
        "title": "EDCBook | Font Tool",
        "input_settings": "Input Settings",
        "font_file": "Font File:",
        "browse": "Browse",
        "output_file": "Output File:",
        "generate_params": "Parameters",
        "font_size": f"Font Size ({FONT_CONFIG['MIN_FONT_SIZE']}-{FONT_CONFIG['MAX_FONT_SIZE']}):",
        "font_size_desc": f"Note: {FONT_CONFIG['MIN_FONT_SIZE']}px max 18x19 layout, {FONT_CONFIG['MAX_FONT_SIZE']}px max 12x13 layout.",
        "white_threshold": f"White Threshold ({FONT_CONFIG['MIN_WHITE_THRESHOLD']}-{FONT_CONFIG['MAX_WHITE_THRESHOLD']}):",
        "white_threshold_desc": "Lower=smoother, Higher=sharper & whiter",
        "black_threshold": f"Black Threshold ({FONT_CONFIG['MIN_BLACK_THRESHOLD']}-{FONT_CONFIG['MAX_BLACK_THRESHOLD']}):",
        "black_threshold_desc": "Higher=smoother, Lower=sharper & blacker",
        "charset_selection": "Charset Selection",
        "full_charset": f"Full Font Charset (Max {FONT_CONFIG['MAX_CHAR_COUNT']})",
        "common_charset": "Common Charset (Chinese+Latin)",
        "custom_charset": "Custom Charset (Unicode):",
        "custom_placeholder": "0x0000-0xFFFF, 0x1234",
        "ready": "Ready",
        "generating": "Processing: {}/{} chars ({:.1f}%) - Generated: {}",
        "generating_no_count": "Processing: {}/{} chars ({:.1f}%)",
        "generate_font": "Generate Font",
        "cancel": "Cancel",
        "exit": "Exit",
        "author": "Author: Mengxiyou | Version: v1.20",
        "website": "Visit: ",
        "website_link": "edcbook.com",
        "complete_title": "Complete",
        "complete_msg": "Font file generated successfully!\n\nTotal chars: {}\nGenerated: {}\nFile path: {}",
        "error_title": "Error",
        "error_font_file": "Please select a valid font file",
        "error_output_path": "Please specify an output file path",
        "error_font_size": f"Font size must be between {FONT_CONFIG['MIN_FONT_SIZE']}-{FONT_CONFIG['MAX_FONT_SIZE']}",
        "error_white_threshold": f"White threshold must be between {FONT_CONFIG['MIN_WHITE_THRESHOLD']}-{FONT_CONFIG['MAX_WHITE_THRESHOLD']}",
        "error_black_threshold": f"Black threshold must be between {FONT_CONFIG['MIN_BLACK_THRESHOLD']}-{FONT_CONFIG['MAX_BLACK_THRESHOLD']}",
        "error_threshold_order": "Black threshold must be greater than white threshold",
        "error_charset": "At least one charset must be selected",
        "error_custom_charset": "Custom charset selected but no range provided",
        "cancelled": "Operation cancelled",
        "language_switch": "中文"
    }
}

# 当前语言
CURRENT_LANGUAGE = "zh"


def update_progress(value, max_value=None, actual_count=None):
    """更新进度信息"""
    if max_value and actual_count is not None:
        progress_queue.put(("progress", value, max_value, actual_count))
    elif max_value:
        progress_queue.put(("progress", value, max_value))
    else:
        progress_queue.put(("progress", value))


def generate_binary_font(char_data, output_path, font_height):
    """生成二进制字体文件"""
    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 计算位图数据偏移量
    char_count = len(char_data)
    header_size = 4 + 1  # char_count (uint32_t) + font_size

    # 结构体大小 (紧密打包)
    entry_size = 20
    entries_size = char_count * entry_size
    current_offset = header_size + entries_size

    # 准备文件内容和位图数据
    bin_content = bytearray()
    entries = []
    bitmap_data = bytearray()

    # 添加文件头：字符数、字体大小
    bin_content.extend(struct.pack('<IB', char_count, font_height))

    # 处理每个字符条目
    for cp, bw, bh, w, xo, yo, bmp in char_data:
        # 打包字符条目
        entry = struct.pack('<HHBBbbIII',
                            cp,  # unicode (2字节)
                            w,  # width (2字节)
                            bw,  # bitmapW (1字节)
                            bh,  # bitmapH (1字节)
                            xo,  # x_offset (1字节，有符号)
                            yo,  # y_offset (1字节，有符号)
                            current_offset,  # bitmap_offset (4字节)
                            len(bmp),  # bitmap_size (4字节)
                            0)  # cached_bitmap 初始化为NULL (4字节)
        entries.append(entry)

        # 添加位图数据
        bitmap_data.extend(bmp)
        current_offset += len(bmp)  # 更新偏移量

    # 合并所有条目和位图数据
    for entry in entries:
        bin_content.extend(entry)
    bin_content.extend(bitmap_data)

    # 写入font.bin文件
    with open(output_path, 'wb') as f:
        f.write(bin_content)

    return output_path


def process_char(args):
    """处理单个字符的函数（用于多进程）"""
    font_path, font_height, char, ascender, white_threshold, black_threshold = args
    face = freetype.Face(font_path)
    face.set_pixel_sizes(0, font_height)

    codepoint = ord(char)
    if codepoint < 0x20 or codepoint == 0xFEFF:
        return (codepoint, 0, 0, 0, 0, 0, b'')

    # 检查字符是否在字体中存在
    if face.get_char_index(codepoint) == 0:
        # 字符不存在于字体中，直接返回空数据
        return None

    # 正常加载当前字符
    face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    bitmap = face.glyph.bitmap
    metrics = face.glyph.metrics

    # 使用NumPy加速位图处理
    if bitmap.buffer:
        bitmap_array = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows, bitmap.width))
    else:
        bitmap_array = np.zeros((bitmap.rows, bitmap.width), dtype=np.uint8)

    # 寻找非空区域
    non_empty_rows = np.any(bitmap_array >= white_threshold, axis=1)
    non_empty_cols = np.any(bitmap_array >= white_threshold, axis=0)

    if np.any(non_empty_rows) and np.any(non_empty_cols):
        min_y = np.argmax(non_empty_rows)
        max_y = bitmap.rows - 1 - np.argmax(non_empty_rows[::-1])
        min_x = np.argmax(non_empty_cols)
        max_x = bitmap.width - 1 - np.argmax(non_empty_cols[::-1])

        cropped_w = max_x - min_x + 1
        cropped_h = max_y - min_y + 1

        # 提取裁剪区域并量化
        cropped_area = bitmap_array[min_y:max_y + 1, min_x:max_x + 1]
        quantized = np.zeros_like(cropped_area, dtype=np.uint8)

        # 使用向量化操作
        low_mask = cropped_area < white_threshold
        high_mask = cropped_area > black_threshold
        mid_mask = ~(low_mask | high_mask)

        quantized[low_mask] = 15
        quantized[high_mask] = 0
        quantized[mid_mask] = (black_threshold - cropped_area[mid_mask]) // 14

        # 霍夫曼编码处理
        bits = []
        for v in quantized.flatten():
            if v == 15:
                bits.append('0')  # 白色像素
            elif v == 0:
                bits.append('10')  # 黑色像素
            else:
                binary_part = bin(v)[2:].zfill(4)
                bits.append('11' + binary_part)  # 灰度像素

        bitstream = ''.join(bits)

        # 将位流转换为字节数组
        byte_array = bytearray()
        current_byte = 0
        current_bit_position = 7  # 从最高位开始填充

        for bit in bitstream:
            if bit == '1':
                current_byte |= (1 << current_bit_position)
            current_bit_position -= 1
            if current_bit_position < 0:
                byte_array.append(current_byte)
                current_byte = 0
                current_bit_position = 7

        # 处理最后未满的字节
        if current_bit_position != 7:
            byte_array.append(current_byte)

        bitmap_data = bytes(byte_array)
        advance_width = metrics.horiAdvance >> 6
        x_offset = (metrics.horiBearingX >> 6) + min_x
        y_offset = (ascender - face.glyph.bitmap_top) + min_y

        return (codepoint, cropped_w, cropped_h, advance_width, x_offset, y_offset, bitmap_data)
    else:
        # 没有有效像素，保留空位图但保留度量信息
        advance_width = metrics.horiAdvance >> 6
        x_offset = metrics.horiBearingX >> 6
        y_offset = ascender - face.glyph.bitmap_top
        return (codepoint, 0, 0, advance_width, x_offset, y_offset, b'')


def parse_custom_charset(custom_text):
    """解析自定义字符集文本"""
    chars = set()

    # 增强正则表达式，允许空格和更灵活的分隔符
    pattern = r'0x[0-9A-Fa-f]+\s*-\s*0x[0-9A-Fa-f]+|0x[0-9A-Fa-f]+'

    # 查找所有匹配的范围或单个字符
    matches = re.findall(pattern, custom_text, re.IGNORECASE)

    for match in matches:
        # 移除所有空格
        match = re.sub(r'\s', '', match)

        if '-' in match:
            # 处理范围
            start_hex, end_hex = match.split('-')
            try:
                start = int(start_hex, 16)
                end = int(end_hex, 16)

                # 确保范围有效
                if start > end:
                    start, end = end, start

                # 只处理0x0000-0xffff范围的字符
                if start > 0xffff:
                    continue
                end = min(end, 0xffff)

                for code_point in range(start, end + 1):
                    try:
                        chars.add(chr(code_point))
                    except ValueError:
                        # 跳过无效的Unicode代码点
                        pass
            except ValueError:
                # 跳过无效的十六进制数
                pass
        else:
            # 处理单个字符
            try:
                code_point = int(match, 16)
                # 只处理0x0000-0xffff范围的字符
                if code_point <= 0xffff:
                    try:
                        chars.add(chr(code_point))
                    except ValueError:
                        # 跳过无效的Unicode代码点
                        pass
            except ValueError:
                # 跳过无效的十六进制数
                pass

    return list(chars)


def get_common_charset():
    """获取常用字符集（合并中文和西文字符集）"""
    chars = set()

    # 添加中文字符集
    chinese_chars = get_chinese_charset()
    chars.update(chinese_chars)

    # 添加西文字符集
    latin_chars = get_latin_charset()
    chars.update(latin_chars)

    return list(chars)


def get_chinese_charset():
    """获取中文字符集"""
    chars = set()

    # 完整GBK扫描
    for lead in range(0x81, 0xFF):  # 首字节 0x81-0xFE
        if stop_event.is_set():
            break

        for trail in chain(range(0x40, 0x7F), range(0x80, 0xFE + 1)):
            try:
                char = bytes([lead, trail]).decode('gbk')
                # 只保留0x0000-0xffff范围的字符
                if ord(char) <= 0xffff:
                    chars.add(char)
            except UnicodeDecodeError:
                pass

    return list(chars)


def get_latin_charset():
    """获取西文字符集"""
    chars = set()

    # 基本ASCII
    chars.update([chr(c) for c in range(0x20, 0x7F)])

    # 拉丁-1补充
    chars.update([chr(c) for c in range(0xA0, 0x100)])

    # 拉丁扩展-A
    chars.update([chr(c) for c in range(0x100, 0x180)])

    # 拉丁扩展-B (部分)
    chars.update([chr(c) for c in range(0x180, 0x250)])

    # 国际音标扩展 (部分)
    chars.update([chr(c) for c in range(0x250, 0x2B0)])

    # 常用标点符号
    chars.update([chr(c) for c in range(0x2000, 0x2070)])

    # 货币符号
    chars.update([chr(c) for c in range(0x20A0, 0x20D0)])

    # 字母符号
    chars.update([chr(c) for c in range(0x2100, 0x2150)])

    # 数字形式
    chars.update([chr(c) for c in range(0x2150, 0x2190)])

    # 箭头
    chars.update([chr(c) for c in range(0x2190, 0x2200)])

    # 数学运算符
    chars.update([chr(c) for c in range(0x2200, 0x2300)])

    # 杂项技术符号
    chars.update([chr(c) for c in range(0x2300, 0x2400)])

    # 制表符
    chars.update([chr(c) for c in range(0x2400, 0x2420)])

    # 几何图形
    chars.update([chr(c) for c in range(0x25A0, 0x2600)])

    # 杂项符号
    chars.update([chr(c) for c in range(0x2600, 0x2700)])

    # 丁贝符
    chars.update([chr(c) for c in range(0x2700, 0x2750)])

    # 只保留0x0000-0xffff范围的字符
    chars = [c for c in chars if ord(c) <= 0xffff]
    return chars


def get_full_charset(font_path):
    """获取字体全量字符集，优先加载常用字符集"""
    chars = set()

    # 首先添加常用字符集（中文+西文）
    common_chars = get_common_charset()
    chars.update(common_chars)

    # 如果已经达到上限，直接返回
    if len(chars) >= FONT_CONFIG["MAX_CHAR_COUNT"]:
        return list(chars)[:FONT_CONFIG["MAX_CHAR_COUNT"]]

    # 使用FreeType的字符映射表迭代器获取其他字符
    # 这种方法比遍历整个Unicode范围更高效
    face = freetype.Face(font_path)
    charcode, gindex = face.get_first_char()
    while gindex != 0 and len(chars) < FONT_CONFIG["MAX_CHAR_COUNT"]:
        try:
            # 将字符代码转换为Unicode字符，只处理0x0000-0xffff范围的字符
            if charcode <= 0xffff:  # 只处理0x0000-0xffff范围的字符
                chars.add(chr(charcode))
        except (ValueError, TypeError):
            # 跳过无效的字符代码
            pass

        # 获取下一个字符
        charcode, gindex = face.get_next_char(charcode, gindex)

    return list(chars)


def generate_font_file(font_path, output_path,
                       font_height=30,
                       white_threshold=32,
                       black_threshold=223,
                       use_common=True,
                       use_custom=False,
                       use_full=False,
                       custom_charset=""):
    """
    生成字体文件的主函数

    参数:
        font_path (str): 字体文件路径
        output_path (str): 输出文件路径
        font_height (int): 字体像素大小 (16-42)
        white_threshold (int): 白色门限值 (16-92)
        black_threshold (int): 黑色门限值 (159-239)
        use_common (bool): 是否包含常用字符集（中文+西文）
        use_custom (bool): 是否使用自定义字符集
        use_full (bool): 是否使用字体全量字符集
        custom_charset (str): 自定义字符集范围文本
    """
    # 参数验证 - 使用公共参数
    if not (FONT_CONFIG["MIN_FONT_SIZE"] <= font_height <= FONT_CONFIG["MAX_FONT_SIZE"]):
        raise ValueError(f"字体大小必须在{FONT_CONFIG['MIN_FONT_SIZE']}-{FONT_CONFIG['MAX_FONT_SIZE']}范围内")
    if not (FONT_CONFIG["MIN_WHITE_THRESHOLD"] <= white_threshold <= FONT_CONFIG["MAX_WHITE_THRESHOLD"]):
        raise ValueError(
            f"白色门限必须在{FONT_CONFIG['MIN_WHITE_THRESHOLD']}-{FONT_CONFIG['MAX_WHITE_THRESHOLD']}范围内")
    if not (FONT_CONFIG["MIN_BLACK_THRESHOLD"] <= black_threshold <= FONT_CONFIG["MAX_BLACK_THRESHOLD"]):
        raise ValueError(
            f"黑色门限必须在{FONT_CONFIG['MIN_BLACK_THRESHOLD']}-{FONT_CONFIG['MAX_BLACK_THRESHOLD']}范围内")
    if black_threshold <= white_threshold:
        raise ValueError("黑色门限必须大于白色门限")

    # 验证字符集选项
    if not (use_common or use_custom or use_full):
        raise ValueError("至少需要选择一个字符集")

    try:
        face = freetype.Face(font_path)
    except freetype.FT_Exception:
        raise RuntimeError(f"无法加载字体文件: {font_path}")

    face.set_pixel_sizes(0, font_height)

    # 收集字符集
    chars = set()

    # 添加特殊字符（始终包含）
    chars.add('\uFEFF')  # 添加BOM

    # 根据选项添加字符集（可以叠加）
    if use_full:
        # 获取字体全量字符集（优先包含常用字符集）
        full_chars = get_full_charset(font_path)
        chars.update(full_chars)
    else:
        # 原有的字符集选择逻辑
        if use_common:
            common_chars = get_common_charset()
            chars.update(common_chars)

        if use_custom:
            custom_chars = parse_custom_charset(custom_charset)
            chars.update(custom_chars)

    # 预处理字体度量
    face.load_char(' ', freetype.FT_LOAD_RENDER)
    ascender = face.size.ascender >> 6

    # 准备多进程参数
    args = [(font_path, font_height, char, ascender, white_threshold, black_threshold) for char in chars]
    total_chars = len(chars)  # 这是实际的总字符数
    processed_chars = 0
    actual_count = 0  # 实际生成的字符数

    char_data = [(cp, 0, 0, 0, 0, 0, b'') for cp in range(0, 0x20)]

    # 使用多进程处理
    with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
        results = []
        for result in pool.imap(process_char, args):
            if stop_event.is_set():
                pool.terminate()
                return

            # 只添加有效的结果（字符在字体中存在）
            if result is not None:
                results.append(result)
                actual_count += 1

            processed_chars += 1
            update_progress(processed_chars, total_chars, actual_count)

    char_data += results

    # 应用最大字符数限制 - 使用公共参数
    if len(char_data) > FONT_CONFIG["MAX_CHAR_COUNT"]:
        char_data = char_data[:FONT_CONFIG["MAX_CHAR_COUNT"]]
        actual_count = FONT_CONFIG["MAX_CHAR_COUNT"] - 32  # 减去控制字符的数量

    # 添加控制字符
    char_data.sort(key=lambda x: x[0])

    # 生成二进制字体文件
    bin_path = generate_binary_font(char_data, output_path, font_height)

    return bin_path, total_chars, len(char_data)


def generate_font_in_thread(font_path, output_path, font_height, white_threshold, black_threshold,
                            use_common, use_custom, use_full, custom_charset):
    """在单独线程中生成字体文件"""
    try:
        bin_path, total_chars, actual_chars = generate_font_file(
            font_path=font_path,
            output_path=output_path,
            font_height=font_height,
            white_threshold=white_threshold,
            black_threshold=black_threshold,
            use_common=use_common,
            use_custom=use_custom,
            use_full=use_full,
            custom_charset=custom_charset
        )
        progress_queue.put(("complete", bin_path, total_chars, actual_chars))
    except Exception as e:
        progress_queue.put(("error", str(e)))


# GUI 界面
class FontGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EDCBook FontTool")
        self.root.geometry("500x750")  # 调整高度以适应新布局
        self.root.resizable(False, False)  # 固定大小

        # 当前语言
        self.current_language = "zh"

        # 创建主框架
        main_frame = ttk.Frame(root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 语言切换按钮 - 右上角
        self.language_button = ttk.Button(main_frame, text=self.get_text("language_switch"),
                                          command=self.toggle_language, width=4)
        self.language_button.place(relx=0.95, rely=0.01, anchor=tk.NE)

        # 标题
        self.title_label = ttk.Label(main_frame, text=self.get_text("title"), font=("Arial", 16, "bold"))
        self.title_label.pack(pady=(0, 15))

        # 输入框架
        self.input_frame = ttk.LabelFrame(main_frame, text=self.get_text("input_settings"), padding=10)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        # 字体文件选择
        self.font_file_label = ttk.Label(self.input_frame, text=self.get_text("font_file"))
        self.font_file_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.font_path = tk.StringVar()
        font_entry = ttk.Entry(self.input_frame, textvariable=self.font_path, width=35)
        font_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        self.browse_font_button = ttk.Button(self.input_frame, text=self.get_text("browse"), command=self.browse_font,
                                             width=8)
        self.browse_font_button.grid(row=0, column=2, padx=5, pady=5)

        # 输出文件选择
        self.output_file_label = ttk.Label(self.input_frame, text=self.get_text("output_file"))
        self.output_file_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

        self.output_path = tk.StringVar()
        output_entry = ttk.Entry(self.input_frame, textvariable=self.output_path, width=35)
        output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        self.browse_output_button = ttk.Button(self.input_frame, text=self.get_text("browse"),
                                               command=self.browse_output, width=8)
        self.browse_output_button.grid(row=1, column=2, padx=5, pady=5)

        # 参数设置
        self.params_frame = ttk.LabelFrame(main_frame, text=self.get_text("generate_params"), padding=10)
        self.params_frame.pack(fill=tk.X, padx=5, pady=10)

        # 字体大小
        self.font_size_label = ttk.Label(self.params_frame, text=self.get_text("font_size"))
        self.font_size_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

        self.font_size = tk.IntVar(value=30)
        font_size_scale = ttk.Scale(self.params_frame,
                                    from_=FONT_CONFIG["MIN_FONT_SIZE"],
                                    to=FONT_CONFIG["MAX_FONT_SIZE"],
                                    variable=self.font_size,
                                    orient=tk.HORIZONTAL, length=180, command=self.update_font_size)
        font_size_scale.grid(row=0, column=1, padx=5, pady=2)

        self.font_size_value_label = ttk.Label(self.params_frame, textvariable=self.font_size, width=3)
        self.font_size_value_label.grid(row=0, column=2, padx=5, pady=2)

        # 添加描述
        self.desc_label1 = ttk.Label(self.params_frame, text=self.get_text("font_size_desc"),
                                     foreground="gray", font=("Arial", 9))
        self.desc_label1.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # 白色门限
        self.white_threshold_label = ttk.Label(self.params_frame, text=self.get_text("white_threshold"))
        self.white_threshold_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)

        self.white_threshold = tk.IntVar(value=32)
        white_scale = ttk.Scale(self.params_frame,
                                from_=FONT_CONFIG["MIN_WHITE_THRESHOLD"],
                                to=FONT_CONFIG["MAX_WHITE_THRESHOLD"],
                                variable=self.white_threshold,
                                orient=tk.HORIZONTAL, length=180, command=self.update_white_threshold)
        white_scale.grid(row=2, column=1, padx=5, pady=2)

        self.white_value_label = ttk.Label(self.params_frame, textvariable=self.white_threshold, width=3)
        self.white_value_label.grid(row=2, column=2, padx=5, pady=2)

        # 添加描述
        self.desc_label2 = ttk.Label(self.params_frame, text=self.get_text("white_threshold_desc"),
                                     foreground="gray", font=("Arial", 9))
        self.desc_label2.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=0)

        # 黑色门限
        self.black_threshold_label = ttk.Label(self.params_frame, text=self.get_text("black_threshold"))
        self.black_threshold_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)

        self.black_threshold = tk.IntVar(value=223)
        black_scale = ttk.Scale(self.params_frame,
                                from_=FONT_CONFIG["MIN_BLACK_THRESHOLD"],
                                to=FONT_CONFIG["MAX_BLACK_THRESHOLD"],
                                variable=self.black_threshold,
                                orient=tk.HORIZONTAL, length=180, command=self.update_black_threshold)
        black_scale.grid(row=4, column=1, padx=5, pady=2)

        self.black_value_label = ttk.Label(self.params_frame, textvariable=self.black_threshold, width=3)
        self.black_value_label.grid(row=4, column=2, padx=5, pady=2)

        # 添加描述
        self.desc_label3 = ttk.Label(self.params_frame, text=self.get_text("black_threshold_desc"),
                                     foreground="gray", font=("Arial", 9))
        self.desc_label3.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=5, pady=0)

        # 字符集选择框架
        self.charset_frame = ttk.LabelFrame(main_frame, text=self.get_text("charset_selection"), padding=10)
        self.charset_frame.pack(fill=tk.X, padx=5, pady=10)

        # 字体全量字符集复选框 - 作为总开关
        self.use_full = tk.BooleanVar(value=False)
        self.full_check = ttk.Checkbutton(self.charset_frame, text=self.get_text("full_charset"),
                                          variable=self.use_full,
                                          command=self.toggle_charset_options)
        self.full_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # 子选项框架
        sub_charset_frame = ttk.Frame(self.charset_frame)
        sub_charset_frame.grid(row=1, column=0, sticky=tk.W, padx=(5, 0), pady=0)

        # 常用字符集复选框（合并中文和西文）
        self.use_common = tk.BooleanVar(value=True)
        self.common_check = ttk.Checkbutton(sub_charset_frame, text=self.get_text("common_charset"),
                                            variable=self.use_common)
        self.common_check.pack(anchor=tk.W, pady=2)

        # 自定义字符集复选框和文本框
        custom_frame = ttk.Frame(sub_charset_frame)
        custom_frame.pack(anchor=tk.W, pady=2)

        self.use_custom = tk.BooleanVar(value=False)
        self.custom_check = ttk.Checkbutton(custom_frame, text=self.get_text("custom_charset"),
                                            variable=self.use_custom)
        self.custom_check.pack(side=tk.LEFT)

        self.custom_charset = tk.StringVar()
        self.custom_entry = ttk.Entry(custom_frame, textvariable=self.custom_charset, width=30)
        self.custom_entry.pack(side=tk.LEFT, padx=(5, 0))
        # 设置默认占位符
        self.custom_entry.insert(0, self.get_text("custom_placeholder"))

        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=(15, 10))

        self.progress_label = ttk.Label(progress_frame, text=self.get_text("ready"))
        self.progress_label.pack(fill=tk.X, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=(10, 15))

        self.generate_button = ttk.Button(button_frame, text=self.get_text("generate_font"),
                                          command=self.start_generation, width=12)
        self.generate_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text=self.get_text("cancel"), command=self.cancel_generation,
                                        state=tk.DISABLED, width=8)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.exit_button = ttk.Button(button_frame, text=self.get_text("exit"), command=self.root.quit, width=8)
        self.exit_button.pack(side=tk.RIGHT, padx=5)

        # 作者信息栏
        author_frame = ttk.Frame(main_frame)
        author_frame.pack(fill=tk.X, padx=5, pady=(10, 0))

        self.author_label = ttk.Label(author_frame, text=self.get_text("author"), font=("Arial", 9),
                                      foreground="#666666")
        self.author_label.pack(pady=2)

        # 版权信息 - 添加超链接
        # 创建可点击的超链接标签
        website_frame = ttk.Frame(author_frame)
        website_frame.pack()

        self.website_label = ttk.Label(website_frame, text=self.get_text("website"),
                                       font=("Arial", 9), foreground="#666666")
        self.website_label.pack(side=tk.LEFT)

        # 超链接部分
        self.website_link = ttk.Label(website_frame, text=self.get_text("website_link"),
                                      font=("Arial", 9), foreground="blue", cursor="hand2")
        self.website_link.pack(side=tk.LEFT)
        self.website_link.bind("<Button-1>", self.open_website)
        self.website_link.bind("<Enter>", lambda e: self.website_link.config(foreground="red"))
        self.website_link.bind("<Leave>", lambda e: self.website_link.config(foreground="blue"))

        # 初始化字符集选项状态
        self.toggle_charset_options()

        # 启动GUI更新循环
        self.update_gui()

    def get_text(self, key):
        """获取当前语言的文本"""
        return LANGUAGE_RESOURCES[self.current_language][key]

    def toggle_language(self):
        """切换语言"""
        self.current_language = "en" if self.current_language == "zh" else "zh"
        self.update_ui_language()

    def update_ui_language(self):
        """更新UI语言"""
        # 更新语言按钮文本
        self.language_button.config(text=self.get_text("language_switch"))

        # 更新标题
        self.title_label.config(text=self.get_text("title"))

        # 更新输入框架
        self.input_frame.config(text=self.get_text("input_settings"))

        # 更新字体文件标签
        self.font_file_label.config(text=self.get_text("font_file"))

        # 更新浏览按钮
        self.browse_font_button.config(text=self.get_text("browse"))

        # 更新输出文件标签
        self.output_file_label.config(text=self.get_text("output_file"))

        # 更新输出浏览按钮
        self.browse_output_button.config(text=self.get_text("browse"))

        # 更新参数框架
        self.params_frame.config(text=self.get_text("generate_params"))

        # 更新字体大小标签
        self.font_size_label.config(text=self.get_text("font_size"))

        # 更新白色门限标签
        self.white_threshold_label.config(text=self.get_text("white_threshold"))

        # 更新黑色门限标签
        self.black_threshold_label.config(text=self.get_text("black_threshold"))

        # 更新字符集框架
        self.charset_frame.config(text=self.get_text("charset_selection"))

        # 更新描述标签
        self.desc_label1.config(text=self.get_text("font_size_desc"))
        self.desc_label2.config(text=self.get_text("white_threshold_desc"))
        self.desc_label3.config(text=self.get_text("black_threshold_desc"))

        # 更新全量字符集复选框
        self.full_check.config(text=self.get_text("full_charset"))

        # 更新常用字符集复选框
        self.common_check.config(text=self.get_text("common_charset"))

        # 更新自定义字符集复选框
        self.custom_check.config(text=self.get_text("custom_charset"))

        # 更新自定义字符集占位符
        current_text = self.custom_entry.get()
        if current_text in [LANGUAGE_RESOURCES["zh"]["custom_placeholder"],
                            LANGUAGE_RESOURCES["en"]["custom_placeholder"]]:
            self.custom_entry.delete(0, tk.END)
            self.custom_entry.insert(0, self.get_text("custom_placeholder"))

        # 更新按钮文本
        self.generate_button.config(text=self.get_text("generate_font"))
        self.cancel_button.config(text=self.get_text("cancel"))
        self.exit_button.config(text=self.get_text("exit"))

        # 更新进度标签
        if self.progress_label.cget("text") == LANGUAGE_RESOURCES["zh"]["ready"] or \
                self.progress_label.cget("text") == LANGUAGE_RESOURCES["en"]["ready"]:
            self.progress_label.config(text=self.get_text("ready"))

        # 更新作者信息
        self.author_label.config(text=self.get_text("author"))

        # 更新网站信息
        self.website_label.config(text=self.get_text("website"))
        self.website_link.config(text=self.get_text("website_link"))

    def toggle_charset_options(self):
        """切换字符集选项状态"""
        if self.use_full.get():
            # 勾选全量字符集时，禁用其他选项
            self.common_check.config(state=tk.DISABLED)
            self.custom_check.config(state=tk.DISABLED)
            self.custom_entry.config(state=tk.DISABLED)
        else:
            # 取消勾选全量字符集时，启用其他选项
            self.common_check.config(state=tk.NORMAL)
            self.custom_check.config(state=tk.NORMAL)
            self.custom_entry.config(state=tk.NORMAL)
            # 默认选中常用字符集
            self.use_common.set(True)

    def open_website(self, event):
        """打开网站"""
        webbrowser.open("https://edcbook.cn")

    def update_font_size(self, value):
        """更新字体大小显示为整数"""
        self.font_size.set(round(float(value)))
        self.font_size_value_label.config(text=str(self.font_size.get()))

    def update_white_threshold(self, value):
        """更新白色门限显示为整数"""
        self.white_threshold.set(round(float(value)))
        self.white_value_label.config(text=str(self.white_threshold.get()))

    def update_black_threshold(self, value):
        """更新黑色门限显示为整数"""
        self.black_threshold.set(round(float(value)))
        self.black_value_label.config(text=str(self.black_threshold.get()))

    def browse_font(self):
        """浏览字体文件"""
        file_path = filedialog.askopenfilename(
            title=self.get_text("font_file"),
            filetypes=[("字体文件", "*.ttf *.otf *.ttc"), ("所有文件", "*.*")]
        )
        if file_path:
            self.font_path.set(file_path)

    def browse_output(self):
        """选择输出文件"""
        file_path = filedialog.asksaveasfilename(
            title=self.get_text("output_file"),
            defaultextension=".bin",
            filetypes=[("二进制字体文件", "*.bin"), ("所有文件", "*.*")]
        )
        if file_path:
            self.output_path.set(file_path)

    def start_generation(self):
        """开始生成字体文件"""
        font_path = self.font_path.get()
        output_path = self.output_path.get()
        font_size = self.font_size.get()
        white_threshold = self.white_threshold.get()
        black_threshold = self.black_threshold.get()
        use_common = self.use_common.get()
        use_custom = self.use_custom.get()
        use_full = self.use_full.get()
        custom_charset = self.custom_charset.get()

        # 验证输入 - 使用公共参数
        if not font_path or not os.path.isfile(font_path):
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_font_file"))
            return

        if not output_path:
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_output_path"))
            return

        if not (FONT_CONFIG["MIN_FONT_SIZE"] <= font_size <= FONT_CONFIG["MAX_FONT_SIZE"]):
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_font_size"))
            return

        if not (FONT_CONFIG["MIN_WHITE_THRESHOLD"] <= white_threshold <= FONT_CONFIG["MAX_WHITE_THRESHOLD"]):
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_white_threshold"))
            return

        if not (FONT_CONFIG["MIN_BLACK_THRESHOLD"] <= black_threshold <= FONT_CONFIG["MAX_BLACK_THRESHOLD"]):
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_black_threshold"))
            return

        if black_threshold <= white_threshold:
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_threshold_order"))
            return

        if not (use_common or use_custom or use_full):
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_charset"))
            return

        if use_custom and not custom_charset.strip():
            messagebox.showerror(self.get_text("error_title"), self.get_text("error_custom_charset"))
            return

        # 重置状态
        self.progress_bar["value"] = 0
        self.progress_label.config(text=self.get_text("ready"))
        stop_event.clear()

        # 更新按钮状态
        self.generate_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        # 在单独线程中运行生成过程
        self.generation_thread = threading.Thread(
            target=generate_font_in_thread,
            args=(font_path, output_path, font_size, white_threshold, black_threshold,
                  use_common, use_custom, use_full, custom_charset),
            daemon=True
        )
        self.generation_thread.start()

    def cancel_generation(self):
        """取消生成过程"""
        stop_event.set()
        self.cancel_button.config(state=tk.DISABLED)
        self.progress_label.config(text=self.get_text("cancelled"))

    def update_gui(self):
        """定期更新GUI状态"""
        # 处理进度更新
        while not progress_queue.empty():
            item = progress_queue.get()
            if item[0] == "progress":
                if len(item) == 4:  # 有最大值和实际字符数
                    value, max_value, actual_count = item[1], item[2], item[3]
                    self.progress_bar["maximum"] = max_value
                    self.progress_bar["value"] = value
                    percentage = value / max_value * 100 if max_value > 0 else 0
                    self.progress_label.config(
                        text=self.get_text("generating").format(value, max_value, percentage, actual_count))
                elif len(item) == 3:  # 只有最大值
                    value, max_value = item[1], item[2]
                    self.progress_bar["maximum"] = max_value
                    self.progress_bar["value"] = value
                    percentage = value / max_value * 100 if max_value > 0 else 0
                    self.progress_label.config(
                        text=self.get_text("generating_no_count").format(value, max_value, percentage))

            elif item[0] == "complete":
                bin_path, total_chars, actual_chars = item[1], item[2], item[3]
                self.generate_button.config(state=tk.NORMAL)
                self.cancel_button.config(state=tk.DISABLED)
                messagebox.showinfo(self.get_text("complete_title"),
                                    self.get_text("complete_msg").format(total_chars, actual_chars, bin_path))

            elif item[0] == "error":
                error_msg = item[1]
                self.generate_button.config(state=tk.NORMAL)
                self.cancel_button.config(state=tk.DISABLED)
                messagebox.showerror(self.get_text("error_title"), error_msg)

        # 每100毫秒检查一次更新
        self.root.after(100, self.update_gui)


def main():
    """主函数"""
    root = tk.Tk()
    app = FontGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    # 确保在Windows上正确使用多进程
    multiprocessing.freeze_support()

    # 检查是否在PyInstaller打包环境中
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        multiprocessing.freeze_support()

    # 忽略libpng警告
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 减少TensorFlow日志（如果有）

    main()

#  pyinstaller --noconsole --onefile --add-binary "freetype.dll;." font_maker.py