import re
from datetime import datetime
from backend.api import api_bp  

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return "Hello, Flask!"


@app.route('/browse')
def browse():
    items = [
        {
            'name': 'Blue Plaid Shirt',
            'category': 'tops',
            'image_url': '/static/images/shirt.jpg',
            'tags': ['casual', 'plaid']
        },
        # ... more items
    ]
    return render_template('browse.html', 
                         items=items, 
                         item_count=len(items))
app.register_blueprint(api_bp, url_prefix="/api/v1")
