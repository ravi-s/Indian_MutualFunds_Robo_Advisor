# test_constants.py
from mfdata import CATEGORY_RETURNS, CATEGORY_VOLATILITY

def test_category_returns():
    """Verify returns match Phase 3 SRS Section 5"""
    assert CATEGORY_RETURNS["Low Risk"]["expected"] == 6.0
    assert CATEGORY_RETURNS["Moderate Risk"]["expected"] == 8.0
    assert CATEGORY_RETURNS["Medium Risk"]["expected"] == 9.0
    assert CATEGORY_RETURNS["High Risk"]["expected"] == 12.0
    print("✅ CATEGORY_RETURNS correct")

def test_category_volatility():
    """Verify volatility matches Phase 3 SRS Section 5"""
    assert CATEGORY_VOLATILITY["Low Risk"] == 3.5
    assert CATEGORY_VOLATILITY["Moderate Risk"] == 5.5
    assert CATEGORY_VOLATILITY["Medium Risk"] == 7.5
    assert CATEGORY_VOLATILITY["High Risk"] == 13.5
    print("✅ CATEGORY_VOLATILITY correct")

if __name__ == "__main__":
    test_category_returns()
    test_category_volatility()
