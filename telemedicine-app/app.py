from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import os
import re
import random
import logging
import uuid
import requests
import threading
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('telemedicine-app')

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URI", "sqlite:///database.db?check_same_thread=False"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}
)

# Custom Jinja2 filter for datetime formatting
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime(format)
    elif isinstance(value, datetime):
        return value.strftime(format)
    return value

app.jinja_env.filters['datetimeformat'] = datetimeformat

csrf = CSRFProtect(app)
db = SQLAlchemy(app)

# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(50))
    otp = db.Column(db.String(200))
    status = db.Column(db.String(10), default="Offline")

    def set_otp(self):
        otp = str(random.randint(100000, 999999))
        self.otp = generate_password_hash(otp)
        db.session.commit()
        return otp

    def verify_otp(self, entered_otp):
        return check_password_hash(self.otp, entered_otp.strip()) if self.otp else False

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    reminder_time = db.Column(db.DateTime(timezone=True), nullable=False)
    notes = db.Column(db.Text)
    frequency = db.Column(db.String(20), default='once')
    alerted = db.Column(db.Boolean, default=False)
    user = db.relationship('User', foreign_keys=[user_id])

class DoctorAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), default='available')
    doctor = db.relationship('User', foreign_keys=[doctor_id])

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    availability_id = db.Column(db.Integer, db.ForeignKey('doctor_availability.id'))
    appointment_time = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    room_id = db.Column(db.String(36), unique=True)
    patient = db.relationship("User", foreign_keys=[patient_id])
    doctor = db.relationship("User", foreign_keys=[doctor_id])
    availability = db.relationship('DoctorAvailability')

# ----------------- Helper Functions -----------------
def generate_room_id():
    return uuid.uuid4().hex[:8]  # 8-character ID

# ----------------- Routes -----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/<role>-login", methods=["GET", "POST"])
def role_login(role):
    try:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()

            if not user:
                flash("No account found with this email", "danger")
                return redirect(f"/{role}-login")
                
            if user.role.lower() != role.lower():
                flash(f"Account is not registered as a {role}", "danger")
                return redirect(f"/{role}-login")

            otp = user.set_otp()
            session['otp'] = otp
            return redirect(url_for("verify", email=email))
            
        return render_template("login.html", role=role.capitalize())
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        flash("Authentication system error", "danger")
        return redirect("/")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    try:
        if request.method == "POST":
            email = request.form.get("email")
            entered_otp = request.form.get("otp", "").strip()

            user = User.query.filter_by(email=email).first()
            if not user:
                flash("Account not found", "danger")
                return redirect(url_for("home"))

            if user.verify_otp(entered_otp):
                session.update({
                    "user_id": user.id,
                    "email": user.email,
                    "role": user.role.lower(),
                    "name": user.name
                })
                user.otp = None
                if user.role == "doctor":
                    user.status = "Online"
                db.session.commit()
                return redirect(url_for(f"{user.role}_dashboard"))
            
            flash("Invalid OTP", "danger")
            return redirect(url_for("verify", email=email))
        
        email = request.args.get("email")
        otp = session.pop('otp', None)
        return render_template("verify.html", email=email, otp=otp)
    
    except Exception as e:
        logger.error(f"Verification error: {str(e)}", exc_info=True)
        flash("System error during verification", "danger")
        return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            role = request.form.get("role", "").lower()
            password = request.form.get("password", "")
            confirm = request.form.get("password_confirm", "")
            
            # Fixed specialty handling
            specialty = request.form.get("specialty", "").strip() if role == "doctor" else None

            errors = []
            
            if len(name) < 3:
                errors.append("Name must be at least 3 characters")
            if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email):
                errors.append("Invalid email format")
            clean_phone = re.sub(r"[^0-9+]", "", phone)
            if not re.match(r"^\+?[1-9]\d{7,14}$", clean_phone):
                errors.append("Invalid phone number format")
            if len(password) < 8 or not re.search(r"\d", password) or not re.search(r"[A-Za-z]", password):
                errors.append("Password must be 8+ characters with letters and numbers")
            if password != confirm:
                errors.append("Passwords do not match")
            if role not in ["patient", "doctor"]:
                errors.append("Invalid role selection")
            if role == "doctor" and not specialty:
                errors.append("Specialty is required for doctors")
            if User.query.filter((User.email == email) | (User.phone == clean_phone)).first():
                errors.append("Email or phone already registered")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("register.html",
                                    name=name,
                                    email=email,
                                    phone=phone,
                                    role=role.capitalize())

            new_user = User(
                name=name,
                email=email,
                phone=clean_phone,
                role=role,
                password=generate_password_hash(password),
                specialty=specialty
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash("Registration successful! Please login", "success")
            return redirect(f"/{role}-login")
        
        return render_template("register.html")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        flash("Registration failed", "danger")
        return redirect("/register")

@app.route("/doctor-dashboard", methods=["GET", "POST"])
def doctor_dashboard():
    if "user_id" not in session or session["role"] != "doctor":
        return redirect("/doctor-login")
    
    doctor_id = session["user_id"]
    
    if request.method == "POST":
        try:
            start_str = request.form.get("start_time")
            end_str = request.form.get("end_time")
            
            start_time = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
            end_time = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)

            if (end_time - start_time) < timedelta(minutes=30):
                flash("Minimum slot duration is 30 minutes", "danger")
                return redirect("/doctor-dashboard")
            
            existing = DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.start_time < end_time,
                DoctorAvailability.end_time > start_time
            ).first()
            
            if existing:
                flash("Overlapping with existing availability", "danger")
                return redirect("/doctor-dashboard")
            
            new_availability = DoctorAvailability(
                doctor_id=doctor_id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_availability)
            db.session.commit()
            flash("Availability added successfully", "success")
            
        except ValueError:
            db.session.rollback()
            flash("Invalid time format", "danger")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Availability error: {str(e)}")
            flash("Error saving availability", "danger")
    
    appointments = Appointment.query.filter_by(doctor_id=doctor_id)\
                    .order_by(Appointment.appointment_time.desc()).all()
    availability_slots = DoctorAvailability.query.filter_by(doctor_id=doctor_id)\
                             .order_by(DoctorAvailability.start_time).all()
    
    min_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')
    return render_template("dashboard_doctor.html", 
                         user=session,
                         appointments=appointments,
                         availability_slots=availability_slots,
                         min_date=min_date)

@app.route("/patient-dashboard")
def patient_dashboard():
    if "user_id" not in session or session["role"] != "patient":
        return redirect("/patient-login")
    
    online_doctors = User.query.filter_by(role="doctor", status="Online").all()
    appointments = Appointment.query.filter_by(patient_id=session["user_id"])\
                    .order_by(Appointment.appointment_time.desc()).all()
    
    return render_template("dashboard_patient.html",
                         user=session,
                         doctors=online_doctors,
                         appointments=appointments)

@app.route("/toggle_status", methods=["POST"])
def toggle_status():
    if "user_id" not in session or session["role"] != "doctor":
        return redirect("/doctor-login")
    
    try:
        user = User.query.get(session["user_id"])
        user.status = "Online" if user.status == "Offline" else "Offline"
        db.session.commit()
        flash(f"Status changed to {user.status}", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Status toggle error: {str(e)}")
        flash("Failed to update status", "danger")
    
    return redirect("/doctor-dashboard")

@app.route("/book", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session or session["role"] != "patient":
        return redirect("/patient-login")

    online_doctors = User.query.filter_by(role="doctor", status="Online").all()
    
    if request.method == "POST":
        try:
            availability_id = request.form.get("availability_id")
            doctor_id = request.form.get("doctor_id")
            
            availability = DoctorAvailability.query.get(availability_id)
            if not availability or availability.status != 'available' or availability.doctor_id != int(doctor_id):
                flash("Slot no longer available", "danger")
                return redirect("/book")
            
            new_appointment = Appointment(
                patient_id=session["user_id"],
                doctor_id=doctor_id,
                availability_id=availability_id,
                appointment_time=availability.start_time,
                status="Pending",
                room_id=generate_room_id()
            )
            
            availability.status = 'booked'
            db.session.add(new_appointment)
            db.session.commit()
            flash("Appointment booked successfully!", "success")
            return redirect("/patient-dashboard")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Booking error: {str(e)}")
            flash("Failed to book appointment", "danger")

    doctor_id = request.args.get("doctor_id")
    available_slots = []
    if doctor_id:
        available_slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.status == 'available',
            DoctorAvailability.start_time > datetime.now(timezone.utc)
        ).order_by(DoctorAvailability.start_time).all()
    
    return render_template("book.html", 
                         doctors=online_doctors,
                         slots=available_slots,
                         selected_doctor_id=doctor_id,
                         min_date=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M'))

@app.route("/delete-slot/<int:slot_id>", methods=["POST"])
def delete_slot(slot_id):
    if "user_id" not in session or session["role"] != "doctor":
        return redirect("/doctor-login")
    
    try:
        slot = DoctorAvailability.query.get(slot_id)
        if slot and slot.doctor_id == session["user_id"]:
            db.session.delete(slot)
            db.session.commit()
            flash("Time slot deleted successfully", "success")
        else:
            flash("Unauthorized action", "danger")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Slot deletion error: {str(e)}")
        flash("Failed to delete time slot", "danger")
    
    return redirect("/doctor-dashboard")

@app.route("/video_call/<room_id>")
def video_call(room_id):
    if "user_id" not in session:
        return redirect("/")
    
    appointment = Appointment.query.filter_by(room_id=room_id).first()
    if not appointment:
        flash("Invalid room ID", "danger")
        return redirect(f"/{session['role']}-dashboard")
    
    if (session['role'] == "patient" and appointment.patient_id != session["user_id"]) or \
       (session['role'] == "doctor" and appointment.doctor_id != session["user_id"]):
        flash("Unauthorized access", "danger")
        return redirect(f"/{session['role']}-dashboard")
    
    return render_template("video_call.html", appointment=appointment)

@app.route("/cancel_appointment/<int:appointment_id>", methods=["POST"])
def cancel_appointment(appointment_id):
    if "user_id" not in session or session["role"] != "patient":
        return redirect("/patient-login")
    
    appointment = Appointment.query.get(appointment_id)
    if appointment and appointment.patient_id == session["user_id"]:
        appointment.status = "Cancelled"
        if appointment.availability:
            appointment.availability.status = 'available'
        db.session.commit()
        flash("Appointment cancelled", "success")
    return redirect("/patient-dashboard")

@app.route("/update_appointment/<int:appointment_id>", methods=["POST"])
def update_appointment(appointment_id):
    if "user_id" not in session or session["role"] != "doctor":
        return redirect("/doctor-login")
    
    appointment = Appointment.query.get(appointment_id)
    if appointment and appointment.doctor_id == session["user_id"]:
        appointment.status = "Done"
        db.session.commit()
        flash("Appointment marked complete", "success")
    return redirect("/doctor-dashboard")

@app.route("/symptom-checker", methods=["GET", "POST"])
def symptom_checker():
    if "user_id" not in session or session["role"] != "patient":
        return redirect("/patient-login")

    if request.method == "POST":
        try:
            symptoms = request.form.get("symptoms", "").split(",")
            age = request.form.get("age", 30)
            gender = request.form.get("gender", "prefer not to say")

            headers = {
                "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
                "X-RapidAPI-Host": "ai-medical-diagnosis-api-symptoms-to-results.p.rapidapi.com"
            }
            payload = {
                "symptoms": [s.strip() for s in symptoms],
                "patientInfo": {"age": age, "gender": gender}
            }

            response = requests.post(
                "https://ai-medical-diagnosis-api-symptoms-to-results.p.rapidapi.com/analyzeSymptomsAndDiagnose?noqueue=1",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return render_template("symptom_results.html", 
                                 result=response.json().get('result', {}),
                                 result_time=datetime.now().timestamp())

        except Exception as e:
            flash(f"Symptom check failed: {str(e)}", "danger")
            return redirect("/symptom-checker")

    return render_template("symptom_checker.html")

@app.route("/reminders", methods=["GET", "POST"])
def reminders():
    if "user_id" not in session or session["role"] != "patient":
        return redirect("/patient-login")

    if request.method == "POST":
        try:
            new_reminder = Reminder(
                user_id=session["user_id"],
                medicine_name=request.form["medicine_name"],
                reminder_time=datetime.fromisoformat(request.form["reminder_time"]),
                notes=request.form.get("notes", ""),
                frequency=request.form.get("frequency", "once")
            )
            db.session.add(new_reminder)
            db.session.commit()
            flash("Reminder added successfully", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

    reminders = Reminder.query.filter_by(user_id=session["user_id"])\
                  .order_by(Reminder.reminder_time).all()
    return render_template("view_reminders.html", reminders=reminders)

@app.route("/delete-reminder/<int:reminder_id>", methods=["POST"])
def delete_reminder(reminder_id):
    if "user_id" not in session:
        return redirect("/login")
    
    reminder = Reminder.query.get(reminder_id)
    if reminder and reminder.user_id == session["user_id"]:
        db.session.delete(reminder)
        db.session.commit()
        flash("Reminder deleted", "success")
    return redirect("/reminders")

def check_reminders():
    while True:
        with app.app_context():
            try:
                now = datetime.now(timezone.utc)
                reminders = Reminder.query.filter(
                    Reminder.alerted == False,
                    Reminder.reminder_time <= now
                ).all()

                for reminder in reminders:
                    print(f"Reminder: {reminder.medicine_name}")
                    if reminder.frequency != 'once':
                        new_time = reminder.reminder_time
                        if reminder.frequency == 'daily':
                            new_time += timedelta(days=1)
                        elif reminder.frequency == 'weekly':
                            new_time += timedelta(weeks=1)
                        reminder.reminder_time = new_time
                    else:
                        reminder.alerted = True
                    
                    db.session.commit()

            except Exception as e:
                print(f"Reminder error: {str(e)}")
        
        time.sleep(60)

@app.route("/logout")
def logout():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user.role == "doctor":
            user.status = "Offline"
            db.session.commit()
    
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/")

@app.cli.command("init-db")
def init_db():
    """Initialize the database"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        logger.info("Database initialized")
    print("Database setup completed")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)
