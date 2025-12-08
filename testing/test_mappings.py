# test_mappings.py
from mfdata import map_fund_category_to_risk_profile, get_category_return_assumptions

def test_mapping_logic():
    """Test category-to-risk mapping"""
    test_cases = [
        ("Liquid", "Low Risk"),
        ("Gilt", "Low Risk"),
        ("Large Cap", "Medium Risk"),
        ("Small Cap", "High Risk"),
        ("Conservative Hybrid", "Moderate Risk"),
        ("Balanced Advantage", "Medium Risk"),
    ]
    
    for category, expected_risk in test_cases:
        result = map_fund_category_to_risk_profile(category)
        assert result == expected_risk, f"Failed: {category} → {result} (expected {expected_risk})"
        print(f"✅ {category} → {expected_risk}")

def test_return_assumptions():
    """Test return lookups"""
    # Liquid should map to Low Risk → 6.0%
    assumptions = get_category_return_assumptions("Liquid")
    assert assumptions["expected"] == 6.0
    print(f"✅ Liquid expected return: {assumptions['expected']}%")
    
    # Small Cap should map to High Risk → 12.0%
    assumptions = get_category_return_assumptions("Small Cap")
    assert assumptions["expected"] == 12.0
    print(f"✅ Small Cap expected return: {assumptions['expected']}%")

if __name__ == "__main__":
    test_mapping_logic()
    test_return_assumptions()
    print("✅ All tests passed!")