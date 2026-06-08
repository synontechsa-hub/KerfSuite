"""
KerfCut — Authentication & Licensing
Handles secure communication with Supabase for license verification.
"""
import os
import sys
import httpx
import json
import time
import secrets
import base64
import uuid
import hashlib
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from PyQt6.QtCore import QSettings
from dotenv import load_dotenv
from core import config
from utils.logger import logger
from version import APP_NAME, APP_AUTHOR

# Some terminal setups export SSLKEYLOGFILE to a virtual path that is not writable.
# Python's ssl.create_default_context() then raises PermissionError before any request.
os.environ.pop("SSLKEYLOGFILE", None)

# Load environment variables from .env (only used for local dev overrides)
load_dotenv()

SUPABASE_URL = os.getenv("PROJECT_URL", config.SUPABASE_URL)
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", config.SUPABASE_KEY)

# Trial limits
TRIAL_MAX_DAYS = 14
TRIAL_MAX_RUNS = 20

# Free tier limits
FREE_MAX_SHEETS = 2
FREE_MAX_PIECES = 20


def force_trial_mode_enabled() -> bool:
    """Developer override: force app to behave as trial mode."""
    return os.getenv("KERFCUT_FORCE_TRIAL", "").lower() in {"1", "true", "yes"}


def _cache_trial_status(tier: str, runs_left: int, days_left: int):
    """Persist trial state for offline fallback."""
    settings = QSettings(APP_AUTHOR, APP_NAME)
    settings.setValue("trial/cached_tier", tier)
    settings.setValue("trial/cached_runs_left", runs_left)
    settings.setValue("trial/cached_days_left", days_left)


def dev_license_enabled() -> bool:
    """Allow the local dev key only during source-based development runs."""
    enabled = os.getenv("KERFCUT_DEV_LICENSE", "").lower() in {"1", "true", "yes"}
    return enabled and not getattr(sys, "frozen", False)

def _get_install_secret() -> bytes:
    """Get or create a per-install secret for offline token encryption."""
    settings = QSettings(APP_AUTHOR, APP_NAME)
    secret_hex = settings.value("auth/install_secret", "", type=str)
    if not secret_hex:
        secret_hex = secrets.token_hex(32)
        settings.setValue("auth/install_secret", secret_hex)
    return secret_hex.encode("utf-8")

def _get_fernet() -> Fernet:
    """Derive the encryption key from machine identity and a per-install secret."""
    install_secret = _get_install_secret()
    mac = str(uuid.getnode()).encode("utf-8")
    digest = hashlib.sha256(install_secret + mac).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

def _get_machine_id() -> str:
    """Generate a unique, stable composite hardware fingerprint.

    Combines multiple hardware identifiers to make spoofing significantly
    harder than a MAC-only approach.  Each component is read via subprocess
    with a short timeout; if any source fails the fingerprint degrades
    gracefully (the remaining components still produce a deterministic hash).

    Sources:
      1. MAC address         — trivial to spoof alone, but stable across OS reinstalls.
      2. Windows Machine SID — hard to change without breaking the OS install.
      3. Boot disk serial    — manufacturer-assigned, very hard to fake.
    """
    import subprocess

    components: list[str] = []

    # 1. MAC address (always available via uuid)
    components.append(str(uuid.getnode()))

    # 2. Windows Machine SID (the domain prefix, not the per-user RID)
    try:
        result = subprocess.run(
            ["wmic", "useraccount", "where",
             f"name='{os.environ.get('USERNAME', '')}'", "get", "sid"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.startswith("S-"):
                # Strip the per-user RID to get the machine-level SID
                machine_sid = "-".join(line.split("-")[:-1])
                components.append(machine_sid)
                break
    except Exception:
        # Fallback: try PowerShell Get-CimInstance (wmic is deprecated on Win11)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_UserAccount -Filter "
                 f"\"Name='{os.environ.get('USERNAME', '')}'\").SID"],
                capture_output=True, text=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line.startswith("S-"):
                    machine_sid = "-".join(line.split("-")[:-1])
                    components.append(machine_sid)
                    break
        except Exception:
            pass  # Both failed — omit this component

    # 3. Boot disk serial number
    try:
        result = subprocess.run(
            ["wmic", "diskdrive", "where", "Index=0", "get", "SerialNumber"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines()
                 if l.strip() and l.strip().lower() != "serialnumber"]
        if lines:
            components.append(lines[0])
    except Exception:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_DiskDrive -Filter 'Index=0').SerialNumber"],
                capture_output=True, text=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            serial = result.stdout.strip()
            if serial:
                components.append(serial)
        except Exception:
            pass

    combined = "|".join(components)
    return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()


def get_machine_id_display() -> str:
    """Return the machine ID formatted for display (XXXX-XXXX-XXXX-XXXX)."""
    mid = _get_machine_id()
    return "-".join([mid[i:i + 4] for i in range(0, 16, 4)])

def save_offline_token(license_key: str):
    """Saves an encrypted token valid for 30 days."""
    try:
        # 30 day grace period
        expiry = time.time() + (30 * 24 * 60 * 60)
        data = {
            "key": license_key,
            "expires_at": expiry,
            "machine_id": _get_machine_id()
        }
        encrypted = _get_fernet().encrypt(json.dumps(data).encode("utf-8"))
        
        settings = QSettings(APP_AUTHOR, APP_NAME)
        settings.setValue("auth/grace_token", encrypted.decode("utf-8"))
        # Record this to detect clock rollbacks
        settings.setValue("auth/last_verified", time.time())
        logger.info("Offline grace token saved.")
    except Exception as e:
        logger.error(f"Failed to save offline token: {e}", exc_info=True)

def check_offline_token() -> bool:
    """Checks if a valid, unexpired offline token exists for this machine."""
    if force_trial_mode_enabled():
        return False
    settings = QSettings(APP_AUTHOR, APP_NAME)
    
    # 1. Clock Tampering Check
    last_verified = float(settings.value("auth/last_verified", 0))
    current_time = time.time()
    
    if current_time < last_verified - 3600: # Allow 1 hour drift
        logger.warning("System clock appears to have been rolled back. Invalidating offline token.")
        return False

    token = settings.value("auth/grace_token", "")
    if not token:
        return False
        
    try:
        decrypted = _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        data = json.loads(decrypted)
        
        # 2. Expiry Check
        if time.time() > data.get("expires_at", 0):
            logger.warning("Offline grace token has expired.")
            return False
            
        # 3. Hardware Lock Check
        if data.get("machine_id") != _get_machine_id():
            logger.error("Offline token belongs to a different machine.")
            return False

        logger.info("Valid 30-day offline token found.")
        return True
    except Exception as e:
        logger.error(f"Offline token validation failed: {e}")
        return False


def get_license_info() -> dict:
    """Returns information about the current license status for UI display.
    Returns dict with keys: status, days_left, tier ('pro', 'trial', 'free').
    """
    if dev_license_enabled():
        return {"status": "Developer", "days_left": 999, "tier": "pro"}

    if force_trial_mode_enabled():
        trial = get_trial_status()
        if trial["tier"] == "trial":
            runs_left = trial["runs_left"]
            return {
                "status": "Trial",
                "days_left": trial["days_left"],
                "runs_left": runs_left,
                "runs_used": max(0, TRIAL_MAX_RUNS - runs_left),
                "runs_total": TRIAL_MAX_RUNS,
                "tier": "trial"
            }
        return {"status": "Free Tier", "days_left": 0, "tier": "free"}
        
    settings = QSettings(APP_AUTHOR, APP_NAME)
    token = settings.value("auth/grace_token", "")
    
    # Check for active Pro license first
    if token:
        try:
            decrypted = _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
            data = json.loads(decrypted)
            
            expires_at = data.get("expires_at", 0)
            remaining_seconds = expires_at - time.time()
            days_left = max(0, int(remaining_seconds / (24 * 60 * 60)))
            
            if data.get("machine_id") != _get_machine_id():
                return {"status": "Hardware Mismatch", "days_left": 0, "tier": "free"}
            
            if remaining_seconds > 0:
                return {
                    "status": "Activated",
                    "days_left": days_left,
                    "key": data.get("key", "****"),
                    "tier": "pro"
                }
        except Exception as e:
            logger.warning(f"Failed to parse offline token: {e}")
    
    # No valid Pro license — check trial status
    trial = get_trial_status()
    if trial["tier"] == "trial":
        runs_left = trial["runs_left"]
        return {
            "status": "Trial",
            "days_left": trial["days_left"],
            "runs_left": runs_left,
            "runs_used": max(0, TRIAL_MAX_RUNS - runs_left),
            "runs_total": TRIAL_MAX_RUNS,
            "tier": "trial"
        }
    
    return {"status": "Free Tier", "days_left": 0, "tier": "free"}


def get_trial_status() -> dict:
    """
    Query Supabase for the current machine's trial record.
    Creates a new record on first contact.
    Returns dict with keys: tier ('trial' or 'free'), runs_left, days_left.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No Supabase credentials — defaulting to free tier.")
        return {"tier": "free", "runs_left": 0, "days_left": 0}
    
    current_mid = _get_machine_id()
    url = f"{SUPABASE_URL}/rest/v1/trials"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # Check if trial record exists
            response = client.get(url, headers=headers, params={
                "machine_id": f"eq.{current_mid}",
                "select": "*"
            })
            
            if response.status_code != 200:
                logger.error(f"Trial check failed: {response.status_code}")
                return {"tier": "free", "runs_left": 0, "days_left": 0}
            
            data = response.json()
            
            if not data:
                # First launch — create trial record
                insert_resp = client.post(url, headers=headers, json={
                    "machine_id": current_mid,
                    "runs_count": 0
                })
                if insert_resp.status_code in (200, 201):
                    logger.info("Trial started.")
                    trial_status = {"tier": "trial", "runs_left": TRIAL_MAX_RUNS, "days_left": TRIAL_MAX_DAYS}
                    _cache_trial_status(**trial_status)
                    return trial_status
                else:
                    logger.error(f"Failed to create trial record: {insert_resp.text}")
                    return {"tier": "free", "runs_left": 0, "days_left": 0}
            
            record = data[0]
            runs_count = record.get("runs_count", 0)
            started_at = record.get("started_at", "")
            
            # Calculate days elapsed
            try:
                start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                elapsed_days = (datetime.now(timezone.utc) - start_dt).days
            except (ValueError, AttributeError):
                elapsed_days = TRIAL_MAX_DAYS  # Fail safe to expired
            
            days_left = max(0, TRIAL_MAX_DAYS - elapsed_days)
            runs_left = max(0, TRIAL_MAX_RUNS - runs_count)
            
            if days_left > 0 and runs_left > 0:
                trial_status = {"tier": "trial", "runs_left": runs_left, "days_left": days_left}
            else:
                trial_status = {"tier": "free", "runs_left": 0, "days_left": 0}
            _cache_trial_status(**trial_status)
            return trial_status
                
    except httpx.RequestError as e:
        logger.error(f"Network error checking trial: {e}")
        # Offline fallback — check local cache
        settings = QSettings(APP_AUTHOR, APP_NAME)
        cached_tier = settings.value("trial/cached_tier", "free")
        cached_runs = int(settings.value("trial/cached_runs_left", 0))
        cached_days = int(settings.value("trial/cached_days_left", 0))
        return {"tier": cached_tier, "runs_left": cached_runs, "days_left": cached_days}
    except Exception as e:
        logger.error(f"Unexpected error in get_trial_status: {e}", exc_info=True)
        return {"tier": "free", "runs_left": 0, "days_left": 0}


def increment_trial_run() -> bool:
    """
    Increment the trial run counter in Supabase.
    Also caches the result locally for offline fallback.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    
    current_mid = _get_machine_id()
    rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/increment_trial_run"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(rpc_url, headers=headers, json={"p_machine_id": current_mid})
            if resp.status_code not in (200, 201, 204):
                logger.error(f"Atomic trial increment failed: {resp.status_code} - {resp.text}")
                return False

            result = resp.json() if resp.content else None
            if isinstance(result, list) and result:
                payload = result[0] if isinstance(result[0], dict) else {}
            elif isinstance(result, dict):
                payload = result
            else:
                payload = {}

            new_count = int(payload.get("runs_count", 0))
            runs_left = max(0, TRIAL_MAX_RUNS - new_count)
            days_left = int(payload.get("days_left", 0))
            tier = "trial" if runs_left > 0 and days_left > 0 else "free"
            _cache_trial_status(tier=tier, runs_left=runs_left, days_left=days_left)
            logger.info(f"Trial run incremented to {new_count}/{TRIAL_MAX_RUNS}.")
            return True
    except Exception as e:
        logger.error(f"Failed to increment trial run: {e}")
        return False


def verify_license(license_key: str) -> bool:
    """
    Check the 'license_slots' table in Supabase for a matching CDKey.
    Handles three statuses:
      - 'waiting'  → first activation, bind machine ID and set active
      - 'active'   → verify bound machine ID matches
      - 'revoked'  → deny access and clear any local offline tokens
    """
    # Development Bypass
    if license_key == "KERFCUT-DEV-99" and dev_license_enabled():
        logger.info("Development bypass key used.")
        save_offline_token(license_key)
        return True

    if force_trial_mode_enabled():
        logger.info("Trial mode forced via KERFCUT_FORCE_TRIAL; skipping license verification.")
        return False

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Licensing Error: Missing Supabase credentials in core/config.py")
        return False
        
    current_mid = _get_machine_id()
    url = f"{SUPABASE_URL}/rest/v1/license_slots"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # 1. Fetch the license slot by CDKey
            params = {
                "cdkey": f"eq.{license_key}",
                "select": "*"
            }
            response = client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"Supabase check failed: {response.status_code}")
                return False
                
            data = response.json()
            if not data:
                logger.warning("License key not found.")
                return False
                
            slot = data[0]
            status = slot.get("status", "")
            bound_mid = slot.get("bound_machine_id")

            # 2. Status-based validation
            if status == "revoked":
                logger.warning("Access Denied: This license key has been revoked.")
                # Enforce kill-switch: clear any local offline tokens
                settings = QSettings(APP_AUTHOR, APP_NAME)
                settings.remove("auth/grace_token")
                settings.remove("auth/last_verified")
                return False

            elif status == "waiting":
                # First-time activation — bind this machine
                logger.info("License is unclaimed. Binding to this machine...")
                now_iso = datetime.now(timezone.utc).isoformat()
                patch_response = client.patch(
                    url,
                    headers=headers,
                    params={"id": f"eq.{slot['id']}"},
                    json={
                        "status": "active",
                        "bound_machine_id": current_mid,
                        "redeemed_at": now_iso
                    }
                )
                if patch_response.status_code in (200, 204):
                    logger.info("License successfully activated and bound to this machine.")
                    save_offline_token(license_key)
                    return True
                else:
                    logger.error(f"Failed to bind license: {patch_response.text}")
                    return False

            elif status == "active":
                if bound_mid == current_mid:
                    # Already bound to this machine — refresh offline token
                    logger.info("License verified (already bound to this machine).")
                    save_offline_token(license_key)
                    return True
                else:
                    # Bound to a different machine
                    logger.warning("Access Denied: License is bound to a different machine.")
                    return False

            else:
                logger.error(f"Unknown license status: '{status}'")
                return False
                
    except httpx.RequestError as e:
        logger.error(f"Network error during license check: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in verify_license: {e}", exc_info=True)
        return False
