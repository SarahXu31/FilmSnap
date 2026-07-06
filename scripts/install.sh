#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/SarahXu31/FilmSnap.git"
TARBALL_URL="https://github.com/SarahXu31/FilmSnap/archive/refs/heads/main.tar.gz"
INSTALL_DIR="$HOME/FilmSnap-app"
APP_PATH="/Applications/FilmSnap.app"
YES=0

for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES=1 ;;
    --dir=*) INSTALL_DIR="${arg#--dir=}" ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

log() { printf '\033[1;34m[FilmSnap]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[FilmSnap]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  err "FilmSnap 只能安装在 macOS。"
  exit 1
fi

MAC_MAJOR="$(sw_vers -productVersion | awk -F. '{print $1}')"
if [[ "$MAC_MAJOR" -lt 11 ]]; then
  err "需要 macOS 11 或更高版本，当前版本：$(sw_vers -productVersion)"
  exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
  err "未检测到 Xcode Command Line Tools。请先运行：xcode-select --install"
  exit 1
fi

PYTHON_BIN="/usr/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  err "未找到 /usr/bin/python3。"
  exit 1
fi

PYTHON_VERSION="$($PYTHON_BIN -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PYTHON_OK="$($PYTHON_BIN -c 'import sys; print(1 if sys.version_info >= (3, 9) else 0)')"
if [[ "$PYTHON_OK" != "1" ]]; then
  err "需要 Python 3.9+，当前 /usr/bin/python3 版本：$PYTHON_VERSION"
  exit 1
fi

log "安装目录：$INSTALL_DIR"
log "目标 App：$APP_PATH"
if [[ "$YES" != "1" ]]; then
  read -r -p "继续安装/更新 FilmSnap？[y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) log "已取消。"; exit 0 ;;
  esac
fi

rm -rf "$INSTALL_DIR"
mkdir -p "$(dirname "$INSTALL_DIR")"

if command -v git >/dev/null 2>&1; then
  log "正在从 GitHub 克隆源码..."
  git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
else
  log "未找到 git，改用 tarball 下载源码..."
  TMP_TGZ="$(mktemp -t filmsnap-main.XXXXXX).tar.gz"
  curl -fsSL "$TARBALL_URL" -o "$TMP_TGZ"
  TMP_DIR="$(mktemp -d -t filmsnap-src.XXXXXX)"
  tar -xzf "$TMP_TGZ" -C "$TMP_DIR"
  mv "$TMP_DIR"/FilmSnap-main "$INSTALL_DIR"
  rm -rf "$TMP_TGZ" "$TMP_DIR"
fi

cd "$INSTALL_DIR"
log "创建虚拟环境..."
"$PYTHON_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "构建 FilmSnap.app..."
chmod +x scripts/build_app.sh
scripts/build_app.sh --install

log "重新 ad-hoc 签名..."
codesign --force --deep --sign - --identifier com.sarahxu31.filmsnap "$APP_PATH"

log "安装完成。"
cat <<EOF

下一步：
  open -a FilmSnap

首次启动会弹出摄像头和 Photos 权限对话框，请点击允许。
日志位置：$HOME/Library/Logs/FilmSnap.log
EOF
