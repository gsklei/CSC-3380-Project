# dao.py
from __future__ import annotations
from typing import Optional, Protocol, Literal
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.orm import Session
from models import Item, ItemKind

SortKey = Literal["created_at", "updated_at", "name", "brand", "kind"]
SortDir = Literal["asc", "desc"]

class ItemDAO(Protocol):
    def create(self, *, user_id:int, kind:str, name:str|None=None, brand:str|None=None,
               image_url:str|None=None, main_color_hex:str|None=None, is_neutral:bool=False) -> Item: ...
    def get(self, item_id:int) -> Item | None: ...
    def update(self, item_id:int, **fields) -> Item: ...
    def delete(self, item_id:int) -> None: ...
    def list(self, *, user_id:int, kinds:list[str]|None=None, search:str|None=None,
             is_neutral:bool|None=None, color_hex:str|None=None,
             page:int=1, page_size:int=20, sort_by:SortKey="created_at", sort_dir:SortDir="desc") -> dict: ...

class SQLItemDAO(ItemDAO):
    """Works with either Flask's db.session or a plain SQLAlchemy Session."""
    def __init__(self, session: Session):
        self.s = session

    # ---- CRUD ----
    def create(self, *, user_id:int, kind:str, name:str|None=None, brand:str|None=None,
               image_url:str|None=None, main_color_hex:str|None=None, is_neutral:bool=False) -> Item:
        item = Item(
            user_id=user_id,
            kind=ItemKind(kind),
            name=name, brand=brand, image_url=image_url,
            main_color_hex=(f"#{main_color_hex.lstrip('#')}" if main_color_hex else None),
            is_neutral=1 if is_neutral else 0
        )
        self.s.add(item); self.s.commit()
        return item

    def get(self, item_id:int) -> Item | None:
        return self.s.get(Item, item_id)

    def update(self, item_id:int, **fields) -> Item:
        obj = self.s.get(Item, item_id)
        if not obj: raise ValueError("Item not found")
        for k, v in fields.items():
            if k == "kind" and v:
                obj.kind = ItemKind(v)
            elif k == "is_neutral" and v is not None:
                obj.is_neutral = 1 if v else 0
            elif k == "main_color_hex" and v:
                obj.main_color_hex = f"#{v.lstrip('#')}"
            else:
                setattr(obj, k, v)
        self.s.commit()
        return obj

    def delete(self, item_id:int) -> None:
        obj = self.s.get(Item, item_id)
        if not obj: return
        self.s.delete(obj); self.s.commit()

    # ---- Query with paging / filter / sort ----
    def list(self, *, user_id:int, kinds:list[str]|None=None, search:str|None=None,
             is_neutral:bool|None=None, color_hex:str|None=None,
             page:int=1, page_size:int=20, sort_by:SortKey="created_at", sort_dir:SortDir="desc") -> dict:
        stmt = select(Item).where(Item.user_id == user_id)

        if kinds:
            stmt = stmt.where(Item.kind.in_([ItemKind(k) for k in kinds]))
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Item.name.ilike(like), Item.brand.ilike(like)))
        if is_neutral is not None:
            stmt = stmt.where(Item.is_neutral == (1 if is_neutral else 0))
        if color_hex:
            short = color_hex.lstrip("#")[:3].lower()
            stmt = stmt.where(or_(
                Item.main_color_hex.ilike(f"%{color_hex.lstrip('#')}%"),
                Item.main_color_hex.ilike(f"%{short}%")
            ))

        sort_col = {
            "created_at": Item.created_at,
            "updated_at": Item.updated_at,
            "name": Item.name,
            "brand": Item.brand,
            "kind": Item.kind,
        }[sort_by]
        stmt = stmt.order_by(asc(sort_col) if sort_dir=="asc" else desc(sort_col))

        total = self.s.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        page = max(1, page); page_size = max(1, min(100, page_size))
        rows = self.s.execute(stmt.offset((page-1)*page_size).limit(page_size)).scalars().all()

        def to_dict(i: Item) -> dict:
            return {
                "id": i.id, "user_id": i.user_id, "kind": i.kind.value,
                "name": i.name, "brand": i.brand, "image_url": i.image_url,
                "main_color_hex": i.main_color_hex, "is_neutral": bool(i.is_neutral),
                "created_at": i.created_at.isoformat(), "updated_at": i.updated_at.isoformat(),
            }

        return {"items": [to_dict(r) for r in rows],
                "meta": {"page": page, "page_size": page_size, "total": total}}
