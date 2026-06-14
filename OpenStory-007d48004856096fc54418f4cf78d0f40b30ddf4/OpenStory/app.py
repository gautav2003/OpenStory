
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
            "INSERT INTO users(username,email,password,phone,role,librarian_code,member_since) VALUES(?,?,?,?,?,?,?)",
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
            "INSERT INTO resources(itle,author,isbn,type,total_copies,available,file_path,added_on) VALUES(?,?,?,?,?,?,?)",
            resources
        )

        today = datetime.now()
        borrowings = [
            (1, 1, "2024-03-15", "2024-03-22", None,        "borrowed", 0.0),
            (3, 2, "2024-03-10", "2024-03-04", None,        "overdue",  2.50),
            (4, 10, "2024-03-05","2024-03-05", "2024-03-18", "returned"  0.0),
        ]
        cur.executemany(
            "INSERT INTO borrowings(user_id,resource_id,borrow_date,due_date,return_date,status,fine_amount)VALUES(?,?,?,?,?,?,?)",
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


@app.route("/catalogue")
@login_required
def catalogue():
    q       = request.args.get("q", "")
    rtype   = request.args.get("type", "")
    status  = request.args.get("status", "")

    conn = get_db()
    sql  = "SELECT * FROM resources WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OEcaithor LIKE ? OR isbn LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%" ]
    if rtype:
        sql += " AND type=?"
        params.append(rtype)
    if status == "available":
        sql += " AND available>0"
    elif status == "unavailable":
        sql += " and available=0"
    sql += " ORDER BY title"
    resources = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("catalogue.html", resources=resources, q=q, rtype=rtype, status=status)


@app.route("/borrow/<int:resource_id>", methods=["POST"])
@login_required
def borrow(resource_id):
    conn = get_db()
    resource = conn.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
    if not resource or resource["available"] < 1:
        flash("Resource not available", "error")
        conn.close()
        return redirect(url_for("catalogue"))
    
    already = conn.execute(
        "SELECT id FROM borrowings WHERE user_id=? AND resource_id=? AND status='borrowed'",
        (session["user_id"], resource_id)
    ).fetchone
    if already:
        flash("You already have this item borrowed.", "error")
        conn.close()
        return redirect(url_for("catalogue"))
    
    borrow_date = datetime.now().strftime("%Y-%m-%d")
    due_date    =(datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO borrowings(user_id,resource_id,borrow_date,due_date,status) VALUES(?,?,?,?,?)",
        (session["user_id"], resource_id, borrow_date, due_date, "borrowed")
    )
    conn.execute("UPDATE resources SET available=available-1 WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()
    flash(f"'{resource['title']}' borrowed successfuly! Due {due_date}.", "success")
    return redirect(url_for("catalogue"))


@app.route("/return/<int:borrowing_id>", methods=["POST"])
@login_required
def return_book(borrowing_id):
    conn = get_db()
    b = conn.execute(
        "SELECT * FROM borrowings WHERE id=? AND user_id=?",
        (borrowing_id, session["user_id"])
    ).fetchone()
    if not b:
        flash("Borrowing record not found.", "error")
        conn.close()
        return redirect(url_for("my_account"))
    
    conn.execute(
        "UPDATE borrowings SET return_date=?, status='returned' WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d"), borrowing_id)
    )
    conn.execute("UPDATE resources SET available=available+1 WHERE id=?", (b["resourse_id"],))
    conn.commit()
    conn.close()
    flash("Item returned successfully.", "success")
    return redirect(url_for("my_account"))


app.route("/account")
@login_required
def my_account():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    borrowed = conn.execute("""
        SELECT b.*, r.title, r.type FROM borrowings b
        JOIN resources r ON b.resource_id=r.id
        WHERE b.user_id=? AND b.status IN ('borrowed','overdue')
        ORDER BY b.due_date
    """, (session["user_id"],)).fetchall()
    history = conn.execute("""
        SELECT b.*, r.title, r.type FROM borrowings b
        JOIN resources r ON b.resource_id=r.id
        WHERE b.user_id=? AND b.status='returned'
        ORDER BY b.return_date DESC LIMIT 10
    """, (session["user_id"],)).fetchall()
    counts = conn.execute("""
        SELECT
          COUNT(*) as total_borrowed,
          SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END) as total_returned,
          SUM(CASE WHEN fine_amount>0 AND status!='returned' THEN fine_amount ELSE 0 END) as outstanding_fines
        FROM borrowings WHERE user_id=?
    """, (session["user_id"],)).fetchone()
    by_type = conn.execute("""
        SELECT r.type, COUNT(*) as cnt FROM borrowings b
        JOIN resources r ON b.resource_id=r.id
        WHERE b.user_id=? AND b.status_IN ('borrowed', 'overdue')
        GROUP BY r.type
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("account.html", user=user, borrowed=borrowed,
                           history=history, counts=counts, by_type=by_type)


@app.route("/account/edit", methods=["POST"])
@login_required
def edit_account():
    username = request.form.get("username", "").strip()
    phone    = request.form.get("phone", "").strip()
    conn = get_db()
    conn.execute("UPDATE users SET username=?, phone=? WHERE id=?",
                 (username, phone, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Profile updated.", "success")
    return redirect(url_for("my_account"))


#--Study Groups--

@app.route("/groups")
@login_required
def groups():
    conn = get_db()
    user_groups = conn.execute("""
        SELECT sg.*, u.username as creator,
               (SELECT COUNT (*) FROM group_members gm2 WHERE gm2.group_id=sg.id) as member_count
        FROM study_groups sg
        JOIN group_members gm ON sg.id=gm.group_id
        JOIN users u ON sg.created_by=u.id
        WHERE gm.user_id=? AND sg.active=1
    """, (session["user_id"],)).fetchall()
    all_groups = conn.execute("""
        SELECT sg.*, u.username as creator,
               (SELECT COUNT(* FROM group_members gm2 WHERE gm2.group_id=sg.id) as member_count
        FROM study_groups sg
        JOIN users u ON sg.created_by=u.id
        WHERE sg.active=1 AND sg.id NOT IN(
            SELECT group_id FROM group_members WHERE user_id=?
        )
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("groups.html", user_groups=user_groups, all_groups=all_groups)


@app.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    name = request.form.get("name", "").strip()
    desc = request.form.get("description", "").strip()
    if not name:
        flash("Group name required.", "error")
        return redirect(url_for("groups"))
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO study_groups(name,description,created_by,created_on) VALUES(?,?,?,?)",
        (name, desc, session["user_id"], datetime.now().strftime("%Y-%m-%d"))
    )
    gid = cur.lastrowid
    conn.execute(
        "INSERT INTO group_members(group_id,user_id,joined_on) VALUES(?,?,?)",
        (gid, session["user_id"], datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()
    flash(f"Group '{name}' created!", "success")
    return redirect(url_for("group_detail", group_id=gid))


@app.route("/groups/int:group_id>")
@login_required
def group_detail(group_id):
    conn = get_db()
    group = conn.execute("SELECT * FROM study_groups WHERE id=?", (group_id,)).fetchone()
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for("groups"))
    messages = conn.execute("""
        SELECT gm.*, u.username FROM group_messages gm
        JOIN users u ON gm.user_id=u.id
        WHERE gm.group_id=? ORDER BY gm.sent_at
    """, (group_id,)).fetchall()
    members = conn.execute("""
        SELECT u.username, u.id FROM group_members gm
        JOIN users u ON gm.user_id=u.id
        WHERE gm.group_id=?
    """, (group_id,)).fetchall()
    tasks = conn.execute("SELECT * FROM group_tasks WHERE group_id=? ORDER BY id", (group_id,)).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("group_detail.html", group=group, messages=messages,
                           members=members, tasks=tasks, user=user)


@app.route("/groups/<int:group_id>/message", methods=["POST"])
@login_required
def group_message(group_id):
    msg = request.form.get("message", "").strip()
    if msg:
        conn = get_db()
        conn.execute(
            "INSERT INTO group_messages(group_id,user_id,message,sent_at) VALUES(?,?,?,?)",
            (group_id, session["user_id"], msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/groups/<int:group_id>/task", methods=["POST"])
@login_required
def add_task(group_id):
    title      = request.form.get("title", "").strip()
    assigned   = request.form.get("assigned_to", "").strip()
    due_date   = request.form.get("due_date", "").strip() or None
    if title:
        conn = get_db()
        conn.execute(
            "INSERT INTO group_tasks(group_id,title,assigned_to,due_date,status) VALUES(?,?,?,?,?)",
            (group_id, title, assigned, due_date, "pending")
        )
        conn.commit()
        conn.close()
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/groups/task/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id):
    status = request.form.get("status","pending")
    conn = get_db()
    task = conn.execute("SELECT * FROM froup_tasks WHERE id=?", (task_id,)).fetchone()
    conn.execute("UPDATE group_tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()
    gid = task["group_id"] if task else None
    conn.close()
    return redirect(url_for("group_detail", group_id=gid))


#--Ask a Librarian Chat--

@app.route("/chat")
@login_required
def chat():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    messages = conn.execute("""
        SELECT cm.*, u.username as sender_name FROM chat_messages cm
        LEFT JOIN users u ON (
            CASE WHEN cm.sender_role='member' THEN cm.user_id
                 ELSE cm.librarian_id END = u.id
        )
        WHERE cm.user_id=? ORDER BY cm.sent_at
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("chat.html", user=user, messages=messages)


@app.route("/chat/send", methods=["POST"])
@login_required
def chat_sent():
    message = request.form.get("message", "").strip()
    if message:
        conn = get_db()
        conn.execute(
            "INSERT INTO chat_messages(user_id,message,sender_role,sent_at,is_read) VALUES(?,?,?,?,?)",
            (session["user_id"], message, "member", datetime.now().strftime("%Y_%m_%d %H:%M:%S"), 0)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("chat"))


#------------------------------------------------
#LIBRARIAN ROUTES
#------------------------------------------------

@app.route("/librarian/dashboard")
@librarian_required
def librarian_dashboard():
    conn = get_db()
    stats = get_stats()
    recent_borrowings = conn.execute("""
        SELECT b.*, u.username, rtitle FROM borrowings b
        JOIN users u ON b.user_id=u.id
        JOIN resources r ON b.resource_id=r.id
        ORDER BY b.borrow_date DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template("librarian_dashboard.html", stats=stats, recent_borrowings=recent_borrowings)


@app.route("/librarian/catalogue")
@librarian_required
def librarian_catalogue():
    q      = request.args.get("q", "")
    rtype  = request.args.get("type", "")
    status = request.args.get("status", "")

    conn = get_db()
    sql    = "SELECT * FROM resources WHERE 1=1"
    params =[]
    if q:
        sql += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if rtype:
        sql += " AND type=?"
        params.append(rtype)
    if status == "available":
        sql += " AND available>0"
    elif status == "unavailable":
        sql += " AND available=0"
    sql += " ORDER BY title"
    resources = conn.execute(sql, params).fetchall()
    stats = get_stats()
    conn.close()
    return render_template("librarian_catalogue.html", resources=resources,
                           stats=stats, q=q, rtype=rtype, status=status)


@app.route("/librarian/resource/add", methods=["POST"])
@librarian_required
def add_resource():
    title   = request.form.get("title", "").strip()
    author  = request.form.get("author", "").strip()
    isbn    = request.form.get("isbn", "N/A").strip()
    rtype   = request.form.get("type", "book").strip()
    copies  = int(request.form.get("copies", 1))

    conn = get_db()
    conn.execute(
        "INSERT INTO resources(title,author,isbn,type,total_copies,available,added_on) VALUES(?,?,?,?,?,?,?)",
        (title, author, isbn, rtype, copies, copies, datetime.now().strftime("%Y-%m-%d"))
    )
    conn.commit()
    conn.close()
    flash(f"'{title}' added to catalogue.", "success")
    return redirect(url_for("librarian_catalogue"))


@app.route("/librarian/resource/delete/<int:resource_id>", methods=["POST"])
@librarian_required
def delete_resource(resource_id):
    conn = get_db()
    conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()
    flash("Resource deleted.", "success")
    return redirect(url_for("librarian_catalogue"))


@app.route("/librarian/borrowers")
@librarian_required
def librarian_borrowers():
    conn = get_db()
    members = conn.execute("""
        SELECT u.*,
                COUNT(CASE WHEN b.status IN('borrowed','overdue') THEN 1 END) as active_borrows,
                COALESCE(SUM(CASE WHEN b.fine_amount>0 AND b.status!='returned' THEN b.fine_amount ELSE 0 END) as fines
        FROM users u
        LEFT JOIN borrowings b ON u.id=b.user_id
        WHERE u.role='member'
        GROUP BY u.id ORDER BY u.username
    """).fetchall()
    conn.close()
    return render_template("librarian_borrowers.html", members=members)


@app.route("/librarian/chat")
@librarian_required
def librarian_chat():
    conn = get_db()
    #Get distinct users who have messaged
    conversations = conn.execute("""
        SELECT u.id, u.username,
                MAX(cm.sent_at) as last_message,
                SUM(CASE WHEN CM.is_read=0 AND cm.sender_role='member' THEN 1 ELSE 0 END) as unread
        FROM chat_messages cm
        JOIN users u.id ORDER BY last_message DESC
    """).fetchall()
    selected_user_id = request.args.get("user_id", type=int)
    selected_messages = []
    selected_user = None
    if selected_user_id:
      selected_user = conn.execute("SELECT * FROM users WHERE id=?", (selected_user_id,)).fetchone()
      selected_messages = conn.execute("""
          SELECT cm.*, u.username FROM chat_messages cm
        LEFT JOIN users u ON (
            CASE WHEN cm.sender_role='member' THEN cm.user_id ELSE cm.librarian_id END = u.id
        )
        WHERE cm.user_id=? ORDER BY cm.sent_at                               
    """, (selected_user_id,)).fetchall()
    #Mark as read
    conn.execute(
        "UPDATE chat_messages SET is_read=1 WHERE user_id=? AND sender_role='member'",
        (selected_user_id,)
    )
    conn.commit()
    conn.close()
    return render_template("librarian_chat.html", conversations=conversations,
                           selected_messages=selected_messages, selected_user=selected_user)


@app.route("/librarian/chat/reply", methods=["POST"])
@librarian_required
def librarian_reply():
    user_id = request.form.get("user_id", type=int)
    message = request.form.get("message", "").strip()
    if message and user_id:
        conn = get_db()
        conn.execute(
            "INSERT INTO chat_messages(user_id,librarian_id,message,sender_role,sent_at,is_read) VALUES(?,?,?,?,?,?)",
            (user_id, session["user_id"], message, "librarian",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("librarian_chat", user_id=user_id))


#-----------------------------------------------
#ENTRY POINT
#-----------------------------------------------

if __name__ == "__main__":
    init_db
    print("=" * 60)
    print(" Open Story Library System")
    print(" https://127.0.0.1:5000")
    print()
    print(" Demo credentials:")
    print(" Member → SushilSharma14 / password123")
    print(" Librarian → LibrarianVicky / lib2024 (code: LTB001)")
    print("=" * 60)
    app.run(debug=True, port=5000)
