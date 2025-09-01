#!/usr/bin/env python3
"""
Comprehensive test script to verify the rounding functionality works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils import calculate_minimum_bid

def test_comprehensive_rounding():
    """Test the rounding functionality comprehensively"""
    
    test_cases = [
        # (current_amount, expected_minimum_bid, description)
        (47761.96, 47762, "User's specific case"),
        (47761.5, 47762, "Half way up"),
        (47761.1, 47762, "Just above half"),
        (47761.99, 47762, "Almost next whole number"),
        (47761.01, 47762, "Just above whole number"),
        (47761.0, 47762, "Exactly whole number"),
        (47760.5, 47761, "Half way up to next"),
        (47760.1, 47761, "Just above half"),
        (100.99, 101, "Small amount with decimal"),
        (100.5, 101, "Small amount half way"),
        (100.1, 101, "Small amount just above"),
        (100.0, 101, "Exactly 100"),
        (99.99, 100, "Just below 100"),
        (99.5, 100, "Half way to 100"),
        (1.99, 2, "Very small amount"),
        (1.5, 2, "Half way to 2"),
        (1.1, 2, "Just above 1"),
        (1.0, 2, "Exactly 1"),
        (0.99, 1, "Just below 1"),
        (0.5, 1, "Half way to 1"),
    ]
    
    print("=== Comprehensive Rounding Test ===")
    print("Testing minimum bid calculation for various scenarios")
    print("=" * 60)
    
    all_passed = True
    
    for current_amount, expected_minimum, description in test_cases:
        result = calculate_minimum_bid(current_amount)
        status = "✓" if result == expected_minimum else "✗"
        print(f"{status} {description}")
        print(f"    Current: ₹{current_amount} -> Min Bid: ₹{result} (Expected: ₹{expected_minimum})")
        
        if result != expected_minimum:
            all_passed = False
            print(f"    ERROR: Expected ₹{expected_minimum}, got ₹{result}")
        
        # Verify that the result is actually higher than the current amount
        if result <= current_amount:
            all_passed = False
            print(f"    ERROR: Minimum bid (₹{result}) is not higher than current amount (₹{current_amount})")
        
        print()
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed! The rounding system works correctly.")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

def test_edge_cases():
    """Test edge cases"""
    
    print("\n=== Edge Cases Test ===")
    
    edge_cases = [
        (0, 1, "Zero amount"),
        (-100, 1, "Negative amount"),
        (999999.99, 1000000, "Large amount with decimal"),
        (1000000.0, 1000001, "Exactly 1 million"),
    ]
    
    for current_amount, expected_minimum, description in edge_cases:
        result = calculate_minimum_bid(current_amount)
        print(f"{description}: ₹{current_amount} -> ₹{result} (Expected: ₹{expected_minimum})")

if __name__ == "__main__":
    test_comprehensive_rounding()
    test_edge_cases()
