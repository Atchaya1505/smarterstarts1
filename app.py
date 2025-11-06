import os
import datetime
import re
import smtplib
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
# STEP 1: Load environment and configure APIs
# =========================================================
app = Flask(__name__)

# ✅ FIXED CORS for Render
CORS(app, origins=["*"], supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response


# =========================================================
# STEP 2: Environment and Firestore Setup
# =========================================================
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import json
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
    """Append consultation session data to Google Sheets."""
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
        print("✅ Data synced to Google Sheet successfully!")
    except Exception as e:
        print(f"⚠️ Error syncing to Google Sheet: {e}")


# =========================================================
# STEP 4: Firestore Save
# =========================================================
def save_to_firestore(data):
    try:
        db.collection("smarterstarts_sessions").add(data)
        print("✅ Data saved to smarterstarts_sessions.")
    except Exception as e:
        print(f"⚠️ Firestore save failed: {e}")


# =========================================================
# STEP 5: Gemini Model Configuration (Fixed)
# =========================================================
def get_available_model():
    """Use a fixed stable Gemini model for production."""
    model_name = "models/gemini-1.5-pro-latest"
    print(f"✅ Using fixed Gemini model: {model_name}")
    return model_name


MODEL_NAME = get_available_model()


# =========================================================
# STEP 6: Generate Recommendations
# =========================================================
def recommend_tools(problem_description, company_size):
    prompt = f"""
    You are an expert AI SaaS Tool Recommender. Analyze the user's problem and company size, 
    and generate the **top 5 SaaS tools**, ranked 1–5, in professional markdown format.

    Problem: {problem_description}
    Company Size: {company_size}

    Each tool must include:
    1. **Tool Name**
    2. **Core Purpose**
    3. **How it suits the user's problem**
    4. **Key Features** (4–6 bullet points)
    5. **Pros**
    6. **Cons**
    7. **Approx Monthly Pricing (USD)**
    8. **Website Link**

    Ensure clean, readable markdown format.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        # ✅ Added longer timeout + better error tracking
        response = model.generate_content(prompt, request_options={"timeout": 60})

        if not response or not hasattr(response, "text") or not response.text.strip():
            raise Exception("Empty Gemini response or timeout")

        text = response.text.strip()

        # Extract tool names
        lines = text.split("\n")
        tool_names = []
        for line in lines:
            match = re.match(r"^\d+\.\s*([A-Za-z0-9 &+_:\-–—()./]+)", line.strip())
            if match:
                tool_names.append(match.group(1).strip())

        print("✅ Gemini generation succeeded.")
        return {"text": text, "tools": tool_names}

    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return {
            "text": """
1. ClickUp – All-in-one project management.
2. HubSpot – CRM & marketing automation.
3. Notion – Team workspace.
4. Asana – Workflow management.
5. Zoho Projects – Affordable suite.
""",
            "tools": ["ClickUp", "HubSpot", "Notion", "Asana", "Zoho Projects"]
        }


# =========================================================
# STEP 7: Email Notification
# =========================================================
def send_admin_alert(data):
    """Send email to admin when new consultation is created."""
    try:
        sender = os.getenv("ALERT_EMAIL")
        password = os.getenv("ALERT_EMAIL_PASSWORD")
        receiver = os.getenv("ALERT_RECEIVER")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 New SmarterStarts Consultation – {data['user']['name']}"
        msg["From"] = sender
        msg["To"] = receiver

        html = f"""
        <html>
        <body>
        <h3>New SmarterStarts Consultation Alert 🚀</h3>
        <p><b>Name:</b> {data['user']['name']}<br>
        <b>Email:</b> {data['user']['email']}<br>
        <b>Company Size:</b> {data['user']['company_size']}<br>
        <b>Problem:</b> {data['problem']}</p>
        <p><b>Selected Tools:</b> {", ".join(data.get("selected_tools", []))}</p>
        <p><b>Rating:</b> {data.get("rating", "N/A")} / 5<br>
        <b>Feedback:</b> {data.get("user_feedback", "N/A")}</p>
        <p><b>Created:</b> {data['createdAt']}</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())

        print("📧 Admin alert sent successfully.")
    except Exception as e:
        print(f"⚠️ Email alert failed: {e}")


# =========================================================
# STEP 8: Flask API Routes
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "SmarterStarts backend is live ✅"})


@app.route("/recommend", methods=["POST"])
def recommend_api():
    """Generate AI recommendations and save the initial session."""
    try:
        data = request.get_json()
        print("📩 Received:", data)

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

        save_to_firestore(session_data)
        append_to_sheet(session_data)
        send_admin_alert(session_data)

        return jsonify({
            "status": "success",
            "recommendations": recommendations["text"],
            "tool_names": recommendations["tools"]
        })
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    """Save final selected tools, rating, and feedback."""
    try:
        data = request.get_json()
        print("📝 Final submission received:", data)

        save_to_firestore(data)
        append_to_sheet(data)
        send_admin_alert(data)

        return jsonify({"status": "success", "message": "Feedback saved successfully!"})
    except Exception as e:
        print("❌ Error saving feedback:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# =========================================================
# STEP 9: Run the server
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ✅ Render dynamically assigns the port
    print(f"🚀 SmarterStarts Flask backend running on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)