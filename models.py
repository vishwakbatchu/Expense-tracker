"""SQLAlchemy models.  IDs and field names mirror the existing JSON API."""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(32), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    category: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Income(Base):
    __tablename__ = "income"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    source: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)


class Budget(Base):
    __tablename__ = "budgets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
    overall: Mapped[float | None] = mapped_column(Float, nullable=True)


class CategoryBudget(Base):
    __tablename__ = "category_budgets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
    category: Mapped[str] = mapped_column(String(255), primary_key=True)
    amount: Mapped[float] = mapped_column(Float)


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)
    day: Mapped[int] = mapped_column(Integer)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    username: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class BackupSnapshot(Base):
    __tablename__ = "backup_snapshots"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)


class LegacyImport(Base):
    __tablename__ = "legacy_imports"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
