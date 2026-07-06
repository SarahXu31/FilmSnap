<div align="center">

<img src="assets/screenshots/banner.png" alt="FilmSnap" width="720" />

# FilmSnap

**A tiny menu-bar film camera for macOS — 18 analog looks, one keystroke, straight to Photos.**

**一款轻量 macOS 菜单栏胶片相机：18 款胶片滤镜，一键拍照，自动保存到 Photos 相册。**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%2011%2B-blue.svg)](#requirements--环境要求)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow.svg)](#requirements--环境要求)
[![Release](https://img.shields.io/badge/Release-v1.0.0-orange.svg)](https://github.com/SarahXu31/FilmSnap/releases)

<img src="assets/screenshots/preview.png" alt="FilmSnap preview" width="640" />

</div>

---

## ✨ Features / 功能亮点

- 🎞️ **18 hand-tuned film emulations / 18 款手工调校胶片滤镜**  
  Kodak Portra 400, Fuji Velvia 50, Cinestill 800T, Lomo LC-A, Polaroid 600 and more.
- 📌 **Menu-bar first / 常驻菜单栏**  
  Keep it one click away without interrupting your workflow.
- ⏱️ **3-second countdown / 3 秒倒计时**  
  Press Space or click the shutter, then get ready for the shot.
- 💄 **Optional beauty smoothing / 可选轻美颜**  
  Off, low, medium, and high smoothing levels.
- 🖼️ **Auto-save to Apple Photos / 自动保存到系统相册**  
  Every shot is saved to both `~/Pictures/FilmSnap/` and the Photos app.
- 🛠️ **Zero Xcode required / 无需安装 Xcode**  
  Built with Python, rumps, PyObjC, and OpenCV. Xcode Command Line Tools are enough.

## 🚀 Install / 安装

### Option 1 — One-line script / 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/SarahXu31/FilmSnap/main/scripts/install.sh | bash
```

### Option 2 — DMG / 安装包

Download `FilmSnap-v1.0.0-arm64.dmg` from the [Releases](https://github.com/SarahXu31/FilmSnap/releases) page, then drag `FilmSnap.app` into `Applications`.

从 [Releases](https://github.com/SarahXu31/FilmSnap/releases) 下载 `FilmSnap-v1.0.0-arm64.dmg`，打开后把 `FilmSnap.app` 拖到「应用程序」即可。

### Option 3 — From source / 从源码运行

```bash
git clone https://github.com/SarahXu31/FilmSnap.git
cd FilmSnap
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/app.py
```

## 📸 How to use / 使用方法

1. Click the **🎞FilmSnap** icon in the macOS menu bar, then choose **Open camera preview**.  
   点击菜单栏里的 **🎞FilmSnap**，选择 **Open camera preview** 打开预览窗口。
2. Pick a film look from the dropdown at the bottom of the window.  
   在窗口底部的下拉列表里选择胶片滤镜。
3. Press **Space** or click the shutter button. A 3-second countdown starts.  
   按 **空格键** 或点击拍照按钮，进入 3 秒倒计时。
4. The photo is saved to both `~/Pictures/FilmSnap/` and Apple **Photos**.  
   照片会同时保存到 `~/Pictures/FilmSnap/` 和系统 **Photos / 照片** App。

## 🎞️ Film Emulations / 胶片滤镜

| Look / 滤镜 | Best for / 适合场景 |
|---|---|
| Original / 原色 | Clean preview, no color grading / 保留原始画面 |
| Kodak Portra 400 | Warm portraits, everyday life / 暖调人像、日常记录 |
| Fuji Velvia 50 | Vibrant landscapes / 高饱和风景 |
| Kodak T-Max 400 | Classic B&W / 经典黑白 |
| Faded / 复古褪色 | Low-saturation nostalgia / 低饱和复古氛围 |
| Warm Print / 暖调冲印 | Cozy indoor moments / 室内暖光、人像 |
| Teal & Orange / 青橙电影 | Cinematic portraits / 电影感人像 |
| Fuji Superia 400 | Casual street / 日常街拍 |
| Cinestill 800T | Night, neon, halation glow / 夜景、霓虹、光晕 |
| Lomo LC-A | High contrast, heavy vignette / 高对比、暗角 |
| Polaroid 600 | Instant-camera dreaminess / 拍立得质感 |
| Ilford HP5+ | Grainy B&W reportage / 颗粒黑白纪实 |
| Ektachrome E100 | Clean, punchy slide-film / 干净通透的反转片 |
| Sepia / 棕褐 | Old-photo tone / 老照片色调 |
| Cross Process / 交叉冲洗 | Bold color shifts / 强烈偏色和对比 |
| Japanese Clean / 日系清新 | Airy, low-saturation look / 清透低饱和 |
| Hong Kong Night / 港风夜色 | Cyan shadows, magenta highlights / 青色阴影、洋红高光 |
| Forest Muted / 森系文艺 | Green-yellow, quiet mood / 绿黄低饱和、安静氛围 |

## ⚙️ Requirements / 环境要求

- macOS 11 Big Sur or later / macOS 11 或更高版本
- Apple Silicon recommended / 推荐 Apple Silicon 芯片
- Intel Mac can work with a small launcher change / Intel Mac 需要移除启动脚本里的 `arch -arm64`
- Xcode Command Line Tools / 命令行工具：`xcode-select --install`
- System Python 3.9+ / 系统 Python 3.9+

## 🐛 Troubleshooting / 故障排查

<details>
<summary><b>Can't see the menu bar icon? / 看不到菜单栏图标？</b></summary>

macOS may hide menu-bar items when there is not enough space. Hold **⌘** and drag other menu-bar icons to make room, then look for **🎞FilmSnap**.

如果菜单栏空间不够，macOS 可能会把图标藏起来。可以按住 **⌘** 拖动其他菜单栏图标腾出空间，然后找 **🎞FilmSnap**。

You can also confirm whether it is running:

```bash
pgrep -fl "FilmSnap|python-app|app.py"
tail -n 80 ~/Library/Logs/FilmSnap.log
```
</details>

<details>
<summary><b>App is running but no window appears / App 在运行但没有窗口？</b></summary>

FilmSnap is a menu-bar app. If it was already running, `open -a FilmSnap` may only activate the existing process and may not reopen the preview window automatically.

FilmSnap 是菜单栏 App。如果它已经在后台运行，`open -a FilmSnap` 可能只会激活旧进程，不一定自动弹出预览窗口。

Restart it:

```bash
pkill -f "FilmSnap.app/Contents/Resources/python-app/Contents/MacOS/Python app.py"
open -a FilmSnap
```

Then click **🎞FilmSnap → Open camera preview** from the menu bar if needed.
</details>

<details>
<summary><b>Camera permission denied / 摄像头权限被拒绝？</b></summary>

Open **System Settings → Privacy & Security → Camera**, then enable FilmSnap.

打开 **系统设置 → 隐私与安全性 → 摄像头**，给 FilmSnap 打开权限。

If FilmSnap does not appear in the list, reset the permission and reopen the app:

```bash
tccutil reset Camera com.sarahxu31.filmsnap
open -a FilmSnap
```
</details>

<details>
<summary><b>Nothing appears in Photos / Photos 相册里没有照片？</b></summary>

Photos permission is requested on the first shot. If it was denied, reset it:

首次拍照时会请求 Photos 写入权限。如果之前点了拒绝，可以重置：

```bash
tccutil reset Photos com.sarahxu31.filmsnap
```

Photos are always saved to `~/Pictures/FilmSnap/` as a fallback.

即使 Photos 写入失败，照片也会先保存在 `~/Pictures/FilmSnap/`。
</details>

<details>
<summary><b>Intel Mac support / Intel Mac 支持</b></summary>

Open `Contents/MacOS/FilmSnap` inside the app bundle and remove `/usr/bin/arch -arm64` from the final launch command, then rebuild with `scripts/build_app.sh`.

如果是 Intel Mac，进入 App 包里的 `Contents/MacOS/FilmSnap`，删除最后启动命令中的 `/usr/bin/arch -arm64`，然后用 `scripts/build_app.sh` 重新构建。
</details>

## 🧹 Uninstall / 卸载

```bash
rm -rf /Applications/FilmSnap.app ~/FilmSnap-app ~/Library/Logs/FilmSnap.log
tccutil reset Camera com.sarahxu31.filmsnap
tccutil reset Photos com.sarahxu31.filmsnap
```

## 🤝 Contributing / 参与贡献

PRs are welcome, especially for new film emulations. Each look lives as a single function in [`src/filters.py`](src/filters.py). Please attach a before/after screenshot when adding a new look.

欢迎提交 PR，尤其是新增胶片滤镜。每个滤镜都在 [`src/filters.py`](src/filters.py) 里以单独函数实现。新增滤镜时建议附上前后对比截图。

## 📄 License / 许可证

MIT © 2026 [SarahXu31](https://github.com/SarahXu31)

---

<div align="center">
Built with ❤️ on a rainy afternoon.  
在一个下雨的下午做出来的。
</div>
