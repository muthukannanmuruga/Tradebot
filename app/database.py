"""
Database models using SQLAlchemy for trade history and portfolio tracking.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from app.config import config

# Create database engine
# For PostgreSQL, we don't need check_same_thread (that's for SQLite)
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,  # Verify connection before using
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Trade(Base):
    """Trade history model"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, index=True)
    side = Column(String)  # BUY or SELL
    quantity = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)
    status = Column(String)  # OPEN, CLOSED, CANCELLED
    ai_reasoning = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)
    order_id = Column(String, nullable=True, unique=True)
    is_sandbox = Column(Boolean, default=False, index=True)  # True for testnet/sandbox, False for live


class Portfolio(Base):
    """Portfolio tracking model"""

    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, unique=True, index=True)
    quantity = Column(Float)
    entry_price = Column(Float)
    current_price = Column(Float)
    total_invested = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    unrealized_pl = Column(Float)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_sandbox = Column(Boolean, default=False, index=True)  # True for testnet/sandbox, False for live


class BotMetrics(Base):
    """Bot performance metrics – one row per market (binance / upstox)"""

    __tablename__ = "bot_metrics"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String, default="binance", index=True)  # 'binance' or 'upstox'
    is_sandbox = Column(Boolean, default=False, index=True)  # True for testnet/sandbox, False for live
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_profit_loss = Column(Float, default=0)
    win_rate = Column(Float, default=0)
    last_trade_time = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AdminSetting(Base):
    """Simple key/value store for runtime admin settings."""

    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
# Initialize tables (lazy initialization on first use)
_tables_initialized = False


def init_db():
    """Initialize database tables"""
    global _tables_initialized
    if not _tables_initialized:
        try:
            Base.metadata.create_all(bind=engine)
            # Migrate: add new columns if they don't exist yet
            with engine.connect() as conn:
                for col, coltype in [
                    ("total_invested", "FLOAT DEFAULT 0.0"),
                    ("current_value",  "FLOAT DEFAULT 0.0"),
                ]:
                    try:
                        conn.execute(
                            text(f"ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS {col} {coltype}")
                        )
                        conn.commit()
                    except Exception:
                        pass  # column already exists or DDL not supported
                # BotMetrics: add 'market' column for per-market metrics
                try:
                    conn.execute(
                        text("ALTER TABLE bot_metrics ADD COLUMN IF NOT EXISTS market VARCHAR DEFAULT 'binance'")
                    )
                    conn.commit()
                except Exception:
                    pass
                # Add is_sandbox column to all tables
                for table in ["trades", "portfolio", "bot_metrics"]:
                    try:
                        conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS is_sandbox BOOLEAN DEFAULT FALSE")
                        )
                        conn.commit()
                    except Exception:
                        pass

                # Create admin_settings table if missing
                try:
                    conn.execute(
                        text("CREATE TABLE IF NOT EXISTS admin_settings (id SERIAL PRIMARY KEY, key VARCHAR UNIQUE, value VARCHAR);")
                    )
                    conn.commit()
                except Exception:
                    pass
            _tables_initialized = True
        except Exception as e:
            print(f"Warning: Could not create tables: {e}")


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
