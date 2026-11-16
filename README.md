# Canes Catering Company | BTE 423 Team 8

Streamlit app for managing catering **clients** and **events** (CRUD), backed by the
`canes_catering` MySQL database.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | Creates the database and all seven tables |
| `seed_data.sql` | Loads the sample data |
| `reports.sql` | The three report queries |
| `app.py` | Streamlit app (CRUD on CLIENT and EVENT) |
| `requirements.txt` | Python dependencies |
| `.streamlit/secrets.toml.example` | Template for your database credentials |

## Setup

1. **Install Python 3.10+ and MySQL 8.0.16+** (CHECK constraints are only enforced from 8.0.16).
2. **Build the database**, in this order:
   ```bash
   mysql -u <user> -p < schema.sql
   mysql -u <user> -p < seed_data.sql
   mysql -u <user> -p < reports.sql
   ```
3. **Install the dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Add your credentials.** Copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in your MySQL host, user and password.
   This file is in `.gitignore`, so your password is never committed.
5. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## What the app does

**Clients**: add a client, browse/search clients, delete a client (with confirmation).
**Events**: book an event (client and venue dropdowns), browse/search events (shows client
and venue names, with status and date filters), edit status/date/guest count, delete an
event (with confirmation).

`Client_ID` and `Event_ID` are `AUTO_INCREMENT`, so the forms have no ID field.

## Validation

| Check | Where it is enforced |
|---|---|
| Required fields are not empty | App |
| Email format; phone has 7+ digits | App |
| Guest count must be at least 1 | App and `CHECK (Guest_Count > 0)` |
| Guest count cannot exceed venue capacity | App (spans two tables, so not a CHECK) |
| Duplicate client email | `UNIQUE` on `Email_Address` (app shows a friendly message) |
| Deleting a client who has events | `ON DELETE RESTRICT` blocks it (app shows a friendly message) |
| Deleting an event with menu orders or staff assignments | `ON DELETE RESTRICT` blocks it |

Note: the guest count box allows 0 on purpose, so the "guest count of 0 is blocked" test
can be demonstrated.
