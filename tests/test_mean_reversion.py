"""
Unit tests for Mean Reversion Logic (Phase 3)
Run with: python tests/test_mean_reversion.py

Imports functions from modules/recommendations.py
Path setup handles both direct execution and pytest invocation.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.recommendations import (
    apply_mean_reversion,
    get_category_return_assumptions,
    get_category_volatility,
    get_confidence_percentage,
    get_confidence_score
)


# ===================================================================
# TEST CASES
# ===================================================================

def test_get_category_return_assumptions():
    """Test return assumption retrieval"""
    
    # Test Medium Risk (most common)
    medium_risk = get_category_return_assumptions("Medium Risk")
    assert medium_risk["conservative"] == 8.1
    assert medium_risk["expected"] == 9.0
    assert medium_risk["best_case"] == 9.9
    
    # Test Low Risk
    low_risk = get_category_return_assumptions("Low Risk")
    assert low_risk["expected"] == 6.0
    
    # Test High Risk
    high_risk = get_category_return_assumptions("High Risk")
    assert high_risk["expected"] == 12.0
    
    # Test unknown category (should fallback to Medium Risk)
    unknown = get_category_return_assumptions("Unknown Risk")
    assert unknown == medium_risk
    
    print("✅ test_get_category_return_assumptions passed")


def test_get_category_volatility():
    """Test volatility retrieval"""
    
    # Test all categories
    assert get_category_volatility("Low Risk") == 3.5
    assert get_category_volatility("Moderate Risk") == 5.5
    assert get_category_volatility("Medium Risk") == 7.5
    assert get_category_volatility("High Risk") == 13.5
    
    # Test unknown category (should fallback to Medium Risk)
    assert get_category_volatility("Unknown Risk") == 7.5
    
    print("✅ test_get_category_volatility passed")


def test_apply_mean_reversion():
    """Test mean reversion logic"""
    
    # Test 1: Recent market is hot (mean reversion applies)
    # 10yr avg = 9%, recent 1yr = 14.5%
    # 14.5 > (9 + 5) = 14? Yes, so adjust to 9 - 1 = 8%
    result = apply_mean_reversion(base_return=9.0, recent_1yr_return=14.5)
    assert result == 8.0, f"Expected 8.0, got {result}"
    
    # Test 2: Recent market is normal (no adjustment)
    # 10yr avg = 9%, recent 1yr = 10%
    # 10 > 14? No, so keep at 9%
    result = apply_mean_reversion(base_return=9.0, recent_1yr_return=10.0)
    assert result == 9.0, f"Expected 9.0, got {result}"
    
    # Test 3: Edge case - exactly at threshold
    # 10yr avg = 9%, recent 1yr = 14%
    # 14 > 14? No, so keep at 9%
    result = apply_mean_reversion(base_return=9.0, recent_1yr_return=14.0)
    assert result == 9.0, f"Expected 9.0, got {result}"
    
    # Test 4: Low risk category
    result = apply_mean_reversion(base_return=6.0, recent_1yr_return=12.0)
    assert result == 5.0, f"Expected 5.0, got {result}"
    
    # Test 5: High risk category
    result = apply_mean_reversion(base_return=12.0, recent_1yr_return=18.0)
    assert result == 11.0, f"Expected 11.0, got {result}"
    
    print("✅ test_apply_mean_reversion passed")


def test_get_confidence_score():
    """
    Test confidence score calculation with weighted formula.
    
    Formula: combined_score = (vol_score * 0.7) + (age_score * 0.3)
    Ranges: High >= 2.5, Medium in [1.5, 2.5), Low < 1.5
    
    vol_score mapping:
        3 if volatility <= 5.0 (Low volatility = High score)
        2 if 5.0 < volatility <= 10.0 (Medium volatility = Medium score)
        1 if volatility > 10.0 (High volatility = Low score)
    
    age_score mapping:
        3 if fund_age >= 10 (Mature = High score)
        2 if 5 <= fund_age < 10 (Established = Medium score)
        1 if fund_age < 5 (Young = Low score)
    """
    
    # Test 1: Low volatility + mature fund = High confidence
    # vol_score=3 (3.5<=5), age_score=3 (10>=10)
    # combined = 3*0.7 + 3*0.3 = 2.1 + 0.9 = 3.0 >= 2.5 → High ✅
    result = get_confidence_score(volatility=3.5, fund_age_years=10)
    assert result == "High", f"Expected 'High', got '{result}'"
    
    # Test 2: Medium volatility + mature fund = Medium confidence
    # vol_score=2 (7.5 in [5-10]), age_score=3 (10>=10)
    # combined = 2*0.7 + 3*0.3 = 1.4 + 0.9 = 2.3 in [1.5, 2.5) → Medium ✅
    result = get_confidence_score(volatility=7.5, fund_age_years=10)
    assert result == "Medium", f"Expected 'Medium', got '{result}'"
    
    # Test 3: High volatility + mature fund = MEDIUM confidence
    # Mature age (10 years) offsets high volatility in weighted formula
    # vol_score=1 (15>10), age_score=3 (10>=10)
    # combined = 1*0.7 + 3*0.3 = 0.7 + 0.9 = 1.6 in [1.5, 2.5) → Medium ✅
    result = get_confidence_score(volatility=15.0, fund_age_years=10)
    assert result == "Medium", f"Expected 'Medium', got '{result}'"
    
    # Test 4: Low volatility but young fund = Medium confidence
    # Low volatility helps offset young age in weighted formula
    # vol_score=3 (3.5<=5), age_score=1 (3<5)
    # combined = 3*0.7 + 1*0.3 = 2.1 + 0.3 = 2.4 in [1.5, 2.5) → Medium ✅
    result = get_confidence_score(volatility=3.5, fund_age_years=3)
    assert result == "Medium", f"Expected 'Medium', got '{result}'"
    
    # Test 5: High volatility and very young fund = Low confidence
    # Both factors are bad: high volatility + very young age
    # vol_score=1 (15>10), age_score=1 (2<5)
    # combined = 1*0.7 + 1*0.3 = 0.7 + 0.3 = 1.0 < 1.5 → Low ✅
    result = get_confidence_score(volatility=15.0, fund_age_years=2)
    assert result == "Low", f"Expected 'Low', got '{result}'"
    
    print("✅ test_get_confidence_score passed")


def test_get_confidence_percentage():
    """Test confidence percentage mapping"""
    
    assert get_confidence_percentage("High") == 70
    assert get_confidence_percentage("Medium") == 50
    assert get_confidence_percentage("Low") == 25
    assert get_confidence_percentage("Unknown") == 50  # Default
    
    print("✅ test_get_confidence_percentage passed")


def test_mean_reversion_end_to_end():
    """
    End-to-end test: Get assumptions, apply mean reversion, get confidence.
    
    Scenario: Medium Risk user, recent 1yr market return was hot (15%)
    """
    
    risk_category = "Medium Risk"
    recent_1yr_return = 15.0
    
    # Get base assumptions
    assumptions = get_category_return_assumptions(risk_category)
    base_expected = assumptions["expected"]  # 9.0
    
    # Apply mean reversion
    # 15.0 > (9.0 + 5) = 14? Yes, so adjust to 9.0 - 1.0 = 8.0
    adjusted_expected = apply_mean_reversion(base_expected, recent_1yr_return)
    assert adjusted_expected == 8.0, f"Expected 8.0, got {adjusted_expected}"
    
    # Get confidence
    volatility = get_category_volatility(risk_category)  # 7.5
    confidence = get_confidence_score(volatility, fund_age_years=10)
    
    # vol_score=2 (7.5 in [5-10]), age_score=3 (10>=10)
    # combined = 2*0.7 + 3*0.3 = 1.4 + 0.9 = 2.3 in [1.5, 2.5) → Medium ✅
    assert confidence == "Medium", f"Expected 'Medium', got '{confidence}'"
    
    print("✅ test_mean_reversion_end_to_end passed")


# ===================================================================
# MAIN TEST RUNNER
# ===================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Mean Reversion Logic Unit Tests")
    print("="*60 + "\n")
    
    try:
        test_get_category_return_assumptions()
        test_get_category_volatility()
        test_apply_mean_reversion()
        test_get_confidence_score()
        test_get_confidence_percentage()
        test_mean_reversion_end_to_end()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60 + "\n")
    
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
