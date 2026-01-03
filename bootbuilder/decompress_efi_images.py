#!/bin/env python
import os
import subprocess
import importlib.util

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

def ImportEfiCompressor():
    efi_compressor_so_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "EfiCompressor.so"))
    if not os.path.exists(efi_compressor_so_path):
        raise Exception(f"File not found at \"{efi_compressor_so_path}\".")
    efi_compressor_spec = importlib.util.spec_from_file_location("EfiCompressor", efi_compressor_so_path)
    if efi_compressor_spec == None:
        raise Exception(f"Could not create module spec for EfiCompressor.")
    efi_compressor_module = importlib.util.module_from_spec(efi_compressor_spec)
    efi_compressor_spec.loader.exec_module(efi_compressor_module)
    return efi_compressor_module
EfiCompressor = ImportEfiCompressor()

def DecompressEFIImage(efi_image_path, efi_program_path):
    efi_image = ReadFile(efi_image_path, binary=True)
    efi_program = EfiCompressor.UefiDecompress(efi_image, len(efi_image)).tobytes()
    if len(efi_program) == 0:
        PrintError(f"Failed to decompress \"{efi_image_path}\".")
        return
    WriteFile(efi_program_path, efi_program, binary=True)
    print(f"Decompressed EFI image from {efi_image_path} to {efi_program_path}.")

def Main():
    oprom_dir_path = os.path.realpath("./oproms")
    for efi_image_path in RunCommand(f"find \"{oprom_dir_path}\" -mindepth 1 -maxdepth 1 -type f -name \"*.efi.img\"", capture=True).splitlines():
        efi_program_path = efi_image_path.removesuffix(".img")
        DecompressEFIImage(efi_image_path, efi_program_path)
Main()

"""
Updating EFI Compressor:
Go to https://pypi.org/project/EfiCompressor/#files and download the latest "EfiCompressor-0.7.tar.gz"
Extract with "tar -xzf EfiCompressor-0.7.tar.gz".
Remove the tarball with "rm EfiCompressor-0.7.tar.gz"
Switch directories with "cd EfiCompressor-0.7"
Compile with "python setup.py build"
"""