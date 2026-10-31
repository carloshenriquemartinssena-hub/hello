import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .tls import postgres_connect_options


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "crm2_leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    place_id: Mapped[str | None] = mapped_column(String(250), unique=True, nullable=True)
    city: Mapped[str] = mapped_column(String(160), default="")
    niche: Mapped[str] = mapped_column(String(120), default="")
    reviews: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[str] = mapped_column(String(10), default="")
    instagram: Mapped[str] = mapped_column(String(500), default="")
    facebook: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="novo", index=True)
    stage: Mapped[int] = mapped_column(Integer, default=-1)
    first_sent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    next_send: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Config(Base):
    __tablename__ = "crm2_config"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class Dispatch(Base):
    __tablename__ = "crm2_dispatches"
    __table_args__ = (UniqueConstraint("lead_id", "stage"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("crm2_leads.id"), index=True)
    stage: Mapped[int] = mapped_column(Integer)
    day: Mapped[str] = mapped_column(String(10), index=True)
    state: Mapped[str] = mapped_column(String(30), default="reservado")
    message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Suppression(Base):
    __tablename__ = "crm2_suppressions"
    email: Mapped[str] = mapped_column(String(254), primary_key=True)
    reason: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Activity(Base):
    __tablename__ = "crm2_activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=utcnow)


class Attachment(Base):
    __tablename__ = "crm2_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    inline: Mapped[bool] = mapped_column(Boolean, default=False)


class Lease(Base):
    __tablename__ = "crm2_lease"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(40), default="")
    expires: Mapped[str] = mapped_column(String(40), default="")


def connect(url=None):
    url = url or os.getenv("CRM_DATABASE_URL", "sqlite:///data/crm2.db")
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    if os.getenv("CRM_ENV") == "production":
        parsed = make_url(url)
        if parsed.drivername != "postgresql+psycopg" or parsed.query.get("sslmode") != "verify-full":
            raise RuntimeError("Produção requer PostgreSQL exclusivo e sslmode=verify-full")
    if url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)
    engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else postgres_connect_options())
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def pragmas(conn, _):
            # Transações explícitas também cobrem SAVEPOINT; o modo legado do
            # sqlite3 pode confirmar o primeiro savepoint antes do commit externo.
            conn.isolation_level = None
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
        @event.listens_for(engine, 'begin')
        def begin_transaction(conn):
            conn.exec_driver_sql('BEGIN')
    if url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    try:
        with sessions.begin() as s:
            if not s.get(Lease, 1):
                s.add(Lease(id=1, owner="", expires=""))
    except Exception:
        engine.dispose()
        raise
    return engine, sessions
