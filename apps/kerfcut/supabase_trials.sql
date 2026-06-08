-- KerfCut — Trial Tracking Table
-- Run this in the Supabase SQL Editor AFTER the main schema has been applied.
-- https://supabase.com/dashboard/project/_/sql

-- 1. Create the trials table
CREATE TABLE IF NOT EXISTS public.trials (
    machine_id TEXT PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT now(),
    runs_count INTEGER DEFAULT 0
);

-- 2. Enable Row Level Security (RLS)
ALTER TABLE public.trials ENABLE ROW LEVEL SECURITY;

-- 3. Allow the app to check if a trial record exists for a machine
CREATE POLICY "Allow anon read trials" ON public.trials
    FOR SELECT USING (true);

-- 4. Allow the app to create a new trial record on first launch
CREATE POLICY "Allow anon insert trials" ON public.trials
    FOR INSERT WITH CHECK (true);


-- 6. Atomic increment RPC to prevent multi-instance race conditions
CREATE OR REPLACE FUNCTION public.increment_trial_run(p_machine_id TEXT)
RETURNS TABLE (runs_count INTEGER, days_left INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_runs_count INTEGER;
    v_started_at TIMESTAMPTZ;
BEGIN
    UPDATE public.trials
    SET runs_count = trials.runs_count + 1
    WHERE trials.machine_id = p_machine_id
    RETURNING trials.runs_count, trials.started_at
    INTO v_runs_count, v_started_at;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'trial record not found for machine_id %', p_machine_id;
    END IF;

    runs_count := v_runs_count;
    days_left := GREATEST(0, 14 - FLOOR(EXTRACT(EPOCH FROM (now() - v_started_at)) / 86400)::INTEGER);
    RETURN NEXT;
END;
$$;

-- 7. Allow anon role to execute the increment RPC
GRANT EXECUTE ON FUNCTION public.increment_trial_run(TEXT) TO anon;

-- 8. Index for fast lookups (machine_id is already PK, but explicit for clarity)
CREATE INDEX IF NOT EXISTS idx_trials_machine_id ON public.trials(machine_id);
