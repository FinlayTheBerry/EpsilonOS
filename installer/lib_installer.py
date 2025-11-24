import subprocess
import os
import requests

def WriteFile(filePath, contents, binary=False):
    filePath = os.path.abspath(filePath)
    dirPath = os.path.dirname(filePath)
    os.makedirs(dirPath, exist_ok=True)
    with open(filePath, "wb" if binary else "w", encoding=(None if binary else "UTF-8")) as file:
        file.write(contents)

def ReadFile(filePath, defaultContents=None, binary=False):
    filePath = os.path.abspath(filePath)
    if not os.path.exists(filePath):
        if defaultContents != None:
            return defaultContents
    with open(filePath, "rb" if binary else "r", encoding=(None if binary else "UTF-8")) as file:
        return file.read()

def RunCommand(command, echo=False, capture=False, input=None, check=True, env=None):
    result = subprocess.run(command, capture_output=(not echo), input=input, check=check, shell=True, text=True,)
    if capture:
        return result.stdout.strip()
    else:
        return result.returncode

def Choice(prompt=None):
    if prompt == None:
        print("(Y)es or (N)o: ", end="")
    else:
        print(f"{prompt} (Y)es/(N)o: ", end="")
    while True:
        userChoice = input().lower()
        if userChoice == "y" or userChoice == "yes" or userChoice == "(y)es":
            return True
        elif userChoice == "n" or userChoice == "no" or userChoice == "(n)o":
            return False
        else:
            print(f"{userChoice} is not a valid choice. Please enter (Y)es or (N)o: ")

RequiredPackageNames = set()
def RequirePackage(packageName):
    global RequiredPackageNames
    RequiredPackageNames.add(packageName)

def AssertPacmanPacs():
    global RequiredPackageNames
    installedPackages = RunCommand("pacman -Qq", capture=True).splitlines()
    missingPackages = set()
    for neededPackage in RequiredPackageNames:
        if not neededPackage in installedPackages:
            missingPackages.add(neededPackage)
    if len(missingPackages) > 0:
        raise Exception(f"Missing needed pacman package/s {" ".join(missingPackages)}")

def AssertRoot():
    if RunCommand("id -u", capture=True) != "0" or RunCommand("id -g", capture=True) != "0":
        raise Exception("The EOS installer must be run as root.")

def AssertInternet():
    try:
        response = requests.get("http://clients3.google.com/generate_204")
        response.raise_for_status()
    except:
        raise Exception("An internet connection is required to install EOS. You may need to setup WiFi.")

def Assertx64():
    if RunCommand("uname -m", capture=True).strip() != "x86_64":
        raise Exception("A 64 bit CPU is required to install EOS.")
    
def AssertEfi():
    if not os.path.isdir("/sys/firmware/efi"):
        raise Exception("A motherboard with EFI support is required to install EOS. Check if your BIOS is set to legacy CSM mode.")

def PrintError(message, end=None):
    print(f"\033[0m\033[31mERROR: {message}\033[0m", end=end)

def PrintWarning(message, end=None):
    print(f"\033[0m\033[33mWarning: {message}\033[0m", end=end)

RequirePackage("util-linux") # uname id