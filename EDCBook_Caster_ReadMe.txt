互动投屏工具使用说明：
1. 需要配合EDC Book设备使用，设备和PC需在同一局域网内。
2. 启动PC端软件，调整截图框大小（横屏竖屏均可）。
3. 确认PC端软件左下的地址，如果是edcbook_cast.local，可直接在设备上启动互动投屏功能；如果是IP（说明mDNS启动失败），需要在在线配置里配置WS的地址和端口后使用。
4. 投屏启动成功后，可以通过edcbook反向操作PC，长按屏幕可退出投屏。

两种使用模式：
1. 懒人模式
直接运行.exe即可使用。
2. 高手模式
如果工具有问题（个人开发，未做兼容性测试）跑不起来，工具的python源码已提供，自己研究修改即可。
依赖安装：pip install numpy pillow mss pynput websockets zeroconf
运行命令：python EDCBook_Caster_1.0.py
生成命令：pyinstaller --onefile --windowed --name="EDCBook_Caster_1.0" EDCBook_Caster_1.0.py

祝大家玩得愉快。

Interactive Screen Casting Tool Usage:
1. Requires an EDC Book device. The device and PC must be on the same local network.
2. Launch the PC software and adjust the screenshot frame size (landscape or portrait).
3. Check the address at the bottom-left of the PC software. If it shows edcbook_cast.local, you can directly start interactive casting on the device; if it shows an IP (meaning mDNS failed), you need to configure the WS address and port in online configuration first.
4. After casting starts successfully, you can reverse-control the PC via edcbook; long-press the screen to exit casting.

Two Usage Modes:
1. Lazy Mode
Simply run the .exe to use.
2. Expert Mode
If the tool doesn't work (developed individually and not compatibility-tested), the Python source code of the tool is provided for you to study and modify as needed.
Install dependencies: pip install numpy pillow mss pynput websockets zeroconf
Run command: python EDCBook_Caster_1.0.py
Build command: pyinstaller --onefile --windowed --name="EDCBook_Caster_1.0" EDCBook_Caster_1.0.py

Enjoy!
