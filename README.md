# Votex.ai — AI-Automated Voting System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange?style=flat-square&logo=mysql)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-ML-orange?style=flat-square&logo=scikit-learn)
![Bootstrap](https://img.shields.io/badge/UI-Modern%20Tech%20Dark-indigo?style=flat-square&logo=bootstrap)

**A next-generation, secure online voting platform powered by AI turnout prediction, autonomous anomaly defense, and real-time election intelligence.**

</div>

---

## 🌟 Key Features

### 🖥️ Modern Tech Dark UI & Glassmorphism Design
- Custom-built dark tech theme using rich slate backgrounds (`#090D16`), cyan and indigo accents, and backdrop-blur glass panels.
- Responsive layout with Bootstrap 5 and Bootstrap Icons.
- Accessible, high-contrast typography powered by *Plus Jakarta Sans* and *Inter*.

### 🕹️ Interactive Admin Command Console
- **Interactive Left Navigation Panel**: Switch dynamically between views with smooth fade transitions:
  - 📊 **Overview Metrics**: 4 glowing high-visibility KPI metric cards (Active Elections, Eligible Voters, Ballots Cast, Live Turnout).
  - 🏆 **Live Standings**: Instant candidate vote tallies, percentage share progress bars, leader badges, and manifesto cards.
  - 📈 **AI Turnout Forecast**: Machine Learning turnout projection chart and regression parameter breakdown.
  - 🛡️ **Velocity Guard**: Real-time threat defense telemetry, status badges, and bot protection audit.
  - 📜 **Audit Ledger**: Cryptographic audit trail with timestamps and verified block IDs.
- **Data Export Suite**: Instant CSV exports for official election results and audit ledgers.
- **AI Burst Diagnostic Tool**: Integrated stress-test button allowing administrators to simulate high-velocity voting bursts and verify the ML detector live.

### 🤖 Machine Learning Intelligence
- **Voter Turnout Predictor**: `RandomForestRegressor` model predicting final election participation based on historical patterns, roster size, duration, and candidate counts.
- **Velocity Guard Anomaly Detector**: `IsolationForest` unsupervised model auditing submission frequency and IP distribution to block automated bot floods and credential replay attacks.

### 🗳️ Secure Voter Experience
- **Authentication**: Role-based access control with Werkzeug password hashing.
- **Double-Voting Prevention**: Database-level constraints ensuring one sealed ballot per eligible voter.
- **Cryptographic Ballot Receipt**: Sealed confirmation screen with reference hash, candidate confirmation, and timestamp.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-SQLAlchemy, Werkzeug
- **Database**: MySQL 8.0+ via PyMySQL
- **Machine Learning**: Scikit-Learn, NumPy, Pandas, Joblib
- **Frontend**: Server-rendered Jinja2, HTML5/CSS3, Chart.js, Bootstrap 5, Bootstrap Icons

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10+**
- **MySQL Server** (running locally on port `3306`)
- **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/singhaisarvagya8-hue/AI-Automated-Voting-System.git
cd AI-Automated-Voting-System
```

### 3. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Database Setup
Start your MySQL server (e.g. via Homebrew on macOS):
```bash
brew services start mysql
```

Create the MySQL database:
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS voting_system_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Configure your `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and set your MySQL password in `DATABASE_URL`:
```ini
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/voting_system_db
SECRET_KEY=votex-production-secret-key-2026
PORT=5001
```

### 5. Seed Initial Data
Populate demo elections, candidates, and voter accounts:
```bash
mysql -u root -p voting_system_db < seed_data.sql
```

### 6. Start the Platform
```bash
./run.sh
# or manually: source venv/bin/activate && python app.py
```

Open your browser at:
**[http://127.0.0.1:5001](http://127.0.0.1:5001)**

> *Note: Port 5001 is used by default to prevent port conflicts with macOS ControlCenter AirPlay services.*

---

## 🔑 Demo Credentials

All test accounts are pre-configured in `seed_data.sql` with password: **`password123`**

| Role | Username / Voter ID | Password | Access / Purpose |
| :--- | :--- | :--- | :--- |
| **Superadmin** | `ADMIN001` | `password123` | Full Admin Command Center, Standings, AI Telemetry, CSV Exports |
| **Voter 1** | `CS202601` | `password123` | Student Voter Dashboard, Ballot Voting Screen, Receipt |
| **Voter 2** | `CS202602` | `password123` | Student Voter Dashboard, Ballot Voting Screen, Receipt |

---

## 📁 Project Structure

```
├── app.py                     # Application entry point & auto-initialization
├── config.py                  # Database & session configuration
├── run.sh                     # Quick launch script
├── requirements.txt           # Python package dependencies
├── seed_data.sql              # Demo data with hashed credentials
├── ml/                        # Machine learning subsystem
│   ├── anomaly_detection.py   # Isolation Forest anomaly detector
│   ├── train_models.py        # Model training script
│   └── turnout_model.py       # Random Forest turnout predictor
├── models/                    # SQLAlchemy database models
│   ├── user.py                # User model & authentication
│   ├── election.py            # Election model
│   ├── candidate.py           # Candidate model
│   ├── vote.py                # Sealed vote model
│   └── audit_log.py           # Audit trail ledger model
├── routes/                    # Flask blueprint route controllers
│   ├── auth.py                # Login & logout
│   ├── voter.py               # Voter dashboard & ballot submission
│   └── admin.py               # Admin console, CSV exports, simulation toggle
└── templates/                 # Modern Tech UI templates
    ├── base.html              # Global layout, glassmorphism CSS & navigation
    ├── login.html             # High-tech login portal
    ├── voter_dashboard.html   # Voter portal with election overview
    ├── vote.html              # Interactive ballot selection screen
    ├── confirmation.html      # Cryptographic vote confirmation receipt
    └── admin/
        └── dashboard.html     # Interactive Admin Command Center with tab navigation
```

---

## 📜 License
This project is developed for educational and institutional governance purposes. Open-source under the MIT License.
