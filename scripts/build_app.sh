#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
BUNDLE_ID="com.xuxiyao.filmsnap"
INSTALL_TO_APPLICATIONS=0
FORCE_ARM64=1

for arg in "$@"; do
  case "$arg" in
    --install) INSTALL_TO_APPLICATIONS=1 ;;
    --no-arm64) FORCE_ARM64=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
APP="$DIST_DIR/FilmSnap.app"
VENV_DIR="$PROJECT_ROOT/.venv"
if [[ ! -d "$VENV_DIR" && -d "$PROJECT_ROOT/venv" ]]; then
  VENV_DIR="$PROJECT_ROOT/venv"
fi

if [[ ! -d "$PROJECT_ROOT/src" ]]; then
  echo "Missing src directory: $PROJECT_ROOT/src" >&2
  exit 1
fi
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing virtualenv. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>FilmSnap</string>
    <key>CFBundleDisplayName</key><string>FilmSnap</string>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key><string>$VERSION</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>FilmSnap</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>LSUIElement</key><true/>
    <key>LSArchitecturePriority</key><array><string>arm64</string></array>
    <key>LSRequiresNativeExecution</key><true/>
    <key>NSCameraUsageDescription</key>
    <string>FilmSnap 需要访问摄像头以拍摄胶片风照片。</string>
    <key>NSPhotoLibraryAddUsageDescription</key>
    <string>FilmSnap 需要写入 Photos 相册以自动保存拍摄成果。</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSHumanReadableCopyright</key>
    <string>© 2026 徐溪遥</string>
</dict>
</plist>
PLIST

if [[ -f "$PROJECT_ROOT/assets/icon.icns" ]]; then
  cp "$PROJECT_ROOT/assets/icon.icns" "$APP/Contents/Resources/AppIcon.icns"
elif [[ -f "/Applications/FilmSnap.app/Contents/Resources/AppIcon.icns" ]]; then
  cp "/Applications/FilmSnap.app/Contents/Resources/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
fi

printf 'Copying source...\n'
cp -R "$PROJECT_ROOT/src" "$APP/Contents/Resources/src"
printf 'Copying virtualenv...\n'
cp -R "$VENV_DIR" "$APP/Contents/Resources/venv"

CLT_PYTHON="/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Python3"
if [[ -e "$CLT_PYTHON" ]]; then
  ln -s "$CLT_PYTHON" "$APP/Contents/Python3"
fi

cat > "$APP/Contents/MacOS/FilmSnap" <<'LAUNCH'
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
chmod +x "$APP/Contents/MacOS/FilmSnap"

codesign --force --deep --sign - --identifier "$BUNDLE_ID" "$APP"

if [[ "$INSTALL_TO_APPLICATIONS" == "1" ]]; then
  rm -rf "/Applications/FilmSnap.app"
  cp -R "$APP" "/Applications/FilmSnap.app"
  codesign --force --deep --sign - --identifier "$BUNDLE_ID" "/Applications/FilmSnap.app"
fi

echo "✅ FilmSnap.app built: $APP"
if [[ "$INSTALL_TO_APPLICATIONS" == "1" ]]; then
  echo "✅ Installed to: /Applications/FilmSnap.app"
fi
