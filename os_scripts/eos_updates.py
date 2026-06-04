#!/usr/bin/env python
import subprocess
import os
import sys

# region EOS Script Helpers
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
# endregion

def Main():
    if os.geteuid() != 0 or os.getegid() != 0:
        script_path = os.path.abspath(__file__)
        return RunCommand(f"sudo \'{script_path}\'", echo=True, check=False)
    print()

    if RunCommand("id yaybld", check=False) != 0:
        RunCommand("useradd -r -U -d /var/lib/yaybld -s /usr/bin/nologin -c \'yay build user\' -M yaybld && usermod -p \'!\' yaybld")
    if not os.path.isdir("/var/lib/yaybld"):
        RunCommand("install -d -m 700 -o yaybld -g yaybld /var/lib/yaybld")
    sudoers_good = False
    for line in ReadFile("/etc/sudoers").splitlines():
        if line == "yaybld ALL=(ALL) NOPASSWD: /usr/bin/pacman":
            sudoers_good = True
            break
    if not sudoers_good:
        WriteFile("/etc/sudoers", ReadFile("/etc/sudoers") + "yaybld ALL=(ALL) NOPASSWD: /usr/bin/pacman\n")

    print("\033[36mUpdating all packages...\033[0m")
    RunCommand("sudo -n -u yaybld yay -Syu --noconfirm", echo=True)
    print()

    print(f"\033[36mRemoving orphaned packages...\033[0m")
    stdout, _ = RunCommand("pacman -Qqdt", capture=True, check=False)
    orphans = stdout.splitlines()
    if len(orphans) == 0:
        print("There is nothing to do.")
    else:
        print(f"{" ".join(orphans)}")
        RunCommand(f"pacman -Rns {" ".join(orphans)} --noconfirm", echo=True)
    print()

    print("\033[36mClearing cache...\033[0m")
    RunCommand("find /var/cache/pacman/pkg -mindepth 1 -delete", check=False)
    RunCommand("find /var/lib/yaybld -mindepth 1 -delete", check=False)
    RunCommand("find /home/*/.cache/yay -mindepth 1 -delete", check=False)
    RunCommand("find /root/.cache/yay -mindepth 1 -delete", check=False)
    print()

    return 0
sys.exit(Main())
