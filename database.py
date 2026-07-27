from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    currency = Column(String(10), default='USD')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user")
    budgets = relationship("Budget", back_populates="user")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    amount = Column(Float, nullable=False)
    category = Column(String(50))
    description = Column(Text)
    type = Column(String(20))  # 'income' or 'expense'
    date = Column(DateTime, default=datetime.utcnow)
    note = Column(Text)
    
    user = relationship("User", back_populates="transactions")

class Budget(Base):
    __tablename__ = 'budgets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    category = Column(String(50))
    amount = Column(Float)
    period = Column(String(20))  # 'monthly', 'weekly', 'yearly'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="budgets")

class SavingsGoal(Base):
    __tablename__ = 'savings_goals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    name = Column(String(100))
    target_amount = Column(Float)
    current_amount = Column(Float, default=0)
    deadline = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

class Database:
    @staticmethod
    def get_session():
        return SessionLocal()
    
    @staticmethod
    def add_user(telegram_id, username=None, first_name=None):
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name
                )
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    @staticmethod
    def add_transaction(telegram_id, amount, category, description, trans_type, note=None):
        session = SessionLocal()
        try:
            transaction = Transaction(
                user_id=telegram_id,
                amount=amount,
                category=category,
                description=description,
                type=trans_type,
                note=note
            )
            session.add(transaction)
            session.commit()
            return transaction
        finally:
            session.close()
    
    @staticmethod
    def get_transactions(telegram_id, limit=50):
        session = SessionLocal()
        try:
            transactions = session.query(Transaction).filter_by(
                user_id=telegram_id
            ).order_by(Transaction.date.desc()).limit(limit).all()
            return transactions
        finally:
            session.close()
    
    @staticmethod
    def get_transactions_by_date(telegram_id, start_date, end_date):
        session = SessionLocal()
        try:
            transactions = session.query(Transaction).filter(
                Transaction.user_id == telegram_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            ).order_by(Transaction.date.desc()).all()
            return transactions
        finally:
            session.close()
    
    @staticmethod
    def add_budget(telegram_id, category, amount, period='monthly'):
        session = SessionLocal()
        try:
            budget = Budget(
                user_id=telegram_id,
                category=category,
                amount=amount,
                period=period
            )
            session.add(budget)
            session.commit()
            return budget
        finally:
            session.close()
    
    @staticmethod
    def get_budgets(telegram_id):
        session = SessionLocal()
        try:
            budgets = session.query(Budget).filter_by(user_id=telegram_id).all()
            return budgets
        finally:
            session.close()
    
    @staticmethod
    def add_savings_goal(telegram_id, name, target_amount, deadline):
        session = SessionLocal()
        try:
            goal = SavingsGoal(
                user_id=telegram_id,
                name=name,
                target_amount=target_amount,
                deadline=deadline
            )
            session.add(goal)
            session.commit()
            return goal
        finally:
            session.close()
    
    @staticmethod
    def update_savings_goal(goal_id, current_amount):
        session = SessionLocal()
        try:
            goal = session.query(SavingsGoal).filter_by(id=goal_id).first()
            if goal:
                goal.current_amount = current_amount
                session.commit()
                return goal
            return None
        finally:
            session.close()
