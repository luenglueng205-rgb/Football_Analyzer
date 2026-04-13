import sys
import os
sys.path.insert(0, os.path.abspath("."))
from data_fetch.match_scraper import MatchScraper
ms = MatchScraper(config_file=None)
print(ms.fetch_data(source='premierleague'))
