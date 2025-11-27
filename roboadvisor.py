# roboadvisor.py
# Indian Mutual Fund Robo-Advisor – Phase 1 + Phase 2 (Registration & Analytics)
#
# Flow (product decision):
#   1) Home
#   2) Step 1 of 4: Risk Assessment
#   3) Step 2 of 4: Registration (mandatory to continue)
#      - If user does NOT register: they walk away with only risk category.
#   4) Step 3 of 4: Investment Preferences (amount, duration)
#   5) Step 4 of 4: Recommendations (Phase 1 logic)
#
# Phase 2 adds:
#   - Registration (with consent + email validation)
#   - SQLite persistence (db.py)
#   - Admin/analytics page (?admin=1 in URL)
#   - Analytics (Phase 2 logic)

import re
from typing import Dict

import streamlit as st
import pandas as pd
import locale

import db  # db.py in same directory

# -------------------------------------------------------------------
# Streamlit page config
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Mutual Fund Robo-Advisor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------------
# Global constants
# -------------------------------------------------------------------

CSV_FILE = "funds.csv"  # Fund data file
MIN_INVESTMENT_AMOUNT = 500  # Minimum allowed amount
DEFAULT_DISPLAY_COUNT = 3  # Default number of funds to show initially

# Risk questionnaire (13 questions, Phase 1)
RISK_QUESTIONNAIRE: Dict[int, Dict] = {
    1: {
        "question": "In general, how would your friends describe you as a risk taker?",
        "options": {
            "A. A real gambler": 4,
            "B. Willing to take risks after thorough research": 3,
            "C. Cautious": 2,
            "D. A real risk avoider": 1,
        },
    },
    2: {
        "question": "You are on a TV game show and can choose one of the following prizes. Which do you take?",
        "options": {
            "A. ₹10,000 in cash": 1,
            "B. 50% chance at winning ₹50,000": 2,
            "C. 25% chance at winning ₹1,00,000": 3,
            "D. 5% chance at winning ₹10,00,000": 4,
        },
    },
    3: {
        "question": "You have just finished saving for a dream vacation. Three weeks before you leave, you lose your job. You would:",
        "options": {
            "A. Cancel the vacation": 1,
            "B. Take a much more modest vacation": 2,
            "C. Go as scheduled, reasoning that you need the break before your job search": 3,
            "D. Extend your vacation, treating it as a last chance to enjoy": 4,
        },
    },
    4: {
        "question": "If you unexpectedly received ₹2,00,000 to invest, what would you do?",
        "options": {
            "A. Deposit it in a bank account or fixed deposit": 1,
            "B. Invest in safe, high-quality bonds or debt mutual funds": 2,
            "C. Invest in equity mutual funds or stocks": 3,
        },
    },
    5: {
        "question": "When you think about investing in equity mutual funds or stocks, how comfortable are you?",
        "options": {
            "A. Not at all comfortable": 1,
            "B. Somewhat comfortable": 2,
            "C. Very comfortable": 3,
        },
    },
    6: {
        "question": 'When you hear the word "risk," which comes to mind first?',
        "options": {
            "A. Loss": 1,
            "B. Uncertainty": 2,
            "C. Opportunity": 3,
            "D. Thrill": 4,
        },
    },
    7: {
        "question": "Suppose experts predict prices of gold, real estate, or collectibles will rise, while bond prices may fall. Most of your investments are in government bonds. What would you do?",
        "options": {
            "A. Hold the bonds": 1,
            "B. Sell bonds; split proceeds between deposits and gold/real-estate funds": 2,
            "C. Invest all proceeds in gold/real-estate funds": 3,
            "D. Invest all proceeds and borrow more to invest further": 4,
        },
    },
    8: {
        "question": "Given the following investment choices and their best/worst case returns, which do you prefer?",
        "options": {
            "A. 3% gain best case, 0% worst case": 1,
            "B. 10% gain best case, -2% worst case": 2,
            "C. 25% gain best case, -8% worst case": 3,
            "D. 50% gain best case, -20% worst case": 4,
        },
    },
    9: {
        "question": "Your portfolio dropped 20% in a month during a market fall. You would:",
        "options": {
            "A. Sell all investments": 1,
            "B. Sell some investments": 2,
            "C. Do nothing and hold": 3,
            "D. Invest more to average down": 4,
        },
    },
    10: {
        "question": "How stable is your primary source of income?",
        "options": {
            "A. Very unstable": 1,
            "B. Somewhat unstable": 2,
            "C. Stable": 3,
            "D. Very stable with growth": 4,
        },
    },
    11: {
        "question": "How many years until you expect to withdraw a significant portion of this investment?",
        "options": {
            "A. Less than 1 year": 1,
            "B. 1–3 years": 2,
            "C. 3–7 years": 3,
            "D. More than 7 years": 4,
        },
    },
    12: {
        "question": "How would you feel if your long-term portfolio delivered 10% annual return but with large short-term ups and downs?",
        "options": {
            "A. Very uncomfortable": 1,
            "B. Uncomfortable": 2,
            "C. Comfortable": 3,
            "D. Excited": 4,
        },
    },
    13: {
        "question": "Your trusted friend is forming an investor group for a startup venture that could multiply your money many times if successful, but may fail. The chance of success is about 20%. If you had the money, how much would you invest?",
        "options": {
            "A. Nothing": 1,
            "B. One month's salary": 2,
            "C. Three months' salary": 3,
            "D. Six months' salary": 4,
        },
    },
}

# Risk categories – 4 buckets (13–45 total score)
RISK_CATEGORIES = [
    {"range": (13, 18), "name": "Low Risk", "description": "Low tolerance for risk (13–18 range)"},
    {"range": (19, 22), "name": "Moderate Risk", "description": "Below-average tolerance for risk (19–22 range)"},
    {"range": (23, 28), "name": "Medium Risk", "description": "Average/moderate tolerance for risk (23–28 range)"},
    {"range": (29, 45), "name": "High Risk", "description": "High tolerance for risk (29–45 range)"},
]

# Risk hierarchy – allows lower-risk profiles to be included for higher-risk users
RISK_HIERARCHY = {
    "High Risk": ["High Risk", "Medium Risk", "Moderate Risk", "Low Risk"],
    "Medium Risk": ["Medium Risk", "Moderate Risk", "Low Risk"],
    "Moderate Risk": ["Moderate Risk", "Low Risk"],
    "Low Risk": ["Low Risk"],
}

# Time-horizon based category/type rules
ALLOWED_FUND_TYPES = {
    "< 6 months": {
        "Category": ["Liquid", "Ultra Short Duration", "Short Duration Debt"],
        "Type": ["Debt", "Hybrid"],
    },
    "6 months to 1 year": {
        "Category": [],
        "Type": ["Debt", "Hybrid"],
    },
    "> 1 year": {
        "Category": [],
        "Type": ["Debt", "Hybrid", "Equity", "Index/ETF"],
    },
}

# Investment duration options as shown in the UI
DURATION_OPTIONS = [
    "Less than 6 months",
    "6 months to 1 year",
    "More than 1 year",
]

# Mapping user-facing duration string → internal CSV duration value
DURATION_MAP = {
    "Less than 6 months": "< 6 months",
    "6 months to 1 year": "6 months to 1 year",
    "More than 1 year": "> 1 year",
}

# Column mapping for CSV → internal names
COLUMN_MAP = {
    "Risk Profile": "risk_profile",
    "Duration": "duration",
    "Min Investment": "min_investment",
    "Rating": "rating",
    "5Y Return %": "return_5y",
    "3Y Return %": "return_3y",
    "Expense Ratio": "expense_ratio",
    "AUM (Cr)": "aum_cr",
    "1Y Return %": "return_1y",
    "Fund Name": "fund_name",
    "Category": "category",
    "Type": "type",
    "Remarks": "remarks",
}

# -------------------------------------------------------------------
# Formatting helpers
# -------------------------------------------------------------------

try:
    locale.setlocale(locale.LC_MONETARY, "en_IN")
except Exception:
    # Fallback – formatting will still work, just without full Indian locale grouping
    pass


def format_percentage(value: float) -> str:
    return f"{float(value):.2f}%"


def format_crores(value: float) -> str:
    return f"₹{locale.format_string('%d', float(value), grouping=True)} Cr."


def format_currency(value: float) -> str:
    return f"₹{locale.format_string('%d', float(value), grouping=True)}"


# -------------------------------------------------------------------
# Email validation
# -------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


# -------------------------------------------------------------------
# Data loading & core business logic
# -------------------------------------------------------------------

@st.cache_data(show_spinner="Loading and validating fund data...")
def load_fund_data() -> pd.DataFrame:
    """Loads and validates the fund data."""
    try:
        df = pd.read_csv(CSV_FILE)
        # df.rename(columns=COLUMN_MAP, inplace=True)

        # required_internal_cols = list(COLUMN_MAP.values())
        # if not all(col in df.columns for col in required_internal_cols):
        #     st.error(
        #         "E006: CSV structure validation failed. "
        #         "Required columns (or their mappings) are missing."
        #     )
        #     st.stop()

        # Strip whitespace from key text columns
        df["risk_profile"] = df["risk_profile"].astype(str).str.strip()
        df["duration"] = df["duration"].astype(str).str.strip()
        df["fund_type"] = df["fund_type"].astype(str).str.strip()
        df["fund_category"] = df["fund_category"].astype(str).str.strip()

        # Ensure min_investment numeric
        df["min_investment"] = pd.to_numeric(df["min_investment"], errors="coerce").fillna(0)

        return df

    except FileNotFoundError:
        st.error(f"Error: Required data file '{CSV_FILE}' not found.")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred while loading data: {e}")
        st.stop()


def calculate_risk_score(answers: Dict[int, int]):
    """Calculate total risk score and map to risk category."""
    total_score = sum(answers.values())

    category = None
    description = "Category not defined by score."
    for profile in RISK_CATEGORIES:
        low, high = profile["range"]
        if low <= total_score <= high:
            category = profile["name"]
            description = profile["description"]
            break

    return total_score, category, description


def filter_and_sort_recommendations(
    df: pd.DataFrame,
    risk_category: str,
    investment_amount: float,
    duration: str,
) -> pd.DataFrame:
    """
    Filters and sorts the fund database using improved logic:
    1. Risk recursion via RISK_HIERARCHY
    2. Min investment amount
    3. Time-horizon (type/category) exclusion
    4. Sort by rating, 5Y, 3Y, expense ratio
    """
    # Map user-friendly duration to internal duration string
    internal_duration = DURATION_MAP.get(duration, "")

    # Risk recursion: allow lower-risk profiles for higher-risk investors
    allowed_risk_profiles = RISK_HIERARCHY.get(risk_category, [risk_category])

    # A: Filter by risk profile
    df_step1 = df[df["risk_profile"].isin(allowed_risk_profiles)].copy()

    # B: Filter by min investment
    df_step2 = df_step1[df_step1["min_investment"] <= investment_amount].copy()

    # C: Time-horizon rules (type/category)
    allowed_rules = ALLOWED_FUND_TYPES.get(internal_duration)
    if not allowed_rules:
        # No specific rules – just return what we have
        df_step3 = df_step2
    else:
        df_step3 = df_step2[df_step2["fund_type"].isin(allowed_rules["Type"])].copy()
        cats = allowed_rules.get("Category") or []
        if cats:
            df_step3 = df_step3[df_step3["fund_category"].isin(cats)].copy()

    # Sort final list – rating high, 5Y high, 3Y high, expense_ratio low
    sorted_df = df_step3.sort_values(
        by=["rating", "return_5y", "return_3y", "exp_ratio"],
        ascending=[False, False, False, True],
    )

    return sorted_df


def format_recommendation_table(df_sorted: pd.DataFrame, limit=None) -> pd.DataFrame:
    """Apply formatting and select key columns for display."""
    display_df = df_sorted.head(limit or len(df_sorted)).reset_index(drop=True)
    display_df["Rank"] = display_df.index + 1

    # Apply formatting
    display_df["aum_cr"] = display_df["aum_cr"].apply(format_crores)
    display_df["return_1y"] = display_df["return_1y"].fillna(0).apply(format_percentage)
    display_df["return_3y"] = display_df["return_3y"].fillna(0).apply(format_percentage)
    display_df["return_5y"] = display_df["return_5y"].fillna(0).apply(format_percentage)
    display_df["exp_ratio"] = display_df["exp_ratio"].apply(format_percentage)
    display_df["min_investment"] = display_df["min_investment"].apply(format_currency)

    display_cols = [
        "Rank",
        "fund_name",
        "fund_category",
        "fund_type",
        "aum_cr",
        "return_1y",
        "return_3y",
        "return_5y",
        "exp_ratio",
        "min_investment",
        "rating",
        "remarks",
    ]

    display_names = {
        "fund_name": "Fund Name",
        "fund_category": "Category",
        "fund_type": "Type",
        "aum_cr": "AUM (in Cr.)",
        "return_1y": "1Y Return",
        "return_3y": "3Y Return",
        "return_5y": "5Y Return",
        "exp_ratio": "Expense Ratio",
        "min_investment": "Min Investment",
        "rating": "Rating",
        "remarks": "Remarks",
    }

    return display_df[display_cols].rename(columns=display_names)


# -------------------------------------------------------------------
# Session state & app flow helpers
# -------------------------------------------------------------------

def init_session_state():
    """Initialise session state on first load."""
    if "current_step" not in st.session_state:
        st.session_state.current_step = "home"
        st.session_state.risk_answers = {}
        st.session_state.risk_category = None
        st.session_state.risk_score = 0
        st.session_state.risk_description = ""
        st.session_state.investment_amount = None
        st.session_state.duration = None
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
        st.session_state.registration_id = None  # DB row id when user registers


# -------------------------------------------------------------------
# Step 0 – Home
# -------------------------------------------------------------------

def render_home_page():
    st.title("💡 Mutual Fund Robo-Advisor Prototype")
    st.markdown("### A simple, intelligent way to explore mutual fund investments")

    # ----------------------------------------
    # Hero Section (visual intro)
    # ----------------------------------------
    c1, c2 = st.columns([1, 2.5])
    with c1:
        st.image(
            "https://cdn-icons-png.flaticon.com/512/1055/1055644.png",
            width=130,
        )
    with c2:
        st.markdown(
            """
            Welcome! This prototype helps you:
            - Understand your **risk tolerance**
            - Capture basic investment preferences
            - Receive a **personalized list** of suitable mutual funds  
            
            It’s designed to be simple, transparent, and educational — helping you gain clarity and
            confidence in your investment decisions.
            """
        )

    st.markdown("---")

    # ----------------------------------------
    # “How it works” interactive section
    # ----------------------------------------
    with st.expander("👉 How this prototype works"):
        st.markdown(
            """
            **1. Risk Assessment**  
            A short questionnaire helps determine your investment risk profile.  
            
            **2. Quick Registration**  
            Only an email and consent are required.  
            No marketing emails. No spam. No transactions.  
            
            **3. Investment Preferences**  
            Provide your investment amount and time horizon.  
            
            **4. Recommendations**  
            You’ll get a curated shortlist of mutual funds based on your profile and preferences.
            """
        )

    # ----------------------------------------
    # Highlight privacy & clarity
    # ----------------------------------------
    st.info(
        "🔒 **Privacy Note:** This prototype stores minimal data locally for analytics only. "
        "No emails will ever be sent. No financial transactions occur."
    )

    st.markdown("---")

    # ----------------------------------------
    # Call-to-action
    # ----------------------------------------
    st.markdown("### Ready to begin?")
    if st.button("🚀 Start Your Assessment", use_container_width=True):
        st.session_state.current_step = "risk_assessment"
        # Feedback footer
        st.rerun()
    
    render_feedback_footer()






# -------------------------------------------------------------------
# Step 1 – Risk Assessment (Questionnaire)
# -------------------------------------------------------------------

def render_risk_assessment():
    st.title("Risk Assessment Questionnaire")
    st.subheader("Step 1 of 4: Determine Your Risk Profile")

    with st.form("risk_form"):
        st.markdown(f"**Please answer all {len(RISK_QUESTIONNAIRE)} questions:**")

        answers_scores: Dict[int, int] = {}
        for q_id, q_data in RISK_QUESTIONNAIRE.items():
            option_texts = list(q_data["options"].keys())
            selected_option = st.radio(
                f"**Q{q_id}.** {q_data['question']}",
                options=option_texts,
                index=0,
                key=f"q_{q_id}",
            )
            answers_scores[q_id] = q_data["options"][selected_option]

        submitted = st.form_submit_button("Calculate Risk Profile")

        if submitted:
            if len(answers_scores) != len(RISK_QUESTIONNAIRE):
                st.error("F-1.3: Please ensure all questions are answered.")
                return

            total_score, category, description = calculate_risk_score(answers_scores)

            st.session_state.risk_score = total_score
            st.session_state.risk_category = category
            st.session_state.risk_description = description
            st.session_state.risk_answers = answers_scores

            st.success(
                f"✅ Your Risk Score is **{total_score}** (Range 13–45). "
                f"Your Risk Category is **{category}** ({description})."
            )

            # New Phase-2 flow: always move to registration next
            st.session_state.current_step = "registration"
            st.rerun()

        render_feedback_footer()


# -------------------------------------------------------------------
# Step 2 – Registration (Mandatory gate)
# -------------------------------------------------------------------

def registration_and_recommendation_flow(
    risk_score: int,
    risk_category: str,
) -> None:
    """
    Registration step (mandatory for continuing to investment inputs).

    Product decision:
      - If user does NOT register, they walk away after seeing risk category only.
      - If user registers (email + consent), they proceed to investment inputs.
    """
    st.markdown("---")
    st.subheader("Step 2 of 4: Register to continue")
    st.write(
        "Register to access personalized mutual fund recommendations and "
        "help us improve this prototype."
    )

    # Keep risk data in state
    st.session_state.risk_score = risk_score
    st.session_state.risk_category = risk_category

    if "registration_id" not in st.session_state:
        st.session_state.registration_id = None

    # --- Registration form ---
    with st.form("registration_form"):
        name = st.text_input("Full Name (optional)")
        email = st.text_input("Email *")
        city = st.text_input("City (optional)", value="Bengaluru")
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

        submit_register = st.form_submit_button("Register & Continue")

    # Handle registration submit
    if submit_register:
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
                st.success("Registration saved. You can now enter investment details.")
            except Exception:
                # Non-blocking error – allow user to proceed
                st.warning(
                    "E102: We couldn't save your details right now — "
                    "you can still continue."
                )
                # In a real app, log the exception with logging/Sentry, etc.

            # In all success/error cases (after validation) – move forward
            st.session_state.current_step = "preference_input"
            st.rerun()

    # If user decides not to register, they walk away with just the risk category
    if st.button("Don't register / Exit"):
        st.info(
            "You can restart later from the home page. "
            "Your risk category remains available in this session."
        )
        st.session_state.registration_id = None
        st.session_state.current_step = "home"
        st.rerun()
    # Feedback footer
    render_feedback_footer()


# -------------------------------------------------------------------
# Step 3 – Investment preferences
# -------------------------------------------------------------------

def render_preference_input():
    st.title("Investment Preferences")
    st.subheader("Step 3 of 4: Input Investment Details")

    st.info(f"Your assessed Risk Category: **{st.session_state.risk_category}**")

    with st.form("preference_form"):
        default_amount = (
            st.session_state.investment_amount
            if st.session_state.investment_amount is not None
            else float(MIN_INVESTMENT_AMOUNT)
        )

        investment_amount = st.number_input(
            "Investment Amount (₹):",
            min_value=0.0,
            value=default_amount,
            step=500.0,
            format="%.0f",
            key="amount_input",
        )

        default_duration_index = (
            DURATION_OPTIONS.index(st.session_state.duration)
            if st.session_state.duration in DURATION_OPTIONS
            else 2
        )
        duration = st.selectbox(
            "Investment Duration:",
            options=DURATION_OPTIONS,
            index=default_duration_index,
            key="duration_select",
        )

        submitted = st.form_submit_button(
            "Generate Recommendations (Step 4)", use_container_width=True
        )

        if submitted:
            if not isinstance(investment_amount, (int, float)) or investment_amount <= 0:
                st.error("E003: Investment Amount must be a positive numeric value.")
                return
            if investment_amount < MIN_INVESTMENT_AMOUNT:
                st.error(
                    f"E004: Investment Amount must be a minimum of ₹{MIN_INVESTMENT_AMOUNT}."
                )
                return

            st.session_state.investment_amount = investment_amount
            st.session_state.duration = duration
            st.session_state.current_step = "recommendations"
            st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
            st.rerun()

        # Feedback footer
        render_feedback_footer()


# -------------------------------------------------------------------
# Step 4 – Recommendations
# -------------------------------------------------------------------

def render_recommendations_display():
    st.title("Fund Recommendations")
    st.subheader("Step 4 of 4: Your Customised Fund List")

    # Mark recommendations_viewed for registered users
    reg_id = st.session_state.get("registration_id")
    if reg_id:
        try:
            db.mark_recommendations_viewed(reg_id)
        except Exception:
            # Non-blocking; analytics might miss a count but UX is fine.
            pass

    st.markdown(
        f"**Filtering by:** "
        f"Risk Profile: **{st.session_state.risk_category}**, "
        f"Duration: **{st.session_state.duration}**, "
        f"Min. Investment: **{format_currency(st.session_state.investment_amount)}**"
    )

    fund_df = load_fund_data()

    recommended_funds = filter_and_sort_recommendations(
        fund_df,
        st.session_state.risk_category,
        st.session_state.investment_amount,
        st.session_state.duration,
    )

    total_matches = len(recommended_funds)

    if total_matches == 0:
        st.warning(
            "E005: No funds match your criteria. "
            "Try a different investment amount or duration."
        )
        if st.button("Modify Preferences", use_container_width=True):
            st.session_state.current_step = "preference_input"
            st.rerun()
        return

    final_display_df = format_recommendation_table(
        recommended_funds, st.session_state.display_limit
    )

    st.dataframe(final_display_df, use_container_width=True, hide_index=True)

    max_total_display = min(10, total_matches)

    if st.session_state.display_limit < max_total_display:
        if st.button(
            f"Show More ({st.session_state.display_limit} / {total_matches} funds shown)",
            use_container_width=True,
        ):
            st.session_state.display_limit = max_total_display
            st.rerun()
    elif total_matches > DEFAULT_DISPLAY_COUNT:
        st.info(f"Showing all {total_matches} matching funds.")

    if st.button(
        "Modify Investment Preferences",
        help="Go back to change amount or duration without re-taking the questionnaire.",
    ):
        st.session_state.current_step = "preference_input"
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
        # Feedback footer
        render_feedback_footer()
        st.rerun()

    if st.button("Back to Home"):
        st.session_state.current_step = "home"
        st.rerun()
    # Feedback footer
    render_feedback_footer()

def render_feedback_footer():
    st.markdown(
        """
        <hr style="margin-top:40px;margin-bottom:10px;">
        <div style="font-size: 14px; color: #555;">
            💬 <strong>Have feedback?</strong><br>
            We would love to hear your thoughts.  
            <a href="mailto:sankarsana@duck.com?subject=Feedback - Mutual Fund Robo-Advisor"
                style="text-decoration: none; color: #1a73e8;">
                👉 Send feedback via email
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------------
# Admin / Analytics page
# -------------------------------------------------------------------

def render_admin_page():
    """
    Minimal admin overview page, local-only usage intended.
    """
    st.title("Admin & Analytics - Robo-Advisor Prototype")

    st.info(
        "This admin page is intended for local use only. "
        "PII (name, email, location) is stored in the SQLite DB file."
    )

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

    st.subheader("Conversion Funnel")
    f = metrics["funnel"]
    st.write(
        f"- % registered of completed questionnaire: "
        f"{f['pct_registered_of_completed']}%"
    )
    st.write(
        f"- % viewed recommendations of registered: "
        f"{f['pct_viewed_recos_of_registered']}%"
    )

    st.subheader("Registrations by Country")
    if metrics["by_country"]:
        for row in metrics["by_country"]:
            country = row["country"] or "(Unknown)"
            st.write(f"- {country}: {row['c']} registrations")
    else:
        st.write("No registrations yet.")

    st.subheader("Top 10 Cities")
    if metrics["top_cities"]:
        for row in metrics["top_cities"]:
            city = row["city"] or "(Unknown)"
            country = row["country"] or "(Unknown)"
            st.write(f"- {city}, {country}: {row['c']} registrations")
    else:
        st.write("No city data yet.")

    st.subheader("Latest Registrations (PII – use with care)")
    rows = db.fetch_latest_registrations(limit=50)
    if rows:
        table_data = [{k: row[k] for k in row.keys() if k != "user_id"} for row in rows]
        st.table(table_data)
    else:
        st.write("No registrations available.")

    st.subheader("Export Registrations to CSV")
    csv_data = db.export_registrations_csv()
    st.download_button(
        label="Download registrations.csv",
        data=csv_data,
        file_name="registrations.csv",
        mime="text/csv",
    )


# -------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------

def main():
    # Init DB schema
    db.init_db()

    # Check if admin view (?admin=1)
    params = st.query_params
    is_admin = params.get("admin", ["0"])[0] == "1"

    if is_admin:
        render_admin_page()
        return

    # Normal user flow
    load_fund_data()
    init_session_state()

    step = st.session_state.current_step

    if step == "home":
        render_home_page()
    elif step == "risk_assessment":
        render_risk_assessment()
    elif step == "registration":
        registration_and_recommendation_flow(
            st.session_state.risk_score, st.session_state.risk_category
        )
    elif step == "preference_input":
        render_preference_input()
    elif step == "recommendations":
        render_recommendations_display()

    # Debug sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Development Debug Info")
    st.sidebar.markdown(f"**Current Step:** `{st.session_state.current_step}`")
    st.sidebar.markdown(f"**Risk Score:** {st.session_state.risk_score}")
    st.sidebar.markdown(f"**Category:** {st.session_state.risk_category}")
    st.sidebar.markdown(f"**Amount:** {st.session_state.investment_amount}")
    st.sidebar.markdown(f"**Duration:** {st.session_state.duration}")
    st.sidebar.markdown(f"**Display Limit:** {st.session_state.display_limit}")
    st.sidebar.markdown(
        "Scope: Streamlit, single-user prototype with local SQLite persistence (Phase 2)."
    )


if __name__ == "__main__":
    main()
