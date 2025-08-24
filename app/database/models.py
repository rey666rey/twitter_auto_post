from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import String, BigInteger, ForeignKey
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# Базовый класс моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass


# Модель пользователя
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Можно UUID
    tg_id: Mapped[int] = mapped_column(BigInteger)
    settings: Mapped[dict] = mapped_column(JSON, nullable=True)
    tweets: Mapped[dict] = mapped_column(JSON, nullable=True)
    communities: Mapped[list] = mapped_column(JSON, nullable=True)

    accounts = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# Модель аккаунта
class Account(Base):
    __tablename__ = "accounts"

    nickname: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    proxy: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)  # TOTP-секрет

    session: Mapped[dict] = mapped_column(JSON, nullable=True)
    user_agent: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    user = relationship("User", back_populates="accounts")


# Инициализация базы
async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
