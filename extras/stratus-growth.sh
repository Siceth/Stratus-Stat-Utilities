#!/bin/bash
if [ ! -f config.ini ]; then
	echo "[*] config.ini does not exist!"
	exit
fi
host=$(awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /host/) print $2}' config.ini)
username=$(awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /username/) print $2}' config.ini)
password=$(awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /password/) print $2}' config.ini)
database=$(awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /database/) print $2}' config.ini)
port=$(awk -F '=' '{if (! ($0 ~ /^;/) && $0 ~ /port/) print $2}' config.ini)
mysql --user="$username" --password="$password" --database="$database" --port="$port" --execute='INSERT INTO `growth` (players, matches) VALUES ((SELECT COUNT(*) AS "players" FROM `players`), (SELECT COUNT(*) AS "matches" FROM `matches`));' 2>&1 | grep -v "Using a password"
echo "Done."