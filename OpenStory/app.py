
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import hashlib
import random
import string
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "openstory_secret_key_2024"

DB_PATH = os.path.join(os.path.dirname(__file__), "openstory.db")


#------------------------------------------------
# DATABASE SETUP
#------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    UNIQUE NOT NULL,
            email        TEXT    UNIQUE NOT NULL,
            password     TEXT    NOT NULL,
            phone        TEXT,
            role         TEXT    NOT NULL DEFAULT 'member', -- 'member' or 'librarian'
            librarian_code TEXT,
            member_since TEXT    NOT NULL,
            active       INTEGER NOT NULL DEFAULT 1  
        );
        
        CREATE TABLE IF NOT EXISTS resources (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,     
            author       TEXT    NOT NULL,
            isbn         TEXT,
            type         TEXT    NOT NULL, -- 'book','ebook','audiobook','journal'
            total_copies INTEGER NOT NULL DEFAULT 1,
            available    INTEGER NOT NULL DEFAULT 1,
            file_path    TEXT,
            description  TEXT,
            added_on     TEXT    NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS borrowingS (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id),
            resource_id  INTEGER NOT NULL REFERENCES resources(id),
            borrow_date  TEXT    NOT NULL,
            due_date     TEXT    NOT NULL,
            return_date  TEXT,
            status       TEXT    NOT NULL DEFAULT 'borrowed', -- 'borrowed', 'returned', 'overdue'
            fine_amount  REAL    NOT NULL DEFAULT  0.0 
        );

        CREATE TABLE IF NOT EXISTS study groups (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            description  TEXT,
            created_by   INTEGER NOT NULL REFERENCES user(id),
            created_on   TEXT    NOT NULL,
            ACTIVE       INTEGER NOT NULL DEFAULT 1    
        );

        CREATE TABLE IF NOT EXISTS group members (
            group_id     INTEGER NOT NULL REFERENCES study_groups(id),
            user_id      INTEGER NOT NULL REFERENCES users(id),
            joined_on    TEXT    NOT NULL,
            PRIMARY KEY  (group_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS group messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id     INTEGER NOT NULL REFERENCES study_groups(id),
            user_id      INTEGER NOT NULL REFERENCES users(id),
            message      TEXT    NOT NULL,
            sent_at      TEXT    NOT NULL    
        );

        CREATE TABLE IF NOT EXISTS group_tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id     INTEGER NOT NULL REFERENCES study_groups(id),
            title        TEXT     NOT NULL,
            assigned to  TEXT,
            due_date     TEXT,
            status       TEXT     NOT NULL DEFAULT 'pending' -- 'pending', 'in-progress', 'completed'
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id),
            librarian_id INTEGER REFERENCES users(id),
            message      TEXT    NOT NULL,
            sender_role  TEXT    NOT NULL, -- 'member' or 'librarian'
            sent_at      TEXT    NOT NULL,
            is_read      INTEGER NOT NULL DEFAULT 0  
        );

        CREATE TABLE IF NOT EXISTS mfa_codes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT    NOT NULL,
            code         TEXT    NOT NULL,
            created_at   TEXT    NOT NULL,
            USED         INTEGER NOT NULL DEFAULT 0
        ); 
    """)

    #--Seed data--
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        def ph(p): return hashlib.sha256(p.encode()).hexdigest()

        users = [
            ("SushilSharma14", "Sushilsharma14@gmail.com", ph("password123"), "+64 02289763546",
             "member", None, "2023-02-20"),
            ("LibrarianVicky", "vicky@openstory.lib", ph("lib2024"), None,
             "librarian", "LIB001", "2022-01-10"),
            ("MangusK",        "mangus@gmail.com",   ph("pass456"), None,
             "member", None, "2023-05-01"),
            ("GursimranT", "gursimran@gmail.com", ph("pass789"), None,
             "member", None, "2023-07-15"),
        ]
        cur.executemany(
            "INSERT INTO users(username,email,password,phone,role,librarian_code,member_since) VALUES(?,?,?,?,?,?,?)"
            users
        )

        resources = [
            ("The Shining",            "Stephen King",        "849-7-593-804",    "book",         5, 3, None,  "2024-01-01"),
            ("Cat in the Hat",          "Dr. Seuss",          "978-0394800011",   "book",         5, 5, None,  "2024-01-01"),
            ("Where's Wally",           "Martian Handford",   "9781406313185",    "book",         5, 2, None,  "2024-01-01"),
            ("Not In Love",             "Ali Hazelwood",      "9781408728901",    "ebook",       10,10, None,  "2024-01-01"),
            ("Joker",                   "DC Comics",          "978-1401215811",   "ebook",       10, 8, None,  "2024-01-01"),
            ("Scooby-Doo",              "DC Comics",          "9783741637490",    "ebook",       10, 6, None,  "2024-01-01"),
            ("IT",                      "Stephen King",       "9781444707861",    "audiobook",    5, 5, None,  "2024-01-01"),
            ("Ritual",                  "Dimitris Xygalatas", "978-0316462402",   "audiobook",    5, 3, None,  "2024-01-01"),
            ("Diary of a Wimpy Kid"     "Jeff Kinney",        "978-0141324906",   "audioook",     5, 4, None,  "2024-01-01"),
            ("Dangers of AI",           "Constantin Jitaru",  "N/A",              "journal",     10, 3, None,  "2024-01-01"),
            ("What Is UFO?",            "Akash B",            "N/A",              "journal",     10, 8, None,  "2024-01-01"),
            ("Conspiracy Theories",     "Andrea Vranic",      "N/A",              "journal",     10, 8, None,  "2024-01-01"),
            ("Isolation Islands",       "James Cooper",       "978-0000000001",   "book",         3, 2, None,  "2024-01-01"),
            ("Machine Learning",        "Tom Mitchell",       "978-0070428072",   "ebook",       10, 7, None,  "2024-01-01"), 
        ]
        cur.executemany(
            "INSERT INTO resources(itle,author,isbn,type,total_copies,available,file_path,added_on) VALUES(?,?,?,?,?,?,?)"
            resources
        )

        today = datetime.now()
        borrowings = [
            (1, 1, "2024-03-15", "2024-03-22", None,        "borrowed", 0.0),
            (3, 2, "2024-03-10", "2024-03-04", None,        "overdue",  2.50),
            (4, 10, "2024-03-05","2024-03-05", "2024-03-18", "returned"  0.0),
        ]
        cur.executemany(
            "INSERT INTO borrowings(user_id,resource_id,borrow_date,due_date,return_date,status,fine_amount)VALUES(?,?,?,?,?,?,?)"
            borrowings
        )
        cur.execute(
            "INSERT INTO study_groups(name,description,create_on) VALUES(?,?,?,?)",
            ("Computer Science Study Group", "Collaborative Learning for CS students", 1, "2024-02-01")
        )
        cur.executemany(
            "INSERT INTO group_members(group_id,user_id,joined_on) VALUES(?,?,?)",
            [(1,1,"2024-02-01"),(1,3,"2024-02-02"),(1,4,"2024-02-03")]
        )
        msgs = [
            (1,4,"Hey everyone! i found great resources on binary trees. Sharing in the files section","2024-03-10 15:30:00"),
            (1,3,"Thanks bro That's exactly what i needed for the assignment.","2024-03-10 15:35:00"),
            (1,1,"lets do a meeting to discuss the project","2024-03-10 15:40:00"),
        ]
        cur.executemany(
            "INSERT INTO group_messages(group_id,message,sent_at) VALUES(?,?,?,?)",
            msgs
        )
        tasks = [
            (1,"Complete Chapter 5 Reading","Kartik & Navneet",None, "pending"),
            (1,"Group Project Presentation","Gursimern","2024-03-25","in-progress"),
            (1,"Review Alogorithm problems","Magnus",None,"completed"),
        ]
        cur.executemany(
            "INSERT INTO group_tasks(group_id,title,assigned_to,due_date,status) VALUES(?,?,?,?,?)",
            tasks
        )
        chat_msgs = [
            (1,2,"Hello Welcome to Open Story Library support. How can I help you today?","librarian","2024-03-10 14:30:00",1),
            (1,2,"Hi I'm looking for books on machine learning. Can you recommend some resources","member","2024-03-10 14:31:00",1),
            (1,2,"Great question! we have several excellent resources on machin learning: Machine Learnig by Tom Mitchell (ebook available), Pattern Recognition (physical copy). Would you like me to place any of these on hold for you?","librarian","2024-03-10 14:32:00",1),
        ]
        cur.executemany(
            "INSERT INTO chat_messages(user_id,librarian_id,message,sender_role,sent_at,is_read) VALUES(?,?,?,?,?,?)",
            chat_msgs
        )

    conn.commit()
    conn.close()


#----------------------------------------------
# HELPERS
#----------------------------------------------

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def librarian_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "librarian":
            flash("Librarian access required.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_stats():
    conn = get_db()
    stats = {
        "total_resources": conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        "active_members":  conn.execute("SELECT COUNT(*) FROM users WHERE role='member' AND active=1").fetchone()[0],
        "active_borrowings": conn.execute("SELECT COUNT(*) FROM borrowings WHERE status='borrowed'").fetchone()[0],
        "overdue_items":  conn.execute("SELECT COUNT(* FROM borrowings WHERE status='overdue'").fetchone()[0],
        "pending_chats":  conn.execute("SELECT COUNT(*) FROM chat_messages WHERE is_read=0 AND sender_role='member'").fetchone()[0],
        "study_groups":   conn.execute("SELECT COUNT(*) FROM study_groups WHERE active=1").fetchone()[0],
        "outstanding_fines": conn.execute("SELECT COALESCE(SUM(fine_amount),0) FROM borrowings WHERE fine_amount>0 AND status!='returned'").fetchone()[0],
        "physical_books": conn.execute("SELECT COUNT(*) FROM resources WHERE type='book'").fetchone()[0],
        "ebooks":         conn.execute("SELECT COUNT(*) FROM rescoures WHERE type='ebook'").fetchone()[0],
        "audiobooks":     conn.execute("SELECT COUNT(*) FORM resources WHERE type='audiobook'").fetchone()[0],
        "journals":       conn.execute("SELECT COUNT(8) FROM resources WHERE type='journal'").fetchone()[0],   
    }
    conn.close()
    return stats


#----------------------------------------------
#AUTH ROUTES
#----------------------------------------------

@app.route("/", methods=("GET"))
def index():
    if "user_id" in session:
        if session.get("role") == "librarian":
            return redirect(url_for("librarian_dashboard"))
        return redirect(url_for("member_home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        is_librarian = request.form.get("is_librarian_code", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM user WHERE (username=? OR email=?) and active=1",
        (username, username)
        ).fetchone()
        conn.close()

        if not user or user["password"] != hash_password(password):
            flash("Incorrect username or password.", "error")
            return render_template("login.html", username=username)
        
        if is_librarian:
            if user["role"] != "librarian" or user["librarian_code"] != librarian_code:
                flash("Invalid librarian code.", "error")
                return render_template("login.html", username=username)
            
        # MFA - store a code and rediret to verify
        code = "".join(random.choices(string.digits, k=4))
        conn = get_db()
        conn.execute(
            "INSERT INTO mfa_codes(email,code,created_at) VALUES(?,?,?)",
            (user["email"], code, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        session["pending_user_id"] = user["id"]
        session["pending_role"] = user["role"]
        session["mfa_code"] = code          # In production: send via email
        session["mfa_email"] = user["email"]
        flash(f"[DEV] Your 4 difit code is: {code}", "info")
        return redirect(url_for("mfa_verify"))
    
    return render_template("login.html")


@app.route("/mfa", methods=["GET", "POST"])
def mfa_verify():
    if "pending_user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        entered = request.form.get("code","").strip()
        if entered == session.get("mfa_code"):
            session["user_id"] = session.pop("pending_user_id")
            session["role"] = session.pop("pending_role")
            session.pop("mfa_code", None)
            masked = session["mfa_email"][:3] + "*****" + session["mfa_email"][session["mfa_email"].index("@"):]
            session.pop("mfa_email", None)
            if session["role"] == "librarian":
                return redirect(url_for("librarian_dashboard"))
            return redirect(url_for("member_home"))
        flash("Incorrect code. Try again.", "error")

    masked = ""
    if "mfa_email" in session:
        e = session["mfa_email"]
        at = e.index("@")
        masked = e[:3] + "*****" + e[at:]

        return render_template("mfa,html", masked_email=masked)
    

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        phone    = request.form.get("phone", "").strip()

        conn = get_db()
        exists = conn.execute(
            "SELECT id FROM users WHERE username=? OR email=?", (username, email)
        ).fetchone()
        if exists:
            conn.close()
            flash("Username or email already exists." "error")
            return render_template("signup.html")
            
        conn.execute(
            "INSERT INTO users(username,email,password,phone,role,member_since) VALUES(?,?,?,?,?,?)",
            (username, email, hash_password(password), phone, "member", datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        conn.close()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
        
    return render_template("signup.html")
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
    

#----------------------------------------------
#MEMBER ROUTES
#----------------------------------------------

@app.route("/home")
@login_required
def member_home():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    featured =conn.execute(
        "SELECT * FROM resources WHERE available>0 ORDER BY id DESC LIMIT 6"
    ).fetchall()
    categories = conn.execute(
        "SELECT type, COUNT(*) as cnt FROM rescources GROUP BY type"
    ).fetchall()
    conn.close()
    return render_template("member_home.html", user=user, featured=featured, categories=categories)


