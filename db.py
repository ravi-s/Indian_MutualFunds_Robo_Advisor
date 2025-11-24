"""
db.py - SQLite helper for Indian MF Robo-Advisor Phase 2

Traceability to SRS:
- FR-R3 (Persistence & Export)
- FR-R4 (Analytics & Metrics)
- FR-R5 (Privacy & Consent)
- FR-R6 (Future auth compatibility)

"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_DB_PATH = "data/robo_advisor.db"


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


def init_db() -> None:
    """
    Initialize DB schema (idempotent).

    Implements:
    - SRS Section 5: Data model (registrations table, indexes)
    - Appendix A: Example SQL (adapted)
    """
    conn = get_connection()
    cur = conn.cursor()

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

    conn.commit()
    conn.close()


def save_registration(
    *,
    name: Optional[str],
    email: str,
    city: Optional[str],
    country: Optional[str],
    consent: bool,
    risk_score: Optional[int],
    risk_category: Optional[str],
) -> int:
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
    - FR-R4.2: Total registered users, completed questionnaire, recommendations viewed,
               breakdowns, and funnel.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Total registered (distinct email)
    cur.execute("SELECT COUNT(DISTINCT email) AS c FROM registrations")
    total_registered = cur.fetchone()["c"]

    # Questionnaire completions: since this table only stores registrations,
    # this is effectively the same as total_registered in this MVP.
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
        "pct_registered_of_completed": pct(total_registered, total_questionnaire_completed),
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
    - FR-R4.3: Export aggregated counts (we export raw registrations here;
               you can add a separate aggregates export if desired.)
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
