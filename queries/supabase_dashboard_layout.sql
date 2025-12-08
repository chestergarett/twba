-- Create table to store dashboard layouts
CREATE TABLE IF NOT EXISTS public.dashboard_layouts (
  id bigserial PRIMARY KEY,
  dashboard_name text NOT NULL UNIQUE,
  layout jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_dashboard_layouts_name ON public.dashboard_layouts(dashboard_name);

-- Add RLS policies if needed (optional)
-- ALTER TABLE public.dashboard_layouts ENABLE ROW LEVEL SECURITY;

