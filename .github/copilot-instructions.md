# GRN & DC Management System - AI Coding Instructions

## Project Overview
A Flask-based inventory management web application tracking **Delivery Challans (DC)** and **Goods Received Notes (GRN)**. Two separate document workflows with items tracking capabilities.

## Architecture

### Backend Stack
- **Framework**: Flask (Python) with SQLite3
- **Database**: SQLite with 4 core tables: `delivery_challan`, `grn`, `dc_items`, `grn_items`
- **Entry Point**: `app.py` - initialize database on startup, runs with `python app.py` (debug mode enabled)

### Data Model
**Two main document types with parallel structures:**

| Delivery Challan (DC) | Goods Received Note (GRN) |
|---|---|
| `delivery_challan` (id, dc_number, date, party_name, remarks) | `grn` (id, grn_number, date, supplier_name, remarks) |
| `dc_items` (id, dc_id, item_name, quantity) | `grn_items` (id, grn_id, item_name, quantity) |

**Key Pattern**: DC numbers auto-generate as "DC-001", "DC-002", etc. GRN numbers are user-provided.

### Routes
| Route | Method | Purpose | Flow |
|---|---|---|---|
| `/` | GET | Home | Returns base.html |
| `/dc/new` | GET/POST | Create DC | POST → auto-generates dc_number → redirects to add_dc_items |
| `/dc` | GET | List all DCs | Ordered DESC by id |
| `/dc/<id>` | GET | View DC + items | Displays dc and related dc_items |
| `/dc/<id>/items` | GET/POST | Add items to DC | POST adds item → refreshes same page |
| `/grn/new` | GET/POST | Create GRN | POST → redirects to add_grn_items |
| `/grn` | GET | List all GRNs | Ordered DESC by id |
| `/grn/<id>/items` | GET/POST | Add items to GRN | POST adds item → refreshes same page |

## Frontend Conventions

### Template Hierarchy
- **base.html**: Master template with navbar styling (2c3e50 color scheme) and container layout
- **create_dc.html, create_grn.html**: Form templates displaying auto-generated numbers
- **add_dc_items.html, add_grn_items.html**: Item entry forms (likely loop-add patterns)
- **list_dc.html, list_grn.html**: Table views with DESC ordering
- **view_dc.html**: Detail page with related items

### Design Pattern
- Simple form-based workflows (create document → add items → view)
- No AJAX/async patterns; POST redirects for data mutations
- Minimal styling in base.html; inline CSS for tables/containers

## Critical Workflows

### Creating & Populating a DC
1. User visits `/dc/new` (GET) → sees pre-filled dc_number from `generate_dc_number()`
2. Submits form (POST) → inserts delivery_challan → retrieves `dc_id` via `last_insert_rowid()`
3. Redirects to `/dc/<dc_id>/items` to add items
4. Each item POST refreshes same page (no deletion visible in code)

### Creating & Populating a GRN
1. User visits `/grn/new` (GET) → empty form
2. Submits form (POST) with manual grn_number → inserts grn → gets `lastrowid`
3. Redirects to `/grn/<grn_id>/items` to add items
4. Same item-add pattern as DC

**Asymmetry**: DC auto-generates numbers; GRN requires user input.

## Database Interaction Patterns

### Connection Management
```python
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn
```
- Always close connection after use (`conn.close()`)
- All queries use parameterized SQL (`?`) to prevent injection

### Common Query Patterns
```python
# Single record
conn.execute("SELECT * FROM delivery_challan WHERE id = ?", (dc_id,)).fetchone()

# Last inserted ID (after INSERT)
cursor.lastrowid  # or conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# Ordered list (DESC for latest first)
conn.execute("SELECT * FROM delivery_challan ORDER BY id DESC").fetchall()
```

## Debugging & Development

### Running the Application
```bash
python app.py
# Output: * Running on http://127.0.0.1:5000 (debug mode)
```

### Database Reset
- Delete `database.db` before next run; `init_db()` recreates tables
- Schema defined in `init_db()` function in app.py

### Known Issues/Patterns
- No item deletion endpoints visible (add-only workflow)
- No input validation beyond `required` attributes in HTML forms
- Print statements used for debugging (e.g., `print("GRN ID:", grn_id)`)

## Code Quality Notes

### What to Preserve
- Parameterized SQL queries (security)
- Row factory pattern for readable column access
- Auto-number generation logic for DCs

### What to Improve (if needed)
- Form validation should move to backend (HTML `required` alone insufficient)
- Consider adding item deletion/edit routes
- Consolidate duplicate DC/GRN creation logic into shared function
- Remove debug print statements in production
- Add error handling for database operations (no try/except currently)

## AI Agent Quick Reference

- **Start here**: [app.py](app.py) for routes and db schema
- **Add features**: Follow POST → INSERT → redirect pattern
- **Fix bugs**: Check `add_dc_items.html` and `add_grn_items.html` templates for item-add UI
- **Test changes**: Restart with `python app.py`, clear `database.db` if needed
- **Database queries**: Use `conn.row_factory = sqlite3.Row` to access results by column name
