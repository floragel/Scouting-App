import requests
import sys

base_url = 'http://localhost:5002'
session = requests.Session()

print("1. Registering dummy user to get session...")
try:
    res = session.post(f"{base_url}/api/auth/register", json={
        "email": "testscout@frc-scouting.com",
        "password": "password123",
        "name": "Test Scout"
    })
    if res.status_code == 400 and "Email already registered" in res.text:
         print("User already exists, logging in instead...")
         res = session.post(f"{base_url}/api/auth/login", json={"email": "testscout@frc-scouting.com", "password": "password123"})
         
    print(f"Auth Response: {res.status_code}")
except Exception as e:
    print(f"Error during auth: {e}")
    sys.exit(1)

print("\n2. Testing /admin-hub routing. Expect redirect since user is non-admin/pending.")
res2 = session.get(f"{base_url}/admin-hub", allow_redirects=False)
print(f"/admin-hub Response Code: {res2.status_code}")
print(f"Location header: {res2.headers.get('Location')}")
if "/scout-dashboard" in res2.headers.get('Location', ''):
    print("SUCCESS: Redirects to scout-dashboard correctly.")
else:
    print("FAIL: Did not redirect correctly.")

print("\n3. Testing profile edit page route (/profile/edit).")
res3 = session.get(f"{base_url}/profile/edit")
print(f"/profile/edit Response Code: {res3.status_code}")
if "Profile & Settings Edit" in res3.text:
    print("SUCCESS: Profile edit HTML served.")
else:
    print("FAIL: HTML does not match.")

print("\n4. Testing /api/user/me PUT.")
res4 = session.put(f"{base_url}/api/user/me", json={"name": "Test Scout Renamed", "email": "testscout@frc-scouting.com"})
print(f"PUT /api/user/me Response Code: {res4.status_code}")
print(f"Response Body: {res4.text}")
if "Test Scout Renamed" in res4.text:
    print("SUCCESS: Profile update works.")
else:
    print("FAIL: Profile name not updated.")

