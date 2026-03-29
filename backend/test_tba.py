import requests

HEADERS = {'X-TBA-Auth-Key': 'ZXyBi2ZeF3qBEj4qFN20fDcuVthDd27EPzD5FiRKgkfLDWVh0rFXZaIdg7KLJizY'}

e_res = requests.get("https://www.thebluealliance.com/api/v3/team/frc6622/events/2025/simple", headers=HEADERS)
events = sorted(e_res.json(), key=lambda x: x['end_date'], reverse=True)
print([e['key'] for e in events])
for e in events:
    m_res = requests.get(f"https://www.thebluealliance.com/api/v3/event/{e['key']}/matches/simple", headers=HEADERS)
    matches = m_res.json()
    print(f"Event {e['key']} has {len(matches)} matches.")
    if matches:
        print("First match keys:", matches[0].keys())
        print("First match 'time':", matches[0].get('time'))
