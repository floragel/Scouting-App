# 🤖 FRC Scouting App — Team 6622

A **premium full-stack web application** built for **FIRST Robotics Competition (FRC)** teams to streamline match scouting, pit scouting, team analytics, and alliance selection.

Built and maintained by **Team 6622 — StanRobotix**.

---

## ✨ 2026 Season Ready
The app has been updated for the **2026 FRC Season** with full support for:
- 📊 **Dynamic Stats**: Specialized tracking for 2026 game pieces and objectives.
- 🔄 **2025 Fallback**: Intelligent data retrieval that falls back to 2025 performance data when current season data is limited.
- 📱 **PWA Support**: Optimized for mobile use on the field with offline-ready architecture.

---

## 🏢 Enhanced Admin Hub
The Admin Hub is the nerve center of your scouting operation:
- **Member Directory**: View all registered members, their roles, and even retrieve forgotten passwords for team members.
- **Scout Assignments**: Drag-and-drop scouts onto specific matches or pit inspections.
- **Project Control**: Post live announcements to all scouts' dashboards and monitor real-time data entry.
- **Batch Initialization**: Quickly set up your entire team roster via the automated initialization script.

---

## 🔐 Authentication & Security
- **Secure Password Hashing**: All passwords are encrypted using Werkzeug security.
- **Admin Visibility**: Admins can see plain-text passwords for members to assist with "Forgot Password" requests without needing complex email reset flows.
- **Role-Based Access**:
    - **Admin**: Full system control.
    - **Head Scout**: Strategy leading, picklists, and analytics.
    - **Pit Scout**: Robot inspections and mechanical specs.
    - **Stand Scout**: Real-time match data entry.

---

## 🚀 Getting Started (Production)

### 1. Initial Setup
Deploy to **Render** or any Python-compatible host. Ensure `DATABASE_URL` is set to a PostgreSQL instance.

### 2. Team Initialization
To quickly populate your database with the Team 6622 roster:
1. Contact the lead developer to run the backend reset script.
2. The script clears the database and creates accounts for all 20+ members (Danaé, Jisoo, Saulius, etc.).
3. **Default Credentials**: All accounts follow the `firstname@scout.com` pattern with a default team password.

### 3. Login
Access the app at: **[https://frc-scouting-app.nayl.ca/login](https://frc-scouting-app.nayl.ca/login)**

---

## 🛠️ Tech Stack
- **Backend**: Python 3.10+, Flask, SQLAlchemy (PostgreSQL/SQLite)
- **Frontend**: HTML5, Vanilla JS, TailwindCSS, Chart.js
- **Integrations**: The Blue Alliance API (TBA), Statbotics API v3
- **DevOps**: Docker ready, Render-optimized `render.yaml`

---

## 🤝 Contributing
1. Fork the repo.
2. Create a feature branch.
3. Submit a PR to `main`.

---

© **Nayl Lahlou** — Team 6622 StanRobotix
