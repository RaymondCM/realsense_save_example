#!/usr/bin/env bash
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit
sudo apt install gnome-startup-applications --assume-yes
mkdir -p ~/.config/autostart
rm ~/.config/autostart/rs_capture.desktop || true
cp rs_capture.desktop ~/.config/autostart/
chmod +x .config/autostart/rs_capture.desktop
echo "Please add 'user_name ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /sbin/shutdown'"
echo "Script will reboot PC by default when crashed occur"
