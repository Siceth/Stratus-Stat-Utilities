# NOTE: If this installed on a crontab, matches typically take one hour per ten thousand entries; plan the reset accordingly!

# START CONFIG

VERBOSE_OUTPUT: bool = True
LOG_VERBOSITY: bool = True
DELETE_INVALID_PAGES: bool = False
FAILURE_THRESHOLD: int = 25
STAT_PLAYERS: bool = True
STAT_MATCHES: bool = True
MIRROR: str = "https://stats.seth-phillips.com/stratus/"
POOL_SIZE: int = 15

# END CONFIG

import argparse
import configparser
import glob
import inspect
import os
import re
import sys
import time

from datetime import date, datetime, timedelta
from io import BytesIO
from multiprocessing.dummy import Pool

def missingPackage(package: str) -> None:
	print("Your system is missing %(0)s. Please run `easy_install %(0)s` or `pip install %(0)s` before executing." % { '0': package })
	exit()

try:
	import mysql.connector
except ImportError:
	missingPackage("mysql-connector-python")

try:
	config = configparser.ConfigParser()
	config.read(str(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) + '/config.ini')
except:
	print("[!] Configuration file missing or unreadable. Checking for parameters...")

cli = argparse.ArgumentParser()
cli.add_argument('--verbose', "-v", help = "bool :: output as much information as possible", type = bool, default = VERBOSE_OUTPUT)
cli.add_argument('--log', "-l", help = "bool :: log all output", type = bool, default = LOG_VERBOSITY)
cli.add_argument('--delete', "-d", help = "bool :: delete invalid pages", type = bool, default = DELETE_INVALID_PAGES)
cli.add_argument('--threshold', "-t", help = "int :: the number of failures to accept before giving up", type = int, default = FAILURE_THRESHOLD)
cli.add_argument('--players', "-p", help = "bool :: stat all players", type = bool, default = STAT_PLAYERS)
cli.add_argument('--matches', "-m", help = "bool :: stat all matches", type = bool, default = STAT_MATCHES)
cli.add_argument('--path', help = "str :: path to root cache", type = str, default = config["Integrator"]["path"] if config["Integrator"]["path"] else None)
cli.add_argument('--clone', "-c", help = "str :: set the cURL stat URL/mirror", type = str, default = MIRROR)
cli.add_argument('--pool-size', "-s", help = "int :: the number of threads to create for async requests", type = int, default = POOL_SIZE)
cli.add_argument('--mysql-host', help = "str :: MySQL hostname", type = str, default = config["MySQL"]["host"] if config["MySQL"]["host"] else "localhost")
cli.add_argument('--mysql-user', help = "str :: MySQL username", type = str, default = config["MySQL"]["username"] if config["MySQL"]["username"] else None)
cli.add_argument('--mysql-pass', help = "str :: MySQL password", type = str, default = config["MySQL"]["password"] if config["MySQL"]["password"] else None)
cli.add_argument('--mysql-db', help = "str :: MySQL database", type = str, default = config["MySQL"]["database"] if config["MySQL"]["database"] else None)
cli.add_argument('--mysql-port', help = "int :: MySQL port", type = int, default = config["MySQL"]["port"] if config["MySQL"]["port"] else 3306)
ARGS: dict = cli.parse_args()

class Tee:
	def __init__(self, out1, out2):
		self.out1 = out1
		self.out2 = out2
	def write(self, *args, **kwargs):
		self.out1.write(*args, **kwargs)
		self.out2.write(*args, **kwargs)
	def flush(self):
		pass

if(ARGS.log):
	sys.stdout = Tee(open("./Stratus Database Integrator.log", "w"), sys.stdout)

if ARGS.mysql_user == None or ARGS.mysql_db == None:
	print("[*] MySQL parameters or corresponding config options must be set!")
	exit()

if ARGS.path == None:
	print("[*] Path parameter or corresponding config option must be set!")
	exit()

# TODO - Deprecate
try:
	import dateparser
except ImportError:
	missingPackage("dateparser")

try:
	import requests
except ImportError:
	missingPackage("import requests")

try:
	print("Connecting to database...")
	M_CNX = mysql.connector.connect(
		host = ARGS.mysql_host,
		user = ARGS.mysql_user,
		password = ARGS.mysql_pass,
		database = ARGS.mysql_db,
		port = ARGS.mysql_port,
		use_unicode = True,
		charset = "utf8"
	)
	M_CURSOR = M_CNX.cursor()
except Exception as err:
	print("[*] Error connecting to MySQL database with specified credentials:\n\t%s" % err)
	exit()

try:
	from lxml import etree
	import lxml.html as lh
except ImportError:
	missingPackage("lxml")

try:
	from bs4 import BeautifulSoup as BS
	from bs4 import Comment
except ImportError:
	missingPackage("beautifulsoup4")

try:
	import pycurl
except ImportError:
	missingPackage("pycurl")

try:
	import dateutil.parser
except ImportError:
	missingPackage("python-dateutil")

def runQuery(query: str, handleCommit: bool = True):
	global ARGS, M_CURSOR
	#print("\n\n" + query + "\n\n")
	try:
		M_CURSOR.execute(query)
		if handleCommit:
			M_CNX.commit()
	except Exception as e:
		print("[*] Can't run query:\n=-=-=\n%s\n=-=-=\nMySQL says: %s\n=-=-=\n" % (query, e))
		ARGS.threshold -= 1
		if ARGS.threshold == 0:
			print("[***] Too many database failures! Terminating.")
			exit()

def runSelect(query: str):
	runQuery(query, False)
	result = M_CURSOR.fetchall()
	M_CNX.commit()
	return result

def deleteFile(path: str) -> None:
	try:
		os.remove(path)
		print(" - Deleted")
	except:
		print("[!] Couldn't delete file at \"%s\"." % path)

MAP_TYPES = ["tdm", "ctw", "ctf", "dtc", "dtm", "dtcm", "koth", "blitz", "rage", "arcade", "ffa", "mixed", "payload", "micro"]
donorRanks: list = ["strato", "alto", "cirro"]
staffRanks: list = ["administrator", "developer", "senior moderator", "junior developer", "moderator", "map developer", "event coordinator", "official"]

if __name__ == '__main__':
	
	futures = []
	pool = Pool(ARGS.pool_size)
	i = t = 0
	
	players: list = list()
	matches: list = list()
	
	if ARGS.players:
		if ARGS.verbose:
			print("Finding players in specified directory...")
		players = list(player for player in os.listdir(ARGS.path) if os.path.isfile(os.path.join(ARGS.path, player)))
		players.sort()
		pstats: dict = {}

	if ARGS.matches:
		if ARGS.verbose:
			print("Finding matches in specified directory...")
		matches = list(match for match in os.listdir(ARGS.path + "/matches") if os.path.isfile(os.path.join(ARGS.path + "/matches", match)))
		matches.sort()
		mstats: dict = {}

	if ARGS.verbose:
		if ARGS.players and ARGS.matches:
			print("Found %d players and %d matches." % (len(players), len(matches)))
		elif ARGS.players:
			print("Found %d players." % len(players))
		elif ARGS.matches:
			print("Found %d matches." % len(matches))
	
	t += len(players) + len(matches)

	if ARGS.players:
		if ARGS.verbose:
			print("Querying and indexing database player cache...")
		qrPlayers = runSelect("SELECT username,cached FROM `players`")
		playerCache: dict = {}
		for (username, cached) in qrPlayers:
			playerCache[str(username).lower()] = str(cached)
		
		player: str
		for player in players:
			if ARGS.verbose:
				i += 1
				print("\nProcessing player %s...\t\t[%d / %d = %.2f%%]" % (player, i, t, i*100/t))
			playerPage: BS = BS(open(ARGS.path + "/" + player.lower(), encoding = "utf-8"), "html.parser")
			
			statsVerifier: BS = playerPage.findAll("li", {"class": "active dropdown"})
			if len(statsVerifier) == 0 or statsVerifier[0].findAll("a")[0].get_text().replace('\n', '').replace(' ', '') != "Players":
				print("[!] Skipping non-player page \"%s\"" % player)
				if ARGS.delete:
					deleteFile(ARGS.path + "/" + player)
				continue
			accountVerifier: BS = playerPage.findAll("h4")
			if len(accountVerifier) > 0 and str(accountVerifier[0].get_text().replace('\n', '').replace(' ', '')).lower() == "accountsuspended":
				print("[!] Skipping suspended account \"%s\"" % player)
				if ARGS.delete:
					deleteFile(ARGS.path + "/" + player)
				continue
			if len(player) > 16:
				print("[!] Invalid player name \"%s\"" % player)
				if ARGS.delete:
					deleteFile(ARGS.path + "/" + player)
				continue
			
			pstats[player] = {}
			pstats[player]["cached"] = playerPage.find_all(string = lambda text:isinstance(text, Comment))[0][8:27]
			
			if player not in playerCache or playerCache[player.lower()] != pstats[player.lower()]["cached"]:
				try:
					# Raw pstats
					pstats[player]["uuid"] = playerPage.findAll("img", {"class": "avatar"})[0]['src'][40:76]
					
					data: BS = playerPage.findAll("div", {"class": "number"})
					if len(data) >= 7:
						pstats[player]["kills"] = int(data[0].get_text())
						pstats[player]["deaths"] = int(data[1].get_text())
						pstats[player]["friends"] = int(data[2].get_text())
						pstats[player]["kill_rank"] = int((data[3].get_text())[:-2])
						pstats[player]["droplets"] = int(float('.'.join(re.findall('\d+', data[6].get_text()))) * (1000 if (data[6].get_text())[-1:] == 'k' else (1000000 if (data[6].get_text())[-1:] == 'm' else (1000000000 if (data[6].get_text())[-1:] == 'b' else 1))))
					else:
						pstats[player]["kills"] = 0
						pstats[player]["deaths"] = 0
						pstats[player]["friends"] = 0
						pstats[player]["kill_rank"] = 0
						pstats[player]["droplets"] = 0
					
					data: BS = playerPage.findAll("h2")
					if len(data) > 0:
						pstats[player]["username"] = BS(str(data[0]), "lxml").findAll("span")[0].get_text().replace('\n', '').replace(' ', '')
					if len(data) > 3:
						for matches in data:
							subs: BS = BS(str(matches), "lxml").findAll("small", {"class": "strong"})
							if len(subs) > 0:
								for sub in subs:
									if sub.text.lower() == "cores leaked":
										pstats[player]["cores"] = int(re.sub("\D", "", matches.get_text()))
										break
									elif sub.text.lower() == "monuments destroyed":
										pstats[player]["monuments"] = int(re.sub("\D", "", matches.get_text()))
										break
									elif sub.text.lower() == "wools placed":
										pstats[player]["wools"] = int(re.sub("\D", "", matches.get_text()))
										break
									elif sub.text.lower() == "flags captured":
										pstats[player]["flags"] = int(re.sub("\D", "", matches.get_text()))
										break
					if "username" not in pstats[player]:
						pstats[player]["username"] = player
					if "monuments" not in pstats[player]:
						pstats[player]["monuments"] = 0
					if "wools" not in pstats[player]:
						pstats[player]["wools"] = 0
					if "flags" not in pstats[player]:
						pstats[player]["flags"] = 0
					if "cores" not in pstats[player]:
						pstats[player]["cores"] = 0
					
					data: BS = playerPage.findAll("section")
					if len(data) > 0:
						ranks = BS(str(data[0]), "lxml").findAll("a", {"class": "label"}) + BS(str(data[0]), "lxml").findAll("span", {"class": "label"})
						pstats[player]["ranks"] = len(ranks)
						playerTags = (BS(str(ranks), "lxml").text).lower()
						pstats[player]["staff"] = True if any(x in playerTags for x in staffRanks) else False
						pstats[player]["donor"] = True if any(x in playerTags for x in donorRanks) else False
					else:
						pstats[player]["ranks"] = 0
						pstats[player]["staff"] = False
						pstats[player]["donor"] = False
					
					pstats[player]["tournament_winner"] = True if [x for x in data if "tournament winner" in (x.text).lower()] else False
					
					data: BS = playerPage.findAll("h4", {"class": "strong"})
					if len(data) >= 3:
						pstats[player]["first_joined"] = dateparser.parse(data[0]['title'][16:]).strftime('%Y-%m-%d')
						pstats[player]["hours_played"] = int(re.sub("\D", "", data[1].get_text()))
						pstats[player]["teams_joined"] = int(re.sub("\D", "", data[2].get_text()))
					else:
						pstats[player]["first_joined"] = dateparser.parse(date.today()).strftime('%Y-%m-%d')
						pstats[player]["hours_played"] = 0
						pstats[player]["teams_joined"] = 0
					
					data: BS = playerPage.findAll("div", {"class": "thumbnail trophy"})
					pstats[player]["trophies"] = int(len(data))
					
					data: BS = playerPage.findAll("h5", {"class": "strong"})
					pstats[player]["has_team"] = True if [x for x in data if "team" in (x.text).lower()] else False
					
					# Calculated pstats
					pstats[player]["kd"] = pstats[player]["kills"] / (1 if pstats[player]["deaths"] == 0 else pstats[player]["deaths"])
					
					pstats[player]["average_kills_per_hour"] = pstats[player]["kills"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_deaths_per_hour"] = pstats[player]["deaths"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_monuments_per_hour"] = pstats[player]["monuments"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_wools_per_hour"] = pstats[player]["wools"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_cores_per_hour"] = pstats[player]["cores"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_flags_per_hour"] = pstats[player]["flags"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_droplets_per_hour"] = pstats[player]["droplets"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_new_friends_per_hour"] = pstats[player]["friends"] / (1 if pstats[player]["hours_played"] == 0 else pstats[player]["hours_played"])
					pstats[player]["average_experienced_game_length_in_minutes"] = pstats[player]["hours_played"] * 60 / (1 if pstats[player]["teams_joined"] == 0 else pstats[player]["teams_joined"])
					pstats[player]["average_kills_per_game"] = pstats[player]["kills"] / (1 if pstats[player]["teams_joined"] == 0 else pstats[player]["teams_joined"])
					
					pstats[player]["khpdg"] = pstats[player]["kd"] / (60.0 / (1 if pstats[player]["average_experienced_game_length_in_minutes"] == 0 else pstats[player]["average_experienced_game_length_in_minutes"]))
					
					joined: int = (date.today() - datetime.strptime(pstats[player]["first_joined"], "%Y-%m-%d").date()).days
					pstats[player]["percent_time_spent_on_stratus"] = 0 if joined < 7 else (pstats[player]["hours_played"] * 100 / (24 if joined == 0 else (joined * 24)))
					pstats[player]["percent_waking_time_spent_on_stratus"] = 0 if joined < 7 else (pstats[player]["hours_played"] * 100 / (16 if joined == 0 else (joined * 16)))
					
					# Unfortunately these pstats have to retire since droplets can be spent, which can result in negative objective percentages.
					#pstats[player]["percent_droplets_are_kills"] = pstats[player]["kills"] * 100 / (1 if pstats[player]["droplets"] == 0 else pstats[player]["droplets"])
					#pstats[player]["percent_droplets_are_objectives"] = 100 - pstats[player]["percent_droplets_are_kills"]
					
					# Merit is based on hours played on a scale to account for veteran players that idle. Using inverse regression
					# analysis, the above formula was found so that the pstats of a user that has only played for less than an hour
					# is only worth 10% of what's reported; 100 hours constitutes 100% accuracy and 1000+ hours grants 120%.
					pstats[player]["kill_based_merit"] = (1.2 - (500 / pstats[player]["kills"])) if pstats[player]["kills"] > 454 else 0.1
					pstats[player]["time_based_merit"] = (1.2 - (5 / pstats[player]["hours_played"])) if pstats[player]["hours_played"] > 4 else 0.1
					pstats[player]["merit_multiplier"] = (pstats[player]["kill_based_merit"] + pstats[player]["time_based_merit"]) / 2
					
					# Reliability is solely based on teams joined and is used similar to merit to evaluate how well this player's
					# pstats can be extrapolated to fit larger data sums
					pstats[player]["reliability_index"] = (1.0 - (50 / pstats[player]["teams_joined"])) if pstats[player]["teams_joined"] > 50 else 0.01
					
					pstats[player]["hours_until_one_million_droplets"] = 0 if pstats[player]["droplets"] > 1000000 else ((1000000 - pstats[player]["droplets"]) / (1 if pstats[player]["average_droplets_per_hour"]==0 else pstats[player]["average_droplets_per_hour"]))
				
					# Database cleanup -- configure based on database float allocation values
					if pstats[player]["kd"] >= 10000:
						pstats[player]["kd"] = 9999.999
					if pstats[player]["average_kills_per_hour"] >= 10000:
						pstats[player]["average_kills_per_hour"] = 9999.999
					if pstats[player]["average_deaths_per_hour"] >= 10000:
						pstats[player]["average_deaths_per_hour"] = 9999.999
					if pstats[player]["average_monuments_per_hour"] >= 10000:
						pstats[player]["average_monuments_per_hour"] = 9999.999
					if pstats[player]["average_wools_per_hour"] >= 10000:
						pstats[player]["average_wools_per_hour"] = 9999.999
					if pstats[player]["average_cores_per_hour"] >= 10000:
						pstats[player]["average_cores_per_hour"] = 9999.999
					if pstats[player]["average_flags_per_hour"] >= 10000:
						pstats[player]["average_flags_per_hour"] = 9999.999
					if pstats[player]["average_droplets_per_hour"] >= 10000000:
						pstats[player]["average_droplets_per_hour"] = 9999999.999
					if pstats[player]["average_new_friends_per_hour"] >= 10000:
						pstats[player]["average_new_friends_per_hour"] = 9999.999
					if pstats[player]["average_experienced_game_length_in_minutes"] >= 1000:
						pstats[player]["average_experienced_game_length_in_minutes"] = 999.999
					if pstats[player]["average_kills_per_game"] >= 100:
						pstats[player]["average_kills_per_game"] = 99.999
					if pstats[player]["average_kills_per_game"] >= 10:
						pstats[player]["average_kills_per_game"] = 9.999999
					if pstats[player]["percent_time_spent_on_stratus"] >= 1000:
						pstats[player]["percent_time_spent_on_stratus"] = 999.99
					if pstats[player]["percent_waking_time_spent_on_stratus"] >= 1000:
						pstats[player]["percent_waking_time_spent_on_stratus"] = 999.99
				except Exception as e:
					print("[*] Error translating web cache info! Did the website's page layout change?\nError: " + str(e))
					continue
				
				if ARGS.verbose:
					print("Adding to database...")
				runQuery("INSERT INTO players (" + (", ".join(x for x in pstats[player].keys())) + ") VALUES (" + (", ".join(("\"" + x + "\"" if isinstance(x, str) else str(x)) for x in pstats[player].values())) + ") ON DUPLICATE KEY UPDATE " + (", ".join(["{}={}{}{}".format(k, ("\"" if isinstance(v, str) else ""), v, ("\"" if isinstance(v, str) else "")) for k,v in pstats[player].items()]))) # This is *professionally* unpythonic
				
				if ARGS.verbose:
					print("Done.")
			else:
				if ARGS.verbose:
					print("No updates. C:%s F:%s" % (playerCache[str(player).lower()], pstats[player]["cached"]))

	if ARGS.matches:
		if ARGS.verbose:
			print("Querying and indexing database match cache...")
		qrMatches = runSelect("SELECT uid,cached,end_timestamp FROM `matches`")
		matchCache: dict = {}
		for (uid, cached, end_timestamp) in qrMatches:
			matchCache[str(uid)] = [str(cached), end_timestamp]
		
		match: str
		for match in matches:
			match = str(match)
			if ARGS.verbose:
				i += 1
				print("\nProcessing match %s...\t\t[%d / %d = %.2f%%]" % (match, i, t, i*100/t))
			matchPage: BS
			try:
				matchPage = BS(open(ARGS.path + "/matches/" + match.lower(), encoding="utf-8"), "html.parser")
			except OSError:
				print("[!] File not found: " + ARGS.path + "/matches/" + match.lower())
				continue
			
			statsVerifier: BS = matchPage.findAll("a", {"class": "btn btn-default"})
			if len(statsVerifier) == 0 or statsVerifier[0].get_text().lower().replace('\n', '').replace(' ', '') != "allmatches":
				print("[!] Skipping non-match page \"%s\"" % match)
				if ARGS.delete:
					deleteFile(ARGS.path + "/matches/" + match)
				continue
			if len(match) != 36:
				print("[!] Invalid match name \"%s\"" % match)
				if ARGS.delete:
					deleteFile(ARGS.path + "/matches/" + match)
				continue
			
			mstats[match] = {}
			mstats[match]["cached"] = matchPage.find_all(string = lambda text:isinstance(text, Comment))[0][8:27]
			
			if match not in matchCache or matchCache[match][0] != mstats[match]["cached"] or matchCache[match][1] is None:
				try:
					mstats[match]["uid"] = match
					
					data: BS = matchPage.find("h2")
					mstats[match]["map"] = data.find("a").get_text()
					
					mstats[match]["type"] = str(matchPage.find("img", {"class": "thumbnail"})).split('/')[4]
					mstats[match]["type"] = mstats[match]["type"] if mstats[match]["type"].lower() in MAP_TYPES else "UNKNOWN"
					
					data: BS = data.find("small")
					representation: str = data.text.strip().lower()
					if representation == "running" or representation == "finished" or representation == "starting":
						print("Cache record likely out of date; requeuing...")
						url = "matches/" + match + "/?force-renew"
						futures.append(pool.apply_async(requests.get, [url if "://" in url else (("https://stratus.network/" if ARGS.clone == "" else ARGS.clone) + str(url))]))
						continue
					
					if data.has_attr("title"):
						mstats[match]["start_timestamp"] = dateutil.parser.parse(data["title"])
					else:
						mstats[match]["start_timestamp"] = None
					
					data: BS = matchPage.findAll("h3", {"class": "strong"})
					if mstats[match]["start_timestamp"] == None:
						mstats[match]["duration"] = 0
						mstats[match]["end_timestamp"] = None
					else:
						durationParts: list = re.findall(r'\d+', str(data[1].text))
						numDurationParts: int = len(durationParts)
						durationMultipliers: list = [1, 60, 60, 24]
						mstats[match]["duration"] = 0
						if len(durationMultipliers) < numDurationParts:
							print("[*] Error translating web info! Did this match last more than serveral days?")
							exit()
						mstats[match]["duration"] = sum([(int(t) * durationMultipliers[numDurationParts - i]) for i, t in enumerate(durationParts, start = 1)])
						
						mstats[match]["end_timestamp"] = mstats[match]["start_timestamp"] + timedelta(seconds = mstats[match]["duration"])
					
					mstats[match]["kills"] = int(re.findall(r'\d+', str(data[2].text))[0])
					mstats[match]["deaths"] = int(re.findall(r'\d+', str(data[3].text))[0])
					
					data: BS = matchPage.findAll("h4", {"class": "strong"})
					mstats[match]["players"] = sum([int(x.find("small").text) for x in data])
					
					mstats[match]["prev_uuid"] = None
					mstats[match]["next_uuid"] = None
					
					data: BS = matchPage.findAll("span", {"class": "label label-success pull-right"})
					mstats[match]["winner"] = None
					if(len(data) > 0):
						data: BS = matchPage.findAll("div", {"class": "row"})[3]
						teamDiv: BS
						for teamDiv in data.findAll("div", {"class": "col-md-4"}):
							if teamDiv.find("h4", {"class": "strong"}).find("span", {"class": ["label label-success pull-right"]}) is not None:
								teamCount: BS = teamDiv.find("h4", {"class": "strong"}).find("small")
								teamTag: BS = teamDiv.find("h4", {"class": "strong"}).find("span", {"class": ["label label-danger pull-right", "label label-success pull-right"]})
								mstats[match]["winner"] = (teamDiv.find("h4", {"class": "strong"}).text.strip())[:-((0 if teamCount is None else len(teamCount.text)) + (0 if teamTag is None else len(teamTag.text)))].strip()
					
				except Exception as e:
					print("[*] Error translating web cache info! Did the website's page layout change?\nError: " + str(e))
					continue
				
				if ARGS.verbose:
					print("Match not detected as ended, trying to re-add..." if match in matchCache and matchCache[match][1] is None else "Adding to database...")
				runQuery("INSERT INTO matches (" + (", ".join(x for x in mstats[match].keys() if mstats[match][x] is not None)) + ") VALUES (" + (", ".join(("\"" + str(x) + "\"" if isinstance(x, str) or isinstance(x, datetime) else str(x)) for x in mstats[match].values() if x is not None)) + ") ON DUPLICATE KEY UPDATE " + (", ".join(["{}={}{}{}".format(k, ("\"" if isinstance(v, str) or isinstance(v, datetime) else ""), v, ("\"" if isinstance(v, str) or isinstance(v, datetime) else "")) for k,v in mstats[match].items() if v is not None]))) # Here it is again!
				
				if ARGS.verbose:
					print("Done.")
			else:
				if ARGS.verbose:
					print("No updates. C:%s F:%s" % (matchCache[match.lower()][0], mstats[match]["cached"]))
	
	if ARGS.verbose and len(futures) > 0:
		print("Waiting for all requests to close...")
	for future in futures:
		future.get()
	if ARGS.verbose:
		print("All futures closed.")
	
	if ARGS.verbose:
		print("Disconnecting from database; processing finished.")
	M_CURSOR.close()
	M_CNX.close()
	print("\nDone.")