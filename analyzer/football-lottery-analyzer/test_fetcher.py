import sys
import os
sys.path.insert(0, os.path.abspath("."))
from data_fetch.news_fetcher import NewsFetcher

class MyNewsFetcher(NewsFetcher):
    def fetch_data(self): pass

nf = MyNewsFetcher(config_file=None)
print(nf.fetch_news('skysports'))
