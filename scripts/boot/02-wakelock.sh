#!/data/data/com.termux/files/usr/bin/sh
# Acquire wake lock + foreground notification on boot
termux-wake-lock

# Ongoing notification — promotes Termux to foreground service priority
sleep 3
termux-notification --ongoing \
    --title "Voice Assistant Active" \
    --content "Starting services..." \
    --id 1 \
    --priority high \
    > /dev/null 2>&1
