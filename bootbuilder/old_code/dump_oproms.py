#!/bin/env python
import subprocess
import os

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
def RunCommand(command, echo=False, capture=False, input=None, check=True):
    result = subprocess.run(command, capture_output=(not echo), input=input, check=check, shell=True, text=True)
    if capture and not check:
        return (result.stdout + result.stderr).strip(), result.returncode
    elif capture:
        return (result.stdout + result.stderr).strip()
    elif not check:
        return result.returncode
    else:
        return
def PrintWarning(message):
    print(f"\033[93mWarning: {message}\033[0m")
def PrintError(message):
    print(f"\033[91mERROR: {message}\033[0m")

def Main():
    oprom_dir_path = os.path.realpath("./oproms")
    RunCommand(f"mkdir -p \"{oprom_dir_path}\"")
    for rom_path in RunCommand("find -L /sys/bus/pci/devices/ -mindepth 2 -maxdepth 2 -type f -name rom", capture=True).splitlines():
        device_id = rom_path.removeprefix("/sys/bus/pci/devices/").removesuffix("/rom")
        print(f"Dumping option rom for {RunCommand(f"lspci -s {device_id}", capture=True)}")
        WriteFile(rom_path, "1")
        try:
            oprom = ReadFile(rom_path, binary=True)
            WriteFile(os.path.join(oprom_dir_path, f"{device_id}.rom"), oprom, binary=True)
        except OSError as ex:
            if ex.errno == 5:
                print("Option ROM returned an IO error. This usually happens when the PCI device doesn't actually have an option ROM and is safe to ignore.")
                continue
            else:
                raise
        finally:
            WriteFile(rom_path, "0")
Main()