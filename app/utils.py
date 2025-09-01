from flask import session, redirect, url_for
from functools import wraps

def calculate_minimum_increment(amount: float) -> float:
    """Calculate initial minimum bid increment based on Indian price brackets.
    Brackets:
    - < 10,000 => 5%
    - 10,000..99,999 => 3%
    - 1,00,000..9,99,999 => 2%
    - 10,00,000..99,99,999 => 1.5%
    - >= 1,00,00,000 => 1%
    Always returns at least 1.0, rounded to nearest whole number
    """
    try:
        amt = float(amount or 0)
    except Exception:
        amt = 0.0

    if amt < 10000:
        pct = 0.05
    elif amt < 100000:
        pct = 0.03
    elif amt < 1000000:
        pct = 0.02
    elif amt < 10000000:
        pct = 0.015
    else:
        pct = 0.01

    increment = amt * pct
    # Round to nearest whole number to avoid decimal bids
    rounded_increment = round(increment)
    return rounded_increment if rounded_increment >= 1.0 else 1.0

def calculate_minimum_bid(current_amount: float) -> float:
    """Calculate the minimum bid amount by adding minimum increment to current amount and rounding to whole number.
    This ensures no decimal bids while maintaining proper minimum increment logic.
    """
    # Handle edge cases
    if current_amount <= 0:
        return 1
    
    # Calculate minimum increment based on current amount
    increment = calculate_minimum_increment(current_amount)
    
    # Add increment to current amount and round to nearest whole number
    minimum_bid = round(current_amount + increment)
    
    return minimum_bid

def format_indian_currency(amount):
    """Format amount in Indian currency style (1,00,000.00)"""
    if amount is None:
        return "Rs 0.00"
    
    # Convert to string with 2 decimal places
    amount_str = f"{amount:.2f}"
    
    # Split into integer and decimal parts
    parts = amount_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    # Indian numbering system: group from right
    # Last 3 digits together, then groups of 2 digits
    if len(integer_part) <= 3:
        formatted_integer = integer_part
    else:
        # Take last 3 digits
        last_three = integer_part[-3:]
        # Take remaining digits
        remaining = integer_part[:-3]
        
        # Add commas every 2 digits from right for remaining part
        formatted_remaining = ""
        for i in range(len(remaining)):
            if i > 0 and i % 2 == 0:
                formatted_remaining = "," + formatted_remaining
            formatted_remaining = remaining[-(i+1)] + formatted_remaining
        
        formatted_integer = formatted_remaining + "," + last_three
    
    return f"Rs {formatted_integer}.{decimal_part}"

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# Role required decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
