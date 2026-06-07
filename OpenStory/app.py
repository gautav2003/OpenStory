
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

         
        """)