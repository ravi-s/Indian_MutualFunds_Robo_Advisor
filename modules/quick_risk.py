# modules/quick_risk.py
"""
Quick Risk Profile Selection Module

This module provides a fast-track risk assessment for users who want to quickly
select a risk profile without completing the full questionnaire. Users can choose
from three predefined risk categories (Low, Medium, High) and either proceed with
that selection or opt into the detailed risk assessment questionnaire.

The quick selection populates the initial risk_category in session_state, allowing
users to refine their profile later through the full questionnaire if desired.
"""

import streamlit as st
from modules.utils_ui import render_feedback_footer

# Predefined risk profile options: (display_name, description)
# Used for the radio button selection and to map user choices back to risk categories
QUICK_OPTIONS = [
    ("Low Risk", "Capital protection, fine with lower returns."),
    ("Medium Risk", "Balance between growth and stability (default)."),
    ("High Risk", "Okay with big ups/downs for higher growth."),
]

def render_quick_risk():
    """
    Render the quick risk profile selection interface.
    
    This is Step 1 of the onboarding flow. Users select a quick risk profile
    from three predefined options. They can then either:
    1. Continue to goal path with the selected profile
    2. Take the full risk questionnaire for a detailed assessment
    
    Session State Updates:
    - risk_category: Set to the selected risk name (Low/Medium/High Risk)
    - risk_score: Set to None for fast-path selections
    - current_step: Navigation state updated based on user action
    """
    st.title("Choose Your Risk Profile")
    st.subheader("Step 1 of 4: Pick a starting point")

    st.markdown(
        "You can **pick a quick profile now** and refine it later with a detailed questionnaire."
    )

    # Create radio button labels combining name and description for clarity
    labels = [f"{name} - {desc}" for name, desc in QUICK_OPTIONS]
    default_index = 1  # Medium Risk is the default selection
    
    # Display radio button for user to select a risk profile
    choice = st.radio(
        "Select the option closest to you:",
        options=labels,
        index=default_index,
        key="quick_risk_choice",
    )

    # Map the selected label back to the risk category name (e.g., "Medium Risk")
    selected_name = QUICK_OPTIONS[labels.index(choice)][0]

    # Create two-column layout for action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Primary action: Accept quick profile and move to goal path
        if st.button("Continue to Goal Path", type="primary", use_container_width=True):
            st.session_state.risk_category = selected_name
            st.session_state.risk_score = None  # fast path - no detailed score yet
            st.session_state.current_step = "goal_path_stage1"
            st.rerun()
    
    with col2:
        # Secondary action: Skip quick profile and complete full questionnaire
        if st.button("Take full risk questionnaire", use_container_width=True):
            st.session_state.current_step = "risk_assessment"
            st.rerun()

    render_feedback_footer()
