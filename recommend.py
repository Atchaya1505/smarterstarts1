import os
import json
import datetime
import smtplib
import re
import time
from threading import Thread
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from sheets_updater import append_to_sheet  # ✅ Direct import for live sheet sync
from flask import Flask, request, jsonify
from flask_cors import CORS

# =========================================================
# STEP 1: Flask + Environment setup
# =========================================================
app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:3000",
    "https://smarterstarts-frontend.onrender.com"
])

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
db = firestore.Client.from_service_account_info(firebase_credentials)

# 🔍 Firestore connection test
try:
    db.collection("connection_test").add({"status": "success"})
    print("✅ Firestore connected successfully.")
except Exception as e:
    print(f"❌ Firestore connection failed: {e}")

# =========================================================
# STEP 2: Model detection
# =========================================================
def get_available_model():
    try:
        available_models = list(genai.list_models())
        for m in available_models:
            if hasattr(m, "supported_generation_methods") and "generateContent" in m.supported_generation_methods:
                print(f"✅ Using model: {m.name}")
                return m.name
    except Exception as e:
        print(f"⚠️ Model detection failed: {e}")
    return "models/gemini-1.5-flash-latest"

MODEL_NAME = get_available_model()

# =========================================================
# STEP 3: Helper functions
# =========================================================
def save_to_firestore(data):
    try:
        db.collection("smarterstarts_sessions").add(data)
        print("✅ Saved to Firestore")
    except Exception as e:
        print(f"⚠️ Firestore save failed: {e}")

def recommend_tools(problem_description, company_size):
    try:
        prompt = f"""
        You are an AI SaaS Tool Recommender.
        Analyze the user's problem and company size, then recommend the top 5 SaaS tools.

        Problem: {problem_description}
        Company Size: {company_size}

        For each tool, include:
        1. Tool Name
        2. Core Purpose
        3. How it suits the user's problem
        4. Key Features
        5. Pros
        6. Cons
        7. Approx Monthly Pricing (USD)
        8. Website Link
        """

        # ⚡ Force fastest model
        model = genai.GenerativeModel("gemini-1.5-flash")

        # ⏱ Safer config with soft token limit
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.8,
                "top_p": 0.9,
                "max_output_tokens": 1024
            }
        )

        # ✅ Handle empty or partial responses gracefully
        if response and hasattr(response, "text") and response.text:
            print("✅ Gemini responded successfully.")
            return response.text

        print("⚠️ Gemini returned no text — fallback triggered.")
        return "⚠️ No recommendations generated. Please try again."

    except Exception as e:
        print(f"⚠️ Gemini generation failed: {e}")
        return f"⚠️ Gemini error: {e}"


def send_admin_alert(data):
    try:
        sender = os.getenv("ALERT_EMAIL")
        password = os.getenv("ALERT_EMAIL_PASSWORD")
        receiver = os.getenv("ALERT_RECEIVER")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 New SmarterStarts Consultation – {data['user']['name']}"
        msg["From"] = sender
        msg["To"] = receiver

        selected_tools = data.get("selected_tools", [])
        rating = data.get("rating", None)
        user_feedback = data.get("user_feedback", "No feedback provided")

        star_display = "⭐" * int(rating) if rating else "N/A"
        tool_list_html = (
            "".join(f"<li>{tool}</li>" for tool in selected_tools)
            if selected_tools else "<li>No tools selected</li>"
        )

        html = f"""
        <html><body>
        <h2>🚀 New SmarterStarts Consultation</h2>
        <p><b>Name:</b> {data['user']['name']}<br>
        <b>Email:</b> {data['user']['email']}<br>
        <b>Company Size:</b> {data['user']['company_size']}<br>
        <b>Problem:</b> {data['problem']}</p>
        <p><b>Selected Tools:</b></p>
        <ul>{tool_list_html}</ul>
        <p><b>Rating:</b> {star_display} ({rating if rating else 'N/A'}/5)<br>
        <b>Feedback:</b> {user_feedback}</p>
        <p><b>Created At:</b> {data['createdAt']}</p>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())

        print("📧 Admin email sent.")
    except Exception as e:
        print(f"⚠️ Email send failed: {e}")

# =========================================================
# STEP 4: Background tasks
# =========================================================
def background_sync(data):
    try:
        save_to_firestore(data)
        append_to_sheet(data)
        send_admin_alert(data)
        print("✅ Background sync done")
    except Exception as e:
        print(f"⚠️ Background sync failed: {e}")

# =========================================================
# STEP 5: API Routes
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "SmarterStarts backend live ✅"})

@app.route("/recommend", methods=["POST"])
def recommend_api():
    try:
        data = request.get_json()
        print("📩 Received:", data)

        # Step 1 – Generate Gemini response quickly
        problem = data.get("problem", "")
        company_size = data.get("company_size", "")
        recommendations = recommend_tools(problem, company_size)

        # Prepare session object
        session_data = {
            "user": {
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "company_size": company_size,
                "budget": data.get("budget", "")
            },
            "problem": problem,
            "recommendations": recommendations,
            "selected_tools": [],
            "rating": 0,
            "user_feedback": "",
            "status": "Pending Consultation",
            "createdAt": datetime.datetime.utcnow().isoformat()
        }

        # Step 2 – Send result to frontend immediately
        Thread(target=background_sync, args=(session_data,)).start()
        print("✅ Sent recommendations instantly.")
        return jsonify({"status": "success", "recommendations": recommendations})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json()
        print("📝 Final feedback received:", data)

        save_to_firestore(data)
        append_to_sheet(data)
        send_admin_alert(data)

        return jsonify({"status": "success", "message": "Feedback saved successfully!"})
    except Exception as e:
        print("❌ Error saving feedback:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# =========================================================
# STEP 6: Run Server
# =========================================================
if __name__ == "__main__":
    print("🚀 SmarterStarts backend running on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
