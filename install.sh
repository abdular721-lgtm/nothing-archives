#!/data/data/com.termux/files/usr/bin/bash
# Nothing Archives — one-command install
# Run: bash <(curl -sL https://raw.githubusercontent.com/abdular721-lgtm/nothing-archives/main/install.sh)
#
# Requirements:
#   - Nothing Phone 2a (or any rooted Android with Termux)
#   - Termux (from F-Droid, NOT Play Store)
#   - Termux:API (from F-Droid)
#   - Magisk root

set -e

echo "=========================================="
echo "  Nothing Archives — Voice Control Setup"
echo "=========================================="
echo ""
echo "Requirements: rooted Nothing Phone, Termux (F-Droid), Termux:API (F-Droid)"
echo ""

# ─── 1. Install Termux packages ──────────────────────────
echo "[1/8] Installing packages..."
pkg update -y
pkg install -y python ffmpeg openssh termux-api git nodejs cmake make

# ─── 2. Clone repo ───────────────────────────────────────
echo ""
echo "[2/8] Cloning nothing-archives..."
mkdir -p ~/projects
if [ -d ~/projects/nothing-archives ]; then
    echo "  Repo exists — pulling latest..."
    cd ~/projects/nothing-archives
    git pull
else
    cd ~/projects
    git clone https://github.com/abdular721-lgtm/nothing-archives.git
    cd nothing-archives
fi

# ─── 3. Install scripts ─────────────────────────────────
echo ""
echo "[3/8] Installing scripts to ~/bin/..."
mkdir -p ~/bin
cp scripts/* ~/bin/
chmod +x ~/bin/voice* ~/bin/hey-nothing* ~/bin/run-voice ~/bin/whisper-listen
chmod +x ~/bin/parse_alarm.py ~/bin/restore-reminders.py 2>/dev/null || true

# ─── 4. PATH setup ──────────────────────────────────────
echo ""
echo "[4/8] Configuring PATH..."
if ! grep -q 'export PATH="$HOME/bin:$PATH"' ~/.bashrc 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
    echo "  Added ~/bin to PATH in .bashrc"
else
    echo "  PATH already configured"
fi

# ─── 5. Build whisper.cpp ────────────────────────────────
echo ""
echo "[5/8] Building whisper.cpp (speech recognition engine)..."
if [ -f ~/whisper.cpp/build/bin/whisper-cli ]; then
    echo "  whisper.cpp already built — skipping"
else
    cd ~
    if [ -d ~/whisper.cpp ]; then
        echo "  Source exists — pulling latest..."
        cd whisper.cpp && git pull
    else
        git clone https://github.com/ggerganov/whisper.cpp
        cd whisper.cpp
    fi
    cmake -B build
    cmake --build build -j$(nproc) --config Release
    echo "  Build complete"
fi

# Download models
echo ""
echo "[6/8] Downloading whisper models..."
cd ~/whisper.cpp
if [ -f models/ggml-base.en.bin ]; then
    echo "  base.en model already downloaded"
else
    echo "  Downloading base.en (142MB — main recognition model)..."
    bash ./models/download-ggml-model.sh base.en
fi

if [ -f models/ggml-tiny.en.bin ]; then
    echo "  tiny.en model already downloaded"
else
    echo "  Downloading tiny.en (75MB — fast wake word model)..."
    bash ./models/download-ggml-model.sh tiny.en
fi

# ─── 7. Create directories and configs ──────────────────
echo ""
echo "[7/8] Creating directories and default configs..."
mkdir -p ~/notes ~/logs ~/.shortcuts

# Default config files (don't overwrite if they exist)
if [ ! -f ~/.hey-nothing-config ]; then
    cat > ~/.hey-nothing-config << 'CONF'
POLL_INTERVAL=1
POLL_INTERVAL_SCREEN_OFF=8
QUIET_POLL_INTERVAL=30
QUIET_HOURS_START=0
QUIET_HOURS_END=6
ENERGY_THRESHOLD=500
SCREEN_AWARE=true
CONF
    echo "  Created ~/.hey-nothing-config"
fi

if [ ! -f ~/.smart-home-config ]; then
    cat > ~/.smart-home-config << 'CONF'
# Smart Home Config — edit with your hub details
#HOME_ASSISTANT_URL=http://192.168.1.X:8123
#HOME_ASSISTANT_TOKEN=your_long_lived_access_token_here
#N8N_WEBHOOK_URL=http://your-vps:5678/webhook/voice-home
CONF
    echo "  Created ~/.smart-home-config"
fi

# Widget shortcuts
echo "  Creating widget shortcuts..."
for script in voice voice-alarm voice-open voice-youtube voice-note voice-screenshot voice-toggle voice-weather voice-briefing voice-macro voice-music voice-home; do
    ln -sf ~/bin/$script ~/.shortcuts/$script 2>/dev/null || true
done

# ─── 8. Termux:Boot setup ───────────────────────────────
echo ""
echo "[8/8] Checking Termux:Boot..."
BOOT_DIR="$HOME/.termux/boot"
if [ -d "$BOOT_DIR" ] || [ -d /data/data/com.termux.boot ]; then
    mkdir -p "$BOOT_DIR"
    # Create boot script for wake word daemon
    cat > "$BOOT_DIR/05-hey-nothing.sh" << 'BOOT'
#!/data/data/com.termux/files/usr/bin/sh
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$HOME/bin:$PATH"
sleep 10
hey-nothing-ctl start >> "$HOME/logs/boot-hey-nothing.log" 2>&1
BOOT
    chmod +x "$BOOT_DIR/05-hey-nothing.sh"
    echo "  Termux:Boot configured — wake word starts on boot"
else
    echo "  Termux:Boot not found — install from F-Droid for auto-start on reboot"
fi

# ─── Done ────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  Installation complete!"
echo "=========================================="
echo ""
echo "Manual steps required:"
echo "  1. Android Settings > Apps > Termux:API > Permissions > enable Microphone"
echo "  2. Android Settings > Notifications > Notification access > enable Termux:API"
echo "  3. Grant root access to Termux in Magisk"
echo "  4. Install Termux:Widget from F-Droid and add widget to home screen"
echo "  5. Optional: Install Termux:Boot from F-Droid for wake word auto-start"
echo ""
echo "Quick test:"
echo "  source ~/.bashrc"
echo "  voice-alarm              # set an alarm by voice"
echo "  voice                    # unified voice router"
echo "  hey-nothing-ctl start    # start wake word detection"
echo "  hey-nothing-ctl status   # check daemon status"
echo ""
