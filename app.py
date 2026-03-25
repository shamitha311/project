from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

import bcrypt
import random
import smtplib
import time
from email.mime.text import MIMEText

otp_store = {}  
# format:
# email: {otp: "1234", expiry: time, attempts: 0}

app = Flask(__name__)
CORS(app)

# =========================
# DB CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="newpassword",
        database="plant_advanced_db"
    )

# =========================
# ADD PLANT (WITH FERTILIZER)
# =========================
@app.route('/add', methods=['POST'])
def add_plant():
    data = request.json

    print("DATA RECEIVED:", data)

    name = data['name']
    user_id = data['user_id']   # ✅ ADD THIS
    type_name = data['type']
    frequency = data['frequency']

    fert_name = data.get('fertilizer_name')
    fert_freq = data.get('fertilizer_frequency')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT category_id FROM categories WHERE category_name=%s",
            (type_name,)
        )
        category = cursor.fetchone()

        if not category:
            return jsonify({"error": "Category not found"}), 400

        category_id = category['category_id']
        

        query = """
        INSERT INTO plants 
        (name, category_id, user_id, frequency, fertilizer_name, fertilizer_frequency, added_on)
        VALUES (%s, %s, %s, %s, %s, %s, CURDATE())
        """

        cursor.execute(query, (
            name, category_id, user_id, frequency,
            fert_name, fert_freq
        ))

        db.commit()

        print("Rows inserted:", cursor.rowcount)

        if cursor.rowcount == 0:
            return jsonify({"error": "Insert failed"}), 500

        return jsonify({"message": "Plant added successfully"})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        db.close()
# =========================
# GET ALL PLANTS
# =========================
@app.route('/plants', methods=['GET'])
def get_plants():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 4))
    user_id = request.args.get('user_id')  # ✅
    offset = (page - 1) * limit

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT p.plant_id AS id,
           p.name,
           c.category_name AS type,
           p.frequency,
           p.next_water_date,
           p.fertilizer_name,
           p.next_fertilizer_date
    FROM plants p
    JOIN categories c ON p.category_id = c.category_id
    WHERE p.user_id = %s
    LIMIT %s OFFSET %s
    """

    cursor.execute(query, (user_id, limit, offset))
    result = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(result)
# =========================
# DELETE
# =========================
@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_plant(id):
    user_id = request.args.get('user_id')   # ✅ ADD

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute(
            "DELETE FROM plants WHERE plant_id=%s AND user_id=%s",
            (id, user_id)
        )
        db.commit()

        return jsonify({"message": "Deleted"})

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        db.close()

# =========================
# CATEGORIES
# =========================
@app.route('/categories', methods=['GET'])
def get_categories():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT category_name FROM categories")
    result = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(result)

# =========================
# WATER TODAY
# =========================
@app.route('/today', methods=['GET'])
def today():
    user_id = request.args.get('user_id')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # 💧 ONLY TODAY
        cursor.execute("""
            SELECT name, next_water_date 
            FROM plants
            WHERE user_id = %s AND DATE(next_water_date) = CURDATE()
        """, (user_id,))
        today_plants = cursor.fetchall()

        # 😌 NEXT UPCOMING
        cursor.execute("""
            SELECT name, next_water_date 
            FROM plants
            WHERE user_id = %s AND next_water_date > CURDATE()
            ORDER BY next_water_date
            LIMIT 1
        """, (user_id,))
        upcoming = cursor.fetchone()

        return jsonify({
            "today": today_plants,
            "upcoming": upcoming
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        db.close()
# =========================
# FERTILIZER TODAY
# =========================
@app.route('/fert_today', methods=['GET'])
def fert_today():
    user_id = request.args.get('user_id')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT name FROM plants 
        WHERE user_id=%s AND next_fertilizer_date = CURDATE()
    """, (user_id,))

    result = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(result)

# =========================
# COUNT
# =========================
@app.route('/count', methods=['GET'])
def count():
    user_id = request.args.get('user_id')

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM plants WHERE user_id=%s", (user_id,))
    total = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return jsonify({"total": total})

# =========================
# HOME
# =========================
@app.route('/')
def home():
    return "Backend running 🚀"

# =========================
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data['message'].lower()

    reply = ""

    # 🌹 FLOWERING PLANTS
    if "rose" in msg:
        reply = "🌹 Rose: Needs full sunlight, water every 2-3 days, use compost or vermicompost + neem cake."
    elif "jasmine" in msg:
        reply = "🌼 Jasmine: Loves sunlight, water regularly, use organic compost + cow dung."
    elif "hibiscus" in msg:
        reply = "🌺 Hibiscus: Needs sunlight, water daily, use potassium-rich fertilizer like banana peel."
    elif "sunflower" in msg:
        reply = "🌻 Sunflower: Full sunlight, moderate watering, compost works best."

    # 🌿 INDOOR PLANTS
    elif "money plant" in msg:
        reply = "💰 Money Plant: Low light ok, water weekly, use liquid fertilizer."
    elif "snake plant" in msg:
        reply = "🐍 Snake Plant: Very low maintenance, water once in 10 days, no heavy fertilizer needed."
    elif "areca palm" in msg:
        reply = "🌴 Areca Palm: Bright light, water 2-3 times/week, use organic compost."
    elif "peace lily" in msg:
        reply = "🕊️ Peace Lily: Low light, water when soil dries, use mild fertilizer."

    # 🌵 SUCCULENTS & CACTUS
    elif "cactus" in msg:
        reply = "🌵 Cactus: Needs sunlight, water once in 10-15 days, avoid overwatering."
    elif "aloe vera" in msg:
        reply = "🪴 Aloe Vera: Needs sunlight, water weekly, no heavy fertilizer needed."

    # 🌿 HERBS
    elif "mint" in msg:
        reply = "🌿 Mint: Needs moisture, water daily, grows well in partial sunlight."
    elif "coriander" in msg:
        reply = "🌿 Coriander: Needs sunlight, water regularly, compost helps growth."
    elif "basil" in msg:
        reply = "🌿 Basil (Tulsi): Needs sunlight, water daily, use organic compost."

    # 🍅 VEGETABLES
    elif "tomato" in msg:
        reply = "🍅 Tomato: Needs sunlight, water daily, use compost + potassium fertilizer."
    elif "chilli" in msg:
        reply = "🌶️ Chilli: Needs sunlight, moderate watering, use compost + neem cake."
    elif "spinach" in msg:
        reply = "🥬 Spinach: Needs water daily, partial sunlight, grows fast with compost."

    # 🍎 FRUITS
    elif "banana" in msg:
        reply = "🍌 Banana: Needs lots of water, sunlight, use organic manure."
    elif "mango" in msg:
        reply = "🥭 Mango: Needs sunlight, water weekly, use compost + cow dung."
    elif "lemon" in msg:
        reply = "🍋 Lemon: Needs sunlight, water regularly, use citrus fertilizer."

    # 🌳 TREES / OUTDOOR
    elif "neem" in msg:
        reply = "🌳 Neem: Very low maintenance, water occasionally, no fertilizer needed."
    elif "tulsi" in msg:
        reply = "🌿 Tulsi: Needs sunlight, water daily, use organic compost."

    # 🧪 GENERAL QUESTIONS
    elif "fertilizer" in msg:
        reply = "🌿 Use organic fertilizers like compost, neem cake, cow dung, banana peel."
    elif "watering" in msg:
        reply = "💧 Water early morning or evening, avoid overwatering."
    elif "sunlight" in msg:
        reply = "☀️ Most plants need 4-6 hours sunlight daily."

    # 🤖 DEFAULT
    else:
        reply = "🌱 Ask about plants like rose, aloe vera, tomato, neem, tulsi etc. I’ll guide you!"

    return jsonify({"reply": reply})



    
@app.route('/register', methods=['POST'])
def register():
    data = request.json

    name = data['name']
    email = data['email']
    phone = data['phone']
    password = data['password']

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 🔥 CHECK USER EXISTS
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email already registered ❌"})

    # 🔥 ONLY INSERT IF NOT EXISTS
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor.execute(
        "INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)",
        (name, email, phone, hashed)
    )

    db.commit()

    return jsonify({"message": "Registered successfully ✅"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"new_user": True})

    if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({
            "message": "Login success",
            "user_id": user['user_id']
        })
    else:
        return jsonify({"error": "Wrong password"})


@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data['email']

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    if not cursor.fetchone():
        return jsonify({"error": "Email not registered ❌"})

    otp = str(random.randint(1000, 9999))

    otp_store[email] = {
        "otp": otp,
        "expiry": time.time() + 30,  # 30 sec
        "attempts": 0
    }

    # 📧 SEND EMAIL
    sender = "shamitha311@gmail.com"
    app_password = "pmfpzzakhiciehzh"

    msg = MIMEText(f"Your OTP is: {otp}")
    msg['Subject'] = "Password Reset OTP"
    msg['From'] = sender
    msg['To'] = email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, app_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        return jsonify({"error": str(e)})

    return jsonify({"message": "OTP sent to email 📧"})


@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json

    email = data['email']
    otp = data['otp']
    new_pass = data['password']

    if email not in otp_store:
        return jsonify({"error": "No OTP requested ❌"})

    record = otp_store[email]

    # ⏳ check expiry
    if time.time() > record["expiry"]:
        otp_store.pop(email)
        return jsonify({"error": "OTP expired ⏳"})

    # 🔒 check attempts
    if record["attempts"] >= 3:
        otp_store.pop(email)
        return jsonify({"error": "Too many attempts 🚫"})

    # ❌ wrong OTP
    if record["otp"] != otp:
        record["attempts"] += 1
        return jsonify({"error": "Invalid OTP ❌"})

    # ✅ correct OTP → update password
    hashed = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt())

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (hashed, email)
    )
    db.commit()

    otp_store.pop(email)

    return jsonify({"message": "Password reset successful ✅"})
# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(debug=True)
