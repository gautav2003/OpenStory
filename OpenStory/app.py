
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

        