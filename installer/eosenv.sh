#!/usr/bin/bash

# Ensure we are running in alacritty not just bash alone
if [[ "$1" != "alacritty" ]]; then
    alacritty -e bash "$0" "alacritty"
    exit 0
fi

# Make sure we are running as root
if [[ "$(id -u)" != "0" ]]; then
    sudo "$0" "alacritty"
    exit 0
fi

# Make sure /mnt is mounted
if [[ "$(findmnt /mnt)" == "" ]]; then
    disk="/dev/$(lsblk -d -o NAME,SIZE,TYPE | grep '^sd' | grep '1.8T' | awk '{print $1}')2"
    mount "$disk" "/mnt"
fi

# Change directories and launch vscode, dolphin, and a shell
cd /mnt/ImportantData/Unsorted/eos/installer
code --no-sandbox --user-data-dir "/home/finlaytheberry" "/mnt/ImportantData/Unsorted/eos/installer"
sudo -u finlaytheberry dolphin "/mnt/ImportantData/Unsorted/eos/installer" &>/dev/null </dev/null &
disown
echo "EOS Installer Shell:"
exec bash