#!/bin/bash
# this is my custom start script for DeformBot
# [IMPORTANT] this has to be run as root!
screen -d -m -S db bash -c 'cd $HOME/vault1/projects/DeformBot/discord && python3 deform_bot.py'
