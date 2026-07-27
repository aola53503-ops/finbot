from datetime import datetime, timedelta
from database import Database
from config import Config

class TransactionManager:
    """Handle transaction operations"""
    
    def __init__(self):
        self.db = Database()
    
    def add_income(self, user_id, amount, category, description, note=None):
        """Add income transaction"""
        if not category:
            category = 'Other Income'
        
        # Validate category
        if category not in Config.INCOME_CATEGORIES:
            category = 'Other Income'
        
        return self.db.add_transaction(
            user_id, amount, category, description, 'income', note
        )
    
    def add_expense(self, user_id, amount, category, description, note=None):
        """Add expense transaction"""
        if not category:
            category = 'Other'
        
        # Validate category
        if category not in Config.CATEGORIES:
            category = 'Other'
        
        return self.db.add_transaction(
            user_id, amount, category, description, 'expense', note
        )
    
    def get_balance(self, user_id):
        """Calculate current balance"""
        transactions = self.db.get_transactions(user_id, limit=1000)
        
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expense = sum(t.amount for t in transactions if t.type == 'expense')
        
        return total_income - total_expense
    
    def get_summary(self, user_id, period='month'):
        """Get financial summary for a period"""
        now = datetime.utcnow()
        
        if period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - timedelta(days=30)
        
        transactions = self.db.get_transactions_by_date(user_id, start_date, now)
        
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expense = sum(t.amount for t in transactions if t.type == 'expense')
        
        # Category breakdown
        expense_by_category = {}
        for t in transactions:
            if t.type == 'expense':
                expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount
        
        income_by_category = {}
        for t in transactions:
            if t.type == 'income':
                income_by_category[t.category] = income_by_category.get(t.category, 0) + t.amount
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'expense_by_category': expense_by_category,
            'income_by_category': income_by_category,
            'transaction_count': len(transactions)
        }
    
    def format_transaction(self, transaction):
        """Format a single transaction for display"""
        emoji = '💰' if transaction.type == 'income' else '💸'
        sign = '+' if transaction.type == 'income' else '-'
        
        return f"""
{emoji} *{transaction.description}*
├─ Amount: {sign}${transaction.amount:.2f}
├─ Category: {transaction.category}
├─ Date: {transaction.date.strftime('%Y-%m-%d %H:%M')}
{f'└─ Note: {transaction.note}' if transaction.note else ''}
"""
    
    def format_summary(self, summary, period='Month'):
        """Format summary for display"""
        message = f"""
📊 *{period.capitalize()} Financial Summary*
━━━━━━━━━━━━━━━━━━━━━

💰 *Income:* ${summary['total_income']:.2f}
💸 *Expenses:* ${summary['total_expense']:.2f}
💎 *Balance:* ${summary['balance']:.2f}
📊 *Transactions:* {summary['transaction_count']}

━━━━━━━━━━━━━━━━━━━━━
"""
        
        if summary['expense_by_category']:
            message += "\n📉 *Top Expenses:*\n"
            sorted_expenses = sorted(
                summary['expense_by_category'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for category, amount in sorted_expenses:
                percentage = (amount / summary['total_expense'] * 100) if summary['total_expense'] > 0 else 0
                message += f"├─ {category}: ${amount:.2f} ({percentage:.1f}%)\n"
        
        if summary['income_by_category']:
            message += "\n📈 *Top Income:*\n"
            sorted_income = sorted(
                summary['income_by_category'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            for category, amount in sorted_income:
                message += f"├─ {category}: ${amount:.2f}\n"
        
        return message
