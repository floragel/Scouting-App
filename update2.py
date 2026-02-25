import os
import re

base_dir = "/Users/nayl/Desktop/Scouting App"
files_to_process = []
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.html'):
            files_to_process.append(os.path.join(root, file))

print(f"Found {len(files_to_process)} html files.")
if files_to_process:
    with open(files_to_process[0], 'r', encoding='utf-8') as f:
        content = f.read()
    print("Content starts with:", content[:100])
    
    new_content = content.replace('lang="fr"', 'lang="en"')
    new_content = new_content.replace('StanRobotix', 'FRC Scouting App')
    print("Same content?" , content == new_content)
