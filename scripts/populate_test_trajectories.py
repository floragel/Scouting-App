import os
import json
import random
from backend.app import app, db, Team, MatchScoutData

# Mock "realistic" paths for REEFSCAPE
# Normalized 0.0 to 1.0
TRAJECTORY_TEMPLATES = [
    {
        "pos_name": "Center Wall",
        "start": {"x": 0.5, "y": 0.1},
        "paths": [
            {"color": "#3b82f6", "points": [{"x": 0.5, "y": 0.1}, {"x": 0.5, "y": 0.25}, {"x": 0.5, "y": 0.4}]}
        ]
    },
    {
        "pos_name": "Left Wall",
        "start": {"x": 0.2, "y": 0.15},
        "paths": [
            {"color": "#3b82f6", "points": [{"x": 0.2, "y": 0.15}, {"x": 0.3, "y": 0.3}, {"x": 0.45, "y": 0.4}]}
        ]
    },
    {
        "pos_name": "Right Wall",
        "start": {"x": 0.8, "y": 0.15},
        "paths": [
            {"color": "#3b82f6", "points": [{"x": 0.8, "y": 0.15}, {"x": 0.7, "y": 0.3}, {"x": 0.55, "y": 0.4}]}
        ]
    },
    {
        "pos_name": "Left Station Run",
        "start": {"x": 0.15, "y": 0.1},
        "paths": [
            {"color": "#3b82f6", "points": [{"x": 0.15, "y": 0.1}, {"x": 0.35, "y": 0.4}]},
            {"color": "#10b981", "points": [{"x": 0.35, "y": 0.4}, {"x": 0.1, "y": 0.8}]}
        ]
    }
]

def populate():
    with app.app_context():
        matches = MatchScoutData.query.all()
        print(f"Found {len(matches)} matches to update.")
        
        for m in matches:
            # Pick a random template
            template = random.choice(TRAJECTORY_TEMPLATES)
            
            # Add some jitter to make it look "real"
            jitter_x = (random.random() - 0.5) * 0.05
            jitter_y = (random.random() - 0.5) * 0.05
            
            start_pos = {
                "x": round(template["start"]["x"] + jitter_x, 3),
                "y": round(template["start"]["y"] + jitter_y, 3)
            }
            
            auto_traj = []
            for p in template["paths"]:
                new_points = []
                for pt in p["points"]:
                    new_points.append({
                        "x": round(pt["x"] + (random.random() - 0.5) * 0.03, 3),
                        "y": round(pt["y"] + (random.random() - 0.5) * 0.03, 3)
                    })
                auto_traj.append({
                    "color": p["color"],
                    "points": new_points
                })
            
            m.starting_position = json.dumps(start_pos)
            m.auto_trajectory = json.dumps(auto_traj)
            
        db.session.commit()
        print("Successfully updated all matches with realistic trajectories.")

if __name__ == "__main__":
    populate()
