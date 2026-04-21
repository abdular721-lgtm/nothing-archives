#!/data/data/com.termux/files/usr/bin/sh
# Start Hey Nothing wake word daemon on boot
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$HOME/bin:$PATH"

# Wait for system to settle (audio, wifi, etc.)
sleep 10
hey-nothing-ctl start >> "$HOME/logs/boot-hey-nothing.log" 2>&1
