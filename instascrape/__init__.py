# Check Python version
import sys
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    print("FAILED: InstaScrape requires Python 3.6 or above. Python {0} detected !".format(".".join(map(str, sys.version_info[:3]))))
    sys.exit(1)

# Environment set up
import os
DIR_PATH = os.path.join(os.path.expanduser("~"), ".instascrape/")
ACCOUNT_DIR = os.path.join(DIR_PATH, "accounts/")
if not os.path.isdir(DIR_PATH):
    os.mkdir(DIR_PATH)
if not os.path.isdir(ACCOUNT_DIR):
    os.mkdir(ACCOUNT_DIR)

from instascrape.instascraper import InstaScraper
from instascrape.download import _down_containers
from instascrape.structures import *
from instascrape.exceptions import *

from colorama import init
init(autoreset=True)
