import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """FinBot Configuration"""
    
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found")
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///finbot.db')
    
    # Default Currency
    DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'USD')
    
    # Categories
    CATEGORIES = [
        'Food & Dining',
        'Transportation',
        'Shopping',
        'Entertainment',
        'Bills & Utilities',
        'Rent & Housing',
        'Healthcare',
        'Education',
        'Insurance',
        'Groceries',
        'Dining Out',
        'Coffee Shops',
        'Fuel',
        'Public Transport',
        'Car Maintenance',
        'Online Shopping',
        'Retail',
        'Movies',
        'Concerts',
        'Subscription',
        'Gaming',
        'Electricity',
        'Water',
        'Internet',
        'Phone',
        'Rent',
        'Mortgage',
        'Insurance Premium',
        'Doctor',
        'Pharmacy',
        'Tuition',
        'Books',
        'Supplies',
        'Salary',
        'Freelance',
        'Investment',
        'Gift',
        'Savings',
        'Other'
    ]
    
    # Income Categories
    INCOME_CATEGORIES = [
        'Salary',
        'Freelance',
        'Investment',
        'Gift',
        'Refund',
        'Bonus',
        'Rental Income',
        'Other Income'
    ]
    
    # Expense Categories
    EXPENSE_CATEGORIES = [c for c in CATEGORIES if c not in INCOME_CATEGORIES]
    
    # Budget Periods
    BUDGET_PERIODS = ['Daily', 'Weekly', 'Monthly', 'Yearly']
