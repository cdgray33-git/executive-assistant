#!/bin/bash
# Create Reinstall Jarvis desktop icon for macOS

APP_NAME="Reinstall Jarvis"
APP_DIR="$HOME/Desktop/$APP_NAME.app"
SCRIPT_PATH="$HOME/executive-assistant/scripts/reinstall_jarvis.sh"

echo "Creating $APP_NAME desktop icon..."

# Create .app bundle structure
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create executable wrapper
cat > "$APP_DIR/Contents/MacOS/$APP_NAME" << 'WRAPPER_EOF'
#!/bin/bash
osascript -e 'tell application "Terminal" to do script "cd ~/executive-assistant && ./scripts/reinstall_jarvis.sh; exec bash"'
WRAPPER_EOF

chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Reinstall Jarvis</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.executiveassistant.reinstall</string>
    <key>CFBundleName</key>
    <string>Reinstall Jarvis</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>
PLIST_EOF

echo "✅ Created desktop icon: $APP_DIR"
echo "🔄 Icon will appear on Mac desktop after installation"
