from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field

class Mention(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    termo: str
    titulo: str
    url: str
    trecho: str
    canal: str
    sentimento: str
    tags_csv: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None  

    @property
    def tags(self) -> List[str]:
        return [t for t in self.tags_csv.split(",") if t.strip()] if self.tags_csv else []

    def set_tags(self, tags: List[str]):
        self.tags_csv = ",".join(sorted(set([t.strip() for t in tags if t.strip()])))
