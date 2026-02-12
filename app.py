from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# ---------- Database Connection ----------
def db():
    return sqlite3.connect('blood.db')


# ---------- PAGES ----------

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/donor')
def donor_page():
    return render_template("donor.html")


@app.route('/request')
def request_page():
    return render_template("request.html")


# ---------- API FUNCTIONS ----------

# ➤ ADD DONOR
# ➤ ADD DONOR
@app.route('/addDonor', methods=['POST'])
def add_donor():

    data = request.json

    # Normalize values
    name = data['name'].strip()
    blood = data['blood'].strip().upper()       # Always uppercase
    phone = data['phone'].strip()
    location = data['location'].strip().lower() # Always lowercase
    last_donated = data['last_donated'].strip()

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO donors (name, blood, phone, location, last_donated)
        VALUES (?, ?, ?, ?, ?)
    """, (name, blood, phone, location, last_donated))

    conn.commit()
    conn.close()

    return jsonify({"msg": "Donor Registered Successfully"})

# ➤ REQUEST BLOOD WITH COMPATIBILITY
@app.route('/requestBlood', methods=['POST'])
def request_blood():
    data = request.json

    conn = db()
    cur = conn.cursor()

    # Insert request record
    cur.execute(
        "INSERT INTO requests VALUES(NULL,?,?,?,?,?)",
        (
            data['patient'],
            data['blood'],
            data['hospital'],
            data['location'],
            "Pending"
        )
    )

    # ---- Blood Compatibility Rules ----
    compat = {
        "O+": ["O+","O-"],
        "A+": ["A+","A-","O+","O-"],
        "B+": ["B+","B-","O+","O-"],
        "AB+": ["A+","A-","B+","B-","O+","O-","AB+","AB-"],
        "O-": ["O-"],
        "A-": ["A-","O-"],
        "B-": ["B-","O-"],
        "AB-": ["AB-","A-","B-","O-"]
    }

    groups = compat.get(data['blood'], [data['blood']])

    query = "SELECT * FROM donors WHERE blood IN ({}) AND location=?".format(
        ",".join("?" * len(groups))
    )

    cur.execute(query, (*groups, data['location']))
    donors = cur.fetchall()

    conn.commit()
    conn.close()

    if donors:
        msg = "Matching Donors Found"
    else:
        msg = "No Donors Available Nearby"

    return jsonify({
        "message": msg,
        "matched_donors": donors
    })


# ➤ VIEW ALL DONORS
@app.route('/donors')
def donors():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM donors")
    data = cur.fetchall()

    conn.close()

    return jsonify(data)


# ➤ VIEW ALL REQUESTS
@app.route('/allRequests')
def all_requests():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM requests")
    data = cur.fetchall()

    conn.close()

    return jsonify(data)

@app.route('/results', methods=['POST'])
def results():

    blood = request.form['blood'].strip().upper()
    location = request.form['location'].strip().lower()

    conn = db()
    cur = conn.cursor()

    compat = {
        "O+": ["O+","O-"],
        "A+": ["A+","A-","O+","O-"],
        "B+": ["B+","B-","O+","O-"],
        "AB+": ["A+","A-","B+","B-","O+","O-","AB+","AB-"],
        "O-": ["O-"],
        "A-": ["A-","O-"],
        "B-": ["B-","O-"],
        "AB-": ["AB-","A-","B-","O-"]
    }

    groups = compat.get(blood, [blood])

    query = f"""
        SELECT * FROM donors
        WHERE UPPER(blood) IN ({','.join('?'*len(groups))})
        AND LOWER(location) = ?
    """

    cur.execute(query, (*groups, location))
    donors = cur.fetchall()

    conn.close()

    return render_template("results.html", donors=donors, location=location)


# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
