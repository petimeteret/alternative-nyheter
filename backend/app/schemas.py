from pydantic import BaseModel
from datetime import datetime

class ArticleOut(BaseModel):
    id: int
    title: str
    summary: str | None
    author: str | None
    published_at: datetime | None
    source_name: str
    source_url: str
    article_url: str
    language: str | None
    theme: str | None

    class Config:
        from_attributes = True

class Paginated(BaseModel):
    items: list[ArticleOut]
    total: int
    page: int
    page_size: int
