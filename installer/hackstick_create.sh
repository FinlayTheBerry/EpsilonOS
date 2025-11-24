#!/bin/bash
# APPROVED: 04/14/2025
set -xeuo pipefail

choice() {
    echo "$1 (Y)es/(N)o:"
    while true; do
        read userChoice
        userChoice=$(echo "$userChoice" | tr "[:upper:]" "[:lower:]")
        if [[ "$userChoice" == "yes" ]] || [[ "$userChoice" == "y" ]]; then
            return 0
        else
            return 1
        fi
    done
}
error() {
    echo -e "\e[91mERROR: $1\e[0m"
}
abort() {
    echo "Aborting..."
    echo -e "\e[m"
    exit 1
}

# Print version header
echo "HackStick Installer v1.0.0"
echo ""
# Scanity checks
if [[ ! $(id -u) == 0 ]] || [[ ! $(id -g) == 0 ]]; then
    error "hackstick_create.sh must be run as root."
    abort
fi
# Prompt to select target usb drive
echo "Select drive to create hackstick."
lsblk -d -n -o NAME,SIZE,MODEL
read osDrive
if [[ ! -b /dev/$osDrive ]] || [[ ! "$(lsblk -dn -o TYPE /dev/$osDrive)" == "disk" ]]; then
    error "/dev/$osDrive is not a valid disk."
    abort
fi
echo "WARNING: All data in all partitions on /dev/$osDrive will be destroyed!"
if (( $(lsblk -b -dn -o SIZE /dev/$osDrive) > 64 * 1024 * 1024 * 1024 )); then
    printf "\e[31m"
    echo "WARNING: Additionally /dev/$osDrive seems to be a LARGE DRIVE!"
    printf "\e[0m"
fi
if ! choice "Are you sure you want to proceed?"; then
    abort
fi
echo ""
echo "Making a hackstick out of /dev/$osDrive"

echo "Nuking existing then creating and formatting partitions..."
# Nuke existing partition table and replace with a brand new GPT
wipefs -a /dev/$osDrive
sgdisk --zap-all /dev/$osDrive
# BIOS Boot Partition (1 MiB)
sgdisk /dev/$osDrive --new=1:1M:+1M --typecode=1:ef02 >/dev/null
# EFI System Partition (ESP) (512 MiB)
sgdisk --new=2:2M:+512M --typecode=2:EF00 --change-name=2:"EFI System Partition" /dev/$osDrive >/dev/null
mkfs.fat -F32 -n "EFI" /dev/${osDrive}2 >/dev/null
# Root partition (rest of the disk)
sgdisk --new=3:514M:0 --typecode=3:8309 --change-name=3:"HackStick" /dev/$osDrive >/dev/null
mkfs.ext4 -q -L "HackStick" -E lazy_journal_init /dev/${osDrive}3 >/dev/null

# Mount filesystems
echo "Mounting filesystems..."
mount /dev/${osDrive}3 /mnt
mkdir -p /mnt/boot
mount /dev/${osDrive}2 /mnt/boot

# Install arch
echo "Installing base arch... (THIS WILL TAKE AWHILE)"
pacstrap /mnt base linux linux-firmware grub efibootmgr

# Install GRUB
echo "Installing GRUB... (THIS WILL ALSO TAKE AWHILE)"
mkdir -p /mnt/boot/grub
# Install grub efi
arch-chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=HackStick --removable --recheck --verbose
# Install grub mbr
arch-chroot /mnt grub-install --target=i386-pc --recheck /dev/$osDrive --verbose
# Create default grub config
arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg

echo "Cleaning up..."
# Unmount filesystems
umount -R /mnt
# genfstab
genfstab -U /mnt >/mnt/etc/fstab

echo "Done. YIPPIE!"