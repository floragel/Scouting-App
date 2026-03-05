import requests
import os
import json

# Replace with an actual TBA Read API Key
# You get this by logging into The Blue Alliance account page -> Account -> Add API Key
TBA_API_KEY = os.environ.get('TBA_API_KEY', 'ZXyBi2ZeF3qBEj4qFN20fDcuVthDd27EPzD5FiRKgkfLDWVh0rFXZaIdg7KLJizY')
BASE_URL = 'https://www.thebluealliance.com/api/v3'

HEADERS = {
    'X-TBA-Auth-Key': TBA_API_KEY
}

def get_events_for_year(year):
    """Fetch all events for a given year."""
    url = f"{BASE_URL}/events/{year}/simple"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return []

def get_teams_for_event(event_key):
    """Fetch all teams attending a specific event."""
    url = f"{BASE_URL}/event/{event_key}/teams"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return []

def get_event_matches(event_key):
    """Fetch all matches for a specific event."""
    url = f"{BASE_URL}/event/{event_key}/matches"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return []

def get_event_rankings(event_key):
    """Fetch official rankings for a specific event."""
    url = f"{BASE_URL}/event/{event_key}/rankings"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return {}

def get_team_info(team_key):
    """Fetch detailed information for a specific team."""
    url = f"{BASE_URL}/team/{team_key}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return {}

def get_status():
    """Fetch status and current/max season from TBA."""
    url = f"{BASE_URL}/status"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return {}

class TBAHandler:
    def __init__(self, api_key=None):
        self.api_key = api_key or TBA_API_KEY
        self.headers = {'X-TBA-Auth-Key': self.api_key}

    def get_team_status(self, team_key):
        """
        Check if the team is currently at an active event.
        Returns 'Next Match' info or 'Last Match Result'.
        """
        try:
            # First, determine the current year
            status_res = requests.get(f"{BASE_URL}/status", headers=self.headers, timeout=5)
            if status_res.status_code != 200:
                return {"text": "TBA Status Unavailable", "color": "grey", "type": "error"}
            current_year = status_res.json().get('current_season', 2025)

            # Get the years the team participated to find the most recent year with matches
            years_url = f"{BASE_URL}/team/{team_key}/years_participated"
            years_res = requests.get(years_url, headers=self.headers, timeout=5)
            if years_res.status_code == 200 and years_res.json():
                years = sorted(years_res.json(), reverse=True)
            else:
                years = [current_year]

            for latest_year in years:
                # Find the most recently played matches in this year
                matches_url = f"{BASE_URL}/team/{team_key}/matches/{latest_year}/simple"
                matches_res = requests.get(matches_url, headers=self.headers, timeout=5)
                
                if matches_res.status_code == 200 and matches_res.json():
                    matches = matches_res.json()
                    # Sort matches by time (handle None times by putting them at the end or start)
                    valid_matches = [m for m in matches if m.get('time')]
                    if valid_matches:
                        valid_matches.sort(key=lambda x: x['time'], reverse=True) # newest first
                        last_match = valid_matches[0]
                        
                        # Determine if it's in the future (next match) or past (last match)
                        import time
                        current_unix = int(time.time())
                        
                        match_number = last_match['match_number']
                        comp_level = last_match['comp_level'].upper()
                        
                        if last_match['time'] > current_unix:
                            # Future Match
                            alliance = 'Red' if f"{team_key}" in last_match['alliances']['red']['team_keys'] else 'Blue'
                            return {
                                "text": f"Next Match: {comp_level} {match_number}",
                                "color": "green",
                                "alliance": alliance,
                                "type": "next_match",
                                "event_key": last_match['event_key']
                            }
                        else:
                            # Past Match Result
                            red_score = last_match['alliances']['red']['score']
                            blue_score = last_match['alliances']['blue']['score']
                            won = False
                            alliance = 'Red' if f"{team_key}" in last_match['alliances']['red']['team_keys'] else 'Blue'
                            if alliance == 'Red' and red_score > blue_score: won = True
                            elif alliance == 'Blue' and blue_score > red_score: won = True
                            
                            outcome = "Won" if won else "Lost"
                            
                            return {
                                "text": f"Last Match ({comp_level} {match_number}): {outcome} ({red_score}-{blue_score})",
                                "color": "grey",
                                "type": "last_match",
                                "event_key": last_match['event_key']
                            }
                            
            # If we exhausted all years and found no matches:
            return {"text": f"No match data found for {team_key}", "color": "grey", "type": "no_data"}

        except Exception as e:
            return {"text": f"TBA Error: {str(e)}", "color": "grey", "type": "error"}

    def get_team_latest_event(self, team_key):
        """
        Gets the first event key for a team in the current season,
        regardless of whether they have played any matches yet.
        """
        try:
            status_res = requests.get(f"{BASE_URL}/status", headers=self.headers, timeout=5)
            current_year = 2025
            if status_res.status_code == 200:
                current_year = status_res.json().get('current_season', 2025)
            
            events_url = f"{BASE_URL}/team/{team_key}/events/{current_year}/simple"
            res = requests.get(events_url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                events = res.json()
                if events:
                    # Return the first registered event for the season
                    return events[0]['key']
            return None
        except Exception:
            return None

def test_api():
    events = get_events_for_year(2024)
    print(f"Fetched {len(events)} events for 2024.")
    if events:
        first_event = events[0]
        print(f"First event: {first_event['name']} ({first_event['key']})")
        
        teams = get_teams_for_event(first_event['key'])
        print(f"Fetched {len(teams)} teams for {first_event['key']}.")

if __name__ == '__main__':
    test_api()
