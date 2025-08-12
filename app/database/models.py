from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import String, JSON, BIGINT, ForeignKey

# Инициализация движка и сессии
engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# Базовый класс моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass

# Модель пользователя
class User(Base):
    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BIGINT)
    settings: Mapped[dict] = mapped_column(JSON, nullable=True)
    tweets: Mapped[dict] = mapped_column(JSON, nullable=True)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")

# Модель аккаунта (например, Twitter-аккаунт)
class Account(Base):
    __tablename__ = 'accounts'

    nickname: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    proxy: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)  # TOTP-секрет

    session: Mapped[dict] = mapped_column(JSON, nullable=True)  # Сессионные данные
    user_agent: Mapped[str] = mapped_column(String, nullable=True)  # Имитация fingerprint'а

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    user = relationship("User", back_populates="accounts")

# Инициализация базы
async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)