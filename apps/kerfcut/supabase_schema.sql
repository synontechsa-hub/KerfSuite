-- KerfCut Supabase Schema
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard/project/_/sql)

-- 1. Create the licenses table
CREATE TABLE IF NOT EXISTS public.licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    user_email TEXT,
    machine_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 2. Enable Row Level Security (RLS)
ALTER TABLE public.licenses ENABLE ROW LEVEL SECURITY;

-- 3. Allow anonymous read access to active licenses (so the client can verify)
-- This allows anyone with the ANON_KEY to check if a specific key exists and is active.
CREATE POLICY "Allow anon read for verification" ON public.licenses
    FOR SELECT
    USING (is_active = true);

-- 4. Allow anon update for machine binding
CREATE POLICY "Allow anon bind machine" ON public.licenses
    FOR UPDATE USING (machine_id IS NULL OR machine_id = '')
    WITH CHECK (machine_id IS NOT NULL AND machine_id != '');

-- 5. Create an index on the key column for fast lookups
CREATE INDEX IF NOT EXISTS idx_licenses_key ON public.licenses(key);
