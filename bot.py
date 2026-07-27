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
SELECTING_CATEGORY, ENTERING_AMOUNT, ENTERING_DESCRIPTION = range(3)
SELECTING_EXPENSE_CATEGORY, ENTERING_EXPENSE_AMOUNT, ENTERING_EXPENSE_DESCRIPTION = range(3, 6)

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

# ==================== INCOME FLOW ====================

async def add_income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add income flow"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['transaction_type'] = 'income'
    
    keyboard = []
    for category in Config.INCOME_CATEGORIES:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"inc_cat_{category}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *Add Income*\n\nSelect income category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SELECTING_CATEGORY

async def income_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income category selection"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("inc_cat_", "")
    context.user_data['category'] = category
    
    await query.edit_message_text(
        f"💰 *Add Income*\n\nCategory: {category}\n\n💰 Enter amount:",
        parse_mode='Markdown'
    )
    return ENTERING_AMOUNT

async def income_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income amount input"""
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0.\n\n💰 Enter amount:",
                parse_mode='Markdown'
            )
            return ENTERING_AMOUNT
        
        context.user_data['amount'] = amount
        
        await update.message.reply_text(
            f"💰 Amount: ${amount:.2f}\n\n📝 Enter description (or /skip):",
            parse_mode='Markdown'
        )
        return ENTERING_DESCRIPTION
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.\n\n💰 Enter amount:",
            parse_mode='Markdown'
        )
        return ENTERING_AMOUNT

async def income_description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income description"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other Income')
    
    # Add transaction
    tm.add_income(user.id, amount, category, description)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Income Added!*

💰 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}

💎 New Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def income_skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip description for income"""
    user = update.effective_user
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other Income')
    
    # Add transaction with no description
    tm.add_income(user.id, amount, category, "No description")
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Income Added!*

💰 Amount: ${amount:.2f}
📂 Category: {category}

💎 New Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# ==================== EXPENSE FLOW ====================

async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add expense flow"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['transaction_type'] = 'expense'
    
    keyboard = []
    # Show top categories
    top_categories = ['Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 
                      'Bills & Utilities', 'Rent & Housing', 'Groceries', 'Other']
    for category in top_categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"exp_cat_{category}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💸 *Add Expense*\n\nSelect expense category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return SELECTING_EXPENSE_CATEGORY

async def expense_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense category selection"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("exp_cat_", "")
    context.user_data['category'] = category
    
    await query.edit_message_text(
        f"💸 *Add Expense*\n\nCategory: {category}\n\n💰 Enter amount:",
        parse_mode='Markdown'
    )
    return ENTERING_EXPENSE_AMOUNT

async def expense_amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense amount input"""
    try:
        amount = float(update.message.text)
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0.\n\n💰 Enter amount:",
                parse_mode='Markdown'
            )
            return ENTERING_EXPENSE_AMOUNT
        
        context.user_data['amount'] = amount
        
        await update.message.reply_text(
            f"💸 Amount: ${amount:.2f}\n\n📝 Enter description (or /skip):",
            parse_mode='Markdown'
        )
        return ENTERING_EXPENSE_DESCRIPTION
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.\n\n💰 Enter amount:",
            parse_mode='Markdown'
        )
        return ENTERING_EXPENSE_AMOUNT

async def expense_description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense description"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other')
    
    # Add transaction
    tm.add_expense(user.id, amount, category, description)
    
    # Check budget alerts
    alerts = budget_mgr.check_budget_alerts(user.id)
    alert_msg = ""
    if alerts:
        alert_msg = "\n\n⚠️ *Budget Alerts:*\n" + "\n".join(alerts)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Expense Added!*

💸 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}

💎 New Balance: ${tm.get_balance(user.id):.2f}
{alert_msg}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def expense_skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip description for expense"""
    user = update.effective_user
    amount = context.user_data.get('amount', 0)
    category = context.user_data.get('category', 'Other')
    
    # Add transaction with no description
    tm.add_expense(user.id, amount, category, "No description")
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Expense Added!*

💸 Amount: ${amount:.2f}
📂 Category: {category}

💎 New Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# ==================== OTHER COMMAND HANDLERS ====================

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
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
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

*To create a goal:*
`/setgoal "Goal Name" Amount YYYY-MM-DD`

*Example:*
`/setgoal "New Car" 5000 2025-12-31`

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

async def set_budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set budget via command"""
    try:
        if not context.args:
            await update.message.reply_text(
                "📝 *Usage:* `/setbudget \"Category\" Amount`\n\nExample: `/setbudget \"Food & Dining\" 500`",
                parse_mode='Markdown'
            )
            return
        
        # Parse the command
        text = ' '.join(context.args)
        if '"' in text:
            category = text.split('"')[1]
            amount_part = text.split('"')[2].strip()
        else:
            parts = text.split(' ')
            category = parts[0]
            amount_part = ' '.join(parts[1:])
        
        amount = float(amount_part)
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Amount must be greater than 0.",
                parse_mode='Markdown'
            )
            return
        
        user = update.effective_user
        budget_mgr.create_budget(user.id, category, amount)
        
        await update.message.reply_text(
            f"✅ *Budget Set!*\n\n📌 Category: {category}\n💰 Amount: ${amount:.2f}\n📅 Period: Monthly",
            parse_mode='Markdown'
        )
        
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Invalid format. Use: `/setbudget \"Category\" Amount`\n\nExample: `/setbudget \"Food & Dining\" 500`",
            parse_mode='Markdown'
        )

async def set_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set savings goal via command"""
    try:
        if len(context.args) < 3:
            await update.message.reply_text(
                "📝 *Usage:* `/setgoal \"Goal Name\" Amount YYYY-MM-DD`\n\n"
                "Example: `/setgoal \"New Car\" 5000 2025-12-31`",
                parse_mode='Markdown'
            )
            return
        
        # Parse the command
        text = ' '.join(context.args)
        if '"' in text:
            name = text.split('"')[1]
            rest = text.split('"')[2].strip().split(' ')
            amount = float(rest[0])
            deadline = datetime.strptime(rest[1], '%Y-%m-%d')
        else:
            parts = text.split(' ')
            name = parts[0]
            amount = float(parts[1])
            deadline = datetime.strptime(parts[2], '%Y-%m-%d')
        
        user = update.effective_user
        db.add_savings_goal(user.id, name, amount, deadline)
        
        await update.message.reply_text(
            f"""
✅ *Savings Goal Set!*

🎯 Goal: {name}
💰 Target: ${amount:.2f}
📅 Deadline: {deadline.strftime('%B %d, %Y')}
""",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {e}\n\nUse: `/setgoal \"Goal Name\" Amount YYYY-MM-DD`",
            parse_mode='Markdown'
        )

# ==================== CANCEL / MENU ====================

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to menu"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start_command(update, context)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled.\n\nType /start to return to menu!",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ==================== MAIN FUNCTION ====================

def main():
    try:
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("❌ BOT_TOKEN not set!")
            sys.exit(1)
        
        logger.info("🏦 FinBot is starting...")
        
        application = Application.builder().token(token).build()
        
        # ===== COMMAND HANDLERS =====
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("setbudget", set_budget_command))
        application.add_handler(CommandHandler("setgoal", set_goal_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # ===== INCOME CONVERSATION =====
        income_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(add_income_start, pattern="^add_income$")],
            states={
                SELECTING_CATEGORY: [
                    CallbackQueryHandler(income_category_selected, pattern="^inc_cat_")
                ],
                ENTERING_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, income_amount_entered)
                ],
                ENTERING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, income_description_entered),
                    CommandHandler("skip", income_skip_description)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                CallbackQueryHandler(menu_callback, pattern="^menu$")
            ]
        )
        application.add_handler(income_conv)
        
        # ===== EXPENSE CONVERSATION =====
        expense_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(add_expense_start, pattern="^add_expense$")],
            states={
                SELECTING_EXPENSE_CATEGORY: [
                    CallbackQueryHandler(expense_category_selected, pattern="^exp_cat_")
                ],
                ENTERING_EXPENSE_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount_entered)
                ],
                ENTERING_EXPENSE_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, expense_description_entered),
                    CommandHandler("skip", expense_skip_description)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                CallbackQueryHandler(menu_callback, pattern="^menu$")
            ]
        )
        application.add_handler(expense_conv)
        
        # ===== CALLBACK HANDLERS =====
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^dashboard$"))
        application.add_handler(CallbackQueryHandler(transactions_command, pattern="^transactions$"))
        application.add_handler(CallbackQueryHandler(analytics_command, pattern="^analytics$"))
        application.add_handler(CallbackQueryHandler(advice_command, pattern="^advice$"))
        application.add_handler(CallbackQueryHandler(budget_command, pattern="^budget$"))
        application.add_handler(CallbackQueryHandler(goals_command, pattern="^goals$"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu$"))
        application.add_handler(CallbackQueryHandler(set_budget_command, pattern="^set_budget$"))
        
        logger.info("✅ FinBot is running!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
