# Stratus Stat Utilities

This was a fun little project that I wanted to do for a while.  It scrapes data from the [Stratus Network](https://stratus.network/) Minecraft server and does your typical computer beeps and boops with it to produce some slick PvP statistics.

## Current Features

* Individual player statistics lookup
* Reverse statistics lookup
* Staff listing
* Match statistics and win prediction
* Apache/PHP files necessary to make a mirror

## Planned Features

* Custom group statistics
* 1v1 comparison
* Local caching
* Nginx/Ruby mirror files
* More planned features

## Requirements

* Python 3.1 to 3.6
* lxml 4.x
* PycURL
* libcurl 7.19.x (should come with PycURL)
* python-tabulate
* BeautifulSoup 4.4.x

You should be able to do the trick with `pip install lxml pycurl tabulate beautifulsoup4`

## Configuration

What little is available to configure should be pretty self-explanitory.

### Stratus Stat Utilities.py
* **TITLE_TEXT** and **VERSION** are currently just for the a e s t h e t i c.
* When **MULTITHREADED** is enabled, Python's futures are used to "asynchronously" (but not really) call cURL requests.  Tests have shown it to be _slightly_ faster.  When disabled, it'll just go through one person at a time.
* **MIRROR** is the full URL to a content deliverer that mirrors the actual website.  A cache mirror is useful because the Stratus Network website can get really slow at peak times and we don't want to overwhelm their servers.  Leaving this option blank will just request data straight from [https://stratus.network/](https://stratus.network/).

### index.php
* **$cacheDir** should point to a pre-existing directory with proper permissions already established.  All of the data requests coming through your mirror will be stored there.
* **$cacheDays** is the number of days you want data to be cached.  Floats are acceptable.
* If you set up the mirror in a subdirectory, you'll have to edit the `.htaccess` file's redirection statement to pass data to that subdirectory.

## Support

I'm open to suggestions for feature requests.  You can open an issue or contact me on Discord @Siceth#2618. I can usually get back within a day.
