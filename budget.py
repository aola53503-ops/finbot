from datetime import datetime, timedelta
from database import Database

class BudgetManager:
    """Handle budget operations"""
    
    def __init__(self):
        self.db = Database()
    
    def create_budget(self, user_id, category, amount, period='monthly'):
        """Create a new budget"""
        return self.db.add_budget(user_id, category, amount, period)
    
    def get_budget_status(self, user_id):
        """Check current budget status"""
        budgets = self.db.get_budgets(user_id)
        
        if not budgets:
            return "No budgets set. Use /setbudget to create one."
        
        # Get current period transactions
        now = datetime.utcnow()
        if 'monthly' in [b.period for b in budgets]:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - timedelta(days=7)
        
        transactions = self.db.get_transactions_by_date(user_id, start_date, now)
        
        status = "📊 *Budget Status*\n━━━━━━━━━━━━━━━━\n\n"
        
        for budget in budgets:
            spent = sum(t.amount for t in transactions 
                       if t.category == budget.category and t.type == 'expense')
            
            remaining = budget.amount - spent
            percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
            
            status += f"📌 *{budget.category}*\n"
            status += f"├─ Budget: ${budget.amount:.2f}\n"
            status += f"├─ Spent: ${spent:.2f}\n"
            status += f"├─ Remaining: ${remaining:.2f}\n"
            
            # Alert
            if percentage > 90:
                status += f"└─ ⚠️ *WARNING:* {percentage:.1f}% used!\n\n"
            elif percentage > 75:
                status += f"└─ ⚠️ *Alert:* {percentage:.1f}% used\n\n"
            else:
                status += f"└─ ✅ On track ({percentage:.1f}% used)\n\n"
        
        return status
    
    def check_budget_alerts(self, user_id):
        """Check for budget alerts"""
        budgets = self.db.get_budgets(user_id)
        alerts = []
        
        now = datetime.utcnow()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        transactions = self.db.get_transactions_by_date(user_id, start_date, now)
        
        for budget in budgets:
            spent = sum(t.amount for t in transactions 
                       if t.category == budget.category and t.type == 'expense')
            
            percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
            
            if percentage > 90:
                alerts.append(f"⚠️ *{budget.category}*: {percentage:.1f}% used (${spent:.2f}/${budget.amount:.2f})")
            elif percentage > 75:
                alerts.append(f"📢 *{budget.category}*: {percentage:.1f}% used (${spent:.2f}/${budget.amount:.2f})")
        
        return alerts
