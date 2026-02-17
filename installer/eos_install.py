#!/bin/env python

import requests
import subprocess
import os
import sys
import shutil

# region EpsilonOS Helpers
def WriteFile(filePath, contents, binary=False):
	filePath = os.path.realpath(os.path.expanduser(filePath))
	os.makedirs(os.path.dirname(filePath), exist_ok=True)
	with open(filePath, "wb" if binary else "w", encoding=(None if binary else "UTF-8")) as file:
		file.write(contents)
def ReadFile(filePath, defaultContents=None, binary=False):
	filePath = os.path.realpath(os.path.expanduser(filePath))
	if not os.path.exists(filePath):
		if defaultContents != None:
			return defaultContents
	with open(filePath, "rb" if binary else "r", encoding=(None if binary else "UTF-8")) as file:
		return file.read()
def CreateFile(filePath, contents, mode=0o600, binary=False):
	filePath = os.path.realpath(os.path.expanduser(filePath))
	fd = os.open(filePath, os.O_WRONLY | os.O_CREAT, mode)
	with open(fd, "wb" if binary else "w", encoding=(None if binary else "UTF-8")) as file:
		file.write(contents)
def RunCommand(command, echo=False, capture=False, input=None, check=True, env=None):
	if echo and capture:
		raise Exception("Command cannot be run with both echo and capture.")
	result = subprocess.run(command, stdout=(None if echo else subprocess.PIPE), stderr=(None if echo else subprocess.STDOUT), input=input, env=env, check=False, shell=True, text=True)
	if check and result.returncode != 0:
		print(result.stdout)
		raise Exception(f"Sub-process returned non-zero exit code.\nExitCode: {result.returncode}\nCmdLine: {command}")
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

def Main():
	# NOTE outdated gpg keys on the host will cause pacstrap to fail.
	# Run sudo pacman -Sy archlinux-keyring on host to fix.

	# Initialization and scanity checking
	ignoreScanityFailures = False
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
		PrintError("Nothing is mounted on /sys. IntegraBoot requires SysFs.")
		if not ignoreScanityFailures:
			return 1
	if not os.path.ismount("/proc"):
		PrintError("Nothing is mounted on /proc. IntegraBoot requires Proc.")
		if not ignoreScanityFailures:
			return 1
	if not os.path.ismount("/dev"):
		PrintError("Nothing is mounted on /dev. IntegraBoot requires DevTmpFs.")
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
	if not os.path.isfile("./offline.conf"):
		offlineDotConf = "\n".join([
			"# Sets the drive where EpsilonOS should be installed. (e.g. /dev/sda)",
			"rootDrive=",
			"",
			"# Sets a secondary drive where the efi system partition should be placed. (e.g. /dev/sdb)",
			"# Leave this field blank to place the efi system partition on the rootDrive.",
			"efiDrive=",
			"",
			"# Sets the disk encryption password for the rootDrive. A password of at least 16 characters in length is strongly recommended.",
			"password=",
			"",
			"# Sets the account password for your user account. A 6 digit pin should be sufficient however a longer password can be used.",
			"# After 5 incorrect login attempts your user account will be locked. This is to prevent brute force attacks.",
			"# You can use your disk encryption password to unlock your user account if it becomes locked using unlockctl.",
			"pin=",
			"",
			"# If ttyOnly=True then after booting up you will be presented with a command line only.",
			"# If ttyOnly=False then the KDE Plasma desktop will be installed with the SDDM login manager.",
			"# If you are unsure then you should set ttyOnly=False for the standard EpsilonOS experience.",
			"ttyOnly=false",
		]) + "\n"
		CreateFile("./offline.conf", offlineDotConf, 0o600)
		PrintWarning("./offline.conf does not exist in the current working directory so a blank template was created.")
		PrintWarning("Please fill out each field in ./offline.conf with your desired options and run eos_install again.")
		print()
		return 1
	rootDrive = None
	efiDrive = None
	password = None
	pin = None
	ttyOnly = None
	for line in ReadFile("./offline.conf").splitlines():
		if line.startswith("#") or line == "":
			continue
		elif not "=" in line:
			PrintError(f"Invalid line in offline.conf: {line}")
			return 1
		else:
			key = line[:line.find("=")]
			value = line[line.find("=") + 1:]
			if key == "rootDrive":
				if rootDrive != None:
					PrintError(f"rootDrive was already set in offline.conf: {line}")
					return 1
				if RunCommand(f"sh -c \'if [ -b \"{value}\" ]; then exit 0; else exit 1; fi\'", check=False) != 0:
					PrintError(f"rootDrive specified in offline.conf was not a valid block device: {line}")
					return 1
				rootDrive = value
			elif key == "efiDrive":
				if efiDrive != None:
					PrintError(f"efiDrive was already set in offline.conf: {line}")
					return 1
				if value != "" and RunCommand(f"sh -c \'if [ -b \"{value}\" ]; then exit 0; else exit 1; fi\'", check=False) != 0:
					PrintError(f"efiDrive specified in offline.conf was not a valid block device: {line}")
					return 1
				efiDrive = value
			elif key == "password":
				if password != None:
					PrintError(f"password was already set in offline.conf: {line}")
					return 1
				if value == "":
					PrintError(f"password specified in offline.conf was empty: {line}")
					return 1
				if len(value) < 16:
					PrintWarning(f"password specified in offline.conf is less than 16 characters in length: {line}")
				password = value
			elif key == "pin":
				if pin != None:
					PrintError(f"pin was already set in offline.conf: {line}")
					return 1
				if value == "":
					PrintError(f"pin specified in offline.conf was empty: {line}")
					return 1
				pin = value
			elif key == "ttyOnly":
				if ttyOnly != None:
					PrintError(f"ttyOnly was already set in offline.conf: {line}")
					return 1
				if value.lower() == "true":
					ttyOnly = True
				elif value.lower() == "false":
					ttyOnly = False
				else:
					PrintError(f"ttyOnly specified in offline.conf must be either True or False: {line}")
					return 1
			else:
				PrintError(f"Unknown key in offline.conf: {line}")
				return 1
	if rootDrive == None:
		PrintError(f"rootDrive was not specified in offline.conf.")
		return 1
	if efiDrive == None or efiDrive == "":
		efiDrive = rootDrive
	if password == None:
		PrintError(f"password was not specified in offline.conf.")
		return 1
	if pin == None:
		PrintError(f"pin was not specified in offline.conf.")
		return 1
	if ttyOnly == None:
		ttyOnly = False
	


	# Disk, partition, filesystem, and encryption setup
	print("Creating new GPT partition table...")
	RunCommand(f"wipefs -a \"{rootDrive}\"")
	RunCommand(f"sgdisk --clear \"{rootDrive}\"")
	if efiDrive != rootDrive:
		RunCommand(f"wipefs -a \"{efiDrive}\"")
		RunCommand(f"sgdisk --clear \"{efiDrive}\"")

	print("Creating partitions...")
	RunCommand(f"sgdisk --new=1:0:+512M --typecode=1:EF00 --change-name=1:\"EpsilonOS EFI Partition\" \"{efiDrive}\"")
	efiPart = efiDrive + ("p1" if efiDrive[-1].isdigit() else "1")
	if efiDrive != rootDrive:
		RunCommand(f"partprobe \"{efiDrive}\"")
	if efiDrive != rootDrive:
		RunCommand(f"sgdisk --new=1:0:0 --typecode=1:8309 --change-name=1:\"EpsilonOS Root\" \"{rootDrive}\"")
		rootPart = rootDrive + ("p1" if rootDrive[-1].isdigit() else "1")
	else:
		RunCommand(f"sgdisk --new=2:0:0 --typecode=2:8309 --change-name=2:\"EpsilonOS Root\" \"{rootDrive}\"")
		rootPart = rootDrive + ("p2" if rootDrive[-1].isdigit() else "2")
	RunCommand(f"partprobe \"{rootDrive}\"")
	
	print("Setting up disk encryption...")
	RunCommand(f"cryptsetup luksFormat \"{rootPart}\" --type luks2 --cipher aes-xts-plain64 --force-password --hash sha512 --pbkdf argon2id --use-random --batch-mode", input=password) # OPTIONAL: --integrity hmac-sha256
	RunCommand(f"cryptsetup open \"{rootPart}\" new_cryptroot --batch-mode", input=password)

	print("Creating filesystems...")
	RunCommand(f"mkfs.fat -F32 -n \"EFI\" -S 4096 \"{efiPart}\"")
	RunCommand("mkfs.ext4 -q -L \"EOS Root\" -E lazy_journal_init /dev/mapper/new_cryptroot")
	
	print("Mounting filesystems...")
	os.makedirs("/new_root/", exist_ok=True)
	RunCommand("mount /dev/mapper/new_cryptroot /new_root")
	os.makedirs("/new_root/boot", exist_ok=True)
	RunCommand(f"mount \"{efiPart}\" /new_root/boot")	

	# Pacstrap base system install
	print("Installing base system... (This will take a very long time.)")
	RunCommand("pacstrap /new_root base linux linux-firmware --noconfirm", echo=True)
	print()

	# Mkswap
	print(f"Not Creating swapfile due to insufficient space...")
	RunCommand("fallocate -l 4G /new_root/swapfile")
	RunCommand("chown +0:+0 /new_root/swapfile")
	RunCommand("chmod 0600 /new_root/swapfile")
	RunCommand("mkswap /new_root/swapfile")

	# Genfstab
	print(f"Generating fstab...")
	efiPartUUID = RunCommand(f"blkid -o value -s UUID \"{efiPart}\"", capture=True)
	rootPartUUID = RunCommand("blkid -o value -s UUID /dev/mapper/new_cryptroot", capture=True)
	eosDriveSupportsTrim = ReadFile(f"/sys/block/{os.path.basename(rootDrive)}/queue/discard_max_bytes").strip() != "0"
	fstab = "\n".join([
		f"# EpsilonOS Root",
		f"UUID={rootPartUUID} / ext4 rw,noatime,errors=remount-ro{",discard" if eosDriveSupportsTrim else ""} 0 1",
		f"",
		f"# EpsilonOS EFI Partition",
		f"UUID={efiPartUUID} /boot vfat rw,noatime,errors=remount-ro,uid=0,gid=0,dmask=0077,fmask=0177,codepage=437,iocharset=ascii,shortname=mixed,utf8{",discard" if eosDriveSupportsTrim else ""} 0 2",
	]) + "\n"
	if os.path.exists("/new_root/swapfile"):
		fstab += "\n".join([
			f"",
			f"# EpsilonOS Swap",
			f"/swapfile swap swap sw 0 0",
		]) + "\n"
	WriteFile("/new_root/etc/fstab", fstab)
	RunCommand("chown +0:+0 /new_root/etc/fstab")
	RunCommand("chmod 0644 /new_root/etc/fstab")
	print()

	print("Installing IntegraBoot...")
	RunCommand("curl -L https://github.com/FinlayTheBerry/IntegraBoot/releases/latest/download/integraboot.py -o /new_root/usr/bin/integraboot")
	RunCommand("chown +0:+0 /new_root/usr/bin/integraboot")
	RunCommand("chmod 0755 /new_root/usr/bin/integraboot")
	RunCommand("mkdir -p /new_root/var/lib/integraboot")
	RunCommand("chown +0:+0 /new_root/var/lib/integraboot")
	RunCommand("chmod 0700 /new_root/var/lib/integraboot")
	RunCommand("curl -L https://github.com/FinlayTheBerry/IntegraBoot/releases/latest/download/integrastub.efi -o /new_root/var/lib/integraboot/integrastub.efi")
	RunCommand("chown +0:+0 /new_root/var/lib/integraboot/integrastub.efi")
	RunCommand("chmod 0400 /new_root/var/lib/integraboot/integrastub.efi")
	RunCommand("pacstrap /new_root python efibootmgr efitools --noconfirm", echo=True)
	print()

	print("Running IntegraBoot...")
	RunCommand("arch-chroot /new_root integraboot", echo=True)
	print()

	# Set local timezone to UTC. In the future we should ask the user to choose.
	RunCommand(f"ln -sf /new_root/usr/share/zoneinfo/UTC /new_root/etc/localtime")

	# Set the locale to en_US UTF-8. In the future we should ask the user to choose.
	WriteFile("/new_root/etc/locale.gen", "en_US.UTF-8 UTF-8")
	RunCommand(f"arch-chroot /new_root locale-gen")

	# Enable to systemd timesync service and update the time
	RunCommand("arch-chroot /new_root systemctl enable systemd-timesyncd")
	RunCommand("arch-chroot /new_root timedatectl set-ntp true")
	RunCommand("arch-chroot /new_root timedatectl set-local-rtc 0 --adjust-system-clock")

	# Set the hostname
	WriteFile("/new_root/etc/hostname", "EpsilonOS")

	# Lock the root user for normal login (sudo is the only way)
	RunCommand(f"arch-chroot /new_root usermod -p \'!*\' root")
	RunCommand(f"arch-chroot /new_root usermod -s /usr/bin/nologin root")

	# Create the user and set their password and assign them membership in wheel
	RunCommand(f"arch-chroot /new_root useradd -m -G wheel -c Epsilon epsilon")
	RunCommand(f"arch-chroot /new_root bash -c \'echo \'\\\'\'epsilon:{pin.replace("\'", "\'\\\'\'")}\'\\\'\' | chpasswd\'")
	RunCommand(f"arch-chroot /new_root chage -m -1 -M -1 -W -1 -I -1 -E \"\" epsilon")
	
	# Install sudo and setup the sudoers file and faillock.conf
	RunCommand("pacstrap /new_root sudo --noconfirm", echo=True)
	sudoers = "\n".join([
		f"Defaults!/usr/bin/visudo env_keep += \"SUDO_EDITOR EDITOR VISUAL\"",
		f"Defaults secure_path=\"/usr/local/sbin:/usr/local/bin:/usr/bin\"",
		f"Defaults timestamp_timeout=0",
		f"root ALL=(ALL:ALL) ALL",
		f"%wheel ALL=(ALL:ALL) ALL",
	]) + "\n"
	WriteFile("/new_root/etc/sudoers", sudoers)
	RunCommand("chown +0:+0 /new_root/etc/sudoers")
	RunCommand("chmod 0400 /new_root/etc/sudoers")
	RunCommand("mkdir -p /new_root/etc/security")
	RunCommand("chown +0:+0 /new_root/etc/security")
	RunCommand("chmod 0755 /new_root/etc/security")
	WriteFile("/new_root/etc/security/faillock.conf", "nodelay")
	RunCommand("chown +0:+0 /new_root/etc/security/faillock.conf")
	RunCommand("chmod 0644 /new_root/etc/security/faillock.conf")

	# Set default target to multi user target
	RunCommand("arch-chroot /new_root systemctl set-default multi-user.target")

	# Setup networkd and resolved
	RunCommand(f"arch-chroot /new_root systemctl enable systemd-networkd.service")
	RunCommand(f"arch-chroot /new_root systemctl enable systemd-resolved.service")
	RunCommand("mkdir -p /new_root/etc/systemd")
	RunCommand("chown +0:+0 /new_root/etc/systemd")
	RunCommand("chmod 755 /new_root/etc/systemd")
	RunCommand("mkdir -p /new_root/etc/systemd/network")
	RunCommand("chown +0:+0 /new_root/etc/systemd/network")
	RunCommand("chmod 755 /new_root/etc/systemd/network")
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
	WriteFile("/new_root/etc/systemd/network/default.network", DefaultDotNetwork)
	RunCommand("chown +0:+0 /new_root/etc/systemd/network/default.network")
	RunCommand("chmod 644 /new_root/etc/systemd/network/default.network")
	ResolvedDotConf = "\n".join([
		"[Resolve]",
		"DNS=194.242.2.2#dns.mullvad.net 2a07:e340::2#dns.mullvad.net",
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
	RunCommand("chown +0:+0 /new_root/etc/systemd/resolved.conf")
	RunCommand("chmod 644 /new_root/etc/systemd/resolved.conf")

	if not ttyOnly:
		# Install sddm
		RunCommand("pacstrap /new_root sddm --noconfirm", echo=True)
		RunCommand("arch-chroot /new_root systemctl enable sddm.service")
		RunCommand("mkdir -p /new_root/etc/sddm.conf.d")
		RunCommand("chown +0:+0 /new_root/etc/sddm.conf.d")
		RunCommand("chmod 755 /new_root/etc/sddm.conf.d")
		NumlockDotConf = "\n".join([
			f"[General]",
			f"Numlock=on",
		]) + "\n"
		WriteFile("/new_root/etc/sddm.conf.d/numlock.conf", NumlockDotConf)
		RunCommand("chown +0:+0 /new_root/etc/sddm.conf.d/numlock.conf")
		RunCommand("chmod 644 /new_root/etc/sddm.conf.d/numlock.conf")
		AutoLoginDotConf = "\n".join([
			f"[Autologin]",
			f"Relogin=false",
			f"Session=plasma.desktop",
			f"User=epsilon",
		]) + "\n"
		WriteFile("/new_root/etc/sddm.conf.d/auto_login.conf", AutoLoginDotConf)
		RunCommand("chown +0:+0 /new_root/etc/sddm.conf.d/auto_login.conf")
		RunCommand("chmod 644 /new_root/etc/sddm.conf.d/auto_login.conf")

		# Set the default target to the graphical target
		RunCommand("arch-chroot /new_root systemctl set-default graphical.target")

		# Install KDE Plasma
		RunCommand("pacstrap /new_root plasma-desktop sddm-kcm plasma-workspace qt6-wayland --noconfirm", echo=True)

	# Unmount /new_root
	RunCommand("umount /new_root/boot")
	RunCommand("umount /new_root")
	RunCommand("cryptsetup close new_cryptroot")

	print(f"Success! EpsilonOS has been installed.")
sys.exit(Main())











"""
# Next we install other useful tools (optional)
pacstrap /mnt nano sudo base-devel git

# Next install wifi service (optional)
pacstrap /mnt iwd

# -- Settings/Configs (from chroot) --
# Next enable wifi service (optional)
# You should only do this if you installed iwd with pacstrap earlier
systemctl enable iwd


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
echo -e "	"buildDir": "/tmp/yay"," >> ~/.config/yay/config.json
echo -e "	"cleanBuild": false," >> ~/.config/yay/config.json
echo -e "	"diffmenu": false," >> ~/.config/yay/config.json
echo -e "	"editmenu": false," >> ~/.config/yay/config.json
echo -e "	"noconfirm": true" >> ~/.config/yay/config.json
echo -e "}" >> ~/.config/yay/config.json
exit

# Next install mkinitcpio-numlock with yay (optional)
su finlaytheberry
yay -S mkinitcpio-numlock
exit

# -- Setting up wifi (optional) --
# If you need to setup wifi 
# First scan for wifi adaperts
iwctl device list

# Then scan for wifi networks
iwctl station wlan0 scan
iwctl station wlan0 get-networks

# Then connect to a wifi network
iwctl station wlan0 connect FinFi

# -- Setting the fastest mirrors (optional) --
yay -S reflector
sudo reflector --country "United States" --age 48 --protocol https --sort rate --save /etc/pacman.d/mirrorlist

# -- Plasma Desktop Environment --
# First install the programs needed for kde plasma desktop
yay -S sddm plasma-desktop sddm-kcm plasma-workspace qt6-wayland
# Next enable and configure sddm

# Next restart sddm after updating sddm.conf
sudo systemctl restart sddm
# Finally set the boot target to graphical.target and reboot
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
"""