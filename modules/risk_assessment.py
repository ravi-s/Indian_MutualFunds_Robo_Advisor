# modules/risk_assessment.py
"""
Risk Assessment Questionnaire & Scoring (Phase 2)
"""

import streamlit as st
from modules.utils_ui import init_session_state
from utils.constants import RISK_QUESTIONNAIRE, RISK_CATEGORIES


def calculate_risk_score(answers: dict) -> tuple:
    """
    Calculate total risk score and map to risk category.
    
    Args:
        answers: Dict of question_id -> score
        
    Returns:
        Tuple: (total_score, category_name, category_description)
    """
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


def render_risk_assessment():
    """Render risk assessment questionnaire form."""
    st.title("Risk Assessment Questionnaire")
    st.subheader("Step 1 of 4: Determine Your Risk Profile")
    
    with st.form("risk_form"):
        st.markdown(f"**Please answer all {len(RISK_QUESTIONNAIRE)} questions:**")
        answers_scores = {}
        
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
            st.error("Please ensure all questions are answered.")
            return
        
        total_score, category, description = calculate_risk_score(answers_scores)
        st.session_state.risk_score = total_score
        st.session_state.risk_category = category
        st.session_state.risk_description = description
        st.session_state.risk_answers = answers_scores
        
        # Show results immediately
        st.success(
            f"✅ Your Risk Score: **{total_score}** (Range: 13-45) \n"
            f"📊 Your Risk Category: **{category}** \n"
            f"💡 {description}"
        )
        
        st.markdown("---")
        st.markdown("### What's Next?")
        st.info(
            "To get personalized mutual fund recommendations, you'll need to:\n"
            "1. **Register** (email + consent)\n"
            "2. Enter your investment preferences\n"
            "3. View customized fund recommendations"
        )
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Continue to Registration", use_container_width=True, type="primary"):
                st.session_state.current_step = "registration"
                st.rerun()
        with col2:
            if st.button("🚪 Exit to Home page", use_container_width=True):
                st.session_state.clear()
                init_session_state()
                st.session_state.current_step = "home"
                st.rerun()
        
        render_feedback_footer()


def render_feedback_footer():
    """Render feedback footer."""
    st.markdown("---")
    st.caption("💬 Feedback? Issues? Let us know!")
