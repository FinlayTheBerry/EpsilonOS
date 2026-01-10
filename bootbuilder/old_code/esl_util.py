import os
import subprocess
import struct

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


EFI_CERT_SHA256_GUID = bytes.fromhex("2616c4c14c509240aca941f936934328")

def WriteESL(signature_data, esl_path):
    signature_type =  # EFI_CERT_SHA256_GUID
    signature_list_size = struct.pack("<I", 76) # SignatureHeaderSize + SignatureSize
    signature_header_size = struct.pack("<I", 28) # sizeof(EFI_SIGNATURE_LIST)
    signature_size = struct.pack("<I", 48) # sizeof(EFI_SIGNATURE_DATA) with 32 bytes for SignatureData
    signature_owner = bytes.fromhex("042c7081cc157345b5d4c3a476b635dc") # EOS_UUID
    esl_payload = signature_type + signature_list_size + signature_header_size + signature_size + signature_owner + signature_data
    WriteFile(esl_path, esl_payload, binary=True)