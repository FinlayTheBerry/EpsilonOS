#!/usr/bin/python3
import subprocess
import os
import sys
import struct

# Dependencies:
# python3
# findmnt
# find
# chattr
# mkinitcpio
# chmod
# chown
# rm
# mkdir
# zstd
# file
# ukify
# cp
# efibootmgr
# openssl
# cert-to-efi-sig-list
# hash-to-efi-sig-list
# sign-efi-sig-list
# filefrag

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

# ----------------------------------------------------------------------------------------------
# The following region contains code copied/adapted from https://github.com/keylime/python3-uefi-eventlog/
# The following region is licensed under version 2.0 of the Apache License.
# You may obtain a copy of the license at https://raw.githubusercontent.com/keylime/python3-uefi-eventlog/refs/heads/main/LICENSE
# The following region was minified using https://python-minifier.com/
# ----------------------------------------------------------------------------------------------
# region TPM2 EventLog
import enum,hashlib,re,struct,uuid
def nullterm8(buffer):return buffer.decode("utf-8").split("\x00")[0]
def nullterm16(buffer):return buffer.decode("utf-16").split("\x00")[0]
class Event(enum.IntEnum):
	EV_PREBOOT_CERT=0;EV_POST_CODE=1;EV_UNUSED=2;EV_NO_ACTION=3;EV_SEPARATOR=4;EV_ACTION=5;EV_EVENT_TAG=6;EV_S_CRTM_CONTENTS=7;EV_S_CRTM_VERSION=8;EV_CPU_MICROCODE=9;EV_PLATFORM_CONFIG_FLAGS=10;EV_TABLE_OF_DEVICES=11;EV_COMPACT_HASH=12;EV_IPL=13;EV_IPL_PARTITION_DATA=14;EV_NONHOST_CODE=15;EV_NONHOST_CONFIG=16;EV_NONHOST_INFO=17;EV_OMIT_BOOT_DEVICE_EVENTS=18;EV_EFI_EVENT_BASE=2147483648;EV_EFI_VARIABLE_DRIVER_CONFIG=EV_EFI_EVENT_BASE+1;EV_EFI_VARIABLE_BOOT=EV_EFI_EVENT_BASE+2;EV_EFI_BOOT_SERVICES_APPLICATION=EV_EFI_EVENT_BASE+3;EV_EFI_BOOT_SERVICES_DRIVER=EV_EFI_EVENT_BASE+4;EV_EFI_RUNTIME_SERVICES_DRIVER=EV_EFI_EVENT_BASE+5;EV_EFI_GPT_EVENT=EV_EFI_EVENT_BASE+6;EV_EFI_ACTION=EV_EFI_EVENT_BASE+7;EV_EFI_PLATFORM_FIRMWARE_BLOB=EV_EFI_EVENT_BASE+8;EV_EFI_HANDOFF_TABLES=EV_EFI_EVENT_BASE+9;EV_EFI_PLATFORM_FIRMWARE_BLOB2=EV_EFI_EVENT_BASE+10;EV_EFI_HANDOFF_TABLES2=EV_EFI_EVENT_BASE+11;EV_EFI_VARIABLE_BOOT2=EV_EFI_EVENT_BASE+12;EV_EFI_VARIABLE_AUTHORITY=EV_EFI_EVENT_BASE+224;EV_UNKNOWN=4294967295
	@staticmethod
	def int2evt(evtnum):
		try:return Event(evtnum)
		except ValueError:return Event.EV_UNKNOWN
class Digest(enum.IntEnum):
	sha1=4;sha256=11;sha384=12;sha512=13;sha3_224=39;sha3_256=40;sha3_512=41
	@staticmethod
	def int2digest(algid):
		try:return Digest(algid)
		except ValueError:return Digest.sha1
class EfiEventDigest:
	hashalgmap={Digest.sha1:hashlib.sha1,Digest.sha256:hashlib.sha256,Digest.sha384:hashlib.sha384,Digest.sha512:hashlib.sha512}
	def __init__(self,algid,buffer,idx):self.algid=algid;self.hashalg=EfiEventDigest.hashalgmap[self.algid]();self.digest_size=self.hashalg.digest_size;self.digest=buffer[idx:idx+self.digest_size]
	def to_json(self):return{"AlgorithmId":self.algid.name,"Digest":self.digest.hex()}
	@staticmethod
	def parse_list(digest_count,buffer,idx):
		digests={}
		for _ in range(digest_count):algid,=struct.unpack("<H",buffer[idx:idx+2]);digest=EfiEventDigest(Digest(algid),buffer,idx+2);digests[algid]=digest;idx+=2+digest.digest_size
		return digests,idx
class EventHeader:
	def __init__(self):self.evtype=Event.int2evt(0);self.evpcr=-1;self.digests={};self.evsize=0;self.evidx=0
	@staticmethod
	def parse_pcrevent(buffer,evidx,idx):hdr=EventHeader();hdr.evidx=evidx;hdr.evpcr,evtype,digestbuf,hdr.evsize=struct.unpack("<II20sI",buffer[idx:idx+32]);hdr.evtype=Event.int2evt(evtype);hdr.digests={4:EfiEventDigest(Digest(4),digestbuf,0)};return hdr,idx+32
	@staticmethod
	def parse_pcrevent2(buffer,evidx,idx):hdr=EventHeader();hdr.evidx=evidx;hdr.evpcr,evtype,digest_count=struct.unpack("<III",buffer[idx:idx+12]);hdr.digests,idx=EfiEventDigest.parse_list(digest_count,buffer,idx+12);hdr.evsize,=struct.unpack("<I",buffer[idx:idx+4]);hdr.evtype=Event.int2evt(evtype);return hdr,idx+4
class GenericEvent:
	def __init__(self,evtheader,buffer,idx):self.evpcr=evtheader.evpcr;self.digests=evtheader.digests;self.evsize=evtheader.evsize;self.evidx=evtheader.evidx;self.evtype=evtheader.evtype;self.evbuf=buffer[idx:idx+self.evsize]
	@classmethod
	def parse(cls,evt_header,buffer,idx):return cls(evt_header,buffer,idx)
	def validate(self):return True,""
	def to_json(self):return{"EventType":self.evtype.name,"EventNum":self.evidx,"PCRIndex":self.evpcr,"EventSize":self.evsize,"DigestCount":len(self.digests),"Digests":list(self.digests.values()),"Event":self.evbuf[:1024].hex()}
class ValidatedEvent(GenericEvent):
	def validate(self):
		for(algid,refdigest)in self.digests.items():
			calchash1=EfiEventDigest.hashalgmap[algid](self.evbuf).digest()
			if refdigest.digest!=calchash1:return False,str(self.evtype.name)
		return True,""
class PostCodeEvent(GenericEvent):
	def __init__(self,evt_header,buffer,idx):
		super().__init__(evt_header,buffer,idx)
		if self.evsize==16:self.blobBase,self.blobLength=struct.unpack("<QQ",buffer[idx:idx+16])
		else:self.blobBase=None;self.blobLength=None
	def to_json(self):
		if self.blobBase is not None:evt={"BlobBase":self.blobBase,"BlobLength":self.blobLength}
		else:evt=self.evbuf.decode("utf-8")
		return{**super().to_json(),"Event":evt}
class FirmwareBlobEvent(GenericEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.base,self.length=struct.unpack("<QQ",buffer[idx:idx+16])
	def to_json(self):return{**super().to_json(),"Event":{"BlobBase":self.base,"BlobLength":self.length}}
class EfiIPLEvent(GenericEvent):
	def to_json(self):return{**super().to_json(),"Event":{"String":nullterm8(self.evbuf[:-1])}}
class SpecIdEvent(GenericEvent):
	def __init__(self,evt_header,buffer,idx):
		super().__init__(evt_header,buffer,idx);self.signature,self.platformClass,self.specVersionMinor,self.specVersionMajor,self.specErrata,self.uintnSize,self.numberOfAlgorithms=struct.unpack("<16sIBBBBI",buffer[idx+0:idx+28]);idx+=28;self.alglist=[]
		for i in range(self.numberOfAlgorithms):algid,digsize=struct.unpack("<HH",buffer[idx:idx+4]);idx+=4;alg=Digest.int2digest(algid);self.alglist.append((i,alg,digsize))
		self.vendorInfoSize,=struct.unpack("<I",buffer[idx:idx+4]);self.vendorInfo=buffer[idx+4:idx+4+self.vendorInfoSize]
	def to_json(self):
		j=super().to_json();del j["DigestCount"];del j["Digests"];del j["Event"];algorithms=[]
		for alg in self.alglist:algorithms.append({f"Algorithm[{alg[0]}]":None,"algorithmId":alg[1].name,"digestSize":alg[2]})
		j["Digest"]=self.digests[Digest.sha1].digest.hex();j["SpecID"]=[{"Signature":nullterm8(self.signature),"platformClass":self.platformClass,"specVersionMinor":self.specVersionMinor,"specVersionMajor":self.specVersionMajor,"specErrata":self.specErrata,"uintnSize":self.uintnSize,"vendorInfoSize":self.vendorInfoSize,"numberOfAlgorithms":self.numberOfAlgorithms,"Algorithms":algorithms}]
		if self.vendorInfoSize>0:j["SpecID"][0]["vendorInfo"]=self.vendorInfo.decode("utf-8")
		return j
class EfiVarEvent(ValidatedEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.guid=uuid.UUID(bytes_le=buffer[idx:idx+16]);self.gg=buffer[idx:idx+16];self.namelen,self.datalen=struct.unpack("<QQ",buffer[idx+16:idx+32]);self.name=buffer[idx+32:idx+32+2*self.namelen];self.data=buffer[idx+32+2*self.namelen:idx+32+2*self.namelen+self.datalen]
	@classmethod
	def parse(cls,evt_header,buffer,idx):
		namelen,datalen=struct.unpack("<QQ",buffer[idx+16:idx+32]);name=buffer[idx+32:idx+32+2*namelen].decode("utf-16")
		if datalen==1:return EfiVarBooleanEvent(evt_header,buffer,idx)
		if name in["PK","KEK","db","dbx"]:return EfiSignatureListEvent(evt_header,buffer,idx)
		return EfiVarEvent(evt_header,buffer,idx)
	def to_json(self):return{**super().to_json(),"Event":{"UnicodeName":self.name.decode("utf-16"),"UnicodeNameLength":self.namelen,"VariableDataLength":self.datalen,"VariableName":str(self.guid),"VariableData":self.data.hex()}}
class EfiVarAuthEvent(EfiVarEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.sigdata=EfiSignatureData(self.data,self.datalen,0)
	@classmethod
	def parse(cls,evt_header,buffer,idx):
		namelen,datalen=struct.unpack("<QQ",buffer[idx+16:idx+32]);name=buffer[idx+32:idx+32+2*namelen].decode("utf-16")
		if datalen==1:return EfiVarBooleanEvent(evt_header,buffer,idx)
		if name=="MokList":return EfiVarHexEvent(evt_header,buffer,idx)
		if name=="SbatLevel":return EfiVarStringEvent(evt_header,buffer,idx)
		return EfiVarAuthEvent(evt_header,buffer,idx)
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]=[self.sigdata];return j
	def validate(self):return None,""
class EfiVarBooleanEvent(EfiVarEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.enabled,=struct.unpack("<?",self.data[:1])
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]={"Enabled":"Yes"if self.enabled else"No"};return j
class EfiVarStringEvent(EfiVarEvent):
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]={"String":self.data.decode("utf-8")};return j
class EfiVarHexEvent(EfiVarEvent):
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]=self.data.hex();return j
class EfiVarBootEvent(EfiVarEvent):
	def __init__(self,evt_header,buffer,idx):
		super().__init__(evt_header,buffer,idx);self.attributes,self.filepathlistlength=struct.unpack("<IH",self.data[0:6]);desclen=0
		while self.data[desclen+6:desclen+8]!=bytes([0,0]):desclen+=2
		self.description=self.data[6:6+desclen];devpathlen=(self.datalen-8-desclen)*2+1;self.devicePath=self.data[8+desclen:8+desclen+devpathlen].hex()
	@classmethod
	def parse(cls,evt_header,buffer,idx):
		namelen,=struct.unpack("<Q",buffer[idx+16:idx+24]);name=buffer[idx+32:idx+32+2*namelen].decode("utf-16")
		if name=="BootOrder":return EfiVarBootOrderEvent(evt_header,buffer,idx)
		if re.compile("^Boot[0-9a-fA-F]{4}$").search(name):return EfiVarBootEvent(evt_header,buffer,idx)
		return EfiVarEvent(evt_header,buffer,idx)
	def validate(self):
		for(algid,refdigest)in self.digests.items():
			calchash1=EfiEventDigest.hashalgmap[algid](self.evbuf).digest();calchash2=EfiEventDigest.hashalgmap[algid](self.data).digest()
			if refdigest.digest not in(calchash1,calchash2):return False,str(self.name.decode("utf-16"))
		return True,""
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]={"Enabled":"Yes"if self.attributes&1==1 else"No","FilePathListLength":self.filepathlistlength,"Description":self.description.decode("utf-16"),"DevicePath":self.devicePath};return j
class EfiVarBootOrderEvent(EfiVarEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.bootorder=struct.unpack(f"<{self.datalen//2}H",self.data)
	def to_json(self):j=super().to_json();j["Event"]["VariableData"]=[f"Boot{b:04x}"for b in self.bootorder];return j
	def validate(self):
		for(algid,refdigest)in self.digests.items():
			calchash1=EfiEventDigest.hashalgmap[algid](self.evbuf).digest();calchash2=EfiEventDigest.hashalgmap[algid](self.data).digest()
			if refdigest.digest not in(calchash1,calchash2):return False,str(self.name.decode("utf-16"))
		return True,""
class EfiSignatureListEvent(EfiVarEvent):
	def __init__(self,evt_header,buffer,idx):
		super().__init__(evt_header,buffer,idx);idx2=0;self.varlist=[]
		while idx2<self.datalen:var=EfiSignatureList(self.data,idx2);idx2+=var.listsize;self.varlist.append(var)
	def to_json(self):
		j=super().to_json()
		if len(self.varlist)==0:j["Event"]["VariableData"]=None
		else:j["Event"]["VariableData"]=self.varlist
		return j
class EfiSignatureList:
	def __init__(self,buffer,idx):
		self.sigtype=uuid.UUID(bytes_le=buffer[idx:idx+16]);self.listsize,self.hsize,self.sigsize=struct.unpack("<III",buffer[idx+16:idx+28]);idx2=28+self.hsize;self.keys=[]
		while idx2<self.listsize:key=EfiSignatureData(buffer,self.sigsize,idx+idx2);self.keys.append(key);idx2+=self.sigsize
	def to_json(self):return{"SignatureType":str(self.sigtype),"SignatureHeaderSize":self.hsize,"SignatureListSize":self.listsize,"SignatureSize":self.sigsize,"Keys":self.keys}
class EfiSignatureData:
	def __init__(self,buffer,sigsize,idx):self.owner=uuid.UUID(bytes_le=buffer[idx:idx+16]);self.sigdata=buffer[idx+16:idx+sigsize]
	def to_json(self):return{"SignatureOwner":str(self.owner),"SignatureData":self.sigdata.hex()}
class EfiActionEvent(GenericEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.event=buffer[idx:idx+self.evsize]
	def to_json(self):return{**super().to_json(),"Event":self.event.decode("utf-8")}
class EfiGPTEvent(ValidatedEvent):
	class GPTPartHeader:
		def __init__(self,buffer,idx):self.signature,self.revision,self.headerSize,self.headerCRC32,_,self.MyLBA,self.alternateLBA,self.firstUsableLBA,self.lastUsableLBA,guidbytes,self.partitionEntryLBA,self.numPartitionEntries,self.sizeOfPartitionEntry,self.partitionEntryArrayCRC=struct.unpack("<8sIIIIQQQQ16sQIII",buffer[idx:idx+92]);self.diskGuid=uuid.UUID(bytes_le=guidbytes)
		def to_json(self):return{"Signature":self.signature.decode("utf-8"),"Revision":self.revision,"HeaderSize":self.headerSize,"HeaderCRC32":self.headerCRC32,"MyLBA":self.MyLBA,"AlternateLBA":self.alternateLBA,"FirstUsableLBA":self.firstUsableLBA,"LastUsableLBA":self.lastUsableLBA,"DiskGUID":str(self.diskGuid),"PartitionEntryLBA":self.partitionEntryLBA,"NumberOfPartitionEntry":self.numPartitionEntries,"SizeOfPartitionEntry":self.sizeOfPartitionEntry,"PartitionEntryArrayCRC32":self.partitionEntryArrayCRC}
	class GPTPartEntry:
		def __init__(self,buffer,idx):self.partitionTypeGUID=uuid.UUID(bytes_le=buffer[idx:idx+16]);self.uniquePartitionGUID=uuid.UUID(bytes_le=buffer[idx+16:idx+32]);self.startingLBA,self.endingLBA,self.attributes,self.partitionName=struct.unpack("<QQQ72s",buffer[idx+32:idx+128])
		def to_json(self):return{"PartitionTypeGUID":str(self.partitionTypeGUID),"UniquePartitionGUID":str(self.uniquePartitionGUID),"Attributes":self.attributes,"StartingLBA":self.startingLBA,"EndingLBA":self.endingLBA,"PartitionName":nullterm16(self.partitionName)}
	def __init__(self,evt_header,buffer,idx):
		super().__init__(evt_header,buffer,idx);self.gptheader=self.GPTPartHeader(buffer,idx);idx+=self.gptheader.headerSize;self.numparts,=struct.unpack("<Q",buffer[idx:idx+8]);idx+=8;self.partitions=[]
		for _ in range(self.numparts):self.partitions.append(self.GPTPartEntry(buffer,idx));idx+=self.gptheader.sizeOfPartitionEntry
	def to_json(self):return{**super().to_json(),"Event":{"Header":self.gptheader.to_json(),"NumberOfPartitions":self.numparts,"Partitions":self.partitions}}
class UefiImageLoadEvent(GenericEvent):
	def __init__(self,evt_header,buffer,idx):super().__init__(evt_header,buffer,idx);self.addrinmem,self.lengthinmem,self.linktimeaddr,self.lengthofdevpath=struct.unpack("<QQQQ",buffer[idx:idx+32]);self.devpathlen=self.evsize-32;self.devpath=buffer[idx+32:idx+32+self.devpathlen].hex()
	def to_json(self):j=super().to_json();j["Event"]={"ImageLocationInMemory":self.addrinmem,"ImageLengthInMemory":self.lengthinmem,"ImageLinkTimeAddress":self.linktimeaddr,"LengthOfDevicePath":self.lengthofdevpath,"DevicePath":str(self.devpath)};return j
class EventLog(list):
	def __init__(self,buffer,buflen):
		super().__init__(self);self.buflen=buflen;evidx=0;idx=0
		while idx<buflen:
			if idx==0:hdr,idx=EventHeader.parse_pcrevent(buffer,evidx,idx);evt=SpecIdEvent(hdr,buffer,idx)
			else:hdr,idx=EventHeader.parse_pcrevent2(buffer,evidx,idx);evt=EventLog.Handler(hdr.evtype)(hdr,buffer,idx)
			self.append(evt);idx+=hdr.evsize;evidx+=1
	@staticmethod
	def Handler(evtype):
		EventHandlers={Event.EV_POST_CODE:PostCodeEvent.parse,Event.EV_SEPARATOR:ValidatedEvent.parse,Event.EV_EFI_ACTION:EfiActionEvent.parse,Event.EV_EFI_GPT_EVENT:EfiGPTEvent.parse,Event.EV_IPL:EfiIPLEvent.parse,Event.EV_EFI_VARIABLE_DRIVER_CONFIG:EfiVarEvent.parse,Event.EV_EFI_VARIABLE_BOOT:EfiVarBootEvent.parse,Event.EV_EFI_BOOT_SERVICES_DRIVER:UefiImageLoadEvent.parse,Event.EV_EFI_BOOT_SERVICES_APPLICATION:UefiImageLoadEvent.parse,Event.EV_EFI_RUNTIME_SERVICES_DRIVER:UefiImageLoadEvent.parse,Event.EV_EFI_PLATFORM_FIRMWARE_BLOB:FirmwareBlobEvent.parse,Event.EV_EFI_PLATFORM_FIRMWARE_BLOB2:FirmwareBlobEvent.parse,Event.EV_EFI_VARIABLE_BOOT2:EfiVarBootEvent.parse,Event.EV_EFI_VARIABLE_AUTHORITY:EfiVarAuthEvent.parse,Event.EV_S_CRTM_VERSION:ValidatedEvent.parse};ev=Event(evtype)
		if ev in EventHandlers:return EventHandlers[ev]
		return GenericEvent.parse
	def pcrs(self):
		pcrs={}
		for alg in self[0].alglist:
			algname=alg[1].name;d0=EfiEventDigest.hashalgmap[alg[1]]();pcrs[algname]={}
			for event in self:
				if event.evtype==Event.EV_NO_ACTION:continue
				pcridx=event.evpcr;oldpcr=pcrs[algname][pcridx]if pcridx in pcrs[algname]else bytes(d0.digest_size);extdata=event.digests[alg[1]].digest;newpcr=EfiEventDigest.hashalgmap[alg[1]](oldpcr+extdata).digest();pcrs[algname][pcridx]=newpcr
		return pcrs
	def validate(self):
		fail_list=[]
		for evt in self:
			passed,why=evt.validate()
			if passed in(None,True):continue
			fail_list.append((evt.evidx,evt.evtype.name,type(evt),why))
		return fail_list
# endregion

WELL_KNOWN_EFI_VARS = {
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
def WriteEfiVar(name, value):
	if name not in WELL_KNOWN_EFI_VARS:
		raise Exception(f"Unknown EFI variable with name {name}.")
	attributes = WELL_KNOWN_EFI_VARS[name]["attributes"]
	path = f"/sys/firmware/efi/efivars/{name}-{WELL_KNOWN_EFI_VARS[name]["guid"]}"
	if os.path.exists(path):
		RunCommand(f"chattr -i \"{path}\"")
	fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
	try:
		os.write(fd, attributes + value)
	finally:
		os.close(fd)
	if os.path.exists(path):
		RunCommand(f"chattr +i \"{path}\"")
def ReadEfiVar(name):
	if name not in WELL_KNOWN_EFI_VARS:
		raise Exception(f"Unknown EFI variable with name {name}.")
	path = f"/sys/firmware/efi/efivars/{name}-{WELL_KNOWN_EFI_VARS[name]["guid"]}"
	buffer = b""
	if os.path.exists(path):
		fd = os.open(path, os.O_RDONLY)
		try:
			size = os.fstat(fd).st_size
			buffer = os.read(fd, size)[4:]
		finally:
			os.close(fd)
	return buffer

def CreateEslHashList(signatures: list[bytes]):
	signature_type = bytes.fromhex("2616c4c14c509240aca941f936934328") # EFI_CERT_SHA256_GUID
	signature_header_size = 28 # sizeof(EFI_SIGNATURE_LIST)
	signature_extra_size = 0 # Incorrectly labled as signature_header_size in UEFI spec. Should always be 0
	signature_size = 16 + 32 # sizeof(EFI_SIGNATURE_DATA) + SHA256_SIZE
	signature_list_size = signature_header_size + (signature_size * len(signatures)) # SignatureHeaderSize + (SignatureSize * NUM_SIGNATURES)
	signature_owner = bytes.fromhex("042c7081cc157345b5d4c3a476b635dc") # EOS_UUID
	return struct.pack("<16sIII", signature_type, signature_list_size, signature_extra_size, signature_size) + b"".join([ signature_owner + signature for signature in signatures ])

def Main():
	script_path = os.path.realpath(__file__)
	script_name = os.path.splitext(os.path.basename(script_path))[0]
	install_path = f"/usr/bin/{script_name}"

	# Initial setup and scanity checks
	is_root = os.geteuid() == 0 and os.getegid() == 0
	if not is_root:
		PrintError(f"Root is required to run {script_name}. Try sudo {script_name}.")
		return 1
	if RunCommand("findmnt --noheadings --raw --output source --target /boot", check=False) != 0:
		PrintError("Nothing is mounted on /boot. Did you forget something?")
		return 1
	if RunCommand("findmnt --noheadings --raw --output source --target /sys/firmware/efi/efivars/", check=False) != 0:
		PrintError("Nothing is mounted on /sys/firmware/efi/efivars/. Did you forget something?")
		return 1
	kernel_paths = RunCommand("find /usr/lib/modules -maxdepth 2 -mindepth 2 -type f -name vmlinuz", capture=True).splitlines()
	if len(kernel_paths) == 0:
		PrintError("Unable to locate system kernel.")
		return 1
	if len(kernel_paths) > 1:
		PrintError("Multiple system kernels found.")
		return 1
	kernel_path = kernel_paths[0]
	root_dev = RunCommand("findmnt --noheadings --raw --output source --target /", capture=True)
	crypt_info, crypt_status_code = RunCommand(f"cryptsetup status \"{root_dev}\"", capture=True, check=False)
	if crypt_status_code != 0:
		PrintError(f"{script_name} requires an encrypted root partition.")
		return 1
	crypt_root_dev = crypt_info[crypt_info.find("device:") + len("device:"):crypt_info.find("\n", crypt_info.find("device:") + len("device:"))].strip()
	secure_boot = ReadFile("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c", binary=True)[4:] == b"\x01"
	setup_mode = ReadFile("/sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c", binary=True)[4:] == b"\x01"
	if not secure_boot and not setup_mode:
		PrintWarning(f"Secure boot is disabled. This feature is required to use {script_name}.")

	# Disable mkinitcpio hooks
	hooks_dir_path = "/usr/share/libalpm/hooks"
	for hook_name in os.listdir(hooks_dir_path):
		if "mkinitcpio" in hook_name and not hook_name.endswith(".disabled"):
			old_hook_path = os.path.join(hooks_dir_path, hook_name)
			new_hook_path = os.path.join(hooks_dir_path, hook_name + ".disabled")
			RunCommand(f"mv \"{old_hook_path}\" \"{new_hook_path}\"")

	# Install the boot builder pacman hook
	hook_payload = [
		f"# This file is auto-generated by {script_name}.",
		f"# Do not modify. All changes will be lost.",
		f"",
		f"[Trigger]",
		f"Operation = Install",
		f"Operation = Upgrade",
		f"Type = Package",
		f"Target = linux",
		f"",
		f"[Action]",
		f"Description = Running {script_name}...",
		f"When = PostTransaction",
		f"Exec = {install_path}",
	]
	hook_path = os.path.join(hooks_dir_path, "boot_builder.hook")
	WriteFile(hook_path, "".join([ line + "\n" for line in hook_payload ]))
	RunCommand(f"chmod 644 \"{hook_path}\"")
	RunCommand(f"chown +0:+0 \"{hook_path}\"")

	# Create boot builder temp folder
	temp_dir_path = "/tmp/boot_builder"
	RunCommand(f"rm -rf \"{temp_dir_path}\"")
	RunCommand(f"mkdir \"{temp_dir_path}\"")
	RunCommand(f"chmod 700 \"{temp_dir_path}\"")
	RunCommand(f"chown +0:+0 \"{temp_dir_path}\"")

	# Generate initramfs
	print("Making initramfs...")
	mkinitcpio_conf_path = os.path.join(temp_dir_path, "mkinitcpio.conf")
	mkinitcpio_conf = [
		f"MODULES=(fat vfat nls_iso8859_1)",
		f"BINARIES=()",
		f"FILES=()",
		f"HOOKS=(autodetect base udev microcode keyboard keymap numlock block encrypt resume filesystems)",
		f"COMPRESSION=\"cat\"",
		f"COMPRESSION_OPTIONS=()",
	]
	WriteFile(mkinitcpio_conf_path, "".join([ line + "\n" for line in mkinitcpio_conf ]))
	cpio_path = os.path.join(temp_dir_path, "initramfs.cpio")
	RunCommand(f"mkinitcpio -c \"{mkinitcpio_conf_path}\" -g \"{cpio_path}\" -k \"{kernel_path}\"")

	# Compress initramfs
	print("Compressing initramfs...")
	cpio_zstd_path = cpio_path + ".zst"
	RunCommand(f"zstd --rm \"{cpio_path}\" -o \"{cpio_zstd_path}\"")

	# Generate unified kernel image
	print("Making unified kernel image...")
	crypt_root_uuid = RunCommand(f"blkid -o value -s UUID \"{crypt_root_dev}\"", capture=True)
	root_uuid = RunCommand(f"blkid -o value -s UUID \"{root_dev}\"", capture=True)
	swap_offset = RunCommand(f"filefrag /swapfile -v", capture=True).splitlines()[3].split(":")[2].partition(".")[0].strip()
	cmdline = f"resume=UUID={root_uuid} resume_offset={swap_offset} hibernate.compressor=lz4 cryptdevice=UUID={crypt_root_uuid}:crypt_root root=/dev/mapper/crypt_root rw"
	kernel_info = RunCommand(f"file \"{kernel_path}\"", capture=True)
	uname = kernel_info[kernel_info.find("version ") + len("version "):]
	uname = uname[:uname.find(" ")]
	ukify_conf_path = os.path.join(temp_dir_path, "ukify.conf")
	ukify_conf = [
		f"[UKI]",
		f"Linux={kernel_path}",
		f"Initrd={cpio_zstd_path}",
		f"OSRelease=EOS",
		f"Uname={uname}",
		f"Cmdline={cmdline}",
	]
	WriteFile(ukify_conf_path, "".join([ line + "\n" for line in ukify_conf ]))
	efi_path = os.path.join(temp_dir_path, "eos.efi")
	RunCommand(f"ukify -c \"{ukify_conf_path}\" build -o \"{efi_path}\"")
	RunCommand(f"rm \"{cpio_zstd_path}\"")

	# Install uki to boot partition
	RunCommand("rm -rf /boot/*")
	RunCommand("chmod 700 /boot")
	RunCommand("chown +0:+0 /boot")
	RunCommand("mkdir /boot/EFI")
	RunCommand("chmod 700 /boot/EFI")
	RunCommand("chown +0:+0 /boot/EFI")
	RunCommand("mkdir /boot/EFI/BOOT")
	RunCommand("chmod 700 /boot/EFI/BOOT")
	RunCommand("chown +0:+0 /boot/EFI/BOOT")
	RunCommand(f"cp \"{efi_path}\" /boot/EFI/BOOT/BOOTX64.EFI")
	RunCommand("chmod 700 /boot/EFI/BOOT/BOOTX64.EFI")
	RunCommand("chown +0:+0 /boot/EFI/BOOT/BOOTX64.EFI")

	# Setup efi boot entries as needed
	for line in RunCommand("efibootmgr", capture=True).splitlines():
		if not len(line) > 8:
			continue
		if not line.startswith("Boot"):
			continue
		if not line[8:].startswith(" ") and not line[8:].startswith("* "):
			continue
		boot_num = line[4:8]
		if not all([ c in "0123456789" for c in boot_num ]):
			continue
		RunCommand(f"efibootmgr --delete-bootnum --bootnum {boot_num}")
	boot_dev = RunCommand("findmnt --noheadings --raw --output source --target /boot", capture=True)
	boot_disk = os.path.join("/dev", RunCommand(f"lsblk --noheadings --raw --output PKNAME \"{boot_dev}\"", capture=True))
	boot_part = RunCommand(f"lsblk --noheadings --raw --output PARTN \"{boot_dev}\"", capture=True)
	RunCommand(f"efibootmgr --create-only --disk \"{boot_disk}\" --part \"{boot_part}\" --loader \"\\EFI\\BOOT\\BOOTX64.EFI\" --label \"EOS\"")
	for line in RunCommand("efibootmgr", capture=True).splitlines():
		if not len(line) > 8:
			continue
		if not line.startswith("Boot"):
			continue
		if not line[8:].startswith(" ") and not line[8:].startswith("* "):
			continue
		boot_num = line[4:8]
		if not all([ c in "0123456789" for c in boot_num ]):
			continue
		RunCommand(f"efibootmgr --bootorder {boot_num}")
		break
	RunCommand("efibootmgr --timeout 0", check=False)
	RunCommand("efibootmgr --delete-bootnext", check=False)

	# Generate efi certs, keys, and values for efi vars
	eos_uuid = "81702c04-15cc-4573-b5d4-c3a476b635dc"
	openssl_conf = "x509_extensions = noext\n[noext]\nsubjectKeyIdentifier=none"
	openssl_conf_path = os.path.join(temp_dir_path, "openssl.conf")
	WriteFile(openssl_conf_path, openssl_conf)
	keys_dir_path = "/etc/efi_keys"
	if not os.path.exists(keys_dir_path):
		RunCommand(f"mkdir \"{keys_dir_path}\"")
		RunCommand(f"chmod 700 \"{keys_dir_path}\"")
		RunCommand(f"chown +0:+0 \"{keys_dir_path}\"")

	pk_key_path = os.path.join(keys_dir_path, "PK.key")
	if not os.path.exists(pk_key_path):
		RunCommand(f"openssl genrsa -out \"{pk_key_path}\" 4096")
	pk_cert_path = os.path.join(keys_dir_path, "PK.crt")
	if not os.path.exists(pk_cert_path):
		RunCommand(f"openssl req -new -x509 -key \"{pk_key_path}\" -out \"{pk_cert_path}\" -days 3650 -sha256 -subj \"/CN=EOS Autogenerated PK\" -config \"{openssl_conf_path}\"")
	pk_esl_path = os.path.join(keys_dir_path, "PK.esl")
	if not os.path.exists(pk_esl_path):
		RunCommand(f"cert-to-efi-sig-list -g \"{eos_uuid}\" \"{pk_cert_path}\" \"{pk_esl_path}\"")

	kek_key_path = os.path.join(keys_dir_path, "KEK.key")
	if not os.path.exists(kek_key_path):
		RunCommand(f"openssl genrsa -out \"{kek_key_path}\" 4096")
	kek_cert_path = os.path.join(keys_dir_path, "KEK.crt")
	if not os.path.exists(kek_cert_path):
		RunCommand(f"openssl req -new -x509 -key \"{kek_key_path}\" -out \"{kek_cert_path}\" -days 3650 -sha256 -subj \"/CN=EOS Autogenerated KEK\" -config \"{openssl_conf_path}\"")
	kek_esl_path = os.path.join(keys_dir_path, "KEK.esl")
	if not os.path.exists(kek_esl_path):
		RunCommand(f"cert-to-efi-sig-list -g \"{eos_uuid}\" \"{kek_cert_path}\" \"{kek_esl_path}\"")

	db_esl_path = os.path.join(keys_dir_path, "db.esl")
	RunCommand(f"hash-to-efi-sig-list \"{efi_path}\" \"{db_esl_path}\"")
	EV_EFI_BOOT_SERVICES_DRIVER = 0x80000004
	ALGORITHM_ID_SHA256 = 11
	evlog_buffer = ReadFile("/sys/kernel/security/tpm0/binary_bios_measurements", binary=True)
	evlog = EventLog(evlog_buffer, len(evlog_buffer))
	oprom_signatures = []
	for event in list(evlog):
		if event.evtype == EV_EFI_BOOT_SERVICES_DRIVER:
			oprom_signatures.append(event.digests[ALGORITHM_ID_SHA256].digest)
	WriteFile(db_esl_path, ReadFile(db_esl_path, binary=True) + CreateEslHashList(oprom_signatures), binary=True)

	dbx_payload = b""
	dbx_esl_path = os.path.join(keys_dir_path, "dbx.esl")
	WriteFile(dbx_esl_path, dbx_payload, binary=True)

	# Set efi var values if they are incorrect
	pk_actual = ReadEfiVar("PK")
	pk_expected = ReadFile(pk_esl_path, binary=True)
	if pk_actual != pk_expected:
		if not setup_mode:
			PrintError("PK is incorrect but the device is not in setup mode. Please manually switch.")
			return 1
		pk_auth_path = os.path.join(temp_dir_path, "pk.auth")
		RunCommand(f"sign-efi-sig-list -g \"{eos_uuid}\" -c \"{pk_cert_path}\" -k \"{pk_key_path}\" PK \"{pk_esl_path}\" \"{pk_auth_path}\"")
		WriteEfiVar("PK", ReadFile(pk_auth_path, binary=True))

	kek_actual = ReadEfiVar("KEK")
	kek_expected = ReadFile(kek_esl_path, binary=True)
	if kek_actual != kek_expected:
		kek_auth_path = os.path.join(temp_dir_path, "kek.auth")
		RunCommand(f"sign-efi-sig-list -g \"{eos_uuid}\" -c \"{pk_cert_path}\" -k \"{pk_key_path}\" KEK \"{kek_esl_path}\" \"{kek_auth_path}\"")
		WriteEfiVar("KEK", ReadFile(kek_auth_path, binary=True))
	
	db_actual = ReadEfiVar("db")
	db_expected = ReadFile(db_esl_path, binary=True)
	if db_actual != db_expected:
		db_auth_path = os.path.join(temp_dir_path, "db.auth")
		RunCommand(f"sign-efi-sig-list -g \"{eos_uuid}\" -c \"{kek_cert_path}\" -k \"{kek_key_path}\" db \"{db_esl_path}\" \"{db_auth_path}\"")
		WriteEfiVar("db", ReadFile(db_auth_path, binary=True))

	dbx_actual = ReadEfiVar("dbx")
	dbx_expected = ReadFile(dbx_esl_path, binary=True)
	if dbx_actual != dbx_expected:
		dbx_auth_path = os.path.join(temp_dir_path, "dbx.auth")
		RunCommand(f"sign-efi-sig-list -g \"{eos_uuid}\" -c \"{kek_cert_path}\" -k \"{kek_key_path}\" dbx \"{dbx_esl_path}\" \"{dbx_auth_path}\"")
		WriteEfiVar("dbx", ReadFile(dbx_auth_path, binary=True))

	# Post Install Cleanup
	RunCommand(f"rm -rf \"{temp_dir_path}\"")
	print("Successfully updated and installed new bootloader!")
	return 0
sys.exit(Main())