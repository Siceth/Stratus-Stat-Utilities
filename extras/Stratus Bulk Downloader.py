# START CONFIG

START_PAGE: int = 1
END_PAGE: int = 0

# END CONFIG

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
import ctypes
import datetime
import glob
import math
import random
import re
import time

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from shutil import copyfile

try:
	from lxml import etree
	import lxml.html as lh
except ImportError:
	missingPackage("lxml")

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

def curlRequest(url: str, forceNoMirror: bool = False, noHTML: bool = False) -> list:
	global UNIX, MIRROR
	try:
		buffer: io.IOBase = BytesIO()
		c = pycurl.Curl()
		c.setopt(pycurl.URL, (("https://stratus.network/" if forceNoMirror else "https://stats.seth-phillips.com/stratus/") + str(url)))
		c.setopt(pycurl.USERAGENT, ("Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0" if UNIX else "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20130401 Firefox/31.0"))
		c.setopt(pycurl.FOLLOWLOCATION, True)
		c.setopt(pycurl.POST, 0)
		c.setopt(pycurl.SSL_VERIFYPEER, 0)
		c.setopt(pycurl.SSL_VERIFYHOST, 0)
		c.setopt(pycurl.WRITEDATA, buffer)
		c.perform()
		response: int = c.getinfo(pycurl.RESPONSE_CODE)
		if not noHTML:
			html: str = buffer.getvalue().decode("iso-8859-1")
		c.close()
		if response < 500:
			if noHTML:
				return [response]
			else:
				return [response, html.replace('\n', '')]
		print("[*] cURL responded with a server error while performing the request (%i). Is the website down?" % response)
		exit()
	except Exception as e:
		print("[*] cURL performance failed. Is your internet operational? Error: " + str(e))
		exit()

def getLastPage() -> int:
	statsPage: list = curlRequest("stats?force-renew&game=global&page=1&sort=kills&time=eternity", True)
	if statsPage[0] > 399:
		print("[*] cURL responded with a server error while requesting the main states page (%i). Is the website down?" % statsPage[0])
		exit()
	else:
		try:
			href: BeautifulSoup = BS(statsPage[1], "lxml").find("ul", {"class": "pagination"}).findAll("li")[6].find("a", href = True)["href"]
			return int(re.findall('\d+', href)[0])
		except:
			print("[*] Last page can't be found! Did the stats page structure change?")
			exit()

def downloadPlayersBetweenPages(start: int = 1, end: int = 1) -> None:
	rank: int = 1
	page: int = start - 1
	seconds_elapsed: int = 0
	
	if end == 0:
		if start <= 10:
			print(" > These limits look like you're trying to download *everything*. I hope you know what you're doing.")
		else:
			print(" > END_PAGE was set to download up until the last page. If that's not what you intended, you should Ctrl+C now.")
		end = getLastPage()
	
	if end - start > 1000:
		print(" > Looks like you're trying to download over 20,000 player profiles -- might want to run this in a screen session.")
	
	print("\n")
	
	while page < end:
		page += 1
		print("Running page %d/%d" % (page, end))
		rate: int = (page - start) / (1 if seconds_elapsed == 0 else seconds_elapsed)
		end_sec: int = (end-page+1) / (1 if rate == 0 else rate)
		print("Elapsed: %ds; Rate: %.2f pages/s (%.2f players/s); Est. finish: %ds (%s)" % (seconds_elapsed, rate, rate*20, int(end_sec), datetime.datetime.fromtimestamp(time.time()+end_sec).strftime('%Y-%m-%d %H:%M:%S')))
		start_time: int = time.time()
		statsList: list = curlRequest("stats?force-renew&game=global&page=" + str(page) + "&sort=kills&time=eternity", True)
		if statsList[0] > 399:
			print("[*] cURL responded with a server error while requesting the stats page (%i). Is the website down?" % statsList[0])
			print("    Retry execution with downloadPlayersBetweenPages(%i,%i)" % (page, end))
			exit()
		player: str
		for player in [x['alt'].replace(' ', '') for x in BS(statsList[1], "lxml").findAll("img", {"class": "avatar"})]:
			if curlRequest(player + "?force-renew", False, True)[0] > 399:
				print("[!] cURL 4xx error for player \"%s\"" % player)
			else:
				print("    - [%d] %s" % (rank, player))
			rank += 1
		seconds_elapsed += (time.time() - start_time)
	
	print("A total of %ds have been elapsed since execution." % seconds_elapsed)

print("BEGINNING BULK DOWNLOAD\n")
downloadPlayersBetweenPages(START_PAGE, END_PAGE)
print("\nHIT END OF BULK DOWNLOAD")
