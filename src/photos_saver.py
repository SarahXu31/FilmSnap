"""
将本地图片写入 Mac 系统「照片 (Photos)」App 相册。
使用 PhotosKit（PyObjC 绑定）。
需要 Info.plist 中声明 NSPhotoLibraryAddUsageDescription。
"""
from __future__ import annotations

import os
import threading

import objc
from Foundation import NSURL
from Photos import (
    PHPhotoLibrary,
    PHAssetCreationRequest,
    PHAuthorizationStatusAuthorized,
    PHAuthorizationStatusLimited,
    PHAccessLevelAddOnly,
)


def _authorize_sync(timeout: float = 30.0) -> int:
    """请求 Photos 添加权限，同步等待用户响应。"""
    done = threading.Event()
    status_holder = {}

    def _handler(status):
        status_holder["status"] = int(status)
        done.set()

    PHPhotoLibrary.requestAuthorizationForAccessLevel_handler_(
        PHAccessLevelAddOnly, _handler
    )
    done.wait(timeout=timeout)
    return status_holder.get("status", -1)


def save_image_to_photos(file_path: str, timeout: float = 30.0) -> tuple[bool, str]:
    """
    把磁盘上的图片文件加入 Photos App 相册。
    返回 (成功?, 消息)。
    """
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"

    status = _authorize_sync()
    if status not in (PHAuthorizationStatusAuthorized, PHAuthorizationStatusLimited):
        return False, "未获得 Photos 权限（可在系统设置→隐私→照片中开启）"

    url = NSURL.fileURLWithPath_(file_path)
    done = threading.Event()
    result = {"ok": False, "err": None}

    def _changes():
        req = PHAssetCreationRequest.creationRequestForAssetFromImageAtFileURL_(url)
        if req is None:
            result["err"] = "PHAssetCreationRequest 创建失败"

    def _completion(success, error):
        result["ok"] = bool(success)
        if error is not None and not success:
            result["err"] = str(error.localizedDescription())
        done.set()

    PHPhotoLibrary.sharedPhotoLibrary().performChanges_completionHandler_(
        _changes, _completion
    )
    done.wait(timeout=timeout)

    if result["ok"]:
        return True, "已保存到 Photos"
    return False, result["err"] or "未知错误"
