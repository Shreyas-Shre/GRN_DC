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
        grn_item_id INTEGER,
        FOREIGN KEY (dc_id) REFERENCES delivery_challan (id),
        FOREIGN KEY (grn_item_id) REFERENCES grn_items (id)
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
    conn = get_db_connection()
    
    # Counts
    dc_count = conn.execute("SELECT COUNT(*) FROM delivery_challan").fetchone()[0]
    grn_count = conn.execute("SELECT COUNT(*) FROM grn").fetchone()[0]
    
    # Recent Activities
    recent_dcs = conn.execute("SELECT * FROM delivery_challan ORDER BY id DESC LIMIT 5").fetchall()
    recent_grns = conn.execute("SELECT * FROM grn ORDER BY id DESC LIMIT 5").fetchall()
    
    conn.close()
    
    return render_template(
        "dashboard.html", 
        dc_count=dc_count, 
        grn_count=grn_count,
        recent_dcs=recent_dcs,
        recent_grns=recent_grns
    )

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
        cursor = conn.cursor()
        print("before insert")
        cursor.execute(
            "INSERT INTO grn (grn_number, date, supplier_name, remarks) VALUES (?, ?, ?, ?)",
            (grn_number, date, supplier_name, remarks)
        )
        print("before grn")
        grn_id = cursor.lastrowid   # ✅ THIS IS CRITICAL

        conn.commit()
        conn.close()

        print("DEBUG GRN ID:", grn_id)  # optional, but useful

        return redirect(url_for("add_grn_items", grn_id=grn_id))


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

    conn = get_db_connection()
    grn_items = conn.execute("""
        SELECT
            g.id,
            g.item_name,
            g.quantity AS received_qty,
            IFNULL(SUM(d.quantity), 0) AS issued_qty,
            (g.quantity - IFNULL(SUM(d.quantity), 0)) AS remaining_qty
        FROM grn_items g
        LEFT JOIN dc_items d ON g.id = d.grn_item_id
        GROUP BY g.id
        HAVING remaining_qty > 0
    """).fetchall()
    conn.close()

    if request.method == "POST":
        item_name = request.form["item_name"]
        quantity = request.form["quantity"]
        grn_item_id = request.form["grn_item_id"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO dc_items (dc_id, item_name, quantity, grn_item_id) VALUES (?, ?, ?, ?)",
            (dc_id, item_name, quantity, grn_item_id)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("add_dc_items", dc_id=dc_id))

    # Fetch existing items in this DC to display
    conn = get_db_connection()
    current_dc_items = conn.execute(
        "SELECT * FROM dc_items WHERE dc_id = ?",
        (dc_id,)
    ).fetchall()
    conn.close()

    return render_template(
        "add_dc_items.html",
        dc_id=dc_id,
        grn_items=grn_items,
        current_items=current_dc_items
    )


@app.route("/grn/<int:grn_id>/items", methods=["GET", "POST"])
def add_grn_items(grn_id):
    
    if request.method == "POST":
        item_name = request.form["item_name"]
        quantity = request.form["quantity"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO grn_items (grn_id, item_name, quantity) VALUES (?, ?, ?)",
            (grn_id, item_name, quantity)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("add_grn_items", grn_id=grn_id))



    # Fetch existing items in this GRN to display
    conn = get_db_connection()
    current_grn_items = conn.execute(
        "SELECT * FROM grn_items WHERE grn_id = ?",
        (grn_id,)
    ).fetchall()
    conn.close()

    return render_template(
        "add_grn_items.html", 
        grn_id=grn_id,
        current_items=current_grn_items
    )

@app.route("/grn/<int:grn_id>")
def view_grn(grn_id):
    conn = get_db_connection()

    grn = conn.execute(
        "SELECT * FROM grn WHERE id = ?",
        (grn_id,)
    ).fetchone()

    items = conn.execute("""
    SELECT
        g.item_name,
        g.quantity AS received_qty,
        IFNULL(SUM(d.quantity), 0) AS issued_qty,
        (g.quantity - IFNULL(SUM(d.quantity), 0)) AS remaining_qty
    FROM grn_items g
    LEFT JOIN dc_items d ON g.id = d.grn_item_id
    WHERE g.grn_id = ?
    GROUP BY g.id
""", (grn_id,)).fetchall()


    conn.close()

    # Calculate Status
    total_remaining = sum(item["remaining_qty"] for item in items)
    # If there are items and total remaining is 0, it's CLOSED. 
    # If no items, it's OPEN (pending items). 
    # If items exist and remaining > 0, it's OPEN (Pending).
    if items and total_remaining == 0:
        status = "Closed"
    else:
        status = "Pending"

    return render_template("view_grn.html", grn=grn, items=items, status=status)


@app.route("/reset-db", methods=["POST"])
def reset_db():
    conn = get_db_connection()
    # Delete data from all tables but keep the structure
    conn.execute("DELETE FROM dc_items")
    conn.execute("DELETE FROM grn_items")
    # We need to delete child records before parent records due to foreign keys,
    # but here we just want to wipe everything. SQLite foreign key constraints 
    # are often disabled by default, but let's be safe and delete properly.
    conn.execute("DELETE FROM delivery_challan")
    conn.execute("DELETE FROM grn")
    
    # Reset auto-increment counters if needed (optional)
    conn.execute("DELETE FROM sqlite_sequence")

    conn.commit()
    conn.close()
    return redirect(url_for("home"))


print("ssss",app.url_map)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
