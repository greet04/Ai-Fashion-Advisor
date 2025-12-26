from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    current_user, login_required
)
import os
import google.generativeai as genai
from werkzeug.utils import secure_filename

# -------------------- Flask Setup --------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fashion_users.db'
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------- Database Setup --------------------
db = SQLAlchemy(app)

# -------------------- Login Setup --------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# -------------------- User Model --------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    height = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    skin_color = db.Column(db.String(20))
    body_shape = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Routes --------------------

@app.route("/")
def home():
    """Redirect to dashboard if logged in."""
    if current_user.is_authenticated:
        return render_template("index.html", name=current_user.name)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """User Registration"""
    if request.method == "POST":
        data = request.form
        new_user = User(
            name=data['name'],
            email=data['email'],
            password=data['password'],
            height=data['height'],
            weight=data['weight'],
            skin_color=data['skin_color'],
            body_shape=data['body_shape'],
            gender=data['gender'],
            age=data['age']
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User Login"""
    if request.method == "POST":
        data = request.form
        user = User.query.filter_by(email=data['email'], password=data['password']).first()
        if user:
            login_user(user)
            return redirect(url_for("home"))
        return "Invalid credentials. Please try again."
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for("login"))


# -------------------- Fashion Advisor AI --------------------

@app.route("/fashion-advisor", methods=["POST"])
@login_required
def fashion_advisor():
    """AI-based fashion recommendations"""
    user = current_user
    query = request.form.get("query", "")
    image = request.files.get("image")

    # Handle image upload
    image_url = None
    image_path = None
    if image:
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        image_url = f"/{image_path}"

    # Full AI system prompt with styling instructions
    user_prompt = f"""
    You are a professional fashion advisor. Keep responses simple and stylish, 
    and highly personalized based on the user's profile and query. 
    Your response will be rendered on HTML, so provide accordingly. 
    Consider the gender and age too. 
    Make the height of the main container cover the full screen height.
    Remove '''html. Just provide the code, no need to write language name.

    User Profile:
    - Name: {user.name}
    - Gender: {user.gender}
    - Age: {user.age}
    - Height: {user.height} cm
    - Weight: {user.weight} kg
    - Skin tone: {user.skin_color}
    - Body shape: {user.body_shape}

    User query or uploaded clothing image: {query}
    Give clear outfit or accessory suggestions that match this style.
    """

    # Gemini AI setup
    API_KEY = os.environ.get("GEMINI_API_KEY", "")
    genai.configure(api_key=API_KEY)

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        if image_path:
            with open(image_path, "rb") as img_file:
                response = model.generate_content([
                    "You are a professional fashion stylist. Analyze this clothing image and suggest matching outfits or accessories. Keep the tone stylish, simple, and HTML-renderable.",
                    {"mime_type": "image/jpeg", "data": img_file.read()}
                ])
        else:
            response = model.generate_content(user_prompt)

        bot_reply = response.text.strip()

    except Exception as e:
        print("Gemini API Error:", e)
        bot_reply = "Sorry, the fashion advisor is temporarily unavailable."

    # Shopping links
    amazon = f"https://www.amazon.in/s?k={query}+outfit"
    flipkart = f"https://www.flipkart.com/search?q={query}+outfit"
    pinterest = f"https://in.pinterest.com/search/pins/?q={query}+outfit"

    return jsonify({
        "reply": bot_reply,
        "image": image_url,
        "amazon": amazon,
        "flipkart": flipkart,
        "pinterest": pinterest
    })


# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(debug=True)

