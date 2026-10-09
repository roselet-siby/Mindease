
from report_generator import generate_user_report
from flask import send_file
import os
from flask import Flask, render_template, request, session, redirect, flash, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
import bcrypt
from datetime import datetime, date, timedelta
from chatbot_engine import  emotion_classifier, EMOTION_MAP

from chatbot_engine import get_response, reset_user_memory
from MySQLdb import IntegrityError
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ==================================
# MySQL Configuration
# ==================================
app.config['MYSQL_HOST']     = 'localhost'
app.config['MYSQL_USER']     = 'root'
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB']       = 'mental_health_chatbot'

mysql = MySQL(app)

# ==================================
# Home
# ==================================


# ==================================
# Register Page
# ==================================
# ==================================
# Helper: mood check-in streak
# ==================================
def calculate_mood_streak(cursor, user_id):
    cursor.execute(
        "SELECT DISTINCT DATE(created_at) AS d FROM mood_logs WHERE user_id=%s ORDER BY d DESC",
        (user_id,)
    )
    dates = [row[0] for row in cursor.fetchall()]
    if not dates:
        return 0

    today = date.today()
    if dates[0] == today:
        expected = today
    elif dates[0] == today - timedelta(days=1):
        expected = today - timedelta(days=1)
    else:
        return 0  # streak broken — most recent check-in wasn't today or yesterday

    streak = 0
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak

@app.route('/register')
def register_page():
    return render_template('register.html')

# ==================================
# Register User
# ==================================
@app.route('/register', methods=['POST'])
def register():
    name     = request.form['name']
    email    = request.form['email']
    password = request.form['password']

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        flash("Email already registered.")
        return redirect('/register')

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
        (name, email, hashed_password, "user")
    )
    mysql.connection.commit()
    cursor.close()

    flash("Registration successful. Please login.")
    return redirect('/login')

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('landing.html')
# ==================================
# Login Page
# ==================================
@app.route('/login')
def login_page():
    return render_template('login.html')

# ==================================
# Login User
# ==================================
@app.route('/login', methods=['POST'])
def login():
    email    = request.form['email']
    password = request.form['password']

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        stored_password = user[3]
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            session['user_id']   = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4]
            session.pop('chat_started_at', None)
            return redirect('/dashboard')

    # Not a regular user (or wrong password) — check if it's a doctor
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM psychiatrists WHERE email=%s", (email,))
    doctor = cursor.fetchone()
    cursor.close()

    # doctor tuple: (doctor_id, name, specialization, location, contact_number, clinic_name, email, password)
    if doctor and doctor[7]:
        if bcrypt.checkpw(password.encode('utf-8'), doctor[7].encode('utf-8')):
            session['doctor_id']   = doctor[0]
            session['doctor_name'] = doctor[1]
            return redirect('/doctor/dashboard')

    flash("Invalid email or password.")
    return redirect('/login')

# ==================================
# Dashboard
# ==================================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor()

    # Upcoming appointment count
    cursor.execute(
        """
        SELECT COUNT(*) FROM appointments
        WHERE user_id=%s AND status IN ('pending', 'confirmed')
        """,
        (user_id,)
    )
    upcoming_count = cursor.fetchone()[0]

    # Most recent mood check-in
    cursor.execute(
        """
        SELECT mood, intensity, created_at
        FROM mood_logs
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    )
    last_mood = cursor.fetchone()
    cursor.close()

    return render_template(
        'dashboard.html',
        username=session.get('user_name'),
        role=session.get('user_role'),
        upcoming_count=upcoming_count,
        last_mood=last_mood
    )

# ==================================
# Logout
# ==================================
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        reset_user_memory(user_id)
    session.clear()
    return redirect('/login')
def get_checkin_streak(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT DATE(created_at) AS d
        FROM mood_logs
        WHERE user_id=%s
        ORDER BY d DESC
        LIMIT 60
        """,
        (user_id,)
    )
    days = [row[0] for row in cursor.fetchall()]
    cursor.close()

    if not days:
        return 0

    streak = 0
    expected = date.today()

    # allow today OR yesterday as the most recent check-in
    if days[0] not in (expected, expected - timedelta(days=1)):
        return 0

    expected = days[0]
    for d in days:
        if d == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        else:
            break

    return streak
# ==================================
# Game Page
# ==================================
# ==================================
# Game landing page
# ==================================
@app.route('/game')
def game():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    streak = get_checkin_streak(user_id)

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT score, correct, attempts FROM game_scores WHERE user_id=%s",
        (user_id,)
    )
    my_stats = cursor.fetchone()

    cursor.execute(
        """
        SELECT u.name, gs.score, gs.correct, gs.attempts
        FROM game_scores gs
        JOIN users u ON u.user_id = gs.user_id
        ORDER BY gs.score DESC
        LIMIT 10
        """
    )
    leaderboard = cursor.fetchall()
    cursor.close()

    return render_template(
        'game.html',
        streak=streak,
        my_stats=my_stats,
        leaderboard=leaderboard
    )
# ==================================
# Submit a guess
# ==================================
@app.route('/game/guess', methods=['POST'])
def game_guess():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401

    user_id = session['user_id']
    data = request.get_json()
    sentence_id = data.get('sentence_id')
    guess = data.get('guess')

    correct_emotion = session.pop('game_answer_%s' % sentence_id, None)
    if correct_emotion is None:
        return jsonify({'error': 'unknown or expired sentence'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT sentence FROM game_sentences WHERE sentence_id=%s",
        (sentence_id,)
    )
    row = cursor.fetchone()
    sentence_text = row[0] if row else ''

    # run YOUR trained model as the "AI opponent"
    raw = emotion_classifier(sentence_text)[0]
    ai_emotion = EMOTION_MAP.get(raw['label'], raw['label'].lower())
    ai_correct = (ai_emotion == correct_emotion)

    user_correct = (guess == correct_emotion)
    points_gained = 10 if user_correct else 0

    cursor.execute(
        """
        INSERT INTO game_scores (user_id, score, correct, attempts)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
            score = score + %s,
            correct = correct + %s,
            attempts = attempts + 1
        """,
        (user_id, points_gained, 1 if user_correct else 0,
         points_gained, 1 if user_correct else 0)
    )
    mysql.connection.commit()

    cursor.execute("SELECT score FROM game_scores WHERE user_id=%s", (user_id,))
    total_score = cursor.fetchone()[0]
    cursor.close()

    return jsonify({
        'correct': user_correct,
        'points_gained': points_gained,
        'correct_emotion': correct_emotion,
        'ai_emotion': ai_emotion,
        'ai_correct': ai_correct,
        'total_score': total_score
    })

# ==================================
# Get a random sentence to guess
# ==================================
@app.route('/game/sentence')
def game_sentence():
    if 'user_id' not in session:
        return jsonify({'error': 'not logged in'}), 401

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT sentence_id, sentence, emotion FROM game_sentences")
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return jsonify({'error': 'no sentences available'}), 500

    import random
    sentence_id, sentence, correct_emotion = random.choice(rows)

    # store the answer server-side so the client can't see/tamper with it
    session['game_answer_%s' % sentence_id] = correct_emotion

    return jsonify({'sentence_id': sentence_id, 'sentence': sentence})
# ==================================
# Chat Page (GET only — renders UI)
# ==================================
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')

    user_id         = session['user_id']
    chat_started_at = session.get('chat_started_at')

    cursor = mysql.connection.cursor()

    if chat_started_at:
        # New Chat was clicked — only show messages from this session onward
        cursor.execute(
            """
            SELECT message, bot_response, emotion, sentiment, stress_level
            FROM chat_history
            WHERE user_id=%s AND timestamp >= %s
            ORDER BY chat_id ASC
            """,
            (user_id, chat_started_at)
        )
    else:
        # First login — show all history so context is visible
        cursor.execute(
            """
            SELECT message, bot_response, emotion, sentiment, stress_level
            FROM chat_history
            WHERE user_id=%s
            ORDER BY chat_id ASC
            """,
            (user_id,)
        )

    chats = cursor.fetchall()
    cursor.close()

    return render_template('chat.html', chat_history=chats)

# ============================================================
# REPORT ROUTES - Add these to your app.py
# Place near your other routes, before "if __name__"
# ============================================================

# At the TOP of app.py, add this import:
# from report_generator import generate_user_report
# from flask import send_file
# import os

# ============================================================
# MOOD CHECK-IN ROUTES - Add these to app.py
# Place near your other routes (e.g. after the /report routes),
# before "if __name__ == '__main__':"
# ============================================================

# ==================================
# Mood Check-in Page (GET) + history
# ==================================
@app.route('/mood', methods=['GET', 'POST'])
def mood():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        SELECT log_id, mood, intensity, note, created_at
        FROM mood_logs
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 30
        """,
        (user_id,)
    )
    logs = cursor.fetchall()
    cursor.close()

    return render_template('mood.html', logs=logs)


# ==================================
# Save a Mood Check-in (POST)
# ==================================
@app.route('/mood/add', methods=['POST'])
def add_mood():
    if 'user_id' not in session:
        return redirect('/login')

    user_id   = session['user_id']
    mood      = request.form['mood']
    intensity = request.form.get('intensity') or None
    note      = request.form.get('note', '').strip() or None

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO mood_logs (user_id, mood, intensity, note) VALUES (%s,%s,%s,%s)",
        (user_id, mood, intensity, note)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Check-in saved.")
    return redirect('/mood')
# ==================================
# Report Selection Page
# ==================================

@app.route('/report')
def report_page():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('report.html')

# ============================================================
# DOCTOR DASHBOARD ROUTES - Add these to app.py
# Place near your other routes, before "if __name__ == '__main__':"
# Requires: doctor_auth_schema.sql already run, and bcrypt already
# imported at the top of app.py (you already use it for user login).
# ============================================================

# ==================================
# Doctor Login Page (GET)
# ==================================
@app.route('/doctor/login')
def doctor_login_page():
    return render_template('doctor_login.html')


# ==================================
# Doctor Login (POST)
# ==================================
@app.route('/doctor/login', methods=['POST'])
def doctor_login():
    email    = request.form['email']
    password = request.form['password']

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM psychiatrists WHERE email=%s", (email,))
    doctor = cursor.fetchone()
    cursor.close()

    # doctor tuple: (doctor_id, name, specialization, location, contact_number, clinic_name, email, password)
    if doctor and doctor[7]:
        if bcrypt.checkpw(password.encode('utf-8'), doctor[7].encode('utf-8')):
            session['doctor_id']   = doctor[0]
            session['doctor_name'] = doctor[1]
            return redirect('/doctor/dashboard')

    flash("Invalid email or password.")
    return redirect('/doctor/login')


# ==================================
# Doctor Logout
# ==================================
@app.route('/doctor/logout')
def doctor_logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    return redirect('/doctor/login')


# ==================================
# Doctor Dashboard - view appointments
# ==================================
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect('/doctor/login')

    doctor_id = session['doctor_id']

    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        SELECT a.appointment_id, u.name, u.email, a.appointment_date,
               a.appointment_time, a.status, a.notes
        FROM appointments a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
        """,
        (doctor_id,)
    )
    appointments = cursor.fetchall()
    cursor.close()

    pending   = [a for a in appointments if a[5] == 'pending']
    upcoming  = [a for a in appointments if a[5] == 'confirmed']
    history   = [a for a in appointments if a[5] in ('cancelled', 'completed')]

    return render_template(
        'doctor_dashboard.html',
        doctor_name=session.get('doctor_name'),
        pending=pending,
        upcoming=upcoming,
        history=history
    )


# ==================================
# Doctor updates appointment status
# ==================================
@app.route('/doctor/appointment/<int:appointment_id>/<action>')
def doctor_update_appointment(appointment_id, action):
    if 'doctor_id' not in session:
        return redirect('/doctor/login')

    status_map = {
        'accept':   'confirmed',
        'reject':   'cancelled',
        'complete': 'completed'
    }
    new_status = status_map.get(action)
    if not new_status:
        flash("Invalid action.")
        return redirect('/doctor/dashboard')

    doctor_id = session['doctor_id']

    cursor = mysql.connection.cursor()
    # Confirm this appointment actually belongs to the logged-in doctor
    cursor.execute(
        "SELECT doctor_id FROM appointments WHERE appointment_id=%s",
        (appointment_id,)
    )
    row = cursor.fetchone()

    if not row or row[0] != doctor_id:
        cursor.close()
        flash("Appointment not found.")
        return redirect('/doctor/dashboard')

    cursor.execute(
        "UPDATE appointments SET status=%s WHERE appointment_id=%s",
        (new_status, appointment_id)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Appointment updated.")
    return redirect('/doctor/dashboard')
# ==================================
# Generate and Download Report
# ==================================
@app.route('/download_report')
def download_report():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Get selected period from query string (?period=7 / 30 / 90 / all)
    period = request.args.get('period', 'all')

    period_labels = {
        '7':   'Last 7 Days',
        '30':  'Last 30 Days',
        '90':  'Last 3 Months',
        'all': 'All Time'
    }
    period_label = period_labels.get(period, 'All Time')

    # Build date filter
    if period == '7':
        date_filter = "AND timestamp >= NOW() - INTERVAL 7 DAY"
    elif period == '30':
        date_filter = "AND timestamp >= NOW() - INTERVAL 30 DAY"
    elif period == '90':
        date_filter = "AND timestamp >= NOW() - INTERVAL 90 DAY"
    else:
        date_filter = ""

    # Get user info
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT name, email FROM users WHERE user_id=%s",
        (user_id,)
    )
    user_row = cursor.fetchone()
    cursor.close()

    if not user_row:
        flash("User not found.")
        return redirect('/dashboard')

    user_name, user_email = user_row

    # Total sessions
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM chat_history
        WHERE user_id=%s {date_filter}
        """,
        (user_id,)
    )
    total_sessions = cursor.fetchone()[0]
    cursor.close()

    if total_sessions == 0:
        flash("No conversation data found for this period.")
        return redirect('/report')

    # Emotion statistics
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"""
        SELECT emotion, COUNT(*) as count
        FROM chat_history
        WHERE user_id=%s {date_filter}
        GROUP BY emotion
        ORDER BY count DESC
        """,
        (user_id,)
    )
    emotion_stats = cursor.fetchall()
    cursor.close()

    top_emotion = emotion_stats[0][0] if emotion_stats else "N/A"

    # Sentiment statistics
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"""
        SELECT sentiment, COUNT(*) as count
        FROM chat_history
        WHERE user_id=%s {date_filter}
        GROUP BY sentiment
        """,
        (user_id,)
    )
    sentiment_rows  = cursor.fetchall()
    sentiment_stats = {row[0]: row[1] for row in sentiment_rows}
    cursor.close()

    # Stress statistics
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"""
        SELECT stress_level, COUNT(*) as count
        FROM chat_history
        WHERE user_id=%s {date_filter}
        GROUP BY stress_level
        """,
        (user_id,)
    )
    stress_rows  = cursor.fetchall()
    stress_stats = {row[0]: row[1] for row in stress_rows}
    cursor.close()

    # Crisis count
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM chat_history
        WHERE user_id=%s AND emotion='crisis' {date_filter}
        """,
        (user_id,)
    )
    crisis_count = cursor.fetchone()[0]
    cursor.close()

    # Generate PDF
    output_dir = "./generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"MindEase_Report_{user_id}_{period}.pdf"
    output_path = os.path.join(output_dir, filename)

    generate_user_report(
        user_name=user_name,
        user_email=user_email,
        period_label=period_label,
        total_sessions=total_sessions,
        emotion_stats=emotion_stats,
        sentiment_stats=sentiment_stats,
        stress_stats=stress_stats,
        crisis_count=crisis_count,
        top_emotion=top_emotion,
        output_path=output_path
    )

    return send_file(
        output_path,
        as_attachment=True,
        download_name=f"MindEase_Wellness_Report.pdf"
    )
# ==================================
# Chat API (JSON — called by JS)
# ==================================
@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return jsonify({'error': 'Empty message'}), 400

    user_message = data['message'].strip()
    user_id      = session['user_id']

    try:
        result = get_response(user_message, user_id)
    except Exception as e:
        print(f"[Chat Error] {e}")
        result = {
            "emotion":      "neutral",
            "sentiment":    "Neutral",
            "stress_level": "Low",
            "response":     "I'm here to listen. Could you tell me more?"
        }

    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        INSERT INTO chat_history
        (user_id, message, bot_response, emotion, sentiment, stress_level)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            user_id,
            user_message,
            result['response'],
            result['emotion'],
            result['sentiment'],
            result['stress_level']
        )
    )
    mysql.connection.commit()
    cursor.close()

    return jsonify(result)

# ==================================
# New Chat — resets Groq memory and
# sets a session timestamp so only
# new messages appear in the chat UI.
# Full history still visible in /history
# ==================================
@app.route('/new_chat')
def new_chat():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Reset Groq conversation memory for this user
    reset_user_memory(user_id)

    # Save timestamp so /chat only loads messages from this point forward
    session['chat_started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return redirect('/chat')

# ==================================
# History (shows ALL past messages)
# ==================================
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        SELECT message, bot_response, emotion, sentiment, stress_level, timestamp
        FROM chat_history
        WHERE user_id=%s
        ORDER BY chat_id DESC
        """,
        (session['user_id'],)
    )
    history_data = cursor.fetchall()
    cursor.close()

    return render_template('history.html', history=history_data)
# ============================================================
# APPOINTMENT ROUTES
# Add these to your app.py before "if __name__ == '__main__'"
# ============================================================


# ==================================
# Book Appointment Page
# ==================================
@app.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Get doctor info
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM psychiatrists WHERE doctor_id=%s", (doctor_id,))
    doctor = cursor.fetchone()
    cursor.close()

    if not doctor:
        flash("Doctor not found.", "error")
        return redirect('/psychiatrists')

  
    if request.method == 'POST':
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        notes            = request.form.get('notes', '').strip()
 
        if not appointment_date or not appointment_time:
            flash("Please select a date and time.", "error")
            return redirect(f'/book_appointment/{doctor_id}')
 
        # Fast, friendly check (kept as-is) — catches the common case
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM appointments
            WHERE doctor_id=%s
            AND appointment_date=%s
            AND appointment_time=%s
            AND status != 'cancelled'
        """, (doctor_id, appointment_date, appointment_time))
        already_booked = cursor.fetchone()[0]
        cursor.close()
 
        if already_booked:
            flash("This slot is already booked. Please choose another time.", "error")
            return redirect(f'/book_appointment/{doctor_id}')
 
        # Real safety net — the DB itself will reject a duplicate slot
        # even if two requests race past the check above at the same time.
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO appointments
                (user_id, doctor_id, appointment_date, appointment_time, notes, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (user_id, doctor_id, appointment_date, appointment_time, notes))
            mysql.connection.commit()
        except IntegrityError:
            mysql.connection.rollback()
            cursor.close()
            flash("Someone just booked this exact slot a moment ago. Please choose another time.", "error")
            return redirect(f'/book_appointment/{doctor_id}')
        cursor.close()
 
        flash("Appointment booked successfully! Status: Pending confirmation.", "success")
        return redirect('/my_appointments')

    # GET — load booked slots for this doctor
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT appointment_date, appointment_time
        FROM appointments
        WHERE doctor_id=%s AND status != 'cancelled'
    """, (doctor_id,))
    booked_rows = cursor.fetchall()
    cursor.close()

    # Format as "YYYY-MM-DD_HH:MM AM/PM" for JS
    booked_slots = [
        f"{str(row[0])}_{row[1]}"
        for row in booked_rows
    ]

    return render_template(
        'book_appointment.html',
        doctor=doctor,
        booked_slots=booked_slots
    )


# ==================================
# My Appointments
# ==================================
@app.route('/my_appointments')
def my_appointments():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT
            a.appointment_id,
            p.name,
            p.specialization,
            p.location,
            p.contact_number,
            p.clinic_name,
            a.appointment_date,
            a.appointment_time,
            a.notes,
            a.status,
            a.created_at
        FROM appointments a
        JOIN psychiatrists p ON a.doctor_id = p.doctor_id
        WHERE a.user_id=%s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (session['user_id'],))
    appointments = cursor.fetchall()
    cursor.close()

    return render_template(
        'my_appointments.html',
        appointments=appointments
    )


# ==================================
# Cancel Appointment
# ==================================
@app.route('/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE appointments
        SET status = 'cancelled'
        WHERE appointment_id=%s AND user_id=%s
    """, (appointment_id, session['user_id']))
    mysql.connection.commit()
    cursor.close()

    flash("Appointment cancelled successfully.", "success")
    return redirect('/my_appointments')


# ==================================
# Admin — View All Appointments
# ==================================
@app.route('/admin/appointments')
def admin_appointments():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        return redirect('/dashboard')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT
            a.appointment_id,
            u.name as patient_name,
            p.name as doctor_name,
            p.specialization,
            a.appointment_date,
            a.appointment_time,
            a.status,
            a.notes,
            a.created_at
        FROM appointments a
        JOIN users u        ON a.user_id   = u.user_id
        JOIN psychiatrists p ON a.doctor_id = p.doctor_id
        ORDER BY a.appointment_date DESC
    """)
    appointments = cursor.fetchall()
    cursor.close()

    return render_template(
        'admin_appointments.html',
        appointments=appointments
    )


# ==================================
# Admin — Update Appointment Status
# ==================================
@app.route('/admin/update_appointment/<int:appointment_id>/<string:status>')
def update_appointment_status(appointment_id, status):
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        return redirect('/dashboard')

    if status not in ['pending', 'confirmed', 'cancelled']:
        flash("Invalid status.", "error")
        return redirect('/admin/appointments')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE appointments
        SET status=%s
        WHERE appointment_id=%s
    """, (status, appointment_id))
    mysql.connection.commit()
    cursor.close()

    flash(f"Appointment status updated to {status}.", "success")
    return redirect('/admin/appointments')
# ==================================
# Psychiatrist Page
# ==================================
@app.route('/psychiatrists')
def psychiatrists():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM psychiatrists")
    doctors = cursor.fetchall()
    cursor.close()

    return render_template('psychiatrists.html', doctors=doctors)

# ==================================
# Admin Panel
# ==================================
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        flash("Access denied. Admins only.")
        return redirect('/dashboard')

    # Total appointments
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status != 'cancelled'")
    total_appointments = cursor.fetchone()[0]
    cursor.close()

# Appointment status counts
    cursor = mysql.connection.cursor()
    cursor.execute("""
    SELECT status, COUNT(*) FROM appointments GROUP BY status
    """)
    appt_status_rows = dict(cursor.fetchall())
    cursor.close()

    pending_appointments   = appt_status_rows.get('pending', 0)
    confirmed_appointments = appt_status_rows.get('confirmed', 0)
    cancelled_appointments = appt_status_rows.get('cancelled', 0)
    # Total users
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
    total_users = cursor.fetchone()[0]
    cursor.close()

    # Total chats
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM chat_history")
    total_chats = cursor.fetchone()[0]
    cursor.close()

    # Emotion statistics
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT emotion, COUNT(*) as count
        FROM chat_history
        GROUP BY emotion
        ORDER BY count DESC
    """)
    emotion_stats = cursor.fetchall()
    cursor.close()

    top_emotion = emotion_stats[0][0] if emotion_stats else "N/A"

    # Stress statistics
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT stress_level, COUNT(*) as count
        FROM chat_history
        GROUP BY stress_level
    """)
    stress_rows  = cursor.fetchall()
    stress_stats = {row[0]: row[1] for row in stress_rows}
    cursor.close()

    high_stress = stress_stats.get('High', 0)

    # Sentiment statistics ← NEW
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT sentiment, COUNT(*) as count
        FROM chat_history
        GROUP BY sentiment
    """)
    sentiment_rows  = cursor.fetchall()
    sentiment_stats = {row[0]: row[1] for row in sentiment_rows}
    cursor.close()

    # Crisis count ← NEW
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM chat_history
        WHERE emotion = 'crisis'
    """)
    crisis_count = cursor.fetchone()[0]
    cursor.close()

    # Positive sessions count ← NEW
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM chat_history
        WHERE sentiment = 'Positive'
    """)
    positive_count = cursor.fetchone()[0]
    cursor.close()

    # All users with chat count ← UPDATED
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT u.user_id, u.name, u.email, u.role,
               u.created_at,
               COUNT(c.chat_id) as chat_count
        FROM users u
        LEFT JOIN chat_history c ON u.user_id = c.user_id
        GROUP BY u.user_id
        ORDER BY u.created_at DESC
    """)
    users = cursor.fetchall()
    cursor.close()

    # Psychiatrists
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM psychiatrists ORDER BY doctor_id DESC")
    doctors = cursor.fetchall()
    cursor.close()

    return render_template (
        'admin.html',
        admin_name=session.get('user_name'),
        total_users=total_users,
        total_chats=total_chats,
        top_emotion=top_emotion,
        high_stress=high_stress,
        crisis_count=crisis_count,
        positive_count=positive_count,
        emotion_stats=emotion_stats,
        stress_stats=stress_stats,
        sentiment_stats=sentiment_stats,
        users=users,
        doctors=doctors,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        confirmed_appointments=confirmed_appointments,
        cancelled_appointments=cancelled_appointments
    )


# ==================================
# Admin - Delete User
# ==================================
@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        return redirect('/dashboard')

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id=%s", (user_id,))
    mysql.connection.commit()
    cursor.close()

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM users WHERE user_id=%s AND role != 'admin'", (user_id,))
    mysql.connection.commit()
    cursor.close()

    flash("User deleted successfully.")
    return redirect('/admin')


# ==================================
# Admin - Add Psychiatrist
# ==================================
@app.route('/admin/add_psychiatrist', methods=['POST'])
def add_psychiatrist():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        return redirect('/dashboard')

    name           = request.form['name']
    specialization = request.form['specialization']
    location       = request.form['location']
    contact_number = request.form['contact_number']
    clinic_name    = request.form['clinic_name']
    email          = request.form['email']
    password       = request.form['password']

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    cursor = mysql.connection.cursor()
    cursor.execute(
        """
        INSERT INTO psychiatrists
        (name, specialization, location, contact_number, clinic_name, email, password)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (name, specialization, location, contact_number, clinic_name, email, hashed_password)
    )
    mysql.connection.commit()
    cursor.close()

    flash("Doctor added successfully!")
    return redirect('/admin')
# ==================================
# Admin - Delete Psychiatrist
# ==================================
@app.route('/admin/delete_psychiatrist/<int:doctor_id>')
def delete_psychiatrist(doctor_id):
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()

    if not user or user[0] != 'admin':
        return redirect('/dashboard')

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM psychiatrists WHERE doctor_id=%s", (doctor_id,))
    mysql.connection.commit()
    cursor.close()

    flash("Doctor removed successfully!")
    return redirect('/admin')

import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

# ==================================
# Run App
# ==================================
if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True)