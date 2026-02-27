import requests

HEADERS = {'X-TBA-Auth-Key': 'ZXyBi2ZeF3qBEj4qFN20fDcuVthDd27EPzD5FiRKgkfLDWVh0rFXZaIdg7KLJizY'}

def get_team_status(team_key):
    url = f"https://www.thebluealliance.com/api/v3/team/{team_key}/events/2026/simple"
    res = requests.get(url, headers=HEADERS)
    print(f"Events 2026: {res.status_code}")
    if res.status_code == 200:
        events = res.json()
        print(f"Found {len(events)} events for {team_key} in 2026")
        if events:
            return events[0]['key']
    return None

def test():
    team_key = 'frc6622'
    event_key = get_team_status(team_key)
    print(f"Event key: {event_key}")
    
    if event_key:
        teams_url = f"https://www.thebluealliance.com/api/v3/event/{event_key}/teams/simple"
        teams_res = requests.get(teams_url, headers=HEADERS)
        print(f"Teams status: {teams_res.status_code}")
        if teams_res.status_code == 200:
            print(f"Found {len(teams_res.json())} teams")
            print(f"First team: {teams_res.json()[0]['team_number']}")

test()
