# 🤖 FRC Scouting App

A full-stack web application for **FIRST Robotics Competition (FRC)** teams to manage scouting data, match assignments, and team analytics — built with Flask and vanilla HTML/JS.

---

## 📁 Project Structure

```
Scouting App/
├── frontend/                    # All HTML pages (Jinja-rendered)
│   ├── admin_scout_management_hub/
│   ├── desktop_scout_dashboard_hub/
│   ├── frc_events_&_dashboard/
│   ├── head_scout_analytics_hub/
│   ├── match_scouting_entry/
│   ├── pit_scouting_form/
│   ├── profile_&_settings_edit/
│   ├── team_onboarding_&_access/
│   ├── teams_directory_&_profile/
│   ├── user_login_&_registration_flow/
│   └── user_profile_&_settings_hub/
├── backend/                     # Flask API + server
│   ├── app.py                   # Main application & routes
│   ├── models.py                # SQLAlchemy database models
│   ├── frc_api.py               # The Blue Alliance API integration
│   ├── requirements.txt         # Python dependencies
│   ├── promote_admin.py         # Utility: promote user to Admin
│   ├── static/                  # Static assets
│   └── uploads/                 # User-uploaded files
├── data/                        # Database
│   └── scouting.db              # SQLite database
├── .env                         # Environment variables (TBA API key)
├── start.sh                     # Launch script
├── venv/                        # Python virtual environment
└── README.md
```

---

## 🚀 Getting Started with Antigravity

### Prerequisites

- **Python 3.10+**
- **Antigravity** (AI coding assistant)
- **SQLite Viewer** extension (recommended for inspecting `data/scouting.db`)

### 1. Clone & Open

Open the `Scouting App` folder in your editor with Antigravity enabled.

### 2. Set Up Virtual Environment

```bash
cd "Scouting App"
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Copy the example file and add your API key:

```bash
cp .env.example .env
```

Then edit `.env` and replace `your_tba_api_key_here` with your actual key from [thebluealliance.com/account](https://www.thebluealliance.com/account)

### 5. Set Up the Database

Copy the empty template database:

```bash
cp data/scouting_empty.db data/scouting.db
```

> The `scouting_empty.db` contains all tables with zero data. Your actual `scouting.db` is gitignored to protect user data.

### 6. Run the App

```bash
bash start.sh
```

Or manually:

```bash
source venv/bin/activate
python3 backend/app.py
```

The app runs on **http://localhost:5002**

---

## 🗄️ Database

The SQLite database is stored at `data/scouting.db`. You can inspect it using:

- **SQLite Viewer** extension in VS Code / Cursor
- Any SQLite browser (e.g., DB Browser for SQLite)

### Promote a User to Admin

```bash
source venv/bin/activate
python3 backend/promote_admin.py
```

---

## 🔑 Key Features

| Feature | Route | Description |
|---|---|---|
| **Login / Register** | `/login`, `/register` | Authentication with password hashing |
| **Dashboard** | `/` | Dynamic scout dashboard with live Statbotics stats and upcoming TBA matches |
| **Events & Schedule** | `/events-dashboard` | FRC events with TBA live data |
| **Admin Hub** | `/admin-hub` | Team management, role assignment, match grid, and **Pit Assignments** |
| **Match Scouting** | `/match-scout` | In-match data collection form |
| **Pit Scouting** | `/pit-scout/<id>` | Pre-match pit inspection form with **photo upload** capabilities |
| **Team Directory** | `/teams` | Browse all teams with stats |
| **Analytics Hub** | `/head-scout-stats`| Advanced performance metrics (SD), consistency badges, and team profiles |
| **Pick List Board** | `/picklist` | Drag-and-drop alliance selection tool with TBA ranking fallback and PDF export |
| **JSON Data Sync**| `/head-scout-stats`| Offline Data Export/Import via JSON files |
| **QR Sync (BETA)** | Multiple | Offline data transfer via QR codes (Generation in forms, Scanning in Hub) |
| **Translation** | All Pages | Integrated Multi-Language Support (EN, FR, ES, HI, ZH, RU, AR) |
| **AI Voice Transcribe**| Pit Form | Smart data entry using **OpenAI Whisper** for mechanism descriptions |
| **Profile** | `/profile` | User profile & settings |

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML5, Vanilla JS, TailwindCSS (CDN)
- **Database:** SQLite
- **APIs:** The Blue Alliance (TBA) REST API, **Statbotics API** (v3)
- **AI/ML:** OpenAI Whisper (Voice Transcription)
- **Libraries:** qrcode.js (Generation), html5-qrcode (Scanning), Chart.js
- **Auth:** Session-based with Werkzeug password hashing

---

## 📝 Environment Variables

| Variable | Description |
|---|---|
| `FLASK_ENV` | `development` or `production` |
| `FLASK_APP` | `backend/app.py` |
| `TBA_API_KEY` | Your Blue Alliance API key |

---

© Nayl Lahlou — Team 6622 StanRobotix
