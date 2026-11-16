"""
Canes Catering Company | BTE 423 Team 8
app.py: Streamlit CRUD app for CLIENT and EVENT, plus the three reports (connects to the canes_catering MySQL database).

Run order for the database: schema.sql -> seed_data.sql -> reports.sql
Run the app with:           streamlit run app.py
"""

import re
from datetime import date, datetime, time, timedelta

import mysql.connector
import pandas as pd
import streamlit as st
from mysql.connector import errorcode

# Allowed values: these mirror the CHECK constraints in schema.sql exactly.
EVENT_TYPES = ["Wedding", "Corporate", "Gala", "Birthday", "Graduation", "Other"]
EVENT_STATUSES = ["Inquiry", "Confirmed", "Completed", "Cancelled"]

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

st.set_page_config(page_title="Canes Catering", page_icon="🍗", layout="wide")


# ----------------------------------------------------------------------------
# Database helpers (credentials come from .streamlit/secrets.toml, never code)
# ----------------------------------------------------------------------------
def get_connection():
    cfg = st.secrets["mysql"]
    return mysql.connector.connect(
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg.get("database", "canes_catering"),
    )


def run_query(sql, params=()):
    """Run a SELECT and return a list of dict rows."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def run_write(sql, params=()):
    """Run an INSERT/UPDATE/DELETE, commit, and return (new id, rows affected)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        conn.close()


def friendly_db_error(err, context=""):
    """Turn a MySQL error into a message a coordinator can understand."""
    if err.errno == errorcode.ER_DUP_ENTRY:
        return "That email address is already in use by another client."
    if err.errno == errorcode.ER_ROW_IS_REFERENCED_2:  # 1451, ON DELETE RESTRICT
        return context or "This record is referenced by other records, so it cannot be deleted."
    if err.errno == errorcode.ER_CHECK_CONSTRAINT_VIOLATED:  # 3819
        return "The database rejected that value (a CHECK constraint failed). Please review the fields."
    return f"Database error ({err.errno}): {err.msg}"


def flash(kind, message):
    """Store a message to show after the page reruns."""
    st.session_state["flash"] = (kind, message)


def show_flash():
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


# ----------------------------------------------------------------------------
# Lookups
# ----------------------------------------------------------------------------
def load_clients():
    return run_query(
        """
        SELECT c.Client_ID, c.Client_FName, c.Client_LName, c.Company_Name,
               c.Email_Address, c.Phone_Number, c.Client_Since,
               COUNT(e.Event_ID) AS Event_Count
        FROM CLIENT c
        LEFT JOIN EVENT e ON e.Client_ID = c.Client_ID
        GROUP BY c.Client_ID
        ORDER BY c.Client_LName, c.Client_FName
        """
    )


def load_venues():
    return run_query(
        "SELECT Venue_ID, Venue_Name, Venue_City, Venue_State, Venue_Capacity "
        "FROM VENUE ORDER BY Venue_Name"
    )


EVENT_SELECT = """
    SELECT e.Event_ID, e.Event_Name, e.Event_Type, e.Event_Date, e.Start_Time,
           e.Guest_Count, e.Status,
           e.Client_ID, CONCAT(c.Client_FName, ' ', c.Client_LName) AS Client_Name,
           c.Company_Name,
           e.Venue_ID, v.Venue_Name, v.Venue_Capacity
    FROM EVENT e
    JOIN CLIENT c ON c.Client_ID = e.Client_ID
    JOIN VENUE  v ON v.Venue_ID  = e.Venue_ID
"""


def client_label(c):
    company = f" ({c['Company_Name']})" if c.get("Company_Name") else ""
    return f"{c['Client_FName']} {c['Client_LName']}{company}"


def venue_label(v):
    return f"{v['Venue_Name']} (capacity {v['Venue_Capacity']})"


def event_label(e):
    return f"#{e['Event_ID']} | {e['Event_Name']} | {e['Event_Date']} | {e['Client_Name']}"


def fmt_time(value):
    """MySQL TIME comes back as a timedelta; show it as HH:MM."""
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value)


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
def validate_client(first, last, email, phone):
    errors = []
    if not first.strip():
        errors.append("First name is required.")
    if not last.strip():
        errors.append("Last name is required.")
    if not email.strip():
        errors.append("Email address is required.")
    elif not EMAIL_PATTERN.match(email.strip()):
        errors.append("Email address is not valid (example: name@example.com).")
    if not phone.strip():
        errors.append("Phone number is required.")
    elif len(re.sub(r"\D", "", phone)) < 7:
        errors.append("Phone number must contain at least 7 digits.")
    return errors


def validate_guest_count(guest_count, capacity, venue_name):
    errors = []
    if guest_count is None or guest_count < 1:
        errors.append("Guest count must be at least 1.")
    elif guest_count > capacity:
        errors.append(
            f"Guest count ({guest_count}) is over the capacity of {venue_name} ({capacity})."
        )
    return errors


def show_errors(errors):
    for message in errors:
        st.error(message)


# ----------------------------------------------------------------------------
# Clients page
# ----------------------------------------------------------------------------
def add_client_tab():
    st.subheader("Add a client")
    st.caption("Client ID is assigned automatically by the database.")
    with st.form("add_client_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        first = col1.text_input("First name *")
        last = col2.text_input("Last name *")
        company = st.text_input("Company name (leave blank for individual clients)")
        col3, col4 = st.columns(2)
        email = col3.text_input("Email address *")
        phone = col4.text_input("Phone number *", placeholder="305-555-0100")
        submitted = st.form_submit_button("Add client")

    if submitted:
        errors = validate_client(first, last, email, phone)
        if errors:
            show_errors(errors)
            return
        try:
            new_id, _ = run_write(
                "INSERT INTO CLIENT (Client_FName, Client_LName, Company_Name, "
                "Email_Address, Phone_Number, Client_Since) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    first.strip(),
                    last.strip(),
                    company.strip() or None,
                    email.strip().lower(),
                    phone.strip(),
                    date.today(),
                ),
            )
            st.success(f"Client added: {first.strip()} {last.strip()} (Client ID {new_id}).")
        except mysql.connector.Error as err:
            st.error(friendly_db_error(err))


def browse_clients_tab():
    st.subheader("Browse clients")
    search = st.text_input("Search by name, company or email", key="client_search").strip().lower()
    rows = load_clients()
    if search:
        rows = [
            r for r in rows
            if search in " ".join(
                str(r[k] or "") for k in
                ("Client_FName", "Client_LName", "Company_Name", "Email_Address")
            ).lower()
        ]
    if not rows:
        st.info("No clients match your search.")
        return
    df = pd.DataFrame(rows).rename(columns={
        "Client_ID": "ID", "Client_FName": "First Name", "Client_LName": "Last Name",
        "Company_Name": "Company", "Email_Address": "Email", "Phone_Number": "Phone",
        "Client_Since": "Client Since", "Event_Count": "Events",
    })
    st.caption(f"{len(df)} client(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)


def delete_client_tab():
    st.subheader("Delete a client")
    clients = load_clients()
    if not clients:
        st.info("There are no clients to delete.")
        return
    by_id = {c["Client_ID"]: c for c in clients}
    client_id = st.selectbox(
        "Client", list(by_id), format_func=lambda i: f"#{i} | {client_label(by_id[i])}",
        key="del_client_select",
    )
    client = by_id[client_id]
    st.write(f"**Email:** {client['Email_Address']}  |  **Events on record:** {client['Event_Count']}")
    confirm = st.checkbox("Yes, I want to permanently delete this client.", key=f"del_client_confirm_{client_id}")
    if st.button("Delete client", type="primary", disabled=not confirm):
        try:
            run_write("DELETE FROM CLIENT WHERE Client_ID = %s", (client_id,))
            flash("success", f"Deleted client {client_label(client)}.")
            st.rerun()
        except mysql.connector.Error as err:
            st.error(friendly_db_error(
                err,
                f"{client_label(client)} has {client['Event_Count']} event(s) on record, so the "
                "database will not allow this client to be deleted. Delete or reassign those "
                "events first.",
            ))


def clients_page():
    st.header("Clients")
    show_flash()
    tab_add, tab_browse, tab_delete = st.tabs(["Add client", "Browse clients", "Delete client"])
    with tab_add:
        add_client_tab()
    with tab_browse:
        browse_clients_tab()
    with tab_delete:
        delete_client_tab()


# ----------------------------------------------------------------------------
# Events page
# ----------------------------------------------------------------------------
def book_event_tab():
    st.subheader("Book an event")
    clients, venues = load_clients(), load_venues()
    if not clients or not venues:
        st.warning("At least one client and one venue are needed before booking an event.")
        return
    clients_by_id = {c["Client_ID"]: c for c in clients}
    venues_by_id = {v["Venue_ID"]: v for v in venues}

    with st.form("book_event_form", clear_on_submit=False):
        client_id = st.selectbox("Client *", list(clients_by_id),
                                 format_func=lambda i: client_label(clients_by_id[i]))
        venue_id = st.selectbox("Venue *", list(venues_by_id),
                                format_func=lambda i: venue_label(venues_by_id[i]))
        name = st.text_input("Event name *")
        col1, col2 = st.columns(2)
        event_type = col1.selectbox("Event type *", EVENT_TYPES)
        status = col2.selectbox("Status", EVENT_STATUSES, index=0)
        col3, col4, col5 = st.columns(3)
        event_date = col3.date_input("Event date *", value=date.today())
        start_time = col4.time_input("Start time *", value=time(18, 0))
        guest_count = col5.number_input("Guest count *", min_value=0, value=50, step=1)
        submitted = st.form_submit_button("Book event")

    if submitted:
        venue = venues_by_id[venue_id]
        errors = []
        if not name.strip():
            errors.append("Event name is required.")
        errors += validate_guest_count(int(guest_count), venue["Venue_Capacity"], venue["Venue_Name"])
        if errors:
            show_errors(errors)
            return
        try:
            new_id, _ = run_write(
                "INSERT INTO EVENT (Client_ID, Venue_ID, Event_Name, Event_Type, Event_Date, "
                "Guest_Count, Start_Time, Status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (client_id, venue_id, name.strip(), event_type, event_date,
                 int(guest_count), start_time, status),
            )
            st.success(f"Event booked: {name.strip()} (Event ID {new_id}).")
        except mysql.connector.Error as err:
            st.error(friendly_db_error(err))


def browse_events_tab():
    st.subheader("Browse and search events")
    col1, col2 = st.columns([2, 2])
    search = col1.text_input("Search by event, client, company or venue", key="event_search").strip().lower()
    statuses = col2.multiselect("Status", EVENT_STATUSES, default=EVENT_STATUSES, key="event_status_filter")
    use_dates = st.checkbox("Filter by date range", key="event_use_dates")
    date_range = None
    if use_dates:
        date_range = st.date_input("Date range", value=(date.today(), date.today() + timedelta(days=90)),
                                   key="event_date_range")

    rows = run_query(EVENT_SELECT + " ORDER BY e.Event_Date, e.Start_Time")
    rows = [r for r in rows if r["Status"] in statuses]
    if search:
        rows = [
            r for r in rows
            if search in " ".join(
                str(r[k] or "") for k in ("Event_Name", "Client_Name", "Company_Name", "Venue_Name")
            ).lower()
        ]
    if use_dates and isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        rows = [r for r in rows if start <= r["Event_Date"] <= end]

    if not rows:
        st.info("No events match your filters.")
        return
    df = pd.DataFrame([{
        "ID": r["Event_ID"], "Event": r["Event_Name"], "Type": r["Event_Type"],
        "Client": r["Client_Name"], "Company": r["Company_Name"], "Venue": r["Venue_Name"],
        "Date": r["Event_Date"], "Start": fmt_time(r["Start_Time"]),
        "Guests": r["Guest_Count"], "Venue Capacity": r["Venue_Capacity"], "Status": r["Status"],
    } for r in rows])
    st.caption(f"{len(df)} event(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)


def pick_event(key):
    """Selectbox of events; returns the chosen event row or None."""
    rows = run_query(EVENT_SELECT + " ORDER BY e.Event_Date DESC, e.Event_ID DESC")
    if not rows:
        st.info("There are no events yet.")
        return None
    by_id = {r["Event_ID"]: r for r in rows}
    event_id = st.selectbox("Event", list(by_id), format_func=lambda i: event_label(by_id[i]), key=key)
    return by_id[event_id]


def edit_event_tab():
    st.subheader("Edit an event")
    st.caption("You can change the status, date and guest count.")
    event = pick_event("edit_event_select")
    if event is None:
        return
    eid = event["Event_ID"]
    st.write(f"**Client:** {event['Client_Name']}  |  **Venue:** {event['Venue_Name']} "
             f"(capacity {event['Venue_Capacity']})")
    with st.form(f"edit_event_form_{eid}"):
        col1, col2, col3 = st.columns(3)
        status = col1.selectbox("Status", EVENT_STATUSES, index=EVENT_STATUSES.index(event["Status"]))
        event_date = col2.date_input("Event date", value=event["Event_Date"])
        guest_count = col3.number_input("Guest count", min_value=0, value=int(event["Guest_Count"]), step=1)
        submitted = st.form_submit_button("Save changes")

    if submitted:
        errors = validate_guest_count(int(guest_count), event["Venue_Capacity"], event["Venue_Name"])
        if errors:
            show_errors(errors)
            return
        try:
            run_write(
                "UPDATE EVENT SET Status=%s, Event_Date=%s, Guest_Count=%s WHERE Event_ID=%s",
                (status, event_date, int(guest_count), eid),
            )
            flash("success", f"Event #{eid} updated.")
            st.rerun()
        except mysql.connector.Error as err:
            st.error(friendly_db_error(err))


def delete_event_tab():
    st.subheader("Delete an event")
    event = pick_event("del_event_select")
    if event is None:
        return
    eid = event["Event_ID"]
    st.write(f"**{event['Event_Name']}** on {event['Event_Date']} for {event['Client_Name']} "
             f"at {event['Venue_Name']} | {event['Guest_Count']} guests | {event['Status']}")
    confirm = st.checkbox("Yes, I want to permanently delete this event.", key=f"del_event_confirm_{eid}")
    if st.button("Delete event", type="primary", disabled=not confirm):
        try:
            run_write("DELETE FROM EVENT WHERE Event_ID = %s", (eid,))
            flash("success", f"Deleted event #{eid}: {event['Event_Name']}.")
            st.rerun()
        except mysql.connector.Error as err:
            st.error(friendly_db_error(
                err,
                f"Event #{eid} still has menu orders or staff assignments, so the database will "
                "not allow it to be deleted. Remove those first, or set the status to Cancelled instead.",
            ))


def events_page():
    st.header("Events")
    show_flash()
    tab_book, tab_browse, tab_edit, tab_delete = st.tabs(
        ["Book event", "Browse / search", "Edit event", "Delete event"]
    )
    with tab_book:
        book_event_tab()
    with tab_browse:
        browse_events_tab()
    with tab_edit:
        edit_event_tab()
    with tab_delete:
        delete_event_tab()


# ----------------------------------------------------------------------------
# Reports page (queries match reports.sql)
# ----------------------------------------------------------------------------
REPORT_1_SQL = """SELECT e.Event_Name,
       e.Event_Date,
       COALESCE(c.Company_Name, CONCAT(c.Client_FName, ' ', c.Client_LName)) AS Client,
       v.Venue_Name,
       m.Item_Name,
       o.Quantity,
       o.Unit_Price,
       o.Quantity * o.Unit_Price AS Line_Total
FROM EVENT_ORDERS o
JOIN EVENT e     ON o.Event_ID = e.Event_ID
JOIN CLIENT c    ON e.Client_ID = c.Client_ID
JOIN VENUE v     ON e.Venue_ID = v.Venue_ID
JOIN MENU_ITEM m ON o.Menu_Item_ID = m.Menu_Item_ID
ORDER BY e.Event_Date, e.Event_ID, m.Item_Name"""

REPORT_2_SQL = """SELECT m.Item_Category,
       SUM(o.Quantity * o.Unit_Price) AS Total_Revenue
FROM EVENT_ORDERS o
JOIN EVENT e     ON o.Event_ID = e.Event_ID
JOIN MENU_ITEM m ON o.Menu_Item_ID = m.Menu_Item_ID
WHERE e.Status = 'Completed'
GROUP BY m.Item_Category
ORDER BY Total_Revenue DESC"""

REPORT_3_SQL = """SELECT Event_Name, Event_Date, Guest_Count
FROM EVENT
WHERE Event_Date BETWEEN %s AND %s
  AND Guest_Count >= %s
  AND Status = 'Confirmed'
ORDER BY Event_Date"""


def report_1():
    st.subheader("Report 1. Event menu detail")
    st.caption("What menu items were ordered for each event, and what is the line total for each item?")
    st.code(REPORT_1_SQL, language="sql")
    rows = run_query(REPORT_1_SQL)
    if not rows:
        st.info("No orders found.")
        return
    df = pd.DataFrame(rows)
    st.caption(f"{len(df)} line(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)


def report_2():
    st.subheader("Report 2. Revenue by menu category")
    st.caption("How much revenue did each menu category generate from completed events?")
    st.code(REPORT_2_SQL, language="sql")
    rows = run_query(REPORT_2_SQL)
    if not rows:
        st.info("No completed events with orders found.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.bar_chart(df.set_index("Item_Category")["Total_Revenue"].astype(float))


def report_3():
    st.subheader("Report 3. Upcoming events")
    st.caption("Which confirmed events fall within the selected date range and meet the minimum guest count?")
    col1, col2, col3 = st.columns(3)
    start = col1.date_input("Start date", value=date(2026, 12, 1), key="r3_start")
    end = col2.date_input("End date", value=date(2026, 12, 31), key="r3_end")
    min_guests = col3.number_input("Minimum guests", min_value=0, value=100, step=10, key="r3_min")
    if start > end:
        st.error("Start date must be on or before the end date.")
        return
    shown_sql = (REPORT_3_SQL.replace("%s", "'{}'", 1).replace("%s", "'{}'", 1)
                 .replace("%s", "{}", 1).format(start, end, int(min_guests)))
    st.code(shown_sql, language="sql")
    rows = run_query(REPORT_3_SQL, (start, end, int(min_guests)))
    if not rows:
        st.info("No confirmed events match these filters.")
        return
    df = pd.DataFrame(rows)
    st.caption(f"{len(df)} event(s)")
    st.dataframe(df, use_container_width=True, hide_index=True)


def reports_page():
    st.header("Reports")
    choice = st.radio(
        "Choose a report",
        ["Report 1: Event menu detail", "Report 2: Revenue by category", "Report 3: Upcoming events"],
        horizontal=True,
    )
    if choice.startswith("Report 1"):
        report_1()
    elif choice.startswith("Report 2"):
        report_2()
    else:
        report_3()



# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    st.sidebar.title("Canes Catering Company")
    page = st.sidebar.radio("Go to", ["Events", "Clients", "Reports"])

    try:
        get_connection().close()
    except (mysql.connector.Error, KeyError, FileNotFoundError) as err:
        st.error(
            "Could not connect to the canes_catering database. Check that MySQL is running, "
            "that schema.sql and seed_data.sql have been loaded, and that "
            ".streamlit/secrets.toml has your [mysql] settings (see README)."
        )
        st.caption(f"Details: {err}")
        st.stop()

    if page == "Clients":
        clients_page()
    elif page == "Reports":
        reports_page()
    else:
        events_page()


main()
