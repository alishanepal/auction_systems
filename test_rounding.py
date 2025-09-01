#!/usr/bin/env python3
"""
Test script to verify rounding functionality for minimum bid increments
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils import calculate_minimum_increment

def test_minimum_increment_rounding():
    """Test that minimum increments are properly rounded"""
    
    test_cases = [
        (100, 5),      # 5% of 100 = 5
        (500, 25),     # 5% of 500 = 25
        (1000, 50),    # 5% of 1000 = 50
        (5000, 250),   # 5% of 5000 = 250
        (9999, 500),   # 5% of 9999 = 499.95, rounded to 500
        (10000, 300),  # 3% of 10000 = 300
        (50000, 1500), # 3% of 50000 = 1500
        (99999, 3000), # 3% of 99999 = 2999.97, rounded to 3000
        (100000, 2000), # 2% of 100000 = 2000
        (500000, 10000), # 2% of 500000 = 10000
        (999999, 20000), # 2% of 999999 = 19999.98, rounded to 20000
        (1000000, 15000), # 1.5% of 1000000 = 15000
        (5000000, 75000), # 1.5% of 5000000 = 75000
        (9999999, 150000), # 1.5% of 9999999 = 149999.985, rounded to 150000
        (10000000, 100000), # 1% of 10000000 = 100000
        (50000000, 500000), # 1% of 50000000 = 500000
    ]
    
    print("Testing minimum increment rounding...")
    print("=" * 50)
    
    all_passed = True
    
    for amount, expected in test_cases:
        result = calculate_minimum_increment(amount)
        status = "✓" if result == expected else "✗"
        print(f"{status} Amount: ₹{amount:,} -> Increment: ₹{result:,} (Expected: ₹{expected:,})")
        
        if result != expected:
            all_passed = False
            print(f"    ERROR: Expected ₹{expected:,}, got ₹{result:,}")
    
    print("=" * 50)
    if all_passed:
        print("✓ All tests passed! Minimum increments are properly rounded.")
    else:
        print("✗ Some tests failed!")
    
    return all_passed

def test_edge_cases():
    """Test edge cases for minimum increments"""
    
    print("\nTesting edge cases...")
    print("=" * 50)
    
    # Test very small amounts
    result = calculate_minimum_increment(1)
    print(f"Amount: ₹1 -> Increment: ₹{result} (Should be at least ₹1)")
    
    result = calculate_minimum_increment(0)
    print(f"Amount: ₹0 -> Increment: ₹{result} (Should be at least ₹1)")
    
    result = calculate_minimum_increment(-100)
    print(f"Amount: ₹-100 -> Increment: ₹{result} (Should be at least ₹1)")
    
    # Test boundary values
    result = calculate_minimum_increment(9999.99)
    print(f"Amount: ₹9,999.99 -> Increment: ₹{result} (Should be ₹500)")
    
    result = calculate_minimum_increment(10000.01)
    print(f"Amount: ₹10,000.01 -> Increment: ₹{result} (Should be ₹300)")

if __name__ == "__main__":
    test_minimum_increment_rounding()
    test_edge_cases()
