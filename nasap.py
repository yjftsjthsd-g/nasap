#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""nasap - news as simple as possible

This is a simple tool to fetch full text posts based on a RSS/Atom feed and
store it as a simple textfile to later view it with a tool of your choice.

upstream git repo: https://github.com/phavx/nasap/
git repo: https://github.com/yjftsjthsd-g/nasap

Information about AUTHORS, TODO and LICENSE can be found in the respective file
"""

# standard libs
from io      import open
from os      import environ, makedirs, path
from urllib.request import urlopen
from sys     import argv, exit
from time    import gmtime, strftime
from multiprocessing import Process, Lock

# external dependencies
import feedparser
from   pypandoc import convert
from   readability.readability import Document

# functions
def error(msg, code):
    """prints an error message and exits the program with the given code"""
    print(msg)
    exit(code)

def current_date_time():
    """create current date and time in case the feed item doesn't provide it"""
    return strftime("%Y-%m-%d", gmtime()), strftime("%H:%M", gmtime())

def check_create_dir(directory):
    """if the passed directory doesn't exist, try to create it"""
    if path.exists(directory):
        if path.isdir(directory):
            return True
        else:
            return False
    else:
        makedirs(directory)
        return True

def s_title(title):
    """replace '/' in the title to circumvent unix file path problems"""
    if "/" in title:
        return "_".join(title.split("/"))
    else:
        return title

def mkheader(feedtitle, feedlink, itemtitle, itemlink, date, time):
    """builds a nice looking header consiting of some box drawing and infos"""
    ft, fl, it, il, d ,t = feedtitle, feedlink, itemtitle, itemlink, date, time

    # calculate how much spacing we need so we can fill the lines nicely
    f_1 = " " * ( 76 - (len(ft[:53] + fl)) )
    f_2 = " " * ( 73 - (len(it[:53] + "..." + d + "-" + t) ) )

    # building a five line header, two for content, three for style
    return "┏━" + 76 * "━"                                       + "━┓\n" \
         + "┃ " + ft[:53]           + f_1 + fl                    + " ┃\n" \
         + "┣━" + 57 * "━"               + "┳"  + 18 * "━"     + "━┫\n" \
         + "┃ " + it[:53]   + "..." + f_2 + "┃ " +  d + " @" + t + " ┃\n" \
         + "┗━" + 57 * "━"               + "┻"  + 18 * "━"     + "━┛\n\n"

def mkfooter(itemlink):
    """adds footer containing link to the original source plus content links"""
    return "\n" + 80 * "━" + "\nLinks:\n[*] " + itemlink

def store_seen(seenlink, SEEN_FILE, seenfile_lock):
    """Store that a link has been seen"""
    seenfile_lock.acquire()
    sh = open(SEEN_FILE, 'a')
    sh.write(seenlink + "\n")
    sh.close()
    seenfile_lock.release()


def process_link(lock, FEED, i):
    """process a link, outputting its contents to a file and mark it as seen"""
    # if we already processed the link earlier, skip processing it
    if FEED.entries[i].link in seen_links:
        return #continue

    html = Document(urlopen(FEED.entries[i].link).read()).summary()
    body = convert(html, "plain", format="html", \
                   extra_args=["--reference-links", "--columns=80"])

    date, time = current_date_time()
    # some feed items have really long titles, so better truncate them
    filename = "[%s]-[%s] " % (date, time) + s_title(FEED.entries[i].title[:59])

    # build the final product, a nice header, the content and enclosed links    
    product = mkheader(FEED.feed.title, FEED.feed.link, FEED.entries[i].title, \
                  FEED.entries[i].link, date, time) \
            + body \
            + mkfooter(FEED.entries[i].link)

    # finally, write out the finished product and store the link as already seen
    fh = open(FEED_DIR + "/" + filename, "w")
    fh.write(product)
    fh.close()

    store_seen(FEED.entries[i].link, SEEN_FILE, lock)

# the basedir where all feed items will be stored
NEWS_DIR = environ["HOME"] + "/news"

# some basic sanity checks
if not check_create_dir(NEWS_DIR):
    error("Error: %s exists, but isn't a directory!" % NEWS_DIR, 1)

if len(argv) != 2:
    exit(1)

URL = argv[1]
REFERRER = "/".join(URL.split("/")[:3])
FEED = feedparser.parse(URL, referrer=REFERRER)

# if we don't already have a directory for this feed, create it
FEED_DIR = NEWS_DIR + "/" + FEED.feed.title
if not check_create_dir(FEED_DIR):
    error("Error: feed directory %s could not be created." % FEED_DIR, 1)

# list of links we've already seen so we can skip them
SEEN_FILE = FEED_DIR + "/.seen.links"
if path.exists(SEEN_FILE):
    if not path.isfile(SEEN_FILE):
        error("Error: %s needs to be a file." % SEEN_FILE, 1)
else:
    open(SEEN_FILE, 'a').close()

seen_links = open(SEEN_FILE).read()

# loop over the feed's items and process them
seenfile_lock = Lock()
for i in range(0, len(FEED["entries"])):
    Process(target=process_link, args=(seenfile_lock, FEED, i)).start() #passing i is probably bad
