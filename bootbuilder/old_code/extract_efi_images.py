#!/bin/env python
import struct
from types import SimpleNamespace
import os
import subprocess

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

def ReadHeader(buffer, index):
    HEADER_FORMAT = '<BBHIH H10s HH'
    HEADER_SIZE = 24 
    if index < 0 or index + HEADER_SIZE > len(buffer):
        return None
    try:
        unpacked = struct.unpack_from(HEADER_FORMAT, buffer, index)
        return SimpleNamespace(
            sig1=unpacked[0],
            sig2=unpacked[1],
            init_size=unpacked[2],
            header_sig=unpacked[3],
            efi_subsys=unpacked[4],
            efi_machine=unpacked[5],
            resv=unpacked[6],
            efi_offset=unpacked[7],
            pcir_offset=unpacked[8]
        )
    except:
        return None
def ReadPCIR(buffer, index):
    PCIR_FORMAT = '<4s H H H H B 3s H H B B H H H'
    PCIR_SIZE = 28 
    if index < 0 or index + PCIR_SIZE > len(buffer):
        return None
    try:
        unpacked = struct.unpack_from(PCIR_FORMAT, buffer, index)
        return SimpleNamespace(
            sig=unpacked[0],
            vendor=unpacked[1],
            device=unpacked[2],
            device_list=unpacked[3],
            pcir_length=unpacked[4],
            pcir_rev=unpacked[5],
            class_bytes=unpacked[6],
            image_length=unpacked[7],
            rom_rev=unpacked[8],
            type=unpacked[9],
            last=unpacked[10],
            runtime_length=unpacked[11],
            config_header=unpacked[12],
            dmtf_entry=unpacked[13]
        )
    except:
        return None
def ExtractEFIImage(rom_path, efi_image_path):
    ROM_BLOCK_SIZE = 512

    rom_data = ReadFile(rom_path, binary=True)
    rom_size = os.path.getsize(rom_path)
    offset = 0

    while offset < rom_size:
        header = ReadHeader(rom_data, offset)
        if header == None or header.sig1 != 0x55 or header.sig2 != 0xAA:
            raise Exception(f"Invalid ROM header at {hex(offset)}.")

        pcir_address = offset + header.pcir_offset
        pcir = ReadPCIR(rom_data, pcir_address)
        if pcir == None or pcir.sig != b"PCIR":
            raise Exception(f"Invalid PCIR header at {hex(pcir_address)}.")

        if pcir.type != 3:
            offset += pcir.image_length *- ROM_BLOCK_SIZE
            continue

        efi_image_start = offset + header.efi_offset
        efi_image_end = efi_image_start + pcir.image_length * ROM_BLOCK_SIZE
        if efi_image_end > rom_size:
            efi_image_end = rom_size

        efi_image = rom_data[efi_image_start:efi_image_end]
        WriteFile(efi_image_path, efi_image, binary=True)
        print(f"Extracted EFI image from {rom_path} to {efi_image_path}.")
        return
    raise Exception("No EFI image found in this Option ROM.")

def Main():
    oprom_dir_path = os.path.realpath("./oproms")
    for rom_path in RunCommand(f"find \"{oprom_dir_path}\" -mindepth 1 -maxdepth 1 -type f -name \"*.rom\"", capture=True).splitlines():
        output_path = rom_path.removesuffix(".rom") + ".efi.compressed"
        ExtractEFIImage(rom_path, output_path)
Main()