#!/bin/bash
# Creates clickable Mac app for desktop

APP_NAME="Executive Assistant"
APP_DIR="$HOME/Desktop/$APP_NAME.app"

mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create launcher script
cat > "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHEOF'
#!/bin/bash
cd ~/executive-assistant
source ~/.executive-assistant-env/bin/activate

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Start server
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 &
sleep 3

# Open browser
open http://localhost:8000

# Keep app running
wait
LAUNCHEOF

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleName</key>
    <string>Executive Assistant</string>
    <key>CFBundleDisplayName</key>
    <string>Executive Assistant</string>
    <key>CFBundleIdentifier</key>
    <string>com.executiveassistant</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
PLISTEOF

echo "✅ Created: $APP_DIR"
echo "   Double-click to launch!"
