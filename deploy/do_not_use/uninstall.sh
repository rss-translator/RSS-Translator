#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

read -p "Are you sure you want to remove RSS Translator and all datas? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

echo "Removed user: rsstranslator"
if id -u rsstranslator >/dev/null 2>&1; then
    userdel rsstranslator
fi
echo "Removed group: rsstranslator"
if getent group rsstranslator >/dev/null 2>&1; then
    groupdel rsstranslator
fi

echo "Removed service: rsstranslator.service"
systemctl stop rsstranslator.service
systemctl disable rsstranslator.service
rm /etc/systemd/system/rsstranslator.service

echo "Remove folder: /home/rsstranslator"
rm -rf /home/rsstranslator
echo "Success Remove RSS Translator"
