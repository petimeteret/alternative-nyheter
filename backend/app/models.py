from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, JSON, Index
from datetime import datetime, timezone
from .db import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    feed_url = Column(String(1024), nullable=True)
    last_etag = Column(String(255), nullable=True)
    last_modified = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    enabled = Column(Integer, default=1)

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    url = Column(String(1024), nullable=False)
    url_canonical = Column(String(1024), nullable=False, index=True)
    source_domain = Column(String(255), index=True, nullable=False)
    source_name = Column(String(255), nullable=False)
    title = Column(String(1024), nullable=False)
    summary = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    language = Column(String(10), nullable=True)
    raw = Column(JSON, nullable=True)
    theme = Column(String(64), nullable=True)
    minhash_sig = Column(String(2048), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('url_canonical', name='uq_articles_urlcanon'),
        Index('ix_articles_pub_desc', 'published_at'),
        Index('ix_articles_search', 'title', 'summary'),  # For text search
        Index('ix_articles_filters', 'source_domain', 'theme', 'language'),  # For filtering
        Index('ix_articles_composite', 'published_at', 'source_domain'),  # For common queries
    )
