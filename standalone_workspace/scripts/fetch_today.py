#!/usr/bin/env python3
"""临时脚本：拉取今日赔率数据"""
import os, sys, json, unicodedata, time, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('THE_ODDS_API_KEY', '')
print(f'API Key: {"OK" if key else "MISSING"}')

def norm(s): return unicodedata.normalize('NFKC', str(s)).lower().strip()

JC_LEAGUES = {
    'soccer_epl': '英格兰超级联赛',
    'soccer_germany_bundesliga': '德国甲级联赛',
}

params = {'apiKey': key, 'regions': 'eu,uk', 'markets': 'h2h', 'oddsFormat': 'decimal'}

all_matches = []
for league_key, league_name in JC_LEAGUES.items():
    url = f'https://api.the-odds-api.com/v4/sports/{league_key}/odds'
    try:
        r = requests.get(url, params=params, timeout=15)
        print(f'{league_key}: HTTP {r.status_code}')
        if r.status_code != 200:
            print(f'  Error: {r.text[:100]}')
            continue
        data = r.json()
        if not isinstance(data, list):
            print(f'  Not a list')
            continue
        for item in data:
            ct = item.get('commence_time', '')
            if not ct.startswith('2026-04-25'):
                continue
            home = item.get('home_team', '')
            away = item.get('away_team', '')
            home_n, away_n = norm(home), norm(away)
            odds = {}
            for bm in item.get('bookmakers', []):
                if odds:
                    break
                for mkt in bm.get('markets', []):
                    if mkt.get('key') != 'h2h':
                        continue
                    for o in mkt.get('outcomes', []):
                        n = norm(o['name'])
                        p = o['price']
                        if 'draw' in n:
                            odds['draw'] = p
                        elif n == home_n or (home_n and home_n in n):
                            odds['home_win'] = p
                        elif n == away_n or (away_n and away_n in n):
                            odds['away_win'] = p
            if len(odds) >= 2:
                all_matches.append({
                    'league_name': league_name,
                    'home_team': home,
                    'away_team': away,
                    'commence_time': ct,
                    'odds': odds
                })
                print(f'  {home} vs {away}: {odds}')
        time.sleep(1)
    except Exception as e:
        print(f'{league_key}: ERROR {e}')

all_matches.sort(key=lambda x: x['commence_time'])
reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports')
os.makedirs(reports_dir, exist_ok=True)
out_path = os.path.join(reports_dir, 'today_matches.json')
with open(out_path, 'w') as f:
    json.dump(all_matches, f, ensure_ascii=False, indent=2)
print(f'\nTotal: {len(all_matches)} matches saved to {out_path}')
