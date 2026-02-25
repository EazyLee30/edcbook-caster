#!/usr/bin/env bash
# EDCBook Caster 1.0 - 打包为 macOS .app 并生成 DMG
set -e
cd "$(dirname "$0")"
APP_NAME="EDCBook Caster 1.0"
DMG_NAME="EDCBook_Caster_1.0"
PY_SCRIPT="EDCBook_Caster_1.0.py"
ICON_PNG="assets/1.png"
ICON_ICNS="assets/icon.icns"

echo "=============================================="
echo "  EDCBook Caster 1.0 - 构建 DMG"
echo "=============================================="

# 0. 从 PNG 生成 .icns（有 1.png 时）
if [[ -f "$ICON_PNG" ]]; then
    echo "[0/3] 生成应用图标 (.icns)..."
    ICONSET="assets/EDCBookCaster.iconset"
    rm -rf "$ICONSET"
    mkdir -p "$ICONSET"
    sips -z 16 16   "$ICON_PNG" --out "$ICONSET/icon_16x16.png"
    sips -z 32 32   "$ICON_PNG" --out "$ICONSET/icon_16x16@2x.png"
    sips -z 32 32   "$ICON_PNG" --out "$ICONSET/icon_32x32.png"
    sips -z 64 64   "$ICON_PNG" --out "$ICONSET/icon_32x32@2x.png"
    sips -z 128 128 "$ICON_PNG" --out "$ICONSET/icon_128x128.png"
    sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_128x128@2x.png"
    sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_256x256.png"
    sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_256x256@2x.png"
    sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_512x512.png"
    sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET/icon_512x512@2x.png"
    iconutil -c icns "$ICONSET" -o "$ICON_ICNS"
    rm -rf "$ICONSET"
    echo "    已生成: $ICON_ICNS"
else
    echo "[0/3] 未找到 assets/1.png，跳过图标"
    ICON_ICNS=""
fi

# 1. 依赖
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[1/3] 安装 PyInstaller..."
    pip3 install pyinstaller
else
    echo "[1/3] PyInstaller 已安装"
fi

# 2. 用 PyInstaller 生成 .app（onedir 模式，避免 Dock 出现两个图标）
echo "[2/3] 正在打包应用 (PyInstaller onedir)..."
rm -rf build dist
PYI_ARGS=(
    --onedir
    --windowed
    --name "$APP_NAME"
    --clean
)
[[ -f "$ICON_ICNS" ]] && PYI_ARGS+=(--icon "$ICON_ICNS")
python3 -m PyInstaller "${PYI_ARGS[@]}" "$PY_SCRIPT"

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "错误: 未找到 $APP_PATH"
    exit 1
fi
echo "    已生成: $APP_PATH"

# 3. 制作 DMG（卷名、拖拽到“应用程序”的布局）
echo "[3/3] 正在生成 DMG..."
DMG_DIR="dmg_temp"
DMG_OUT="${DMG_NAME}.dmg"
rm -rf "$DMG_DIR" "$DMG_OUT"
mkdir -p "$DMG_DIR"
cp -R "$APP_PATH" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "$DMG_OUT"
rm -rf "$DMG_DIR"
echo "    已生成: $DMG_OUT"

echo ""
echo "=============================================="
echo "  完成。DMG 文件: $DMG_OUT"
echo "=============================================="
