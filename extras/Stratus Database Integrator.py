import datetime
import configparser
import glob
import inspect
import os
import re
import sys
import time

# START CONFIG

VERBOSE_OUTPUT = True
LOG_VERBOSITY = True
DELETE_INVALID_PAGES = True
FAILURE_THRESHOLD = 25

# END CONFIG

class Tee:
	def __init__(self, out1, out2):
		self.out1 = out1
		self.out2 = out2
	def write(self, *args, **kwargs):
		self.out1.write(*args, **kwargs)
		self.out2.write(*args, **kwargs)
	def flush(self):
		pass

if(LOG_VERBOSITY):
	sys.stdout = Tee(open("./Stratus Database Integrator.log", "w"), sys.stdout)

try:
	import dateparser
except ImportError:
	print("Your system is missing dateparser. Please run `easy_install dateparser` or `pip install dateparser` before executing.")
	exit()

try:
	import _mysql
	from MySQLdb.constants import FIELD_TYPE
except ImportError:
	print("Your system is missing mysqlclient. Please run `easy_install mysqlclient` or `pip install mysqlclient` before executing.")
	exit()

try:
	from lxml import etree
	import lxml.html as lh
except ImportError:
	print("Your system is missing lxml. Please run `easy_install lxml` or `pip install lxml` before executing.")
	exit()

try:
	from bs4 import BeautifulSoup as BS
	from bs4 import Comment
except ImportError:
	print("Your system is missing BeautifulSoup. Please run `easy_install beautifulsoup4` or `pip install beautifulsoup4` before executing.")
	exit()

try:
	config = configparser.ConfigParser()
	config.read(str(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) + '/config.ini')
except:
	print("Configuration file missing or unreadable!")
	exit()

try:
	if VERBOSE_OUTPUT:
		print("Connecting to database...")
	db = _mysql.connect(host=config["MySQL"]["host"], user=config["MySQL"]["username"], passwd=config["MySQL"]["password"], db=config["MySQL"]["database"], conv={ FIELD_TYPE.LONG: int, FIELD_TYPE.INT24: int, FIELD_TYPE.CHAR: bool })
except:
	print("[*] Can't connect to database!")
	exit()

def runQuery(query):
	global FAILURE_THRESHOLD
	try:
		db.query(query)
		return db.store_result()
	except:
		print("[*] Can't run query:\n=-=-=\n%s\n=-=-=\n" % query)
		FAILURE_THRESHOLD -= 1
		if FAILURE_THRESHOLD==0:
			print("[***] Too many database failures! Terminating.")
			exit()

def deleteFile(path):
	try:
		os.remove(path)
		print(" - Deleted")
	except:
		print("[!] Couldn't delete file at \"%s\"." % path)

donorRanks = ["strato", "alto", "cirro"]
staffRanks = ["administrator", "developer", "senior moderator", "junior developer", "moderator", "map developer", "event coordinator", "official"]

if VERBOSE_OUTPUT:
	print("Finding players in specified directory...")
players = list(player for player in os.listdir(config["Integrator"]["path"]) if os.path.isfile(os.path.join(config["Integrator"]["path"], player)))
players.sort()

if VERBOSE_OUTPUT:
	print("Finding matches in specified directory...")
matches = list(match for match in os.listdir(config["Integrator"]["path"] + "/matches") if os.path.isfile(os.path.join(config["Integrator"]["path"], player)))

if VERBOSE_OUTPUT:
	print("Found %d players and %d matches." % (len(players), len(matches))
pstats = {}
mstats = {}

if VERBOSE_OUTPUT:
	print("Querying and indexing database player cache...")
qrPlayers = runQuery("SELECT username,cached FROM `players`").fetch_row(maxrows=0, how=1)
playerCache = {}
for v in qrPlayers:
	playerCache[str(v['username'].decode("utf-8")).lower()] = v['cached']

for player in players:
	if VERBOSE_OUTPUT:
		print("\nProcessing %s..." % player)
	playerPage = BS(open(config["Integrator"]["path"] + "/" + player, encoding="utf-8"), "html.parser")
	
	statsVerifier = playerPage.findAll("li", {"class": "active dropdown"})
	if len(statsVerifier)==0 or statsVerifier[0].findAll("a")[0].get_text().replace('\n', '').replace(' ', '')!="Players":
		print("[!] Skipping non-player page \"%s\"" % player)
		if DELETE_INVALID_PAGES:
			deleteFile(config["Integrator"]["path"] + "/" + player)
		continue
	accountVerifier = playerPage.findAll("h4")
	if len(accountVerifier)>0 and str(accountVerifier[0].get_text().replace('\n', '').replace(' ', '')).lower()=="accountsuspended":
		print("[!] Skipping suspended account \"%s\"" % player)
		if DELETE_INVALID_PAGES:
			deleteFile(config["Integrator"]["path"] + "/" + player)
		continue
	if len(player) > 16:
		print("[!] Invalid player name \"%s\"" % player)
		if DELETE_INVALID_PAGES:
			deleteFile(config["Integrator"]["path"] + "/" + player)
		continue
	
	pstats[player] = {}
	pstats[player]["cached"] = playerPage.find_all(string=lambda text:isinstance(text,Comment))[0][8:27]
	
	if player not in playerCache or playerCache[str(player).lower()] != pstats[player]["cached"]:
		try:
			# Raw pstats
			pstats[player]["uuid"] = playerPage.findAll("img", {"class": "avatar"})[0]['src'][40:76]
			
			data = playerPage.findAll("div", {"class": "number"})
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
			
			data = playerPage.findAll("h2")
			if len(data) > 0:
				pstats[player]["username"] = BS(str(data[0]), "lxml").findAll("span")[0].get_text().replace('\n', '').replace(' ', '')
			if len(data) > 3:
				for matches in data:
					subs = BS(str(matches), "lxml").findAll("small", {"class": "strong"})
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
			
			data = playerPage.findAll("section")
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
			
			data = playerPage.findAll("h4", {"class": "strong"})
			if len(data) >= 3:
				pstats[player]["first_joined"] = dateparser.parse(data[0]['title'][16:]).strftime('%Y-%m-%d')
				pstats[player]["hours_played"] = int(re.sub("\D", "", data[1].get_text()))
				pstats[player]["teams_joined"] = int(re.sub("\D", "", data[2].get_text()))
			else:
				pstats[player]["first_joined"] = dateparser.parse(datetime.date.today()).strftime('%Y-%m-%d')
				pstats[player]["hours_played"] = 0
				pstats[player]["teams_joined"] = 0
			
			data = playerPage.findAll("div", {"class": "thumbnail trophy"})
			pstats[player]["trophies"] = int(len(data))
			
			data = playerPage.findAll("h5", {"class": "strong"})
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
			
			joined = (datetime.date.today() - datetime.datetime.strptime(pstats[player]["first_joined"], "%Y-%m-%d").date()).days
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
			print("[*] Error translating web cache info! Did the website's page layout change?\nError:" + str(e))
			continue
		
		if VERBOSE_OUTPUT:
			print("Adding to database...")
		runQuery("INSERT INTO players (" + (", ".join(_mysql.escape_string(x).decode("utf-8") for x in pstats[player].keys())) + ") VALUES(" + (", ".join(("\"" + _mysql.escape_string(str(x)).decode("utf-8") + "\"" if isinstance(x, str) else _mysql.escape_string(str(x)).decode("utf-8")) for x in pstats[player].values())) + ") ON DUPLICATE KEY UPDATE " + (", ".join(["{}={}{}{}".format(_mysql.escape_string(k).decode("utf-8"),("\"" if isinstance(v, str) else ""),_mysql.escape_string(str(v)).decode("utf-8"),("\"" if isinstance(v, str) else "")) for k,v in pstats[player].items()])))
		
		if VERBOSE_OUTPUT:
			print("Done.")
	else:
		if VERBOSE_OUTPUT:
			print("No updates. C:%s F:%s" % (playerCache[str(player).lower()], pstats[player]["cached"]))

if VERBOSE_OUTPUT:
	print("Disconnecting from database; processing finished.")
db.close()
