import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "blood.db"

# ---------- CREATE DATABASE ----------
def create_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Users table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        age INTEGER,
        weight REAL,
        blood TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
        last_donated TEXT,
        is_donor INTEGER DEFAULT 0,
        is_available INTEGER DEFAULT 1,
        role TEXT DEFAULT 'donor',
        is_admin INTEGER DEFAULT 0
    )
    ''')

    # Requests table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        gender TEXT,
        age INTEGER,
        blood TEXT,
        units_required INTEGER,
        hospital TEXT,
        contact_number TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
        requester_id INTEGER,
        is_emergency INTEGER DEFAULT 0
    )
    ''')

    # Blood banks table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS blood_banks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        blood_groups_available TEXT,
        phone TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
        email TEXT UNIQUE,
        password TEXT
    )
    ''')

    # Donation Drives table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS drives(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_id INTEGER,
        title TEXT,
        date TEXT,
        deadline TEXT,
        location TEXT,
        description TEXT,
        status TEXT DEFAULT 'open',
        registration_limit INTEGER,
        registration_open INTEGER DEFAULT 1
    )
    ''')
    
    # Drive Notifications table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS drive_notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER,
        drive_id INTEGER,
        message TEXT,
        created_at TEXT,
        is_read INTEGER DEFAULT 0
    )
    ''')

    # Drive Registrations table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS drive_registrations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_id INTEGER,
        donor_id INTEGER,
        status TEXT DEFAULT 'registered'
    )
    ''')

    # Donations table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS donations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER,
        request_id INTEGER,
        status TEXT
    )
    ''')

    # Notifications table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER,
        request_id INTEGER,
        status TEXT DEFAULT 'pending'
    )
    ''')

    # Request Blood Banks table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS request_blood_banks(
        request_id INTEGER,
        bank_id INTEGER,
        status TEXT DEFAULT 'pending'
    )
    ''')

    # Stories table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        image_url TEXT,
        date TEXT,
        privacy TEXT DEFAULT 'public'
    )
    ''')

    # Badges table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS badges(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        badge_type TEXT,
        date_earned TEXT
    )
    ''')

    conn.commit()

    cur.execute("PRAGMA table_info(drives)")
    columns = [row[1] for row in cur.fetchall()]
    if "status" not in columns:
        cur.execute("ALTER TABLE drives ADD COLUMN status TEXT DEFAULT 'open'")
        conn.commit()
    if "registration_limit" not in columns:
        cur.execute("ALTER TABLE drives ADD COLUMN registration_limit INTEGER")
        conn.commit()
    if "registration_open" not in columns:
        cur.execute("ALTER TABLE drives ADD COLUMN registration_open INTEGER DEFAULT 1")
        conn.commit()
    cur.execute("UPDATE drives SET registration_open = 1 WHERE status='open' AND (registration_open IS NULL OR registration_open = 0)")
    conn.commit()

    cur.execute("PRAGMA table_info(requests)")
    columns = [row[1] for row in cur.fetchall()]
    if "requester_id" not in columns:
        cur.execute("ALTER TABLE requests ADD COLUMN requester_id INTEGER")
        conn.commit()
    if "is_emergency" not in columns:
        cur.execute("ALTER TABLE requests ADD COLUMN is_emergency INTEGER DEFAULT 0")
        conn.commit()
    if "status" not in columns:
        cur.execute("ALTER TABLE requests ADD COLUMN status TEXT DEFAULT 'open'")
        conn.commit()

    cur.execute("PRAGMA table_info(blood_banks)")
    columns = [row[1] for row in cur.fetchall()]
    if "email" not in columns:
        cur.execute("ALTER TABLE blood_banks ADD COLUMN email TEXT")
        cur.execute("ALTER TABLE blood_banks ADD COLUMN password TEXT")
        conn.commit()

    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]
    if "role" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'donor'")
        conn.commit()
    if "is_admin" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.commit()

    conn.close()


def ensure_schema():
    create_db()
    remove_self_notifications()


def remove_self_notifications():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM notifications
        WHERE EXISTS (
            SELECT 1 FROM requests r
            WHERE r.id = notifications.request_id
            AND r.requester_id = notifications.donor_id
        )
    ''')
    conn.commit()
    conn.close()


    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Remove notifications, donations, requests, blood banks, and users created for test data.
    cur.execute("DELETE FROM notifications WHERE request_id IN (SELECT id FROM requests WHERE patient_name LIKE '%[TESTDATA]%' OR hospital LIKE '%[TESTDATA]%')")
    cur.execute("DELETE FROM donations WHERE request_id IN (SELECT id FROM requests WHERE patient_name LIKE '%[TESTDATA]%' OR hospital LIKE '%[TESTDATA]%')")
    cur.execute("DELETE FROM requests WHERE patient_name LIKE '%[TESTDATA]%' OR hospital LIKE '%[TESTDATA]%'")
    cur.execute("DELETE FROM blood_banks WHERE name LIKE '%TESTDATA%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'testdata+%@example.com' OR name LIKE '%[TESTDATA]%' OR phone LIKE '+1000000%'")

    conn.commit()
    conn.close()


def mark_request_completed(request_id, actual_donors=None, actual_banks=None):
    if actual_donors is None:
        actual_donors = []
    if actual_banks is None:
        actual_banks = []

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Close the request
    cur.execute("UPDATE requests SET status='completed' WHERE id=?", (request_id,))

    # Only credit donors who actually donated
    cur.execute("SELECT donor_id, request_id FROM notifications WHERE request_id=? AND status='accepted'", (request_id,))
    accepted_notifications = cur.fetchall()
    
    for donor_id, req_id in accepted_notifications:
        if str(donor_id) in map(str, actual_donors):
            cur.execute("UPDATE notifications SET status='completed' WHERE donor_id=? AND request_id=?", (donor_id, req_id))
            cur.execute("SELECT 1 FROM donations WHERE donor_id=? AND request_id=?", (donor_id, req_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO donations (donor_id, request_id, status) VALUES (?, ?, 'completed')", (donor_id, req_id))
                from datetime import date
                cur.execute("UPDATE users SET last_donated=? WHERE id=?", (date.today().isoformat(), donor_id))
        else:
            cur.execute("UPDATE notifications SET status='declined' WHERE donor_id=? AND request_id=?", (donor_id, req_id))

    # Hide all pending notifications for this request
    cur.execute("UPDATE notifications SET status='declined' WHERE request_id=? AND status='pending'", (request_id,))

    # Remove unfulfilled blood banks from the request record
    cur.execute("SELECT bank_id FROM request_blood_banks WHERE request_id=?", (request_id,))
    selected_banks = cur.fetchall()
    for (bank_id,) in selected_banks:
        if str(bank_id) not in map(str, actual_banks):
            cur.execute("DELETE FROM request_blood_banks WHERE request_id=? AND bank_id=?", (request_id, bank_id))

    conn.commit()
    conn.close()


def delete_request(request_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM requests WHERE id=?", (request_id,))
    cur.execute("DELETE FROM notifications WHERE request_id=?", (request_id,))
    cur.execute("DELETE FROM donations WHERE request_id=?", (request_id,))
    cur.execute("DELETE FROM request_blood_banks WHERE request_id=?", (request_id,))
    conn.commit()
    conn.close()


def get_open_requests_by_requester(requester_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE requester_id=? AND status='open' ORDER BY id DESC", (requester_id,))
    requests = cur.fetchall()
    conn.close()
    return requests


def get_completed_requests_by_requester(requester_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE requester_id=? AND status='completed' ORDER BY id DESC", (requester_id,))
    requests = cur.fetchall()
    conn.close()
    return requests


# ---------- USERS ----------
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    conn.close()
    return users


def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def add_user(name, email, password, phone, age=None, weight=None, blood=None, location=None, last_donated=None, is_donor=0, is_available=0, latitude=None, longitude=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    role = 'donor' if is_donor else 'requester'
    password_hash = generate_password_hash(password)
    cur.execute('''
        INSERT INTO users (name, email, password, phone, age, weight, blood, location, latitude, longitude, last_donated, is_donor, is_available, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, password_hash, phone, age, weight, blood, location, latitude, longitude, last_donated, is_donor, is_available, role))
    conn.commit()
    conn.close()


def get_user_by_email_or_phone(identifier):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=? OR phone=?", (identifier, identifier))
    user = cur.fetchone()
    conn.close()
    return user


# ---------- REQUESTS ----------
def get_all_requests():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests")
    requests = cur.fetchall()
    conn.close()
    return requests


def add_request(patient_name, gender, age, blood, units_required, hospital, contact_number, location, latitude=None, longitude=None, requester_id=None, is_emergency=0):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO requests (patient_name, gender, age, blood, units_required, hospital, contact_number, location, latitude, longitude, requester_id, is_emergency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (patient_name, gender, age, blood, units_required, hospital, contact_number, location, latitude, longitude, requester_id, is_emergency))
    request_id = cur.lastrowid
    conn.commit()
    conn.close()
    return request_id


def get_requests_by_requester(requester_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE requester_id=? ORDER BY id DESC", (requester_id,))
    requests = cur.fetchall()
    conn.close()
    return requests


def get_request_by_id(request_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM requests WHERE id=?", (request_id,))
    request_row = cur.fetchone()
    conn.close()
    return request_row


def get_notifications_by_request(request_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM notifications WHERE request_id=?", (request_id,))
    notifications = cur.fetchall()
    conn.close()
    return notifications


def add_request_blood_bank(request_id, bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO request_blood_banks (request_id, bank_id)
        VALUES (?, ?)
    ''', (request_id, bank_id))
    conn.commit()
    conn.close()


def get_blood_banks_for_request(request_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT b.id, b.name, b.phone, b.location, b.latitude, b.longitude, rb.status
        FROM blood_banks b
        JOIN request_blood_banks rb ON b.id = rb.bank_id
        WHERE rb.request_id=?
    ''', (request_id,))
    banks = cur.fetchall()
    conn.close()
    return banks

def get_bank_requests(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT r.*, rb.status as bank_status
        FROM requests r
        JOIN request_blood_banks rb ON r.id = rb.request_id
        WHERE rb.bank_id=? AND r.status='open' ORDER BY r.id DESC
    ''', (bank_id,))
    reqs = cur.fetchall()
    conn.close()
    return reqs


def get_bank_completed_requests(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT r.*, rb.status as bank_status
        FROM requests r
        JOIN request_blood_banks rb ON r.id = rb.request_id
        WHERE rb.bank_id=? AND r.status='completed' AND rb.status='accepted' ORDER BY r.id DESC
    ''', (bank_id,))
    reqs = cur.fetchall()
    conn.close()
    return reqs


def delete_request_blood_bank(request_id, bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM request_blood_banks WHERE request_id=? AND bank_id=?", (request_id, bank_id))
    conn.commit()
    conn.close()


def update_bank_request_status(request_id, bank_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE request_blood_banks SET status=? WHERE request_id=? AND bank_id=?", (status, request_id, bank_id))
    conn.commit()
    conn.close()


def add_notification(donor_id, request_id, status='pending'):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO notifications (donor_id, request_id, status)
        VALUES (?, ?, ?)
    ''', (donor_id, request_id, status))
    conn.commit()
    conn.close()


def get_notifications_for_donor(donor_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT n.id, n.request_id, n.status, r.patient_name, r.blood, r.hospital, r.location, r.units_required, r.contact_number, r.is_emergency
        FROM notifications n
        JOIN requests r ON n.request_id = r.id
        WHERE n.donor_id = ? AND n.status != 'declined' AND r.status = 'open' AND r.requester_id != ?
        ORDER BY r.is_emergency DESC, n.id DESC
    ''', (donor_id, donor_id))
    notifications = cur.fetchall()
    conn.close()
    return notifications


def get_notification_by_id(notification_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM notifications WHERE id=?", (notification_id,))
    notification = cur.fetchone()
    conn.close()
    return notification


def update_notification_status(notification_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET status=? WHERE id=?", (status, notification_id))
    conn.commit()
    conn.close()


def get_donations_for_donor(donor_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT d.id, d.status, r.patient_name, r.blood, r.hospital, r.location, r.units_required
        FROM donations d
        JOIN requests r ON d.request_id = r.id
        WHERE d.donor_id = ?
        ORDER BY d.id DESC
    ''', (donor_id,))
    donations = cur.fetchall()
    conn.close()
    return donations


def get_compatible_donors():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE is_donor=1 AND is_available=1")
    donors = cur.fetchall()
    conn.close()
    return donors


# ---------- BLOOD BANKS ----------
def get_all_blood_banks():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM blood_banks")
    banks = cur.fetchall()
    conn.close()
    return banks


def add_blood_bank(name, blood_groups_available, phone, location, email, password, latitude=None, longitude=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    password_hash = generate_password_hash(password)
    cur.execute('''
        INSERT INTO blood_banks (name, blood_groups_available, phone, location, latitude, longitude, email, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, blood_groups_available, phone, location, latitude, longitude, email, password_hash))
    conn.commit()
    conn.close()

def get_blood_bank_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM blood_banks WHERE email=?", (email,))
    bank = cur.fetchone()
    conn.close()
    return bank

def get_blood_bank_by_id(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM blood_banks WHERE id=?", (bank_id,))
    bank = cur.fetchone()
    conn.close()
    return bank

def update_blood_bank_email(bank_id, email):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE blood_banks SET email=? WHERE id=?", (email, bank_id))
    conn.commit()
    conn.close()

def update_blood_bank_inventory(bank_id, inventory):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE blood_banks SET blood_groups_available=? WHERE id=?", (inventory, bank_id))
    conn.commit()
    conn.close()

# ---------- DRIVES ----------

def create_drive(bank_id, title, date, deadline, location, description, registration_limit=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO drives (bank_id, title, date, deadline, location, description, registration_limit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (bank_id, title, date, deadline, location, description, registration_limit))
    conn.commit()
    conn.close()

def get_all_open_drives():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT d.*, b.name as bank_name
        FROM drives d 
        JOIN blood_banks b ON d.bank_id = b.id 
        WHERE d.status='open' ORDER BY d.id DESC
    ''')
    drives = cur.fetchall()
    conn.close()
    return drives

def get_drives_by_bank(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM drives WHERE bank_id=? ORDER BY id DESC", (bank_id,))
    drives = cur.fetchall()
    conn.close()
    return drives


def get_drive_by_id(drive_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM drives WHERE id=?", (drive_id,))
    drive = cur.fetchone()
    conn.close()
    return drive


def update_drive_settings(drive_id, bank_id, registration_open=None, registration_limit=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fields = []
    values = []
    if registration_open is not None:
        fields.append("registration_open = ?")
        values.append(1 if registration_open else 0)
    if registration_limit is not None:
        fields.append("registration_limit = ?")
        values.append(registration_limit)
    if not fields:
        conn.close()
        return
    values.extend([drive_id, bank_id])
    cur.execute(f"UPDATE drives SET {', '.join(fields)} WHERE id=? AND bank_id=?", values)
    conn.commit()
    conn.close()


def add_drive_notification(donor_id, drive_id, message):
    from datetime import datetime
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO drive_notifications (donor_id, drive_id, message, created_at, is_read)
        VALUES (?, ?, ?, ?, 0)
    ''', (donor_id, drive_id, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_drive_notifications_for_donor(donor_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT n.message, n.created_at, d.title
        FROM drive_notifications n
        LEFT JOIN drives d ON n.drive_id = d.id
        WHERE n.donor_id = ?
        ORDER BY n.id DESC
    ''', (donor_id,))
    notes = cur.fetchall()
    conn.close()
    return notes


def cancel_bank_drive(drive_id, bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM drives WHERE id=? AND bank_id=?", (drive_id, bank_id))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute("UPDATE drives SET status='cancelled' WHERE id=?", (drive_id,))
    cur.execute("SELECT donor_id FROM drive_registrations WHERE drive_id=?", (drive_id,))
    registrations = cur.fetchall()
    conn.commit()
    conn.close()

    for (donor_id,) in registrations:
        add_drive_notification(donor_id, drive_id, "Sorry, this donation drive has been called off by the blood bank.")
    return True


def register_for_drive(donor_id, drive_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT status, registration_open, registration_limit FROM drives WHERE id=?", (drive_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, 'Drive not found.'
    status, registration_open, registration_limit = row
    if status != 'open':
        conn.close()
        return False, 'This drive is no longer accepting registrations.'
    if registration_open == 0:
        conn.close()
        return False, 'Registrations for this drive are closed.'
    if registration_limit is not None:
        cur.execute("SELECT COUNT(*) FROM drive_registrations WHERE drive_id=?", (drive_id,))
        count = cur.fetchone()[0]
        if count >= registration_limit:
            conn.close()
            return False, 'This drive has reached its registration limit.'
    cur.execute("SELECT 1 FROM drive_registrations WHERE donor_id=? AND drive_id=?", (donor_id, drive_id))
    if not cur.fetchone():
        cur.execute("INSERT INTO drive_registrations (drive_id, donor_id) VALUES (?, ?)", (drive_id, donor_id))
        conn.commit()
    conn.close()
    return True, None


def cancel_drive_registration(donor_id, drive_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM drive_registrations WHERE donor_id=? AND drive_id=?", (donor_id, drive_id))
    conn.commit()
    conn.close()

def get_drive_registrations(drive_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT u.id, u.name, u.phone, u.blood, d.status
        FROM drive_registrations d
        JOIN users u ON d.donor_id = u.id
        WHERE d.drive_id=?
    ''', (drive_id,))
    regs = cur.fetchall()
    conn.close()
    return regs

def complete_drive(drive_id, actual_donors):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    from datetime import date
    today = date.today().isoformat()
    
    cur.execute("UPDATE drives SET status='completed' WHERE id=?", (drive_id,))
    cur.execute("SELECT donor_id FROM drive_registrations WHERE drive_id=?", (drive_id,))
    registrations = cur.fetchall()
    
    for (donor_id,) in registrations:
        if str(donor_id) in map(str, actual_donors):
            cur.execute("UPDATE drive_registrations SET status='completed' WHERE donor_id=? AND drive_id=?", (donor_id, drive_id))
            cur.execute("UPDATE users SET last_donated=? WHERE id=?", (today, donor_id))
        else:
            cur.execute("UPDATE drive_registrations SET status='no_show' WHERE donor_id=? AND drive_id=?", (donor_id, drive_id))
            
    conn.commit()
    conn.close()

def delete_drive(drive_id, bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM drives WHERE id=? AND bank_id=?", (drive_id, bank_id))
    cur.execute("DELETE FROM drive_registrations WHERE drive_id=?", (drive_id,))
    conn.commit()
    conn.close()


def delete_drives_by_bank(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM drives WHERE bank_id=?", (bank_id,))
    drive_ids = [row[0] for row in cur.fetchall()]
    cur.execute("DELETE FROM drives WHERE bank_id=?", (bank_id,))
    cur.executemany("DELETE FROM drive_registrations WHERE drive_id=?", [(drive_id,) for drive_id in drive_ids])
    conn.commit()
    conn.close()


def delete_blood_bank(bank_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    delete_drives_by_bank(bank_id)
    cur.execute("DELETE FROM blood_banks WHERE id=?", (bank_id,))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    cur.execute("DELETE FROM notifications WHERE donor_id=?", (user_id,))
    cur.execute("DELETE FROM drive_registrations WHERE donor_id=?", (user_id,))
    cur.execute("DELETE FROM drive_notifications WHERE donor_id=?", (user_id,))
    conn.commit()
    conn.close()


# ---------- STORIES ----------
def add_story(user_id, content, image_url=None, privacy='public'):
    from datetime import datetime
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO stories (user_id, content, image_url, date, privacy) VALUES (?, ?, ?, ?, ?)", (user_id, content, image_url, datetime.now().isoformat(), privacy))
    conn.commit()
    conn.close()

def get_stories():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT s.*, u.name FROM stories s JOIN users u ON s.user_id = u.id WHERE s.privacy='public' ORDER BY s.date DESC")
    stories = cur.fetchall()
    conn.close()
    return stories

# ---------- BADGES ----------
def add_badge(user_id, badge_type):
    from datetime import datetime
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO badges (user_id, badge_type, date_earned) VALUES (?, ?, ?)", (user_id, badge_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_badges_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM badges WHERE user_id=?", (user_id,))
    badges = cur.fetchall()
    conn.close()
    return badges

def update_donor_status(user_id, is_donor):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET is_donor=? WHERE id=?', (is_donor, user_id))
    conn.commit()
    conn.close()
