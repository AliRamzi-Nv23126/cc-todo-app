from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# ---- Database configuration ----
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "tasks.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev"  # prevents some Flask warnings

db = SQLAlchemy(app)

# ---- Task Model ----
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Task {self.id}>"

# ---- Create database ----
with app.app_context():
    db.create_all()


# ---- Simple auth helpers ----
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    return wrapper

# ---- Routes ----
@app.route("/")
def index():
    tasks = Task.query.order_by(Task.id.desc()).all()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
@login_required
def add():
    task_content = request.form.get("content")

    if task_content and task_content.strip():
        new_task = Task(content=task_content.strip())
        db.session.add(new_task)
        db.session.commit()

    return redirect(url_for("index"))

@app.route("/complete/<int:id>")
@login_required
def complete(id):
    task = Task.query.get_or_404(id)
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))

# ---- Run app ----
@app.route("/edit/<int:id>", methods=["POST"])
@login_required
def edit(id):
    task = Task.query.get_or_404(id)
    new_content = request.form.get("content")

    if new_content and new_content.strip():
        task.content = new_content.strip()
        db.session.commit()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)


# ---- Auth routes ----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        expected_user = os.environ.get("TODO_USER", "admin")
        expected_pass = os.environ.get("TODO_PASS", "password")

        if username == expected_user and password == expected_pass:
            session["user"] = username
            flash("Logged in successfully", "success")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)

        flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))