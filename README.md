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
