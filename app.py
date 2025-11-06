import os
import datetime
import re
import smtplib
import json
from threading import Thread
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, jsonify
from flask_cors import CORS

# =========================================================
# STEP 1: Environment + Flask Setup
# =========================================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# =========================================================
# STEP 2: Firebase + Firestore Setup
# =========================================================
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
db = firestore.Client.from_service_account_info(firebase_credentials)

try:
    db.collection("connection_test").add({"status": "success"})
    print("✅ Firestore connected successfully.")
except Exception as e:
    print(f"❌ Firestore connection failed: {e}")

# =========================================================
# STEP 3: Google Sheets Setup
# =========================================================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(firebase_credentials, scopes=SCOPE)
gc = gspread.authorize(creds)
SHEET_NAME = "SmarterStarts_Consultations"
worksheet = gc.open(SHEET_NAME).sheet1


def append_to_sheet(data):
    try:
        worksheet.append_row([
            data["user"]["name"],
            data["user"]["email"],
            data["user"]["company_size"],
            data["user"].get("budget", ""),
            data.get("problem", ""),
            ", ".join(data.get("selected_tools", [])),
            str(data.get("recommendations", ""))[:500],
            data.get("rating", ""),
            data.get("user_feedback", ""),
            data.get("createdAt", ""),
            data.get("status", "Pending Consultation"),
        ])
        print("✅ Synced to Google Sheet successfully.")
    except Exception as e:
        print(f"⚠️ Sheet sync error: {e}")

# =========================================================
# STEP 4: Save to Firestore
# =========================================================
def save_to_firestore(data):
    try:
        db.collection("smarterstarts_sessions").add(data)
        print("✅ Saved to Firestore.")
    except Exception as e:
        print(f"⚠️ Firestore save failed: {e}")

# =========================================================
# STEP 5: Gemini Recommendation Logic (Fixed)
# =========================================================
def recommend_tools(problem_description, company_size):
    try:
        prompt = f"""
        You are an expert SaaS Tool Recommender.
        Based on the user's problem and company size, suggest the top 5 SaaS tools in professional markdown format.

        Problem: {problem_description}
        Company Size: {company_size}

        Each tool must include:
        1. **Tool Name**
        2. **Purpose**
        3. **Why it fits the user's need**
        4. **3–5 Key Features**
        5. **Approx Monthly Pricing (USD)**
        6. **Website Link**
        """

        # ✅ Use fast, stable Gemini model
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 700
            }
        )

        if not response or not response.text:
            raise Exception("Empty Gemini response")

        text = response.text.strip()

        # Extract tool names for frontend display
        tool_names = []
        for line in text.split("\n"):
            match = re.match(r"^\d+\.\s*([A-Za-z0-9 &+_:\-–—()./]+)", line.strip())
            if match:
                tool_names.append(match.group(1).strip())

        return {"text": text, "tools": tool_names[:5]}

    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return {
            "text": "⚠️ Gemini model failed. Please try again.",
            "tools": []
        }

# =========================================================
# STEP 6: Email Alert
# =========================================================
def send_admin_alert(data):
    try:
        sender = os.getenv("ALERT_EMAIL")
        password = os.getenv("ALERT_EMAIL_PASSWORD")
        receiver = os.getenv("ALERT_RECEIVER")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 New SmarterStarts Consultation – {data['user']['name']}"
        msg["From"] = sender
        msg["To"] = receiver

        html = f"""
        <html><body>
        <h3>New Consultation Created 🚀</h3>
        <p><b>Name:</b> {data['user']['name']}<br>
        <b>Email:</b> {data['user']['email']}<br>
        <b>Company Size:</b> {data['user']['company_size']}<br>
        <b>Problem:</b> {data['problem']}</p>
        <p><b>Created:</b> {data['createdAt']}</p>
        </body></html>
        """

        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())

        print("📧 Admin email sent successfully.")
    except Exception as e:
        print(f"⚠️ Email alert failed: {e}")

# =========================================================
# STEP 7: Background Sync
# =========================================================
def background_sync(data):
    try:
        save_to_firestore(data)
        append_to_sheet(data)
        send_admin_alert(data)
    except Exception as e:
        print(f"⚠️ Background sync failed: {e}")

# =========================================================
# STEP 8: API Routes
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "SmarterStarts backend is live ✅"})

@app.route("/recommend", methods=["POST"])
def recommend_api():
    try:
        data = request.get_json()
        print("📩 Received request:", data)

        problem = data.get("problem", "")
        name = data.get("name", "")
        email = data.get("email", "")
        company_size = data.get("company_size", "")
        budget = data.get("budget", "")

        recommendations = recommend_tools(problem, company_size)

        session_data = {
            "user": {
                "name": name,
                "email": email,
                "company_size": company_size,
                "budget": budget,
            },
            "problem": problem,
            "recommendations": recommendations["text"],
            "selected_tools": [],
            "rating": 0,
            "user_feedback": "",
            "status": "Pending Consultation",
            "createdAt": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        # Run Firestore/Sheets/Email in background
        Thread(target=background_sync, args=(session_data,)).start()

        return jsonify({
            "status": "success",
            "recommendations": recommendations["text"],
            "tool_names": recommendations["tools"]
        })
    except Exception as e:
        print("❌ /recommend Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    try:
        data = request.get_json()
        print("📝 Feedback received:", data)
        Thread(target=background_sync, args=(data,)).start()
        return jsonify({"status": "success", "message": "Feedback saved successfully!"})
    except Exception as e:
        print("❌ /submit_feedback Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# =========================================================
# STEP 9: Production Entry Point (Gunicorn)
# =========================================================
if __name__ == "__main__":
    print("🚀 SmarterStarts backend running locally...")
    app.run(host="0.0.0.0", port=5000, debug=True)