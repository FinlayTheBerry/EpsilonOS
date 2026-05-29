#!/bin/env python

import requests
import subprocess
import os
import sys
import shutil

# region EpsilonOS Helpers
def RealPath(filePath):
    return os.path.realpath(os.path.expanduser(filePath))
def GetEnvironmentDir():
    return os.path.dirname(RealPath(__file__))
def WriteFile(filePath, contents, binary=False):
    filePath = RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_TRUNC)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def AppendFile(filePath, contents, binary=False):
    filePath = RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_APPEND)
    with open(fd, "ab" if binary else "a", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def CreateFile(filePath, contents, mode, binary=False):
    filePath = RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def ReadFile(filePath, defaultContents=None, binary=False):
    filePath = RealPath(filePath)
    try:
        with open(filePath, "rb" if binary else "r", encoding=None if binary else "utf-8") as f:
            return f.read()
    except FileNotFoundError:
        if defaultContents != None:
            return defaultContents
        else:
            raise
    if defaultContents != None and not os.path.exists(filePath):
        return defaultContents
def RunCommand(command, echo=False, capture=False, input=None, check=True, env=None):
    if echo and capture:
        raise Exception("Command cannot be run with both echo and capture.")
    result = subprocess.run(command, stdout=(None if echo else subprocess.PIPE), stderr=(None if echo else subprocess.STDOUT), input=input, env=env, check=False, shell=True, text=True)
    if check and result.returncode != 0:
        raise Exception(f"Sub-process returned non-zero exit code.\nExitCode: {result.returncode}\nCmdLine: {command}\n\n{result.stdout}")
    if capture and not check:
        return result.stdout.strip(), result.returncode
    elif capture:
        return result.stdout.strip()
    elif not check:
        return result.returncode
    else:
        return
def PrintWarning(message):
	print(f"\033[93mWarning: {message}\033[0m")
def PrintError(message):
	print(f"\033[91mERROR: {message}\033[0m")
def Choice(prompt=None):
	print(f"{prompt + " " if prompt != None else ""}(Y)es/(N)o: ", end="")
	while True:
		userChoice = input().lower()
		if userChoice == "y" or userChoice == "yes" or userChoice == "(y)es":
			return True
		elif userChoice == "n" or userChoice == "no" or userChoice == "(n)o":
			return False
		else:
			print(f"{userChoice} is not a valid choice. Please enter (Y)es or (N)o: ")
# endregion

CONF_KEYS = [ "root_drive", "pin", "tty_only", "password", "efi_drive", "swap_size" ]
DEFAULT_CONF = """# Sets the drive where EpsilonOS should be installed. (e.g. /dev/sda)
root_drive=

# Sets the account password for your user account. A 6 digit pin should be sufficient however a longer password can be used.
# After 5 incorrect login attempts your user account will be locked. This is to prevent brute force attacks.
# You can use your disk encryption password to unlock your user account if it becomes locked using unlockctl.
pin=

# If tty_only=True then after booting up you will be presented with a command line only.
# If tty_only=False then the KDE Plasma desktop will be installed with the SDDM login manager.
# If you are unsure then you should set tty_only=False for the standard EpsilonOS experience.
tty_only=False

# Sets the disk encryption password for the root_drive. A password of at least 16 characters in length is strongly recommended.
# Leave this field blank to install EpsilonOS without disk encryption.
password=

# Sets a secondary drive where the efi system partition should be placed. (e.g. /dev/sdb)
# Leave this field blank to place the efi system partition on the root_drive.
efi_drive=

# Sets the size of the swapfile in bytes. (e.g. 8589934592 for 8 GiB)
# 0 means no swapfile. Leave ths field black for the same amount of swap as physical memory.
swap_size=
"""

DEPENDENCIES = [
	("uname", "util-linux"),
	("id", "util-linux"),
	("lsblk", "util-linux"),
	("wipefs", "util-linux"),
	("mount", "util-linux"),
	("blockdev", "util-linux"),
	("cryptsetup", "base"),
	("sgdisk", "gptfdisk"),
	("mkfs.fat", "dosfstools"),
	("mkfs.ext4", "e2fsprogs"),
	("pacstrap", "arch-install-scripts"),
	("arch-chroot", "arch-install-scripts"),
	("ping", "iputils"),
	("curl", "curl")
]

def Main():
	# NOTE outdated gpg keys on the host will cause pacstrap to fail.
	# Run sudo pacman -Sy archlinux-keyring on host to fix.

	# Initialization and scanity checking
	ignoreScanityFailures = True
	if os.geteuid() != 0 or os.getegid() != 0:
		PrintError(f"Root is required to run eos_install. Try sudo eos_install.")
		if not ignoreScanityFailures:
			return 1
	for dep, pac in DEPENDENCIES:
		if shutil.which(dep) == None:
			PrintError(f"Unable to locate required dependency {dep}. Try pacman -Syu {pac}.")
			if not ignoreScanityFailures:
				return 1
	if not os.path.ismount("/sys"):
		PrintError("Nothing is mounted on /sys. eos_install requires SysFs.")
		if not ignoreScanityFailures:
			return 1
	if not os.path.ismount("/proc"):
		PrintError("Nothing is mounted on /proc. eos_install requires Proc.")
		if not ignoreScanityFailures:
			return 1
	if not os.path.ismount("/dev"):
		PrintError("Nothing is mounted on /dev. eos_install requires DevTmpFs.")
		if not ignoreScanityFailures:
			return 1
	cpuinfo = ReadFile("/proc/cpuinfo").replace("\t", "")
	if not "lm" in cpuinfo[cpuinfo.find("\nflags:") + len("\nflags:"):].splitlines()[0].strip().split(" "):
		PrintError("EpsilonOS requires an x86-64 CPU.")
		if not ignoreScanityFailures:
			return 1
	if ReadFile("/sys/class/tpm/tpm0/tpm_version_major", defaultContents="").strip() != "2":
		PrintError("EpsilonOS requires a motherboard with a TPM2 chip.")
		if not ignoreScanityFailures:
			return 1
	if not os.path.exists("/sys/firmware/efi"):
		PrintError("EpsilonOS requires a UEFI motherboard. Double check that your system is not booted in CSM mode.")
		if not ignoreScanityFailures:
			return 1
	if os.path.ismount("/new_root"):
		PrintError("Something is already mounted at /new_root. Please manually unmount.")
		if not ignoreScanityFailures:
			return 1
	if os.path.isdir("/new_root") and len(os.listdir("/new_root")) != 0:
		PrintError("/new_root already exists and is not empty. Please manually check.")
		if not ignoreScanityFailures:
			return 1
	if os.path.exists("/dev/mapper/new_cryptroot"):
		PrintError("Something is already open in cryptsetup as new_cryptroot. Please manually close.")
		if not ignoreScanityFailures:
			return 1
	if RunCommand("ping -c 1 1.1.1.1", check=False) != 0:
		PrintError("An internet connection is required to run eos_install. You may need to setup WiFi with iwctl.")
		if not ignoreScanityFailures:
			return 1
	print()
	print("----- EpsilonOS Installer v1.1.0 -----")
	print()



	# offline.conf template and parsing
	CONF = {}
	if not os.path.isfile("./offline.conf"):
		CreateFile("./offline.conf", DEFAULT_CONF, 0o600)
		PrintWarning("./offline.conf does not exist in the current working directory so a blank template was created.")
		PrintWarning("Please fill out each field in ./offline.conf with your desired options and run eos_install again.")
		print()
		return 1
	for line in ReadFile("./offline.conf").splitlines():
		if line.startswith("#") or line == "":
			continue
		elif not "=" in line:
			PrintError(f"Invalid line in offline.conf: {line}")
			return 1
		else:
			key = line[:line.find("=")].lower()
			value = line[line.find("=") + 1:]
			if key in CONF:
				PrintError(f"{key} was already set in offline.conf: {line}")
				return 1
			if not key in CONF_KEYS:
				PrintError(f"Unknown key in offline.conf: {line}")
				return 1
			CONF[key] = value
	if not "root_drive" in CONF or CONF['root_drive'] == "":
		PrintError(f"root_drive was not specified in offline.conf.")
		return 1
	if RunCommand(f"sh -c \'if [ -b \"{CONF['root_drive']}\" ]; then exit 0; else exit 1; fi\'", check=False) != 0:
		PrintError(f"root_drive specified in offline.conf was not a valid block device: {CONF['root_drive']}")
		return 1
	if not "pin" in CONF:
		PrintError(f"pin was not specified in offline.conf.")
		return 1
	if not "tty_only" in CONF:
		CONF['tty_only'] = "True"
	if "tty_only" in CONF and CONF['tty_only'].lower() == "true":
		CONF['tty_only'] = True
	elif "tty_only" in CONF and CONF['tty_only'].lower() == "false":
		CONF['tty_only'] = False
	else:
		PrintError(f"tty_only specified in offline.conf must be either True or False: {CONF['tty_only']}")
		return 1
	if not "password" in CONF:
		PrintError(f"password was not specified in offline.conf.")
		return 1
	if not "efi_drive" in CONF or CONF['efi_drive'] == "":
		CONF['efi_drive'] = CONF['root_drive']
	if RunCommand(f"sh -c \'if [ -b \"{CONF['efi_drive']}\" ]; then exit 0; else exit 1; fi\'", check=False) != 0:
		PrintError(f"efi_drive specified in offline.conf was not a valid block device: {CONF['efi_drive']}")
		return 1
	if not "swap_size" in CONF or CONF['swap_size'] == "":
		swap_size_set = False
		for line in ReadFile("/proc/meminfo").splitlines():
			if line.startswith("MemTotal: "):
				swap_size_set = True
				CONF['swap_size'] = f"{int(line.split()[1]) * 1024}"
				break
		if not swap_size_set:
			PrintError(f"Unable to determine MemTotal from /proc/meminfo")
			return 1
	try:
		CONF['swap_size'] = int(CONF['swap_size'])
		if CONF['swap_size'] < -1:
			raise Exception()
	except:
		PrintError(f"swap_size specified in offline.conf was invalid: {CONF['swap_size']}")
		return 1


	# Disk, partition, filesystem, and encryption setup
	RUNTIME = {}
	print("Creating new GPT partition table...")
	RunCommand(f"wipefs -a \"{CONF['root_drive']}\"")
	RunCommand(f"sgdisk --clear \"{CONF['root_drive']}\"")
	if CONF['efi_drive'] != CONF['root_drive']:
		RunCommand(f"wipefs -a \"{CONF['efi_drive']}\"")
		RunCommand(f"sgdisk --clear \"{CONF['efi_drive']}\"")

	print("Creating partitions...")
	RunCommand(f"sgdisk --new=1:0:+512M --typecode=1:EF00 --change-name=1:\"EpsilonOS EFI Partition\" \"{CONF['efi_drive']}\"")
	RUNTIME['efi_part'] = CONF['efi_drive'] + ("p1" if CONF['efi_drive'][-1].isdigit() else "1")
	if CONF['efi_drive'] != CONF['root_drive']:
		RunCommand(f"partprobe \"{CONF['efi_drive']}\"")
	if CONF['efi_drive'] != CONF['root_drive']:
		RunCommand(f"sgdisk --new=1:0:0 --typecode=1:8309 --change-name=1:\"EpsilonOS Root\" \"{CONF['root_drive']}\"")
		RUNTIME['root_part'] = CONF['root_drive'] + ("p1" if CONF['root_drive'][-1].isdigit() else "1")
	else:
		RunCommand(f"sgdisk --new=2:0:0 --typecode=2:8309 --change-name=2:\"EpsilonOS Root\" \"{CONF['root_drive']}\"")
		RUNTIME['root_part'] = CONF['root_drive'] + ("p2" if CONF['root_drive'][-1].isdigit() else "2")
	RunCommand(f"partprobe \"{CONF['root_drive']}\"")
	
	if CONF['password'] != "":
		print("Setting up disk encryption...")
		RunCommand(f"cryptsetup luksFormat \"{RUNTIME['root_part']}\" --type luks2 --cipher aes-xts-plain64 --force-password --hash sha512 --pbkdf argon2id --use-random --batch-mode", input=CONF['password']) # OPTIONAL: --integrity hmac-sha256
		RunCommand(f"cryptsetup open \"{RUNTIME['root_part']}\" new_cryptroot --batch-mode", input=CONF['password'])

	print("Creating filesystems...")
	RunCommand(f"mkfs.fat -F32 -n \"EFI\" -S 4096 \"{RUNTIME['efi_part']}\"")
	if CONF['password'] != "":
		RunCommand("mkfs.ext4 -q -L \"EOS Root\" -E lazy_journal_init /dev/mapper/new_cryptroot")
	else:
		RunCommand(f"mkfs.ext4 -q -L \"EOS Root\" -E lazy_journal_init \"{RUNTIME['root_part']}\"")

	print("Mounting filesystems...")
	RunCommand("mkdir -m 700 -p /new_root/")
	if CONF['password'] != "":
		RunCommand("mount /dev/mapper/new_cryptroot /new_root")
	else:
		RunCommand(f"mount \"{RUNTIME['root_part']}\" /new_root")
	RunCommand("mkdir -m 700 -p /new_root/boot/")
	RunCommand(f"mount \"{RUNTIME['efi_part']}\" /new_root/boot")

	RUNTIME['efi_uuid'] = RunCommand(f"blkid -o value -s UUID \"{RUNTIME['efi_part']}\"", capture=True)
	if CONF['password'] != "":
		RUNTIME['root_uuid'] = RunCommand("blkid -o value -s UUID /dev/mapper/new_cryptroot", capture=True)
	else:
		RUNTIME['root_uuid'] = RunCommand(f"blkid -o value -s UUID \"{RUNTIME['root_part']}\"", capture=True)


		
	# Pacstrap base system install
	print("Installing base system...")
	RunCommand("pacstrap /new_root base linux linux-firmware-amdgpu linux-firmware-atheros linux-firmware-broadcom linux-firmware-cirrus linux-firmware-intel linux-firmware-mediatek linux-firmware-nvidia linux-firmware-other linux-firmware-radeon linux-firmware-realtek linux-firmware-liquidio linux-firmware-marvell linux-firmware-mellanox linux-firmware-nfp linux-firmware-qcom linux-firmware-qlogic nano --noconfirm", echo=True)
	print()

	# Mkswap
	if CONF['swap_size'] != 0:
		print(f"Creating swapfile with size {CONF['swap_size']} bytes...")
		RunCommand(f"fallocate -l {CONF['swap_size']} /new_root/swapfile")
		RunCommand("chmod 600 /new_root/swapfile")
		RunCommand("mkswap /new_root/swapfile")

	# Genfstab
	print(f"Generating fstab...")
	eosDriveSupportsTrim = ReadFile(f"/sys/block/{os.path.basename(CONF['root_drive'])}/queue/discard_max_bytes").strip() != "0"
	fstab = "\n".join([
		f"# EpsilonOS Root",
		f"UUID={RUNTIME['root_uuid']} / ext4 rw,noatime,errors=remount-ro{",discard" if eosDriveSupportsTrim else ""} 0 1",
		f"",
		f"# EpsilonOS EFI Partition",
		f"UUID={RUNTIME['efi_uuid']} /boot vfat rw,noatime,errors=remount-ro,uid=0,gid=0,dmask=0077,fmask=0177,codepage=437,iocharset=ascii,shortname=mixed,utf8{",discard" if eosDriveSupportsTrim else ""} 0 2",
	]) + "\n"
	if os.path.exists("/new_root/swapfile"):
		fstab += "\n".join([
			f"",
			f"# EpsilonOS Swap",
			f"/swapfile swap swap sw 0 0",
		]) + "\n"
	WriteFile("/new_root/etc/fstab", fstab)
	print()

	print("Installing IntegraBoot...")
	# Install IntegraBoot deps
	RunCommand("pacstrap /new_root python efibootmgr efitools --noconfirm", echo=True)
	# Install integraboot.py and integrastub.efi from GitHub
	RunCommand("curl -L https://github.com/FinlayTheBerry/IntegraBoot/releases/latest/download/integraboot.py -o /new_root/usr/bin/integraboot")
	RunCommand("chmod 755 /new_root/usr/bin/integraboot")
	RunCommand("mkdir -m 700 -p /new_root/var/lib/integraboot")
	RunCommand("curl -L https://github.com/FinlayTheBerry/IntegraBoot/releases/latest/download/integrastub.efi -o /new_root/var/lib/integraboot/integrastub.efi")
	RunCommand("chmod 400 /new_root/var/lib/integraboot/integrastub.efi")
	# Run IntegraBoot
	RunCommand("arch-chroot /new_root integraboot", echo=True)
	print()

	# Install sudo and setup the sudoers file and faillock.conf
	RunCommand("pacstrap /new_root sudo --noconfirm", echo=True)
	sudoers = "\n".join([
		f"Defaults!/usr/bin/visudo env_keep += \"SUDO_EDITOR EDITOR VISUAL\"",
		f"Defaults secure_path=\"/usr/local/sbin:/usr/local/bin:/usr/bin\"",
		f"Defaults timestamp_timeout=0",
		f"root ALL=(ALL:ALL) ALL",
		f"%wheel ALL=(ALL:ALL) ALL",
		f"@includedir /etc/sudoers.d",
	]) + "\n"
	WriteFile("/new_root/etc/sudoers", sudoers)
	WriteFile("/new_root/etc/security/faillock.conf", "nodelay")

	# Lock the root user for normal login (sudo is the only way)
	RunCommand(f"arch-chroot /new_root usermod -p \'!*\' root")
	RunCommand(f"arch-chroot /new_root usermod -s /usr/bin/nologin root")

	# Create the user and set their password and assign them membership in wheel
	RunCommand(f"arch-chroot /new_root useradd -m -G wheel -c Epsilon epsilon")
	RunCommand(f"arch-chroot /new_root chage -m -1 -M -1 -W -1 -I -1 -E \"\" epsilon")
	if CONF['pin'] != "":
		RunCommand(f"arch-chroot /new_root bash -c \'echo \'\\\'\'epsilon:{CONF['pin'].replace("\'", "\'\\\'\'")}\'\\\'\' | chpasswd\'")
	else:
		RunCommand(f"arch-chroot /new_root passwd -d epsilon")

	# Install yay-bin
	RunCommand("pacstrap /new_root base-devel --noconfirm", echo=True)
	RunCommand("arch-chroot /new_root sudo -u epsilon mkdir -m 700 /home/epsilon/yay-bin")
	RunCommand("arch-chroot /new_root sudo -u epsilon curl https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=yay-bin -o /home/epsilon/yay-bin/PKGBUILD")
	RunCommand("arch-chroot /new_root sudo -u epsilon sh -c \'cd /home/epsilon/yay-bin && makepkg --nodeps\'")
	RunCommand("arch-chroot /new_root sudo -u epsilon sh -c \'rm /home/epsilon/yay-bin/yay-bin-debug-*.pkg.tar.zst\'")
	RunCommand("arch-chroot /new_root sh -c \'pacman -U --noconfirm --needed /home/epsilon/yay-bin/yay-bin-*.pkg.tar.zst\'", echo=True)
	RunCommand("arch-chroot /new_root sudo -u epsilon rm -rf /home/epsilon/yay-bin")

	# Set the hostname
	CreateFile("/new_root/etc/hostname", "EpsilonOS", 0o644)
	
	# Set default target to multi user target
	RunCommand("arch-chroot /new_root systemctl set-default multi-user.target")

	# Setup networkd and resolved
	RunCommand("arch-chroot /new_root systemctl enable systemd-networkd.service")
	DefaultDotNetwork = "\n".join([
		f"[Match]",
		f"Name=en* wl* ww*",
		f"",
		f"[Network]",
		f"DHCP=yes",
		f"IPv6PrivacyExtensions=yes",
		f"LLDP=no",
		f"",
		f"[DHCP]",
		f"UseDNS=no",
		f"UseHostname=no",
		f"UseDomains=no",
		f"UseRoutes=yes",
	]) + "\n"
	CreateFile("/new_root/etc/systemd/network/default.network", DefaultDotNetwork, 0o644)

	RunCommand("arch-chroot /new_root systemctl enable systemd-resolved.service")
	ResolvedDotConf = "\n".join([
		"[Resolve]",
		"DNS=1.1.1.1#cloudflare-dns.com 1.0.0.1#cloudflare-dns.com 2606:4700:4700::1111#cloudflare-dns.com 2606:4700:4700::1001#cloudflare-dns.com",
		"FallbackDNS=",
		"DNSSEC=yes",
		"DNSOverTLS=yes",
		"MulticastDNS=no",
		"LLMNR=no",
		"Cache=yes",
		"CacheFromLocalhost=no",
		"DNSStubListener=yes",
		"ReadEtcHosts=yes",
		"ResolveUnicastSingleLabel=no",
		"StaleRetentionSec=0",
	]) + "\n"
	WriteFile("/new_root/etc/systemd/resolved.conf", ResolvedDotConf)

	# Set locale
	WriteFile("/new_root/etc/locale.gen", "en_US.UTF-8 UTF-8")
	RunCommand(f"arch-chroot /new_root locale-gen")
	CreateFile("/new_root/etc/locale.conf", "LANG=en_US.UTF-8", 0o644)

	# Enable to systemd timesync service and update the time
	RunCommand("arch-chroot /new_root systemctl enable systemd-timesyncd")
	RunCommand("arch-chroot /new_root timedatectl set-timezone America/Los_Angeles")
	RunCommand("arch-chroot /new_root timedatectl set-local-rtc 0")
	
	if not CONF['tty_only']:
		# TTYS=$(busybox ls /dev/tty* | busybox grep -E '^/dev/tty[0-9]+$'); for tty in $TTYS; do /usr/bin/setleds -D +num -caps -scroll < $tty; done
		
		# Install KDE Plasma
		RunCommand("pacstrap /new_root plasma-desktop sddm sddm-kcm --noconfirm", echo=True)

		RunCommand("arch-chroot /new_root systemctl enable sddm.service")
		RunCommand("mkdir -m 755 -p /new_root/etc/sddm.conf.d")
		SDDMEpsilonOSDotConf = "\n".join([
			f"[General]",
			f"Numlock=on",
			f"",
			f"[Autologin]",
			f"Relogin=false",
			f"User=epsilon",
			f"Session=plasma",
			f"",
			f"[Theme]",
			f"Current=breeze",
			f"CursorTheme=breeze_cursors",
			f"Font=Noto Sans,10,-1,0,400,0,0,0,0,0,0,0,0,0,0,1",
		]) + "\n"
		CreateFile("/new_root/etc/sddm.conf.d/EpsilonOS.conf", SDDMEpsilonOSDotConf, 0o644)

		RunCommand("pacstrap /new_root plasma-nm plasma-pa pipewire-pulse wireplumber kscreen powerdevil power-profiles-daemon bluedevil --noconfirm", echo=True)
		RunCommand("arch-chroot /new_root systemctl enable NetworkManager")

		RunCommand("arch-chroot /new_root systemctl enable --global pipewire pipewire-pulse wireplumber")
		RunCommand("arch-chroot /new_root systemctl enable power-profiles-daemon")
		RunCommand("arch-chroot /new_root systemctl enable bluetooth")

		RunCommand("pacstrap /new_root dolphin spectacle alacritty firefox --noconfirm", echo=True)
		
		# Set the default target to the graphical target
		RunCommand("arch-chroot /new_root systemctl set-default graphical.target")
		
	# Unmount /new_root
	RunCommand("umount -R /new_root")
	if CONF['password'] != "":
		RunCommand("cryptsetup close new_cryptroot")

	print(f"Success! EpsilonOS has been installed.")
	print()
sys.exit(Main())











"""
# Next set the yay config (optional)
su finlaytheberry
echo -e "{" > ~/.config/yay/config.json
echo -e "	"buildDir": "/tmp/yay"," >> ~/.config/yay/config.json
echo -e "	"cleanBuild": false," >> ~/.config/yay/config.json
echo -e "	"diffmenu": false," >> ~/.config/yay/config.json
echo -e "	"editmenu": false," >> ~/.config/yay/config.json
echo -e "	"noconfirm": true" >> ~/.config/yay/config.json
echo -e "}" >> ~/.config/yay/config.json
exit

# Next install mkinitcpio-numlock with yay (optional)
yay -S mkinitcpio-numlock

# -- Setting the fastest mirrors (optional) --
yay -S reflector
sudo reflector --country "United States" --age 48 --protocol https --sort rate --save /etc/pacman.d/mirrorlist

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
"""