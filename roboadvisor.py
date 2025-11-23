# Import necessary libraries
import streamlit as st
import pandas as pd
import locale

# --- Configuration and Constants ---

# Application Title Requirement F-1.1
st.set_page_config(
    page_title="Mutual Fund Robo-Advisor",
    layout="wide", # Helps with mobile-responsiveness I-1.1
    initial_sidebar_state="collapsed"
)

# Constants based on Specification
CSV_FILE = 'funds.csv' # Using the new file name
MIN_INVESTMENT_AMOUNT = 500 # Validation F-2.3
DEFAULT_DISPLAY_COUNT = 3 # F-3.3

# Risk Questionnaire (F-1.2) - (Omitted for brevity, assumed correct)
RISK_QUESTIONNAIRE = {
    1: {"question": "In general, how would your friends describe you as a risk taker?", "options": {"A. A real gambler": 4, "B. Willing to take risks after thorough research": 3, "C. Cautious": 2, "D. A real risk avoider": 1}},
    2: {"question": "You are on a TV game show and can choose one of the following prizes. Which do you take?", "options": {"A. ₹10,000 in cash": 1, "B. 50% chance at winning ₹50,000": 2, "C. 25% chance at winning ₹1,00,000": 3, "D. 5% chance at winning ₹10,00,000": 4}},
    3: {"question": "You have just finished saving for a dream vacation. Three weeks before you leave, you lose your job. You would:", "options": {"A. Cancel the vacation": 1, "B. Take a much more modest vacation": 2, "C. Go as scheduled, reasoning that you need the break before your job search": 3, "D. Extend your vacation, treating it as a last chance to enjoy": 4}},
    4: {"question": "If you unexpectedly received ₹2,00,000 to invest, what would you do?", "options": {"A. Deposit it in a bank account or fixed deposit": 1, "B. Invest in safe, high-quality bonds or debt mutual funds": 2, "C. Invest in equity mutual funds or stocks": 3}},
    5: {"question": "When you think about investing in equity mutual funds or stocks, how comfortable are you?", "options": {"A. Not at all comfortable": 1, "B. Somewhat comfortable": 2, "C. Very comfortable": 3}},
    6: {"question": "When you hear the word \"risk,\" which comes to mind first?", "options": {"A. Loss": 1, "B. Uncertainty": 2, "C. Opportunity": 3, "D. Thrill": 4}},
    7: {"question": "Suppose experts predict prices of gold, real estate, or collectibles will rise, while bond prices may fall. Most of your investments are in government bonds. What would you do?", "options": {"A. Hold the bonds": 1, "B. Sell bonds, split proceeds between fixed deposits and gold/real estate funds": 2, "C. Invest all proceeds in gold/real estate funds": 3, "D. Invest all proceeds and borrow more to invest further in gold/real estate": 4}},
    8: {"question": "Given the following investment choices and their best/worst case returns, which do you prefer?", "options": {"A. ₹2,000 gain (best), no gain/loss (worst)": 1, "B. ₹8,000 gain (best), ₹2,000 loss (worst)": 2, "C. ₹26,000 gain (best), ₹8,000 loss (worst)": 3, "D. ₹48,000 gain (best), ₹24,000 loss (worst)": 4}},
    9: {"question": "In addition to your own money, you are given ₹10,000. Choose between:", "options": {"A. A sure gain of ₹5,000": 1, "B. 50% chance to gain ₹10,000, 50% chance nothing": 2}},
    10: {"question": "In addition to your own money, you are given ₹20,000. Choose between:", "options": {"A. A sure loss of ₹5,000": 2, "B. 50% chance to lose ₹10,000, 50% chance to lose nothing": 1}},
    11: {"question": "Suppose you inherit ₹10,00,000 and must invest all in one choice. Which do you select?", "options": {"A. Savings account or liquid fund": 1, "B. Hybrid mutual fund (mix of equity and debt)": 2, "C. Diversified equity mutual funds": 3, "D. Gold, commodities, or real estate": 4}},
    12: {"question": "If you had to invest ₹2,00,000, your most preferred allocation would be:", "options": {"A. 60% in low-risk, 30% in medium-risk, 10% in high-risk": 1, "B. 30% low-risk, 40% medium-risk, 30% high-risk": 2, "C. 10% low-risk, 40% medium-risk, 50% high-risk": 3}},
    13: {"question": "Your trusted friend is forming an investor group for a startup venture that could multiply your money many times if successful, but may fail. The chance of success is about 20%. If you had the money, how much would you invest?", "options": {"A. Nothing": 1, "B. One month's salary": 2, "C. Three months' salary": 3, "D. Six months' salary": 4}}
}

# Risk Score Categories (F-1.5, F-1.6 - Mapped to the four categories based on new score range 13-45)
RISK_CATEGORIES = [
    {"range": (13, 18), "name": "Low Risk", "description": "Low tolerance for risk (0-18 range)"},
    {"range": (19, 22), "name": "Moderate Risk", "description": "Below-average tolerance for risk (19-22 range)"},
    {"range": (23, 28), "name": "Medium Risk", "description": "Average/moderate tolerance for risk (23-28 range)"},
    {"range": (29, 45), "name": "High Risk", "description": "High tolerance for risk (29-45 range)"}
]

# Risk Hierarchy for Recursive Filtering (NEW LOGIC)
RISK_HIERARCHY = {
    "High Risk": ["High Risk", "Medium Risk", "Moderate Risk", "Low Risk"],
    "Medium Risk": ["Medium Risk", "Moderate Risk", "Low Risk"],
    "Moderate Risk": ["Moderate Risk", "Low Risk"],
    "Low Risk": ["Low Risk"]
}

# Mapping of fund types for Time-Horizon Filtering (NEW LOGIC)
ALLOWED_FUND_TYPES = {
    # FIX: Corrected Category names to match funds.csv data (e.g., 'Liquid' not 'Liquid Fund')
    "< 6 months": {
        "Category": ["Liquid", "Ultra Short Duration", "Short Duration Debt"], 
        "Type": ["Debt", "Hybrid"]
    },
    
    "6 months to 1 year": {
        "Category": [], 
        "Type": ["Debt", "Hybrid"]
    },
    
    "> 1 year": {
        "Category": [], 
        "Type": ["Debt", "Hybrid", "Equity", "Index/ETF"]
    }
}

# Investment Duration Options (F-2.2)
DURATION_OPTIONS = [
    "Less than 6 months",
    "6 months to 1 year",
    "More than 1 year"
]

# Mapping of user-facing strings to internal CSV strings (FIXED)
DURATION_MAP = {
    "Less than 6 months": "< 6 months",
    "6 months to 1 year": "6 months to 1 year",
    "More than 1 year": "> 1 year"
}


# Column Mapping for CSV
COLUMN_MAP = {
    'Risk Profile': 'risk_profile',
    'Duration': 'duration',
    'Min Investment': 'min_investment',
    'Rating': 'rating',
    '5Y Return %': 'return_5y',
    '3Y Return %': 'return_3y',
    'Expense Ratio': 'expense_ratio',
    'AUM (Cr)': 'aum_cr',
    '1Y Return %': 'return_1y',
    'Fund Name': 'fund_name',
    'Category': 'category',
    'Type': 'type',
    'Remarks': 'remarks'
}

# --- Formatting Functions (F-3.7) ---

# Set locale for Indian Rupees formatting
try:
    locale.setlocale(locale.LC_MONETARY, 'en_IN')
except:
    pass # Fallback

def format_percentage(value):
    return f"{value:.2f}%"

def format_crores(value):
    # Ensure float conversion before formatting for robustness
    return f"₹{locale.format_string('%d', float(value), grouping=True)} Cr."

def format_currency(value):
    return f"₹{locale.format_string('%d', float(value), grouping=True)}"

# --- Core Functions ---

@st.cache_data(show_spinner="Loading and validating fund data...")
def load_fund_data():
    """Loads and validates the fund data (3.1, N-1.4)."""
    try:
        df = pd.read_csv(CSV_FILE)
        df.rename(columns=COLUMN_MAP, inplace=True)
        required_internal_cols = list(COLUMN_MAP.values())
        if not all(col in df.columns for col in required_internal_cols):
            st.error(f"E006: CSV structure validation failed. Required columns (or their mappings) are missing.")
            st.stop()
        
        # Apply stripping logic from original load_fund_data in roboadvisor.py for robustness
        df['risk_profile'] = df['risk_profile'].astype(str).str.strip()
        df['duration'] = df['duration'].astype(str).str.strip()
        df['type'] = df['type'].astype(str).str.strip() # Needed for new logic
        df['category'] = df['category'].astype(str).str.strip() # Needed for new logic

        # Ensure min_investment is numeric
        df['min_investment'] = pd.to_numeric(df['min_investment'], errors='coerce').fillna(0)

        return df
    except FileNotFoundError:
        st.error(f"Error: Required data file '{CSV_FILE}' not found.")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred while loading data: {e}")
        st.stop()

def calculate_risk_score(answers):
    """Calculates total risk score (F-1.4) and categorizes it (F-1.5)."""
    total_score = sum(answers.values()) 
    
    category = None
    description = "Category not defined by score."
    for profile in RISK_CATEGORIES:
        low, high = profile['range']
        if low <= total_score <= high:
            category = profile['name']
            description = profile['description']
            break
            
    return total_score, category, description

def filter_and_sort_recommendations(df, risk_category, investment_amount, duration):
    """
    Filters and sorts the fund database using the improved logic:
    1. Risk Recursion
    2. Investment Amount
    3. Time-Horizon Exclusion
    """
    
    # 1. Map the user-friendly duration string to the internal CSV string.
    internal_duration = DURATION_MAP.get(duration, '')

    # 2. IMPLEMENT RISK RECURSION (IMPLICIT RANKING)
    # Get the list of allowed risk profiles (e.g., Medium includes Moderate, Low)
    allowed_risk_profiles = RISK_HIERARCHY.get(risk_category, [risk_category])
    
    # Filter A: Risk Profile Inclusion
    df_step1 = df[
        df['risk_profile'].isin(allowed_risk_profiles)
    ].copy()
    
    # Filter B: Investment Amount
    df_step2 = df_step1[
        df_step1['min_investment'] <= investment_amount
    ].copy()
    
    # 3. TIME-HORIZON EXCLUSION (Based on Pseudocode)
    
    # Get the allowed Type/Category based on the internal_duration
    allowed_rules = ALLOWED_FUND_TYPES.get(internal_duration)

    if not allowed_rules:
        # If duration is not recognized, return what was matched so far (df_step2)
        return df_step2

    # Filter C: Type and Category Constraints
    
    # Initial filter based on general fund Type (e.g., Debt vs Hybrid vs Equity)
    type_filter = df_step2['type'].isin(allowed_rules['Type'])
    df_step3 = df_step2[type_filter].copy()

    # Additional filter for short durations: apply Category constraint
    if internal_duration == "< 6 months":
        # For < 6 months, must ONLY allow Liquid, Ultra Short, or Short Duration Debt funds
        category_filter = df_step3['category'].isin(allowed_rules['Category'])
        df_step3 = df_step3[category_filter].copy()
    
    # Note: For '6 months to 1 year' and '> 1 year', the type_filter is sufficient per the pseudocode.

    # F-3.2: Sort the final filtered list
    sorted_df = df_step3.sort_values(
        by=['rating', 'return_5y', 'return_3y', 'expense_ratio'],
        ascending=[False, False, False, True] # Rating/Returns Highest first, Expense Ratio Lowest first
    )
    
    return sorted_df

def format_recommendation_table(df_sorted, limit=None):
    """Applies required formatting (F-3.7) and selects columns (F-3.6) for display."""
    display_df = df_sorted.head(limit if limit is not None else len(df_sorted)).reset_index(drop=True)
    display_df['Rank'] = display_df.index + 1
    
    # Apply formatting
    # Added float conversion for robustness in formatting functions
    display_df['aum_cr'] = display_df['aum_cr'].apply(format_crores)
    display_df['return_1y'] = display_df['return_1y'].fillna(0).apply(format_percentage)
    display_df['return_3y'] = display_df['return_3y'].fillna(0).apply(format_percentage)
    display_df['return_5y'] = display_df['return_5y'].fillna(0).apply(format_percentage)
    display_df['expense_ratio'] = display_df['expense_ratio'].apply(format_percentage)
    display_df['min_investment'] = display_df['min_investment'].apply(format_currency)
    
    # F-3.6: Select and Reorder Key Columns for Display
    display_cols = ['Rank', 'fund_name', 'category', 'type', 'aum_cr', 'return_1y', 'return_3y', 
                    'return_5y', 'expense_ratio', 'min_investment', 'rating', 'remarks']
    
    display_names = {
        'fund_name': 'Fund Name', 'category': 'Category', 'type': 'Type', 'aum_cr': 'AUM (in Cr.)', 
        'return_1y': '1Y Return', 'return_3y': '3Y Return', 'return_5y': '5Y Return', 
        'expense_ratio': 'Expense Ratio', 'min_investment': 'Min Investment', 'rating': 'Rating', 
        'remarks': 'Remarks'
    }
    
    return display_df[display_cols].rename(columns=display_names)


# --- Application Flow Logic (Omitted for brevity, assumed correct) ---

def init_session_state():
    # Initializes session state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'home'
        st.session_state.risk_answers = {}
        st.session_state.risk_category = None
        st.session_state.risk_score = 0
        st.session_state.risk_description = ""
        st.session_state.investment_amount = None
        st.session_state.duration = None
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT

def render_home_page():
    st.title("Mutual Fund Robo-Advisor")
    st.markdown("### MVP Phase 1: Risk Assessment and Recommendation Engine")
    st.warning("**Disclaimer (N-1.3):** Past performance does not guarantee future results. This tool does not execute financial transactions.")
    if st.button("Start Risk Assessment", use_container_width=True):
        st.session_state.current_step = 'risk_assessment'
        st.rerun()

def render_risk_assessment():
    st.title("Risk Assessment Questionnaire")
    st.subheader("Step 1 of 3: Determine Your Risk Profile")
    
    with st.form("risk_form"):
        st.markdown(f"**Please answer all {len(RISK_QUESTIONNAIRE)} questions:**")
        
        answers_scores = {}
        for q_id, q_data in RISK_QUESTIONNAIRE.items():
            option_texts = list(q_data['options'].keys())
            selected_option = st.radio(
                f"**Q{q_id}.** {q_data['question']}",
                options=option_texts,
                index=0, 
                key=f"q_{q_id}"
            )
            answers_scores[q_id] = q_data['options'][selected_option]

        submitted = st.form_submit_button("Calculate Risk Profile")
        
        if submitted:
            if len(answers_scores) != 13: 
                st.error("F-1.3: Please ensure all 13 questions are answered.")
                return 

            total_score, category, description = calculate_risk_score(answers_scores)
            
            st.session_state.risk_score = total_score
            st.session_state.risk_category = category
            st.session_state.risk_description = description
            st.session_state.risk_answers = answers_scores
            
            st.success(f"✅ Your Risk Score is **{total_score}** (Range 13-45). Your Risk Category is **{category}** ({description}).")
            
            st.session_state.current_step = 'preference_input'
            st.rerun()

def render_preference_input():
    st.title("Investment Preferences")
    st.subheader("Step 2 of 3: Input Investment Details")
    
    st.info(f"Your assessed Risk Category: **{st.session_state.risk_category}**")
    
    with st.form("preference_form"):
        default_amount = st.session_state.investment_amount if st.session_state.investment_amount else float(MIN_INVESTMENT_AMOUNT)
        investment_amount = st.number_input(
            "Investment Amount (₹):", 
            min_value=0.0, 
            value=default_amount, 
            step=500.0,
            format="%.0f",
            key="amount_input"
        )
        
        default_duration_index = DURATION_OPTIONS.index(st.session_state.duration) if st.session_state.duration in DURATION_OPTIONS else 2
        duration = st.selectbox(
            "Investment Duration:", 
            options=DURATION_OPTIONS, 
            index=default_duration_index, 
            key="duration_select"
        )
        
        submitted = st.form_submit_button("Generate Recommendations (Step 3)", use_container_width=True)
        
        if submitted:
            if not isinstance(investment_amount, (int, float)) or investment_amount <= 0:
                st.error("E003: Investment Amount must be a positive numeric value.")
                return
            if investment_amount < MIN_INVESTMENT_AMOUNT:
                st.error(f"E004: Investment Amount must be a minimum of ₹{MIN_INVESTMENT_AMOUNT}.")
                return
                
            st.session_state.investment_amount = investment_amount
            st.session_state.duration = duration
            st.session_state.current_step = 'recommendations'
            st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
            st.rerun()

def render_recommendations_display():
    st.title("Fund Recommendations")
    st.subheader("Step 3 of 3: Your Customised Fund List")
    
    st.markdown(f"**Filtering by:** Risk Profile: **{st.session_state.risk_category}**, Duration: **{st.session_state.duration}**, Min. Investment: **{format_currency(st.session_state.investment_amount)}**")
    
    fund_df = load_fund_data()
    
    # F-3.1, F-3.2: Filter and Sort
    recommended_funds = filter_and_sort_recommendations(
        fund_df, 
        st.session_state.risk_category, 
        st.session_state.investment_amount, 
        st.session_state.duration
    )
    
    total_matches = len(recommended_funds)
    
    if total_matches == 0:
        st.warning("E005: No funds match your criteria. Try a different investment amount or duration.")
        if st.button("Modify Preferences", use_container_width=True):
            st.session_state.current_step = 'preference_input'
            st.rerun()
        return
        
    final_display_df = format_recommendation_table(recommended_funds, st.session_state.display_limit)

    st.dataframe(final_display_df, use_container_width=True, hide_index=True)

    max_total_display = min(10, total_matches)
    
    if st.session_state.display_limit < max_total_display:
        if st.button(f"Show More ({st.session_state.display_limit} / {total_matches} funds shown)", use_container_width=True):
            st.session_state.display_limit = max_total_display
            st.rerun()
    elif total_matches > DEFAULT_DISPLAY_COUNT:
        st.info(f"Showing all {total_matches} matching funds.")

    if st.button("Modify Investment Preferences", help="Go back to change amount or duration without re-taking the questionnaire."):
        st.session_state.current_step = 'preference_input'
        st.session_state.display_limit = DEFAULT_DISPLAY_COUNT
        st.rerun()


# --- Main App Execution ---

if __name__ == '__main__':
    load_fund_data()
    init_session_state()
    
    if st.session_state.current_step == 'home':
        render_home_page()
    elif st.session_state.current_step == 'risk_assessment':
        render_risk_assessment()
    elif st.session_state.current_step == 'preference_input':
        render_preference_input()
    elif st.session_state.current_step == 'recommendations':
        render_recommendations_display()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Development Debug Info")
    st.sidebar.markdown(f"**Current Step:** `{st.session_state.current_step}`")
    st.sidebar.markdown(f"**Risk Score:** {st.session_state.risk_score}")
    st.sidebar.markdown(f"**Category:** {st.session_state.risk_category}")
    st.sidebar.markdown(f"**Amount:** {st.session_state.investment_amount}")
    st.sidebar.markdown("Scope: Streamlit, Single User. No persistence.")