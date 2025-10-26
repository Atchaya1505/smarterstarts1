import os
import json
import datetime
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from sheets_updater import append_to_sheet  # ✅ Direct import for live sheet sync

# ----------------------------------------------
# Step 1: Environment setup
# ----------------------------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
import json, os
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
db = firestore.Client.from_service_account_info(firebase_credentials)

# 🔍 Firestore connection test
try:
    db.collection("connection_test").add({"status": "success"})
    print("✅ Firestore connected successfully and test document created.")
except Exception as e:
    print(f"❌ Firestore connection failed: {e}")

# ----------------------------------------------
# Step 2: Auto-detect valid Gemini model
# ----------------------------------------------
def get_available_model():
    try:
        available_models = list(genai.list_models())
        for m in available_models:
            if hasattr(m, "supported_generation_methods") and "generateContent" in m.supported_generation_methods:
                print(f"✅ Found compatible model: {m.name}")
                return m.name
        print("⚠️ No compatible model found. Defaulting to gemini-1.5-flash-latest.")
        return "models/gemini-1.5-flash-latest"
    except Exception as e:
        print(f"⚠️ Error detecting model. Defaulting to gemini-1.5-flash-latest. Error: {e}")
        return "models/gemini-1.5-flash-latest"

MODEL_NAME = get_available_model()

# ----------------------------------------------
# Step 3: Firestore Save Function
# ----------------------------------------------
def save_to_firestore(data):
    try:
        print("📝 Saving data to Firestore (smarterstarts_sessions)...")
        db.collection("smarterstarts_sessions").add(data)
        print("✅ Data successfully saved to smarterstarts_sessions.\n")

    except Exception as e:
        print(f"⚠️ Firestore save failed: {e}\n")


# ----------------------------------------------
# Step 4: Generate Recommendations
# ----------------------------------------------
def recommend_tools(problem_description, company_size):
    try:
        prompt = f"""
        You are an AI SaaS Tool Recommender.
        Analyze the user's problem and company size, then recommend the **top 5 SaaS tools** ranked from 1 to 5.

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

        Format neatly as:
        1. ToolName - short summary
        2. ToolName - short summary
        ...
        """
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text if response and response.text else "⚠️ No recommendations found."
    except Exception as e:
        return f"⚠️ Error generating recommendations: {e}"

# ----------------------------------------------
# Step 5: Send Admin Email Alert
# ----------------------------------------------
def send_admin_alert(data):
    try:
        sender = os.getenv("ALERT_EMAIL")
        password = os.getenv("ALERT_EMAIL_PASSWORD")
        receiver = os.getenv("ALERT_RECEIVER")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚀 New SmarterStarts Consultation – {data['user']['name']}"
        msg["From"] = sender
        msg["To"] = receiver

        # ✅ Ensure these fields exist (avoid KeyError)
        selected_tools = data.get("selected_tools", [])
        rating = data.get("rating", None)
        user_feedback = data.get("user_feedback", "No feedback provided")

        # ✅ Create formatted stars (⭐)
        star_display = "⭐" * int(rating) if rating else "N/A"

        # ✅ Make tools list HTML
        tool_list_html = (
            "".join(f"<li>{tool}</li>" for tool in selected_tools)
            if selected_tools else "<li>No tools selected</li>"
        )

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color:#222;">
            <h2>🚀 New SmarterStarts Consultation Alert</h2>

            <p><b>Name:</b> {data['user']['name']}<br>
            <b>Email:</b> {data['user']['email']}<br>
            <b>Company Size:</b> {data['user']['company_size']}<br>
            <b>Problem:</b> {data['problem']}</p>

            <hr style="border:0; border-top:1px solid #ccc; margin:12px 0;">

            <p><b>Selected Tools:</b></p>
            <ul>{tool_list_html}</ul>

            <p><b>Rating:</b> {star_display} ({rating if rating else 'N/A'}/5)<br>
            <b>Feedback:</b> {user_feedback}</p>

            <p><b>Created At:</b> {data['createdAt']}</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.sendmail(sender, receiver, msg.as_string())

        print("📧 Admin alert email sent successfully with tools, rating & feedback.")
    except Exception as e:
        print(f"❌ Failed to send admin alert: {e}")

# ----------------------------------------------
# Step 6: Main Workflow
# ----------------------------------------------
def main():
    print("\n💡 Welcome to SmarterStarts AI Tool Finder 💡\n")

    problem = input("🧠 Describe the problem you're trying to solve:\n> ")
    print("\n📩 Please share your details:\n")
    name = input("Your Name: ")
    email = input("Your Email: ")
    company_size = input("Company Size (Solo / SMB / Mid / Enterprise): ")
    budget = input("Approx Monthly Budget (USD): ")

    print("\n🤖 Generating your top SaaS recommendations...\n")
    recommendations = recommend_tools(problem, company_size)
    print("\n✨ Here are your personalized recommendations:\n")
    print(recommendations)
    print("------------------------------------------------------------")

    selected_tools = input("✅ Which tools would you like to explore further? (Enter numbers separated by commas): ")

    # Extract tool names
    lines = recommendations.split("\n")
    selected_tool_names = []
    for num in selected_tools.split(","):
        num = num.strip()
        if num.isdigit():
            pattern = re.compile(rf"[*#\s]*{num}\.\s*([A-Za-z0-9][A-Za-z0-9\s&+:\-–—_/()]+)", re.UNICODE)
            for line in lines:
                clean_line = line.strip().replace("**", "").replace("*", "")
                match = pattern.match(clean_line)
                if match:
                    tool_name = re.split(r"[-–—:]", match.group(1).strip())[0].strip()
                    selected_tool_names.append(tool_name)
                    break

    if selected_tool_names:
        print(f"🎯 You selected: {', '.join(selected_tool_names)}")
    else:
        print("⚠️ Could not extract tool names from recommendations.")

    # Rating + Feedback
    while True:
        try:
            rating = int(input("\n⭐ Rate your experience (1–5): "))
            if 1 <= rating <= 5:
                break
            else:
                print("⚠️ Please enter a number between 1–5.")
        except ValueError:
            print("⚠️ Invalid input. Please enter a number between 1–5.")

    user_feedback = input("\n📝 Please share your detailed feedback:\n> ")

    # Prepare session data
    session_data = {
        "user": {
            "name": name,
            "email": email,
            "company_size": company_size,
            "budget": budget,
        },
        "problem": problem,
        "recommendations": recommendations,
        "selected_tools": selected_tool_names,
        "rating": rating,
        "user_feedback": user_feedback,
        "status": "Pending Consultation",
        "createdAt": datetime.datetime.utcnow().isoformat()
    }

    # --------------------------------------
    # 🔁 Run all three in real time
    # --------------------------------------
    print("\n💾 Syncing data across all systems...\n")

    save_to_firestore(session_data)     # Firestore ✅
    send_admin_alert(session_data)      # Email ✅
    append_to_sheet(session_data)       # Google Sheet ✅

    print("\n🎯 Great choice! We've saved your preferences.\n")
    print("------------------------------------------------------------")
    print("🧩 Done For You — SmarterStarts Implementation Offer 🧩\n")
    print("Your personalized tool recommendations have been saved.")
    print("💬 Book a free consultation now:")
    print("📅 https://calendar.app.google/RrukbCNLTkUuDyYG8\n")
    print("------------------------------------------------------------")
    print("💾 All data synced: Firestore + Email + Google Sheet ✅")

# ----------------------------------------------
# Entry Point
# ----------------------------------------------
if __name__ == "__main__":
    main()
