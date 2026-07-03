"""
FilmSnap 主入口：菜单栏 App + 相机预览窗口。
架构：
- rumps 提供菜单栏图标和菜单
- PyObjC + AppKit 提供原生 NSWindow 预览窗口
- OpenCV 抓帧，filters 处理，photos_saver 写入相册
"""
from __future__ import annotations

import os
import sys
import time
import datetime
import threading
from pathlib import Path

import numpy as np
import cv2

import rumps
import objc
from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSWindow,
    NSPanel,
    NSView,
    NSImageView,
    NSImage,
    NSButton,
    NSTextField,
    NSSlider,
    NSColor,
    NSBackingStoreBuffered,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSImageScaleProportionallyUpOrDown,
    NSMakeRect,
    NSFont,
    NSMenuItem,
    NSRunningApplication,
    NSApplicationActivateIgnoringOtherApps,
)
from Foundation import (
    NSObject,
    NSTimer,
    NSRunLoop,
    NSDefaultRunLoopMode,
    NSData,
    NSMutableData,
    NSMakeSize,
)
from Quartz import (
    CGColorSpaceCreateDeviceRGB,
    CGDataProviderCreateWithCFData,
    CGImageCreate,
    kCGImageAlphaNoneSkipLast,
    kCGRenderingIntentDefault,
    kCGBitmapByteOrderDefault,
)

from filters import FILTERS, FILTER_MAP, apply_beauty
from photos_saver import save_image_to_photos


APP_NAME = "FilmSnap"
SAVE_DIR = Path.home() / "Pictures" / "FilmSnap"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


# ---------- BGR ndarray -> NSImage ----------

def bgr_to_nsimage(bgr: np.ndarray) -> NSImage:
    """把 OpenCV BGR ndarray 转成 NSImage 用于 NSImageView 显示。"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.dstack([rgb, np.full(rgb.shape[:2], 255, dtype=np.uint8)])
    h, w = rgba.shape[:2]
    data = rgba.tobytes()
    ns_data = NSData.dataWithBytes_length_(data, len(data))
    provider = CGDataProviderCreateWithCFData(ns_data)
    color_space = CGColorSpaceCreateDeviceRGB()
    cg_image = CGImageCreate(
        w, h,
        8,              # bitsPerComponent
        32,             # bitsPerPixel
        w * 4,          # bytesPerRow
        color_space,
        kCGImageAlphaNoneSkipLast | kCGBitmapByteOrderDefault,
        provider,
        None,           # decode
        False,          # shouldInterpolate
        kCGRenderingIntentDefault,
    )
    ns_image = NSImage.alloc().initWithCGImage_size_(cg_image, NSMakeSize(w, h))
    return ns_image


# ---------- 相机窗口（NSWindow） ----------

class CameraWindowController(NSObject):
    """管理预览窗口 + 摄像头帧循环。"""

    def initWithApp_(self, app_ref):
        self = objc.super(CameraWindowController, self).init()
        if self is None:
            return None
        self._app = app_ref
        self._cap = None
        self._timer = None
        self._window = None
        self._image_view = None
        self._status_label = None
        self._filter_label = None
        self._beauty_slider = None
        self._counting_down = False
        self._countdown_end = 0
        return self

    # ---- Window life cycle ----

    def show(self):
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)
            self._activate_app()
            return

        # 创建窗口
        rect = NSMakeRect(200, 200, 720, 620)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
        )
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        win.setTitle_(f"{APP_NAME} · 相机预览")
        win.setReleasedWhenClosed_(False)
        win.setDelegate_(self)

        content = win.contentView()

        # 预览
        image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(20, 140, 680, 460))
        image_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        image_view.setWantsLayer_(True)
        content.addSubview_(image_view)
        self._image_view = image_view

        # 滤镜标签
        f_label = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 108, 680, 22))
        f_label.setStringValue_(f"当前滤镜：{self._app.current_filter_name}    美颜：{self._app.beauty_level_label()}")
        f_label.setBezeled_(False)
        f_label.setDrawsBackground_(False)
        f_label.setEditable_(False)
        f_label.setSelectable_(False)
        f_label.setFont_(NSFont.systemFontOfSize_(13))
        content.addSubview_(f_label)
        self._filter_label = f_label

        # 拍照按钮
        shoot_btn = NSButton.alloc().initWithFrame_(NSMakeRect(280, 40, 160, 44))
        shoot_btn.setTitle_("📸  拍照 (Space)")
        shoot_btn.setBezelStyle_(1)  # rounded
        shoot_btn.setTarget_(self)
        shoot_btn.setAction_("onShoot:")
        shoot_btn.setKeyEquivalent_(" ")
        content.addSubview_(shoot_btn)

        # 滤镜下拉列表（NSPopUpButton）
        popup = objc.lookUpClass("NSPopUpButton").alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, 45, 240, 34), False
        )
        for name, _fn in FILTERS:
            popup.addItemWithTitle_(name)
        popup.selectItemAtIndex_(self._app._filter_idx)
        popup.setTarget_(self)
        popup.setAction_("onFilterPicked:")
        content.addSubview_(popup)
        self._filter_popup = popup

        # 美颜滑竿
        beauty_label = NSTextField.alloc().initWithFrame_(NSMakeRect(470, 62, 60, 20))
        beauty_label.setStringValue_("美颜")
        beauty_label.setBezeled_(False)
        beauty_label.setDrawsBackground_(False)
        beauty_label.setEditable_(False)
        beauty_label.setFont_(NSFont.systemFontOfSize_(12))
        content.addSubview_(beauty_label)

        slider = NSSlider.alloc().initWithFrame_(NSMakeRect(530, 45, 170, 30))
        slider.setMinValue_(0.0)
        slider.setMaxValue_(1.0)
        slider.setDoubleValue_(self._app.beauty)
        slider.setTarget_(self)
        slider.setAction_("onBeautyChange:")
        content.addSubview_(slider)
        self._beauty_slider = slider

        # 状态
        status = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 8, 680, 20))
        status.setBezeled_(False)
        status.setDrawsBackground_(False)
        status.setEditable_(False)
        status.setSelectable_(False)
        status.setFont_(NSFont.systemFontOfSize_(11))
        status.setStringValue_("就绪。空格或点击「拍照」触发，图片会保存到 ~/Pictures/FilmSnap 并加入 Photos。")
        content.addSubview_(status)
        self._status_label = status

        self._window = win

        # 打开摄像头 + 启动帧循环
        self._open_camera()
        win.center()
        win.makeKeyAndOrderFront_(None)
        self._activate_app()

    def _activate_app(self):
        NSApp.activateIgnoringOtherApps_(True)

    def windowShouldClose_(self, sender):
        self.hide()
        return False

    def hide(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._window is not None:
            self._window.orderOut_(None)

    # ---- Camera ----

    def _draw_placeholder(self, text: str):
        """在预览区画中文错误提示，用 PIL 渲染避免乱码。"""
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        W, H = 720, 480
        pil = Image.new("RGB", (W, H), (32, 32, 32))
        d = ImageDraw.Draw(pil)
        d.rectangle([0, 0, W, 6], fill=(220, 60, 60))
        # 找一个支持中文的系统字体
        for fp in [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            try:
                font = ImageFont.truetype(fp, 26); break
            except Exception:
                font = None
        if font is None:
            font = ImageFont.load_default()
        lines = text.split("\n")
        total_h = len(lines) * 40
        y = (H - total_h) // 2
        for line in lines:
            try:
                bbox = d.textbbox((0, 0), line, font=font); tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(line) * 20
            x = (W - tw) // 2
            d.text((x, y), line, font=font, fill=(240, 240, 240))
            y += 40
        arr = np.array(pil)  # RGB
        # bgr_to_nsimage 接受 BGR，但内部做 BGR->RGB 转换，我们这里其实是 RGB→BGR→RGB。简单起见转一下：
        bgr = arr[..., ::-1].copy()
        if self._image_view is not None:
            self._image_view.setImage_(bgr_to_nsimage(bgr))

    def _on_perm_result(self, granted: bool):
        print(f"[FilmSnap] perm result: {granted}", flush=True)
        if granted:
            self.performSelectorOnMainThread_withObject_waitUntilDone_("retryOpenCamera:", None, False)
        else:
            self._draw_placeholder("摄像头未授权\n\n去 系统设置 → 隐私与安全性 → 摄像头\n开启开关后重新打开预览窗")

    def retryOpenCamera_(self, _):
        self._open_camera()

    def _open_camera(self):
        # 先通过 AVFoundation 检查/请求授权
        try:
            import AVFoundation
            status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                AVFoundation.AVMediaTypeVideo
            )
            print(f"[FilmSnap] camera auth status={status}", flush=True)
            if status == 0:  # notDetermined
                self._set_status("⏳ 正在请求摄像头权限，请点击弹窗中的「允许」…")
                self._draw_placeholder("正在请求摄像头权限\n请点弹窗中的 允许")
                AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                    AVFoundation.AVMediaTypeVideo, lambda ok: self._on_perm_result(bool(ok))
                )
                return
            if status == 2:  # denied
                self._draw_placeholder("摄像头被拒绝\n\n请到 系统设置 → 隐私与安全性\n→ 摄像头 中打开 Python / FilmSnap 开关")
                self._set_status("❌ 摄像头权限被拒。系统设置里打开开关后重新打开预览窗。")
                return
        except Exception as e:
            print("perm check failed:", e, flush=True)

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not cap.isOpened():
            self._draw_placeholder("摄像头无法打开\n\n可能未授权，或者没有摄像头设备")
            self._set_status("❌ 摄像头打不开。请检查授权 / 是否被其他 App 占用。")
            return
        self._cap = cap
        # 30 fps timer
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 30.0, self, "onTick:", None, True
        )
        # 确保在合适的 runloop mode 下
        NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSDefaultRunLoopMode)

    def onTick_(self, timer):
        if self._cap is None:
            return
        ok, frame = self._cap.read()
        if not ok:
            return
        # 水平翻转（自拍视角）
        frame = cv2.flip(frame, 1)
        # 处理帧
        processed = self._app.process_frame(frame)

        # 倒计时叠加
        if self._counting_down:
            remaining = self._countdown_end - time.time()
            if remaining <= 0:
                self._counting_down = False
                self._capture_now(processed)
            else:
                num = int(remaining) + 1
                self._draw_countdown(processed, num)

        ns_img = bgr_to_nsimage(processed)
        self._image_view.setImage_(ns_img)

    def _draw_countdown(self, img: np.ndarray, num: int):
        text = str(num)
        h, w = img.shape[:2]
        font = cv2.FONT_HERSHEY_DUPLEX
        scale = 6
        thickness = 12
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        x = (w - tw) // 2
        y = (h + th) // 2
        # 阴影
        cv2.putText(img, text, (x + 4, y + 4), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        cv2.putText(img, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # ---- Button actions ----

    def onShoot_(self, sender):
        if self._counting_down or self._cap is None:
            return
        self._counting_down = True
        self._countdown_end = time.time() + 3.05  # 3, 2, 1
        self._set_status("倒计时 3 秒…")

    def _capture_now(self, processed_frame: np.ndarray):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"FilmSnap_{ts}.jpg"
        filepath = SAVE_DIR / filename
        # 写文件（jpg 质量 95）
        cv2.imwrite(str(filepath), processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self._set_status(f"已保存本地：{filepath.name}，正在写入 Photos…")

        def _bg_save():
            ok, msg = save_image_to_photos(str(filepath))
            if ok:
                text = f"✅ 已保存到 Photos + {filepath}"
            else:
                text = f"⚠️ Photos 写入失败：{msg}（本地文件已保存）"
            # 回主线程更新
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "_updateStatus:", text, False
            )
            try:
                rumps.notification(APP_NAME, "拍摄完成", "已存入 Photos" if ok else "本地已保存，Photos 失败")
            except Exception:
                pass

        threading.Thread(target=_bg_save, daemon=True).start()

    def _updateStatus_(self, text):
        self._set_status(text)

    def onFilterPicked_(self, sender):
        idx = int(sender.indexOfSelectedItem())
        self._app._filter_idx = idx
        self._app._refresh_filter_marks()
        self._update_filter_label()

    def onNextFilter_(self, sender):
        self._app.cycle_filter()
        self._update_filter_label()

    def onBeautyChange_(self, sender):
        self._app.beauty = float(sender.doubleValue())
        self._update_filter_label()

    def _update_filter_label(self):
        if self._filter_label is not None:
            self._filter_label.setStringValue_(
                f"当前滤镜：{self._app.current_filter_name}    美颜：{self._app.beauty_level_label()}"
            )

    def _set_status(self, text: str):
        if self._status_label is not None:
            self._status_label.setStringValue_(text)


# ---------- rumps 菜单栏 App ----------

class FilmSnapApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="🎞FilmSnap", quit_button=None)
        import sys; print("[FilmSnap] menu bar item created", flush=True); sys.stdout.flush()
        self._filter_idx = 1  # 默认 Portra
        self.beauty = 0.4     # 默认美颜强度

        # 滤镜子菜单
        self._filter_items = []
        filters_menu = rumps.MenuItem("胶片滤镜")
        for i, (name, _fn) in enumerate(FILTERS):
            item = rumps.MenuItem(name, callback=self._make_filter_callback(i))
            self._filter_items.append(item)
            filters_menu.add(item)
        self._refresh_filter_marks()

        # 美颜子菜单
        beauty_menu = rumps.MenuItem("美颜强度")
        self._beauty_items = {}
        for label, val in [("关", 0.0), ("弱", 0.25), ("中", 0.5), ("强", 0.8)]:
            it = rumps.MenuItem(label, callback=self._make_beauty_callback(val))
            self._beauty_items[label] = (it, val)
            beauty_menu.add(it)
        self._refresh_beauty_marks()

        self.menu = [
            rumps.MenuItem("📸 打开相机预览", callback=self._on_open_camera),
            None,
            filters_menu,
            beauty_menu,
            None,
            rumps.MenuItem("打开保存目录", callback=self._on_open_folder),
            rumps.MenuItem("关于 FilmSnap", callback=self._on_about),
            None,
            rumps.MenuItem("退出", callback=self._on_quit),
        ]

        # 相机窗口控制器（延迟创建）
        self._cam_ctrl = None

    # ---- 属性 ----

    @property
    def current_filter_name(self) -> str:
        return FILTERS[self._filter_idx][0]

    @property
    def current_filter_fn(self):
        return FILTERS[self._filter_idx][1]

    def beauty_level_label(self) -> str:
        b = self.beauty
        if b <= 0.05: return "关"
        if b <= 0.3:  return "弱"
        if b <= 0.6:  return "中"
        return "强"

    # ---- 帧处理 ----

    def process_frame(self, bgr: np.ndarray) -> np.ndarray:
        out = apply_beauty(bgr, strength=self.beauty)
        out = self.current_filter_fn(out)
        return out

    def cycle_filter(self):
        self._filter_idx = (self._filter_idx + 1) % len(FILTERS)
        self._refresh_filter_marks()

    def _refresh_filter_marks(self):
        for i, it in enumerate(self._filter_items):
            it.state = 1 if i == self._filter_idx else 0

    def _refresh_beauty_marks(self):
        cur_label = self.beauty_level_label()
        for label, (it, _val) in self._beauty_items.items():
            it.state = 1 if label == cur_label else 0

    # ---- Menu callbacks ----

    def _make_filter_callback(self, idx: int):
        def cb(_sender):
            self._filter_idx = idx
            self._refresh_filter_marks()
            if self._cam_ctrl is not None:
                self._cam_ctrl._update_filter_label()
                # 同步下拉框
                popup = getattr(self._cam_ctrl, "_filter_popup", None)
                if popup is not None:
                    popup.selectItemAtIndex_(idx)
        return cb

    def _make_beauty_callback(self, val: float):
        def cb(_sender):
            self.beauty = val
            self._refresh_beauty_marks()
            if self._cam_ctrl is not None:
                self._cam_ctrl._update_filter_label()
                if self._cam_ctrl._beauty_slider is not None:
                    self._cam_ctrl._beauty_slider.setDoubleValue_(val)
        return cb

    def _on_open_camera(self, _sender):
        if self._cam_ctrl is None:
            self._cam_ctrl = CameraWindowController.alloc().initWithApp_(self)
        self._cam_ctrl.show()

    def _on_open_folder(self, _sender):
        os.system(f'open "{SAVE_DIR}"')

    def _on_about(self, _sender):
        rumps.alert(
            title=f"关于 {APP_NAME}",
            message=(
                f"{APP_NAME} · 菜单栏胶片相机\n\n"
                f"• 6 款胶片风滤镜（Portra / Velvia / T-Max / 褪色 / 暖调 / 青橙）\n"
                f"• 一键美颜（弱/中/强）\n"
                f"• 拍照自动写入 Photos 相册\n"
                f"• 图片同时保存到 {SAVE_DIR}\n\n"
                f"作者：为SarahXu31定制"
            ),
        )

    def _on_quit(self, _sender):
        if self._cam_ctrl is not None:
            self._cam_ctrl.hide()
        rumps.quit_application()


def main():
    # 让 App 同时出现在 Dock（Regular）+ 菜单栏
    NSApp_ = NSApplication.sharedApplication()
    NSApp_.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    app = FilmSnapApp()

    # 延迟 500ms 自动打开相机预览窗（等 rumps event loop 起来）
    from Foundation import NSTimer
    import objc

    class _AutoOpen(objc.lookUpClass('NSObject')):
        def open_(self, _t):
            try: app._on_open_camera(None)
            except Exception as e: print('auto-open failed:', e, flush=True)

    _obj = _AutoOpen.alloc().init()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.5, _obj, 'open:', None, False
    )
    print('[FilmSnap] main() started, auto-open scheduled', flush=True)
    app.run()


if __name__ == "__main__":
    main()
