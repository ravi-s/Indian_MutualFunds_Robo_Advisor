
"""
Automated Robo-Advisor Fund Data Refresh Script (Phase 3 Enhanced)

Runs monthly to generate updated fund recommendations with:
- Goal Path support (10-year category returns, volatility)
- Data freshness tracking
- Fund-specific volatility (optional)

Data Source: MFAPI.in + pre-defined metadata
Output: funds.csv with Phase 3 columns

Version: 0.3.1
"""

import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import logging
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robo_advisor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===================================================================
# CONFIGURATION
# ===================================================================
MFAPI_BASE_URL = "https://api.mfapi.in"
API_TIMEOUT = 15
RATE_LIMIT_DELAY = 0.5
OUTPUT_DIR = "."
METADATA_FILE = "fund_metadata.csv"

# ===================================================================
# PHASE 3 ENHANCEMENTS: Return Assumptions & Volatility (From SRS)
# ===================================================================
# Based on 10-year rolling averages for Indian mutual fund categories (post-2015)
CATEGORY_RETURNS = {
    "Low Risk": {
        "conservative": 5.4,      # 10yr - 10%
        "expected": 6.0,           # 10yr avg (median)
        "best_case": 6.6           # 10yr + 10%
    },
    "Moderate Risk": {
        "conservative": 7.2,       # 10yr - 10%
        "expected": 8.0,           # 10yr avg (median)
        "best_case": 8.8           # 10yr + 10%
    },
    "Medium Risk": {
        "conservative": 8.1,       # 10yr - 10%
        "expected": 9.0,           # 10yr avg (median)
        "best_case": 9.9           # 10yr + 10%
    },
    "High Risk": {
        "conservative": 10.8,      # 10yr - 10%
        "expected": 12.0,          # 10yr avg (median)
        "best_case": 13.2          # 10yr + 10%
    }
}

CATEGORY_VOLATILITY = {
    "Low Risk": 3.5,               # % (3-4% range, using 3.5)
    "Moderate Risk": 5.5,          # % (5-6% range, using 5.5)
    "Medium Risk": 7.5,            # % (7-8% range, using 7.5)
    "High Risk": 13.5              # % (12-15% range, using 13.5)
}

# ===================================================================
# SUITABILITY MATRIX (Phase 2/3 Compatible)
# ===================================================================
SUITABILITY_MATRIX = {
    ("Low Risk", "< 6 months"): ["Liquid"],
    ("Low Risk", "6 months to 1 year"): ["Short Duration", "Ultra Short Duration", "Banking & PSU"],
    ("Low Risk", "> 1 year"): ["Gilt", "Short Duration", "Banking & PSU"],
    ("Moderate Risk", "< 6 months"): ["Ultra Short Duration", "Liquid"],
    ("Moderate Risk", "6 months to 1 year"): ["Conservative Hybrid", "Short Duration", "Low Duration"],
    ("Moderate Risk", "> 1 year"): ["Aggressive Hybrid", "Balanced Advantage", "Large Cap"],
    ("Medium Risk", "< 6 months"): ["Low Duration", "Ultra Short Duration"],
    ("Medium Risk", "6 months to 1 year"): ["Balanced Advantage", "Conservative Hybrid", "Dynamic Asset Allocation"],
    ("Medium Risk", "> 1 year"): ["Large Cap", "Flexi Cap", "Mid Cap"],
    ("High Risk", "< 6 months"): ["Not recommended"],
    ("High Risk", "6 months to 1 year"): ["Balanced Advantage", "Dynamic Asset Allocation"],
    ("High Risk", "> 1 year"): ["Small Cap", "Mid Cap", "Flexi Cap"]
}

# Ranking weights for composite scoring
RANKING_WEIGHTS = {
    "return_1y": 0.2,
    "return_3y": 0.5,
    "return_5y": 0.3
}

# ===================================================================
# PHASE 3: Helper Functions for Return Assumptions
# ===================================================================

def map_fund_category_to_risk_profile(fund_category):
    """
    Map fund category to risk profile for return assumption lookup.
    
    Example mappings:
    - "Liquid" → "Low Risk"
    - "Gilt" → "Low Risk"
    - "Large Cap" → "Moderate Risk" / "Medium Risk"
    - "Small Cap" → "High Risk"
    - "Hybrid" → varies by subtype
    
    This is a simplified mapping; can be enhanced based on AMFI classification.
    """
    category_lower = str(fund_category).lower()
    
    # Low Risk categories
    if any(x in category_lower for x in ["liquid", "ultra short", "short duration", "gilt", "banking", "psu"]):
        return "Low Risk"
    
    # Moderate Risk categories
    if any(x in category_lower for x in ["conservative hybrid", "low duration"]):
        return "Moderate Risk"
    
    # Medium Risk categories
    if any(x in category_lower for x in ["balanced advantage", "dynamic asset", "large cap"]):
        return "Medium Risk"
    
    # High Risk categories
    if any(x in category_lower for x in ["small cap", "mid cap", "flexi cap", "aggressive hybrid"]):
        return "High Risk"
    
    # Default fallback
    return "Medium Risk"


def get_category_return_assumptions(fund_category):
    """
    Retrieve 10-year return assumptions for a fund category.
    
    Returns dict with: conservative, expected, best_case percentages.
    """
    risk_profile = map_fund_category_to_risk_profile(fund_category)
    return CATEGORY_RETURNS.get(risk_profile, CATEGORY_RETURNS["Medium Risk"])


def get_category_volatility(fund_category):
    """
    Retrieve historical volatility for a fund category.
    
    Returns volatility % (standard deviation).
    """
    risk_profile = map_fund_category_to_risk_profile(fund_category)
    return CATEGORY_VOLATILITY.get(risk_profile, CATEGORY_VOLATILITY["Medium Risk"])


# ===================================================================
# CORE DATA FETCH FUNCTIONS
# ===================================================================

def fetch_nav_history(scheme_code):
    """Fetch NAV history from MFAPI"""
    try:
        url = f"{MFAPI_BASE_URL}/mf/{scheme_code}"
        logger.info(f"Fetching NAV for scheme {scheme_code}...")
        response = requests.get(url, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "SUCCESS":
            logger.warning(f"Non-success status for {scheme_code}")
            return None, None
        
        nav_data = pd.DataFrame(data["data"])
        nav_data["date"] = pd.to_datetime(nav_data["date"], format="%d-%m-%Y")
        nav_data["nav"] = pd.to_numeric(nav_data["nav"])
        nav_data = nav_data.sort_values("date")
        
        return nav_data, data.get("meta", {})
    
    except Exception as e:
        logger.error(f"Error fetching {scheme_code}: {e}")
        return None, None


def calculate_cagr(nav_data, years):
    """Calculate CAGR for given period"""
    if nav_data is None or len(nav_data) < 2:
        return None
    
    try:
        end_date = nav_data.iloc[-1]["date"]
        start_date = end_date - relativedelta(years=years)
        start_nav_data = nav_data[nav_data["date"] <= start_date]
        
        if start_nav_data.empty:
            return None
        
        start_nav = start_nav_data.iloc[-1]["nav"]
        end_nav = nav_data.iloc[-1]["nav"]
        
        if start_nav <= 0:
            return None
        
        cagr = ((end_nav / start_nav) ** (1 / years) - 1) * 100
        return round(cagr, 2)
    
    except Exception as e:
        logger.error(f"Error calculating CAGR: {e}")
        return None


def calculate_volatility(nav_data):
    """
    Calculate historical volatility (annualized standard deviation of daily returns).
    
    Returns: volatility as % (annualized)
    """
    if nav_data is None or len(nav_data) < 2:
        return None
    
    try:
        # Calculate daily returns
        nav_data = nav_data.sort_values("date").reset_index(drop=True)
        daily_returns = nav_data["nav"].pct_change() * 100  # Convert to %
        
        # Calculate standard deviation of daily returns
        daily_std = daily_returns.std()
        
        if pd.isna(daily_std) or daily_std == 0:
            return None
        
        # Annualize: multiply by sqrt(252) for trading days
        annualized_vol = daily_std * (252 ** 0.5)
        
        return round(annualized_vol, 2)
    
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        return None


def fetch_all_fund_data(metadata_df):
    """
    Fetch performance data for all funds.
    
    Enhanced for Phase 3: Includes fund_volatility calculation.
    """
    all_fund_data = []
    
    for idx, row in metadata_df.iterrows():
        scheme_code = str(row['scheme_code'])
        logger.info(f"Processing {row['fund_name']}...")
        
        nav_data, meta = fetch_nav_history(scheme_code)
        
        if nav_data is not None:
            fund_category = row.get('category', 'Medium Risk')
            
            fund_data = {
                "scheme_code": scheme_code,
                "fund_name": row['fund_name'],
                "fund_house": row['fund_house'],
                "category": fund_category,
                "fund_type": row['fund_type'],
                "aum_cr": row['aum_cr'],
                "exp_ratio": row['exp_ratio'],
                "min_investment": row['min_investment'],
                "rating": row['rating'],
                "exit_load": row.get('exit_load', 0),
                "return_1y": calculate_cagr(nav_data, 1),
                "return_3y": calculate_cagr(nav_data, 3),
                "return_5y": calculate_cagr(nav_data, 5),
                "latest_nav": round(nav_data.iloc[-1]["nav"], 2),
                "latest_date": nav_data.iloc[-1]["date"].strftime("%Y-%m-%d"),
                # ========== PHASE 3 ADDITIONS ==========
                "fund_volatility": calculate_volatility(nav_data),  # Fund-specific volatility
            }
            
            all_fund_data.append(fund_data)
        
        time.sleep(RATE_LIMIT_DELAY)
    
    return pd.DataFrame(all_fund_data)


def rank_and_select_funds(df, risk_profile, duration, top_n=10):
    """Rank and select top N funds for given risk/duration"""
    allowed_categories = SUITABILITY_MATRIX.get((risk_profile, duration), [])
    
    if "Not recommended" in allowed_categories:
        return pd.DataFrame()
    
    filtered = df[df["category"].isin(allowed_categories)].copy()
    
    if filtered.empty:
        return pd.DataFrame()
    
    # Calculate composite score based on returns
    filtered["score"] = (
        filtered["return_1y"].fillna(0) * RANKING_WEIGHTS["return_1y"] +
        filtered["return_3y"].fillna(0) * RANKING_WEIGHTS["return_3y"] +
        filtered["return_5y"].fillna(0) * RANKING_WEIGHTS["return_5y"]
    )
    
    top_funds = filtered.nlargest(top_n, "score")
    top_funds["rank"] = range(1, len(top_funds) + 1)
    
    return top_funds


def generate_recommendations_csv(df, output_file):
    """
    Generate final recommendations CSV with Phase 3 enhancements.
    
    Includes: risk_profile, duration, rank, data freshness, category returns, volatility
    """
    risk_profiles = ["Low Risk", "Moderate Risk", "Medium Risk", "High Risk"]
    durations = ["< 6 months", "6 months to 1 year", "> 1 year"]
    
    all_recommendations = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for risk in risk_profiles:
        for duration in durations:
            logger.info(f"Generating: {risk} / {duration}")
            top_funds = rank_and_select_funds(df, risk, duration, top_n=10)
            
            if top_funds.empty:
                # Add placeholder for "not recommended"
                for i in range(1, 4):
                    all_recommendations.append({
                        "risk_profile": risk,
                        "duration": duration,
                        "rank": i,
                        "fund_name": "Not recommended",
                        "fund_category": "N/A",
                        "fund_type": "N/A",
                        "aum_cr": "N/A",
                        "exp_ratio": "N/A",
                        "return_1y": "N/A",
                        "return_3y": "N/A",
                        "return_5y": "N/A",
                        "min_investment": "N/A",
                        "rating": "N/A",
                        "remarks": f"Equity/high-risk funds not suitable for {duration}",
                        # ========== PHASE 3 COLUMNS ==========
                        "last_updated": today,
                        "category_10y_return": CATEGORY_RETURNS[risk]["expected"],
                        "category_volatility": CATEGORY_VOLATILITY[risk],
                        "fund_volatility": "N/A"
                    })
            else:
                for _, fund in top_funds.iterrows():
                    all_recommendations.append({
                        "risk_profile": risk,
                        "duration": duration,
                        "rank": int(fund["rank"]),
                        "fund_name": fund["fund_name"],
                        "fund_category": fund["category"],
                        "fund_type": fund["fund_type"],
                        "aum_cr": fund["aum_cr"],
                        "exp_ratio": fund["exp_ratio"],
                        "return_1y": fund["return_1y"],
                        "return_3y": fund["return_3y"],
                        "return_5y": fund["return_5y"],
                        "min_investment": fund["min_investment"],
                        "rating": fund["rating"],
                        "remarks": f"Data as of {fund['latest_date']}",
                        # ========== PHASE 3 COLUMNS ==========
                        "last_updated": today,
                        "category_10y_return": CATEGORY_RETURNS[risk]["expected"],
                        "category_volatility": CATEGORY_VOLATILITY[risk],
                        "fund_volatility": fund.get("fund_volatility")  # Fund-specific volatility
                    })
    
    recommendations_df = pd.DataFrame(all_recommendations)
    
    # Ensure column order: Risk/Duration/Rank + Base Columns + Phase 3 Columns
    column_order = [
        "risk_profile", "duration", "rank",
        "fund_name", "fund_category", "fund_type",
        "aum_cr", "exp_ratio",
        "return_1y", "return_3y", "return_5y",
        "min_investment", "rating", "remarks",
        # Phase 3 columns at the end
        "last_updated",
        "category_10y_return",
        "category_volatility",
        "fund_volatility"
    ]
    
    recommendations_df = recommendations_df[column_order]
    recommendations_df.to_csv(output_file, index=False)
    logger.info(f"✅ CSV generated: {output_file}")
    
    return output_file


def send_email_notification(csv_file, recipient_email):
    """Send email with CSV attachment"""
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_APP_PASSWORD")
    
    if not sender_email or not sender_password:
        logger.warning("Email credentials not set. Skipping email.")
        return
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Robo-Advisor Fund Recommendations (Phase 3) - {datetime.now().strftime('%B %Y')}"
    
    body = f"""
Hi,

Your monthly mutual fund recommendations (Phase 3) are ready.

Report Date: {datetime.now().strftime('%B %d, %Y')}
Data Source: MFAPI.in (verified NAV data)

This CSV now includes:
✓ Risk profiles and investment durations
✓ 10-year category return assumptions (for Goal Path calculations)
✓ Category volatility metrics
✓ Fund-specific volatility
✓ Data freshness tracking

Please find the attached CSV file.

Best regards,
Robo-Advisor Automation (Phase 3)
"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach CSV
    try:
        with open(csv_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(csv_file)}')
            msg.attach(part)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent to {recipient_email}")
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("Starting Robo-Advisor Data Refresh (Phase 3)")
    logger.info("=" * 60)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load metadata
    if not os.path.exists(METADATA_FILE):
        logger.error(f"Metadata file not found: {METADATA_FILE}")
        sys.exit(1)
    
    metadata_df = pd.read_csv(METADATA_FILE)
    logger.info(f"Loaded {len(metadata_df)} funds from metadata")
    
    # Fetch fresh NAV data
    logger.info("Fetching fresh NAV data from MFAPI...")
    fund_data_df = fetch_all_fund_data(metadata_df)
    logger.info(f"Successfully fetched data for {len(fund_data_df)} funds")
    
    # Generate recommendations with Phase 3 columns
    output_file = os.path.join(
        OUTPUT_DIR,
        f"funds_{datetime.now().strftime('%Y_%m_%d')}.csv"
    )
    generate_recommendations_csv(fund_data_df, output_file)
    
    # Also create a "funds.csv" symlink/copy for roboadvisor.py to use
    import shutil
    main_csv = os.path.join(OUTPUT_DIR, "funds.csv")
    shutil.copy(output_file, main_csv)
    logger.info(f"✅ Main CSV updated: {main_csv}")
    
    # Send email notification
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    if recipient_email:
        send_email_notification(output_file, recipient_email)
    
    logger.info("=" * 60)
    logger.info("✅ Phase 3 Data refresh completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
