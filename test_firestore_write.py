from google.cloud import firestore

# 🔹 Step 1 — Connect using your same key
print("Connecting to Firestore...")
db = firestore.Client.from_service_account_json("keys/smarterstarts1-firebase.json")

try:
    # 🔹 Step 2 — Try to write a test document
    test_data = {
        "name": "Atchaya Test",
        "email": "atchaya@test.com",
        "problem": "connectivity check",
        "status": "manual test",
    }

    doc_ref = db.collection("smarterstarts_sessions").add(test_data)
    print("✅ Test document successfully written with ID:", doc_ref[1].id)

    # 🔹 Step 3 — Read back and confirm
    print("\nListing documents in smarterstarts_sessions:")
    docs = db.collection("smarterstarts_sessions").stream()
    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")

except Exception as e:
    print("❌ Firestore test failed:", e)