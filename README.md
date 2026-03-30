# 🤖 StanRobotix Scouting Ecosystem v2.0 — Team 6622

A **premium, high-performance scouting platform** engineered for the **FIRST Robotics Competition (FRC)**. This application centralizes match intelligence, pit specifications, and strategic heatmaps into a unified, elite-tier ecosystem.

Designed and refined by **Team 6622 — StanRobotix** for the **2026 FRC Season**.

---

## ⚡ 2026 Season: RECHARGED
The platform is built to handle the precision and speed of the **2026 FRC Game**:
- 🎨 **Visual Trajectory Tracking**: Advanced canvas interface for recording autonomous paths with high-fidelity background mapping.
- 📉 **Autonomous Heatmaps**: Aggregated analysis of team paths across multiple matches to identify "Power Lanes" and high-risk zones.
- 🕒 **Season-Aware Persistence**: One-click switching between current and historical seasons, with data isolation and cross-year analytics.
- 📱 **True PWA Capability**: Field-ready offline scouting with intelligent synchronization for high-interference arenas.

---

## 🏗️ Core Platform Features

### 🏢 Elite Admin Hub & Fleet Management
The nerve center for mission control and user oversight:
- **Assignment Engine**: Automated and manual distribution of match and pit scouting duties to available scouts.
- **Multi-Role Flexible System**: Custom role arrays allowing members to hold multiple simultaneous permissions (e.g., *Captain + Head Scout + Driver*).
- **Real-Time Member Directory**: Live monitoring of scout contributions with "Lifetime" and "Season-Specific" performance metrics.
- **Access Control**: One-click approval/revocation and plain-password overrides for rapid field support.

### 📈 Tactical Analytics & Scouting
Decision-making powered by objective, high-quality data:
- **Match Scouting**: Real-time scoring interface with integrated autonomous strategy tracking.
- **Pit Scouting**: Intelligent pre-filling system using existing team keys and nicknames to minimize data entry errors.
- **Teams Directory**: Deep-dive profile for every team at the event, featuring historical performance and trajectory overlays.
- **Briefing Hub**: Automated pre-match reports summarizing ally strengths and opponent weaknesses for the drive team.

### 👤 Personal Performance Portfolios
Empowering scouts to manage their own digital presence:
- **Progress Tracking**: Personal dashboard showing Matches vs. Pits scouted and data accuracy scores.
- **Profile Cloud Sync**: Profile customization with secure image uploads via **Cloudinary**.
- **Onboarding Key System**: Secure, invitation-based registration to protect team data integrity.

---

## 🛠️ Performance Architecture
- **Backend Core**: Python 3.10+ | Flask | SQLAlchemy (PostgreSQL)
- **Persistence Layer**: Resilient `safe_set` logic to handle production schema drift without interruption.
- **Frontend Engine**: Vanilla High-Performance JS | Tailwind CSS | HTML5 Semantic Structure
- **Global Data Hub**: Bi-directional syncing with **The Blue Alliance** and **Statbotics** v3.
- **Deployment**: Enterprise-ready Docker orchestration via `render.yaml`.

---

## 🚀 Deployment & Initialization

### 1. Production Environment
Configured for **Render**. Ensure `DATABASE_URL` and `CLOUDINARY_URL` are present in your production environment variables.

### 2. Team Initialization
Run the specialized promote scripts to set up the **StanRobotix** roster (Danaé, Jisoo, Saulius, etc.) or promote individual admins:
```bash
python3 scripts/promote_admin.py someone@stanrobotix.com
```

### 3. LIVE Endpoint
Production Hub: **[https://frc-scouting-app.nayl.ca/](https://frc-scouting-app.nayl.ca/)**

---

## 🤝 Creative Commons & Contribution
Built with the spirit of **Gracious Professionalism**. Team 6622 encourages forks and contributions to advance the standard of FRC scouting technology.

© **Nayl Lahlou** — Lead Architect, Team 6622
