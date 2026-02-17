from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
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

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "completed": bool(self.completed),
            "deadline": getattr(self, "deadline", None),
            "priority": getattr(self, "priority", None),
        }

    def __repr__(self):
        return f"<Task {self.id}>"

# ---- Create database ----
with app.app_context():
    db.create_all()

# ---- Routes ----
@app.route("/")
def index():
    tasks = Task.query.order_by(Task.id.desc()).all()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add():
    task_content = request.form.get("content")

    if task_content and task_content.strip():
        new_task = Task(content=task_content.strip())
        db.session.add(new_task)
        db.session.commit()

    return redirect(url_for("index"))

@app.route("/complete/<int:id>")
def complete(id):
    task = Task.query.get_or_404(id)
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete/<int:id>")
def delete(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("index"))


# ---- JSON API endpoints ----
@app.route("/api/tasks", methods=["GET", "POST"])
def api_tasks():
    if request.method == "GET":
        tasks = Task.query.order_by(Task.id.desc()).all()
        return jsonify([t.to_dict() for t in tasks])

    # POST -> create new task via JSON
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    data = request.get_json()
    content = data.get("content")
    if not content or not content.strip():
        return jsonify({"error": "Content is required"}), 400

    new_task = Task(content=content.strip())
    # optional fields if model has them
    if "deadline" in data:
        try:
            new_task.deadline = data.get("deadline")
        except Exception:
            pass
    if "priority" in data:
        try:
            new_task.priority = int(data.get("priority"))
        except Exception:
            pass

    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201


@app.route("/api/tasks/<int:id>", methods=["GET", "PUT", "DELETE"])
def api_task(id):
    task = Task.query.get_or_404(id)

    if request.method == "GET":
        return jsonify(task.to_dict())

    if request.method == "DELETE":
        db.session.delete(task)
        db.session.commit()
        return jsonify({"result": "deleted"}), 200

    # PUT -> update
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    data = request.get_json()
    if "content" in data and data.get("content") and data.get("content").strip():
        task.content = data.get("content").strip()
    if "completed" in data:
        task.completed = bool(data.get("completed"))
    if "deadline" in data:
        task.deadline = data.get("deadline")
    if "priority" in data:
        try:
            task.priority = int(data.get("priority"))
        except Exception:
            pass

    db.session.commit()
    return jsonify(task.to_dict())

# ---- Run app ----
@app.route("/edit/<int:id>", methods=["POST"])
def edit(id):
    task = Task.query.get_or_404(id)
    new_content = request.form.get("content")

    if new_content and new_content.strip():
        task.content = new_content.strip()
        db.session.commit()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)