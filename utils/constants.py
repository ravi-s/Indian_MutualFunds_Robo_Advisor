# utils/constants.py
"""
Global constants for Robo-Advisor (Phase 2 + Phase 3)
"""
DEFAULT_DISPLAY_COUNT = 3

# ===================================================================
# RISK ASSESSMENT CONSTANTS (Phase 2)
# ===================================================================

RISK_QUESTIONNAIRE = {
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

RISK_CATEGORIES = [
    {"range": (13, 18), "name": "Low Risk", "description": "Low tolerance for risk (13–18 range)"},
    {"range": (19, 22), "name": "Moderate Risk", "description": "Below-average tolerance for risk (19–22 range)"},
    {"range": (23, 28), "name": "Medium Risk", "description": "Average/moderate tolerance for risk (23–28 range)"},
    {"range": (29, 45), "name": "High Risk", "description": "High tolerance for risk (29–45 range)"},
]

RISK_HIERARCHY = {
    "High Risk": ["High Risk", "Medium Risk", "Moderate Risk", "Low Risk"],
    "Medium Risk": ["Medium Risk", "Moderate Risk", "Low Risk"],
    "Moderate Risk": ["Moderate Risk", "Low Risk"],
    "Low Risk": ["Low Risk"],
}
# ===================================================================
# PHASE 3: Return Assumptions & Goal Path Constants
# ===================================================================

# Based on 10-year rolling averages for Indian mutual fund categories (post-2015)
# Source: mfdata.py + historical CAGR analysis
CATEGORY_RETURNS = {
    "Low Risk": {
        "conservative": 5.4,   # 10yr avg - 10%
        "expected": 6.0,       # 10yr avg (median)
        "best_case": 6.6       # 10yr avg + 10%
    },
    "Moderate Risk": {
        "conservative": 7.2,   # 10yr avg - 10%
        "expected": 8.0,       # 10yr avg (median)
        "best_case": 8.8       # 10yr avg + 10%
    },
    "Medium Risk": {
        "conservative": 8.1,   # 10yr avg - 10%
        "expected": 9.0,       # 10yr avg (median)
        "best_case": 9.9       # 10yr avg + 10%
    },
    "High Risk": {
        "conservative": 10.8,  # 10yr avg - 10%
        "expected": 12.0,      # 10yr avg (median)
        "best_case": 13.2      # 10yr avg + 10%
    }
}

# Historical volatility by risk category (%)
CATEGORY_VOLATILITY = {
    "Low Risk": 3.5,           # 3-4% range, using 3.5
    "Moderate Risk": 5.5,      # 5-6% range, using 5.5
    "Medium Risk": 7.5,        # 7-8% range, using 7.5
    "High Risk": 13.5          # 12-15% range, using 13.5
}
# ===================================================================
# Phase 3a: Recent 1-Year Market Returns (for Mean Reversion)
# As of: December 2025
# ===================================================================


# Low Risk (6.2%): Government/high-grade debt in India has delivered mid-single digits over the past year as rates stabilized. This is realistic for a low-duration bond index.​

# Moderate Risk (10.5%): A 50:50 balanced hybrid sitting between debt (6%) and equity (14-18%) makes sense; captures both drag and upside.​

# Medium Risk (14.8%): NIFTY 50 has had a strong year (2024–2025 was a bull year in India). This aligns with recent market data.​

# High Risk (18.2%): Midcap/smallcap significantly outpaced large-cap; 18%+ is realistic for more aggressive equity indices.​

RECENT_1YR_MARKET_RETURNS = {
    "Low Risk": 6.2,        # NIFTY Low Duration Bond (debt-heavy, stable)
    "Moderate Risk": 10.5,  # NIFTY Hybrid 50:50 (balanced)
    "Medium Risk": 14.8,    # NIFTY 50 (strong equity year)
    "High Risk": 18.2,      # NIFTY Midcap 100 (aggressive equity outperformed)
}

# Phase 3a: Baseline calibration metadata
BASELINE_AS_OF = "2025-Q4"  # Quarterly review cadence

# Confidence score benchmarks (based on volatility)
VOLATILITY_BENCHMARKS = {
    "High": 5.0,      # Volatility <= 5% = High confidence
    "Medium": 10.0,   # Volatility <= 10% = Medium confidence
    "Low": float('inf')  # Volatility > 10% = Low confidence
}

DURATION_OPTIONS = [
    "Less than 6 months",
    "6 months to 1 year",
    "More than 1 year",
]

DURATION_MAP = {
    "Less than 6 months": "< 6 months",
    "6 months to 1 year": "6 months to 1 year",
    "More than 1 year": "> 1 year",
}

DURATION_HIERARCHY = {
    "< 6 months": ["< 6 months"],
    "6 months to 1 year": ["6 months to 1 year", "< 6 months"],
    "> 1 year": ["> 1 year", "6 months to 1 year", "< 6 months"],
}

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

# ===================================================================
# PHASE 3: RETURN ASSUMPTIONS & VOLATILITY
# ===================================================================

CATEGORY_RETURNS = {
    "Low Risk": {
        "conservative": 5.4,   # 10yr avg - 10%
        "expected": 6.0,       # 10yr avg (median)
        "best_case": 6.6       # 10yr avg + 10%
    },
    "Moderate Risk": {
        "conservative": 7.2,   # 10yr avg - 10%
        "expected": 8.0,       # 10yr avg (median)
        "best_case": 8.8       # 10yr avg + 10%
    },
    "Medium Risk": {
        "conservative": 8.1,   # 10yr avg - 10%
        "expected": 9.0,       # 10yr avg (median)
        "best_case": 9.9       # 10yr avg + 10%
    },
    "High Risk": {
        "conservative": 10.8,  # 10yr avg - 10%
        "expected": 12.0,      # 10yr avg (median)
        "best_case": 13.2      # 10yr avg + 10%
    }
}

CATEGORY_VOLATILITY = {
    "Low Risk": 3.5,           # 3-4% range, using 3.5
    "Moderate Risk": 5.5,      # 5-6% range, using 5.5
    "Medium Risk": 7.5,        # 7-8% range, using 7.5
    "High Risk": 13.5          # 12-15% range, using 13.5
}

VOLATILITY_BENCHMARKS = {
    "High": 5.0,               # Volatility <= 5% = High confidence
    "Medium": 10.0,            # Volatility <= 10% = Medium confidence
    "Low": float('inf')        # Volatility > 10% = Low confidence
}

# ===================================================================
# CSV & DATA CONSTANTS
# ===================================================================

CSV_FILE = "funds.csv"
MIN_INVESTMENT_AMOUNT = 500
DEFAULT_DISPLAY_COUNT = 3

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
