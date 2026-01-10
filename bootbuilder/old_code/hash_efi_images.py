#!/bin/env python
import os
import subprocess
import struct
import pefile
import hashlib

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

def HashEFIImage(efi_image_path):
    efi_image = ReadFile(efi_image_path, binary=True)

    pe = pefile.PE(data=efi_image, fast_load=True)

    hasher = hashlib.new("sha256")

    checksum_offset = pe.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum")

    security_dir_entry_offset = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].get_field_absolute_offset("VirtualAddress")
    
    sig_pos = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].VirtualAddress
    sig_len = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size
    
    if sig_pos > 0 and sig_len > 0:
        file_end = sig_pos
        is_signed = True
    else:
        file_end = len(efi_image)
        is_signed = False

    hasher.update(efi_image[0:checksum_offset])
    hasher.update(efi_image[checksum_offset + 4:security_dir_entry_offset])
    hasher.update(efi_image[security_dir_entry_offset + 8:file_end])
    
    if not is_signed:
        remainder = file_end % 8
        if remainder > 0:
            padding_len = 8 - remainder
            hasher.update(b'\x00' * padding_len)

    return hasher.digest()
def WriteESL(signature_data, esl_path):
    print(signature_data.hex())
    signature_type = bytes.fromhex("2616c4c14c509240aca941f936934328") # EFI_CERT_SHA256_GUID
    signature_list_size = struct.pack("<I", 76) # SignatureHeaderSize + SignatureSize
    signature_header_size = struct.pack("<I", 28) # sizeof(EFI_SIGNATURE_LIST)
    signature_size = struct.pack("<I", 48) # sizeof(EFI_SIGNATURE_DATA) with 32 bytes for SignatureData
    signature_owner = bytes.fromhex("042c7081cc157345b5d4c3a476b635dc") # EOS_UUID
    esl_payload = signature_type + signature_list_size + signature_header_size + signature_size + signature_owner + signature_data
    WriteFile(esl_path, esl_payload, binary=True)

def Main():
    oprom_dir_path = os.path.realpath("./oproms")
    for efi_image_path in RunCommand(f"find \"{oprom_dir_path}\" -mindepth 1 -maxdepth 1 -type f -name \"*.efi\"", capture=True).splitlines():
        efi_image_hash = HashEFIImage(efi_image_path)
        esl_path = efi_image_path.removesuffix(".efi") + ".esl"
        WriteESL(efi_image_hash, esl_path)
Main()
