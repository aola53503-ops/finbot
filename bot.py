#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

from config import Config
from database import Database
from transactions import TransactionManager
from analytics import Analytics
from budget import BudgetManager

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================
ADD_INCOME, ADD_EXPENSE, SET_BUDGET, SET_GOAL = range(4)

# ==================== INITIALIZATION ====================
db = Database()
tm = TransactionManager()
analytics = Analytics()
budget_mgr = BudgetManager()

# ==================== COMMAND HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with main menu"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    # Get user summary
    summary = tm.get_summary(user.id, 'today')
    
    keyboard = [
        [InlineKeyboardButton("💰 Add Income", callback_data="add_income"),
         InlineKeyboardButton("💸 Add Expense", callback_data="add_expense")],
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
         InlineKeyboardButton("📈 Analytics", callback_data="analytics")],
        [InlineKeyboardButton("📋 Transactions", callback_data="transactions"),
         InlineKeyboardButton("📌 Budget", callback_data="budget")],
        [InlineKeyboardButton("🎯 Savings Goals", callback_data="goals"),
         InlineKeyboardButton("💡 Tips & Advice", callback_data="advice")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
🏦 *FINBOT* - Your Intelligent Banking Assistant 🏦

*Welcome {user.first_name}!*

💎 *Today's Summary:*
💰 Income: ${summary['total_income']:.2f}
💸 Expenses: ${summary['total_expense']:.2f}
💵 Balance: ${summary['balance']:.2f}
📊 Transactions: {summary['transaction_count']}

*Select an option:*
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show financial dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    summary = tm.get_summary(user.id, 'month')
    
    message = f"""
📊 *Financial Dashboard*
━━━━━━━━━━━━━━━━━━━━━

📅 *This Month:*
💰 Total Income: ${summary['total_income']:.2f}
💸 Total Expenses: ${summary['total_expense']:.2f}
💎 Net Balance: ${summary['balance']:.2f}
📊 Transactions: {summary['transaction_count']}

━━━━━━━━━━━━━━━━━━━━━

📈 *Quick Stats:*
• Daily Avg Spend: ${summary['total_expense']/30:.2f}
• Savings Rate: {((summary['balance']/summary['total_income'])*100) if summary['total_income'] > 0 else 0:.1f}%

• Top Category: {max(summary['expense_by_category'].items(), key=lambda x: x[1])[0] if summary['expense_by_category'] else 'N/A'}
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent transactions"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    transactions = db.get_transactions(user.id, limit=10)
    
    if not transactions:
        await query.edit_message_text(
            "📋 *No transactions yet*\n\nAdd your first transaction using the menu!",
            parse_mode='Markdown'
        )
        return
    
    message = "📋 *Recent Transactions*\n━━━━━━━━━━━━━━━━\n\n"
    
    for t in transactions[:10]:
        sign = '+' if t.type == 'income' else '-'
        emoji = '💰' if t.type == 'income' else '💸'
        message += f"{emoji} *{t.description}*\n"
        message += f"├─ {sign}${t.amount:.2f}\n"
        message += f"├─ {t.category}\n"
        message += f"└─ {t.date.strftime('%b %d, %H:%M')}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 View All", callback_data="view_all")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show financial analytics"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Get trends
    trends = analytics.calculate_monthly_trends(user.id)
    trends_msg = analytics.format_trends(trends)
    
    keyboard = [
        [InlineKeyboardButton("📈 Spending Trends", callback_data="trends")],
        [InlineKeyboardButton("💡 Get Advice", callback_data="advice")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"""
📈 *Financial Analytics*

{trends_msg}

Select an option below:
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def advice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show financial advice"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    advice = analytics.get_spending_advice(user.id)
    advice_msg = analytics.format_advice(advice)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        advice_msg,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show budget status"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    status = budget_mgr.get_budget_status(user.id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Set Budget", callback_data="set_budget")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        status,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show savings goals"""
    query = update.callback_query
    await query.answer()
    
    goals_msg = """
🎯 *Savings Goals*

Track your savings goals and progress!

*Features:*
• Set custom savings goals
• Track progress
• Get achievement notifications

*To create a goal:*
1. Type: `/setgoal "Goal Name" 1000 YYYY-MM-DD`
2. Example: `/setgoal "New Car" 5000 2025-12-31`

*Current Goals:*
No active goals. Create one using the command above!
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        goals_msg,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def add_income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add income flow"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for category in Config.INCOME_CATEGORIES:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"income_{category}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *Add Income*\n\nSelect income category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADD_INCOME

async def add_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add expense flow"""
    query = update.callback_query
    await query.answer()
    
    # Show top categories first
    keyboard = []
    for category in ['Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 'Bills & Utilities', 'Rent & Housing', 'Groceries', 'Other']:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"expense_{category}")])
    keyboard.append([InlineKeyboardButton("➕ All Categories", callback_data="all_categories")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💸 *Add Expense*\n\nSelect expense category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ADD_EXPENSE

# ==================== MESSAGE HANDLERS ====================

async def handle_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income amount input"""
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0.",
                parse_mode='Markdown'
            )
            return ADD_INCOME
        
        context.user_data['amount'] = amount
        
        await update.message.reply_text(
            f"💰 Amount: ${amount:.2f}\n\nDescribe this income:",
            parse_mode='Markdown'
        )
        return ADD_INCOME
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.",
            parse_mode='Markdown'
        )
        return ADD_INCOME

async def handle_income_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income description"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other Income')
    
    # Add transaction
    tm.add_income(user.id, amount, category, description)
    
    await update.message.reply_text(
        f"""
✅ *Income Added!*

💰 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}

💎 New Balance: ${tm.get_balance(user.id):.2f}

Type /start for menu!
""",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def handle_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense amount input"""
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0.",
                parse_mode='Markdown'
            )
            return ADD_EXPENSE
        
        context.user_data['amount'] = amount
        
        await update.message.reply_text(
            f"💸 Amount: ${amount:.2f}\n\nDescribe this expense:",
            parse_mode='Markdown'
        )
        return ADD_EXPENSE
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.",
            parse_mode='Markdown'
        )
        return ADD_EXPENSE

async def handle_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense description"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other')
    
    # Check budget alert
    tm.add_expense(user.id, amount, category, description)
    
    alerts = budget_mgr.check_budget_alerts(user.id)
    alert_msg = ""
    if alerts:
        alert_msg = "\n\n⚠️ *Budget Alerts:*\n" + "\n".join(alerts)
    
    await update.message.reply_text(
        f"""
✅ *Expense Added!*

💸 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}

💎 New Balance: ${tm.get_balance(user.id):.2f}
{alert_msg}

Type /start for menu!
""",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ==================== CALLBACK HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu":
        await start_command(update, context)
        return
    
    if data == "dashboard":
        await dashboard_command(update, context)
        return
    
    if data
