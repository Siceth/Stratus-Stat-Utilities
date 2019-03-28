#!/bin/bash
wget -q -N https://raw.githubusercontent.com/Siceth/Stratus-Stat-Utilities/master/Stratus%20Stat%20Utilities.py
sed -i 's/HEADLESS_MODE: bool = False/HEADLESS_MODE: bool = True/g' "Stratus Stat Utilities.py"
sed -i 's/REALTIME_MODE: bool = False/REALTIME_MODE: bool = True/g' "Stratus Stat Utilities.py"
