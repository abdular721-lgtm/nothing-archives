#!/data/data/com.termux/files/usr/bin/sh
# Start location monitor on boot
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$HOME/bin:$PATH"

# Wait for WiFi to connect
sleep 25
nohup "$HOME/bin/voice-location-monitor" </dev/null >> "$HOME/logs/boot-location-monitor.log" 2>&1 &
disown
