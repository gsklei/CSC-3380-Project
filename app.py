import os
import json
from urllib.parse import urlparse
from models import ClothingItem
import random
from flask import (
    Flask, render_template, send_from_directory,
    url_for, redirect, request, flash
)
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField, StringField
from flask_login import (
    LoginManager, login_user, logout_user,
    current_user, login_required
)
from werkzeug.utils import secure_filename

from forms import LoginForm, RegistrationForm
from models import db, ClothingItem, User


app = Flask(__name__)
app.config["SECRET_KEY"] = "asklsh"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///closet.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
# ------------------------------


db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = None


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Form for uploads ---
class UploadForm(FlaskForm):
    name = StringField("Item Name")
    category = SelectField(
        "Category",
        choices=[
            ("tops", "Tops"),
            ("bottoms", "Bottoms"),
            ("shoes", "Shoes"),
            ("accessories", "Accessories"),
        ],
    )
    tags = StringField("Tags (comma separated)")
    photo = FileField(
        validators=[
            FileRequired("File field should not be empty"),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Only images are allowed"),
        ]
    )
    submit = SubmitField("Upload")


# --- Route to serve uploaded files ---
@app.route("/uploads/<filename>")
def get_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# --- Upload route ---
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_image():
    form = UploadForm()
    if form.validate_on_submit():
        file = form.photo.data

        # secure + save filename
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        # Process tags into a list
        tags_list = (
            [t.strip() for t in form.tags.data.split(",")] if form.tags.data else []
        )

        # Create a new ClothingItem linked to the current user
        new_item = ClothingItem(
            name=form.name.data,
            category=form.category.data,
            image_filename=filename,
            tags=json.dumps(tags_list),
            user_id=current_user.id,
        )

        db.session.add(new_item)
        db.session.commit()

        return redirect(url_for("browse"))

    return render_template("upload.html", form=form)


# --- Browse route ---
@app.route("/")
@login_required
def browse():
    form = UploadForm()
    items = ClothingItem.query.filter_by(user_id=current_user.id).all()

    # Build URL for images
    for item in items:
        item.image_url = url_for("get_file", filename=item.image_filename)
        try:
            item.tags_list = json.loads(item.tags) if item.tags else []
        except json.JSONDecodeError:
            item.tags_list = []

    return render_template(
        "browse.html",
        items=items,
        item_count=len(items),
        form=form,
    )


# --- Delete Upload ---
@app.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    item = ClothingItem.query.get_or_404(item_id)

    # ensure ownership
    if item.user_id != current_user.id:
        flash("You can only delete your own items.", "danger")
        return redirect(url_for("browse"))

    try:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], item.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        db.session.delete(item)
        db.session.commit()
        flash(f"{item.name} has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting item.", "danger")
        print(e)

    return redirect(url_for("browse"))

@app.route("/generate-outfit")
@login_required
def generate_outfit():
    def pick_one(cat):
        items = ClothingItem.query.filter_by(
            user_id=current_user.id,
            category=cat
        ).all()
        return random.choice(items) if items else None

    top = pick_one("tops")
    bottom = pick_one("bottoms")
    shoes = pick_one("shoes")

    if not (top and bottom and shoes):
        flash("You need at least one top, bottom, and pair of shoes to generate an outfit.", "warning")
        return redirect(url_for("browse"))

    # reuse browse.html but pass a special outfit
    outfit = [top, bottom, shoes]
    for item in outfit:
        item.image_url = url_for("get_file", filename=item.image_filename)

    return render_template(
        "browse.html",
        items=outfit,
        item_count=len(outfit),
        form=UploadForm(),      
        generated=True         
    )
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("browse"))

    form = LoginForm()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        login_user(user)

        next_page = request.args.get("next")
        if not next_page or urlparse(next_page).netloc != "":
            next_page = url_for("browse")

        return redirect(next_page)

    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("browse"))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("browse"))

    return render_template("register.html", form=form)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
