#!/data/data/com.termux/files/usr/bin/sh
# Start assistant watchdog on boot (runs AFTER all services)
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$HOME/bin:$PATH"

# Wait for services to start first
sleep 30

# Apply OOM protection
TPID=$(pgrep -f com.termux | head -1)
[ -n "$TPID" ] && su -c "echo -1000 > /proc/$TPID/oom_score_adj" 2>/dev/null

# Start watchdog
nohup "$HOME/bin/assistant-watchdog" </dev/null >> "$HOME/logs/boot-watchdog.log" 2>&1 &
disown
