#!/usr/bin/env python3
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
        script_name = os.path.splitext(os.path.basename(os.path.realpath(__file__)))[0]
        PrintError(f"Root is required to take a backup. Try sudo {script_name}.")
        return 1
    if not os.path.exists("/important_data"):
        PrintError("/important_data does not exist. Did you forget to run important_data?")
        return
    if RunCommand("findmnt /important_data", check=False) != 0:
        PrintError("Nothing is mounted at /important_data. Did you forget to run important_data?")
        return
    if not os.path.exists("/backup"):
        RunCommand("mkdir /backup")
        RunCommand("chmod 777 /backup")
        RunCommand("chown root:root /backup")
    if len(os.listdir("/backup")) != 0:
        PrintError("/backup is not empty.")
        return 1
    if RunCommand("findmnt /backup", check=False) == 0:
        PrintError("Something is already mounted at /backup.")
    backup_dev, status_code = RunCommand("blkid --uuid b463d26d-23d8-4c12-8f4b-5be63fb1b2f3", check=False, capture=True)
    if status_code != 0:
        PrintError("backup drive is not connected to this PC.")
        return 1
    RunCommand(f"mount -t ext4 -o rw,noatime,discard,errors=remount-ro \"{backup_dev}\" /backup")
    RunCommand(f"mount -o ro,noatime,discard,errors=remount-ro,remount /important_data")
    RunCommand(f"rsync --verbose --archive --executability --acls --xattrs --atimes --open-noatime --delete-after --numeric-ids --human-readable --progress --sparse --hard-links /important_data/ /backup/", echo=True)
    RunCommand(f"mount -o rw,noatime,discard,errors=remount-ro,remount /important_data")
    RunCommand(f"umount /backup")
    print("Backup Complete!")
    return 0
sys.exit(Main())