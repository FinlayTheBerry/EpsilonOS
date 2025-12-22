# -- Making An Arch Linux Live CD --
# Start by downloading the latest arch iso (I recomment the mit.edu mirror)
# The list of mirrors can be found here https://archlinux.org/download/
# Then use rufus to flash the iso to a thumb drive (I recommend dd mode)
# Next boot into your new arch live cd



# -- Partitioning System --
# Start by figuring out which disk is which
lsblk

# Next nuke the existing partition tables and create new ones
parted /dev/sda mklabel gpt # Label Types: gpt or msdos

# Next create the partitions
gdisk /dev/sda
n
1
1M
+512M
EF00 # EF00 = EFI System Partition, 8300 = Linux Filesystem, 8309 = Encrypted Linux Filesystem
w

# Next set up encryption (optional)
cryptsetup luksFormat /dev/sda1
cryptsetup open /dev/sda1 cryptroot

# Next set up filesystems
mkfs.fat -F32 /dev/sda1 # For fat32
mkfs.ext4 /dev/mapper/cryptroot # For ext4 (encrypted or unencrypted)
mkfs.exfat -s 4096 /dev/sda1 # For exFat (with cluster size of 4096 bytes)

# Next set up mount points
mount /dev/mapper/cryptroot /mnt
mkdir /mnt/boot
mount /dev/sda1 /mnt/boot

# Next setup fstab to configure how partitions auto-mount on boot
echo -e "# <partition> <mount point> <filesystem type> <options> <dump> <pass>" > /mnt/etc/fstab
echo -e "" >> /mnt/etc/fstab
echo -e "# /dev/sda1" >> /mnt/etc/fstab
echo -e "# /dev/mapper/cryptroot" >> /mnt/etc/fstab
echo -e "UUID=$(blkid -o value -s UUID /dev/mapper/cryptroot) / ext4 rw,noatime,discard,errors=remount-ro 0 1" >> /mnt/etc/fstab # discard is for SSDs which support trim
echo -e "" >> /mnt/etc/fstab
echo -e "# /dev/sda1" >> /mnt/etc/fstab
echo -e "UUID=$(blkid -o value -s UUID /dev/sda1) /boot vfat rw,noatime,discard,errors=remount-ro,uid=0,gid=0,dmask=0077,fmask=0177,codepage=437,iocharset=ascii,shortname=mixed,utf8 0 2" >> /mnt/etc/fstab # Options for FAT32 drives



# -- Setting up wifi for live cd (optional) --
# First scan for wifi adaperts
iwctl device list

# Then scan for wifi networks
iwctl station wlan0 scan
iwctl station wlan0 get-networks

# Then connect to a wifi network
iwctl station wlan0 connect FinFi

# Then test
iwctl station wlan0 show
ping google.com



# -- Installing Base System --
# Keyring Troubleshooting (optional)
# If you try the steps below and get keyring related errors then try this
pacman-key --init
pacman-key --populate archlinux

# Next we install the base system (note this step requires ethernet or wifi)
pacstrap /mnt base linux linux-firmware

# Next we install other useful tools (optional)
pacstrap /mnt nano sudo base-devel git

# Next install wifi service (optional)
pacstrap /mnt iwd

# Next we chroot into our new system
arch-chroot /mnt



# -- Settings/Configs (from chroot) --
# First set the timezone (optional)
ln -sf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime

# Next sync the bios time (optional)
hwclock --systohc

# Next set the locale and language settings (optional)
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen

# Next set a hostname (optional)
echo "your hostname" > /etc/hostname

# Next enable network service and DNS service (optional)
systemctl enable systemd-networkd
systemctl enable systemd-resolved
ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf

# Next enable wifi service (optional)
# You should only do this if you installed iwd with pacstrap earlier
systemctl enable iwd

# Next set the password for the root user
passwd

# Next make a non-root user (optional)
useradd -m -c FinlayTheBerry -G wheel finlaytheberry
passwd finlaytheberry
mkdir /home/finlaytheberry
chown finlaytheberry:finlaytheberry /home/finlaytheberry
chmod 755 /home/finlaytheberry

# Next set the sudoers file (optional)
echo -e "Defaults!/usr/bin/visudo env_keep += \"SUDO_EDITOR EDITOR VISUAL\"" > /etc/sudoers
echo -e "Defaults secure_path=\"/usr/local/sbin:/usr/local/bin:/usr/bin\"" >> /etc/sudoers
echo -e "root ALL=(ALL:ALL) ALL" >> /etc/sudoers
echo -e "%wheel ALL=(ALL:ALL) ALL" >> /etc/sudoers
echo -e "Defaults timestamp_timeout=0" >> /etc/sudoers

# Next set the default boot target
ln -sf /usr/lib/systemd/system/multi-user.target /etc/systemd/system/default.target



# -- Bootloader (SystemDBoot) (from chroot) --
# First install systemd boot
bootctl install

# Next set general systemd boot settings
echo -e "default arch" > /boot/loader/loader.conf
echo -e "timeout 0" >> /boot/loader/loader.conf
echo -e "editor 0" >> /boot/loader/loader.conf

# Next create arch linux systemd boot entry
echo -e "title Arch Linux" > /boot/loader/entries/arch.conf
echo -e "linux /vmlinuz-linux" >> /boot/loader/entries/arch.conf
echo -e "initrd /initramfs-linux.img" >> /boot/loader/entries/arch.conf
echo -e "options cryptdevice=UUID=$(blkid -o value -s UUID /dev/sda1):cryptroot root=/dev/mapper/cryptroot rw" >> /boot/loader/entries/arch.conf # If encrypted
echo -e "options root=/dev/sda1 rw" >> /boot/loader/entries/arch.conf # If unencrypted

# Next install yay manually (optional)
mkdir /yay
chown finlaytheberry:finlaytheberry /yay
su finlaytheberry
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
yay -Rns yay-debug
exit
rm -rf /yay

# Next set the yay config (optional)
su finlaytheberry
echo -e "{" > ~/.config/yay/config.json
echo -e "    "buildDir": "/tmp/yay"," >> ~/.config/yay/config.json
echo -e "    "cleanBuild": false," >> ~/.config/yay/config.json
echo -e "    "diffmenu": false," >> ~/.config/yay/config.json
echo -e "    "editmenu": false," >> ~/.config/yay/config.json
echo -e "    "noconfirm": true" >> ~/.config/yay/config.json
echo -e "}" >> ~/.config/yay/config.json
exit

# Next install mkinitcpio-numlock with yay (optional)
su finlaytheberry
yay -S mkinitcpio-numlock
exit

# Set systemd boot hooks and regenerate initramfs
echo -e "MODULES=()" > /etc/mkinitcpio.conf
echo -e "BINARIES=()" >> /etc/mkinitcpio.conf
echo -e "FILES=()" >> /etc/mkinitcpio.conf
echo -e "HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont numlock block encrypt filesystem fsck)" >> /etc/mkinitcpio.conf # If you want numlock
echo -e "HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont block encrypt filesystem fsck)" >> /etc/mkinitcpio.conf # If you dont want numlock
mkinitcpio -P



# -- Bootloader (Unified Kernel Image) (from chroot) --
# Get bootbuilder set up and remove stuff we don't need
mkdir /bootbuilder
chmod 700 /bootbuilder
touch /bootbuilder/build.sh
chmod 700 /bootbuilder/build.sh
mv /boot/vmlinuz-linux /bootbuilder/vmlinuz-linux
chmod 600 /bootbuilder/vmlinuz-linux
mv /etc/mkinitcpio.conf /bootbuilder/mkinitcpio.conf
chmod 600 /bootbuilder/mkinitcpio.conf
touch /bootbuilder/ukify.conf
chmod 600 /bootbuilder/ukify.conf
rm -rf /etc/mkinitcpio.d
rm -rf /etc/mkinitcpio.conf.d
find /boot -mindepth 1 -maxdepth 1 -exec rm -rf {} \;
echo -e "# Make initramfs" >> /bootbuilder/build.sh
echo -e "mkinitcpio -c /bootbuilder/mkinitcpio.conf -k /bootbuilder/vmlinuz-linux -g /bootbuilder/initramfs-linux" > /bootbuilder/build.sh
echo -e "" >> /bootbuilder/build.sh
echo -e "# Make unified kernel image" >> /bootbuilder/build.sh
echo -e "ukify build -c /bootbuilder/ukify.conf -o /bootbuilder/uki.efi" >> /bootbuilder/build.sh
echo -e "" >> /bootbuilder/build.sh
echo -e "# Copy unified kernel image to /boot" >> /bootbuilder/build.sh
echo -e "cp /bootbuilder/uki.efi /boot/uki.efi" >> /bootbuilder/build.sh

# Next install yay manually (optional)
mkdir /yay
chown finlaytheberry:finlaytheberry /yay
su finlaytheberry
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
yay -Rns yay-debug
exit
rm -rf /yay

# Next set the yay config (optional)
su finlaytheberry
echo -e "{" > ~/.config/yay/config.json
echo -e "    "buildDir": "/tmp/yay"," >> ~/.config/yay/config.json
echo -e "    "cleanBuild": false," >> ~/.config/yay/config.json
echo -e "    "diffmenu": false," >> ~/.config/yay/config.json
echo -e "    "editmenu": false," >> ~/.config/yay/config.json
echo -e "    "noconfirm": true" >> ~/.config/yay/config.json
echo -e "}" >> ~/.config/yay/config.json
exit

# Next install mkinitcpio-numlock with yay (optional)
su finlaytheberry
yay -S mkinitcpio-numlock
exit

# Set mkinitcpio.conf settings
echo -e "MODULES=()" > /bootbuilder/mkinitcpio.conf
echo -e "BINARIES=()" >> /bootbuilder/mkinitcpio.conf
echo -e "FILES=()" >> /bootbuilder/mkinitcpio.conf
echo -e "HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont numlock block encrypt filesystem fsck)" >> /bootbuilder/mkinitcpio.conf # If you want numlock
echo -e "HOOKS=(base udev autodetect microcode modconf kms keyboard keymap consolefont block encrypt filesystem fsck)" >> /bootbuilder/mkinitcpio.conf # If you dont want numlock

# Set ukify.conf settings
echo -e "[UKI]" > /bootbuilder/ukify.conf
echo -e "Linux=/bootbuilder/vmlinuz-linux" >> /bootbuilder/ukify.conf
echo -e "Initrd=/bootbuilder/initramfs-linux" >> /bootbuilder/ukify.conf
echo -e "Cmdline=\"cryptdevice=UUID=$(blkid -o value -s UUID /dev/sda1):cryptroot root=/dev/mapper/cryptroot rw\"" >> /bootbuilder/ukify.conf

# Install ukify
yay -S ukify efibootmgr

# Finally run boot builder to build your bootloader
/bootbuilder/build.sh

# And finally configure boot entries
efibootmgr # To list entries
efibootmgr -B -b 0000 # To delete old entries
efibootmgr -c -d /dev/sda -p 1 -l /uki.efi -L "Arch Linux UKI"
efibootmgr -c -d /dev/sda -p 1 -l /uki.efi -L "Arch Linux UKI" -e 3 # If above doesn't work
efibootmgr -c -d /dev/sda -p 1 -l /uki.efi -L "Arch Linux UKI" -e 1 # If above doesn't work
efibootmgr -o 0000
efibootmgr -t 0



# -- Your TTY Only Arch System Is Ready --
# Your system is now ready to reboot into and use with a tty
# There is more setup. But most of it is optional
# YIPPIE!
exit # from chroot
umount -R /mnt
cryptsetup close cryptroot
reboot



# -- Secure Boot (optional) --
# Gone are the days of linux requiring secure boot to be disabled
# First go into your systems bios
# Make sure that secure boot is enabled
# Make sure the boot mode is UEFI
# Remove all trusted secure boot keys (optional)
# Add a new trusted bootloader and select /boot/systemd/systemd-bootx64.efi
# Exit and make sure you save changes
# After a reboot you should be good to go!



# -- Setting up wifi (optional) --
# If you need to setup wifi 
# First scan for wifi adaperts
iwctl device list

# Then scan for wifi networks
iwctl station wlan0 scan
iwctl station wlan0 get-networks

# Then connect to a wifi network
iwctl station wlan0 connect FinFi

# Then test
iwctl station wlan0 show
ping google.com

# Then enable DHCP
echo -e "[Match]" > /etc/systemd/network/default.network
echo -e "Name=*" >> /etc/systemd/network/default.network
echo -e "" >> /etc/systemd/network/default.network
echo -e "[Network]" >> /etc/systemd/network/default.network
echo -e "DHCP=yes" >> /etc/systemd/network/default.network



# -- Setting the fastest mirrors (optional) --
yay -S reflector
sudo reflector --country "United States" --age 48 --protocol https --sort rate --save /etc/pacman.d/mirrorlist




# -- Plasma Desktop Environment --
# First install the programs needed for kde plasma desktop
yay -S sddm plasma-desktop sddm-kcm plasma-workspace qt6-wayland
# Next enable and configure sddm
sudo systemctl enable sddm
sudo echo -e "[Theme]" > /etc/sddm.conf
sudo echo -e "Current=breeze" >> /etc/sddm.conf
# Next enable numlock in sddm while we are here (optional)
sudo echo -e "" >> /etc/sddm.conf
sudo echo -e "[General]" >> /etc/sddm.conf
sudo echo -e "Numlock=on" >> /etc/sddm.conf
# Next restart sddm after updating sddm.conf
sudo systemctl restart sddm
# Finally set the boot target to graphical.target and reboot
sudo ln -sf /usr/lib/systemd/system/graphical.target /etc/systemd/system/default.target
sudo reboot



# -- Audio Setup --
# Install the tools needed for audio on linux with kde plasma
yay -S pipewire pipewire-pulse pavucontrol plasma-pa
# Sadly this seems to require a reboot
sudo reboot



# -- KDE Wallet Setup --
yay -S kwalletmanager gnupg
gpg --quick-gen-key "FinlayTheBerry <finlaytheberry@gmail.com>" rsa4096 default 0
kwalletmanager5
# Then from in the gui create a new wallet and use the GPG key we just created



# -- KDE Plasma Settings (optional) --
# Settings>Keyboard>NumLock on startup = Turn on
# Settings>Keyboard>Key Repeat>Delay=200 ms
# Settings>Keyboard>Key Repeat>Rate=30 repeats/s



# -- NVIDIA Drivers (optional) --
yay -S nvidia nvidia-utils lib32-nvidia-utils
reboot
# Then add the following to Environment Variables of the shortcut for programs you want to run on the nvidia gpu
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only
# Then hit save



# -- Cool Apps (optional) --
yay -S alacritty
yay -S dolphin
yay -S google-chrome
yay -S visual-studio-code-bin
yay -S gcc
yay -S gpp
yay -S nasm
yay -S python3
yay -S nodejs
yay -S gdb
yay -S git
yay -S bless
yay -S vlc
yay -S kdenlive
yay -S audacity
yay -S discord
yay -S featherpad
yay -S unzip
yay -S zip
yay -S minecraft-launcher
yay -S firefox
yay -S wireshark-qt
yay -S obs-studio
yay -S ffmpeg
yay -S libreoffice
yay -S yt-dlp
# And setup the multilib x86-32 arch repo
su root
echo -e "" >> /etc/pacman.conf
echo -e "[multilib]" >> /etc/pacman.conf
echo -e "Include = /etc/pacman.d/mirrorlist" >> /etc/pacman.conf
exit
yay -Sy
# Then install packages which are in multilib
yay -S steam
yay -S wine wine-mono

jetbrains stuff
