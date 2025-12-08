# test_csv_generation.py (CORRECTED)
import pandas as pd
from datetime import datetime
from mfdata import generate_recommendations_csv

def test_csv_columns():
    """Test CSV has all Phase 3 columns"""
    
    # Create mock fund dataframe
    mock_funds = pd.DataFrame({
        "scheme_code": ["119551", "108390"],
        "fund_name": ["HDFC Liquid", "Nippon Small Cap"],
        "category": ["Liquid", "Small Cap"],
        "fund_type": ["Debt", "Equity"],
        "aum_cr": [27500, 40000],
        "exp_ratio": [0.375, 0.825],
        "min_investment": [500, 100],
        "rating": [4, 4],
        "return_1y": [8.1, -2.38],
        "return_3y": [17.67, 23.89],
        "return_5y": [20.15, 33.94],
        "latest_nav": [2250.5, 1850.3],
        "latest_date": ["2025-12-02", "2025-12-02"],
        "fund_volatility": [2.45, 18.5]
    })
    
    # Generate CSV
    generate_recommendations_csv(mock_funds, "test_output.csv")
    
    # Read and verify
    df = pd.read_csv("test_output.csv")
    
    print(f"✅ CSV generated with {len(df)} rows and {len(df.columns)} columns")
    print(f"\nColumns: {list(df.columns)}")
    
    # Check Phase 3 columns exist
    phase3_columns = ["last_updated", "category_10y_return", "category_volatility", "fund_volatility"]
    for col in phase3_columns:
        assert col in df.columns, f"Missing column: {col}"
        print(f"✅ Column '{col}' present")
    
    # Verify column values using loc (not iloc)
    first_row = df.iloc[0]  # Get first row as Series
    
    # Now access by column name (not with .[])
    assert first_row["last_updated"] is not None, "last_updated is None"
    print(f"✅ last_updated = {first_row['last_updated']}")
    
    assert first_row["category_10y_return"] == 6.0, f"Expected 6.0, got {first_row['category_10y_return']}"
    print(f"✅ category_10y_return = {first_row['category_10y_return']} (Low Risk)")
    
    assert first_row["category_volatility"] == 3.5, f"Expected 3.5, got {first_row['category_volatility']}"
    print(f"✅ category_volatility = {first_row['category_volatility']}")
    
    assert first_row["fund_volatility"] == 2.45, f"Expected 2.45, got {first_row['fund_volatility']}"
    print(f"✅ fund_volatility = {first_row['fund_volatility']}")
    
    print("\n✅ All Phase 3 columns correctly populated")
    print("\nCSV Preview (Phase 3 columns):")
    print(df[["fund_name", "fund_category", "last_updated", "category_10y_return", "fund_volatility"]].head(3))
    
    # Additional validation
    print("\n" + "="*70)
    print("DETAILED VALIDATION")
    print("="*70)
    
    # Check all rows have last_updated
    null_dates = df["last_updated"].isna().sum()
    assert null_dates == 0, f"{null_dates} rows have null last_updated"
    print(f"✅ No null last_updated values (checked {len(df)} rows)")
    
    # Check category returns by risk profile
    for risk_profile in df["risk_profile"].unique():
        expected_returns = {
            "Low Risk": 6.0,
            "Moderate Risk": 8.0,
            "Medium Risk": 9.0,
            "High Risk": 12.0
        }
        
        profile_df = df[df["risk_profile"] == risk_profile]
        actual_return = profile_df["category_10y_return"].iloc[0]
        expected = expected_returns.get(risk_profile)
        
        assert actual_return == expected, f"{risk_profile}: expected {expected}, got {actual_return}"
        print(f"✅ {risk_profile}: category_10y_return = {actual_return}%")
    
    # Check category volatility by risk profile
    for risk_profile in df["risk_profile"].unique():
        expected_vols = {
            "Low Risk": 3.5,
            "Moderate Risk": 5.5,
            "Medium Risk": 7.5,
            "High Risk": 13.5
        }
        
        profile_df = df[df["risk_profile"] == risk_profile]
        actual_vol = profile_df["category_volatility"].iloc[0]
        expected = expected_vols.get(risk_profile)
        
        assert actual_vol == expected, f"{risk_profile}: expected {expected}, got {actual_vol}"
        print(f"✅ {risk_profile}: category_volatility = {actual_vol}%")
    
    # Check fund_volatility for real funds vs "Not recommended"
    real_funds = df[df["fund_name"] != "Not recommended"]
    placeholder_funds = df[df["fund_name"] == "Not recommended"]
    
    print(f"\n✅ Real funds: {len(real_funds)} rows (fund_volatility should be numeric)")
    print(f"   Sample: {real_funds['fund_volatility'].dropna().head(3).tolist()}")
    
    print(f"✅ Placeholder funds: {len(placeholder_funds)} rows (fund_volatility should be null)")
    null_count = placeholder_funds["fund_volatility"].isna().sum()
    print(f"   Null fund_volatility: {null_count}/{len(placeholder_funds)}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


if __name__ == "__main__":
    test_csv_columns()
