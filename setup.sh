#!/bin/bash
#Automated Sprinkler Shutoff System setup script

apt-get install chvt
cp sprinkler.service /etc/systemd/system
systemctl daemon-reload
systemctl enable sprinkler.service
echo "sprinkler.service installed and enabled, service will start after reboot"