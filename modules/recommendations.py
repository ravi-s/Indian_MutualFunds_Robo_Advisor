# modules/recommendations.py
"""
Fund recommendations, filtering, and display (Phase 2 + Phase 3)
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import logging

from utils.constants import (
    CATEGORY_RETURNS, CATEGORY_VOLATILITY, RISK_HIERARCHY, DURATION_MAP, ALLOWED_FUND_TYPES, 
    DURATION_HIERARCHY, DEFAULT_DISPLAY_COUNT, VOLATILITY_BENCHMARKS
)
from utils.formatting import format_percentage, format_crores, format_currency

logger = logging.getLogger(__name__)


def get_freshness_badge(last_updated_str: str) -> dict:
    """
    Calculate freshness badge status and color based on last_updated date.
    
    Args:
        last_updated_str: Date string in YYYY-MM-DD format
        
    Returns:
        dict with keys: 'badge_text', 'badge_color', 'days_old', 'status'
    """
    try:
        last_updated_date = datetime.strptime(last_updated_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_old = (today - last_updated_date).days
        
        if days_old < 7:
            badge_color = "🟢"
            badge_text = f"🟢 Updated {days_old} day{'s' if days_old != 1 else ''} ago"
            status = "recent"
        elif days_old < 28:
            badge_color = "🟡"
            badge_text = f"🟡 Updated {days_old} days ago (1-4 weeks)"
            status = "moderate"
        else:
            badge_color = "🔴"
            badge_text = f"🔴 Data stale ({days_old} days old)"
            status = "stale"
        
        return {
            'badge_text': badge_text,
            'badge_color': badge_color,
            'days_old': days_old,
            'status': status
        }
    
    except Exception as e:
        logger.warning(f"Error parsing last_updated date '{last_updated_str}': {e}")
        return {
            'badge_text': '⚠️ Unknown data freshness',
            'badge_color': '⚠️',
            'days_old': None,
            'status': 'unknown'
        }
# ===================================================================
# Mean Reversion & Return Assumptions (Phase 3)
# ===================================================================

def get_category_return_assumptions(risk_category: str) -> dict:
    """
    Retrieve 10-year historical return assumptions for a risk category.
    
    Args:
        risk_category: One of "Low Risk", "Moderate Risk", "Medium Risk", "High Risk"
        
    Returns:
        dict with keys: conservative, expected, best_case (all as percentages)
        Example: {'conservative': 8.1, 'expected': 9.0, 'best_case': 9.9}
    """
    assumptions = CATEGORY_RETURNS.get(risk_category)
    
    if assumptions is None:
        logger.warning(f"Unknown risk category '{risk_category}'. Using 'Medium Risk' as fallback.")
        assumptions = CATEGORY_RETURNS["Medium Risk"]
    
    return assumptions


def get_category_volatility(risk_category: str) -> float:
    """
    Retrieve historical volatility for a risk category.
    
    Args:
        risk_category: One of "Low Risk", "Moderate Risk", "Medium Risk", "High Risk"
        
    Returns:
        float: Volatility as percentage (standard deviation)
    """
    volatility = CATEGORY_VOLATILITY.get(risk_category)
    
    if volatility is None:
        logger.warning(f"Unknown risk category '{risk_category}'. Using 'Medium Risk' volatility as fallback.")
        volatility = CATEGORY_VOLATILITY["Medium Risk"]
    
    return volatility


def apply_mean_reversion(base_return: float, recent_1yr_return: float) -> float:
    """
    Apply mean reversion adjustment to expected return.
    
    Logic: If recent 1-year returns exceed 10-year average by ≥5%, 
    reduce expected return by 1% (mean reversion principle).
    
    Args:
        base_return: 10-year historical average return (%)
        recent_1yr_return: Recent 1-year market return (%)
        
    Returns:
        float: Adjusted expected return (%)
        
    Example:
        >>> apply_mean_reversion(9.0, 14.5)  # 14.5 > 9+5? Yes
        8.0  # Reduced by 1%
        
        >>> apply_mean_reversion(9.0, 10.0)  # 10 < 14? No
        9.0  # No adjustment
    """
    threshold = base_return + 5.0
    
    if recent_1yr_return > threshold:
        adjusted_return = base_return - 1.0
        logger.info(
            f"Mean reversion applied: Recent 1Y return ({recent_1yr_return:.1f}%) "
            f"exceeds 10Y avg ({base_return:.1f}%) + 5% threshold. "
            f"Adjusting expected return from {base_return:.1f}% to {adjusted_return:.1f}%"
        )
        return adjusted_return
    else:
        logger.info(
            f"No mean reversion: Recent 1Y return ({recent_1yr_return:.1f}%) "
            f"is within normal range of 10Y avg ({base_return:.1f}%)"
        )
        return base_return


def get_confidence_score(volatility: float, fund_age_years: int = 10) -> str:
    """
    Calculate confidence score for projections based on volatility and fund age.
    
    Args:
        volatility: Historical volatility (%)
        fund_age_years: Fund age in years (default 10 = mature)
        
    Returns:
        str: Confidence level ("High", "Medium", "Low")
        
    Logic:
        Score combines volatility (70% weight) and age (30% weight)
        - High: Volatility <= 5% + any age, OR low volatility + mature
        - Medium: Moderate volatility (5-10%) + any age, OR good volatility + young
        - Low: High volatility (>10%) OR very young fund (<2 years)
    """
    # Score volatility (70% weight)
    if volatility <= 5.0:
        vol_score = 3  # High
    elif volatility <= 10.0:
        vol_score = 2  # Medium
    else:
        vol_score = 1  # Low
    
    # Score age (30% weight)
    if fund_age_years >= 10:
        age_score = 3  # High
    elif fund_age_years >= 5:
        age_score = 2  # Medium
    else:
        age_score = 1  # Low
    
    # Weighted combination: volatility (70%) + age (30%)
    combined_score = (vol_score * 0.7) + (age_score * 0.3)
    
    # Map combined score back to confidence level
    if combined_score >= 2.5:
        final_confidence = "High"
    elif combined_score >= 1.5:
        final_confidence = "Medium"
    else:
        final_confidence = "Low"
    
    logger.debug(
        f"Confidence Score: {final_confidence} "
        f"(combined: {combined_score:.2f}, vol: {vol_score}/3, age: {age_score}/3)"
    )
    
    return final_confidence



def get_confidence_percentage(confidence_level: str) -> int:
    """
    Map confidence level to approximate percentage.
    
    Args:
        confidence_level: One of "High", "Medium", "Low"
        
    Returns:
        int: Approximate probability/confidence as percentage
        
    Example:
        >>> get_confidence_percentage("High")
        70
        
        >>> get_confidence_percentage("Low")
        25
    """
    confidence_map = {
        "High": 70,      # ~70% confidence (conservative)
        "Medium": 50,    # ~50% confidence (expected)
        "Low": 25        # ~25% confidence (best case)
    }
    
    return confidence_map.get(confidence_level, 50)


def filter_and_sort_recommendations(
    df: pd.DataFrame, 
    risk_category: str, 
    investment_amount: float, 
    duration: str
) -> pd.DataFrame:
    """
    Filter and sort fund recommendations based on risk, amount, and duration.
    
    Args:
        df: Fund dataframe
        risk_category: User's risk category
        investment_amount: Investment amount in ₹
        duration: Investment duration string
        
    Returns:
        Filtered and sorted dataframe
    """
    internal_duration = DURATION_MAP.get(duration, "")
    allowed_risk_profiles = RISK_HIERARCHY.get(risk_category, [risk_category])
    
    # Filter by risk profile
    df_step1 = df[df["risk_profile"].isin(allowed_risk_profiles)].copy()
    
    # Filter by investment amount
    df_step2 = df_step1[df_step1["min_investment"] <= investment_amount].copy()
    
    # Filter by duration
    allowed_durations = DURATION_HIERARCHY.get(internal_duration, [internal_duration])
    df_step3 = df_step2[df_step2["duration"].isin(allowed_durations)].copy()
    
    # Filter by fund type/category
    allowed_rules = ALLOWED_FUND_TYPES.get(internal_duration)
    if allowed_rules:
        df_step3 = df_step3[df_step3["fund_type"].isin(allowed_rules["Type"])].copy()
        cats = allowed_rules.get("Category") or []
        if cats:
            df_step3 = df_step3[df_step3["fund_category"].isin(cats)].copy()
    
    # Sort by rating, returns, expense ratio
    sorted_df = df_step3.sort_values(
        by=["rating", "return_5y", "return_3y", "exp_ratio"],
        ascending=[False, False, False, True]
    )
    
    # Remove duplicates
    sorted_df = sorted_df.drop_duplicates(subset=['fund_name'], keep='first')
    
    return sorted_df


def format_recommendation_table(df_sorted: pd.DataFrame, limit=None) -> pd.DataFrame:
    """
    Format recommendation table with all columns including freshness badge.
    
    Args:
        df_sorted: Sorted fund dataframe
        limit: Number of rows to display
        
    Returns:
        Formatted dataframe ready for st.dataframe()
    """
    display_df = df_sorted.head(limit or len(df_sorted)).reset_index(drop=True)
    display_df["Rank"] = display_df.index + 1
    
    # Apply formatting
    display_df["aum_cr"] = display_df["aum_cr"].apply(format_crores)
    display_df["return_1y"] = display_df["return_1y"].fillna(0).apply(format_percentage)
    display_df["return_3y"] = display_df["return_3y"].fillna(0).apply(format_percentage)
    display_df["return_5y"] = display_df["return_5y"].fillna(0).apply(format_percentage)
    display_df["exp_ratio"] = display_df["exp_ratio"].apply(format_percentage)
    display_df["min_investment"] = display_df["min_investment"].apply(format_currency)
    
    # Phase 3: Add data freshness badge
    display_df["Data Freshness"] = display_df["last_updated"].apply(
        lambda x: get_freshness_badge(x)['badge_text']
    )
    
    display_cols = [
        "Rank", "fund_name", "fund_category", "fund_type", "aum_cr",
        "return_1y", "return_3y", "return_5y", "exp_ratio", "min_investment",
        "rating", "remarks", "Data Freshness"
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
        "Data Freshness": "Data Freshness"
    }
    
    return display_df[display_cols].rename(columns=display_names)


def render_recommendations_display():
    """Render fund recommendations page."""
    st.title("Fund Recommendations")
    st.subheader("Step 4 of 4: Your Customised Fund List")
    
    # Mark recommendations_viewed for registered users
    reg_id = st.session_state.get("registration_id")
    if reg_id:
        try:
            import db
            db.mark_recommendations_viewed(reg_id)
        except Exception:
            pass  # Non-blocking
    
    st.markdown(
        f"**Filtering by:** "
        f"Risk Profile: **{st.session_state.risk_category}**, "
        f"Duration: **{st.session_state.duration}**, "
        f"Min. Investment: **{format_currency(st.session_state.investment_amount)}**"
    )
    
    from roboadvisor import load_fund_data
    fund_df = load_fund_data()
    recommended_funds = filter_and_sort_recommendations(
        fund_df,
        st.session_state.risk_category,
        st.session_state.investment_amount,
        st.session_state.duration,
    )
    
    # Check for stale data
    if not recommended_funds.empty:
        stale_funds = recommended_funds[recommended_funds["last_updated"].apply(
            lambda x: get_freshness_badge(x)['status'] == 'stale'
        )]
        
        if not stale_funds.empty:
            st.warning(
                f"⚠️ **Data Alert:** {len(stale_funds)} fund(s) have data older than 4 weeks. "
                f"Consider refreshing data by running the data pipeline."
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
    
    # Show more button
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
    
    # Navigation buttons
    if st.button("Modify Investment Preferences", use_container_width=True):
        st.session_state.current_step = "preference_input"
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
        st.rerun()
    
    if st.button("Back to Home", use_container_width=True):
        st.session_state.current_step = "home"
        st.rerun()
