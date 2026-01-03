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

# Types of .backup files:
# ignorerepos.backup: Tells this script not to commit, push, or warn about no remote for the git repo in the given folder.
# ignorecode.backup: Tells this script to silence warnings about unprotected code in the given folder recursively.
#
# To audit .backup files:
# find /important_data/ -type f -name "*.backup"

def Main():
    # Initial scanity checks
    if os.geteuid() == 0 or os.getegid() == 0:
        script_name = os.path.splitext(os.path.basename(os.path.realpath(__file__)))[0]
        PrintError(f"{script_name} may not be run as root. Please try again.")
        return 1
    if RunCommand(f"git config user.name", capture=True, check=False)[0] == "":
        PrintError("Git username not set. Please run: git config --global user.name \"Your Name\"")
        return 1
    if RunCommand(f"git config user.email", capture=True, check=False)[0] == "":
        PrintError("Git email not set. Please run: git config --global user.email \"Your Email\"")
        return 1
    if RunCommand(f"git config push.autoSetupRemote", capture=True, check=False)[0] != "true":
        PrintError("Git is not configured with auto setup remote. Please run: git config --global push.autoSetupRemote true")
        return 1
    if RunCommand(f"git config branch.autoSetupMerge", capture=True, check=False)[0] != "always":
        PrintError("Git is not configured with auto setup merge. Please run: git config --global branch.autoSetupMerge always")
        return 1
    sshStatusEndMarker = "! You've successfully authenticated, but GitHub does not provide shell access."
    sshStatusStartMarker = "Hi "
    sshStatus = RunCommand(f"ssh git@github.com", capture=True, check=False)[0]
    sshStatusEndMarkerPos = sshStatus.find(sshStatusEndMarker)
    sshStatusStartMarkerPos = sshStatus.rfind(sshStatusStartMarker, 0, sshStatusEndMarkerPos)
    if sshStatusEndMarkerPos == -1 or sshStatusStartMarkerPos == -1:
        PrintError("ssh doesn't seem to be properly setup. git@github.com refused authentication.")
        return 1
    githubUsername = sshStatus[sshStatusStartMarkerPos + len(sshStatusStartMarker):sshStatusEndMarkerPos]

    # Enumerating files and folders
    print("Locating repos...")
    repo_paths = [ os.path.dirname(repo_path) for repo_path in RunCommand(f"find \"/important_data/\" -type d -name \".git\"", capture=True).splitlines() ]
    print()
    
    # Committing and pushing git repos
    print("Committing and pushing all repos...")
    for i in range(len(repo_paths)):
        print(f"{i} of {len(repo_paths)}...")
        repo_path = repo_paths[i]
        os.chdir(repo_path)
        remote = RunCommand("git remote", capture=True)
        if remote == "":
            PrintError(f"Repo \"{repo_path}\" has a no origin.")
            continue
        origin = RunCommand(f"git remote get-url \"{remote}\"", capture=True)
        if not origin.startswith(f"git@github.com:{githubUsername}/") or not origin.endswith(".git"):
            PrintWarning(f"Repo \"{repo_path}\" has a bad origin \"{origin}\".")
            continue
        if not os.path.isfile(os.path.join(repo_path, ".gitignore")):
            PrintError(f"Repo \"{repo_path}\" has no .gitignore.")
            continue
        changes = RunCommand(f"git status --porcelain", capture=True)
        if changes != "":
            print(f"Committing and pushing changes to \"{repo_path}\"...")
            RunCommand(f"git rm --cached -r .", check=False) # Ignore status as this fails when nothing is tracked currently
            RunCommand(f"git add --all")
            RunCommand(f"git commit -m\"Auto-generated backup commit.\"")
        RunCommand(f"git push origin --all")

    print("Backup Complete!")
    return 0
sys.exit(Main())