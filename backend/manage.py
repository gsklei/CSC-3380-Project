from db import init_db, SessionLocal
from models import ClothingItem

def seed():
    db = SessionLocal()
    demo = [
        ("seed_top.jpg", "top", "blue"),
        ("seed_bottom.jpg", "bottom", "black"),
        ("seed_shoes.jpg", "shoes", "white"),
    ]
    for fname, cat, clr in demo:
        db.add(ClothingItem(filename=fname, category=cat, color=clr))
    db.commit()
    db.close()

if __name__ == "__main__":
    init_db()
    # seed()  # ← uncomment once if you want demo rows
    print("DB ready.")
