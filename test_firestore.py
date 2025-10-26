from google.cloud import firestore

print("🔗 Connecting to Firestore...")

try:
    # Connect using your service account
    db = firestore.Client.from_service_account_json("keys/smarterstarts1-firebase.json")

    # Test write
    doc_ref = db.collection("smarterstarts_sessions").add({
        "test_field": "Hello Smarterstarts 🔥",
        "status": "connectivity check"
    })
    print(f"✅ Firestore connected and test document added! ID: {doc_ref[1].id}")

    # Test read
    print("\n📂 All documents in smarterstarts_sessions:")
    docs = db.collection("smarterstarts_sessions").stream()
    for doc in docs:
        print(doc.id, "=>", doc.to_dict())

except Exception as e:
    print(f"❌ Firestore connection failed: {e}")
