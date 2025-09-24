🏥 Teledoctor – Telemedicine Platform

A telemedicine web application that bridges the gap between rural patients and doctors through secure video consultations, appointment management, and healthcare tools. Built with Flask, SQLAlchemy, and Jitsi Meet API, the project demonstrates how technology can make healthcare more accessible and cost-effective.

🚀 Features

👨‍⚕️ Role-based Login – Separate login for doctors and patients with OTP verification

📅 Appointment Management – Patients can book, cancel, and view appointments; doctors can manage availability and consultations

📹 Video Consultations – Secure, browser-based video calls using Jitsi Meet API

💊 Medication Reminders – Patients can set reminders for medicines with recurrence options

🤖 Symptom Checker – AI-powered preliminary diagnosis tool (via external API)

🟢 Doctor Availability Tracking – Real-time online/offline status for doctors

🔒 Security – CSRF protection, password hashing, session-based authentication

🛠️ Tech Stack

Frontend: HTML5, CSS3, Bootstrap, Jinja2
Backend: Python Flask, SQLAlchemy
Database: SQLite (development), can scale to PostgreSQL
Video Calling: Jitsi Meet API
Other Tools: Requests, Flask-WTF, WTForms, dotenv
Deployment: Localhost / Cloud server (Heroku, AWS, etc.)

📂 Project Structure
teledoctor/
│── app.py                 # Main Flask application
│── add_data.py             # Script to add sample users & appointments
│── database.db             # SQLite database (auto-created)
│── requirements.txt        # Python dependencies
│── /templates              # HTML templates (home, login, register, dashboards, etc.)
│── /static                 # CSS, JS, images

⚡ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/your-username/teledoctor.git
cd teledoctor

2️⃣ Create Virtual Environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Setup Environment Variables

Create a .env file in the root directory:

SECRET_KEY=your_secret_key
DATABASE_URI=sqlite:///database.db?check_same_thread=False
RAPIDAPI_KEY=your_rapidapi_key

5️⃣ Initialize Database
flask init-db

6️⃣ Run the App
python app.py


App will run at: http://127.0.0.1:5000/

📸 Screenshots

Home Page

Patient Dashboard

Doctor Dashboard

Video Call Page

Symptom Checker

Medication Reminder

🔮 Future Enhancements

AI-powered advanced symptom analysis

Mobile App (Android & iOS)

Digital e-prescriptions

SMS-based offline reminders

Migration to PostgreSQL for production

👨‍💻 Contributors

S. Karthik Reddy (22ECB0B02)

P. Moulik (22ECB0B29)

Supervised by: Prof. Lakshmi B
Department of ECE, NIT Warangal

Would you like me to also generate a requirements.txt file from your app.py so you can directly include it in the GitHub repo?
