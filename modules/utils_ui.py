# modules/utils_ui.py
"""
Miscellaneous UI utilities (feedback, etc.)
"""

import streamlit as st

from utils.constants import DEFAULT_DISPLAY_COUNT

def init_session_state():
    """Initialize session state on first load - only set if not already present."""
    # These should only be set if they don't exist
    if "current_step" not in st.session_state:
        st.session_state.current_step = "home"
    
    if "risk_answers" not in st.session_state:
        st.session_state.risk_answers = {}
    
    if "risk_category" not in st.session_state:
        st.session_state.risk_category = None
    
    if "risk_score" not in st.session_state:
        st.session_state.risk_score = 0
    
    if "risk_description" not in st.session_state:
        st.session_state.risk_description = ""
    
    if "investment_amount" not in st.session_state:
        st.session_state.investment_amount = None
    
    if "duration" not in st.session_state:
        st.session_state.duration = None
    
    if "display_limit" not in st.session_state:
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
    
    if "registration_id" not in st.session_state:
        st.session_state.registration_id = None
    
    # Phase 3 Iteration 2: Goal Path
    if "goal_corpus" not in st.session_state:
        st.session_state.goal_corpus = None
    
    if "goal_sip" not in st.session_state:
        st.session_state.goal_sip = None
    
    if "goal_horizon" not in st.session_state:
        st.session_state.goal_horizon = None
    
    if "goal_id" not in st.session_state:
        st.session_state.goal_id = None
    
    if "revisiting_goal_id" not in st.session_state:
        st.session_state.revisiting_goal_id = None

    # Phase 3a: Disclaimer acknowledgment flags
    if "goal_path_disclaimer_acknowledged" not in st.session_state:
        st.session_state.goal_path_disclaimer_acknowledged = False

    if "goal_path_stage2_disclaimer_acknowledged" not in st.session_state:
        st.session_state.goal_path_stage2_disclaimer_acknowledged = False
        
    if "recommendations_disclaimer_acknowledged" not in st.session_state:
        st.session_state.recommendations_disclaimer_acknowledged = False



def render_feedback_footer():
    """Render feedback footer at bottom of pages."""
    st.markdown("---")
    st.caption("Feedback? Issues? Let us know!")
    st.caption("[sankarsana@duck.com](mailto:sankarsana@duck.com)")


def render_home_page():
    """Render home page."""
    st.title("💡 Mutual Fund Robo-Advisor Prototype")
    st.markdown("### A simple, intelligent way to explore mutual fund investments")
    
    # Hero section
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
            
            It's designed to be simple, transparent, and educational — helping you gain clarity and confidence in your investment decisions.
            """
        )
    
    st.markdown("---")
    
    # How it works
    with st.expander("👉 How this prototype works"):
        st.markdown(
            """
            **1. Risk Assessment**
            A short questionnaire helps determine your investment risk profile.
            
            **2. Quick Registration**
            Only an email and consent are required. No marketing emails. No spam. No transactions.
            
            **3. Investment Preferences**
            Provide your investment amount and time horizon.
            
            **4. Recommendations**
            You'll get a curated shortlist of mutual funds based on your profile and preferences.
            """
        )
    
    # Privacy note
    st.info(
        "🔒 **Privacy Note:** This prototype stores minimal data locally for analytics only. "
        "No emails will ever be sent. No financial transactions occur."
    )
    
    st.markdown("---")
    
    # CTA
    st.markdown("### Ready to begin?")
    if st.button("🚀 Start Your Assessment", width = 'stretch'):
        st.session_state.current_step = "risk_assessment"
        st.rerun()
    
    render_feedback_footer()
