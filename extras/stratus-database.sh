#!/bin/bash
screen -S stratus-database -X quit
screen -dmS stratus-database bash -c 'echo "Executing..."; python3.6 "/path/to/Stratus Database Integrator.py";'
