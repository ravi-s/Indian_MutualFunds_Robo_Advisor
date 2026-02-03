"""
Goal Path Module - Phase 3 Iteration 2
Capture investment goals, calculate projections, and display confidence metrics.

Features:
- Stage 1: Capture goal inputs (corpus, SIP, horizon)
- Stage 2: Display projections with mean reversion applied
- Confidence scoring based on volatility and fund age
- Data freshness indicators
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from typing import Optional
from modules.pdf_export import generate_goal_pdf

from modules.persistence import save_goal
from modules.utils_ui import navigate_to_home
from utils.constants import (
    BASELINE_AS_OF,
    CATEGORY_RETURNS, 
    CATEGORY_VOLATILITY, 
    VOLATILITY_BENCHMARKS,
    RECENT_1YR_MARKET_RETURNS,
)
from utils.formatting import format_currency, format_percentage
logger = logging.getLogger(__name__)


# ===================================================================
# GOAL CALCULATIONS (Business Logic - Testable)
# ===================================================================

def calculate_corpus_growth(
    initial_corpus: float,
    monthly_sip: float,
    years: int,
    annual_return_pct: float
) -> float:
    """
    Calculate final corpus after SIP for given years at annual return.
    
    Formula:
    FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
    where:
      PV = initial corpus
      PMT = monthly SIP
      r = monthly return rate (annual_return / 12 / 100)
      n = number of months
    
    Args:
        initial_corpus: Starting amount (₹)
        monthly_sip: Monthly SIP (₹)
        years: Investment duration (years)
        annual_return_pct: Annual return percentage
        
    Returns:
        Final corpus (₹)
    """
    if years <= 0:
        return initial_corpus + (monthly_sip * 12 * years)
    
    if annual_return_pct == 0:
        # No returns - just compound SIP
        total_sip = monthly_sip * 12 * years
        return initial_corpus + total_sip
    
    monthly_return_pct = annual_return_pct / 12 / 100
    months = years * 12
    
    # FV of initial corpus
    fv_corpus = initial_corpus * ((1 + monthly_return_pct) ** months)
    
    # FV of SIP (using FV of annuity formula)
    fv_sip = monthly_sip * (((1 + monthly_return_pct) ** months - 1) / monthly_return_pct)
    
    return fv_corpus + fv_sip


def get_category_return_assumptions(risk_category: str) -> dict:
    """
    Get return assumptions for a risk category.
    
    Args:
        risk_category: Risk category name
        
    Returns:
        dict with 'conservative', 'expected', 'best_case' keys
    """
    return CATEGORY_RETURNS.get(risk_category, CATEGORY_RETURNS["Medium Risk"])


def get_category_volatility(risk_category: str) -> float:
    """
    Get volatility for a risk category.
    
    Args:
        risk_category: Risk category name
        
    Returns:
        Volatility percentage
    """
    return CATEGORY_VOLATILITY.get(risk_category, CATEGORY_VOLATILITY["Medium Risk"])


def apply_mean_reversion(base_return: float, recent_1yr_return: float) -> float:
    """
    Apply mean reversion adjustment if market is overheated.
    
    Logic:
    - If recent_1yr_return > (base_return + 5%), adjust down by 1%
    - Otherwise, keep base_return unchanged
    
    Args:
        base_return: Long-term expected return %
        recent_1yr_return: Recent 1-year actual return %
        
    Returns:
        Adjusted return percentage
    """
    threshold = base_return + 5.0
    
    if recent_1yr_return > threshold:
        return base_return - 1.0
    
    return base_return


def get_confidence_score(volatility: float, fund_age_years: int) -> str:
    """
    Calculate confidence level based on volatility and fund maturity.
    
    Scoring:
    - Volatility: vol <= 5 = 3pts, 5-10 = 2pts, >10 = 1pt
    - Fund Age: age >= 10 = 3pts, 5-9 = 2pts, <5 = 1pt
    - Combined: (vol_score * 0.7) + (age_score * 0.3)
      - Result >= 2.5 = "High"
      - Result >= 1.5 = "Medium"
      - Result < 1.5 = "Low"
    
    Args:
        volatility: Category volatility percentage
        fund_age_years: Fund maturity in years
        
    Returns:
        "High", "Medium", or "Low"
    """
    # Volatility scoring
    if volatility <= 5.0:
        vol_score = 3
    elif volatility <= 10.0:
        vol_score = 2
    else:
        vol_score = 1
    
    # Fund age scoring
    if fund_age_years >= 10:
        age_score = 3
    elif fund_age_years >= 5:
        age_score = 2
    else:
        age_score = 1
    
    # Combined score (weighted)
    combined = (vol_score * 0.7) + (age_score * 0.3)
    
    if combined >= 2.5:
        return "High"
    elif combined >= 1.5:
        return "Medium"
    else:
        return "Low"


def get_confidence_percentage(confidence_level: str) -> int:
    """
    Map confidence level to percentage (for display).
    
    Args:
        confidence_level: "High", "Medium", or "Low"
        
    Returns:
        Percentage (0-100)
    """
    mapping = {
        "High": 70,
        "Medium": 50,
        "Low": 25
    }
    return mapping.get(confidence_level, 50)

def calculate_goal_projections(
    corpus: float,
    sip: float,
    horizon: int,
    risk_category: str,
    recent_1yr_return: Optional[float] = None
) -> dict:

    """
    Calculate goal projections (conservative, expected, best-case).
    
    Args:
        corpus: Initial corpus (₹)
        sip: Monthly SIP (₹)
        horizon: Investment horizon (years)
        risk_category: Risk category
        recent_1yr_return: Optional recent 1-year return for mean reversion
        
    Returns:
        dict with projections and metadata
    """
    assumptions = get_category_return_assumptions(risk_category)
    base_return = assumptions["expected"]

    # Phase 3a: plug in real 1Y market data if not explicitly provided
    if recent_1yr_return is None:
        recent_1yr_return = RECENT_1YR_MARKET_RETURNS.get(risk_category, base_return)

    # Always apply mean reversion using a concrete 1Y value
    # Ensure recent_1yr_return is not None before passing to apply_mean_reversion
    recent_1yr_return = recent_1yr_return if recent_1yr_return is not None else base_return
    adjusted_return = apply_mean_reversion(base_return, recent_1yr_return)
    
    # Calculate projections
    conservative = calculate_corpus_growth(
        corpus, sip, horizon, assumptions["conservative"]
    )
    expected = calculate_corpus_growth(
        corpus, sip, horizon, adjusted_return
    )
    best_case = calculate_corpus_growth(
        corpus, sip, horizon, assumptions["best_case"]
    )
    
    # Confidence scoring
    volatility = get_category_volatility(risk_category)
    confidence = get_confidence_score(volatility, fund_age_years=10)  # Assuming mature fund
    confidence_pct = get_confidence_percentage(confidence)
    
    mean_reversion_applied = (adjusted_return != base_return)

    return {
        "conservative": conservative,
        "expected": expected,
        "best_case": best_case,
        "adjusted_return": adjusted_return,
        "base_return": base_return,
        "confidence": confidence,
        "confidence_percentage": confidence_pct,
        "volatility": volatility,
        "mean_reversion_applied": mean_reversion_applied,
    }



# ===================================================================
# UI COMPONENTS - Stage 1
# ===================================================================

def render_goal_path_stage1():
    """
    Render Goal Path Stage 1: Capture goal inputs.
    
    Inputs:
    - Initial Corpus (₹)
    - Monthly SIP (₹)
    - Investment Horizon (years)
    - Risk Category (read-only, from Step 1)
    """
    
    st.title("Goal Path: Stage 1")
    st.subheader("Step 5 of 6: Define Your Investment Goal")
    
    # CRITICAL DISCLAIMER (Non-dismissable)
    """ ack = st.session_state.get("goal_path_disclaimer_acknowledged", False)
    if not ack:
        st.error(
                "⚠️ **CRITICAL DISCLAIMER - MUST ACKNOWLEDGE**\n\n"
                "This tool is for **informational purposes only**.\n\n"
                "It does **NOT** constitute investment advice.\n\n"
                "**Past performance is NO guarantee of future results**.\n\n"
                "We are **NOT SEBI-registered investment advisors**.\n\n"
                "Please consult a **certified financial advisor** before investing."
            )
        if st.checkbox("✅ I acknowledge this disclaimer and understand the risks"):
                st.session_state.goal_path_disclaimer_acknowledged = True
                st.rerun()
        else:
                st.stop() """
    
    st.info(
        "This goal path uses historical averages for your risk category to show "
        "three possible scenarios. It is an estimate, not a guarantee."
    )

    
        # Display current risk profile
    risk_category = st.session_state.get("risk_category")
    st.info(f"📊 Your Risk Profile: **{risk_category}**")

    
    # Input form
    with st.form("goal_path_stage1_form"):
        st.markdown("### Investment Details")
        
        # Initial Corpus
        corpus = st.number_input(
            "Initial Corpus (₹)",
            min_value=0.0,
            value=500000.0,
            step=50000.0,
            format="%.0f",
            help="Starting amount you'll invest"
        )
        
        # Monthly SIP
        sip = st.number_input(
            "Monthly SIP (₹)",
            min_value=0.0,
            value=10000.0,
            step=1000.0,
            format="%.0f",
            help="Systematic Investment Plan - regular monthly contribution"
        )
        
        # Investment Horizon
        horizon = st.number_input(
            "Investment Horizon (Years)",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            help="How long will you invest?"
        )
        
        submitted = st.form_submit_button(
            "Calculate Projections (Stage 2)",
            width='stretch',
            type="primary"
        )
    
    if submitted:
        # Validation
        if corpus < 0 or sip < 0 or horizon <= 0:
            st.error("Please enter valid positive values.")
            return
        
        if corpus == 0 and sip == 0:
            st.error("Either corpus or monthly SIP must be greater than 0.")
            return
        
        # Save to session state
        st.session_state.goal_corpus = corpus
        st.session_state.goal_sip = sip
        st.session_state.goal_horizon = horizon
        
        # Move to Stage 2
        st.session_state.current_step = "goal_path_stage2"
        st.rerun()
    
    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Recommendations", width = 'stretch'):
            st.session_state.current_step = "recommendations"
            st.rerun()
    
    with col2:
        if st.button("🏠 Home", width = 'stretch'):
            navigate_to_home()


# ===================================================================
# UI COMPONENTS - Stage 2
# ===================================================================

def render_goal_path_stage2():
    """
    Render Goal Path Stage 2: Display projections and save option.

    Shows:
    - Conservative projection
    - Expected projection (with mean reversion applied)
    - Best-case projection
    - Confidence level with explanation
    - Data freshness badge
    - Option to save goal
    """
    st.title("Goal Path: Stage 2")
    st.subheader("Your Projections & Next Steps")

    # Light disclaimer only (no blocking)
    st.caption(
        "These projections are estimates based on past data. They are not guarantees "
        "of future performance."
    )

    # Retrieve inputs from session state (works for both real goal and demo)
    corpus = st.session_state.get("goal_corpus", 0.0)
    sip = st.session_state.get("goal_sip", 0.0)
    horizon = st.session_state.get("goal_horizon", 5)
    risk_category = st.session_state.get("risk_category") or "Medium Risk"

    # Guard against totally empty goal
    if corpus == 0.0 and sip == 0.0:
        st.warning(
            "We need either an initial corpus or a monthly SIP greater than zero "
            "to show a goal path. Please define a goal first."
        )
        if st.button("Go to Goal Input", use_container_width=True):
            st.session_state.current_step = "goal_path_stage1"
            st.rerun()
        return

    st.markdown(
        f"""
        **Your Goal Summary:**
        - Initial Corpus: {format_currency(corpus)}
        - Monthly SIP: {format_currency(sip)}
        - Investment Horizon: {horizon} years
        - Risk Category: **{risk_category}**
        """
    )

    st.markdown("---")

    # Calculate projections
    projections = calculate_goal_projections(
        corpus=corpus,
        sip=sip,
        horizon=horizon,
        risk_category=risk_category,
        recent_1yr_return=None,  # uses RECENT_1YR_MARKET_RETURNS fallback
    )

    # Display projections
    st.markdown(f"### Projected Corpus After {horizon} Years")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "🟢 Conservative",
            format_currency(projections["conservative"]),
            help="Lower growth scenario",
        )
    with col2:
        st.metric(
            "🟡 Expected",
            format_currency(projections["expected"]),
            help="Most likely scenario (adjusted for market conditions)",
        )
    with col3:
        st.metric(
            "🔵 Best Case",
            format_currency(projections["best_case"]),
            help="Optimistic scenario",
        )

    st.markdown("---")

    # Baseline date
    st.info(
        f"📅 Return assumptions as of **{BASELINE_AS_OF}**, reviewed quarterly.",
        width="stretch",
    )

    st.markdown("---")

    # Confidence & Volatility
    st.markdown("### Projection Confidence")

    confidence = projections["confidence"]
    confidence_pct = projections["confidence_percentage"]
    volatility = projections["volatility"]
    adjusted_return = projections["adjusted_return"]

    if confidence == "High":
        badge = "🟢 **HIGH** (70% confidence)"
    elif confidence == "Medium":
        badge = "🟡 **MEDIUM** (50% confidence)"
    else:
        badge = "🔴 **LOW** (25% confidence)"

    recent_1yr = RECENT_1YR_MARKET_RETURNS.get(
        risk_category, projections["base_return"]
    )
    recent_1yr = recent_1yr if recent_1yr is not None else projections["base_return"]

    st.markdown(
        f"""
        **Confidence Level:** {badge}

        This confidence level is based on:

        - **Volatility:** {format_percentage(volatility)}
          - Lower volatility = Higher confidence in projections
        - **Expected (Adjusted) Return:** {format_percentage(adjusted_return)}
          - Long-term base: {format_percentage(projections['base_return'])}
          - Recent 1Y performance: {format_percentage(recent_1yr)}
          - Mean reversion applied: {'Yes ✓' if projections['mean_reversion_applied'] else 'No (market normal)'}
        """
    )

    st.markdown("---")

    # Projection breakdown (advanced view)
    with st.expander("📊 Detailed Projection Breakdown"):
        st.write("**How we calculated your projections:**")

        st.write(
            f"""
            **Long-term base return** for {risk_category}: {format_percentage(projections['base_return'])}
            - Based on historical data for your risk level.
            - **Adjusted expected return** (final): {format_percentage(adjusted_return)}
            - If the last year was unusually strong or weak, we gently adjust expectations.
            - This is called **mean reversion**—extreme returns rarely persist.
            """
        )

        st.markdown("---")

        breakdown_df = pd.DataFrame(
            {
                "Scenario": ["Conservative", "Expected", "Best Case"],
                "Annual Return": [
                    format_percentage(
                        get_category_return_assumptions(risk_category)[
                            "conservative"
                        ]
                    ),
                    format_percentage(adjusted_return),
                    format_percentage(
                        get_category_return_assumptions(risk_category)["best_case"]
                    ),
                ],
                "Final Corpus": [
                    format_currency(projections["conservative"]),
                    format_currency(projections["expected"]),
                    format_currency(projections["best_case"]),
                ],
            }
        )
        st.dataframe(breakdown_df, width="stretch", hide_index=True)

    st.markdown("---")
    st.subheader("Save & Download Your Goal")

    # Ensure we have a goal_id in session (for PDF naming and future links)
    goal_id = st.session_state.get("goalid")

    col_save, col_pdf = st.columns(2)

    with col_save:
        if st.button("💾 Save Goal", use_container_width=True, type="primary"):
            try:
                goal_data = {
                    "registration_id": st.session_state.get("registration_id"),
                    "corpus": corpus,
                    "sip": sip,
                    "horizon": horizon,
                    "risk_category": risk_category,
                    "conservative_projection": projections["conservative"],
                    "expected_projection": projections["expected"],
                    "best_case_projection": projections["best_case"],
                    "confidence": projections["confidence"],
                    "adjusted_return": adjusted_return,
                    "created_at": datetime.now().isoformat(),
                }

                goal_id = save_goal(goal_data)
                st.session_state["goalid"] = goal_id
                st.success(f"Goal saved! Goal ID: {goal_id}")
                st.info(
                    "You can revisit this goal later using this ID or a shareable link (coming soon)."
                )
            except Exception as e:
                st.warning(f"Could not save goal: {e}")
                logger.error(f"Error saving goal: {e}")

    with col_pdf:
        disabled = goal_id is None
        if st.button(
            "📥 Generate PDF", use_container_width=True, disabled=disabled
        ):
            try:
                if disabled:
                    st.warning("Please save your goal first to generate a PDF.")
                else:
                    pdf_buffer = generate_goal_pdf(
                        goal_id=goal_id,
                        goal_name=f"{risk_category} Goal",
                        goal_inputs={
                            "startingcorpus": corpus,
                            "monthlysip": sip,
                            "horizonyears": horizon,
                            "riskcategory": risk_category,
                        },
                        projections=projections,
                        goal_url="",  # can be updated later
                    )

                    pdf_buffer.seek(0)
                    st.download_button(
                        label="Download Goal PDF",
                        data=pdf_buffer,
                        file_name=f"GoalPath_{goal_id}.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                logger.error(f"Error generating PDF: {e}")

    st.markdown("---")
    st.markdown("### Next Steps")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Back to Stage 1", width="stretch"):
            st.session_state.current_step = "goal_path_stage1"
            st.rerun()

    with col2:
        if st.button("📋 View Recommendations", width="stretch"):
            st.session_state.current_step = "preference_input"
            st.rerun()

    with col3:
        if st.button("🏠 Home", width="stretch"):
            navigate_to_home()

# ===================================================================
# HELPER: Get recommended funds for goal
# ===================================================================

def get_recommended_funds_for_goal(
    fund_df: pd.DataFrame,
    risk_category: str,
    sip: float
) -> pd.DataFrame:
    """
    Filter funds suitable for SIP-based goal investing.
    
    Args:
        fund_df: Fund dataframe
        risk_category: Risk category
        sip: Monthly SIP amount
        
    Returns:
        Filtered dataframe of recommended funds
    """
    from modules.recommendations import filter_and_sort_recommendations
    
    # For SIP, typically use "More than 1 year" duration
    filtered = filter_and_sort_recommendations(
        df=fund_df,
        risk_category=risk_category,
        investment_amount=sip,  # Use SIP as investment amount
        duration="More than 1 year"  # SIP-friendly duration
    )
    
    return filtered.head(5)  # Top 5 funds for goal