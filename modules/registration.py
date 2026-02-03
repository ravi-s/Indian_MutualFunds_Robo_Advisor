# modules/registration.py
"""
User registration and preference input (Phase 2)
"""

import streamlit as st
from utils.constants import DEFAULT_DISPLAY_COUNT, DURATION_OPTIONS
from utils.validators import is_valid_email
from modules.utils_ui import navigate_to_home


def registration_and_recommendation_flow(risk_score: int, risk_category: str) -> None:
    """
    Registration step (mandatory for continuing to recommendations).
    
    Args:
        risk_score: User's calculated risk score
        risk_category: User's risk category
    """
    st.info(f"📊 Your Risk Profile: **{risk_category}** (Score: {risk_score})")
    st.markdown("---")
    st.subheader("Step 2 of 4: Register (optional but recommended)")
    st.write(
        "Register to save your goal, download PDFs later, and access personalized mutual fund recommendations. "
        "If you prefer not to register, you can still try a sample goal path from the home page."
    )

    
    st.session_state.risk_score = risk_score
    st.session_state.risk_category = risk_category
    
    if "registration_id" not in st.session_state:
        st.session_state.registration_id = None
    
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
    
    if submit_register:
        if not email.strip():
            st.error("Email is required to register.")
        elif not is_valid_email(email):
            st.error("E101: Please enter a valid email address.")
        elif not consent:
            st.error("Please tick the consent checkbox to register.")
        else:
            try:
                import db
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
                st.warning(
                    "E102: We couldn't save your details right now — "
                    "you can still continue."
                )
            
            st.session_state.current_step = "preference_input"
            st.rerun()
    
    if st.button("Continue without registering / Exit"):
        st.info(
            "You can still explore the demo goal path from the home page. "
            "Your risk category will stay in this session only."
        )
        st.session_state.registration_id = None
        navigate_to_home()

    if st.button("Cancel Registration and Go to Home"):
        navigate_to_home()

    if st.button("⬅️ Back to Risk Assessment"):
        st.session_state.current_step = "risk_assessment"
        st.rerun()


def render_preference_input() -> None:
    """
    Render investment preferences input form.
    
    Captures investment amount and duration from user, with
    validation and navigation options.
    """
    st.title("Investment Preferences")
    st.subheader("Step 3 of 4: Input Investment Details")
    st.info(
        f"Your assessed Risk Category: "
        f"**{st.session_state.risk_category}**"
    )
    
    with st.form("preference_form"):
        from utils.constants import MIN_INVESTMENT_AMOUNT
        
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
        from utils.constants import MIN_INVESTMENT_AMOUNT
        
        if (
            not isinstance(investment_amount, (int, float))
            or investment_amount <= 0
        ):
            st.error(
                "E003: Investment Amount must be a positive "
                "numeric value."
            )
            return
        
        if investment_amount < MIN_INVESTMENT_AMOUNT:
            st.error(
                f"E004: Investment Amount must be a minimum of "
                f"₹{MIN_INVESTMENT_AMOUNT}."
            )
            return
        
        st.session_state.investment_amount = investment_amount
        st.session_state.duration = duration
        st.session_state.current_step = "recommendations"
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
        st.rerun()
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Back to Registration", use_container_width=True):
            st.session_state.current_step = "registration"
            st.rerun()
    
    with col2:
        if st.button("🏠 Home", use_container_width=True):
            navigate_to_home()
    
    with col3:
        if st.button("Skip to Goals", use_container_width=True):
            st.session_state.current_step = "goal_path_stage1"
            st.rerun()
