#!/bin/env python
import fcntl
import os

WELL_KNOWN_VARS = {
    "BootOrder": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" },
    "BootCurrent": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x06\x00\x00\x00" },
    "BootNext": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" },
    "Timeout": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" },
    "BootOptionSupport": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x06\x00\x00\x00" },
    "SecureBoot": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x06\x00\x00\x00" },
    "SetupMode": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x06\x00\x00\x00" },
    "PK": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x27\x00\x00\x00" },
    "KEK": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x27\x00\x00\x00" },
    "db": { "guid": "d719b2cb-3d3a-4596-a3bc-dad00e67656f", "attributes": b"\x27\x00\x00\x00" },
    "dbx": { "guid": "d719b2cb-3d3a-4596-a3bc-dad00e67656f", "attributes": b"\x27\x00\x00\x00" },
    "OsIndications": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" },
    "OsIndicationsSupported": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x06\x00\x00\x00" },
    "PlatformLang": { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" },
}
WELL_KNOWN_BOOT_ENTRY = { "guid": "8be4df61-93ca-11d2-aa0d-00e098032b8c", "attributes": b"\x07\x00\x00\x00" }
def GetWellKnownVarInfo(var_name: str) -> dict[str, bytes]:
    if var_name in WELL_KNOWN_VARS:
        return WELL_KNOWN_VARS[var_name]
    if len(var_name) == 8 and var_name[:4] == "Boot" and all(c in "0123456789ABCDEF" for c in var_name[4:]):
        return WELL_KNOWN_BOOT_ENTRY
    raise Exception(f"Unknown efi var {var_name}.")
def ReadVar(var_name: str) -> bytes:
    var_info = GetWellKnownVarInfo(var_name)
    path = f"/sys/firmware/efi/efivars/{var_name}-{var_info["guid"]}"
    if not os.path.isfile(path):
        return b""
    fd = os.open(path, os.O_RDONLY)
    size = os.stat(fd).st_size
    buffer = os.read(fd, size)
    os.close(fd)
    if buffer[:4] != var_info["attributes"]:
        raise Exception(f"Bad attributes for {var_name} expected {var_info["attributes"]} got {buffer[:4]}.")
    return buffer[4:]
def WriteVar(var_name: str, value: bytes) -> None:
    FS_IOC_GETFLAGS = 0x80086601
    FS_IOC_SETFLAGS = 0x40086602
    
    var_info = GetWellKnownVarInfo(var_name)
    path = f"/sys/firmware/efi/efivars/{var_name}-{var_info["guid"]}"
    buffer = var_info["attributes"] + value
    
    old_attributes = None
    if os.path.exists(path):
        fd = os.open(path, os.O_RDONLY)
        old_attributes = bytearray(b"\x00\x00\x00\x00")
        fcntl.ioctl(fd, FS_IOC_GETFLAGS, old_attributes)
        new_attributes = bytearray(b"\x00\x00\x00\x00")
        fcntl.ioctl(fd, FS_IOC_SETFLAGS, new_attributes)
        os.close(fd)

    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.write(fd, buffer)
    os.close(fd)

    if old_attributes != None:
        fd = os.open(path, os.O_RDONLY)
        fcntl.ioctl(fd, FS_IOC_SETFLAGS, old_attributes)
        os.close(fd)
def GetBootIds() -> list[int]:
    var_paths = os.listdir("/sys/firmware/efi/efivars/")
    output = []
    for var_path in var_paths:
        if (len(var_path) == len("BootXXXX-8be4df61-93ca-11d2-aa0d-00e098032b8c")
            and var_path.startswith("Boot")
            and var_path.endswith("-8be4df61-93ca-11d2-aa0d-00e098032b8c")
            and all(c in "0123456789ABCDEF" for c in var_path[4:8])):
                output.append(int(var_path[4:8]))
    return output

def GetPlatformLang() -> str:
    buffer = ReadVar("PlatformLang")
    if buffer[-1:] == b"\x00":
        buffer = buffer[:-1]
    return buffer.decode(encoding="ascii")
def SetPlatformLang(value: str) -> None:
    buffer = value.encode(encoding="ascii")
    if not buffer[-1:] == b"\x00":
        buffer = buffer + b"\x00"
    WriteVar("PlatformLang", buffer)

WriteVar("OsIndications", b"\x01\x00\x00\x00\x00\x00\x00\x00")