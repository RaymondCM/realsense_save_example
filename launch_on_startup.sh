sudo apt install gnome-startup-applications
mkdir -p ~/.config/autostart
cp rs_capture.desktop ~/.config/autostart/
chmod +x .config/autostart/rs_capture.desktop
echo "Please add 'user_name ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /sbin/shutdown'"
echo "Script will reboot PC by default when crashed occur"
