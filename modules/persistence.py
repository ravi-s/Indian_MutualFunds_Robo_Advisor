"""
Persistence Module - Phase 3 Iteration 2
Save, retrieve, and manage investment goals in the database.

Features:
- Generate unique Goal IDs
- Save goal data to database
- Retrieve goal history
- Email notifications (Phase 3.3)
- Revisit & update goals (Phase 4)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)


# ===================================================================
# GOAL ID GENERATION
# ===================================================================

def generate_goal_id(registration_id: int | None = None) -> str:
    """
    Generate a unique, shareable Goal ID.
    
    Format: GOAL_YYYYMMDD_XXXXX
    where XXXXX is a 5-char hash of timestamp + registration_id
    
    Args:
        registration_id: Optional registration ID
        
    Returns:
        Unique goal ID string
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    
    # Create a hash of timestamp + registration_id for uniqueness
    seed = f"{now.isoformat()}{registration_id or 'anon'}"
    hash_obj = hashlib.md5(seed.encode())
    hash_suffix = hash_obj.hexdigest()[:5].upper()
    
    goal_id = f"GOAL_{date_str}_{hash_suffix}"
    return goal_id


# ===================================================================
# GOAL PERSISTENCE (Database Operations)
# ===================================================================

def save_goal(goal_data: dict) -> str:
    """
    Save a goal to the database.
    
    Args:
        goal_data: Dict with keys:
          - registration_id (int, optional)
          - corpus (float)
          - sip (float)
          - horizon (int)
          - risk_category (str)
          - conservative_projection (float)
          - expected_projection (float)
          - best_case_projection (float)
          - confidence (str)
          - adjusted_return (float)
          - created_at (str, ISO format)
          
    Returns:
        goal_id (str)
    """
    try:
        import db
        
        goal_id = generate_goal_id(goal_data.get("registration_id"))
        
        # Call database function to insert goal
        db.save_goal(
            goal_id=goal_id,
            registration_id=goal_data.get("registration_id"),
            corpus=goal_data["corpus"],
            sip=goal_data["sip"],
            horizon=goal_data["horizon"],
            risk_category=goal_data["risk_category"],
            conservative_projection=goal_data["conservative_projection"],
            expected_projection=goal_data["expected_projection"],
            best_case_projection=goal_data["best_case_projection"],
            confidence=goal_data["confidence"],
            adjusted_return=goal_data["adjusted_return"],
            created_at=goal_data["created_at"]
        )
        
        logger.info(f"Goal saved: {goal_id}")
        return goal_id
    
    except Exception as e:
        logger.error(f"Error saving goal: {e}")
        raise


def retrieve_goal(goal_id: str) -> dict:
    """
    Retrieve a saved goal by ID.
    
    Args:
        goal_id: Goal ID (e.g., "GOAL_20251208_ABC123")
        
    Returns:
        Goal data dict or empty dict if not found
    """
    try:
        import db
        goal = db.get_goal(goal_id)
        return goal if goal is not None else {}
    
    except Exception as e:
        logger.error(f"Error retrieving goal {goal_id}: {e}")
        return {}


def get_user_goals(registration_id: int) -> pd.DataFrame:
    """
    Retrieve all goals for a user.
    
    Args:
        registration_id: User's registration ID
        
    Returns:
        DataFrame with all user's goals
    """
    try:
        import db
        goals_df = db.get_user_goals(registration_id)
        return goals_df
    
    except Exception as e:
        logger.error(f"Error retrieving goals for user {registration_id}: {e}")
        return pd.DataFrame()


def mark_goal_email_sent(goal_id: str) -> bool:
    """
    Mark a goal as having email notification sent (Phase 3.3).
    
    Args:
        goal_id: Goal ID
        
    Returns:
        True if successful
    """
    try:
        import db
        db.mark_goal_email_sent(goal_id)
        logger.info(f"Goal {goal_id} marked as email sent")
        return True
    
    except Exception as e:
        logger.error(f"Error marking goal email: {e}")
        return False


def mark_goal_revisited(goal_id: str) -> bool:
    """
    Mark a goal as revisited (Phase 4 - Dashboard).
    
    Args:
        goal_id: Goal ID
        
    Returns:
        True if successful
    """
    try:
        import db
        db.mark_goal_revisited(goal_id)
        logger.info(f"Goal {goal_id} marked as revisited")
        return True
    
    except Exception as e:
        logger.error(f"Error marking goal revisited: {e}")
        return False


# ===================================================================
# GOAL FORMATTING & DISPLAY
# ===================================================================

def format_goal_for_display(goal: dict) -> dict:
    """
    Format goal data for UI display.
    
    Args:
        goal: Raw goal dict from database
        
    Returns:
        Formatted dict with currency/percentage strings
    """
    from utils.formatting import format_currency, format_percentage
    
    return {
        "Goal ID": goal.get("goal_id"),
        "Created": goal.get("created_at"),
        "Corpus": format_currency(goal.get("corpus", 0)),
        "Monthly SIP": format_currency(goal.get("sip", 0)),
        "Horizon": f"{goal.get('horizon', 0)} years",
        "Risk": goal.get("risk_category"),
        "Expected Projection": format_currency(goal.get("expected_projection", 0)),
        "Confidence": goal.get("confidence"),
        "Status": goal.get("status", "saved")
    }


# ===================================================================
# UI COMPONENTS - Goal Retrieval & History
# ===================================================================

def render_goal_history():
    """
    Render a page showing user's goal history (Phase 4 - Dashboard).
    
    Allows user to:
    - View all saved goals
    - Revisit a goal
    - Compare projections
    - Email results
    """
    st.title("My Goals")
    st.subheader("Your Investment Goal History")
    
    reg_id = st.session_state.get("registration_id")
    
    if not reg_id:
        st.warning("Please register first to view your goals.")
        if st.button("Go to Registration", width = 'stretch'):
            st.session_state.current_step = "registration"
            st.rerun()
        return
    
    # Fetch goals
    goals_df = get_user_goals(reg_id)
    
    if goals_df.empty:
        st.info("No saved goals yet. Create one in the Goal Path!")
        return
    
    st.markdown(f"**Total Goals:** {len(goals_df)}")
    st.markdown("---")
    
    # Display goals table
    display_cols = ["Goal ID", "Created", "Corpus", "Monthly SIP", "Horizon", 
                    "Risk", "Expected Projection", "Confidence"]
    
    if all(col in goals_df.columns for col in display_cols):
        st.dataframe(
            goals_df[display_cols],
            width = 'stretch',
            hide_index=True
        )
    else:
        st.dataframe(goals_df, width = 'stretch', hide_index=True)
    
    st.markdown("---")
    
    # Revisit goal option
    st.markdown("### Revisit a Goal")
    goal_ids = goals_df["goal_id"].tolist() if "goal_id" in goals_df.columns else []
    
    if goal_ids:
        selected_goal_id = st.selectbox(
            "Select a goal to revisit:",
            options=goal_ids
        )
        
        if st.button("📍 Revisit This Goal", width='stretch'):
            if selected_goal_id is not None:
                goal = retrieve_goal(selected_goal_id)
                
                if goal:
                    # Store in session state
                    st.session_state.revisiting_goal_id = selected_goal_id
                    st.session_state.goal_corpus = goal.get("corpus")
                    st.session_state.goal_sip = goal.get("sip")
                    st.session_state.goal_horizon = goal.get("horizon")
                    
                    # Mark as revisited
                    mark_goal_revisited(selected_goal_id)
                    
                    # Show goal details
                    st.success(f"✅ Loaded goal {selected_goal_id}")
                    st.info("Goal data has been loaded. You can update projections with new market data.")
                else:
                    st.error(f"Could not load goal {selected_goal_id}")
            else:
                st.error("No goal selected to revisit.")


def render_goal_share():
    """
    Render a page for sharing goals via email or link (Phase 3.3).
    
    Features:
    - Share Goal ID via email
    - Generate shareable link
    - Add custom message
    """
    st.title("Share Your Goal")
    st.subheader("Share Results with Friends or Advisors")
    
    goal_id = st.session_state.get("goal_id")
    
    if not goal_id:
        st.warning("No goal to share. Create a goal first.")
        return
    
    st.info(f"Goal ID: **{goal_id}**")
    
    # Share methods
    share_method = st.radio(
        "How would you like to share?",
        ["Email Results", "Share Link", "Copy Goal ID"]
    )
    
    if share_method == "Email Results":
        recipient_email = st.text_input("Recipient Email")
        custom_message = st.text_area(
            "Add a personal message (optional)",
            placeholder="Share your thoughts..."
        )
        
        if st.button("📧 Send Email", width = 'stretch'):
            st.info("✅ Email feature coming in Phase 3.3")
            logger.info(f"Email share requested for goal {goal_id}")
    
    elif share_method == "Share Link":
        # Generate shareable link (Phase 4)
        share_link = f"https://robo-advisor.example.com/goal/{goal_id}"
        st.code(share_link, language="text")
        st.info("📋 Link feature coming in Phase 4 (Dashboard)")
    
    elif share_method == "Copy Goal ID":
        st.code(goal_id, language="text")
        st.caption("Share this Goal ID to let others view your goal using the 'Revisit Goal' feature.")


# ===================================================================
# EXPORT GOALS
# ===================================================================

def export_goals_to_csv(registration_id: int) -> str:
    """
    Export user's goals to CSV file (for download).
    
    Args:
        registration_id: User's registration ID
        
    Returns:
        Path to CSV file
    """
    try:
        import db
        
        goals_df = db.get_user_goals(registration_id)
        
        if goals_df.empty:
            return ''
        
        filename = f"goals_{registration_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        goals_df.to_csv(filename, index=False)
        
        logger.info(f"Goals exported to {filename}")
        return filename
    
    except Exception as e:
        logger.error(f"Error exporting goals: {e}")
        return ''