import requests

ODDS_API_KEY = "fb47ab523dd9db967003590d76ec9074"
url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"

try:
    response = requests.get(url)
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        print("The Odds API: Success. Sample:", data[0]['home_team'], "vs", data[0]['away_team'])
    else:
        print("The Odds API: Empty or Error:", data)
except Exception as e:
    print("The Odds API Error:", e)

