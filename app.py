from flask import Flask, render_template, send_from_directory, url_for, redirect, request, flash
from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField, StringField
from models import db, ClothingItem
import os
import json


app = Flask(__name__)
app.config['SECRET_KEY']= 'asklsh'
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///closet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

# --- Form for uploads ---
class UploadForm(FlaskForm):
    name = StringField("Item Name")
    category = SelectField(
        "Category", 
        choices=[("tops","Tops"), ("bottoms","Bottoms"), ("shoes","Shoes"), ("accessories","Accessories")]
    )
    tags = StringField("Tags (comma separated)")
    photo = FileField(
        validators=[
            FileAllowed(photos, 'Only images are allowed'),
            FileRequired('File field should not be empty')
        ]
    )
    submit = SubmitField("Upload")

# --- Route to serve uploaded files ---
@app.route('/uploads/<filename>')
def get_file(filename):    
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

# --- Upload route ---
@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
    form = UploadForm()
    if form.validate_on_submit():
        filename = photos.save(form.photo.data)
        tags_list = [t.strip() for t in form.tags.data.split(',')] if form.tags.data else []
        new_item = ClothingItem(
            name=form.name.data,
            category=form.category.data,
            image_filename=filename,
            tags=json.dumps(tags_list)
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('browse'))
    return render_template('upload.html', form=form)

# --- Browse route ---
@app.route('/')
def browse():
    form = UploadForm() 
    items = ClothingItem.query.all()
    # Build URL for images
    for item in items:
        item.image_url = url_for('get_file', filename=item.image_filename)
        try:
           item.tags_list = json.loads(item.tags) if item.tags else []
        except json.JSONDecodeError:
            item.tags_list = []

    return render_template(
        'browse.html',
        items=items,
        item_count=len(items),
        form=form
    )

# --- Delete Upload ---
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = ClothingItem.query.get_or_404(item_id)
    try:
        # Delete image file from uploads folder
        import os
        image_path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], item.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        # Delete the item from the database
        db.session.delete(item)
        db.session.commit()
        flash(f"{item.name} has been deleted.", "success")
    except Exception as e:
        flash("Error deleting item.", "danger")
        print(e)
    return redirect(url_for('browse'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # create tables if they don't exist
    app.run(debug=True)