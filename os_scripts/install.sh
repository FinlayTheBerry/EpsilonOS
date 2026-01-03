#!/bin/sh

install -m755 -o0 -g0 ./backup_commit.py /usr/bin/backup_commit
install -m755 -o0 -g0 ./backup_service.py /usr/bin/backup_service
install -m755 -o0 -g0 ./eos_updates.py /usr/bin/eos_updates
install -m755 -o0 -g0 ./important_data_scan.py /usr/bin/important_data_scan
install -m755 -o0 -g0 ./sudocode.py /usr/bin/sudocode