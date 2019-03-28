################################
#    STRATUS STAT UTILITIES    #
#       because why not        #
#                              #
# Author: Seth Phillips        #
################################

TITLE_TEXT: str = "Stratus Stat Utilities"
VERSION: str = "1.2"
MULTITHREADED: bool = True
MIRROR: str = "https://stats.seth-phillips.com/stratus/"
DELAY: int = 15
HEADLESS_MODE: bool = False
REALTIME_MODE: bool = False
UNIXBOT: bool = True

def missingPackage(package: str) -> None:
	print("Your system is missing %(0)s. Please run `easy_install %(0)s` or `pip install %(0)s` before executing." % { '0': package })
	exit()

import os
import platform
import sys
if platform.system() == "Windows":
	UNIX: bool = False
elif platform.system() == "Linux" or platform.system() == "Darwin":
	UNIX: bool = True
else:
	print("[*] OS not supported!")
	exit()

try:
	from packaging import version
except ImportError:
	missingPackage("packaging")

if version.parse(platform.python_version()) < version.parse("3.6"):
	print("[*] You must run this on Python 3.6!")
	exit()

import _thread
import argparse
import ctypes
import glob
import json
import math
import random
import re
import time

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
from shutil import copyfile

cli = argparse.ArgumentParser()
cli.add_argument('--multithreaded', "-m", help = "bool :: use multithreaded player lookups", type = bool, default = MULTITHREADED)
cli.add_argument('--clone', "-c", help = "str :: set the cURL stat URL/mirror", type = str, default = MIRROR)
cli.add_argument('--delay', "-d", help = "int :: run the win predictor after a number of seconds", type = int, default = DELAY)
cli.add_argument('--headless', "-n", help = "bool :: automatically run the program in non-interactive win predictor mode", type = bool, default = HEADLESS_MODE)
cli.add_argument('--realtime', "-r", help = "bool :: run headless mode consistently", type = bool, default = REALTIME_MODE)
cli.add_argument('--mysql-host', help = "str :: MySQL hostname", type = str, default="localhost")
cli.add_argument('--mysql-user', help = "str :: MySQL username", type = str)
cli.add_argument('--mysql-pass', help = "str :: MySQL password", type = str)
cli.add_argument('--mysql-db', help = "str :: MySQL database", type = str)
cli.add_argument('--mysql-port', help = "int :: MySQL database", type = int, default = 3306)
ARGS: dict = cli.parse_args()
MYSQL: bool = ARGS.mysql_user != None and ARGS.mysql_db != None

try:
	from lxml import etree
	import lxml.html as lh
except ImportError:
	missingPackage("lxml")

if MYSQL:
	try:
		import mysql.connector
	except ImportError:
		missingPackage("mysql-connector")
	try:
		M_CNX = mysql.connector.connect(
			host = ARGS.mysql_host,
			user = ARGS.mysql_user,
			password = ARGS.mysql_pass,
			database = ARGS.mysql_db,
			port = ARGS.mysql_port,
			autocommit = True,
			use_unicode = True,
			charset = "utf8"
		)
		M_CURSOR = M_CNX.cursor()
	except mysql.connector.Error as err:
		print("[*] Error connecting to MySQL database with specified credentials:\n\t%s" % err)
		exit()

try:
	import pycurl
except ImportError:
	missingPackage("pycurl")

try:
	from tabulate import tabulate
except ImportError:
	missingPackage("tabulate")

try:
	from bs4 import BeautifulSoup as BS
except ImportError:
	missingPackage("beautifulsoup4")

try:
	import dateutil.parser
except ImportError:
	missingPackage("python-dateutil")

def logHeadless(data: str, newLine: bool = True, mode: str = 'a') -> None:
	global ARGS
	if ARGS.headless:
		with open("output.log", mode) as f:
			f.write(data + ('\n' if newLine else ''))

def output(data: str) -> None:
	global ARGS
	if ARGS.headless:
		logHeadless(data)
	else:
		print(data)

def exit(pause: bool = True) -> None:
	if pause:
		os.system("read _ > /dev/null" if UNIX else "pause > nul")
	sys.exit(0)

def lazy_input(L: list) -> None:
	global UNIX
	os.system("read _ > /dev/null" if UNIX else "pause > nul")
	L.append(None)

# tdm, ctw, ctf, dtc, dtm, (dtcm,) ad, koth, blitz, rage, scorebox, arcade, gs, ffa, mixed, survival, payload, ranked, micro	
MAP_TYPES = ["tdm", "ctw", "ctf", "dtc", "dtm", "dtcm", "koth", "blitz", "rage", "arcade", "ffa", "mixed", "payload", "micro"]

def loadMessage() -> str:
	return random.choice(["Searching the cloud", "Getting Stratus status", "Completing the water cycle", "Querying for snakes and goobers", "Watching the clouds"]) + "...\n"

def curlRequest(url: str, forceNoMirror: bool = False, handleError: bool = True) -> list:
	global ARGS, UNIX
	try:
		buffer = BytesIO()
		c = pycurl.Curl()
		c.setopt(pycurl.URL, (url if "://" in url else (("https://stratus.network/" if ARGS.clone == "" or forceNoMirror else ARGS.clone) + str(url))))
		c.setopt(pycurl.USERAGENT, ("Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0" if UNIX else "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20130401 Firefox/31.0"))
		c.setopt(pycurl.FOLLOWLOCATION, True)
		c.setopt(pycurl.POST, 0)
		c.setopt(pycurl.SSL_VERIFYPEER, 0)
		c.setopt(pycurl.SSL_VERIFYHOST, 0)
		c.setopt(pycurl.WRITEDATA, buffer)
		c.perform()
		response: int = c.getinfo(pycurl.RESPONSE_CODE)
		html: str = buffer.getvalue().decode("iso-8859-1")
		c.close()
		if response < 500:
			return [response, html.replace('\n', '')]
		if handleError:
			print("[*] cURL responded with a server error while performing the request (%s; %i). Is the website down?" % (url, response))
			exit()
		return [response, ""]
	except:
		print("[*] cURL performance failed. Is your internet operational?")
		exit()

def getStatPos(stat: str) -> int:
	# 0->rank; 1->playing_time; 2->kills; 3->deaths; 4->killed; 5->kd; 6->kk; 7->name
	if stat == "kills":
		return 2
	elif stat == "deaths":
		return 3
	elif stat == "killed":
		return 4
	else:
		return 1

def getPlayerStats(player: str, doCalculations: bool = True, forceRenew: bool = True) -> dict:
	stats: dict = dict()
	playerPage: list = curlRequest(player + ("?force-renew" if forceRenew else ""))
	
	if playerPage[0] > 399:
		stats["exists"] = False
	else:
		stats["exists"] = True
		playerPage: BeautifulSoup = BS(playerPage[1], "lxml")
		
		try:
			# Raw stats
			stats["uuid"]: str = playerPage.findAll("img", {"class": "avatar"})[0]['src'][40:76]
			
			data: BeautifulSoup = playerPage.findAll("div", {"class": "number"})
			if len(data) >= 7:
				stats["kills"]: int = int(data[0].get_text())
				stats["deaths"]: int = int(data[1].get_text())
				stats["friends"]: int = int(data[2].get_text())
				stats["kill_rank"]: int = int((data[3].get_text())[:-2])
				stats["reported_kd"]: float = float(data[4].get_text())
				stats["reported_kk"]: float = float(data[5].get_text())
				stats["droplets"]: int = int(float('.'.join(re.findall('\d+', data[6].get_text()))) * (1000 if (data[6].get_text())[-1:] == 'k' else (1000000 if (data[6].get_text())[-1:] == 'm' else (1000000000 if (data[6].get_text())[-1:] == 'b' else 1))))
			else:
				stats["kills"]: int = 0
				stats["deaths"]: int = 0
				stats["friends"]: int = 0
				stats["kill_rank"]: int = 0
				stats["reported_kd"]: float = 0
				stats["reported_kk"]: float = 0
				stats["droplets"]: int = 0
			
			data: BeautifulSoup = playerPage.findAll("h2")
			if len(data) > 0:
				stats["username"]: str = BS(str(data[0]), "lxml").findAll("span")[0].get_text().replace('\n', '').replace(' ', '')
			if len(data) > 3:
				matches: BeautifulSoup
				for matches in data:
					subs: BeautifulSoup = BS(str(matches), "lxml").findAll("small", {"class": "strong"})
					if len(subs) > 0:
						sub: BeautifulSoup
						for sub in subs:
							if sub.text.lower() == "cores leaked":
								stats["cores"]: int = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower() == "monuments destroyed":
								stats["monuments"]: int = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower() == "wools placed":
								stats["wools"]: int = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower() == "flags captured":
								stats["flags"]: int = int(re.sub("\D", "", matches.get_text()))
								break
			if "username" not in stats:
				stats["username"]: str = player
			if "monuments" not in stats:
				stats["monuments"]: int = 0
			if "wools" not in stats:
				stats["wools"]: int = 0
			if "cores" not in stats:
				stats["cores"]: int = 0
			if "flags" not in stats:
				stats["flags"]: int = 0
			
			data: BeautifulSoup = playerPage.findAll("section")
			if len(data) > 0:
				ranks: BeautifulSoup = BS(str(data[0]), "lxml").findAll("a", {"class": "label"}) + BS(str(data[0]), "lxml").findAll("span", {"class": "label"})
				stats["ranks"]: int = len(ranks)
				donorRanks: list = ["strato", "alto", "cirro"]
				staffRanks: list = ["administrator", "developer", "senior moderator", "junior developer", "moderator", "map developer", "event coordinator", "official"]
				playerTags: BeautifulSoup = (BS(str(ranks), "lxml").text).lower()
				stats["staff"]: bool = True if any(x in playerTags for x in staffRanks) else False
				stats["donor"]: bool = True if any(x in playerTags for x in donorRanks) else False
			else:
				stats["ranks"]: int = 0
				stats["staff"]: bool = False
				stats["donor"]: bool = False
			
			stats["tournament_winner"]: bool = True if [x for x in data if "tournament winner" in (x.text).lower()] else False
			
			data: BeautifulSoup = playerPage.findAll("h4", {"class": "strong"})
			if len(data) >= 3:
				stats["first_joined_days_ago"] = int(re.sub("\D", "", data[0].get_text()))
				stats["hours_played"]: int = int(re.sub("\D", "", data[1].get_text()))
				stats["teams_joined"]: int = int(re.sub("\D", "", data[2].get_text()))
			else:
				stats["first_joined_days_ago"]: int = 0
				stats["hours_played"]: int = 0
				stats["teams_joined"]: int = 0
			
			data: BeautifulSoup = playerPage.findAll("div", {"class": "thumbnail trophy"})
			stats["trophies"]: int = int(len(data))
			
			data: BeautifulSoup = playerPage.findAll("h5", {"class": "strong"})
			stats["team"]: bool = True if [x for x in data if "team" in (x.text).lower()] else False
			
			# Calculated Stats
			if doCalculations:
				
				stats["kd"]: float = stats["kills"] / (1 if stats["deaths"] == 0 else stats["deaths"])
				stats["kd_error"]: float = abs(stats["reported_kd"] - stats["kd"])
				stats["kk_max_death_error"]: float = math.ceil(0.49 * stats["kills"])
				
				# Averages
				stats["average_kills_per_hour"]: float = stats["kills"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_deaths_per_hour"]: float = stats["deaths"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_monuments_per_hour"]: float = stats["monuments"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_wools_per_hour"]: float = stats["wools"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_flags_per_hour"]: float = stats["flags"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_cores_per_hour"]: float = stats["cores"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_droplets_per_hour"]: float = stats["droplets"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_new_friends_per_hour"]: float = stats["friends"] / (1 if stats["hours_played"] == 0 else stats["hours_played"])
				stats["average_experienced_game_length_in_minutes"]: float = stats["hours_played"] * 60 / (1 if stats["teams_joined"] == 0 else stats["teams_joined"])
				stats["average_kills_per_game"]: float = stats["kills"] / (1 if stats["teams_joined"] == 0 else stats["teams_joined"])
				
				# Experimental
				stats["khpdg"]: float = stats["kd"] / (60.0 / (1 if stats["average_experienced_game_length_in_minutes"] == 0 else stats["average_experienced_game_length_in_minutes"]))
				
				# Percents, expressed out of 100
				stats["percent_time_spent_on_stratus"]: float = 0 if stats["first_joined_days_ago"] < 7 else (stats["hours_played"] * 100 / (24 if stats["first_joined_days_ago"] == 0 else (stats["first_joined_days_ago"] * 24)))
				stats["percent_waking_time_spent_on_stratus"]: float = 0 if stats["first_joined_days_ago"] < 7 else (stats["hours_played"] * 100 / (16 if stats["first_joined_days_ago"] == 0 else (stats["first_joined_days_ago"] * 16)))
				
				# Unfortunately these stats have to retire since droplets can be spent, which can result in negative objective percentages.
				#stats["percent_droplets_are_kills"] = stats["kills"] * 100 / (1 if stats["droplets"] == 0 else stats["droplets"])
				#stats["percent_droplets_are_objectives"] = 100 - stats["percent_droplets_are_kills"]
				
				# Merit is based on hours played on a scale to account for veteran players that idle. Using inverse regression
				# analysis, the above formula was found so that the stats of a user that has only played for less than an hour
				# is only worth 10% of what's reported; 100 hours constitutes 100% accuracy and 1000+ hours grants 120%.
				stats["kill_based_merit"]: float = (1.2 - (500 / stats["kills"])) if stats["kills"] > 454 else 0.1
				stats["time_based_merit"]: float = (1.2 - (5 / stats["hours_played"])) if stats["hours_played"] > 4 else 0.1
				stats["merit_multiplier"]: float = (stats["kill_based_merit"] + stats["time_based_merit"]) / 2
				
				# Reliability is solely based on teams joined and is used similar to merit to evaluate how well this player's
				# stats can be extrapolated to fit larger data sums
				stats["reliability_index"]: float = (1.0 - (50 / stats["teams_joined"])) if stats["teams_joined"] > 50 else 0.01
				
				stats["hours_until_one_million_droplets"]: float = 0 if stats["droplets"] > 1000000 else ((1000000 - stats["droplets"]) / (1 if stats["average_droplets_per_hour"] == 0 else stats["average_droplets_per_hour"]))
			
		except KeyboardInterrupt:
			raise
		except:
			print("[*] Error translating web info! Did the website's page layout change?")
			exit()
	return stats

def getMatchStats(uid: str, forceRenew: bool = True) -> dict:
	global MAP_TYPES
	
	stats: dict = dict()
	matchPage: list = curlRequest("matches/" + uid + ("?force-renew" if forceRenew else ""))
	
	if matchPage[0] > 399:
		stats["exists"] = False
	else:
		stats["exists"] = True
		matchPage: BeautifulSoup = BS(matchPage[1], "lxml")
		
		try:
			stats["uid"] = uid
			
			data: BeautifulSoup = matchPage.find("h2")
			stats["map"] = data.find("a").get_text()
			
			stats["type"] = str(matchPage.find("img", {"class": "thumbnail"})).split('/')[4]
			stats["type"] = stats["type"] if stats["type"].lower() in MAP_TYPES else None
			
			data: BeautifulSoup = data.find("small")
			if "title" in data:
				stats["start_timestamp"] = dateutil.parser.parse(data['title'])
			else:
				stats["start_timestamp"] = None
			
			data: BeautifulSoup = matchPage.findAll("h3", {"class": "strong"})
			if stats["start_timestamp"] == None:
				stats["duration"] = 0
				stats["end_timestamp"] = None
			else:
				durationParts: list = re.findall(r'\d+', str(data[1].text))
				numDurationParts: int = len(durationParts)
				durationMultipliers: list = [1, 60, 60, 24]
				stats["duration"] = 0
				if len(durationMultipliers) < numDurationParts:
					print("[*] Error translating web info! Did this match last more than serveral days?")
					exit()
				stats["duration"] = sum([(int(t) * durationMultipliers[numDurationParts - i]) for i, t in enumerate(durationParts, start = 1)])
				
				stats["end_timestamp"] = stats["start_timestamp"] + timedelta(seconds = stats["duration"])
			
			stats["kills"] = re.findall(r'\d+', str(data[2].text))[0]
			stats["deaths"] = re.findall(r'\d+', str(data[3].text))[0]
			
			data: BeautifulSoup = matchPage.findAll("h4", {"class": "strong"})
			stats["players"] = sum([int(x.find("small").text) for x in data])
			
			stats["prev_uuid"] = None
			stats["next_uuid"] = None
			
		except KeyboardInterrupt:
			raise
		except Exception as e:
			print("[*] Error translating web info! Did the website's page layout change?\n" + e) # TODO remove
			exit()
	return stats

def playerStatsLookup() -> None:
	print("Enter player to lookup:")
	username: str = ""
	
	while True:
		username: str = input(" > ").replace(' ', '')
		if re.match("^[A-Za-z0-9_]{3,16}$", username):
			break
		else:
			print("Input must be a valid username. Try again:")
	
	print(loadMessage())
	stats: dict = getPlayerStats(username)
	if stats["exists"]:
		for stat in stats:
			if stat != "exists":
				print("%s: %s" % (stat.replace('_', ' ').title(), stats[stat]))
	else:
		print("[*] The specified username does not exist!")

def matchStatsLookup() -> None:
	print("Enter match UID to lookup:")
	uid: str = ""
	
	while True:
		uid: str = input(" > ").replace(' ', '')
		if re.match("^[A-Za-z0-9-]{36}$", uid):
			break
		else:
			print("Input must be a valid UID (36 characters with dashes). Try again:")
	
	print(loadMessage())
	stats: dict = getMatchStats(uid)
	if stats["exists"]:
		for stat in stats:
			if stat != "exists":
				print("%s: %s" % (stat.replace('_', ' ').title(), stats[stat]))
	else:
		print("[*] The specified UID does not exist!")

def getStatsList(stat: str, stop: int, verbose: bool = True) -> list:
	players: list = list()
	statPos: int = getStatPos(stat)
	search: bool = True
	page: int = 0
	
	while search:
		page += 1
		if verbose:
			print("Searching page %s..." % page)
		rowNum: int = 0
		statsList: list = curlRequest("stats?game = global&page=" + str(page) + "&sort=" + stat + "&time = eternity", True)
		if statsList[0] > 399:
			print("[*] cURL responded with a server error while requesting the stats page (%i). Is the website down?" % statsList[0])
			exit()
		row: BeautifulSoup
		for row in BS(statsList[1], "lxml").findAll("tr"):
			if not search:
				break
			dataNum: int = 0
			player: list = list()
			data: BeautifulSoup
			for data in BS(str(row), "lxml").findAll("td"):
				data = data.get_text()
				if dataNum == statPos:
					if int(data) <= stop - 1:
						search = False
						break
				dataNum += 1
				player.append(data)
			if len(player) > 0 and search:
				rowNum += 1
				players.append(player)
	
	if verbose:
		print("Last possible match found on page %s.\n" % page)
	
	return players

def reverseStatsLookup() -> None:
	stats: list = ["kills", "deaths", "killed"]
	print("Find player by:")
	stat: str
	for stat in stats:
		print("[%s] %s" % (stats.index(stat)+1, stat.title()))
	stat_num: int = 0
	while True:
		try:
			stat_num = int(input(" > "))
			if stat_num in range(1,len(stats)+1):
				break
			else:
				print("Number not in range of options. Try again:")
		except:
			print("Input must be a number. Try again:")
	stop: int = 0
	print("Enter number to lookup:")
	while True:
		try:
			stop = int(input(" > "))
			break
		except:
			print("Input must be a number. Try again:")
	print(loadMessage())
	stat = stats[stat_num-1].replace(' ', '_')
	statPos: int = getStatPos(stat)
	suspects: list = getStatsList(stat, stop)
	
	if len(suspects) > 0:
		closeMatches: list = [x for x in suspects if int(x[statPos]) <= stop * 1.02]
		exactMatches: list = [x for x in closeMatches if int(x[statPos]) == stop]
		
		if len(exactMatches) > 0:
			print("Exact match%s: " % ("es" if len(exactMatches)>1 else ""))
			player: str
			for player in exactMatches:
				print(" - %s (%s %s)" % (player[7], player[statPos], stat.replace('_',' ')))
				if player in closeMatches:
					closeMatches.remove(player)
		else:
			print("No exact matches found.")
		
		if len(closeMatches):
			print("Close match%s: " % ("es" if len(closeMatches)>1 else ""))
			player: str
			for player in closeMatches:
				print(" - %s (%s %s)" % (player[7], player[statPos], stat.replace('_',' ')))
		else:
			print("No close matches (< 2% away) found.")
		
	else:
		print("No matches found. Decrease the number you're looking up for search results.")

def getStaff() -> list:
	staff: list = list()
	staffPage: dict = curlRequest("staff")
	if staffPage[0] > 399:
		print("[*] cURL responded with a server error while requesting the stats page (%i). Is the website down?" % staffPage[0])
		exit()
	member: BeautifulSoup
	for member in (BS(staffPage[1], "lxml")).findAll("div", {"class": "staff-username strong"}):
		member = BS(str(member), "lxml").text
		if member not in staff:
			staff.append(member)
	return sorted(staff, key = str.lower)

def listStaff() -> None:
	print("Current listed staff and referees (%s):" % len(staff))
	staff: list = getStaff()
	member: str
	for member in staff:
		print(" - %s" % member)

def getCurrentPlayers() -> dict:
	teamsPage: dict = curlRequest("https://stratusapi.unixfox.eu/teams", False, False)
	if teamsPage[0] > 399:
		logHeadless("[*] Error making request!");
		print("[*] cURL responded with a server error while requesting the player list (%i). Is unixfox's Stratus API down?" % teamsPage[0])
		exit()
	teams: dict = json.loads(teamsPage[1])
	if "Observers" in teams:
		teams.pop("Observers", None)
	return teams

def getLatestMatch() -> str:
	matchPage: dict = curlRequest("matches/?force-renew")
	if matchPage[0] > 399:
		logHeadless("[*] Error making request!");
		print("[*] cURL responded with a server error while requesting the main match page (%i). Is the website down?" % matchPage[0])
		exit()
	return ([x["href"] for x in (BS(str((BS(matchPage[1], "lxml").findAll("tr"))[1]), "lxml").findAll("a", href = True)) if x.text][0][9:])

def winPredictor(match: str = "", cycleStart: str = "") -> None:
	global ARGS, MYSQL, M_CNX, M_CURSOR, MAP_TYPES
	
	if not ARGS.headless:
		if ARGS.delay == 0:
			print("Enter a match to lookup (leave blank for the current match):")
			while True:
				match = input(" > ").replace(' ', '')
				if re.match("^[A-Za-z0-9\-]{0,36}$", match) or match.replace(' ', '') == "":
					break
				else:
					print("Input must be a valid match ID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). Try again:")
		else:
			print("\nWaiting %s seconds before stating...\n(Or press any key to override & stat now)\n" % ARGS.delay)
			L: list = []
			_thread.start_new_thread(lazy_input, (L,))
			for x in range(0, ARGS.delay * 10):
				time.sleep(.1)
				if L: break
		print(loadMessage())
	
	if match.replace(' ', '') == "":
		latestMatch: bool = True
		logHeadless("Getting list of matches...");
		match = str(getLatestMatch())
	else:
		latestMatch: bool = False
	
	logHeadless("Getting match info (%s)..." % match);
	matchPage: dict = curlRequest("matches/" + match + "?force-renew")
	if matchPage[0] > 399:
		logHeadless("[*] Error making request!");
		print("[*] cURL responded with a server error while requesting the match page (%i). Does the match exist?" % matchPage[0])
		exit()
	matchPage: BeautifulSoup = BS(matchPage[1], "lxml")
	
	logHeadless("Parsing response...");
	mapName: str = matchPage.find("h2").find("a").get_text().title()
	mapType: str = str(matchPage.find("img", {"class": "thumbnail"})).split('/')[4]
	
	if mapType in MAP_TYPES or ARGS.headless:
		mapExists: bool = True
	else:
		if mapType == "" or mapType == "map.png" or mapType[:7] == "map.png":
			print("The match is missing its map.png file and therefore the gamemode cannot be determined!")
		else:
			print("The requested match type (\"%s\") is not a supported gamemode!" % mapType)
		print("Continue anyway? [y/n]")
		if ARGS.headless:
			mapExists: bool = True
		else:
			while True:
				option = input(" > ").lower()
				if option == 'y' or option == 'yes':
					mapExists: bool = True
					break
				elif option == 'n' or option == 'no':
					mapExists: bool = False
					break
				else:
					print("Please specify a \"yes\" or \"no\":")
	
	if mapExists:
		players: list = list()
		gstats: dict = dict()
		composition: dict = dict()
		
		if UNIXBOT and (latestMatch or ARGS.headless):
			logHeadless("Getting the live team structure...");
			currentPlayers: dict = getCurrentPlayers()
			team: str
			for team in currentPlayers:
				if team.lower() not in composition:
					composition[team.lower()] = {"players": dict(), "stats": dict()}
				player: str
				for player in currentPlayers[team]:
					composition[team.lower()]["players"][player] = dict()
		else:
			logHeadless("Using the legacy team structure...");
			teamRow: BeautifulSoup = matchPage.findAll("div", {"class": "row"})[3]		
			teamDiv: BeautifulSoup
			for teamDiv in teamRow.findAll("div", {"class": "col-md-4"}):
				teamCount: BeautifulSoup = teamDiv.find("h4", {"class": "strong"}).find("small")
				teamTag: BeautifulSoup = teamDiv.find("h4", {"class": "strong"}).find("span", {"class": ["label label-danger pull-right", "label label-success pull-right"]})
				team: str = (teamDiv.find("h4", {"class": "strong"}).text.lower())[:-((0 if teamCount is None else len(teamCount.text)) + (0 if teamTag is None else len(teamTag.text)))]
				composition[team] = {"players": dict(), "stats": dict()}
				player: str
				for player in [x["href"][1:] for x in teamDiv.findAll("a", href = True)]:
					composition[team]["players"][player] = dict()
		
		tPreFetch: int = time.time()
		tEst: int = 0
		
		logHeadless("Downloading player statistics...");
		if ARGS.multithreaded:
			if not ARGS.headless:
				print("NOTE: You've enabled the MULTITHREADED option, which is currently developmental and needs more timing tests.") # AKA "it works on my machine"
			with ThreadPoolExecutor(max_workers = 4) as executor:
				team: str
				for team in composition:
					print("\nGetting stats for players on %s (%d)..." % (team, len(composition[team]["players"])))
					player: str
					for player in composition[team]["players"]:
						print("Getting stats for %s..." % player)
						composition[team]["players"][player] = executor.submit(getPlayerStats, player, True, False)
						players.append(player)
				tEst = len(players) * 2.2
				print("\nQuerying web server for player statistics (this will take some time; ETA %ds)..." % math.ceil(tEst))
				team: str
				for team in composition:
					player: str
					for player in composition[team]["players"]:
						if not isinstance(composition[team]["players"][player], dict):
							composition[team]["players"][player] = (composition[team]["players"][player]).result()
		else:
			team: str
			for team in composition:
				tEstTeam = len(composition[team]["players"]) * 2.5
				tEst += tEstTeam
				print("\nGetting stats for players on %s (%d; ETA %ds)..." % (team, len(composition[team]["players"]), math.ceil(tEstTeam)))
				player: str
				for player in composition[team]["players"]:
					print("Getting stats for %s..." % player)
					composition[team]["players"][player] = getPlayerStats(player, True, False)
					players.append(player)
		
		team: str
		for team in composition:
			player: str
			for player in list(composition[team]["players"]):
				if not composition[team]["players"][player]["exists"]:
					composition[team]["players"].pop(player, None)
		
		tPostFetch: int = time.time()
		
		logHeadless("Compiling and computing statistics...");
		gstats["largest_kd"]: dict = ["Nobody", 0]
		gstats["largest_adjusted_kd"]: dict = ["Nobody", 0]
		gstats["most_kills_per_hour"]: dict = ["Nobody", 0]
		gstats["most_deaths_per_hour"]: dict = ["Nobody", 0]
		gstats["most_merit"]: dict = ["Nobody", 0]
		gstats["largest_khpdg"]: dict = ["Nobody", 0]
		gstats["smallest_khpdg"]: dict = ["Nobody", 0]
		gstats["most_hours_played"]: dict = ["Nobody", 0]
		gstats["most_friends"]: dict = ["Nobody", 0]
		gstats["most_droplets"]: dict = ["Nobody", 0]
		gstats["best_rank"]: dict = ["Nobody", 0]
		gstats["worst_rank"]: dict = ["Nobody", 0]
		gstats["most_trophies"]: dict = ["Nobody", 0]
		
		gstats["top_monuments_per_hour"]: dict = ["Nobody", 0]
		gstats["top_flags_per_hour"]: dict = ["Nobody", 0]
		gstats["top_wools_per_hour"]: dict = ["Nobody", 0]
		gstats["top_cores_per_hour"]: dict = ["Nobody", 0]
		gstats["top_droplets_per_hour"]: dict = ["Nobody", 0]
		gstats["top_new_friends_per_hour"]: dict = ["Nobody", 0]
		gstats["top_kills_per_game"]: dict = ["Nobody", 0]
		gstats["top_adjusted_kills_per_game"]: dict = ["Nobody", 0]
		gstats["top_waking_time_spent_on_stratus"]: dict = ["Nobody", 0]
		gstats["top_adjusted_waking_time_spent_on_stratus"]: dict = ["Nobody", 0]
		gstats["longest_average_game_experience"]: dict = ["Nobody", 0]
		gstats["longest_adjusted_average_game_experience"]: dict = ["Nobody", 0]
		gstats["shortest_average_game_experience"]: dict = ["Nobody", 0]
		gstats["shortest_adjusted_average_game_experience"]: dict = ["Nobody", 0]
		
		gstats["average_kd"]: float = 0
		gstats["average_kill_rank"]: float = 0
		gstats["average_experienced_game_length_in_minutes"]: float = 0
		gstats["average_username_length"]: float = 0
		gstats["average_reliability_index"]: float = 0
		gstats["cumulative_reliability_index"]: float = 0
		
		for team in composition:
			print("\nCalculating larger statistics for %s..." % team)
			
			composition[team]["stats"]["number_of_players"]: int = len(composition[team]["players"])
			composition[team]["stats"]["total_kills"]: int = 0
			composition[team]["stats"]["total_deaths"]: int = 0
			composition[team]["stats"]["total_friends"]: int = 0
			composition[team]["stats"]["total_droplets"]: int = 0
			composition[team]["stats"]["total_monuments"]: int = 0
			composition[team]["stats"]["total_flags"]: int = 0
			composition[team]["stats"]["total_wools"]: int = 0
			composition[team]["stats"]["total_cores"]: int = 0
			composition[team]["stats"]["total_staff"]: int = 0
			composition[team]["stats"]["total_donors"]: int = 0
			composition[team]["stats"]["total_tournament_winners"]: int = 0
			composition[team]["stats"]["total_hours_played"]: int = 0
			composition[team]["stats"]["total_teams_joined"]: int = 0
			composition[team]["stats"]["total_nonunique_trophies"]: int = 0
			composition[team]["stats"]["total_team_members"]: int = 0
			
			composition[team]["stats"]["total_average_kills_per_hour"]: float = 0
			composition[team]["stats"]["total_average_deaths_per_hour"]: float = 0
			composition[team]["stats"]["total_average_monuments_per_hour"]: float = 0
			composition[team]["stats"]["total_average_flags_per_hour"]: float = 0
			composition[team]["stats"]["total_average_wools_per_hour"]: float = 0
			composition[team]["stats"]["total_average_cores_per_hour"]: float = 0
			composition[team]["stats"]["total_average_droplets_per_hour"]: float = 0
			composition[team]["stats"]["total_average_new_friends_per_hour"]: float = 0
			composition[team]["stats"]["total_average_experienced_game_length_in_minutes"]: float = 0
			composition[team]["stats"]["total_average_kills_per_game"]: float = 0
			
			# Nonce values don't really tell anything useful on their own, but are necessary for certain calculations (mostly averages)
			composition[team]["stats"]["nonce_total_time_based_merit"]: float = 0
			composition[team]["stats"]["nonce_total_kill_based_merit"]: float = 0
			composition[team]["stats"]["nonce_total_merit"]: float = 0
			composition[team]["stats"]["nonce_total_khpdg"]: float = 0
			composition[team]["stats"]["nonce_total_kill_rank"]: int = 0
			composition[team]["stats"]["nonce_total_reported_kd"]: float = 0
			composition[team]["stats"]["nonce_total_reported_kk"]: float = 0
			composition[team]["stats"]["nonce_total_username_length"]: int = 0
			composition[team]["stats"]["nonce_total_first_joined_days_ago"]: int = 0
			composition[team]["stats"]["nonce_total_kd"]: float = 0
			composition[team]["stats"]["nonce_total_kd_error"]: float = 0
			composition[team]["stats"]["nonce_total_percent_time_spent_on_stratus"]: float = 0
			composition[team]["stats"]["nonce_total_percent_waking_time_spent_on_stratus"]: float = 0
			#composition[team]["stats"]["nonce_total_percent_droplets_are_kills"]: float = 0
			#composition[team]["stats"]["nonce_total_percent_droplets_are_objectives"]: float = 0
			
			player: str
			pstats: dict
			for player, pstats in composition[team]["players"].items():
				composition[team]["stats"]["total_kills"] += pstats["kills"]
				composition[team]["stats"]["total_deaths"] += pstats["deaths"]
				composition[team]["stats"]["total_friends"] += pstats["friends"]
				composition[team]["stats"]["total_droplets"] += pstats["droplets"]
				composition[team]["stats"]["total_monuments"] += pstats["monuments"]
				composition[team]["stats"]["total_wools"] += pstats["wools"]
				composition[team]["stats"]["total_flags"] += pstats["flags"]
				composition[team]["stats"]["total_cores"] += pstats["cores"]
				composition[team]["stats"]["total_staff"] += 1 if pstats["staff"] else 0
				composition[team]["stats"]["total_donors"] += 1 if pstats["donor"] else 0
				composition[team]["stats"]["total_tournament_winners"] += 1 if pstats["tournament_winner"] else 0
				composition[team]["stats"]["total_hours_played"] += pstats["hours_played"]
				composition[team]["stats"]["total_teams_joined"] += pstats["teams_joined"]
				composition[team]["stats"]["total_nonunique_trophies"] += pstats["trophies"]
				composition[team]["stats"]["total_team_members"] += 1 if pstats["team"] else 0
				composition[team]["stats"]["total_average_kills_per_hour"] += pstats["average_kills_per_hour"]
				composition[team]["stats"]["total_average_deaths_per_hour"] += pstats["average_deaths_per_hour"]
				composition[team]["stats"]["total_average_monuments_per_hour"] += pstats["average_monuments_per_hour"]
				composition[team]["stats"]["total_average_flags_per_hour"] += pstats["average_flags_per_hour"]
				composition[team]["stats"]["total_average_wools_per_hour"] += pstats["average_wools_per_hour"]
				composition[team]["stats"]["total_average_cores_per_hour"] += pstats["average_cores_per_hour"]
				composition[team]["stats"]["total_average_droplets_per_hour"] += pstats["average_droplets_per_hour"]
				composition[team]["stats"]["total_average_new_friends_per_hour"] += pstats["average_new_friends_per_hour"]
				composition[team]["stats"]["total_average_experienced_game_length_in_minutes"] += pstats["average_experienced_game_length_in_minutes"]
				composition[team]["stats"]["total_average_kills_per_game"] += pstats["average_kills_per_game"]
				
				composition[team]["stats"]["nonce_total_time_based_merit"] += pstats["time_based_merit"]
				composition[team]["stats"]["nonce_total_kill_based_merit"] += pstats["kill_based_merit"]
				composition[team]["stats"]["nonce_total_merit"] += pstats["merit_multiplier"]
				composition[team]["stats"]["nonce_total_khpdg"] += pstats["khpdg"]
				
				composition[team]["stats"]["nonce_total_kill_rank"] += pstats["kill_rank"]
				composition[team]["stats"]["nonce_total_reported_kd"] += pstats["reported_kd"]
				composition[team]["stats"]["nonce_total_reported_kk"] += pstats["reported_kk"]
				composition[team]["stats"]["nonce_total_username_length"] += len(pstats["username"])
				composition[team]["stats"]["nonce_total_first_joined_days_ago"] += pstats["first_joined_days_ago"]
				composition[team]["stats"]["nonce_total_kd"] += pstats["kd"]
				composition[team]["stats"]["nonce_total_kd_error"] += pstats["kd_error"]
				composition[team]["stats"]["nonce_total_percent_time_spent_on_stratus"] += pstats["percent_time_spent_on_stratus"]
				composition[team]["stats"]["nonce_total_percent_waking_time_spent_on_stratus"] += pstats["percent_waking_time_spent_on_stratus"]
				#composition[team]["stats"]["nonce_total_percent_droplets_are_kills"] += pstats["percent_droplets_are_kills"]
				#composition[team]["stats"]["nonce_total_percent_droplets_are_objectives"] += pstats["percent_droplets_are_objectives"]
				
				if pstats["kd"] > gstats["largest_kd"][1]:
					gstats["largest_kd"][0] = pstats["username"]
					gstats["largest_kd"][1] = pstats["kd"]
				if pstats["kd"] * pstats["merit_multiplier"] > gstats["largest_adjusted_kd"][1]:
					gstats["largest_adjusted_kd"][0] = pstats["username"]
					gstats["largest_adjusted_kd"][1] = pstats["kd"]
				if pstats["average_kills_per_hour"] > gstats["most_kills_per_hour"][1]:
					gstats["most_kills_per_hour"][0] = pstats["username"]
					gstats["most_kills_per_hour"][1] = pstats["average_kills_per_hour"]
				if pstats["average_deaths_per_hour"] > gstats["most_deaths_per_hour"][1]:
					gstats["most_deaths_per_hour"][0] = pstats["username"]
					gstats["most_deaths_per_hour"][1] = pstats["average_deaths_per_hour"]
				if pstats["merit_multiplier"] > gstats["most_merit"][1]:
					gstats["most_merit"][0] = pstats["username"]
					gstats["most_merit"][1] = pstats["merit_multiplier"]
				if pstats["khpdg"] > gstats["largest_khpdg"][1]:
					gstats["largest_khpdg"][0] = pstats["username"]
					gstats["largest_khpdg"][1] = pstats["khpdg"]
				if pstats["khpdg"] < gstats["smallest_khpdg"][1] or gstats["smallest_khpdg"][0] == "Nobody":
					gstats["smallest_khpdg"][0] = pstats["username"]
					gstats["smallest_khpdg"][1] = pstats["khpdg"]
				if pstats["hours_played"] > gstats["most_hours_played"][1]:
					gstats["most_hours_played"][0] = pstats["username"]
					gstats["most_hours_played"][1] = pstats["hours_played"]
				if pstats["friends"] > gstats["most_friends"][1]:
					gstats["most_friends"][0] = pstats["username"]
					gstats["most_friends"][1] = pstats["friends"]
				if pstats["droplets"] > gstats["most_droplets"][1]:
					gstats["most_droplets"][0] = pstats["username"]
					gstats["most_droplets"][1] = pstats["droplets"]
				if pstats["kill_rank"] < gstats["best_rank"][1] or gstats["best_rank"][0] == "Nobody":
					gstats["best_rank"][0] = pstats["username"]
					gstats["best_rank"][1] = pstats["kill_rank"]
				if pstats["kill_rank"] > gstats["worst_rank"][1]:
					gstats["worst_rank"][0] = pstats["username"]
					gstats["worst_rank"][1] = pstats["kill_rank"]
				if pstats["trophies"] > gstats["most_trophies"][1]:
					gstats["most_trophies"][0] = pstats["username"]
					gstats["most_trophies"][1] = pstats["trophies"]
				
				if pstats["average_monuments_per_hour"] > gstats["top_monuments_per_hour"][1]:
					gstats["top_monuments_per_hour"][0] = pstats["username"]
					gstats["top_monuments_per_hour"][1] = pstats["average_monuments_per_hour"]
				if pstats["average_wools_per_hour"] > gstats["top_wools_per_hour"][1]:
					gstats["top_wools_per_hour"][0] = pstats["username"]
					gstats["top_wools_per_hour"][1] = pstats["average_wools_per_hour"]
				if pstats["average_flags_per_hour"] > gstats["top_flags_per_hour"][1]:
					gstats["top_flags_per_hour"][0] = pstats["username"]
					gstats["top_flags_per_hour"][1] = pstats["average_flags_per_hour"]
				if pstats["average_cores_per_hour"] > gstats["top_cores_per_hour"][1]:
					gstats["top_cores_per_hour"][0] = pstats["username"]
					gstats["top_cores_per_hour"][1] = pstats["average_cores_per_hour"]
				if pstats["average_droplets_per_hour"] > gstats["top_droplets_per_hour"][1]:
					gstats["top_droplets_per_hour"][0] = pstats["username"]
					gstats["top_droplets_per_hour"][1] = pstats["average_droplets_per_hour"]
				if pstats["average_new_friends_per_hour"] > gstats["top_new_friends_per_hour"][1]:
					gstats["top_new_friends_per_hour"][0] = pstats["username"]
					gstats["top_new_friends_per_hour"][1] = pstats["average_new_friends_per_hour"]
				if pstats["average_kills_per_game"] > gstats["top_kills_per_game"][1]:
					gstats["top_kills_per_game"][0] = pstats["username"]
					gstats["top_kills_per_game"][1] = pstats["average_kills_per_game"]
				if pstats["average_kills_per_game"] * pstats["merit_multiplier"] > gstats["top_adjusted_kills_per_game"][1]:
					gstats["top_adjusted_kills_per_game"][0] = pstats["username"]
					gstats["top_adjusted_kills_per_game"][1] = pstats["average_kills_per_game"]
				if pstats["percent_waking_time_spent_on_stratus"] > gstats["top_waking_time_spent_on_stratus"][1]:
					gstats["top_waking_time_spent_on_stratus"][0] = pstats["username"]
					gstats["top_waking_time_spent_on_stratus"][1] = pstats["percent_waking_time_spent_on_stratus"]
				if pstats["percent_waking_time_spent_on_stratus"] * pstats["merit_multiplier"] > gstats["top_adjusted_waking_time_spent_on_stratus"][1]:
					gstats["top_adjusted_waking_time_spent_on_stratus"][0] = pstats["username"]
					gstats["top_adjusted_waking_time_spent_on_stratus"][1] = pstats["percent_waking_time_spent_on_stratus"]
				if pstats["average_experienced_game_length_in_minutes"] > gstats["longest_average_game_experience"][1]:
					gstats["longest_average_game_experience"][0] = pstats["username"]
					gstats["longest_average_game_experience"][1] = pstats["average_experienced_game_length_in_minutes"]
				if pstats["average_experienced_game_length_in_minutes"] * pstats["merit_multiplier"] > gstats["longest_adjusted_average_game_experience"][1]:
					gstats["longest_adjusted_average_game_experience"][0] = pstats["username"]
					gstats["longest_adjusted_average_game_experience"][1] = pstats["average_experienced_game_length_in_minutes"]
				if gstats["shortest_average_game_experience"][0] == "Nobody" or pstats["average_experienced_game_length_in_minutes"] < gstats["shortest_average_game_experience"][1]:
					gstats["shortest_average_game_experience"][0] = pstats["username"]
					gstats["shortest_average_game_experience"][1] = pstats["average_experienced_game_length_in_minutes"]
				if gstats["shortest_adjusted_average_game_experience"][0] == "Nobody" or pstats["average_experienced_game_length_in_minutes"]/pstats["merit_multiplier"] < gstats["shortest_adjusted_average_game_experience"][1]:
					gstats["shortest_adjusted_average_game_experience"][0] = pstats["username"]
					gstats["shortest_adjusted_average_game_experience"][1] = pstats["average_experienced_game_length_in_minutes"]
				
				gstats["average_reliability_index"] += pstats["reliability_index"]
				gstats["cumulative_reliability_index"] *= pstats["reliability_index"]
			
			teamSize: int = 1 if len(composition[team]["players"]) == 0 else len(composition[team]["players"])
			composition[team]["stats"]["average_kills"]: float = composition[team]["stats"]["total_kills"] / teamSize
			composition[team]["stats"]["average_deaths"]: float = composition[team]["stats"]["total_deaths"] / teamSize
			composition[team]["stats"]["average_friends"]: float = composition[team]["stats"]["total_friends"] / teamSize
			composition[team]["stats"]["average_kill_rank"]: float = int(composition[team]["stats"]["nonce_total_kill_rank"] / teamSize)
			composition[team]["stats"]["average_reported_kd"]: float = composition[team]["stats"]["nonce_total_reported_kd"] / teamSize
			composition[team]["stats"]["average_reported_kk"]: float = composition[team]["stats"]["nonce_total_reported_kk"] / teamSize
			composition[team]["stats"]["average_droplets"]: float = composition[team]["stats"]["total_droplets"] / teamSize
			composition[team]["stats"]["average_username_length"]: float = composition[team]["stats"]["nonce_total_username_length"] / teamSize
			composition[team]["stats"]["average_monuments"]: float = composition[team]["stats"]["total_monuments"] / teamSize
			composition[team]["stats"]["average_flags"]: float = composition[team]["stats"]["total_flags"] / teamSize
			composition[team]["stats"]["average_wools"]: float = composition[team]["stats"]["total_wools"] / teamSize
			composition[team]["stats"]["average_cores"]: float = composition[team]["stats"]["total_cores"] / teamSize
			composition[team]["stats"]["average_first_joined_days_ago"]: float = composition[team]["stats"]["nonce_total_first_joined_days_ago"] / teamSize
			composition[team]["stats"]["average_hours_played"]: float = composition[team]["stats"]["total_hours_played"] / teamSize
			composition[team]["stats"]["average_teams_joined"]: float = composition[team]["stats"]["total_teams_joined"] / teamSize
			composition[team]["stats"]["average_trophies"]: float = composition[team]["stats"]["total_nonunique_trophies"] / teamSize
			composition[team]["stats"]["average_kd"]: float = composition[team]["stats"]["nonce_total_kd"] / teamSize
			composition[team]["stats"]["average_kd_error"]: float = composition[team]["stats"]["nonce_total_kd_error"] / teamSize
			composition[team]["stats"]["average_kills_per_hour"]: float = composition[team]["stats"]["total_average_kills_per_hour"] / teamSize
			composition[team]["stats"]["average_deaths_per_hour"]: float = composition[team]["stats"]["total_average_deaths_per_hour"] / teamSize
			composition[team]["stats"]["average_monuments_per_hour"]: float = composition[team]["stats"]["total_average_monuments_per_hour"] / teamSize
			composition[team]["stats"]["average_flags_per_hour"]: float = composition[team]["stats"]["total_average_flags_per_hour"] / teamSize
			composition[team]["stats"]["average_wools_per_hour"]: float = composition[team]["stats"]["total_average_wools_per_hour"] / teamSize
			composition[team]["stats"]["average_cores_per_hour"]: float = composition[team]["stats"]["total_average_cores_per_hour"] / teamSize
			composition[team]["stats"]["average_droplets_per_hour"]: float = composition[team]["stats"]["total_average_droplets_per_hour"] / teamSize
			composition[team]["stats"]["average_new_friends_per_hour"]: float = composition[team]["stats"]["total_average_new_friends_per_hour"] / teamSize
			composition[team]["stats"]["average_experienced_game_length_in_minutes"]: float = composition[team]["stats"]["total_average_experienced_game_length_in_minutes"] / teamSize
			composition[team]["stats"]["average_kills_per_game"]: float = composition[team]["stats"]["total_average_kills_per_game"] / teamSize
			composition[team]["stats"]["average_percent_time_spent_on_stratus"]: float = composition[team]["stats"]["nonce_total_percent_time_spent_on_stratus"] / teamSize
			composition[team]["stats"]["average_percent_waking_time_spent_on_stratus"]: float = composition[team]["stats"]["nonce_total_percent_waking_time_spent_on_stratus"] / teamSize
			#composition[team]["stats"]["average_percent_droplets_are_kills"]: float = composition[team]["stats"]["nonce_total_percent_droplets_are_kills"] / teamSize
			#composition[team]["stats"]["average_percent_droplets_are_objectives"]: float = composition[team]["stats"]["nonce_total_percent_droplets_are_objectives"] / teamSize
			composition[team]["stats"]["average_time_based_merit"]: float = composition[team]["stats"]["nonce_total_time_based_merit"] / teamSize
			composition[team]["stats"]["average_kill_based_merit"]: float = composition[team]["stats"]["nonce_total_kill_based_merit"] / teamSize
			composition[team]["stats"]["average_merit"]: float = composition[team]["stats"]["nonce_total_merit"] / teamSize
			composition[team]["stats"]["average_khpdg"]: float = composition[team]["stats"]["nonce_total_khpdg"] / teamSize
			
			composition[team]["stats"]["raw_score"]: float = 0
			if mapType == "tdm":
				composition[team]["stats"]["raw_score"] = 0.8 * composition[team]["stats"]["average_kd"] + 0.2 * composition[team]["stats"]["average_kills_per_game"]
			elif mapType == "ctw":
				composition[team]["stats"]["raw_score"] = 0.6 * composition[team]["stats"]["average_kd"] + 0.4 * composition[team]["stats"]["average_wools_per_hour"]
			elif mapType == "ctf":
				composition[team]["stats"]["raw_score"] = 0.6 * composition[team]["stats"]["average_khpdg"] + 0.4 * composition[team]["stats"]["average_flags_per_hour"]
			elif mapType == "dtc":
				composition[team]["stats"]["raw_score"] = 0.6 * composition[team]["stats"]["average_kd"] + 0.4 * composition[team]["stats"]["average_cores_per_hour"]
			elif mapType == "dtm":
				composition[team]["stats"]["raw_score"] = 0.6 * composition[team]["stats"]["average_kd"] + 0.4 * composition[team]["stats"]["average_monuments_per_hour"]
			elif mapType == "dtcm":
				composition[team]["stats"]["raw_score"] = 0.5 * composition[team]["stats"]["average_kd"] + 0.3 * composition[team]["stats"]["average_monuments_per_hour"] + 0.2 * composition[team]["stats"]["average_cores_per_hour"]
			elif mapType == "koth":
				composition[team]["stats"]["raw_score"] = composition[team]["stats"]["average_kd"]
			elif mapType == "blitz" or mapType == "payload" or mapType == "micro":
				composition[team]["stats"]["raw_score"] = composition[team]["stats"]["average_khpdg"]
			elif mapType == "rage":
				composition[team]["stats"]["raw_score"] = 0 if composition[team]["stats"]["average_khpdg"] == 0 or composition[team]["stats"]["average_experienced_game_length_in_minutes"] == 0 else (1 / (composition[team]["stats"]["average_khpdg"] * composition[team]["stats"]["average_experienced_game_length_in_minutes"]))
			elif mapType == "ffa":
				# Stratus matches don't seem to show any players on FFA matches
				composition[team]["stats"]["raw_score"] = composition[team]["stats"]["average_khpdg"] + (0 if composition[team]["stats"]["average_kill_rank"] == 0 else (1 / composition[team]["stats"]["average_kill_rank"]))
			elif mapType == "mixed":
				composition[team]["stats"]["raw_score"] = 0.5 * composition[team]["stats"]["average_kd"] + 0.1 * composition[team]["stats"]["average_monuments_per_hour"] + 0.1 * composition[team]["stats"]["average_wools_per_hour"] + 0.1 * composition[team]["stats"]["average_cores_per_hour"] + 0.2 * composition[team]["stats"]["average_kills_per_game"]
			else:
				mapType = "UNKNOWN"
				print("[*] Generalizing statistics to rely on KHPDG; approximation of estimation will be lower.")
				composition[team]["stats"]["raw_score"] = composition[team]["stats"]["average_khpdg"]
			
			composition[team]["stats"]["raw_score"] += 0.02 * composition[team]["stats"]["total_donors"] + 0.03 * composition[team]["stats"]["total_tournament_winners"]
			composition[team]["stats"]["adjusted_score"] = composition[team]["stats"]["raw_score"] * composition[team]["stats"]["average_merit"]
			
			gstats["average_kd"] += composition[team]["stats"]["average_kd"]
			gstats["average_kill_rank"] += composition[team]["stats"]["average_kill_rank"]
			gstats["average_experienced_game_length_in_minutes"] += composition[team]["stats"]["average_experienced_game_length_in_minutes"]
			gstats["average_username_length"] += composition[team]["stats"]["average_username_length"]
		
		numTeams: int = len(composition)
		
		gstats["total_players"]: int = len(players)
		gstats["username_amalgamation"]: str = ""
		
		# This section was just a creative outlet that ended in disappointment
		username_mess: list = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
		playerName: str
		for playerName in players:
			i: int = 0
			for letter in playerName:
				username_mess[i].append(letter)
				i += 1
		letters: list
		for letters in username_mess:
			letterProperties: dict = {"lowers": 0, "uppers": 0, "numbers": 0, "unders": 0}
			character: str
			for character in letters:
				if character == character.lower():
					letterProperties["lowers"] += 1
				elif character == character.upper():
					letterProperties["uppers"] += 1
				elif character.isdigit():
					letterProperties["numbers"] += 1
				else:
					letterProperties["unders"] += 1
			if letterProperties["lowers"] + letterProperties["uppers"] > letterProperties["numbers"]:
				letters: list = [ord(x.lower() if letterProperties["lowers"] > letterProperties["uppers"] else x.upper()) for x in letters if not x.isdigit()]
				gstats["username_amalgamation"] += chr(round(sum(letters) / (1 if len(letters) == 0 else len(letters))))
			elif letterProperties["numbers"] > letterProperties["unders"]:
				numbers = [x for x in letters if x.isdigit()]
				gstats["username_amalgamation"] += chr(round(sum(numbers) / (1 if len(numbers) == 0 else len(numbers))))
			else:
				gstats["username_amalgamation"] += "_"
		
		gstats["average_kd"] = gstats["average_kd"] / (1 if numTeams == 0 else numTeams)
		gstats["average_kill_rank"] = round(gstats["average_kill_rank"] / (1 if numTeams == 0 else numTeams))
		gstats["average_experienced_game_length_in_minutes"] = gstats["average_experienced_game_length_in_minutes"] / (1 if numTeams == 0 else numTeams)
		gstats["average_username_length"] = gstats["average_username_length"] / (1 if numTeams == 0 else numTeams)
		gstats["average_reliability_index"] = gstats["average_reliability_index"] / (1 if gstats["total_players"] == 0 else gstats["total_players"])
		gstats["username_amalgamation"] = gstats["username_amalgamation"][:round(gstats["average_username_length"])]
		
		tPostCalc: int = time.time()
		
		if numTeams > 0:
		
			if not UNIX:
				ctypes.windll.kernel32.SetConsoleTitleW(TITLE_TEXT)
				os.system("cls")
			else:
				os.system("clear")
			
			logHeadless(";;;")
			
			output("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n          Meta Statistics          \n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")
			
			tTotal: int = tPostCalc - tPreFetch
			if cycleStart != "":
				output("Cycle start time: %s" % cycleStart)
			output("Program took %.2fs to fetch base player statistics and %.5fs to calculate all other statistics, totaling %.2fs." % (tPostFetch - tPreFetch, tPostCalc - tPostFetch, tTotal))
			output("Expected total run time was %.2fs." % tEst)
			output("Latency margin of error is %.2f%%." % abs((tEst - tTotal) * 100 / tTotal))
			
			output("\n\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n         Global Statistics         \n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")
			output("Map name: %s" % mapName)
			output("Detected map type: %s" % mapType.upper())
			stat: str
			for stat in gstats:
				if isinstance(gstats[stat], list):
					if isinstance(gstats[stat][1], float):
						output("%s: %s (%.2f)" % (stat.replace('_', ' ').title(), gstats[stat][0], gstats[stat][1]))
					else:
						output("%s: %s (%s)" % (stat.replace('_', ' ').title(), gstats[stat][0], gstats[stat][1]))
				else:
					if isinstance(gstats[stat], float):
						output("%s: %.2f" % (stat.replace('_', ' ').title(), gstats[stat]))
					else:
						output("%s: %s" % (stat.replace('_', ' ').title(), gstats[stat]))
			
			output(("\n\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n Team Statistics for Current Match \n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n") if latestMatch else ("\n\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n Team Statistics for %s \n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n" % match))
			
			tableHeaders: list = [x.title() for x in composition]
			tableHeaders.insert(0, "")
			tableData: list = list()
			
			for stat in composition[next(iter(composition))]["stats"]:
				if stat[:5] != "nonce" and stat[:13] != "total_average":
					substat = list()
					substat.append(stat.replace('_', ' ').title())
					for team in composition:
						substat.append(composition[team]["stats"][stat])
					tableData.append(substat)
			
			output(tabulate(tableData, headers = tableHeaders))
			
			scoreTotal: int = 0
			winner: dict = ["nobody", 0]
			assuredness_index: float = 1
			for team in composition:
				scoreTotal += composition[team]["stats"]["adjusted_score"]
				if composition[team]["stats"]["adjusted_score"] > winner[1]:
					assuredness_index = composition[team]["stats"]["adjusted_score"] / (1 if composition[team]["stats"]["adjusted_score"] == 0 else composition[team]["stats"]["adjusted_score"] + winner[1])
					winner[0]: str = team
					winner[1]: float = composition[team]["stats"]["adjusted_score"]
				else:
					assuredness_index = winner[1] / (1 if composition[team]["stats"]["adjusted_score"] == 0 else composition[team]["stats"]["adjusted_score"] + winner[1])
			
			output("\n")
			for team in composition:
				output("%s has a %.2f%% chance of winning." % (team.title(), (composition[team]["stats"]["adjusted_score"] * 100 / (1 if scoreTotal == 0 else scoreTotal))))
			
			if assuredness_index < 0.525 or gstats["average_reliability_index"] < 0.4:
				output("\nIt's too hard to tell who will win this game due to a low player stat accuracy (%.2f%%) or a low decision accuracy (%.2f%%)." % (gstats["average_reliability_index"] * 100, assuredness_index * 100))
				if MYSQL:
					M_CURSOR.execute("UPDATE currentmap SET Value = 'Too close to predict' WHERE id='7'")
			elif assuredness_index > 0.825 and gstats["average_reliability_index"] > 0.7:
				output("\nI am very sure that %s will win with a %.2f%% player stat accuracy and a high decision accuracy (%.2f%%)." % (winner[0].title(), gstats["average_reliability_index"] * 100, assuredness_index * 100))
				if MYSQL:
					M_CURSOR.execute("UPDATE currentmap SET Value = '%s (%.2f%% chance)' WHERE id='7'" % (winner[0].title(), assuredness_index * 100))
			else:
				output("\nI predict that %s will win with a %.2f%% player stat accuracy and a %.2f%% decision accuracy." % (winner[0].title(), gstats["average_reliability_index"] * 100, assuredness_index * 100))
				if MYSQL:
					M_CURSOR.execute("UPDATE currentmap SET Value = '%s (%.2f%% chance)' WHERE id='7'" % (winner[0].title(), assuredness_index * 100))
		else:
			output("[*] The team list is empty and therefore no stats can be found!")
	else:
		print("\nAborted. Press any key to continue.")

def main() -> None:
	global UNIX, TITLE_TEXT, VERSION
	os.chdir(os.path.dirname(os.path.abspath(__file__)))
	EXIT = False
	while not EXIT:
		if not UNIX:
			ctypes.windll.kernel32.SetConsoleTitleW(TITLE_TEXT)
			os.system("cls")
		else:
			os.system("clear")
		
		print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
		print(" %s v%s" % (TITLE_TEXT, VERSION))
		print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
		
		options: list = ["Get a player's stats", "Reverse player stats lookup", "Get a public match's stats", "List staff members", "Win predictor", "Exit"]
		print("Pick a utility:")
		stat: str
		for stat in options:
			print("[%s] %s" % (options.index(stat) + 1, stat))
		option_num: int = 0
		while True:
			try:
				option_num = int(input(" > "))
				if option_num in range(1, len(options) + 1):
					break
				else:
					print("Number not in range of options. Try again:")
			except:
				print("Input must be a number. Try again:")
		if option_num == 1:
			playerStatsLookup()
		elif option_num == 2:
			reverseStatsLookup()
		elif option_num == 3:
			matchStatsLookup()
		elif option_num == 4:
			listStaff()
		elif option_num == 5:
			winPredictor()
		else:
			EXIT = True
		if not EXIT:
			os.system("read _ > /dev/null" if UNIX else "pause > nul")
	print("Goodbye.")
	exit(False)

if __name__ == '__main__':
	try:
		if ARGS.headless:
			print("Headless mode is enabled. Events will be recorded to `output.log`. Keyboard terminate / pkill if the loop gets messy.")
			logHeadless("", False)
			
			lastMatch: str = ""
			waitCycle: int = 30
			while True:
				latestMatch = str(getLatestMatch())
				if not ARGS.realtime and latestMatch == lastMatch:
					print("[%s] No match difference. Pinging again in %i seconds..." % (datetime.now().isoformat(), waitCycle))
					time.sleep(waitCycle)
					if waitCycle < 300:
						waitCycle += 1
				else:
					waitCycle = 30
					lastMatch = latestMatch
					
					if not UNIX:
						os.system("cls")
					else:
						os.system("clear")
					
					print("Cycle beginning.")
					cycleStart: str = datetime.now().isoformat()
					logHeadless("Cycle start time: ", False, 'w')
					logHeadless(cycleStart)
					time.sleep(20 if ARGS.delay == 0 else ARGS.delay)
					winPredictor(lastMatch, cycleStart)
					copyfile('output.log', 'complete_output.log')
					print("Cycle complete. Running again in %i seconds..." % 15 if ARGS.realtime else 60)
					time.sleep(15 if ARGS.realtime else 60)
		else:
			main()
	except KeyboardInterrupt:
		print("\n\nTerminating.")
		sys.exit(0)