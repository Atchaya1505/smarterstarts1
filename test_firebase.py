from google.cloud import firestore

# Connect using your existing key
db = firestore.Client.from_service_account_json("keys/smarterstarts1-firebase.json")

print("🔍 Connected to Firestore...")

# Add test data
doc_ref = db.collection("smarterstarts_sessions").add({
    "test_field": "hello smarterstarts",
    "status": "firestore connectivity test"
})

print(f"✅ Test document written with ID: {doc_ref[1].id}")

# Read back to confirm
print("\n📄 Listing all docs in smarterstarts_sessions:")
docs = db.collection("smarterstarts_sessions").stream()
for doc in docs:
    print(f"→ {doc.id}: {doc.to_dict()}")