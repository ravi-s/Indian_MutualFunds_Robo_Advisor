#!/usr/bin/env python3
"""
Metadata Validation Script
Flags outdated, suspicious, or incorrect fund metadata
"""

import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

METADATA_FILE = "fund_metadata.csv"
MFAPI_BASE_URL = "https://api.mfapi.in"
VALIDATION_REPORT = "metadata_validation_report.csv"

# Validation thresholds
THRESHOLDS = {
    "max_expense_ratio": {
        "Debt": 1.0,
        "Hybrid": 1.5,
        "Equity": 1.2
    },
    "min_aum_cr": 50,  # Funds below 50 Cr are illiquid
    "aum_change_alert": 0.3,  # 30% change in AUM is suspicious
    "ter_change_alert": 0.3,  # 0.3% change in TER
    "return_outlier_std": 2.5  # 2.5 standard deviations from category mean
}


def load_metadata():
    """Load metadata CSV"""
    try:
        df = pd.read_csv(METADATA_FILE)
        logger.info(f"✓ Loaded {len(df)} funds from {METADATA_FILE}")
        return df
    except FileNotFoundError:
        logger.error(f"✗ Metadata file not found: {METADATA_FILE}")
        sys.exit(1)


def fetch_latest_nav(scheme_code):
    """Fetch only latest NAV from MFAPI (fast check)"""
    try:
        url = f"{MFAPI_BASE_URL}/mf/{scheme_code}/latest"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "SUCCESS" and data.get("data"):
            nav_info = data["data"][0]
            return {
                "latest_nav": float(nav_info["nav"]),
                "latest_date": pd.to_datetime(nav_info["date"], format="%d-%m-%Y")
            }
    except Exception as e:
        logger.warning(f"Could not fetch NAV for {scheme_code}: {e}")
    
    return None


def validate_scheme_exists(df):
    """Check if scheme codes are valid and active"""
    issues = []
    
    logger.info("\n[1/7] Validating scheme codes...")
    for idx, row in df.iterrows():
        scheme_code = str(row['scheme_code'])
        nav_data = fetch_latest_nav(scheme_code)
        
        if nav_data is None:
            issues.append({
                "scheme_code": scheme_code,
                "fund_name": row['fund_name'],
                "issue_type": "INVALID_SCHEME",
                "severity": "HIGH",
                "message": "Scheme code not found or inactive in MFAPI"
            })
        else:
            # Check data freshness
            days_old = (datetime.now() - nav_data["latest_date"]).days
            if days_old > 7:
                issues.append({
                    "scheme_code": scheme_code,
                    "fund_name": row['fund_name'],
                    "issue_type": "STALE_NAV",
                    "severity": "MEDIUM",
                    "message": f"NAV is {days_old} days old (last update: {nav_data['latest_date'].date()})"
                })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] in ['INVALID_SCHEME', 'STALE_NAV']])} scheme issues")
    return issues


def validate_expense_ratios(df):
    """Check if expense ratios are within reasonable bounds"""
    issues = []
    
    logger.info("\n[2/7] Validating expense ratios...")
    for idx, row in df.iterrows():
        fund_type = row['fund_type']
        exp_ratio = row['exp_ratio']
        
        if pd.isna(exp_ratio) or exp_ratio == 'TBD':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "MISSING_DATA",
                "severity": "MEDIUM",
                "message": "Expense ratio not set"
            })
            continue
        
        max_ter = THRESHOLDS["max_expense_ratio"].get(fund_type, 2.0)
        
        if float(exp_ratio) > max_ter:
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "HIGH_EXPENSE",
                "severity": "MEDIUM",
                "message": f"Expense ratio {exp_ratio}% exceeds typical {fund_type} fund max ({max_ter}%)"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] in ['MISSING_DATA', 'HIGH_EXPENSE']])} expense ratio issues")
    return issues


def validate_aum(df):
    """Check AUM for liquidity concerns"""
    issues = []
    
    logger.info("\n[3/7] Validating AUM...")
    for idx, row in df.iterrows():
        aum = row['aum_cr']
        
        if pd.isna(aum) or aum == 'TBD':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "MISSING_DATA",
                "severity": "MEDIUM",
                "message": "AUM not set"
            })
            continue
        
        if float(aum) < THRESHOLDS["min_aum_cr"]:
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "LOW_AUM",
                "severity": "HIGH",
                "message": f"AUM of ₹{aum} Cr is below minimum threshold (₹{THRESHOLDS['min_aum_cr']} Cr) - liquidity risk"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] == 'LOW_AUM'])} AUM issues")
    return issues


def validate_ratings(df):
    """Check if ratings are set and valid"""
    issues = []
    
    logger.info("\n[4/7] Validating ratings...")
    for idx, row in df.iterrows():
        rating = row['rating']
        
        if pd.isna(rating) or rating == 'TBD':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "MISSING_DATA",
                "severity": "LOW",
                "message": "Rating not set"
            })
        elif rating not in [1, 2, 3, 4, 5, '1', '2', '3', '4', '5']:
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "INVALID_RATING",
                "severity": "LOW",
                "message": f"Invalid rating value: {rating}"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] in ['MISSING_DATA', 'INVALID_RATING']])} rating issues")
    return issues


def validate_min_investment(df):
    """Check minimum investment amounts"""
    issues = []
    
    logger.info("\n[5/7] Validating minimum investment...")
    for idx, row in df.iterrows():
        min_inv = row['min_investment']
        
        if pd.isna(min_inv) or min_inv == 'TBD':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "MISSING_DATA",
                "severity": "LOW",
                "message": "Minimum investment not set"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] == 'MISSING_DATA'])} min investment issues")
    return issues


def validate_category_consistency(df):
    """Check if fund categorization makes sense"""
    issues = []
    
    logger.info("\n[6/7] Validating category consistency...")
    
    # Check fund_type matches category
    for idx, row in df.iterrows():
        category = row['category']
        fund_type = row['fund_type']
        
        debt_categories = ['Liquid', 'Ultra Short Duration', 'Short Duration', 'Low Duration', 'Gilt', 'Banking & PSU']
        hybrid_categories = ['Conservative Hybrid', 'Aggressive Hybrid', 'Balanced Advantage', 'Dynamic Asset Allocation']
        equity_categories = ['Large Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap']
        
        if category in debt_categories and fund_type != 'Debt':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "CATEGORY_MISMATCH",
                "severity": "HIGH",
                "message": f"Category '{category}' should have fund_type 'Debt', not '{fund_type}'"
            })
        elif category in hybrid_categories and fund_type != 'Hybrid':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "CATEGORY_MISMATCH",
                "severity": "HIGH",
                "message": f"Category '{category}' should have fund_type 'Hybrid', not '{fund_type}'"
            })
        elif category in equity_categories and fund_type != 'Equity':
            issues.append({
                "scheme_code": row['scheme_code'],
                "fund_name": row['fund_name'],
                "issue_type": "CATEGORY_MISMATCH",
                "severity": "HIGH",
                "message": f"Category '{category}' should have fund_type 'Equity', not '{fund_type}'"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] == 'CATEGORY_MISMATCH'])} category issues")
    return issues


def validate_duplicate_entries(df):
    """Check for duplicate scheme codes"""
    issues = []
    
    logger.info("\n[7/7] Checking for duplicates...")
    duplicates = df[df.duplicated(subset=['scheme_code'], keep=False)]
    
    if not duplicates.empty:
        for scheme_code in duplicates['scheme_code'].unique():
            dup_funds = duplicates[duplicates['scheme_code'] == scheme_code]
            issues.append({
                "scheme_code": scheme_code,
                "fund_name": ", ".join(dup_funds['fund_name'].tolist()),
                "issue_type": "DUPLICATE",
                "severity": "HIGH",
                "message": f"Duplicate scheme code found {len(dup_funds)} times"
            })
    
    logger.info(f"  Found {len([i for i in issues if i['issue_type'] == 'DUPLICATE'])} duplicates")
    return issues


def generate_report(all_issues):
    """Generate validation report"""
    if not all_issues:
        logger.info("\n" + "="*60)
        logger.info("✅ VALIDATION PASSED: No issues found!")
        logger.info("="*60)
        return
    
    issues_df = pd.DataFrame(all_issues)
    issues_df.to_csv(VALIDATION_REPORT, index=False)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("⚠️  VALIDATION REPORT")
    logger.info("="*60)
    
    severity_counts = issues_df['severity'].value_counts()
    logger.info(f"\nTotal Issues: {len(issues_df)}")
    for severity in ['HIGH', 'MEDIUM', 'LOW']:
        count = severity_counts.get(severity, 0)
        if count > 0:
            logger.info(f"  - {severity}: {count}")
    
    logger.info(f"\nIssue Types:")
    issue_type_counts = issues_df['issue_type'].value_counts()
    for issue_type, count in issue_type_counts.items():
        logger.info(f"  - {issue_type}: {count}")
    
    logger.info(f"\n📄 Detailed report saved to: {VALIDATION_REPORT}")
    logger.info("="*60)
    
    # Show HIGH severity issues
    high_issues = issues_df[issues_df['severity'] == 'HIGH']
    if not high_issues.empty:
        logger.info("\n🚨 HIGH SEVERITY ISSUES (immediate action required):")
        logger.info("-" * 60)
        for _, issue in high_issues.iterrows():
            logger.info(f"  • {issue['fund_name'][:50]}")
            logger.info(f"    {issue['message']}")


def main():
    """Main validation"""
    logger.info("="*60)
    logger.info("METADATA VALIDATION SCRIPT")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    df = load_metadata()
    
    all_issues = []
    all_issues.extend(validate_scheme_exists(df))
    all_issues.extend(validate_expense_ratios(df))
    all_issues.extend(validate_aum(df))
    all_issues.extend(validate_ratings(df))
    all_issues.extend(validate_min_investment(df))
    all_issues.extend(validate_category_consistency(df))
    all_issues.extend(validate_duplicate_entries(df))
    
    generate_report(all_issues)


if __name__ == "__main__":
    main()
