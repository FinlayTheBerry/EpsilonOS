#!/bin/bash
# Initializes and sets up a new debian install.
# Written by RandomiaGaming

# Update package cache
apt update

# Make sure x86 packages are supported
# Note that x64 will still be the default whenever possible
sudo dpkg --add-architecture i386

# Install KDE Plasma (Desktop Shell)
apt install kde-plasma-desktop
apt install sddm-theme-breeze
echo -e "[Theme]\nCurrent=breeze" > /etc/sddm.conf

# Setup KRunner as search
kwriteconfig5 --file kwinrc --group ModifierOnlyShortcuts --key Meta "org.kde.krunner,/App,,toggleDisplay"
qdbus org.kde.KWin /KWin reconfigure

# Install Alacritty (Terminal)
apt install alacritty

# Install Dolphin (File Manager)
apt install dolphin

# Install Chrome (Web Browser)
wget https://dl-ssl.google.com/linux/linux_signing_key.pub -O /tmp/google.pub

# Install our favorite code editor VSCode
apt-get install wget gpg
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | tee /etc/apt/sources.list.d/vscode.list > /dev/null
rm -f packages.microsoft.gpg
apt install apt-transport-https
apt update
apt install code

# Install language compilers and tools
apt install gcc
apt install g++
apt install nasm
apt install python3
apt install nodejs
apt install gdb

# Install git
apt install git

# Install mono
apt install dirmngr gnupg apt-transport-https ca-certificates software-properties-common
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
apt-add-repository 'deb https://download.mono-project.com/repo/ubuntu stable-focal main'
apt update
apt install mono-complete

# Install our favorite hex editor Bless
apt install bless

# Install our favorite media player
apt install vlc

# Install the best free video editor
apt install kdenlive

# Install the best free audio editor
apt install audacity

# Install GParted
apt install gparted

# Install discord
echo Download ./discord.deb then press Ctrl+C
open "https://discord.com/api/download?platform=linux&format=deb"
apt install ./discord.deb
rm -f discord.deb

# Install steam
wget -O "/etc/apt/keyrings/steam.gpg" "https://repo.steampowered.com/steam/archive/stable/steam.gpg"
tee /etc/apt/sources.list.d/steam-stable.list <<'EOF'
deb [arch=amd64,i386 signed-by=/usr/share/keyrings/steam.gpg] https://repo.steampowered.com/steam/ stable steam
deb-src [arch=amd64,i386 signed-by=/usr/share/keyrings/steam.gpg] https://repo.steampowered.com/steam/ stable steam
EOF
apt update
apt install steam-launcher

# Install the best ultra-light text editor
sudo apt install featherpad

# Install our favorite C and C++ IDE CLion
sudo apt install libfuse2
echo Download ./JetbrainsToolbox.tar.gz then press Ctrl+C
open "https://www.jetbrains.com/toolbox-app/"
tar -xzf JetbrainsToolbox.tar.gz
./JetbrainsToolbox/jetbrains-toolbox
rm -f JetbrainsToolbox.tar.gz
rm -fr JetbrainsToolbox

# Finally make sure everything is up to date and ready to go
apt update
apt upgrade
apt autoremove



# SETTINGS TO CHANGE
#
# In input settings set the keyboard repeat rate to 30hrtz and the delay to 300ms
# In input settings set the default num lock state to on

# GIT IS A PAIN IN THE ASS
#
# To avoid crying follow the steps below to set up your enviroment
#
# Run git config --list --show-origin to see any configs which are not default
# It is safe to delete all the config files to get a fresh start
# Then get yourself set up by running the following
# git config --global user.name RandomiaGaming
# git config --global user.email RandomiaGaming@gmail.com
#
# Now it's time to set up ssh authentication
# Run ssh-keygen -t ed25519 -f ~/.ssh/GitHubSSH
# Then upload ~/.ssh/GitHubSSH.pub to GitHub.com
# Then add the following to ~/.ssh/config
#
# Host github.com
#    HostName github.com
#    User git
#    IdentityFile ~/.ssh/GitHubSSH
#    IdentitiesOnly yes
#
# Check the config with ssh -T git@github.com
#
# Next go to your repo and make sure the url is in the format:
# git@github.com:RandomiaGaming/RepoNameHere.git
#
# Finally enjoy git