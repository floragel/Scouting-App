# 🤖 FRC Scouting App

A **full-stack web application** built for **FIRST Robotics Competition (FRC)** teams to streamline match scouting, pit scouting, team analytics, and alliance selection — all from a single, centralized platform.

Built by **Team 6622 — StanRobotix**.

---

## ✨ Features at a Glance

| Feature | Description |
|---|---|
| 🔒 **Authentication & Roles** | Login/register with role-based access control (Scout, Pit Scout, Head Scout, Admin) |
| 📊 **Scout Dashboard** | Real-time overview with live match status, assignments, and Regional/Final Season rankings |
| 🏟️ **Match Scouting** | In-match data entry form for tracking auto, teleop, and endgame performance |
| 🔧 **Pit Scouting** | Pre-match robot inspection with photo uploads and mechanical spec documentation |
| 📋 **Team Directory** | Browse all teams with detailed profiles, radar charts, and autonomous trajectory heatmaps |
| 📱 **Mobile Native UI** | Premium mobile experience with bottom navigation and responsive glassmorphism design |
| 📈 **Analytics Hub** | Advanced performance analysis with standard deviations, consistency badges, and exportable data |
| 🎯 **Pick List Generator** | Drag-and-drop alliance selection board with power score rankings and PDF export |
| 🗺️ **Drive Team Briefing** | Pre-match strategy briefings with opponent analysis and field positioning |
| 🏢 **Admin Hub** | Manage scout assignments, match grids, team roster, and event configuration |
| 🌍 **Multi-Language** | Integrated translation (English, French, Spanish, Hindi, Chinese, Russian, Arabic) |
| 🎙️ **AI Voice Transcription** | Smart data entry using OpenAI Whisper for hands-free pit scouting |
| 📡 **QR Code Sync** | Offline data transfer between devices via QR code generation and scanning |
| 📤 **JSON Data Export/Import** | Full offline data sync via JSON file export and import |

---

## 🔐 Authentication & Role System

The app supports **four user roles**, each with different permissions:

| Role | Permissions |
|---|---|
| **Scout** | View dashboard, complete assigned match scouting forms |
| **Pit Scout** | View pit dashboard, complete assigned pit scouting inspections |
| **Head Scout** | Access analytics hub, pick list generator, drive team briefings |
| **Admin** | Full access: manage users, assign scouts, configure events, promote roles |

Users register with their name, email, and password. After logging in, new users are directed to the **Team Onboarding** page where they join or create a team using a team access code. Admins can promote users to higher roles using the Admin Hub or the CLI script.

---

## 📊 Scout Dashboard (`/dashboard`)

The main landing page for scouts after login. Displays:

- **Live Match Status** — Shows the current or next match happening on the field, pulled from The Blue Alliance API.
- **Scouting Assignments** — Lists the user's upcoming match scouting tasks with team numbers, match numbers, and completion status.
- **Regional Rank & Final Standing** — Context-specific ranking that automatically identifies the team's final season standing (Day 3 or Championship).
- **Personal Performance Stats** — How many matches and pits the logged-in user has scouted.
- **Dashboard Notes** — Admin-posted announcements visible to all scouts.

There's also a dedicated **Pit Scout Dashboard** for users with the "Pit Scout" role, which emphasizes pit assignments instead of match assignments.

---

## 🏟️ Match Scouting (`/match-scout`)

The core data collection form used during live matches. Scouts fill in:

- **Autonomous Period** — Starting position (tappable field map that records coordinates), balls scored, and autonomous trajectory drawing (freehand path on a field canvas).
- **Teleop Period** — Balls shot, shooter accuracy rating, intake speed rating.
- **Endgame** — Climb status (None, L1, L2, L3) and climb time.
- **General Notes** — Free-text observations about the robot's performance.

All data is saved to the database and immediately available in analytics. The **autonomous trajectory** is stored as an array of stroke objects with color and coordinate data, which is later visualized as a heatmap.

---

## 🔧 Pit Scouting (`/pit-scout/<id>`)

A pre-match inspection form for gathering robot specifications:

- **Drivetrain Type** — Swerve, Tank, Mecanum, etc.
- **Weight** — Robot weight in lbs.
- **Programming Language** — Java, Python, C++, LabVIEW, etc.
- **Shooter Mechanism** — Type and details.
- **Target Tower Accuracy** — Estimated accuracy percentage.
- **Fits Under Stage** — Boolean.
- **Fuel Capacity** — Number of game pieces.
- **Robot Photo** — Camera or file upload, stored in `backend/static/uploads/pit_photos/`.
- **Notes** — Free-text observations and 🎙️ **AI Voice Transcription** support (OpenAI Whisper).

---

## 📋 Team Directory (`/teams-dir`)

Browse all scouted teams at the current event:

- **Sidebar** — Searchable, sortable list of all teams with event selector dropdown.
- **Team Profile** — Click a team to see:
  - **Header** — Team number, name, location.
  - **Stats Cards** — Avg Auto Pts, Avg Teleop Pts, Matches Played, Total Avg Pts.
  - **Performance Radar Chart** — 5-axis visualization (Auto, Teleop, Climb, Accuracy, Speed).
  - **Pit Specs** — Drivetrain, weight, programming language, shooter type, and pit notes.
  - **Match History Table** — Full match-by-match breakdown with auto pts, teleop pts, and notes.
  - **Robot Gallery** — Two-column view:
    - 📷 **Pit Photo** of the robot.
    - 🗺️ **Autonomous Trajectory Canvas** — Field background with heatmap overlay showing all historical paths (faint blue), the average path (bold orange), and the average starting position (orange square).

---

## 📈 Analytics Hub (`/head-scout-stats`)

Advanced analytics dashboard for Head Scouts:

- **Team Performance Table** — Sortable by any metric, with calculated averages and standard deviations.
- **Consistency Badges** — Teams are flagged as "Consistent" or "Inconsistent" based on performance variance.
- **Power Score** — Composite ranking metric: `(auto_avg × 2) + (teleop_avg × accuracy/100) + (climb_rate/20)`.
- **Data Export** — Export all scouting data as JSON for offline analysis or sharing with other scouts.
- **Data Import** — Import JSON data files from other devices to merge scouting databases.
- **QR Code Scanning** — Scan QR codes containing scouting data for field-to-field sync.

---

## 🎯 Pick List Generator (`/picklist`)

An interactive alliance selection tool for Head Scouts and Admins:

- **Drag-and-Drop Board** — Reorder teams visually to build your preferred pick list.
- **Power Score Rankings** — Teams are auto-ranked by their computed power score.
- **TBA Fallback** — If no local scouting data exists, the app falls back to official TBA rankings.
- **Team Cards** — Each card shows key stats at a glance (auto avg, teleop avg, climb rate).
- **PDF Export** — Generate a printable PDF of your finalized pick list.
- **Real-Time Updates** — Rankings update as new scouting data is submitted.

---

## 🗺️ Drive Team Briefing (`/briefing`)

Pre-match strategy preparation for drive teams:

- **Opponent Analysis** — View detailed scouting data on upcoming alliance partners and opponents.
- **Match-Specific Stats** — Aggregated performance metrics filtered to the specific event.
- **Strategy Suggestions** — Data-driven insights for match preparation.

---

## 🏢 Admin Hub (`/admin-hub`)

Central management dashboard for team administrators:

- **Scout Management** — Assign scouts to specific matches, track completion rates.
- **Match Grid** — Visual grid showing all matches at the event with assignment status.
- **Pit Assignments** — Assign pit scouts to specific teams for pre-match inspections.
- **User Role Management** — Promote or demote users between roles (Scout, Pit Scout, Head Scout, Admin).
- **Event Configuration** — Select which FRC events the team is attending.
- **Dashboard Notes** — Post announcements visible to all scouts on their dashboard.
- **Data Management** — View and manage all submitted scouting data.

---

## 🌍 Multi-Language Support

All pages include integrated translation via a language dropdown accessible from any page. Supported languages:

| Code | Language |
|---|---|
| 🇬🇧 EN | English |
| 🇫🇷 FR | Français |
| 🇪🇸 ES | Español |
| 🇮🇳 HI | हिन्दी |
| 🇨🇳 ZH | 中文 |
| 🇷🇺 RU | Русский |
| 🇸🇦 AR | العربية |

The translation system dynamically replaces visible text while preserving Material Icons and interactive elements.

---

## 📁 Project Structure

```
Scouting App/
├── backend/                         # Flask API & server
│   ├── app.py                       # Main application & all routes (~2100 lines)
│   ├── models.py                    # SQLAlchemy database models
│   ├── frc_api.py                   # The Blue Alliance API integration
│   ├── requirements.txt             # Python dependencies
│   └── static/                      # Static assets (images, uploads)
│       ├── images/                  # Field images, logos
│       └── uploads/                 # User-uploaded files
│           ├── pit_photos/          # Robot photos from pit scouting
│           └── strategies/          # Strategy documents
├── frontend/
│   ├── pages/                       # All page templates (Jinja2-rendered HTML)
│   │   ├── admin/                   # Admin scout management hub
│   │   ├── analytics/               # Head scout analytics hub
│   │   ├── auth/                    # Login & registration flow
│   │   ├── briefing/                # Drive team briefing page
│   │   ├── dashboard/               # Main scout dashboard
│   │   ├── dashboard_pit/           # Pit scout dashboard variant
│   │   ├── events/                  # FRC events & schedule browser
│   │   ├── match_scout/             # Match scouting data entry form
│   │   ├── onboarding/              # Team onboarding & access code
│   │   ├── picklist/                # Drag-and-drop pick list generator
│   │   ├── pit_scout/               # Pit scouting inspection form
│   │   ├── profile/                 # User profile & settings view
│   │   ├── profile_edit/            # Profile editing form
│   │   └── teams/                   # Team directory & team profiles
│   └── shared/                      # Shared assets (translation scripts)
├── scripts/                         # Utility scripts
│   ├── promote_admin.py             # Promote a user to Admin role
│   ├── seed_data.py                 # Seed the database with test data
│   ├── check_db.py                  # Inspect database contents
│   ├── populate_test_trajectories.py # Generate test trajectory data
│   └── wipe_data.py                 # Clear all scouting data
├── data/                            # Database storage
│   ├── scouting.db                  # SQLite database (gitignored)
│   └── scouting_empty.db           # Empty template database
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Example env file
├── start.sh                         # Launch script
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- A **TBA API Key** from [thebluealliance.com/account](https://www.thebluealliance.com/account)

### 1. Clone the Repository

```bash
git clone https://github.com/floragel/Scouting-App.git
cd "Scouting App"
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your TBA API key:
```env
FLASK_ENV=development
FLASK_APP=backend/app.py
TBA_API_KEY=your_tba_api_key_here
```

### 5. Set Up the Database

```bash
cp data/scouting_empty.db data/scouting.db
```

> `scouting_empty.db` contains all tables with zero data. Your `scouting.db` is gitignored to protect user data.

### 6. Run the App

```bash
bash start.sh
```

Or manually:

```bash
source venv/bin/activate
python3 backend/app.py
```

The app runs on **http://localhost:5002**.

### 7. Create an Admin User

After registering your first user, promote them to Admin:

```bash
source venv/bin/activate
python3 scripts/promote_admin.py
```

---

## ☁️ Deploying to Render

This application is ready to be deployed to [Render.com](https://render.com/) with a production PostgreSQL database. 

### Quick Deployment via `render.yaml`

1. Fork this repository to your GitHub account.
2. Log into Render and click **Blueprints > New Blueprint Instance**.
3. Connect your repository.
4. Render will automatically detect the `render.yaml` file and create two services:
   - A **PostgreSQL Database**
   - A **Web Service** running the app via Gunicorn.
5. In your Render Dashboard, go to your new Web Service > **Environment**. Add a missing environment variable:
   - `TBA_API_KEY`: Your Blue Alliance API Key.
6. Once deployed, the app will automatically run `db.create_all()` and connect to the PostgreSQL database!

### Manual Deployment

1. Create a **PostgreSQL** database on Render and copy the "Internal Database URL".
2. Create a **Web Service** using this repository.
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `gunicorn --chdir backend app:app`
   - Framework: `Python`
3. Set the following **Environment Variables**:
   - `DATABASE_URL`: Add your PostgreSQL Internal Database URL here.
   - `TBA_API_KEY`: Your Blue Alliance API Key.
   - `FLASK_ENV`: `production`

---

## 🗄️ Database Schema

The SQLite database contains the following tables:

| Table | Purpose |
|---|---|
| `user` | User accounts (name, email, password hash, role, team affiliation) |
| `team` | Team records (number, name, access code) |
| `event` | FRC events (name, TBA event key, location, dates) |
| `event_team` | Many-to-many: which teams are at which events |
| `pit_scout_data` | Pit inspection data (drivetrain, weight, photo path, notes) |
| `match_scout_data` | Match performance data (auto/teleop scores, trajectory, climb status) |
| `scout_assignment` | Scout-to-match/pit assignments (who scouts what) |

---

## 🛠️ Tech Stack

| **Tech** | Descriptions |
|---|---|
| **Backend** | Python 3, Flask, SQLAlchemy |
| **Frontend** | HTML5, Vanilla JavaScript, TailwindCSS (CDN), Mobile-Native Navigation |
| **Database** | SQLite |
| **APIs** | The Blue Alliance (TBA) REST API, Statbotics API (v3) |
| **AI/ML** | OpenAI Whisper (voice transcription) |
| **Charts** | Chart.js (radar charts, performance graphs) |
| **QR Codes** | qrcode.js (generation), html5-qrcode (scanning) |
| **Auth** | Session-based with Werkzeug password hashing |
| **Icons** | Google Material Symbols |

---

## 📝 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `FLASK_ENV` | `development` or `production` | Yes |
| `FLASK_APP` | `backend/app.py` | Yes |
| `TBA_API_KEY` | Your Blue Alliance API key | Yes |

---

## 🧰 Utility Scripts

All utility scripts are in the `scripts/` directory:

```bash
# Promote a user to Admin
python3 scripts/promote_admin.py

# Seed database with test data
python3 scripts/seed_data.py

# Check database contents
python3 scripts/check_db.py

# Generate test trajectory data
python3 scripts/populate_test_trajectories.py

# Wipe all scouting data (caution!)
python3 scripts/wipe_data.py
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

© **Nayl Lahlou** — Team 6622 StanRobotix
