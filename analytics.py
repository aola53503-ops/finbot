from datetime import datetime, timedelta
from database import Database
import numpy as np

class Analytics:
    """Financial analytics engine"""
    
    def __init__(self):
        self.db = Database()
    
    def calculate_monthly_trends(self, user_id, months=3):
        """Calculate monthly spending trends"""
        trends = []
        
        now = datetime.utcnow()
        for i in range(months):
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_start = month_start - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            transactions = self.db.get_transactions_by_date(user_id, month_start, month_end)
            
            total_expense = sum(t.amount for t in transactions if t.type == 'expense')
            total_income = sum(t.amount for t in transactions if t.type == 'income')
            
            trends.append({
                'month': month_start.strftime('%B %Y'),
                'income': total_income,
                'expense': total_expense,
                'savings': total_income - total_expense
            })
        
        return trends
    
    def get_spending_advice(self, user_id):
        """Generate personalized spending advice"""
        summary = self.db.get_summary(user_id, period='month')
        
        advice = []
        
        # Check savings rate
        if summary['total_income'] > 0:
            savings_rate = (summary['balance'] / summary['total_income']) * 100
            
            if savings_rate < 20:
                advice.append("💡 *Tip:* Try to save at least 20% of your income. Consider cutting unnecessary expenses.")
            elif savings_rate < 40:
                advice.append("👍 *Good:* You're saving above 20%. Keep it up!")
            else:
                advice.append("🌟 *Excellent:* You're saving over 40%. You're on the right track!")
        
        # Check biggest expense categories
        if summary['expense_by_category']:
            top_category = max(summary['expense_by_category'].items(), key=lambda x: x[1])
            advice.append(f"📊 *Top Expense:* {top_category[0]} (${top_category[1]:.2f}) - Consider reducing this category.")
        
        # Check for unnecessary subscriptions
        subscriptions = summary['expense_by_category'].get('Subscription', 0)
        if subscriptions > 50:
            advice.append("💸 *Subscriptions Alert:* You're spending ${:.2f} on subscriptions. Review what you actually use.".format(subscriptions))
        
        return advice
    
    def format_trends(self, trends):
        """Format trends for display"""
        if not trends:
            return "No data available"
        
        message = "📈 *Monthly Trends*\n━━━━━━━━━━━━━━━━\n\n"
        
        for trend in trends:
            message += f"📅 *{trend['month']}*\n"
            message += f"├─ Income: ${trend['income']:.2f}\n"
            message += f"├─ Expenses: ${trend['expense']:.2f}\n"
            message += f"└─ Savings: ${trend['savings']:.2f}\n\n"
        
        return message
    
    def format_advice(self, advice):
        """Format advice for display"""
        if not advice:
            return "📊 No advice available. Keep tracking your finances!"
        
        message = "💡 *Financial Insights*\n━━━━━━━━━━━━━━━━\n\n"
        for tip in advice:
            message += f"{tip}\n\n"
        
        return message
