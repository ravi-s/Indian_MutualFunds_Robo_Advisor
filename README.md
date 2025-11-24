# 📘 Indian Mutual Fund Robo-Advisor – MVP (Phase 1 + Phase 2)

This project is a **self-contained robo-advisory prototype** built using **Python + Streamlit**, designed to guide users through:

1. **Risk Profiling**  
2. **Mandatory Registration**  
3. **Investment Preference Input**  
4. **Personalized Mutual Fund Recommendations**

Phase 2 introduces **user registration, local persistence, admin analytics, and SRS-aligned data handling**.

## 🚀 Features Overview

### ✔ Risk Assessment (Phase 1)
- 13-question risk questionnaire  
- Calculates:
  - **Risk Score (13–45)**
  - **Risk Category (Low / Moderate / Medium / High)**
  - **Risk Description**
- Users may walk away after viewing their risk category.

### ✔ Mandatory Registration (Updated Flow)
After risk assessment:
- Registration is **required to continue**.
- If user declines to register:
  - Flow ends  
  - User only sees their risk category (minimal value)  
- Registration fields include:
  - Name (optional)
  - Email (required)
  - City (optional)
  - Country (dropdown)
  - Consent checkbox (required)

### ✔ Investment Preferences
Registered users enter:
- Investment amount (₹)
- Duration:  
  - Less than 6 months  
  - 6 months to 1 year  
  - More than 1 year  

### ✔ Fund Recommendation Engine (Phase 1)
Filters & ranks mutual funds using:
- Risk category recursion
- Minimum investment thresholds
- Time-horizon category/type rules
- Sorting by:
  - Rating → 5Y return → 3Y return → Expense ratio

Users may:
- View top results  
- Show more funds  
- Modify preferences  

### ✔ Admin Dashboard (Phase 2)
Accessible via:
```
?admin=1
```
Includes:
- Total registrations  
- Questionnaire completions  
- Recommendations viewed  
- Conversion funnel  
- Country & city breakdown  
- Latest 50 registrations  
- CSV export of entire DB  

## 🧭 Updated User Flow (Mandatory Registration)
```
Home
  ↓
Step 1 — Risk Assessment (13 questions)
  ↓
Step 2 — Mandatory Registration
      ↳ If user does NOT register → End
      ↳ If user registers → Continue
  ↓
Step 3 — Investment Preferences (amount + duration)
  ↓
Step 4 — Personalized Fund Recommendations
```

## 🗄️ Local Persistence (SQLite)
All registration data is stored locally in:
```
data/robo_advisor.db
```

Fields stored:
- Name  
- Email  
- City  
- Country  
- Consent + timestamp  
- Risk score & category  
- questionnaire_completed  
- recommendations_viewed  
- created_ts  

Override DB path:
```bash
export ROBO_DB_PATH=/custom/path/mydb.sqlite
```

## 🧱 Tech Stack
| Component | Technology |
|----------|------------|
| UI & Flow | Streamlit |
| Language | Python 3 |
| Data | Pandas |
| Persistence | SQLite |
| Dataset | CSV |
| Architecture | Modular (app + DB layer) |

## 📂 Project Structure
```
/
├── roboadvisor.py              # Main application (4-step flow)
├── db.py                       # SQLite persistence + analytics
├── funds.csv                   # Mutual fund dataset
└── data/
    └── robo_advisor_phase2.db  # Auto-generated DB file
```

## 📦 Installation & Setup

### 1. Clone
```bash
git clone https://github.com/<your-name>/<repo>.git
cd <repo>
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run roboadvisor.py
```

### 4. App URL
```
http://localhost:8501
```

## 🔐 Admin Mode
Open:
```
http://localhost:8501/?admin=1
```

Provides:
- Overview metrics  
- Funnel insights  
- Country & city breakdown  
- Last 50 registrations  
- CSV export  

⚠️ Registration table contains **PII** — handle carefully.

## 📊 Recommendation Engine – How It Works
### Risk Profile Recursion
| User Category | Allowed Profiles |
|---------------|------------------|
| High Risk | High → Medium → Moderate → Low |
| Medium Risk | Medium → Moderate → Low |
| Moderate Risk | Moderate → Low |
| Low Risk | Low only |

### Horizon Rules
| Duration | Allowed Types |
|---------|----------------|
| < 6 months | Debt, Hybrid (short duration) |
| 6 months–1 year | Debt, Hybrid |
| > 1 year | Equity, Hybrid, Debt, Index/ETF |

### Sorting Priority
1. Rating  
2. 5Y Return  
3. 3Y Return  
4. Expense Ratio  

## 📌 Notes & Prototype Limitations
- No real-time NAV/market API  
- No authentication (planned Phase 3)  
- DB stored locally (unencrypted)  
- Prototype intended for UX + learning  

## 🛤️ Future Roadmap (Phase 3+)
- User login / authentication  
- Cloud deployment (Render / AWS / Streamlit Cloud)  
- Live NAV data via AMFI API  
- SIP projections & goal planning  
- Full portfolio simulation  
- Cloud DB (PostgreSQL / Firestore)  
- Event tracking & user cohorts  

## 👤 Contributors
- **Product Manager:** You  
- **Technical Architect / Developer:** ChatGPT (collaborative development)
