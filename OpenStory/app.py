
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


def get_stats():
    conn = get_db()
    stats = {
        "total_resources": conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
        "active_members":  conn.execute("SELECT COUNT(*) FROM users WHERE role='member' AND active=1").fetchone()[0],
        "active_borrowings": conn.execute("SELECT COUNT(*) FROM borrowings WHERE status='borrowed'").fetchone()[0],
        "overdue_items":  conn.execute("SELECT COUNT(* FROM borrowings WHERE status='overdue'").fetchone()[0],
        "pending_chats":  conn.execute("SELECT COUNT(*) FROM chat_messages WHERE is_read=0 AND sender_role='member'").fetchone()[0],
        "study_groups":   conn.execute("SELECT COUNT(*) FROM study_groups WHERE active=1").fetchone()[0],
        "outstanding_fines": conn.execute("SELECT COALESCE(SUM(FINE))")  
    }