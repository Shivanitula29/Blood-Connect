from sms import send_sms
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
@app.route('/addDonor', methods=['POST'])
def add_donor():
    data = request.json

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO donors VALUES(NULL,?,?,?,?,?)",
        (
            data['name'],
            data['blood'],
            data['phone'],
            data['location'],
            data['last_donated']
        )
    )

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
    # ----- SEND SMS TO MATCHED DONORS -----
    for d in donors:
       phone = d[3]
    msg = f"Emergency Blood Request: {data['blood']} needed at {data['hospital']}. Please help!"
    send_sms(phone, msg)

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


# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
