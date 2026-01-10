# What is UEFI?
When you turn on your PC the first piece of software that runs is your motherboard's firmware (called the UEFI).
The UEFI is responsible for checking the hardware to ensure it's working correctly and then selecting which operating system to run next.
When making this decision the UEFI has an ordered list of OSes to choose from or you can press F8 to bring up a menu where you can select an OS manually.
This system makes it super easy to switch between multiple OSes like Windows and Linux but it puts your PC at risk if a hacker gets physical access to your PC.
If a hacker is able to plug in a thumb drive with a custom OS into your PC they can select it from the boot menu and launch into an OS that they control.
This means the normal security restrictions EOS places on apps don't apply anymore and the hacker has full control of your PC.

# What is Secure Boot?
Secure boot is a feature of the UEFI which exists to fix this issue by creating a list of approved operating systems and only allowing those to boot.
By default secure boot is usually enabled but the allow list contains lots of operating systems which don't have proper security and can easily be abused.
EOS changes the allow list to only include the current EOS installation and blocking all other OSes.
This makes your PC more secure however it prevents windows or other OSes from functioning.

# Setup Requires Your Help!
When it comes to secure boot the UEFI doesn't trust any OS not even EOS.
That's why we need your help to tell the UEFI that you concent to letting EOS modify the secure boot settings.
To do this you must clear any existing secure boot keys.
This puts your UEFI into setup mode where the next booted OS will be allowed to setup and take control of the secure boot settings.
Reboot into your motherboard's UEFI settings menu (often called the BIOS) and look for an option called "Clear All Secure Boot Keys" or "Enable Custom Secure Boot Mode".
If you did it right then the EOS installer will tell you that the system is in setup mode and ask if you would like EOS to take control of the secure boot settings.

# What If I Still Want Windows?
We totally get it. EOS is cool but most software is still made for Windows so completely switching is tricky.
If you want to dual boot EOS and Windows you unfortunately must disable secure boot. Even though this is less secure EOS uses full disk encryption to keep you as safe as possible even without help from secure boot.