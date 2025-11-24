#!/bin/sh

cp /usr/share/edk2-ovmf/x64/OVMF_VARS.4m.fd ./OVMF_VARS.4m.fd

qemu-system-x86_64 \
  -enable-kvm \
  -cpu host \
  -smp cores=4 \
  -m 4G \
  -device ahci,id=ahci0 \
  -device ide-hd,drive=hd0,bus=ahci0.0 \
  -drive file=/dev/sda,format=raw,if=none,id=hd0 \
  -display sdl -vga std \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd \
  -drive if=pflash,format=raw,file=./OVMF_VARS.4m.fd \
  -name "EOS VM"
