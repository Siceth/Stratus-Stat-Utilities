#!/bin/bash
screen -S stratus-gameplay -X quit

if [ -f /path/to/complete_output.log ]; then
	rm /path/to/complete_output.log
fi

screen -dmS stratus-gameplay bash -c 'cd "/residual/path/"; echo "Checking for updates..."; ./fetchUtility.sh; echo "Executing..."; python3.6 "Stratus Stat Utilities.py"; rm /path/to/complete_output.log; exec bash'
