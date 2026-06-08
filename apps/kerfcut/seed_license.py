"""
KerfCut — License Seeding Script
Use this to create a real license in your Supabase database.
"""
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
# Some terminal setups set SSLKEYLOGFILE to a non-writable virtual path.
# That causes ssl.create_default_context() to fail before any HTTP request.
os.environ.pop("SSLKEYLOGFILE", None)

# We use the SECRET_KEY (Service Role) to bypass RLS and insert data
URL = os.getenv("PROJECT_URL")
SECRET_KEY = os.getenv("DB_SECRET_KEY")

def create_license(key: str, email: str = "test@example.com"):
    if not URL or not SECRET_KEY:
        print("Error: Missing credentials in .env")
        return

    endpoint = f"{URL}/rest/v1/licenses"
    headers = {
        "apikey": SECRET_KEY,
        "Authorization": f"Bearer {SECRET_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    payload = {
        "key": key,
        "user_email": email,
        "is_active": True
    }
    
    try:
        response = httpx.post(endpoint, headers=headers, json=payload)
        if response.status_code in (201, 204):
            print(f"Successfully created license: {key}")
        else:
            print(f"Failed to create license: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Prefer CLI arg to avoid shell input edge-cases.
    if len(sys.argv) > 1 and sys.argv[1].strip():
        new_key = sys.argv[1].strip()
    else:
        try:
            new_key = input("Enter new license key (or press enter for 'TEST-KEY-2026'): ") or "TEST-KEY-2026"
        except OSError:
            new_key = "TEST-KEY-2026"
            print("Input unavailable in this shell. Using default key: TEST-KEY-2026")
    create_license(new_key)
