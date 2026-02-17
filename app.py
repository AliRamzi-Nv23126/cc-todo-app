import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ---- Configuration ----
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "tasks.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

db = SQLAlchemy(app)

# ---- Models ----
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default="medium")  # low, medium, high
    due_date = db.Column(db.DateTime, nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.id}>"
    
    def is_overdue(self):
        if not self.due_date or self.completed:
            return False
        return self.due_date < datetime.utcnow()
    
    def is_today(self):
        if not self.due_date:
            return False
        today = datetime.utcnow().date()
        return self.due_date.date() == today
    
    def is_this_week(self):
        if not self.due_date:
            return False
        today = datetime.utcnow()
        week_end = today + timedelta(days=7)
        return today <= self.due_date <= week_end

# Create database
with app.app_context():
    db.create_all()

# ---- Auth Helpers ----
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            # This was failing because 'login' wasn't registered yet
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

# ---- Routes ----
@app.route("/")
def index():
    # Get filter and sort parameters
    status_filter = request.args.get("status", "all")  # all, pending, completed
    priority_filter = request.args.get("priority", "all")
    due_date_filter = request.args.get("due_date", "all")  # all, overdue, today, this_week
    sort_by = request.args.get("sort", "created_date_desc")  # created_date_asc, created_date_desc, due_date_asc, priority
    
    # Start with base query
    query = Task.query
    
    # Apply status filter
    if status_filter == "pending":
        query = query.filter_by(completed=False)
    elif status_filter == "completed":
        query = query.filter_by(completed=True)
    
    # Apply priority filter
    if priority_filter != "all":
        query = query.filter_by(priority=priority_filter)
    
    # Apply due date filter
    if due_date_filter != "all":
        today = datetime.utcnow()
        if due_date_filter == "overdue":
            query = query.filter(Task.due_date < today, Task.completed == False)
        elif due_date_filter == "today":
            query = query.filter(Task.due_date >= today.replace(hour=0, minute=0, second=0, microsecond=0),
                                Task.due_date < today.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        elif due_date_filter == "this_week":
            week_end = today + timedelta(days=7)
            query = query.filter(Task.due_date >= today, Task.due_date <= week_end)
    
    # Apply sorting
    if sort_by == "created_date_asc":
        query = query.order_by(Task.created_date.asc())
    elif sort_by == "created_date_desc":
        query = query.order_by(Task.created_date.desc())
    elif sort_by == "due_date_asc":
        query = query.order_by(Task.due_date.asc().nullslast())
    elif sort_by == "priority":
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks = query.all()
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 3), t.created_date), reverse=True)
        return render_template("index.html", tasks=tasks, status_filter=status_filter, 
                             priority_filter=priority_filter, due_date_filter=due_date_filter, sort_by=sort_by)
    else:
        query = query.order_by(Task.created_date.desc())
    
    tasks = query.all()
    return render_template("index.html", tasks=tasks, status_filter=status_filter, 
                         priority_filter=priority_filter, due_date_filter=due_date_filter, sort_by=sort_by)

@app.route("/add", methods=["POST"])
@login_required
def add():
    task_content = request.form.get("content")
    priority = request.form.get("priority", "medium")
    due_date_str = request.form.get("due_date")
    
    if task_content and task_content.strip():
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
            except:
                pass
        
        new_task = Task(content=task_content.strip(), priority=priority, due_date=due_date)
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

@app.route("/edit/<int:id>", methods=["POST"])
@login_required
def edit(id):
    task = Task.query.get_or_404(id)
    new_content = request.form.get("content")
    priority = request.form.get("priority")
    due_date_str = request.form.get("due_date")
    
    if new_content and new_content.strip():
        task.content = new_content.strip()
    
    if priority:
        task.priority = priority
    
    if due_date_str:
        try:
            task.due_date = datetime.fromisoformat(due_date_str)
        except:
            pass
    elif due_date_str == "":
        task.due_date = None
    
    db.session.commit()
    return redirect(url_for("index"))

# ---- Auth Routes (Moved above the run block) ----
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

# ---- Run App (ALWAYS AT THE BOTTOM) ----
if __name__ == "__main__":
    app.run(debug=True)