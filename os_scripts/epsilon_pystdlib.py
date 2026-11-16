#!/bin/env python

import subprocess
import os
import time
import json
import pwd
import grp
import datetime

# region Epsilon PYSTDLIB
def RealPath(filePath):
    return os.path.realpath(os.path.expanduser(filePath))
def GetScriptDir():
    return os.path.dirname(RealPath(__file__))
def InstallFile(filePath, contents, mode, user, group, binary=False):
    filePath = RealPath(filePath)
    uid = int(user[1:]) if user.startswith("+") else pwd.getpwnam(user).pw_uid
    gid = int(group[1:]) if group.startswith("+") else grp.getgrnam(group).gr_gid
    fd = os.open(filePath, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, mode)
    os.fchown(fd, uid, gid)
    os.fchmod(fd, mode)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def InstallDirectory(dirPath, mode, user, group):
    dirPath = RealPath(dirPath)
    uid = int(user[1:]) if user.startswith("+") else pwd.getpwnam(user).pw_uid
    gid = int(group[1:]) if group.startswith("+") else grp.getgrnam(group).gr_gid
    if not os.path.isdir(dirPath):
        os.mkdir(dirPath, mode)
    os.chown(dirPath, uid, gid)
    os.chmod(dirPath, mode)
def AppendFile(filePath, contents, binary=False):
    filePath = RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_APPEND)
    with open(fd, "ab" if binary else "a", encoding=None if binary else "utf-8") as f:
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
def SerializeJson(obj, compact=False):
    return json.dumps(obj, separators=(',', ':') if compact else None, indent=None if compact else 4)
def DeserializeJson(jsonString):
    return json.loads(jsonString)
def GetEpoch():
    return time.time()
def FormatEpoch(epoch):
    if epoch == float("inf") or epoch == float("-inf"):
        return "NONE_TIME"
    timestamp = datetime.datetime.fromtimestamp(epoch)
    return timestamp.strftime("%I:%M%p %m/%d").lower()
def RunCommand(command, echo=False, capture=False, noerr=False, input=None, check=True, env=None):
    if echo and capture:
        raise Exception("Command cannot be run with both echo and capture.")
    result = subprocess.run(command, stdout=(None if echo else subprocess.PIPE), stderr=(subprocess.DEVNULL if noerr else (None if echo else subprocess.STDOUT)), input=input, env=env, check=False, shell=True, text=True)
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
os.chdir(GetScriptDir())
# endregion
