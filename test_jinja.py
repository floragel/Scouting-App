import requests
import sys

base_url = 'http://localhost:5002'
session = requests.Session()

print("1. Registering/Logging into 2 dummy users: Admin & Scout")

# Admin Login
try:
    res = session.post(f"{base_url}/api/auth/register", json={"email": "admin@frc.com", "password": "password", "name": "Admin User"})
    if "Email already" in res.text:
         res = session.post(f"{base_url}/api/auth/login", json={"email": "admin@frc.com", "password": "password"})
    print(f"Admin Auth Response: {res.status_code}")
except Exception as e:
    print(f"Admin Auth Failed: {e}")

# Check Admin Dashboard
res2 = session.get(f"{base_url}/scout-dashboard")
print(f"Admin Dashboard Response: {res2.status_code}")
if "Admin Panel" in res2.text:
     print("SUCCESS: Admin panel rendered correctly.")
else:
     print("FAIL: Admin panel not found.")

# We won't test Scout rendering yet because we need to seed the database directly. Let's do that.
