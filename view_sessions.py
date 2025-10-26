import json
import datetime
from google.cloud import firestore

# ----------------------------------------------
# Step 1: Connect to Firestore
# ----------------------------------------------
print("🔗 Connecting to Firestore...")
db = firestore.Client.from_service_account_json("keys/smarterstarts1-firebase.json")

# ----------------------------------------------
# Step 2: Retrieve and Display Documents
# ----------------------------------------------
print("\n📂 Listing all Firestore documents in smarterstarts_sessions:\n")

try:
    docs = db.collection("smarterstarts_sessions").stream()

    session_list = []
    for doc in docs:
        data = doc.to_dict()
        data["_id"] = doc.id
        session_list.append(data)

    # ✅ Safe sort for mixed datetime (aware/naive)
    def safe_sort_key(item):
        val = item.get("createdAt", "")
        if isinstance(val, datetime.datetime):
            # convert all to UTC-aware
            if val.tzinfo is None:
                val = val.replace(tzinfo=datetime.timezone.utc)
            return val
        try:
            parsed = datetime.datetime.fromisoformat(val)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return parsed
        except Exception:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    session_list.sort(key=safe_sort_key, reverse=True)

    # Display neatly
    for i, session in enumerate(session_list, start=1):
        print(f"\n📄 Session #{i}")
        print(f"🆔 Document ID: {session.get('_id', 'N/A')}")
        print(json.dumps(session, indent=2, default=str))
        print("-" * 80)

    if not session_list:
        print("⚠️ No documents found in 'smarterstarts_sessions' collection.")

except Exception as e:
    print(f"❌ Error reading Firestore data: {e}")

# ----------------------------------------------
# Step 3: Final message
# ----------------------------------------------
print("\n✅ Firestore session listing complete!\n")
