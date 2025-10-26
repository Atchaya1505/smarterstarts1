import json
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Firebase setup
cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load tool data from JSON file
with open("seed/tools.json", "r") as f:
    tools_data = json.load(f)

# Add tools to Firestore
for tool in tools_data:
    db.collection("tools").add(tool)
    print(f"✅ Added: {tool['name']}")

print("🔥 Seeding complete.")