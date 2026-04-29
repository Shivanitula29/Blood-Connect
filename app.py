import os
from flask import Flask, redirect, request, jsonify, render_template, session, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
from flask_cors import CORS
from functools import wraps
from werkzeug.security import check_password_hash
from database import (
    get_all_users,
    get_all_blood_banks,
    add_blood_bank,
    ensure_schema,
    add_user,
    get_user_by_id,
    get_user_by_email_or_phone,
    add_request,
    get_compatible_donors,
    add_notification,
    get_notifications_for_donor,
    get_notification_by_id,
    update_notification_status,
    get_donations_for_donor,
    update_donor_status,
    get_requests_by_requester,
    get_request_by_id,
    get_notifications_by_request,
    get_open_requests_by_requester,
    get_completed_requests_by_requester,
    mark_request_completed,
    add_request_blood_bank,
    get_blood_banks_for_request,
    get_bank_completed_requests,
    delete_request_blood_bank,
    delete_request,
    get_blood_bank_by_email,
    get_blood_bank_by_id,
    update_blood_bank_email,
    update_blood_bank_inventory,
    get_bank_requests,
    update_bank_request_status,
    create_drive,
    get_all_open_drives,
    get_drives_by_bank,
    register_for_drive,
    cancel_drive_registration,
    get_drive_registrations,
    complete_drive,
    delete_drive,
    update_drive_settings,
    cancel_bank_drive,
    get_drive_notifications_for_donor,
    delete_user,
    delete_blood_bank,
    get_all_requests,
    add_story,
    get_stories,
    add_badge,
    get_badges_by_user
)
from io import BytesIO
from reportlab.pdfgen import canvas
import sqlite3
from math import radians, sin, cos, sqrt, atan2
import random
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-dev-key')
CORS(app)

ensure_schema()

@app.context_processor
def inject_user():
    return {'user': session.get('user')}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('user'):
            next_page = request.path
            if request.query_string:
                next_page += '?' + request.query_string.decode('utf-8')
            return redirect(f"/login?next={next_page}")
        return view(*args, **kwargs)
    return wrapped_view


# ---------- Database Connection ----------
def db():
    return sqlite3.connect('blood.db')


# ---------- Distance Function ----------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# ---------- Blood Compatibility ----------
compat = {
    "O+": ["O+", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
    "O-": ["O-"],
    "A-": ["A-", "O-"],
    "B-": ["B-", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"]
}


# ---------- PAGES ----------
@app.route('/')
def home():
    user = session.get('user')
    drives_raw = get_all_open_drives()
    drives = []
    
    if user and user.get('role') == 'donor':
        donor_id = user['id']
        for d in drives_raw:
            regs = get_drive_registrations(d[0]) # d[0] is drive_id
            is_reg = any(r[0] == donor_id for r in regs) # r[0] is donor id
            drives.append({
                'id': d[0],
                'title': d[2],
                'date': d[3],
                'deadline': d[4],
                'location': d[5],
                'description': d[6],
                'bank_name': d[8],  # index 8 is b.name
                'is_registered': is_reg
            })
    else:
        # If not logged in or is a bank, just show drives without registration status
        for d in drives_raw:
            drives.append({
                'id': d[0],
                'title': d[2],
                'date': d[3],
                'deadline': d[4],
                'location': d[5],
                'description': d[6],
                'bank_name': d[8],
                'is_registered': False
            })

    return render_template("index.html", drives=drives)


@app.route('/drives')
@login_required
def drives_page():
    user = session.get('user')
    drives_raw = get_all_open_drives()
    drives = []
    
    if user and user.get('role') == 'donor':
        donor_id = user['id']
        for d in drives_raw:
            regs = get_drive_registrations(d[0]) # d[0] is drive_id
            is_reg = any(r[0] == donor_id for r in regs) # r[0] is donor id
            drives.append({
                'id': d[0],
                'title': d[2],
                'date': d[3],
                'deadline': d[4],
                'location': d[5],
                'description': d[6],
                'bank_name': d[8],  # index 8 is b.name
                'is_registered': is_reg
            })
    else:
        # If not logged in or is a bank, just show drives without registration status
        for d in drives_raw:
            drives.append({
                'id': d[0],
                'title': d[2],
                'date': d[3],
                'deadline': d[4],
                'location': d[5],
                'description': d[6],
                'bank_name': d[8],
                'is_registered': False
            })

    return render_template("drives.html", drives=drives)


@app.route('/donor')
@login_required
def donor_page():
    return render_template("donor.html")


@app.route('/request')
@login_required
def request_page():
    return render_template("request.html")


@app.route('/emergency')
@login_required
def emergency_page():
    request_id = request.args.get('request_id')
    if request_id:
        req = get_request_by_id(request_id)
        if req and req[11] == session['user']['id'] and req[12]:  # is_emergency
            return render_template("emergency.html", show_tracker=True, request_id=request_id)
    return render_template("emergency.html")


@app.route('/education')
@login_required
def education_page():
    return render_template("education.html")


@app.route('/stories')
@login_required
def stories_page():
    stories = get_stories()
    return render_template("stories.html", stories=stories)


@app.route('/certificate/<int:user_id>')
@login_required
def certificate(user_id):
    if session['user']['id'] != user_id:
        return "Unauthorized", 403
    # Placeholder for PDF generation
    return "Certificate PDF would be generated here"


@app.route('/bloodbank')
def bloodbank_page():
    return render_template("bloodbank.html")

@app.route('/addBloodBank', methods=['POST'])
def add_bloodbank():
    name = request.form.get("name")
    phone = request.form.get("phone")
    location = request.form.get("location")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    blood_groups = request.form.get("blood_groups_available")
    email = request.form.get("email")
    password = request.form.get("password")
    
    # minimal validation
    if not email or not password or not name:
        return render_template("bloodbank.html", error="Email, password, and name are required.")
    
    try:
        add_blood_bank(name, blood_groups, phone, location, email, password, float(latitude) if latitude else None, float(longitude) if longitude else None)
        return render_template("login.html", success="Blood Bank registered successfully! Please log in.")
    except Exception as e:
        return render_template("bloodbank.html", error="Could not register blood bank. Email might already be taken.")


# ---------- AUTH PAGES ----------
@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        age = request.form.get("age", "")
        weight = request.form.get("weight", "")
        blood = request.form.get("blood", "")
        location = request.form.get("location", "").strip()
        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")
        is_donor = int(request.form.get("is_donor", 0))
        last_donated = request.form.get("last_donated") or None
        # Backend validations
        if not name or len(name) < 2:
            return render_template("signup.html", error="Name must be at least 2 characters long.")

        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
            return render_template("signup.html", error="Please enter a valid email address.")

        if len(password) < 6:
            return render_template("signup.html", error="Password must be at least 6 characters long.")

        if not re.match(r"^\+?[\d\s\-\(\)]{10,}$", phone):
            return render_template("signup.html", error="Please enter a valid phone number.")

        try:
            age_num = int(age)
            if age_num < 18 or age_num > 65:
                return render_template("signup.html", error="Age must be between 18 and 65.")
        except:
            return render_template("signup.html", error="Please enter a valid age.")

        try:
            weight_num = float(weight)
            if weight_num < 45 or weight_num > 150:
                return render_template("signup.html", error="Weight must be between 45kg and 150kg.")
        except:
            return render_template("signup.html", error="Please enter a valid weight.")

        if not blood:
            return render_template("signup.html", error="Please select your blood group.")

        if not location or not latitude or not longitude:
            return render_template("signup.html", error="Please select a valid location.")

        is_available = 1 if is_donor else 0

        try:
            add_user(name, email, password, phone, age_num, weight_num, blood, location, last_donated, is_donor, is_available, float(latitude), float(longitude))
            return render_template("login.html", success="Account created successfully! Please log in.")
        except Exception as e:
            return render_template("signup.html", error="Could not create account. Please try again.")

    return render_template("signup.html")


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == "POST":
        identifier = request.form.get("identifier")
        password = request.form.get("password")

        user = get_user_by_email_or_phone(identifier)
        if user and (check_password_hash(user[3], password) or user[3] == password):
            session['user'] = {
                "id": user[0],
                "name": user[1],
                "email": user[2],
                "role": user[15],
                "is_donor": bool(user[12]),
                "is_available": bool(user[13]),
                "is_admin": bool(user[16])
            }
            next_page = session.pop('next', '/profile')
            return redirect(next_page)
            
        bank = get_blood_bank_by_email(identifier)
        if bank and (check_password_hash(bank[8], password) or bank[8] == password):
            session['user'] = {
                "id": bank[0],
                "name": bank[1],
                "email": bank[7],
                "role": "bank",
                "is_admin": False
            }
            next_page = session.pop('next', '/profile')
            return redirect(next_page)

        return render_template("login.html", error="Invalid Credentials")

    next_page = request.args.get('next')
    if next_page:
        session['next'] = next_page

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


@app.route('/requestBlood', methods=['POST'])
@login_required
def request_blood():
    data = request.get_json() or request.form
    patient_name = data.get('patient_name')
    gender = data.get('gender')
    age = data.get('age')
    blood = data.get('blood')
    units_required = data.get('units_required')
    hospital = data.get('hospital')
    contact_number = data.get('contact_number')
    location = data.get('location')
    latitude = data.get('latitude') or None
    longitude = data.get('longitude') or None

    if not all([patient_name, gender, age, blood, units_required, hospital, contact_number, location]):
        return jsonify({"message": "Missing required fields."}), 400

    is_emergency = int(data.get('emergency', 0))

    request_id = add_request(
        patient_name,
        gender,
        age,
        blood,
        units_required,
        hospital,
        contact_number,
        location,
        latitude,
        longitude,
        requester_id=session['user']['id'],
        is_emergency=is_emergency
    )

    return jsonify({"request_id": request_id})


@app.route('/results/<int:request_id>')
@login_required
def show_results(request_id):
    req = get_request_by_id(request_id)
    if not req or req[11] != session['user']['id']:
        return "Request not found", 404

    compatible_blood_groups = compat.get(req[4], [req[4]])
    donors = get_compatible_donors()
    request_notifications = get_notifications_by_request(request_id)
    requested_donor_ids = {note[1] for note in request_notifications}

    donor_list = []
    for donor in donors:
        if donor[0] == session['user']['id']:
            continue
        donor_blood = donor[7]
        if req[12] or donor_blood in compatible_blood_groups:  # For emergency, show all donors
            distance = None
            if req[9] and req[10] and donor[9] and donor[10]:
                distance = haversine(req[9], req[10], donor[9], donor[10])
            donor_list.append({
                'id': donor[0],
                'name': donor[1],
                'blood': donor[7],
                'phone': donor[4],
                'location': donor[8],
                'last_donated': donor[11] or 'Never',
                'latitude': donor[9],
                'longitude': donor[10],
                'distance': distance,
                'already_requested': donor[0] in requested_donor_ids
            })
    donor_list.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))

    request_banks = get_blood_banks_for_request(request_id)
    requested_bank_ids = {bank[0] for bank in request_banks}

    blood_banks = get_all_blood_banks()
    bank_list = []
    for bank in blood_banks:
        if req[12] or req[4] in bank[2]:  # For emergency, show all banks
            distance = None
            if req[9] and req[10] and bank[5] is not None and bank[6] is not None:
                distance = haversine(req[9], req[10], bank[5], bank[6])
            bank_list.append({
                'id': bank[0],
                'name': bank[1],
                'blood_groups_available': bank[2],
                'phone': bank[3],
                'location': bank[4],
                'latitude': bank[5],
                'longitude': bank[6],
                'distance': distance,
                'already_requested': bank[0] in requested_bank_ids
            })
    bank_list.sort(key=lambda x: x['distance'] if x['distance'] is not None else float('inf'))

    request_notes = get_notifications_by_request(request_id)
    accepted_count = sum(1 for note in request_notes if note[3] == 'accepted')
    pending_count = sum(1 for note in request_notes if note[3] == 'pending')
    declined_count = sum(1 for note in request_notes if note[3] == 'declined')
    completed_count = sum(1 for note in request_notes if note[3] == 'completed')
    sent_to_count = len({note[1] for note in request_notes}) + len(get_blood_banks_for_request(request_id))
    if accepted_count:
        request_status = f"{accepted_count} accepted, {pending_count} pending"
    elif pending_count:
        request_status = "Waiting for donor responses"
    elif declined_count:
        request_status = "All donor responses declined"
    else:
        request_status = "No requests sent yet"

    return render_template('results.html',
        request_id=request_id,
        request_status=request_status,
        sent_to_count=sent_to_count,
        patient_name=req[1],
        patient_gender=req[2],
        patient_age=req[3],
        requested_blood=req[4],
        units_required=req[5],
        hospital=req[6],
        contact_number=req[7],
        request_location=req[8],
        donors=donor_list,
        blood_banks=bank_list,
        show_blood_banks="yes" if bank_list else "no",
        is_emergency=req[12]
    )


@app.route('/send-request', methods=['POST'])
@login_required
def send_request():
    request_id = request.form.get('request_id')
    is_emergency = request.form.get('is_emergency') == '1'
    selected_donors = request.form.getlist('selected_donors')
    selected_banks = request.form.getlist('selected_banks')

    if not selected_donors and not selected_banks:
        return "Please select at least one donor or blood bank.", 400

    req = get_request_by_id(request_id)
    if not req or req[11] != session['user']['id']:
        return "Request not found.", 404

    existing_notifications = get_notifications_by_request(request_id)
    existing_donor_ids = {note[1] for note in existing_notifications}

    for donor_id in selected_donors:
        donor_id_int = int(donor_id)
        if donor_id_int not in existing_donor_ids:
            add_notification(donor_id_int, request_id)

    existing_banks = get_blood_banks_for_request(request_id)
    existing_bank_ids = {bank[0] for bank in existing_banks}
    for bank_id in selected_banks:
        bank_id_int = int(bank_id)
        if bank_id_int not in existing_bank_ids:
            add_request_blood_bank(request_id, bank_id_int)

    if is_emergency:
        # For emergency, after sending, redirect to emergency tracker
        return redirect(f'/emergency?request_id={request_id}')
    else:
        # For standard, redirect to profile or something
        return redirect('/profile')


@app.route('/profile')
@login_required
def profile_page():
    user = session['user']
    
    if user.get('role') == 'bank':
        bank_requests_raw = get_bank_requests(user['id'])
        bank_requests = []
        accepted_requests_count = 0
        for req in bank_requests_raw:
            bank_status = req[-1] if len(req) > 0 else None
            if bank_status == 'accepted':
                accepted_requests_count += 1
            bank_requests.append({
                'id': req[0],
                'patient_name': req[1],
                'blood': req[4],
                'units_required': req[5],
                'hospital': req[6],
                'location': req[8],
                'bank_status': bank_status
            })

        bank_history_raw = get_bank_completed_requests(user['id'])
        bank_history = []
        for req in bank_history_raw:
            bank_history.append({
                'id': req[0],
                'patient_name': req[1],
                'blood': req[4],
                'units_required': req[5],
                'hospital': req[6],
                'location': req[8],
                'bank_status': req[-1] if len(req) > 0 else None
            })

        bank_drives_raw = get_drives_by_bank(user['id'])
        bank_drives = []
        completed_drives_count = 0
        for d in bank_drives_raw:
            regs = get_drive_registrations(d[0])
            if d[7] == 'completed':
                completed_drives_count += 1
            bank_drives.append({
                'id': d[0],
                'title': d[2],
                'date': d[3],
                'deadline': d[4],
                'location': d[5],
                'description': d[6],
                'status': d[7],
                'registration_limit': d[8] if len(d) > 8 else None,
                'registration_open': bool(d[9]) if len(d) > 9 else True,
                'registration_count': len(regs),
                'registrations': regs
            })

        bank_info = get_blood_bank_by_id(user['id'])
        bank_inventory = {}
        if bank_info and bank_info[2]:
            for item in str(bank_info[2]).split(','):
                if ':' in item:
                    group, units = item.split(':', 1)
                    bank_inventory[group.strip()] = int(units) if units.isdigit() else units.strip()
                elif item.strip():
                    bank_inventory[item.strip()] = ''

        bank_achievements = {
            'total_drives': len(bank_drives),
            'completed_drives': completed_drives_count,
            'accepted_requests': accepted_requests_count,
            'inventory_groups': len(bank_inventory),
            'total_units_supplied': sum(req['units_required'] for req in bank_history)
        }

        return render_template(
            "profile.html",
            user=user,
            bank_requests=bank_requests,
            bank_drives=bank_drives,
            bank_info=bank_info,
            bank_inventory=bank_inventory,
            bank_achievements=bank_achievements,
            bank_history=bank_history
        )
        
    notifications = get_notifications_for_donor(user['id'])
    donations = get_donations_for_donor(user['id'])
    requests = get_open_requests_by_requester(user['id'])
    completed_requests_raw = get_completed_requests_by_requester(user['id'])

    emergency_requests = []
    standard_requests = []
    for req in requests:
        notes = get_notifications_by_request(req[0])
        is_emergency = bool(req[12])
        if any(note[3] == 'accepted' for note in notes):
            status = 'Accepted by a donor'
        elif any(note[3] == 'pending' for note in notes):
            status = 'Pending donor response'
        elif notes:
            status = 'No donor accepted yet'
        else:
            status = 'No responses yet'

        accepted_donors = []
        for note in notes:
            if note[3] == 'accepted':

                donor_info = get_user_by_id(note[1])
                if donor_info:
                    accepted_donors.append({
                        'id': donor_info[0],
                        'type': 'donor',
                        'name': donor_info[1],
                        'phone': donor_info[4],
                        'blood': donor_info[7],
                        'location': donor_info[8]
                    })
        
        request_banks = get_blood_banks_for_request(req[0])
        for b in request_banks:
            accepted_donors.append({
                'id': b[0],
                'type': 'bank',
                'name': 'Bank: ' + b[1],
                'phone': b[3],
                'blood': b[2],
                'location': b[4]
            })

        request_data = {
            'id': req[0],
            'patient_name': req[1],
            'blood': req[4],
            'units_required': req[5],
            'hospital': req[6],
            'location': req[8],
            'status': status,
            'is_emergency': is_emergency,
            'accepted_donors': accepted_donors
        }

        if is_emergency:
            emergency_requests.append(request_data)
        else:
            standard_requests.append(request_data)

    completed_requests = []
    for req in completed_requests_raw:
        accepted_donors = []
        for note in get_notifications_by_request(req[0]):
            if note[3] == 'completed':
                donor_info = get_user_by_id(note[1])
                if donor_info:
                    accepted_donors.append({
                        'name': donor_info[1],
                        'phone': donor_info[4],
                        'blood': donor_info[7],
                        'location': donor_info[8]
                    })

        request_banks = get_blood_banks_for_request(req[0])
        for b in request_banks:
            accepted_donors.append({
                'name': 'Bank: ' + b[1],
                'phone': b[3],
                'blood': b[2],
                'location': b[4]
            })

        completed_requests.append({
            'id': req[0],
            'patient_name': req[1],
            'blood': req[4],
            'units_required': req[5],
            'hospital': req[6],
            'location': req[8],
            'accepted_donors': accepted_donors
        })

    return render_template(
        "profile.html",
        notifications=notifications,
        donations=donations,
        emergency_requests=emergency_requests,
        standard_requests=standard_requests,
        completed_requests=completed_requests,
        bloodbanks=get_all_blood_banks(),
        badges=get_badges_by_user(user['id'])
    )


@app.route('/emergencyDonors')
def emergency_donors():
    blood = request.args.get('blood', '').upper()
    donors = get_compatible_donors()
    if blood:
        valid_groups = compat.get(blood, [blood])
        donors = [donor for donor in donors if donor[7] in valid_groups]

    donor_list = []
    for donor in donors:
        donor_list.append({
            'id': donor[0],
            'name': donor[1],
            'email': donor[2],
            'phone': donor[4],
            'blood': donor[7],
            'location': donor[8],
            'latitude': donor[9],
            'longitude': donor[10]
        })

    return jsonify(donor_list)


@app.route('/emergencyStatus')
@login_required
def emergency_status():
    request_id = request.args.get('request_id')
    if not request_id:
        return jsonify({'success': False, 'message': 'Missing request id.'}), 400

    req = get_request_by_id(request_id)
    if not req or req[11] != session['user']['id']:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404

    conn = db()
    cur = conn.cursor()
    cur.execute('''
        SELECT n.id, n.status, u.id, u.name, u.latitude, u.longitude, u.blood, u.phone, u.location
        FROM notifications n
        JOIN users u ON n.donor_id = u.id
        WHERE n.request_id = ?
    ''', (request_id,))
    notifications = cur.fetchall()
    conn.close()

    donors = []
    pending_count = 0
    accepted_count = 0
    for note in notifications:
        status = note[1]
        if status == 'pending':
            pending_count += 1
        if status == 'accepted':
            accepted_count += 1
            donor_lat = note[4]
            donor_lon = note[5]
            if donor_lat is not None and donor_lon is not None:
                donors.append({
                    'id': note[2],
                    'name': note[3],
                    'latitude': donor_lat,
                    'longitude': donor_lon,
                    'blood': note[6],
                    'phone': note[7],
                    'location': note[8],
                    'status': status
                })

    response = {
        'success': True,
        'request': {
            'id': req[0],
            'patient_name': req[1],
            'blood': req[4],
            'hospital': req[6],
            'location': req[8],
            'latitude': req[9],
            'longitude': req[10],
            'units_required': req[5],
            'is_emergency': bool(req[12])
        },
        'donors': donors,
        'pending_count': pending_count,
        'accepted_count': accepted_count
    }
    return jsonify(response)


@app.route('/complete-request', methods=['POST'])
@login_required
def complete_request_route():
    data = request.get_json() or request.form
    request_id = data.get('request_id')
    actual_donors = data.get('actual_donors', [])
    actual_banks = data.get('actual_banks', [])

    if not request_id:
        return jsonify({'success': False, 'message': 'Request ID required.'}), 400

    req = get_request_by_id(request_id)
    if not req or req[11] != session['user']['id']:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404

    if req[13] == 'completed':
        return jsonify({'success': False, 'message': 'Request already completed.'}), 400

    mark_request_completed(request_id, actual_donors, actual_banks)
    return jsonify({'success': True})


@app.route('/delete-request', methods=['POST'])
@login_required
def delete_request_route():
    data = request.get_json() or request.form
    request_id = data.get('request_id')

    if not request_id:
        return jsonify({'success': False, 'message': 'Request ID required.'}), 400

    req = get_request_by_id(request_id)
    if not req or req[11] != session['user']['id']:
        return jsonify({'success': False, 'message': 'Request not found.'}), 404

    delete_request(request_id)
    return jsonify({'success': True})


@app.route('/notification-action', methods=['POST'])
@login_required
def notification_action():
    data = request.get_json() or request.form
    notification_id = data.get('id')
    action = data.get('action')
    note = get_notification_by_id(notification_id)
    if not note:
        return jsonify({'success': False}), 404

    # Ensure it belongs to the logged in user
    if str(note[1]) != str(session['user']['id']) or session['user'].get('role') != 'donor':
        return jsonify({'success': False}), 403

    if action == 'accept':
        update_notification_status(notification_id, 'accepted')
    elif action == 'decline':
        update_notification_status(notification_id, 'declined')
    elif action == 'cancel':
        update_notification_status(notification_id, 'pending')

    return jsonify({'success': True})

@app.route('/bank-action', methods=['POST'])
@login_required
def bank_action():
    data = request.get_json() or request.form
    request_id = data.get('request_id')
    action = data.get('action')
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False}), 403

    bank_id = session['user']['id']
    if action == 'accept':
        update_bank_request_status(request_id, bank_id, 'accepted')
    elif action == 'decline':
        update_bank_request_status(request_id, bank_id, 'declined')
    elif action == 'delete':
        delete_request_blood_bank(request_id, bank_id)
    else:
        return jsonify({'success': False, 'message': 'Unknown action'}), 400
        
    return jsonify({'success': True})

@app.route('/update-donor-status', methods=['POST'])
@login_required
def update_donor_status_route():
    user = session['user']
    if user.get('role') != 'donor':
        return jsonify({'success': False}), 403
    
    data = request.get_json()
    action = data.get('action')
    is_donor = 1 if action == 'show' else 0
    
    update_donor_status(user['id'], is_donor)
    
    # Update session so the UI reflects the change on refresh
    user_data = get_user_by_id(user['id'])
    session['user'] = {
        'id': user_data[0],
        'name': user_data[1],
        'email': user_data[2],
        'phone': user_data[4],
        'role': 'donor',
        'is_donor': bool(user_data[12]),
        'is_available': bool(user_data[13])
    }
    session.modified = True
    
    return jsonify({'success': True, 'is_donor': is_donor})

# ---------- DONATION DRIVES ----------

@app.route('/create-drive', methods=['POST'])
@login_required
def create_drive_route():
    data = request.get_json() or request.form
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False}), 403
    
    bank_id = session['user']['id']
    title = data.get('title')
    date = data.get('date')
    deadline = data.get('deadline')
    location = data.get('location')
    description = data.get('description')
    registration_limit = data.get('registration_limit')
    limit_value = None
    if registration_limit not in (None, ''):
        try:
            limit_value = int(registration_limit)
        except ValueError:
            return jsonify({'success': False, 'message': 'Registration limit must be a number.'}), 400
    create_drive(bank_id, title, date, deadline, location, description, registration_limit=limit_value)
    return jsonify({'success': True})

@app.route('/register-drive', methods=['POST'])
@login_required
def register_drive_route():
    if session['user'].get('role') != 'donor':
        return jsonify({'success': False, 'message': 'Only donors may register for donation drives.'}), 403

    data = request.get_json() or request.form
    drive_id = data.get('drive_id')
    if not drive_id:
        return jsonify({'success': False, 'message': 'Drive ID is required.'}), 400

    try:
        drive_id = int(drive_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid drive ID.'}), 400

    success, message = register_for_drive(session['user']['id'], drive_id)
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    return jsonify({'success': True})

@app.route('/cancel-drive', methods=['POST'])
@login_required
def cancel_drive_route():
    data = request.get_json() or request.form
    if session['user'].get('role') != 'donor':
        return jsonify({'success': False}), 403
    
    drive_id = data.get('drive_id')
    cancel_drive_registration(session['user']['id'], drive_id)
    return jsonify({'success': True})

@app.route('/cancel-bank-drive', methods=['POST'])
@login_required
def cancel_bank_drive_route():
    data = request.get_json() or request.form
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False}), 403

    drive_id = data.get('drive_id')
    if not drive_id:
        return jsonify({'success': False, 'message': 'Drive ID required.'}), 400

    canceled = cancel_bank_drive(drive_id, session['user']['id'])
    if not canceled:
        return jsonify({'success': False, 'message': 'Drive not found or not authorized.'}), 404
    return jsonify({'success': True})

@app.route('/update-drive-settings', methods=['POST'])
@login_required
def update_drive_settings_route():
    data = request.get_json() or request.form
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False}), 403

    drive_id = data.get('drive_id')
    if not drive_id:
        return jsonify({'success': False, 'message': 'Drive ID required.'}), 400

    registration_open = data.get('registration_open')
    registration_limit = data.get('registration_limit')
    limit_value = None
    if registration_limit is not None and registration_limit != '':
        try:
            limit_value = int(registration_limit)
        except ValueError:
            return jsonify({'success': False, 'message': 'Registration limit must be a number.'}), 400

    update_drive_settings(drive_id, session['user']['id'], registration_open=(registration_open in [True, 'true', '1', 1]), registration_limit=limit_value)
    return jsonify({'success': True})

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account_route():
    user = session['user']
    if user.get('role') == 'bank':
        delete_blood_bank(user['id'])
    else:
        delete_user(user['id'])

    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/complete-drive', methods=['POST'])
@login_required
def complete_drive_route():
    data = request.get_json() or request.form
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False}), 403
    
    drive_id = data.get('drive_id')
    actual_donors = data.get('actual_donors', [])
    complete_drive(drive_id, actual_donors)
    return jsonify({'success': True})


@app.route('/update-bloodbank-stock', methods=['POST'])
@login_required
def update_bloodbank_stock():
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    data = request.get_json() or request.form
    blood_group = data.get('blood_group')
    units = data.get('units')

    if not blood_group or units is None:
        return jsonify({'success': False, 'message': 'Blood group and units are required.'}), 400

    try:
        units_int = int(units)
    except ValueError:
        return jsonify({'success': False, 'message': 'Units must be a number.'}), 400

    bank_info = get_blood_bank_by_id(session['user']['id'])
    if not bank_info:
        return jsonify({'success': False, 'message': 'Blood bank not found.'}), 404

    inventory = {}
    if bank_info[2]:
        for item in str(bank_info[2]).split(','):
            if ':' in item:
                group, count = item.split(':', 1)
                inventory[group.strip()] = int(count) if count.strip().isdigit() else count.strip()
            elif item.strip():
                inventory[item.strip()] = ''

    if units_int <= 0:
        inventory.pop(blood_group, None)
    else:
        inventory[blood_group] = units_int

    inventory_string = ','.join(f"{group}:{count}" for group, count in inventory.items())
    update_blood_bank_inventory(session['user']['id'], inventory_string)

    return jsonify({
        'success': True,
        'message': 'Inventory updated successfully.',
        'inventory': inventory
    })


@app.route('/send-bank-email-verification', methods=['POST'])
@login_required
def send_bank_email_verification():
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    data = request.get_json() or request.form
    new_email = data.get('new_email', '').strip()
    if not new_email:
        return jsonify({'success': False, 'message': 'Please enter a new email.'}), 400

    bank_info = get_blood_bank_by_id(session['user']['id'])
    if not bank_info:
        return jsonify({'success': False, 'message': 'Blood bank not found.'}), 404

    verification_code = str(random.randint(100000, 999999))
    expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()

    session['bank_email_change'] = {
        'old_email': bank_info[7],
        'new_email': new_email,
        'code': verification_code,
        'expires_at': expires_at
    }
    session.modified = True

    print(f"[Email verification] Code sent to {bank_info[7]}: {verification_code}")

    return jsonify({
        'success': True,
        'message': 'A verification code has been sent to your current email address. Please enter it to confirm the change.'
    })


@app.route('/confirm-bank-email-change', methods=['POST'])
@login_required
def confirm_bank_email_change():
    if session['user'].get('role') != 'bank':
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    data = request.get_json() or request.form
    code = data.get('code', '').strip()
    stored = session.get('bank_email_change')

    if not stored:
        return jsonify({'success': False, 'message': 'No email change request found.'}), 400

    if datetime.now() > datetime.fromisoformat(stored['expires_at']):
        session.pop('bank_email_change', None)
        return jsonify({'success': False, 'message': 'Verification code expired.'}), 400

    if code != stored['code']:
        return jsonify({'success': False, 'message': 'Invalid verification code.'}), 400

    try:
        update_blood_bank_email(session['user']['id'], stored['new_email'])
    except Exception as e:
        return jsonify({'success': False, 'message': 'Could not update email. It may already be in use.'}), 400

    session['user']['email'] = stored['new_email']
    session.modified = True
    session.pop('bank_email_change', None)

    return jsonify({
        'success': True,
        'message': 'Email updated successfully.'
    })


# ---------- NEW FEATURES ----------

@app.route('/add-story', methods=['POST'])
@login_required
def add_story_route():
    data = request.get_json()
    content = data.get('content')
    image_url = data.get('image_url')
    privacy = data.get('privacy', 'public')
    add_story(session['user']['id'], content, image_url, privacy)
    return jsonify({"success": True})


# ---------- ADMIN PANEL ----------
@app.route('/admin')
@login_required
def admin_page():
    if not session['user'].get('is_admin'):
        return redirect('/')
    users = get_all_users()
    requests = get_all_requests()
    return render_template("admin.html", users=users, requests=requests)


@app.route("/dashboard")
def dashboard():
    if session.get("admin"):
        users = get_all_users()  # now gets all users, including donors
        donors = [u for u in users if u[12]]  # is_donor = 1
        return render_template("dashboard.html", donors=donors)
    else:
        return redirect("/admin")


@app.route("/delete/<int:id>")
def delete_user(id):
    if session.get("admin"):
        conn = db()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return redirect("/dashboard")
    else:
        return redirect("/admin")


# ---------- API ROUTES ----------

@app.route('/get-user-data')
@login_required
def get_user_data():
    user_id = session['user']['id']
    user = get_user_by_id(user_id)
    if user:
        return jsonify({'success': True, 'user': {
            'name': user[1],
            'email': user[2],
            'phone': user[4],
            'age': user[5],
            'weight': user[6],
            'blood': user[7],
            'location': user[8]
        }})
    return jsonify({'success': False, 'message': 'User not found'})


@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    user_id = session['user']['id']
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    age = data.get('age')
    weight = data.get('weight')
    blood = data.get('blood')
    location = data.get('location')

    if not all([name, email, blood]):
        return jsonify({'success': False, 'message': 'Required fields missing'})

    try:
        conn = db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET name=?, email=?, phone=?, age=?, weight=?, blood=?, location=?
            WHERE id=?
        ''', (name, email, phone, age, weight, blood, location, user_id))
        conn.commit()
        conn.close()

        # Update session
        session['user']['name'] = name
        session['user']['email'] = email
        session['user']['blood'] = blood

        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/check-eligibility')
@login_required
def check_eligibility():
    user_id = session['user']['id']
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'eligible': False, 'message': 'User not found'})

    age = user[5]
    weight = user[6]
    last_donated = user[11]
    is_donor = user[12]

    # Check basic eligibility
    if not age or age < 18:
        return jsonify({'eligible': False, 'message': 'You must be at least 18 years old to donate blood.'})

    if not weight or weight < 50:
        return jsonify({'eligible': False, 'message': 'You must weigh at least 50 kg to donate blood.'})

    if not is_donor:
        return jsonify({'eligible': False, 'message': 'You have indicated you are not interested in donating blood.'})

    # Check donation frequency
    from datetime import datetime, timedelta

    if last_donated:
        try:
            last_date = datetime.strptime(last_donated, '%Y-%m-%d')
            next_date = last_date + timedelta(days=56)
            today = datetime.now()

            if today < next_date:
                days_left = (next_date - today).days
                return jsonify({
                    'eligible': False,
                    'message': f'You donated blood on {last_donated}. You can donate again in {days_left} days.',
                    'next_donation': next_date.strftime('%Y-%m-%d')
                })
            else:
                return jsonify({
                    'eligible': True,
                    'message': 'You are eligible to donate blood.',
                    'next_donation': None
                })
        except ValueError:
            # Invalid date format
            return jsonify({'eligible': True, 'message': 'You are eligible to donate blood.'})
    else:
        # First donation
        return jsonify({
            'eligible': True,
            'message': 'You are eligible to donate blood. This appears to be your first donation.'
        })


@app.route('/appointment')
@login_required
def appointment_page():
    user = session['user']
    blood_banks = get_all_blood_banks()
    
    # Get user's location
    user_lat = user.get('latitude')
    user_lon = user.get('longitude')
    
    if not user_lat or not user_lon:
        # If no location, show all banks without sorting
        sorted_banks = blood_banks
    else:
        # Sort by distance and add distance to each bank
        for bank in blood_banks:
            if bank[5] and bank[6]:
                bank_distance = haversine(float(user_lat), float(user_lon), float(bank[5]), float(bank[6]))
                bank.append(bank_distance)
            else:
                bank.append(None)
        sorted_banks = sorted(blood_banks, key=lambda b: b[-1] if b[-1] else float('inf'))
    
    return render_template("appointment.html", blood_banks=sorted_banks)


@app.route('/book-appointment', methods=['POST'])
@login_required
def book_appointment():
    data = request.get_json()
    bank_id = data.get('bank_id')
    date = data.get('date')
    time = data.get('time')
    notes = data.get('notes', '')
    
    if not all([bank_id, date, time]):
        return jsonify({'success': False, 'message': 'All fields required'})
    
    # Here you could save to database, but for now just return success
    # In real app, add appointment table
    return jsonify({'success': True, 'message': 'Appointment booked successfully'})


@app.route('/request-details')
@login_required
def request_details():
    request_id = request.args.get('request_id')
    if not request_id:
        return jsonify({'success': False, 'message': 'Request ID required'})

    req = get_request_by_id(request_id)
    if not req:
        return jsonify({'success': False, 'message': 'Request not found'})

    # Get accepted donors for this request
    notifications = get_notifications_by_request(request_id)
    donors = []
    for notif in notifications:
        if notif[3] == 'accepted':  # status
            donor = get_user_by_id(notif[1])  # donor_id
            if donor:
                donors.append({
                    'name': donor[1],
                    'phone': donor[4],
                    'blood': donor[7],
                    'location': donor[8],
                    'latitude': donor[9],
                    'longitude': donor[10]
                })

    request_banks = get_blood_banks_for_request(request_id)
    for b in request_banks:
        donors.append({
            'name': 'Bank: ' + b[1],
            'phone': b[3],
            'blood': b[2],
            'location': b[4],
            'latitude': b[5],
            'longitude': b[6]
        })

    return jsonify({
        'success': True,
        'request': {
            'patient_name': req[1],
            'blood': req[4],
            'hospital': req[6],
            'location': req[8],
            'latitude': req[9],
            'longitude': req[10],
            'is_emergency': bool(req[12])
        },
        'donors': donors
    })
@app.route('/results')
@login_required
def results():
    request_id = request.args.get('request_id')
    if not request_id:
        return "Request ID required", 400
    refresh = request.args.get('refresh')
    query = f"?refresh={refresh}" if refresh else ""
    return redirect(f"/results/{request_id}{query}")

@app.route('/download-certificate/<badge>')
@login_required
def download_certificate(badge):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Congratulations on your blood donation!")
    p.drawString(100, 730, f"Badge: {badge.replace('_', ' ').title()}")
    p.drawString(100, 710, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    p.drawString(100, 690, "BloodConnect - Connecting Donors with Those in Need")
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'certificate_{badge}.pdf', mimetype='application/pdf')

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)