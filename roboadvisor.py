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

# roboadvisor.py
"""
Mutual Fund Robo-Advisor Prototype - Phase 2 & Phase 3
Main entry point with modular architecture
"""

import streamlit as st
import pandas as pd
import logging
# import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================================================================
# IMPORTS: Modules & Utils
# ===================================================================

from modules.utils_ui import init_session_state, render_home_page, render_feedback_footer
from modules.risk_assessment import render_risk_assessment, calculate_risk_score
from modules.registration import registration_and_recommendation_flow, render_preference_input
from modules.recommendations import apply_mean_reversion, render_recommendations_display

from utils.constants import CATEGORY_RETURNS, CATEGORY_VOLATILITY, CSV_FILE, MIN_INVESTMENT_AMOUNT, DEFAULT_DISPLAY_COUNT

# ===================================================================
# STREAMLIT CONFIG
# ===================================================================

st.set_page_config(
    page_title="Mutual Fund Robo-Advisor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ===================================================================
# CORE FUNCTIONS
# ===================================================================

@st.cache_data(show_spinner="Loading and validating fund data...")
def load_fund_data() -> pd.DataFrame:
    """Loads and validates the fund data."""
    try:
        df = pd.read_csv(CSV_FILE)
        
        # Strip whitespace from key text columns
        df["risk_profile"] = df["risk_profile"].astype(str).str.strip()
        df["duration"] = df["duration"].astype(str).str.strip()
        df["fund_type"] = df["fund_type"].astype(str).str.strip()
        df["fund_category"] = df["fund_category"].astype(str).str.strip()
        
        # Ensure min_investment numeric
        df["min_investment"] = pd.to_numeric(df["min_investment"], errors="coerce").fillna(0)
        
        # Phase 3: Handle last_updated column
        if "last_updated" not in df.columns:
            logger.warning("'last_updated' column not found in CSV. Using today's date as fallback.")
            from datetime import datetime
            df["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        else:
            df["last_updated"] = df["last_updated"].astype(str).str.strip()
        
        return df
        
    except FileNotFoundError:
        st.error(f"Error: Required data file '{CSV_FILE}' not found.")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred while loading data: {e}")
        st.stop()





# ===================================================================
# ADMIN PAGE (Phase 2)
# ===================================================================

def render_admin_page():
    """Render admin/analytics page."""
    st.title("📊 Admin Panel")
    st.subheader("Analytics & Registration Data")
    
    try:
        import db
        
        # Overview cards
        col1, col2, col3 = st.columns(3)
        
        stats = db.get_overview_metrics()
        
        with col1:
            st.metric("Total Registrations", stats.get("total_registrations", 0))
        with col2:
            st.metric("Questionnaires Completed", stats.get("questionnaires_completed", 0))
        with col3:
            st.metric("Recommendations Viewed", stats.get("recommendations_viewed", 0))
        
        st.markdown("---")
        
        # Export button
        if st.button("📥 Export Registrations to CSV"):
            csv_file = db.export_registrations_csv()
            with open(csv_file, "rb") as f:
                st.download_button(
                    label="Download CSV",
                    data=f.read(),
                    file_name="registrations.csv",
                    mime="text/csv"
                )
        
        st.markdown("---")
        
        # Add this at the end of the admin page (around line 1100)

        with st.expander("🔬 Phase 3: Mean Reversion Debug"):
            st.subheader("Return Assumptions & Volatility")
        
            col1, col2 = st.columns(2)
        
            with col1:
                st.write("**Return Assumptions by Risk Category:**")
                for risk_cat, returns in CATEGORY_RETURNS.items():
                    st.write(f"**{risk_cat}:**")
                    st.write(f"  • Conservative: {returns['conservative']:.1f}%")
                    st.write(f"  • Expected: {returns['expected']:.1f}%")
                    st.write(f"  • Best Case: {returns['best_case']:.1f}%")
        
            with col2:
                st.write("**Volatility by Risk Category:**")
                for risk_cat, vol in CATEGORY_VOLATILITY.items():
                    st.write(f"**{risk_cat}:** {vol:.1f}%")
        
            # Mean reversion simulator
            st.markdown("---")
            st.write("**Test Mean Reversion Logic:**")
        
            test_base = st.number_input("Base Return (10yr avg) %", value=9.0, step=0.1)
            test_recent = st.number_input("Recent 1Y Return %", value=14.5, step=0.1)
        
            adjusted = apply_mean_reversion(test_base, test_recent)
        
            st.write(f"**Result:** {test_base:.1f}% → {adjusted:.1f}%")
            if adjusted < test_base:
                st.success(f"Mean reversion applied (reduced by {test_base - adjusted:.1f}%)")
            else:
                st.info("No mean reversion (market conditions normal)")

    
    except Exception as e:
        st.error(f"Error loading admin data: {e}")


# ===================================================================
# MAIN APP FLOW
# ===================================================================

def main():
    """Main application orchestration."""
    init_session_state()
    
    # Check for admin route
    if st.query_params.get("admin") == "1":
        render_admin_page()
        return
    
    # Main flow orchestration
    if st.session_state.current_step == "home":
        render_home_page()
    
    elif st.session_state.current_step == "risk_assessment":
        render_risk_assessment()
    
    elif st.session_state.current_step == "registration":
        registration_and_recommendation_flow(
            st.session_state.risk_score,
            st.session_state.risk_category
        )
    
    elif st.session_state.current_step == "preference_input":
        render_preference_input()
    
    elif st.session_state.current_step == "recommendations":
        render_recommendations_display()
    
    else:
        st.error(f"Unknown step: {st.session_state.current_step}")
        if st.button("Back to Home"):
            st.session_state.current_step = "home"
            st.rerun()


if __name__ == "__main__":
    main()
