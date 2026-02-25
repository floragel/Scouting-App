# 🤖 FRC Scouting App (Team 6622 StanRobotix)

A comprehensive, modern web application designed for FIRST Robotics Competition (FRC) teams to efficiently scout matches, manage pit data, and analyze team strengths using The Blue Alliance API integration.

![Dashboard Preview](https://via.placeholder.com/1000x500.png?text=FRC+Scouting+App+Dashboard)

## ✨ Features

- **Role-Based Routing:** Different dashboards tailored for Admins, Head Scouts, and regular Scouts.
- **Match & Pit Scouting Forms:** Beautiful, responsive inputs to track auto, teleop, climb status, and detailed robot characteristics (including image uploads).
- **The Blue Alliance (TBA) Integration:** Live data synchronization to fetch team statuses, recent match results ("Next Match" / "Last Match"), and competition schedules automatically.
- **Scout Assignment Management:** Admins can dynamically assign specific teams and matches to individual scouts directly from their dashboard.
- **Automated Startup Scripts:** Quick launch capability for Mac/Linux (`start.sh` or double-click `.command` files).

---

## 🚀 Getting Started

Follow these steps to install and run the application locally on your machine.

### Prerequisites

You need Python 3 installed on your machine. 
If you don't have it, download it from [python.org](https://www.python.org/downloads/).

### 1. Clone the repository
```bash
git clone https://github.com/floragel/Scouting-App.git
cd "Scouting App"
```

### 2. Set up the Python Virtual Environment
We use a virtual environment to manage dependencies locally.

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

*(Note: If the `requirements.txt` is missing, you can install the core packages manually: `pip install flask flask_sqlalchemy werkzeug python-dotenv requests`)*

### 3. Add your Blue Alliance API Key
To fetch live match data, you need an API key from The Blue Alliance.
1. Create a `TBA Account` at [The Blue Alliance](https://www.thebluealliance.com/).
2. Go to your Account page and generate a `Read API Key`.
3. Open the `.env` file at the root of the project.
4. Replace the existing fake key with your real one:
   ```env
   TBA_API_KEY=your_real_key_here_...
   ```

### 4. Initialize the Database
Before the first run, ensure the database is properly initialized. In your terminal (with the virtual environment activated), run:
```bash
cd backend
python3 -c "from app import db, app; app.app_context().push(); db.create_all()"
cd ..
```

---

## 🏃‍♂️ Running the Server

### Option A: Using the fast startup script (Mac/Linux)
Simply run the startup script from the root directory:
```bash
./start.sh
```
Or, if you are on macOS, you can double-click the `start_app.command` file directly in Finder to launch the terminal and open the app in your browser automatically!

### Option B: Manual Startup
```bash
source venv/bin/activate
cd backend
python3 app.py
```
The server will start at **http://localhost:5002**. 

---

## 🛠️ Typical Workflow

1. **Register User:** Users create accounts via `/login` -> `/register`. Initially, they are placed in a 'Pending' status.
2. **Admin Approval:** An Admin navigates to the Admin Panel to approve the user's account and set their role (`Scout`, `Pit Scout`, etc.).
3. **Task Assignment:** Admins assign specific match keys (e.g., `2026qcmo_qm1`) and team numbers to Scouts.
4. **Scout Dashboard:** The Scout logs in and is greeted by their personalized `Scout Assignments` and the live `TBA Team Status` widget showing the team's next or last match.
5. **Data Entry & Analysis:** Scouts submit Match/Pit data, which is aggregated and queryable in the Head Scout Analytics Hub.

---

## 🗂️ Project Structure

- `/backend/`: Contains the Flask server (`app.py`), Database Models (`models.py`), and TBA Integration (`frc_api.py`).
- `/backend/instance/`: Holds the local SQLite Database (`scouting.db`).
- `/*_hub/` or `/*_flow/`: These HTML frontend directories (e.g., `desktop_scout_dashboard_hub`) contain the TailwindCSS UI logic served directly by Flask via Jinja2 formatting.
- `start.sh` & `start_app.command`: Helper scripts for quick application launches.

---

## 📜 License
© Nayl Lahlou, Team 6622 StanRobotix.
Developed for internal scouting usage.
