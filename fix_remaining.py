import os
import re

base_dir = "/Users/nayl/Desktop/Scouting App"
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace email domains
            content = content.replace('stanrobotix.com', 'frc-scouting.com')
            
            # Replace remaining case-sensitive ones
            content = content.replace('6002 - StanRobotix', '6622 - FRC Scouting App')
            content = content.replace('StanRobotix has added', 'FRC Scouting App has added')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

print("Remaining fixes applied.")
