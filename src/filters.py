"""
FilmSnap 胶片滤镜库
用 numpy 曲线映射模拟六种经典胶片色彩风格 + 一档美颜。
所有输入输出都是 uint8 BGR ndarray（OpenCV 格式）。
"""
from __future__ import annotations

import numpy as np
import cv2


# ---------- 通用工具 ----------

def _apply_curve(channel: np.ndarray, curve: np.ndarray) -> np.ndarray:
    """按 256 元素 LUT 做单通道映射。"""
    return cv2.LUT(channel, curve.astype(np.uint8))


def _build_curve(points: list[tuple[int, int]]) -> np.ndarray:
    """
    从若干 (x, y) 锚点插值出 0-255 的曲线。
    points 按 x 递增排列，首尾建议包含 0 和 255。
    """
    xs = np.array([p[0] for p in points], dtype=np.float32)
    ys = np.array([p[1] for p in points], dtype=np.float32)
    all_x = np.arange(256, dtype=np.float32)
    curve = np.interp(all_x, xs, ys)
    return np.clip(curve, 0, 255).astype(np.uint8)


def _split_bgr(img: np.ndarray):
    b, g, r = cv2.split(img)
    return b, g, r


def _merge_bgr(b, g, r) -> np.ndarray:
    return cv2.merge([b, g, r])


def _blend(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    """a*(1-alpha) + b*alpha"""
    return cv2.addWeighted(a, 1.0 - alpha, b, alpha, 0)


def _add_grain(img: np.ndarray, strength: float = 0.03) -> np.ndarray:
    """加胶片颗粒。strength 相对 0-1。"""
    if strength <= 0:
        return img
    noise = np.random.normal(0, 255 * strength, img.shape).astype(np.int16)
    out = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return out


def _vignette(img: np.ndarray, strength: float = 0.35) -> np.ndarray:
    """径向暗角。strength 越大暗角越重。"""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    r = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
    mask = 1 - np.clip(r * strength, 0, 1) * 0.55
    mask = mask.astype(np.float32)[..., None]
    out = np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)
    return out


# ---------- 六款胶片滤镜 ----------

def filter_original(img: np.ndarray) -> np.ndarray:
    """原色，不作处理。"""
    return img


def filter_portra(img: np.ndarray) -> np.ndarray:
    """柯达 Portra 400：暖调、皮肤讨喜、S 型对比。"""
    # 红：中间提亮，高光轻收
    curve_r = _build_curve([(0, 0), (64, 78), (128, 148), (200, 216), (255, 252)])
    # 绿：中间轻抬
    curve_g = _build_curve([(0, 0), (64, 66), (128, 132), (192, 196), (255, 252)])
    # 蓝：整体压暗，制造暖调
    curve_b = _build_curve([(0, 0), (64, 56), (128, 118), (192, 180), (255, 240)])
    b, g, r = _split_bgr(img)
    b = _apply_curve(b, curve_b)
    g = _apply_curve(g, curve_g)
    r = _apply_curve(r, curve_r)
    out = _merge_bgr(b, g, r)
    out = _add_grain(out, 0.025)
    out = _vignette(out, 0.30)
    return out


def filter_velvia(img: np.ndarray) -> np.ndarray:
    """富士 Velvia 50：高饱和、通透、风景神器。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)  # 饱和度
    hsv[..., 2] = np.clip(hsv[..., 2] * 1.05, 0, 255)  # 明度
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    # 加对比
    curve = _build_curve([(0, 0), (48, 32), (128, 132), (208, 224), (255, 255)])
    b, g, r = _split_bgr(out)
    b = _apply_curve(b, curve)
    g = _apply_curve(g, curve)
    r = _apply_curve(r, curve)
    out = _merge_bgr(b, g, r)
    return out


def filter_bw_tmax(img: np.ndarray) -> np.ndarray:
    """柯达 T-Max 400 黑白：中灰调、颗粒感、经典。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 黑白 S 曲线
    curve = _build_curve([(0, 0), (40, 24), (128, 138), (215, 232), (255, 255)])
    gray = _apply_curve(gray, curve)
    out = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    out = _add_grain(out, 0.045)
    out = _vignette(out, 0.35)
    return out


def filter_faded(img: np.ndarray) -> np.ndarray:
    """复古褪色：低饱和、抬黑位、雾感。"""
    b, g, r = _split_bgr(img)
    # 抬黑位（阴影不到 0）
    curve = _build_curve([(0, 22), (64, 78), (128, 138), (192, 200), (255, 240)])
    b = _apply_curve(b, curve)
    g = _apply_curve(g, curve)
    r = _apply_curve(r, curve)
    out = _merge_bgr(b, g, r)
    # 降饱和
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 0.75, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    out = _add_grain(out, 0.020)
    out = _vignette(out, 0.25)
    return out


def filter_warmprint(img: np.ndarray) -> np.ndarray:
    """暖调冲印：奶油色高光、微紫阴影。"""
    b, g, r = _split_bgr(img)
    # 红：亮部加强
    r = _apply_curve(r, _build_curve([(0, 8), (64, 78), (128, 148), (200, 220), (255, 254)]))
    # 绿：正常带点抬亮
    g = _apply_curve(g, _build_curve([(0, 6), (64, 68), (128, 130), (192, 194), (255, 250)]))
    # 蓝：阴影偏暖，高光留一点
    b = _apply_curve(b, _build_curve([(0, 12), (64, 52), (128, 108), (192, 168), (255, 235)]))
    out = _merge_bgr(b, g, r)
    out = _add_grain(out, 0.020)
    return out


def filter_teal_orange(img: np.ndarray) -> np.ndarray:
    """青橙调：电影感、高光偏橙、阴影偏青。"""
    b, g, r = _split_bgr(img)
    # 高光偏橙：R 亮部提，B 亮部压
    r = _apply_curve(r, _build_curve([(0, 0), (128, 130), (200, 218), (255, 254)]))
    b = _apply_curve(b, _build_curve([(0, 22), (64, 72), (128, 122), (200, 178), (255, 220)]))
    g = _apply_curve(g, _build_curve([(0, 12), (128, 128), (255, 246)]))
    out = _merge_bgr(b, g, r)
    # 加一点对比
    curve = _build_curve([(0, 0), (48, 36), (128, 132), (208, 220), (255, 255)])
    b2, g2, r2 = _split_bgr(out)
    out = _merge_bgr(_apply_curve(b2, curve), _apply_curve(g2, curve), _apply_curve(r2, curve))
    out = _vignette(out, 0.28)
    return out


# ---------- 美颜 ----------

def apply_beauty(img: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """
    磨皮 + 微亮 + 微暖。strength ∈ [0, 1]。
    - 双边滤波保留边缘做磨皮
    - 轻微亮度 & 暖化
    """
    if strength <= 0:
        return img
    # 双边滤波磨皮
    d = int(5 + strength * 6)
    smooth = cv2.bilateralFilter(img, d=d, sigmaColor=45, sigmaSpace=45)
    out = _blend(img, smooth, alpha=0.75)
    # 亮度 & 暖化
    out = out.astype(np.float32)
    out[..., 2] = np.clip(out[..., 2] * (1 + 0.04 * strength), 0, 255)  # R+
    out[..., 0] = np.clip(out[..., 0] * (1 - 0.03 * strength), 0, 255)  # B-
    out += 6 * strength
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out


# ---------- 滤镜注册表 ----------

FILTERS = [
    ("原色 Original", filter_original),
    ("柯达 Portra 400", filter_portra),
    ("富士 Velvia 50", filter_velvia),
    ("黑白 T-Max 400", filter_bw_tmax),
    ("复古褪色 Faded", filter_faded),
    ("暖调冲印 Warm Print", filter_warmprint),
    ("青橙电影 Teal & Orange", filter_teal_orange),
]

FILTER_MAP = {name: fn for name, fn in FILTERS}


# ==================== 更多胶片滤镜（V2 补充） ====================

def filter_superia(img: np.ndarray) -> np.ndarray:
    """富士 Superia 400：绿调、生活感、饱和适中。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 0), (64, 68), (128, 132), (200, 210), (255, 250)]))
    g = _apply_curve(g, _build_curve([(0, 0), (64, 74), (128, 142), (192, 202), (255, 254)]))
    b = _apply_curve(b, _build_curve([(0, 0), (64, 62), (128, 124), (192, 188), (255, 245)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.12, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _add_grain(out, 0.022)


def filter_cinestill(img: np.ndarray) -> np.ndarray:
    """Cinestill 800T：电影卷、青蓝阴影、暖高光、光晕感。"""
    b, g, r = _split_bgr(img)
    # 阴影青蓝、高光暖橙
    r = _apply_curve(r, _build_curve([(0, 8), (48, 40), (128, 138), (200, 224), (255, 252)]))
    g = _apply_curve(g, _build_curve([(0, 12), (48, 44), (128, 128), (200, 200), (255, 240)]))
    b = _apply_curve(b, _build_curve([(0, 28), (48, 72), (128, 122), (200, 172), (255, 210)]))
    out = _merge_bgr(b, g, r)
    # 高光光晕（对红通道做轻微模糊 + 叠加）
    r_ch = out[..., 2]
    highlight = np.where(r_ch > 200, r_ch, 0).astype(np.uint8)
    glow = cv2.GaussianBlur(highlight, (0, 0), 8)
    out[..., 2] = np.clip(out[..., 2].astype(np.int16) + (glow * 0.3).astype(np.int16), 0, 255).astype(np.uint8)
    return _add_grain(out, 0.028)


def filter_lomo(img: np.ndarray) -> np.ndarray:
    """Lomo LC-A：高对比、浓暗角、色偏。"""
    b, g, r = _split_bgr(img)
    curve = _build_curve([(0, 0), (32, 12), (128, 138), (220, 240), (255, 255)])
    r = _apply_curve(r, curve); g = _apply_curve(g, curve); b = _apply_curve(b, curve)
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    out = _vignette(out, 0.65)
    return out


def filter_polaroid(img: np.ndarray) -> np.ndarray:
    """Polaroid 600：拍立得，偏黄、软对比、稍雾。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 24), (64, 90), (128, 156), (200, 216), (255, 250)]))
    g = _apply_curve(g, _build_curve([(0, 20), (64, 84), (128, 148), (200, 208), (255, 246)]))
    b = _apply_curve(b, _build_curve([(0, 18), (64, 70), (128, 118), (200, 172), (255, 220)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 0.88, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _add_grain(out, 0.03)


def filter_ilford_hp5(img: np.ndarray) -> np.ndarray:
    """Ilford HP5+ 黑白：高对比、深黑、细颗粒。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    curve = _build_curve([(0, 0), (32, 12), (128, 132), (220, 244), (255, 255)])
    gray = _apply_curve(gray, curve)
    out = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return _add_grain(out, 0.055)


def filter_ektachrome(img: np.ndarray) -> np.ndarray:
    """Ektachrome E100 反转片：清冷蓝绿、明快通透。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 0), (64, 60), (128, 124), (200, 204), (255, 250)]))
    g = _apply_curve(g, _build_curve([(0, 0), (64, 72), (128, 140), (200, 214), (255, 254)]))
    b = _apply_curve(b, _build_curve([(0, 0), (64, 76), (128, 142), (200, 216), (255, 255)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.10, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def filter_sepia(img: np.ndarray) -> np.ndarray:
    """Sepia 棕褐怀旧：老照片风。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    r = np.clip(gray * 1.07 + 20, 0, 255)
    g = np.clip(gray * 0.92 + 10, 0, 255)
    b = np.clip(gray * 0.72, 0, 255)
    out = cv2.merge([b, g, r]).astype(np.uint8)
    return _vignette(out, 0.30)


def filter_cross_process(img: np.ndarray) -> np.ndarray:
    """Cross Process 交叉冲洗：高对比、魔幻色偏。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 0), (48, 20), (128, 148), (200, 232), (255, 255)]))
    g = _apply_curve(g, _build_curve([(0, 8), (48, 40), (128, 128), (200, 208), (255, 250)]))
    b = _apply_curve(b, _build_curve([(0, 24), (48, 76), (128, 122), (200, 172), (255, 218)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def filter_japan_clean(img: np.ndarray) -> np.ndarray:
    """日系清新：高光溢出、低饱和、粉绿倾向。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 12), (64, 82), (128, 150), (200, 224), (255, 255)]))
    g = _apply_curve(g, _build_curve([(0, 14), (64, 84), (128, 152), (200, 224), (255, 255)]))
    b = _apply_curve(b, _build_curve([(0, 16), (64, 82), (128, 148), (200, 218), (255, 250)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 0.82, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def filter_hongkong_night(img: np.ndarray) -> np.ndarray:
    """港风夜色：青蓝阴影、霓虹粉红高光。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 4), (48, 36), (128, 130), (200, 214), (255, 250)]))
    g = _apply_curve(g, _build_curve([(0, 6), (48, 30), (128, 118), (200, 196), (255, 232)]))
    b = _apply_curve(b, _build_curve([(0, 20), (48, 68), (128, 130), (200, 194), (255, 236)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.20, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _vignette(out, 0.32)


def filter_forest(img: np.ndarray) -> np.ndarray:
    """森系文艺：绿黄暖调、低饱和、静谧。"""
    b, g, r = _split_bgr(img)
    r = _apply_curve(r, _build_curve([(0, 8), (64, 74), (128, 138), (200, 208), (255, 246)]))
    g = _apply_curve(g, _build_curve([(0, 10), (64, 78), (128, 142), (200, 210), (255, 248)]))
    b = _apply_curve(b, _build_curve([(0, 8), (64, 62), (128, 116), (200, 172), (255, 218)]))
    out = _merge_bgr(b, g, r)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 0.78, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


# 追加到 FILTERS 注册表
FILTERS.extend([
    ("富士 Superia 400", filter_superia),
    ("Cinestill 800T", filter_cinestill),
    ("Lomo LC-A", filter_lomo),
    ("Polaroid 600", filter_polaroid),
    ("Ilford HP5+ 黑白", filter_ilford_hp5),
    ("Ektachrome E100", filter_ektachrome),
    ("棕褐 Sepia", filter_sepia),
    ("交叉冲洗", filter_cross_process),
    ("日系清新", filter_japan_clean),
    ("港风夜色", filter_hongkong_night),
    ("森系文艺", filter_forest),
])
FILTER_MAP = {name: fn for name, fn in FILTERS}
