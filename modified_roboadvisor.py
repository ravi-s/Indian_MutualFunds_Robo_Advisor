"""
roboadvisor_phase2.py - Indian Mutual Fund Robo-Advisor MVP (Phase 2)

You are Product Manager; this file is the Phase-2 technical implementation.

Traceability to SRS (Phase 2):
- FR-R1: Registration UI (post-risk)
- FR-R2: Validation & Errors
- FR-R3: Persistence & Export (via db.py)
- FR-R4: Analytics & Metrics
- FR-R5: Privacy & Consent
- FR-R6: Future auth compatibility (user_id placeholder in DB)

NOTE: Replace the placeholder questionnaire & recommendation code
with your existing Phase-1 implementation.
"""

import re
from typing import Optional, Tuple

import streamlit as st

import db  # Our helper module from db.py


# -------------- Utility: Email validation (FR-R2.1) -------------- #

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


# -------------- Placeholder: Questionnaire & Risk logic -------------- #
# Replace this section with your existing Phase-1 code.


# def run_questionnaire_and_compute_risk() -> Tuple[Optional[int], Optional[str]]:
#     """
#     Run your 13-question risk questionnaire and compute risk score & category.

#     In your real app, this should:
#     - Render questions via Streamlit widgets
#     - Compute a numerical risk score
#     - Map score to a risk category label (e.g., 'Conservative', 'Balanced', 'Aggressive')

#     For now, we show a placeholder minimal flow to keep this reference app runnable.
#     """
#     st.header("Risk Profiling Questionnaire (Phase 1 MVP placeholder)")

#     # --- BEGIN: Replace this block with your actual Phase-1 questionnaire ---
#     total_score = 0

#     q1 = st.slider(
#         "Q1: Age bracket (younger → higher risk appetite)",
#         min_value=1,
#         max_value=5,
#         value=3,
#     )
#     q2 = st.slider(
#         "Q2: Investment horizon (years)",
#         min_value=1,
#         max_value=5,
#         value=3,
#     )
#     q3 = st.slider(
#         "Q3: Comfort with volatility",
#         min_value=1,
#         max_value=5,
#         value=3,
#     )

#     total_score = q1 + q2 + q3

#     if st.button("Calculate Risk Score"):
#         if total_score <= 6:
#             category = "Conservative"
#         elif total_score <= 10:
#             category = "Balanced"
#         else:
#             category = "Aggressive"

#         st.success(f"Your risk score is {total_score} ({category})")
#         return total_score, category

#     return None, None
#     # --- END: Replace with your actual logic ---


# def show_recommendations(risk_category: str) -> None:
#     """
#     Render personalized mutual fund recommendations based on risk_category.

#     In your real MVP, this should use your funds dataset and filter logic.

#     For this reference, we just show simple example text.
#     """
#     st.subheader("Personalized Mutual Fund Recommendations")

#     if risk_category == "Conservative":
#         st.write("- Short-duration debt fund")
#         st.write("- Conservative hybrid fund")
#     elif risk_category == "Balanced":
#         st.write("- Balanced advantage fund")
#         st.write("- Large & midcap equity fund")
#     else:
#         st.write("- Midcap equity fund")
#         st.write("- Smallcap equity fund")


# -------------- Registration UI (FR-R1, FR-R2, FR-R5) -------------- #


def registration_and_reco_flow(
    risk_score: int,
    risk_category: str,
) -> None:
    """
    Show registration card and then recommendations.

    Traceability:
    - FR-R1.1: Registration card after risk calculation
    - FR-R1.2: 'Register & Show Recommendations' and 'Skip & View Recommendations'
    - FR-R1.3: Persist record, set questionnaire_completed and recommendations_viewed
    - FR-R2: Validation & non-blocking errors
    - FR-R5: Privacy & consent texts
    """
    st.markdown("---")

    st.subheader("Register to access recommendations")
    st.write(
        "Register to access personalized mutual fund recommendations and "
        "help us improve this prototype."
    )

    # Session state to know whether to show recommendations
    if "show_recos" not in st.session_state:
        st.session_state.show_recos = False
    if "registration_id" not in st.session_state:
        st.session_state.registration_id = None

    # Registration form (Streamlit form keeps KISS UX)
    with st.form("registration_form"):
        name = st.text_input("Full Name (optional)")
        email = st.text_input("Email *")
        city = st.text_input("City (optional)")
        country = st.selectbox(
            "Country",
            [
                "India",
                "United Arab Emirates",
                "United States",
                "Singapore",
                "United Kingdom",
                "Other",
            ],
            index=0,
        )
        consent = st.checkbox(
            "I agree to share my details for prototype research and to receive no emails."
        )

        st.caption(
            "We store your name, email, and location only to understand interest in "
            "this prototype. No marketing emails will be sent."
        )

        submit_register = st.form_submit_button("Register & Show Recommendations")

    # Handle registration submit
    if submit_register:
        # Validation (FR-R2.1, FR-R2.2)
        if not email.strip():
            st.error("Email is required to register.")
        elif not is_valid_email(email):
            st.error("E101: Please enter a valid email address.")
        elif not consent:
            st.error("Please tick the consent checkbox to register.")
        else:
            try:
                reg_id = db.save_registration(
                    name=name or None,
                    email=email,
                    city=city or None,
                    country=country,
                    consent=consent,
                    risk_score=risk_score,
                    risk_category=risk_category,
                )
                st.session_state.registration_id = reg_id
                st.session_state.show_recos = True
                st.success("Registration saved. Showing recommendations...")
            except Exception as ex:
                # Non-blocking error (FR-R2.3, FR-R3.3)
                st.warning(
                    "E102: We couldn't save your details right now — "
                    "you can still view recommendations."
                )
                # In a real app, log ex with logging / sentry etc.
                st.session_state.show_recos = True

    # Separate "Skip" action (FR-R1.2)
    if st.button("Skip & View Recommendations"):
        st.session_state.show_recos = True

    # Show recommendations when state says so
    if st.session_state.show_recos:
        show_recommendations(risk_category)

        # Mark recommendations_viewed in DB if we have a registration row
        if st.session_state.registration_id:
            try:
                db.mark_recommendations_viewed(st.session_state.registration_id)
            except Exception:
                # Non-blocking; in MVP we just ignore the failure.
                pass


# -------------- Admin & Analytics UI (FR-R3, FR-R4, FR-R6) -------------- #


def render_admin_page():
    """
    Minimal admin overview page, local-only usage intended.

    Traceability:
    - FR-R3.2: CSV export
    - FR-R4.2: Overview with counts & breakdowns
    - Section 6: Minimal admin UI (overview cards, latest registrations)
    """
    st.title("Admin & Analytics - Robo-Advisor Prototype")

    st.info(
        "This admin page is intended for local use only. "
        "PII (name, email, location) is stored in the SQLite DB file."
    )

    # Overview cards
    metrics = db.get_overview_metrics()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total registered users", metrics["total_registered"])
    c2.metric(
        "Questionnaire completions (registered)",
        metrics["total_questionnaire_completed"],
    )
    c3.metric(
        "Recommendations viewed (registered)",
        metrics["total_recommendations_viewed"],
    )

    # Funnel
    st.subheader("Conversion Funnel")
    f = metrics["funnel"]
    st.write(
        f"- % registered of completed questionnaire: {f['pct_registered_of_completed']}%"
    )
    st.write(
        f"- % viewed recommendations of registered: {f['pct_viewed_recos_of_registered']}%"
    )

    # Breakdown by country
    st.subheader("Registrations by Country")
    if metrics["by_country"]:
        for row in metrics["by_country"]:
            country = row["country"] or "(Unknown)"
            st.write(f"- {country}: {row['c']} registrations")
    else:
        st.write("No registrations yet.")

    # Top cities
    st.subheader("Top 10 Cities")
    if metrics["top_cities"]:
        for row in metrics["top_cities"]:
            city = row["city"] or "(Unknown)"
            country = row["country"] or "(Unknown)"
            st.write(f"- {city}, {country}: {row['c']} registrations")
    else:
        st.write("No city data yet.")

    # Latest registrations table
    st.subheader("Latest Registrations (PII – use with care)")
    rows = db.fetch_latest_registrations(limit=50)
    if rows:
        # Convert to simple dicts for Streamlit
        table_data = [
            {k: row[k] for k in row.keys() if k not in ["user_id"]} for row in rows
        ]
        st.table(table_data)
    else:
        st.write("No registrations available.")

    # CSV export (FR-R3.2, FR-R4.3)
    st.subheader("Export Registrations to CSV")
    csv_data = db.export_registrations_csv()
    st.download_button(
        label="Download registrations.csv",
        data=csv_data,
        file_name="registrations.csv",
        mime="text/csv",
    )


# -------------- Main entry point -------------- #


def main():
    # Initialize DB once (FR-R3.1, Section 8 step 1)
    db.init_db()

    # Decide if this is admin page via query parameter (Section 6)
    params = st.experimental_get_query_params()
    is_admin = params.get("admin", ["0"])[0] == "1"

    if is_admin:
        render_admin_page()
        return

    st.title("Indian Mutual Fund Robo-Advisor (Phase 2 MVP)")

    # Run questionnaire, compute risk
    risk_score, risk_category = run_questionnaire_and_compute_risk()

    # Only show registration & recos after risk is computed
    if risk_score is not None and risk_category is not None:
        registration_and_reco_flow(risk_score, risk_category)


if __name__ == "__main__":
    main()
