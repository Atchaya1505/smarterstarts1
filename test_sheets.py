import os
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Define the scopes required for Sheets and Drive API access
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials from the service account JSON file
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Authorize gspread with the credentials
gc = gspread.authorize(creds)

# Access your Google Sheet by its ID (from .env)
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")

try:
    # Open the sheet and get the first worksheet
    sheet = gc.open_by_key(SHEET_ID).sheet1

    # Update cell A1 with a test message (use list of lists!)
    sheet.update('A1', [['✅ Connection successful!']])

    print("✅ Successfully updated Google Sheet!")

except gspread.exceptions.SpreadsheetNotFound:
    print("❌ Spreadsheet not found. Please check your GOOGLE_SHEETS_ID and sharing permissions.")
except gspread.exceptions.APIError as e:
    print(f"⚠️ Google Sheets API error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")