from flask import Flask, render_template
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

import os

app = Flask(__name__)

DB_NAME = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    return conn
def generate_dc_number():
    conn = get_db_connection()
    last_dc = conn.execute(
        "SELECT dc_number FROM delivery_challan ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if last_dc is None:
        return "DC-001"

    dc_value = last_dc["dc_number"]

    # Handle old / unexpected formats safely
    if "-" not in dc_value:
        return "DC-001"

    try:
        last_number = int(dc_value.split("-")[1])
    except (IndexError, ValueError):
        return "DC-001"

    new_number = last_number + 1
    return f"DC-{new_number:03d}"




def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_challan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dc_number TEXT UNIQUE,
            date TEXT,
            party_name TEXT,
            remarks TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_number TEXT UNIQUE,
            date TEXT,
            supplier_name TEXT,
            remarks TEXT
        )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dc_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dc_id INTEGER,
        item_name TEXT,
        quantity INTEGER,
        FOREIGN KEY (dc_id) REFERENCES delivery_challan (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grn_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            FOREIGN KEY (grn_id) REFERENCES grn (id)
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("base.html")

@app.route("/dc/new", methods=["GET", "POST"])
def create_dc():
    if request.method == "POST":
        dc_number = generate_dc_number()
        date = request.form["date"]
        party_name = request.form["party_name"]
        remarks = request.form["remarks"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO delivery_challan (dc_number, date, party_name, remarks) VALUES (?, ?, ?, ?)",
            (dc_number, date, party_name, remarks)
        )
        conn.commit()
        
        dc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return redirect(url_for("add_dc_items", dc_id=dc_id))

    
    return render_template(
    "create_dc.html",
    next_dc=generate_dc_number()
)

@app.route("/dc")
def list_dc():
    conn = get_db_connection()
    dcs = conn.execute(
        "SELECT * FROM delivery_challan ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("list_dc.html", dcs=dcs)
@app.route("/dc/<int:dc_id>")
def view_dc(dc_id):
    conn = get_db_connection()

    dc = conn.execute(
        "SELECT * FROM delivery_challan WHERE id = ?",
        (dc_id,)
    ).fetchone()

    items = conn.execute(
        "SELECT * FROM dc_items WHERE dc_id = ?",
        (dc_id,)
    ).fetchall()

    conn.close()

    return render_template("view_dc.html", dc=dc, items=items)

@app.route("/grn/new", methods=["GET", "POST"])
def create_grn():
    if request.method == "POST":
        grn_number =request.form["grn_number"]
        date = request.form["date"]
        supplier_name = request.form["supplier_name"]
        remarks = request.form["remarks"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO grn (grn_number, date, supplier_name, remarks) VALUES (?, ?, ?, ?)",
            (grn_number, date, supplier_name, remarks)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("list_grn"))

    return render_template("create_grn.html")



@app.route("/grn")
def list_grn():
    conn = get_db_connection()
    grns = conn.execute(
        "SELECT * FROM grn ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("list_grn.html", grns=grns)
@app.route("/dc/<int:dc_id>/items", methods=["GET", "POST"])
def add_dc_items(dc_id):
    if request.method == "POST":
        item_name = request.form["item_name"]
        quantity = request.form["quantity"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO dc_items (dc_id, item_name, quantity) VALUES (?, ?, ?)",
            (dc_id, item_name, quantity)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("add_dc_items", dc_id=dc_id))

    return render_template("add_dc_items.html", dc_id=dc_id)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
