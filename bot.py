#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import os
from datetime import datetime
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
INCOME_CATEGORY, INCOME_AMOUNT, INCOME_DESCRIPTION = range(3)
EXPENSE_CATEGORY, EXPENSE_AMOUNT, EXPENSE_DESCRIPTION = range(3, 6)

# ==================== INITIALIZATION ====================
db = Database()
tm = TransactionManager()
analytics = Analytics()
budget_mgr = BudgetManager()

# ==================== START COMMAND ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with main menu"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    summary = tm.get_summary(user.id, 'today')
    
    keyboard = [
        [InlineKeyboardButton("💰 Add Income", callback_data="income"),
         InlineKeyboardButton("💸 Add Expense", callback_data="expense")],
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
         InlineKeyboardButton("📈 Analytics", callback_data="analytics")],
        [InlineKeyboardButton("📋 Transactions", callback_data="transactions"),
         InlineKeyboardButton("📌 Budget", callback_data="budget")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
🏦 *FINBOT* - Your Intelligent Banking Assistant 🏦

*Welcome {user.first_name}!*

💰 Income: ${summary['total_income']:.2f}
💸 Expenses: ${summary['total_expense']:.2f}
💎 Balance: ${summary['balance']:.2f}

*Select an option:*
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ==================== INCOME FLOW ====================

async def income_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select income category"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for cat in Config.INCOME_CATEGORIES:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"inc_{cat}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 *Add Income*\n\nSelect category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return INCOME_CATEGORY

async def income_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Income category selected"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("inc_", "")
    context.user_data['income_category'] = category
    
    await query.edit_message_text(
        f"💰 *Add Income*\n\nCategory: {category}\n\nEnter amount:",
        parse_mode='Markdown'
    )
    return INCOME_AMOUNT

async def income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Income amount entered"""
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be > 0. Enter amount:")
            return INCOME_AMOUNT
        
        context.user_data['income_amount'] = amount
        
        await update.message.reply_text(
            f"💰 Amount: ${amount:.2f}\n\nEnter description (or type /skip):",
            parse_mode='Markdown'
        )
        return INCOME_DESCRIPTION
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Enter amount:")
        return INCOME_AMOUNT

async def income_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Income description entered"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('income_amount', 0)
    category = context.user_data.get('income_category', 'Other Income')
    
    tm.add_income(user.id, amount, category, description)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Income Added!*

💰 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}
💎 Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def income_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip income description"""
    user = update.effective_user
    amount = context.user_data.get('income_amount', 0)
    category = context.user_data.get('income_category', 'Other Income')
    
    tm.add_income(user.id, amount, category, "No description")
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Income Added!*

💰 Amount: ${amount:.2f}
📂 Category: {category}
💎 Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# ==================== EXPENSE FLOW ====================

async def expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select expense category"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    top_cats = ['Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 
                'Bills & Utilities', 'Rent & Housing', 'Groceries', 'Other']
    for cat in top_cats:
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"exp_{cat}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💸 *Add Expense*\n\nSelect category:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return EXPENSE_CATEGORY

async def expense_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Expense category selected"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("exp_", "")
    context.user_data['expense_category'] = category
    
    await query.edit_message_text(
        f"💸 *Add Expense*\n\nCategory: {category}\n\nEnter amount:",
        parse_mode='Markdown'
    )
    return EXPENSE_AMOUNT

async def expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Expense amount entered"""
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be > 0. Enter amount:")
            return EXPENSE_AMOUNT
        
        context.user_data['expense_amount'] = amount
        
        await update.message.reply_text(
            f"💸 Amount: ${amount:.2f}\n\nEnter description (or type /skip):",
            parse_mode='Markdown'
        )
        return EXPENSE_DESCRIPTION
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Enter amount:")
        return EXPENSE_AMOUNT

async def expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Expense description entered"""
    user = update.effective_user
    description = update.message.text
    amount = context.user_data.get('expense_amount', 0)
    category = context.user_data.get('expense_category', 'Other')
    
    tm.add_expense(user.id, amount, category, description)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Expense Added!*

💸 Amount: ${amount:.2f}
📂 Category: {category}
📝 Description: {description}
💎 Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def expense_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip expense description"""
    user = update.effective_user
    amount = context.user_data.get('expense_amount', 0)
    category = context.user_data.get('expense_category', 'Other')
    
    tm.add_expense(user.id, amount, category, "No description")
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
✅ *Expense Added!*

💸 Amount: ${amount:.2f}
📂 Category: {category}
💎 Balance: ${tm.get_balance(user.id):.2f}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# ==================== DASHBOARD & OTHER COMMANDS ====================

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dashboard"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    summary = tm.get_summary(user.id, 'month')
    
    message = f"""
📊 *Dashboard*
━━━━━━━━━━━━━━━━

💰 Income: ${summary['total_income']:.2f}
💸 Expenses: ${summary['total_expense']:.2f}
💎 Balance: ${summary['balance']:.2f}
📊 Transactions: {summary['transaction_count']}
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show transactions"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    transactions = db.get_transactions(user.id, limit=10)
    
    if not transactions:
        await query.edit_message_text("📋 No transactions yet.")
        return
    
    message = "📋 *Recent Transactions*\n\n"
    for t in transactions[:5]:
        sign = '+' if t.type == 'income' else '-'
        emoji = '💰' if t.type == 'income' else '💸'
        message += f"{emoji} {t.description}: {sign}${t.amount:.2f} ({t.category})\n"
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show analytics"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📈 *Analytics*\n\nFeature coming soon!\n\n🏠 Menu",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="menu")]])
    )

async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show budget"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    status = budget_mgr.get_budget_status(user.id)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== MENU & CANCEL ====================

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to menu"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await start_command(update, context)

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel callback"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "❌ Cancelled.\n\nType /start to return!",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel command"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled.\n\nType /start to return!",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ==================== MAIN ====================

def main():
    try:
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("❌ BOT_TOKEN not set!")
            sys.exit(1)
        
        logger.info("🏦 FinBot is starting...")
        
        application = Application.builder().token(token).build()
        
        # ===== INCOME CONVERSATION =====
        income_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(income_category, pattern="^income$")],
            states={
                INCOME_CATEGORY: [CallbackQueryHandler(income_category_selected, pattern="^inc_")],
                INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_amount)],
                INCOME_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, income_description),
                    CommandHandler("skip", income_skip)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                CallbackQueryHandler(cancel_callback, pattern="^cancel$")
            ]
        )
        application.add_handler(income_conv)
        
        # ===== EXPENSE CONVERSATION =====
        expense_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(expense_category, pattern="^expense$")],
            states={
                EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category_selected, pattern="^exp_")],
                EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount)],
                EXPENSE_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, expense_description),
                    CommandHandler("skip", expense_skip)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                CallbackQueryHandler(cancel_callback, pattern="^cancel$")
            ]
        )
        application.add_handler(expense_conv)
        
        # ===== COMMANDS =====
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("skip", cancel_command))
        
        # ===== CALLBACKS =====
        application.add_handler(CallbackQueryHandler(dashboard_command, pattern="^dashboard$"))
        application.add_handler(CallbackQueryHandler(transactions_command, pattern="^transactions$"))
        application.add_handler(CallbackQueryHandler(analytics_command, pattern="^analytics$"))
        application.add_handler(CallbackQueryHandler(budget_command, pattern="^budget$"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu$"))
        application.add_handler(CallbackQueryHandler(cancel_callback, pattern="^cancel$"))
        
        logger.info("✅ FinBot is running!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
