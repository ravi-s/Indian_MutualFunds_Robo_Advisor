"""
Updated db.py - SQLite helper for Indian MF Robo-Advisor Phase 2 & Phase 3

Additions:
- Goals table schema (Phase 3 Iteration 2)
- Goal persistence functions
- Goal retrieval and analytics

Existing functionality:
- Registrations table management
- Registration analytics
- Export utilities
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = "/app/data/robo_advisor.db"


# ===================================================================
# DATABASE CONNECTION
# ===================================================================

def get_db_path() -> str:
    """Allow override via env var, else use default path. (FR-R3.1)"""
    return os.getenv("ROBO_DB_PATH", DEFAULT_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with Row factory."""
    db_path = Path(get_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ===================================================================
# DATABASE INITIALIZATION (Combined: Registrations + Goals)
# ===================================================================

def init_db() -> None:
    """
    Initialize DB schema (idempotent).
    
    Creates:
    - registrations table (Phase 2)
    - goals table (Phase 3 Iteration 2)
    
    Implements:
    - SRS Section 5: Data model
    - Phase 3 Goal Path persistence
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # =========================================================
    # REGISTRATIONS TABLE (Phase 2 - Existing)
    # =========================================================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT NOT NULL,
            city TEXT,
            country TEXT,
            consent INTEGER NOT NULL,
            consent_ts TEXT NOT NULL,
            questionnaire_completed INTEGER NOT NULL DEFAULT 1,
            recommendations_viewed INTEGER NOT NULL DEFAULT 0,
            risk_score INTEGER,
            risk_category TEXT,
            created_ts TEXT NOT NULL DEFAULT (datetime('now')),
            user_id TEXT
        )
        """
    )
    
    # Indexes as per SRS (email, country)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_reg_email ON registrations(email)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_reg_country ON registrations(country)"
    )
    
    # =========================================================
    # GOALS TABLE (Phase 3 Iteration 2 - New)
    # =========================================================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id TEXT UNIQUE NOT NULL,
            registration_id INTEGER,
            corpus REAL NOT NULL,
            sip REAL NOT NULL,
            horizon INTEGER NOT NULL,
            risk_category TEXT NOT NULL,
            conservative_projection REAL,
            expected_projection REAL,
            best_case_projection REAL,
            confidence TEXT,
            adjusted_return REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT DEFAULT 'saved',
            email_sent_at TEXT,
            revisited_at TEXT,
            FOREIGN KEY (registration_id) REFERENCES registrations(id)
        )
        """
    )
    
    # Indexes for goals table
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_goal_id ON goals(goal_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_goal_reg_id ON goals(registration_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_goal_status ON goals(status)"
    )
    
    conn.commit()
    conn.close()


# ===================================================================
# REGISTRATIONS (Phase 2 - Existing Functions)
# ===================================================================

def save_registration(
    *,
    name: Optional[str],
    email: str,
    city: Optional[str],
    country: Optional[str],
    consent: bool,
    risk_score: Optional[int],
    risk_category: Optional[str],
) -> Optional[int]:
    """
    Insert a new registration row.
    
    Traceability:
    - FR-R1.3: Persist record with flags
    - FR-R4.1: Record questionnaire_completed, registered (implicit), recommendations_viewed
    - FR-R5.1: Record consent and timestamp
    """
    conn = get_connection()
    cur = conn.cursor()
    
    consent_ts = datetime.utcnow().isoformat(timespec="seconds")
    
    cur.execute(
        """
        INSERT INTO registrations (
            name, email, city, country,
            consent, consent_ts,
            questionnaire_completed, recommendations_viewed,
            risk_score, risk_category,
            created_ts, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?, datetime('now'), NULL)
        """,
        (
            name or None,
            email.strip(),
            city or None,
            country or None,
            1 if consent else 0,
            consent_ts,
            risk_score,
            risk_category,
        ),
    )
    
    reg_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    return reg_id


def mark_recommendations_viewed(registration_id: int) -> None:
    """
    Set recommendations_viewed flag for a registration.
    
    Traceability:
    - FR-R1.3: recommendations_viewed = true when recommendations page loads
    - FR-R4.1: Track recommendations_viewed event
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        """
        UPDATE registrations
        SET recommendations_viewed = 1
        WHERE id = ?
        """,
        (registration_id,),
    )
    
    conn.commit()
    conn.close()


def fetch_latest_registrations(limit: int = 50) -> List[sqlite3.Row]:
    """Return latest N registrations for admin view. (FR-R3.1, FR-R4.2)"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT id, name, email, city, country,
            consent, consent_ts,
            questionnaire_completed, recommendations_viewed,
            risk_score, risk_category,
            created_ts
        FROM registrations
        ORDER BY created_ts DESC
        LIMIT ?
        """,
        (limit,),
    )
    
    rows = cur.fetchall()
    conn.close()
    
    return rows


def get_overview_metrics() -> Dict[str, Any]:
    """
    Compute basic analytics and funnel metrics.
    
    Traceability:
    - FR-R4.2: Total registered users, completed questionnaire, 
               recommendations viewed, breakdowns, and funnel.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Total registered (distinct email)
    cur.execute("SELECT COUNT(DISTINCT email) AS c FROM registrations")
    total_registered = cur.fetchone()["c"]
    
    # Questionnaire completions
    cur.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE questionnaire_completed = 1"
    )
    total_questionnaire_completed = cur.fetchone()["c"]
    
    # Recommendations viewed
    cur.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE recommendations_viewed = 1"
    )
    total_recommendations_viewed = cur.fetchone()["c"]
    
    # Breakdown by country
    cur.execute(
        """
        SELECT country, COUNT(*) AS c
        FROM registrations
        GROUP BY country
        ORDER BY c DESC
        """
    )
    by_country = cur.fetchall()
    
    # Top 10 cities
    cur.execute(
        """
        SELECT city, country, COUNT(*) AS c
        FROM registrations
        WHERE city IS NOT NULL AND city <> ''
        GROUP BY city, country
        ORDER BY c DESC
        LIMIT 10
        """
    )
    top_cities = cur.fetchall()
    
    # Funnel percentages (guard against divide-by-zero)
    def pct(num: int, den: int) -> float:
        return round((num / den * 100.0), 1) if den else 0.0
    
    funnel = {
        "pct_registered_of_completed": pct(
            total_registered, total_questionnaire_completed
        ),
        "pct_viewed_recos_of_registered": pct(
            total_recommendations_viewed, total_registered
        ),
    }
    
    conn.close()
    
    return {
        "total_registered": total_registered,
        "total_questionnaire_completed": total_questionnaire_completed,
        "total_recommendations_viewed": total_recommendations_viewed,
        "by_country": by_country,
        "top_cities": top_cities,
        "funnel": funnel,
    }


def export_registrations_csv() -> str:
    """
    Export full registrations table as CSV string.
    
    Traceability:
    - FR-R3.2, FR-R3.3: Admin CSV export
    - FR-R4.3: Export aggregated counts
    """
    import csv
    from io import StringIO
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT id, name, email, city, country,
            consent, consent_ts,
            questionnaire_completed, recommendations_viewed,
            risk_score, risk_category,
            created_ts, user_id
        FROM registrations
        ORDER BY created_ts DESC
        """
    )
    
    rows = cur.fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(
        [
            "id",
            "name",
            "email",
            "city",
            "country",
            "consent",
            "consent_ts",
            "questionnaire_completed",
            "recommendations_viewed",
            "risk_score",
            "risk_category",
            "created_ts",
            "user_id",
        ]
    )
    
    # Rows
    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["name"],
                r["email"],
                r["city"],
                r["country"],
                r["consent"],
                r["consent_ts"],
                r["questionnaire_completed"],
                r["recommendations_viewed"],
                r["risk_score"],
                r["risk_category"],
                r["created_ts"],
                r["user_id"],
            ]
        )
    
    return output.getvalue()


# ===================================================================
# GOALS (Phase 3 Iteration 2 - New Functions)
# ===================================================================

def save_goal(
    goal_id: str,
    registration_id: Optional[int],
    corpus: float,
    sip: float,
    horizon: int,
    risk_category: str,
    conservative_projection: float,
    expected_projection: float,
    best_case_projection: float,
    confidence: str,
    adjusted_return: float,
    created_at: str,
) -> str:
    """
    Save a goal to the database.
    
    Args:
        goal_id: Unique goal ID (e.g., "GOAL_20251208_ABC123")
        registration_id: FK to registrations (optional for anonymous)
        corpus: Initial corpus (₹)
        sip: Monthly SIP (₹)
        horizon: Investment horizon (years)
        risk_category: Risk category name
        conservative_projection: Conservative projection (₹)
        expected_projection: Expected projection (₹)
        best_case_projection: Best case projection (₹)
        confidence: Confidence level (High/Medium/Low)
        adjusted_return: Return after mean reversion (%)
        created_at: ISO format timestamp
        
    Returns:
        goal_id (str)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    now = datetime.utcnow().isoformat(timespec="seconds")
    
    cur.execute(
        """
        INSERT INTO goals (
            goal_id, registration_id, corpus, sip, horizon, risk_category,
            conservative_projection, expected_projection, best_case_projection,
            confidence, adjusted_return, created_at, updated_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            goal_id,
            registration_id,
            corpus,
            sip,
            horizon,
            risk_category,
            conservative_projection,
            expected_projection,
            best_case_projection,
            confidence,
            adjusted_return,
            created_at,
            now,
            "saved",
        ),
    )
    
    conn.commit()
    conn.close()
    
    return goal_id


def get_goal(goal_id: str) -> Optional[Dict]:
    """
    Retrieve a goal by ID.
    
    Args:
        goal_id: Goal ID string
        
    Returns:
        Goal dict or None if not found
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT * FROM goals WHERE goal_id = ?",
        (goal_id,),
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_goals(registration_id: int) -> pd.DataFrame:
    """
    Retrieve all goals for a user.
    
    Args:
        registration_id: User's registration ID
        
    Returns:
        DataFrame with all user's goals ordered by creation date (newest first)
    """
    conn = get_connection()
    
    query = """
    SELECT * FROM goals 
    WHERE registration_id = ? 
    ORDER BY created_at DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(registration_id,))
    conn.close()
    
    return df


def mark_goal_email_sent(goal_id: str) -> None:
    """
    Mark a goal as having email sent (Phase 3.3).
    
    Args:
        goal_id: Goal ID
    """
    conn = get_connection()
    cur = conn.cursor()
    
    now = datetime.utcnow().isoformat(timespec="seconds")
    
    cur.execute(
        """
        UPDATE goals 
        SET status = 'email_sent', email_sent_at = ?, updated_at = ?
        WHERE goal_id = ?
        """,
        (now, now, goal_id),
    )
    
    conn.commit()
    conn.close()


def mark_goal_revisited(goal_id: str) -> None:
    """
    Mark a goal as revisited (Phase 4 - Dashboard).
    
    Args:
        goal_id: Goal ID
    """
    conn = get_connection()
    cur = conn.cursor()
    
    now = datetime.utcnow().isoformat(timespec="seconds")
    
    cur.execute(
        """
        UPDATE goals 
        SET status = 'revisited', revisited_at = ?, updated_at = ?
        WHERE goal_id = ?
        """,
        (now, now, goal_id),
    )
    
    conn.commit()
    conn.close()


def get_goals_analytics() -> Dict[str, Any]:
    """
    Get analytics on saved goals (Phase 3.3 Admin).
    
    Returns:
        Dict with goal statistics
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Total goals
    cur.execute("SELECT COUNT(*) AS c FROM goals")
    total_goals = cur.fetchone()["c"]
    
    # By status
    cur.execute(
        "SELECT status, COUNT(*) AS c FROM goals GROUP BY status"
    )
    by_status = {row["status"]: row["c"] for row in cur.fetchall()}
    
    # By confidence
    cur.execute(
        "SELECT confidence, COUNT(*) AS c FROM goals GROUP BY confidence"
    )
    by_confidence = {row["confidence"]: row["c"] for row in cur.fetchall()}
    
    # By risk category
    cur.execute(
        "SELECT risk_category, COUNT(*) AS c FROM goals GROUP BY risk_category"
    )
    by_risk_category = {row["risk_category"]: row["c"] for row in cur.fetchall()}
    
    # Average projection
    cur.execute(
        """
        SELECT 
            ROUND(AVG(corpus), 0) AS avg_corpus,
            ROUND(AVG(sip), 0) AS avg_sip,
            ROUND(AVG(horizon), 1) AS avg_horizon,
            ROUND(AVG(expected_projection), 0) AS avg_expected
        FROM goals
        """
    )
    avg_row = cur.fetchone()
    
    conn.close()
    
    return {
        "total_goals": total_goals,
        "by_status": by_status,
        "by_confidence": by_confidence,
        "by_risk_category": by_risk_category,
        "averages": {
            "corpus": avg_row["avg_corpus"],
            "sip": avg_row["avg_sip"],
            "horizon": avg_row["avg_horizon"],
            "expected_projection": avg_row["avg_expected"],
        },
    }


def export_goals_csv() -> str:
    """
    Export all goals as CSV (Admin export).
    
    Returns:
        CSV string
    """
    import csv
    from io import StringIO
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        """
        SELECT * FROM goals
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    if rows:
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow(r)
    
    return output.getvalue()