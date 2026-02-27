import sys
import os

# Add backend directory to path so we can import app modules safely
sys.path.append(os.path.abspath('backend'))

from frc_api import TBAHandler, get_teams_for_event, get_event_rankings

def test_fallback_logic():
    team_key = 'frc6622'
    tba = TBAHandler()
    event_key = tba.get_team_latest_event(team_key)
    print(f"Latest event for {team_key}: {event_key}")
    
    if not event_key: return
    
    event_teams = get_teams_for_event(event_key)
    event_rankings = get_event_rankings(event_key)
    
    print(f"Found {len(event_teams)} teams for {event_key}")
    
    rankings_dict = {}
    if event_rankings and 'rankings' in event_rankings:
        for r in event_rankings['rankings']:
            rankings_dict[r['team_key']] = r['rank']
            
    team_averages = {}
    for t in event_teams:
        tk = t['key']
        t_num = t['team_number']
        team_averages[tk] = {
            'team_id': t_num,
            'name': t.get('nickname', 'Unknown'),
            'tba_rank': rankings_dict.get(tk, 999)
        }
        
    sorted_teams = list(team_averages.values())
    sorted_teams.sort(key=lambda x: x['tba_rank'])
    
    print("\nTop 5 Teams by TBA Rank:")
    for team in sorted_teams[:5]:
        print(f"Rank {team['tba_rank']}: Team {team['team_id']} ({team['name']})")
        
test_fallback_logic()
