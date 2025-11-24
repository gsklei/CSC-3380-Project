from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id        = Column(Integer, primary_key=True, index=True)
    filename  = Column(String, nullable=False)
    category  = Column(String, nullable=False, index=True)
    color     = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
