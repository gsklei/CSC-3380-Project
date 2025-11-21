from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ClothingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_filename = db.Column(db.String(200), nullable=False)
    tags = db.Column(db.String(200))  # optional, comma-separated