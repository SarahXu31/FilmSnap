#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
ARCH="arm64"
BUNDLE_ID="com.SarahXu31.filmsnap"
APP_NAME="FilmSnap.app"
INSTALLED_APP="/Applications/$APP_NAME"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build/dmg"
STAGE_DIR="$BUILD_DIR/FilmSnap"
WORK_APP="$STAGE_DIR/$APP_NAME"
DIST_DIR="$PROJECT_ROOT/dist"
DMG_PATH="$DIST_DIR/FilmSnap-v${VERSION}-${ARCH}.dmg"

if [[ ! -d "$INSTALLED_APP" ]]; then
  echo "未找到 $INSTALLED_APP。请先运行 scripts/install.sh 或 scripts/build_app.sh --install。" >&2
  exit 1
fi

SRC_DIR="$PROJECT_ROOT/src"
if [[ ! -d "$SRC_DIR" && -d "$HOME/FilmSnap" ]]; then
  SRC_DIR="$HOME/FilmSnap"
fi
if [[ ! -d "$SRC_DIR" ]]; then
  echo "未找到源码目录：$PROJECT_ROOT/src 或 $HOME/FilmSnap" >&2
  exit 1
fi

VENV_DIR="$PROJECT_ROOT/.venv"
if [[ ! -d "$VENV_DIR" && -d "$PROJECT_ROOT/venv" ]]; then
  VENV_DIR="$PROJECT_ROOT/venv"
fi
if [[ ! -d "$VENV_DIR" && -d "$HOME/FilmSnap/venv" ]]; then
  VENV_DIR="$HOME/FilmSnap/venv"
fi
if [[ ! -d "$VENV_DIR" ]]; then
  echo "未找到虚拟环境。请先创建 .venv，或确保 $HOME/FilmSnap/venv 存在。" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$STAGE_DIR" "$DIST_DIR"

printf 'Copying installed app...\n'
cp -R "$INSTALLED_APP" "$WORK_APP"

printf 'Embedding virtualenv: %s\n' "$VENV_DIR"
rm -rf "$WORK_APP/Contents/Resources/venv"
cp -R "$VENV_DIR" "$WORK_APP/Contents/Resources/venv"

printf 'Embedding source: %s\n' "$SRC_DIR"
rm -rf "$WORK_APP/Contents/Resources/src"
mkdir -p "$WORK_APP/Contents/Resources/src"
cp "$SRC_DIR/app.py" "$SRC_DIR/filters.py" "$SRC_DIR/photos_saver.py" "$WORK_APP/Contents/Resources/src/"

cat > "$WORK_APP/Contents/MacOS/FilmSnap" <<'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/Library/Logs/FilmSnap.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "==== $(date) FilmSnap launching ===="
  PY="$APP_DIR/Resources/venv/bin/python"
  SRC="$APP_DIR/Resources/src/app.py"
  if [[ ! -x "$PY" ]]; then
    echo "Missing Python executable: $PY"
    exit 1
  fi
  if [[ ! -f "$SRC" ]]; then
    echo "Missing app entry: $SRC"
    exit 1
  fi
  if [[ "$(uname -m)" == "arm64" ]]; then
    exec /usr/bin/arch -arm64 "$PY" "$SRC"
  else
    exec "$PY" "$SRC"
  fi
} >>"$LOG" 2>&1
LAUNCH
chmod +x "$WORK_APP/Contents/MacOS/FilmSnap"

# 保留 Contents/Python3 符号链接，不改动。
printf 'Ad-hoc signing app...\n'
codesign --force --deep --sign - --identifier "$BUNDLE_ID" "$WORK_APP"

cat > "$STAGE_DIR/README.txt" <<EOF
FilmSnap v$VERSION ($ARCH)

安装方式：
1. 将 FilmSnap.app 拖入 Applications 文件夹。
2. 运行：open -a FilmSnap
3. 首次启动时允许摄像头和 Photos 权限。

系统要求：macOS 11+、Xcode Command Line Tools、/usr/bin/python3 3.9+。

作者：SarahXu31 (SarahXu31)
项目：https://github.com/SarahXu31/FilmSnap
EOF

ln -s /Applications "$STAGE_DIR/Applications"
rm -f "$DMG_PATH"
printf 'Creating DMG: %s\n' "$DMG_PATH"
hdiutil create -volname "FilmSnap" -srcfolder "$STAGE_DIR" -ov -format UDZO "$DMG_PATH"

SHA256="$(shasum -a 256 "$DMG_PATH" | awk '{print $1}')"
SIZE="$(du -h "$DMG_PATH" | awk '{print $1}')"

echo "✅ DMG: $DMG_PATH"
echo "✅ Size: $SIZE"
echo "✅ SHA256: $SHA256"
