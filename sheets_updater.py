import gspread
from google.oauth2.service_account import Credentials

# ----------------------------------------------
# Google Sheets authentication
# ----------------------------------------------
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

import json, os
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
creds = Credentials.from_service_account_info(firebase_credentials, scopes=SCOPE)
)

gc = gspread.authorize(creds)

# ----------------------------------------------
# Define sheet
# ----------------------------------------------
SHEET_NAME = "SmarterStarts_Consultations"
worksheet = gc.open(SHEET_NAME).sheet1

# ----------------------------------------------
# Append data function
# ----------------------------------------------
def append_to_sheet(data):
    try:
        worksheet.append_row([
            data["user"]["name"],
            data["user"]["email"],
            data["user"]["company_size"],
            data["user"]["budget"],
            data["problem"],
            ", ".join(data.get("selected_tools", [])),
            data.get("recommendations", "")[:500],  # limit for readability
            data.get("rating", ""),
            data.get("user_feedback", ""),
            data.get("createdAt", ""),
            data.get("status", "Pending Consultation")
        ])
        print("✅ Data synced to Google Sheet successfully!")
    except Exception as e:
        print(f"⚠️ Error syncing to Google Sheet: {e}")

# ----------------------------------------------
# Optional test
# ----------------------------------------------
if __name__ == "__main__":
    # Test a dummy entry (remove later)
    append_to_sheet({
        "user": {
            "name": "Test User",
            "email": "test@smarterstarts.ai",
            "company_size": "SMB",
            "budget": "100"
        },
        "problem": "onboarding issues",
        "selected_tools": ["HubSpot", "Asana"],
        "recommendations": "HubSpot - for CRM and automation, Asana - for project tracking",
        "rating": 5,
        "user_feedback": "Works great!",
        "createdAt": "2025-10-24T17:00:00Z",
        "status": "Pending Consultation"
    })
