---
description: Git pull before and push after every code modification
---

## Before any code modification

// turbo
1. Pull the latest changes from the remote repository:
```bash
cd /Users/User/Scouting-App && git pull
```

## After all code modifications are complete

2. Stage, commit and push all changes:
```bash
cd /Users/User/Scouting-App && git add -A && git commit -m "<descriptive commit message>" && git push
```

### Notes
- Git user is configured as: `alban` / `alban@alban.alban`
- Always pull BEFORE making changes and push AFTER completing changes
- Use descriptive commit messages in French or English based on the user's language
