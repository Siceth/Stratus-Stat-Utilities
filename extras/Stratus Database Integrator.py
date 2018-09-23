import datetime
import configparser
import glob
import os
import re
import time

# START CONFIG

VERBOSE_OUTPUT = False

# END CONFIG

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
	config.read('config.ini')
except:
	print("Configuration file missing or unreadable!")
	exit()

try:
	db = _mysql.connect(host=config["MySQL"]["host"], user=config["MySQL"]["username"], passwd=config["MySQL"]["password"], db=config["MySQL"]["database"], conv={ FIELD_TYPE.LONG: int, FIELD_TYPE.INT24: int, FIELD_TYPE.CHAR: bool })
except:
	print("[*] Can't connect to database!")
	exit()

def runQuery(query):
	try:
		db.query(query)
		return db.store_result()
	except:
		print("[*] Can't run query:\n=-=-=\n%s\n=-=-=\n" % query)
		exit()

donorRanks = ["strato", "alto", "cirro"]
staffRanks = ["administrator", "developer", "senior moderator", "junior developer", "moderator", "map developer", "event coordinator", "official"]

players = list(player for player in os.listdir(config["Integrator"]["path"]) if os.path.isfile(os.path.join(config["Integrator"]["path"], player)))
players.sort()
stats = {}

for player in players:
	if VERBOSE_OUTPUT:
		print("Processing %s..." % player)
	else:
		print(player)
	playerPage = BS(open(config["Integrator"]["path"] + "/" + player, encoding="utf-8"), "html.parser")	
	stats[player] = {}
	stats[player]["cached"] = playerPage.find_all(string=lambda text:isinstance(text,Comment))[0][8:27]
	
	statsVerifier = playerPage.findAll("li", {"class": "active dropdown"})
	if len(statsVerifier)==0 or statsVerifier[0].findAll("a")[0].get_text().replace('\n', '').replace(' ', '')!="Players":
		print("[!] Skipping non-player page \"%s\"" % player)
		continue
	if len(player) > 16:
		print("[!] Invalid player name \"%s\"" % player)
		continue
	
	qr = runQuery("SELECT cached FROM `players` WHERE username=\"" + _mysql.escape_string(player).decode("utf-8") + "\" LIMIT 1").fetch_row(maxrows=1, how=1)
	if len(qr)==0 or qr[0]["cached"]!=stats[player]["cached"]:
		try:
			# Raw Stats
			stats[player]["uuid"] = playerPage.findAll("img", {"class": "avatar"})[0]['src'][40:76]
			
			data = playerPage.findAll("div", {"class": "number"})
			if len(data) >= 7:
				stats[player]["kills"] = int(data[0].get_text())
				stats[player]["deaths"] = int(data[1].get_text())
				stats[player]["friends"] = int(data[2].get_text())
				stats[player]["kill_rank"] = int((data[3].get_text())[:-2])
				stats[player]["droplets"] = int(float('.'.join(re.findall('\d+', data[6].get_text()))) * (1000 if (data[6].get_text())[-1:]=='k' else (1000000 if (data[6].get_text())[-1:]=='m' else (1000000000 if (data[6].get_text())[-1:]=='b' else 1))))
			else:
				stats[player]["kills"] = 0
				stats[player]["deaths"] = 0
				stats[player]["friends"] = 0
				stats[player]["kill_rank"] = 0
				stats[player]["droplets"] = 0
			
			data = playerPage.findAll("h2")
			if len(data) > 0:
				stats[player]["username"] = BS(str(data[0]), "lxml").findAll("span")[0].get_text().replace('\n', '').replace(' ', '')
			if len(data) > 3:
				for matches in data:
					subs = BS(str(matches), "lxml").findAll("small", {"class": "strong"})
					if len(subs) > 0:
						for sub in subs:
							if sub.text.lower()=="cores leaked":
								stats[player]["cores"] = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower()=="monuments destroyed":
								stats[player]["monuments"] = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower()=="wools placed":
								stats[player]["wools"] = int(re.sub("\D", "", matches.get_text()))
								break
							elif sub.text.lower()=="flags captured":
								stats[player]["flags"] = int(re.sub("\D", "", matches.get_text()))
								break
			if "username" not in stats[player]:
				stats[player]["username"] = player
			if "monuments" not in stats[player]:
				stats[player]["monuments"] = 0
			if "wools" not in stats[player]:
				stats[player]["wools"] = 0
			if "flags" not in stats[player]:
				stats[player]["flags"] = 0
			if "cores" not in stats[player]:
				stats[player]["cores"] = 0
			
			data = playerPage.findAll("section")
			if len(data) > 0:
				ranks = BS(str(data[0]), "lxml").findAll("a", {"class": "label"}) + BS(str(data[0]), "lxml").findAll("span", {"class": "label"})
				stats[player]["ranks"] = len(ranks)
				playerTags = (BS(str(ranks), "lxml").text).lower()
				stats[player]["staff"] = True if any(x in playerTags for x in staffRanks) else False
				stats[player]["donor"] = True if any(x in playerTags for x in donorRanks) else False
			else:
				stats[player]["ranks"] = 0
				stats[player]["staff"] = False
				stats[player]["donor"] = False
			
			stats[player]["tournament_winner"] = True if [x for x in data if "tournament winner" in (x.text).lower()] else False
			
			data = playerPage.findAll("h4", {"class": "strong"})
			if len(data) >= 3:
				stats[player]["first_joined"] = dateparser.parse(data[0]['title'][16:]).strftime('%Y-%m-%d')
				stats[player]["hours_played"] = int(re.sub("\D", "", data[1].get_text()))
				stats[player]["teams_joined"] = int(re.sub("\D", "", data[2].get_text()))
			else:
				stats[player]["first_joined"] = dateparser.parse(datetime.date.today()).strftime('%Y-%m-%d')
				stats[player]["hours_played"] = 0
				stats[player]["teams_joined"] = 0
			
			data = playerPage.findAll("div", {"class": "thumbnail trophy"})
			stats[player]["trophies"] = int(len(data))
			
			data = playerPage.findAll("h5", {"class": "strong"})
			stats[player]["has_team"] = True if [x for x in data if "team" in (x.text).lower()] else False
			
			# Calculated Stats
			stats[player]["kd"] = stats[player]["kills"] / (1 if stats[player]["deaths"]==0 else stats[player]["deaths"])
			
			stats[player]["average_kills_per_hour"] = stats[player]["kills"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_deaths_per_hour"] = stats[player]["deaths"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_monuments_per_hour"] = stats[player]["monuments"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_wools_per_hour"] = stats[player]["wools"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_cores_per_hour"] = stats[player]["cores"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_flags_per_hour"] = stats[player]["flags"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_droplets_per_hour"] = stats[player]["droplets"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_new_friends_per_hour"] = stats[player]["friends"] / (1 if stats[player]["hours_played"]==0 else stats[player]["hours_played"])
			stats[player]["average_experienced_game_length_in_minutes"] = stats[player]["hours_played"] * 60 / (1 if stats[player]["teams_joined"]==0 else stats[player]["teams_joined"])
			stats[player]["average_kills_per_game"] = stats[player]["kills"] / (1 if stats[player]["teams_joined"]==0 else stats[player]["teams_joined"])
			
			stats[player]["khpdg"] = stats[player]["kd"] / (60.0 / (1 if stats[player]["average_experienced_game_length_in_minutes"]==0 else stats[player]["average_experienced_game_length_in_minutes"]))
			
			joined = (datetime.date.today() - datetime.datetime.strptime(stats[player]["first_joined"], "%Y-%m-%d").date()).days
			stats[player]["percent_time_spent_on_stratus"] = 0 if joined < 7 else (stats[player]["hours_played"] * 100 / (24 if joined==0 else (joined * 24)))
			stats[player]["percent_waking_time_spent_on_stratus"] = 0 if joined < 7 else (stats[player]["hours_played"] * 100 / (16 if joined==0 else (joined * 16)))
			
			# Unfortunately these stats have to retire since droplets can be spent, which can result in negative objective percentages.
			#stats[player]["percent_droplets_are_kills"] = stats[player]["kills"] * 100 / (1 if stats[player]["droplets"]==0 else stats[player]["droplets"])
			#stats[player]["percent_droplets_are_objectives"] = 100 - stats[player]["percent_droplets_are_kills"]
			
			# Merit is based on hours played on a scale to account for veteran players that idle. Using inverse regression
			# analysis, the above formula was found so that the stats of a user that has only played for less than an hour
			# is only worth 10% of what's reported; 100 hours constitutes 100% accuracy and 1000+ hours grants 120%.
			stats[player]["kill_based_merit"] = (1.2 - (500 / stats[player]["kills"])) if stats[player]["kills"] > 454 else 0.1
			stats[player]["time_based_merit"] = (1.2 - (5 / stats[player]["hours_played"])) if stats[player]["hours_played"] > 4 else 0.1
			stats[player]["merit_multiplier"] = (stats[player]["kill_based_merit"] + stats[player]["time_based_merit"]) / 2
			
			# Reliability is solely based on teams joined and is used similar to merit to evaluate how well this player's
			# stats can be extrapolated to fit larger data sums
			stats[player]["reliability_index"] = (1.0 - (50 / stats[player]["teams_joined"])) if stats[player]["teams_joined"] > 50 else 0.01
			
			stats[player]["hours_until_one_million_droplets"] = 0 if stats[player]["droplets"] > 1000000 else ((1000000 - stats[player]["droplets"]) / (1 if stats[player]["average_droplets_per_hour"]==0 else stats[player]["average_droplets_per_hour"]))
		
		except Exception as e:
			print("[*] Error translating web cache info! Did the website's page layout change?\nError:" + e)
		
		if VERBOSE_OUTPUT:
			print("Adding to database...")
		qr = runQuery("INSERT INTO players (" + (", ".join(_mysql.escape_string(x).decode("utf-8") for x in stats[player].keys())) + ") VALUES(" + (", ".join(("\"" + _mysql.escape_string(str(x)).decode("utf-8") + "\"" if isinstance(x, str) else _mysql.escape_string(str(x)).decode("utf-8")) for x in stats[player].values())) + ") ON DUPLICATE KEY UPDATE " + (", ".join(["{}={}{}{}".format(_mysql.escape_string(k).decode("utf-8"),("\"" if isinstance(v, str) else ""),_mysql.escape_string(str(v)).decode("utf-8"),("\"" if isinstance(v, str) else "")) for k,v in stats[player].items()])))
		
		if VERBOSE_OUTPUT:
			print("Done.")
	else:
		if VERBOSE_OUTPUT:
			print("No updates.")

db.close()