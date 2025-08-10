from flask import session, redirect, url_for
from functools import wraps

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
