# 🤖 FRC Scouting App — Team 6622 "StanRobotix"

A **premium, elite-tier full-stack scouting ecosystem** engineered for the **FIRST Robotics Competition (FRC)**. This application centralizes match data, pit specifications, and advanced team analytics into a unified, high-performance platform.

Built with passion and precision by **Team 6622 — StanRobotix** for the **2026 FRC Season**.

---

## ⚡ 2026 Season: RECHARGED
The app has been architected to handle the dynamic requirements of the **2026 FRC Game**:
- 📊 **Dynamic Objective Tracking**: Real-time scoring for game-specific pieces and auto-calibration for various scoring zones.
- 🔄 **Intelligent Data Fallback**: Integrated Statbotics v3 logic that falls back to 2025 historic data when early-season 2026 data is sparse.
- 📱 **Enhanced PWA v2**: Fully offline-capable field scouting with automated sync protocols for low-connectivity arenas.

---

## 🏗️ Core Ecosystem Features

### 🏢 Elite Admin Hub
The nerve center for team management and oversight:
- **Automated Team Initialization**: Rapidly deploy the entire team roster with `@scout.com` placeholders and default secure credentials.
- **Scout Progress Monitoring**: Real-time dashboard showing match-by-match completion rates and data quality for every scout.
- **Fleet Access Control**: Transparent role management (Admin, Head Scout, Pit, Stand) with administrative password visibility for on-field support.

### 📈 Precision Analytics & Strategy
Move beyond raw data into actionable intelligence:
- **Briefing System**: Dedicated reports for drive teams and strategists, summarizing opponent weaknesses and ally strengths before match call.
- **Dynamic Picklist Tool**: Drag-and-drop alliance selection interface with live-updating statistical rankings based on scouted performance.
- **API Powerhouse**: Seamless bi-directional integration with **The Blue Alliance** and **Statbotics** for verified global stats.

### 👤 Member Portfolios
Empowering scouts to track their own contribution:
- **Personal Metrics**: Automated tracking of matches scouted and team tenure (`join_date`).
- **Profile Customization**: Individualized settings for regional preferences and scouting focus.

---

## 🛠️ Performance Tech Stack

- **Backend**: Python 3.10+ | Flask | SQLAlchemy | PostgreSQL
- **Frontend**: High-Performance Vanilla JS | HTML5 | CSS3 | Tailwind CSS
- **APIs**: The Blue Alliance (v3) | Statbotics (v3)
- **Deployment**: Render-optimized with fully managed Docker orchestration (`render.yaml`).

---

## 🚀 Deployment & Initialization

### 1. Cloud Infrastructure
Optimized for **Render**. Ensure your `DATABASE_URL` points to a production PostgreSQL instance and all environment variables from `.env.example` are populated.

### 2. High-Speed Onboarding
Use the backend initialization script to set up the **StanRobotix** roster (Danaé, Jisoo, Saulius, etc.) in seconds. Accounts follow the `firstname@scout.com` format.

### 3. LIVE Access
Global Entry point: **[https://frc-scouting-app.nayl.ca/login](https://frc-scouting-app.nayl.ca/login)**

---

## 🤝 The StanRobotix Philosophy
We believe in open-source collaboration for the FRC community. Feel free to fork, enhance, and contribute to the evolution of scouting excellence.

© **Nayl Lahlou** — Lead Architect, Team 6622
