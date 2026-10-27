import os, re, sqlite3
from datetime import date
from functools import wraps
from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
DB_PATH = os.environ.get("DB_PATH") or ("/tmp/lostfound.db" if os.environ.get("K_SERVICE") else "lostfound.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS items(
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
  what TEXT NOT NULL, place TEXT NOT NULL, found_on TEXT NOT NULL,
  photo_url TEXT, returned INTEGER NOT NULL DEFAULT 0);
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed(con)
    con.commit(); con.close()

def seed(con):
    for name in ("maya", "jordan", "sam"):
        con.execute("INSERT INTO users(username, pw) VALUES(?,?)",
                    (name, generate_password_hash("password123")))
    img = lambda s: f"https://picsum.photos/seed/{s}/300/200"
    rows = [
        (1, "Blue water bottle", "Library, 2nd floor", "2026-10-20", img("bottle"), 0),
        (1, "Black umbrella", "Engineering Hall lobby", "2026-10-18", img("umbrella"), 1),
        (2, "Student ID card", "Cafeteria", "2026-10-22", "", 0),
        (2, "Silver laptop charger", "Room B105", "2026-10-21", img("charger"), 0),
        (3, "Green backpack", "Gym entrance", "2026-10-19", img("backpack"), 0),
        (3, "Prescription glasses", "Bus stop on Main St", "2026-10-15", img("glasses"), 1),
        (1, "Set of keys with red tag", "Parking lot C", "2026-10-24", img("keys"), 0),
        (2, "Wireless earbuds", "Student center", "2026-10-25", img("earbuds"), 0),
    ]
    con.executemany("INSERT INTO items(user_id,what,place,found_on,photo_url,returned)"
                    " VALUES(?,?,?,?,?,?)", rows)

def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if "user_id" not in session:
            flash("Log in to do that.", "error")
            return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return wrap

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    unclaimed = request.args.get("unclaimed") == "1"
    sql = "SELECT items.*, username FROM items JOIN users ON users.id = user_id WHERE 1=1"
    args = []
    if q:
        sql += " AND (what LIKE ? OR place LIKE ?)"
        args += [f"%{q}%"] * 2
    if unclaimed:
        sql += " AND returned = 0"
    items = db().execute(sql + " ORDER BY found_on DESC, id DESC", args).fetchall()
    return render_template("index.html", items=items, q=q, unclaimed=unclaimed)

def credentials():
    return request.form.get("username", "").strip().lower(), request.form.get("password", "")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u, p = credentials()
        if not re.fullmatch(r"[a-z0-9_]{3,20}", u):
            flash("Username must be 3-20 letters, digits or underscores.", "error")
        elif len(p) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif db().execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone():
            flash("That username is taken. Pick another.", "error")
        else:
            cur = db().execute("INSERT INTO users(username,pw) VALUES(?,?)",
                               (u, generate_password_hash(p)))
            db().commit()
            session.update(user_id=cur.lastrowid, username=u)
            flash("Welcome! Your account is ready.", "ok")
            return redirect(url_for("index"))
    return render_template("auth.html", title="Register", button="Create account")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u, p = credentials()
        row = db().execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if row and check_password_hash(row["pw"], p):
            session.update(user_id=row["id"], username=row["username"])
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
        flash("Wrong username or password.", "error")
    return render_template("auth.html", title="Log in", button="Log in")

@app.route("/logout")
def logout():
    session.clear()
    flash("You are logged out.", "ok")
    return redirect(url_for("index"))

@app.route("/items/new", methods=["GET", "POST"])
@login_required
def new_item():
    f = {k: request.form.get(k, "").strip() for k in ("what", "place", "found_on", "photo_url")}
    if request.method == "POST":
        err = None
        try:
            date.fromisoformat(f["found_on"])
        except ValueError:
            err = "Enter the date found as YYYY-MM-DD."
        if not f["what"] or not f["place"]:
            err = "Describe what you found and where."
        elif f["photo_url"] and not f["photo_url"].startswith(("http://", "https://")):
            err = "The photo URL must start with http:// or https://."
        if err:
            flash(err, "error")
        else:
            db().execute("INSERT INTO items(user_id,what,place,found_on,photo_url)"
                         " VALUES(?,?,?,?,?)",
                         (session["user_id"], f["what"], f["place"], f["found_on"], f["photo_url"]))
            db().commit()
            flash("Item posted.", "ok")
            return redirect(url_for("index"))
    f["found_on"] = f["found_on"] or date.today().isoformat()
    return render_template("new.html", f=f)

@app.route("/items/<int:item_id>/return", methods=["POST"])
@login_required
def mark_returned(item_id):
    item = db().execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        abort(404)
    if item["user_id"] != session["user_id"]:
        abort(403)
    db().execute("UPDATE items SET returned=1 WHERE id=?", (item_id,))
    db().commit()
    flash("Marked as returned.", "ok")
    return redirect(request.referrer or url_for("index"))

@app.route("/u/<username>")
def user_page(username):
    user = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        abort(404)
    items = db().execute("SELECT items.*, username FROM items JOIN users ON users.id=user_id"
                         " WHERE user_id=? ORDER BY found_on DESC", (user["id"],)).fetchall()
    return render_template("user.html", items=items, owner=username)

MSG = {403: "You can only change your own posts.", 404: "We couldn't find that page or item.",
       500: "Something went wrong on our side. Try again in a moment."}
for code in MSG:
    app.register_error_handler(code, lambda e, c=code: (render_template("error.html", msg=MSG[c]), c))

init_db()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
