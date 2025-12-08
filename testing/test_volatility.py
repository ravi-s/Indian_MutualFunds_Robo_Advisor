# test_volatility.py
import pandas as pd
import numpy as np
from mfdata import calculate_volatility

def test_calculate_volatility():
    """Test volatility calculation"""
    # Create mock NAV data with known volatility
    dates = pd.date_range("2025-01-01", periods=252, freq="D")
    
    # Simulate constant 1% daily volatility
    np.random.seed(42)
    daily_returns = np.random.normal(0, 0.01, 252)  # 1% std dev
    nav_values = (1 + daily_returns).cumprod() * 100
    
    nav_data = pd.DataFrame({
        "date": dates,
        "nav": nav_values
    })
    
    vol = calculate_volatility(nav_data)
    print(f"Calculated volatility: {vol}%")
    
    # Expected: 1% * sqrt(252) ≈ 15.87%
    expected_vol = 0.01 * (252 ** 0.5) * 100
    print(f"Expected volatility: ~{expected_vol:.1f}%")
    
    # Allow 10% margin
    assert vol is not None
    assert expected_vol * 0.9 < vol < expected_vol * 1.1
    print("✅ Volatility calculation correct")

if __name__ == "__main__":
    test_calculate_volatility()
