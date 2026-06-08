-- KerfSuite Database Schema

-- 1. Create the Workspaces table
CREATE TABLE IF NOT EXISTS public.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Create the Users extension table (links auth.users to workspaces)
-- Supabase handles auth.users, so we just map their ID here
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES public.workspaces(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member', -- 'admin', 'member'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Create the License Slots table (The core CDKey tracker)
CREATE TABLE IF NOT EXISTS public.license_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    app TEXT NOT NULL DEFAULT 'kerfcut', -- 'kerfcut', 'kerfstock'
    cdkey TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'active', 'revoked'
    bound_machine_id TEXT, -- Populated when a machine redeems the key
    redeemed_at TIMESTAMPTZ,
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Set up Row Level Security (RLS) policies
-- Enable RLS on all tables
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.license_slots ENABLE ROW LEVEL SECURITY;

-- 5. Policies
-- Users can only see their own workspace
CREATE POLICY "Users view own workspace" 
ON public.workspaces FOR SELECT 
USING (id IN (SELECT workspace_id FROM public.users WHERE users.id = auth.uid()));

-- Users can only see profiles in their workspace
CREATE POLICY "Users view workspace peers" 
ON public.users FOR SELECT 
USING (workspace_id IN (SELECT workspace_id FROM public.users WHERE users.id = auth.uid()));

-- Users can view and manage license slots in their workspace
CREATE POLICY "Users manage workspace licenses" 
ON public.license_slots FOR ALL 
USING (workspace_id IN (SELECT workspace_id FROM public.users WHERE users.id = auth.uid()));

-- 6. Helper Trigger: Auto-create User Profile on Auth Signup
-- This trigger automatically creates a row in public.users when you sign up in Supabase
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
DECLARE
    default_workspace_id UUID;
BEGIN
    -- For V1, we just create a default workspace for the new admin if none exists
    -- In a real SaaS, this would be handled by a proper onboarding flow
    INSERT INTO public.workspaces (name) VALUES ('My Workshop') RETURNING id INTO default_workspace_id;
    
    INSERT INTO public.users (id, workspace_id, email, role)
    VALUES (new.id, default_workspace_id, new.email, 'admin');
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop trigger if exists to prevent duplicates on re-run
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
