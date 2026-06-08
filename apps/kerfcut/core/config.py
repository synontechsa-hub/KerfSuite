"""
KerfCut — Build Configuration
Constants in this file are baked into the executable by Nuitka.
"""
import os

# Supabase credentials are loaded from environment variables at runtime.
# Keep empty defaults here to avoid shipping secrets in source or binaries.
SUPABASE_URL = os.getenv("PROJECT_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
