## Mounting Efivars Filesystem
User space programs like easysb cannot talk directly with the UEFI firmware. Instead they read and write to files in `/sys/firmware/efi/efivars` to instruct the linux kernel to send requests to the UEFI on their behalf. If this filesystem is not mounted or not availible these requests may fail. To fix this try running `mount -t efivarfs none /sys/firmware/efi/efivars`. If that doesn't work then your system may not support UEFI or efivarfs kernel module may not be loaded. Try `modprobe efivarfs`. Additionally lots of the files in `/sys/firmware/efi/efivars` have the immutable attribute. This is intentional to prevent accidentally writting to important vars and damaging the UEFI but if you are sure you can easily remove this safeguard with `chattr -i /sys/firmware/efi/efivars/NAME-GUID`.

<br />

## EFI Var Basics
Every efi var contains a value, a vendor guid, and attributes. The vendor guid is appended to the filename so paths look like this `/sys/firmware/efi/efivars/NAME-GUID`. The vendor guid can either be one of the predefined values in the UEFI spec indicating a standard variable or a custom guid indicating an extra variable added by the motherboard manufacture. Attributes are stored inside the efi var file and take up the first 4 bytes. These attributes will need to be removed from the start of the file contents before working with the variable but note that the attributes must be prepended to the value before writting it back to the file. Additionally it's worth noting that all values in the UEFI have the same endianness as the CPU. So in 99% of cases values will be little endian. The UEFI spec defines the following builtin vendor guids, and variable attributes:
```
EFI_GUID EOS_UEFI_GUID = {}
```
```
uint32_t EFI_VARIABLE_NON_VOLATILE = 0x00000001;
uint32_t EFI_VARIABLE_BOOTSERVICE_ACCESS = 0x00000002;
uint32_t EFI_VARIABLE_RUNTIME_ACCESS = 0x00000004;
uint32_t EFI_VARIABLE_HARDWARE_ERROR_RECORD = 0x00000008;
uint32_t EFI_VARIABLE_AUTHENTICATED_WRITE_ACCESS = 0x00000010; // Deprecated
uint32_t EFI_VARIABLE_TIME_BASED_AUTHENTICATED_WRITE_ACCESS = 0x00000020;
uint32_t EFI_VARIABLE_APPEND_WRITE = 0x00000040;
uint32_t EFI_VARIABLE_ENHANCED_AUTHENTICATED_ACCESS = 0x00000080;
```
```
struct for "/sys/firmware/efi/efivars/*" {
	uint32_t attributes;
	uint8_t value[ANY_SIZE];
}
```

<br />

## Basic Boot Sequence
The boot order stored in the UEFI is not too complex. First there are the boot entries themselves. Each boot entry has an id which is a 16 bit unsigned integer. Each boot entry is stored in a variable named "BootXXXX" where XXXX stands in for the hexadecimal representation of that boot entry's id. For example entry number 3 is stored at "/sys/firmware/efi/efivars/Boot0003-8be4df61-93ca-11d2-aa0d-00e098032b8c". In addition to the boot entries the BootOrder variable stores a list of boot ids in order so the UEFI knows which boot entries to boot first and which are the fall backs. After the UEFI chooses a boot entry to load it saves that entry's' boot id into the BootCurrent variable. Normally to change which boot loader is executed you would place the boot entry ids in a different order within BootOrder however for a one time override you can instead place the target boot entry's id into BootNext which will set that boot entry as the chosen one for the next boot, however after one boot the variable will be deleted so this is not a perminant change. The Timeout variable stores the integer number of seconds that the UEFI will wait before loading the chosen boot entry. Finally the BootOptionSupport variable stores a bitwise combination of the following feature flags indicating weather they are supported:
uint32_t EFI_BOOT_OPTION_SUPPORT_KEY = 0x00000001;
uint32_t EFI_BOOT_OPTION_SUPPORT_APP = 0x00000002;
uint32_t EFI_BOOT_OPTION_SUPPORT_SYSPREP = 0x00000010;
uint32_t EFI_BOOT_OPTION_SUPPORT_COUNT = 0x00000300;
struct for "/sys/firmware/efi/efivars/BootOrder-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	uint16_t boot_entry_ids_in_order[ANY_SIZE];
}
struct for "/sys/firmware/efi/efivars/BootNext-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	uint16_t next_boot_entry_id;
}
struct for "/sys/firmware/efi/efivars/BootCurrent-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000006;
	uint16_t current_boot_entry_id;
}
struct for "/sys/firmware/efi/efivars/Timeout-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	uint16_t boot_delay_in_seconds;
}
struct for "/sys/firmware/efi/efivars/BootOptionSupport-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000006;
	uint32_t boot_option_supported_features;
}

<br />

## Boot Entries (NEEDS TO BE EXPANDED)
The boot entries themselves have a more complex structure as they store important data about where the .efi bootloader is stored. 

struct for "/sys/firmware/efi/efivars/BootXXXX-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	uint32_t load_attributes;
    uint16_t path_list_length; // sizeof(path_list) only that array included
	char16_t boot_entry_name[ANY_SIZE]; // Null terminated
	struct {
		uint16_t path_type;
    	uint16_t length; // sizeof(path_list[i]) includes entire struct
		uint8_t payload[ANY_SIZE];
	} path_list[ANY_SIZE];
    uint8_t extra_data[ANY_SIZE]; // Passed as arguments to binary
}

uint32_t LOAD_OPTION_ACTIVE = 0x00000001;
uint32_t LOAD_OPTION_FORCE_RECONNECT = 0x00000002;
uint32_t LOAD_OPTION_HIDDEN = 0x00000008;
uint32_t LOAD_OPTION_CATEGORY = 0x00001F00;
uint32_t LOAD_OPTION_CATEGORY_BOOT = 0x00000000;
uint32_t LOAD_OPTION_CATEGORY_APP = 0x00000100;

uint16_t PATH_TYPE_PCI = 0x0101;
uint16_t PATH_TYPE_PCCard = 0x0102;
uint16_t PATH_TYPE_MMAP = 0x0103;
uint16_t PATH_TYPE_Vendor = 0x0104;
uint16_t PATH_TYPE_Controller = 0x0105;
uint16_t PATH_TYPE_BMC = 0x0106;
uint16_t PATH_TYPE_ACPI = 0x0201;
uint16_t PATH_TYPE_ACPI_Ex = 0x0202;
uint16_t PATH_TYPE_ACPI_ADR = 0x0203;
uint16_t PATH_TYPE_ACPI_NVDIMM = 0x0204;
uint16_t PATH_TYPE_ATAPI = 0x0301;
uint16_t PATH_TYPE_SCSI = 0x0302;
uint16_t PATH_TYPE_Fibre = 0x0303;
uint16_t PATH_TYPE_Fibre_Ex = 0x0304;
uint16_t PATH_TYPE_1394 = 0x0305;
uint16_t PATH_TYPE_USB = 0x0306;
uint16_t PATH_TYPE_I2O = 0x0307;
uint16_t PATH_TYPE_Infiniband = 0x0308;
uint16_t PATH_TYPE_Vendor_Messaging = 0x0309;
uint16_t PATH_TYPE_MAC = 0x030A;
uint16_t PATH_TYPE_IPv4 = 0x030B;
uint16_t PATH_TYPE_IPv6 = 0x030C;
uint16_t PATH_TYPE_UART = 0x030D;
uint16_t PATH_TYPE_USB_Class = 0x030E;
uint16_t PATH_TYPE_USB_WWID = 0x030F;
uint16_t PATH_TYPE_Logical_Unit = 0x0310;
uint16_t PATH_TYPE_Sata = 0x0311;
uint16_t PATH_TYPE_USB_Ex = 0x0312;
uint16_t PATH_TYPE_SD = 0x0313;
uint16_t PATH_TYPE_eMMC = 0x0314;
uint16_t PATH_TYPE_Bluetooth = 0x0315;
uint16_t PATH_TYPE_WiFi = 0x0316;
uint16_t PATH_TYPE_eNIC = 0x0317;
uint16_t PATH_TYPE_UFS = 0x0318;
uint16_t PATH_TYPE_NVMe = 0x0319;
uint16_t PATH_TYPE_RoN = 0x031A;
uint16_t PATH_TYPE_Hard_Drive = 0x0401;
struct for PATH_TYPE_Hard_Drive {
	uint32_t partition_number; // 0 means whole device
	uint64_t partition_start; // LBA of the partition start within the drive
	uint64_t partition_size; // Size in logical blocks
	uint128_t signature; // signature_type 0 = all zeros, signature_type 1 = 4 bytes from MBR and the rest zeros, signature_type 2 = UUID from GPT
	uint8_t MBR_type; // 0x01 = PC-AT legacy MBR, 0x02 = GPT GUID
	uint8_t signature_type; // 0x00 = None, 0x01 = uint32_t signature from 0x01b8 on an MBR drive, 0x02 = GPT partition GUID
}
uint16_t PATH_TYPE_CDROM = 0x0402;
uint16_t PATH_TYPE_Vendor_Media = 0x0403;
uint16_t PATH_TYPE_File_Path = 0x0404;
struct for PATH_TYPE_File_Path {
	char16_t path[ANY_SIZE]; // Null terminated
}
uint16_t PATH_TYPE_Media_Protocol = 0x0405;
uint16_t PATH_TYPE_PIWG_File = 0x0406;
uint16_t PATH_TYPE_PIWG_Volume = 0x0407;
uint16_t PATH_TYPE_Relative_Offset_Range = 0x0408;
uint16_t PATH_TYPE_RAM_Disk = 0x0409;
uint16_t PATH_TYPE_BBS = 0x0501;
uint16_t PATH_TYPE_END_Instance = 0x7F01;
uint16_t PATH_TYPE_END = 0x7FFF;
struct for PATH_TYPE_END {
	// No fields empty payload
}

<br />

## Basic Secure Boot  (NEEDS TO BE EXPANDED)
Secure boot is a collection of settings which govern what binaries are allowed to be executed by the UEFI firmware. It's important to note secure boot only controls what the UEFI will execute. Once an OS loads that OS can run programs and drivers without needing furthar approval from the UEFI or secure boot. Secure boot depends upon a higharchy of keys and digital signatures. At the top is the platform key PK. This key can only be set when the platform key is empty. When the platform key is empty the system is said to be in setup mode. From setup mode you can make a one time request to set the PK. After being set the system leaves setup mode and the OS cannot modify the PK without assistance from the user manually entering the UEFI settings menu and clearing the current PK. Having the OS reset the PK later on is impossible by design for security reasons. With access to the private portion of the PK an OS can sign an update to KEK which is the next certificate in the chain. Then with access to KEK an OS can sign updates to db and dbx which are the lowest level of keys. This three layer higharchy exists for the following reason. PK is a single cert with all the power. Unlike PK KEK can contain multiple certs and allows you to create a list of people or OSes you trust enough to let them manage your secure boot keys. db and dbx are used to store allowed bootloader certificates and hashes as well as revoked or banned certificates and hashes. db and dbx are opposites and dbx always takes priorety over db.
struct for "/sys/firmware/efi/efivars/PK-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000027;
	ESL value;
}
struct for "/sys/firmware/efi/efivars/KEK-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000027;
	ESL value;
}
struct for "/sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f" {
	uint32_t attributes = 0x00000027;
	ESL value;
}
struct for "/sys/firmware/efi/efivars/dbx-d719b2cb-3d3a-4596-a3bc-dad00e67656f" {
	uint32_t attributes = 0x00000027;
	ESL value;
}
struct for "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000006;
	uint8_t secure_boot_enabled; // value != 0
}
struct for "/sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000006;
	uint8_t in_setup_mode_enabled; // value != 0	
}

<br />

## EFI Signature Lists (NEEDS TO BE EXPANDED)

<br />

## Authenticated Writes (NEEDS TO BE EXPANDED)

<br />

## Os Indications
The OsIndications variable is a set of flags that the OS can set to indicate it's intent to the UEFI. Think of this as a place where the OS can ask the UEFI firmware to do something by setting flags. The main use case for OsIndications is to instruct the UEFI to boot into the firmware settings menu on the next boot for a convenient way to enter the UEFI BIOS settings. First we must read the OsIndicationsSupported variable and check the bit coorisponding to the flag we want to use. If that bit is 1 then the flag is supported and we are good to go if not then the flag is unsupported and should be left as 0. To set a flag we simply write the new values for all the flags into OsIndications as a 64 bit value. Below is a list of all the flags defined in the UEFI specification:
uint64_t EFI_OS_INDICATIONS_BOOT_TO_FW_UI = 0x0000000000000001;
uint64_t EFI_OS_INDICATIONS_TIMESTAMP_REVOCATION = 0x0000000000000002;
uint64_t EFI_OS_INDICATIONS_FILE_CAPSULE_DELIVERY_SUPPORTED = 0x0000000000000004;
uint64_t EFI_OS_INDICATIONS_FMP_CAPSULE_SUPPORTED = 0x0000000000000008;
uint64_t EFI_OS_INDICATIONS_CAPSULE_RESULT_VAR_SUPPORTED = 0x0000000000000010;
uint64_t EFI_OS_INDICATIONS_START_OS_RECOVERY = 0x0000000000000020;
uint64_t EFI_OS_INDICATIONS_START_PLATFORM_RECOVERY = 0x0000000000000040;
uint64_t EFI_OS_INDICATIONS_JSON_CONFIG_DATA_REFRESH = 0x0000000000000080;
struct for "/sys/firmware/efi/efivars/OsIndications-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	uint64_t os_indications;
}
struct for "/sys/firmware/efi/efivars/OsIndicationsSupported-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000006;
	uint64_t supported_os_indications;
}

<br />

## Platform Language
To get the language and country locale from the UEFI firmware we can read the contents of the PlatformLang variable. Inside this var is a null terminated string containing the locale value (for example en-us). These values are standardized under ISO 639.
struct for "/sys/firmware/efi/efivars/PlatformLang-8be4df61-93ca-11d2-aa0d-00e098032b8c" {
	uint32_t attributes = 0x00000007;
	char8_t locale[ANY_SIZE]; // Null terminated
}