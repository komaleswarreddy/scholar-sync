-- ScholarSync Database Schema (Supabase)
-- Run this SQL script in Supabase SQL Editor to set up tables for this repo.
--
-- Notes:
-- - This is intended for development and quick-start onboarding.
-- - It preserves the original manual schema, but includes additional columns/tables
--   required by the current Python models so the API can run without missing-column errors.
-- - If you use Alembic migrations instead, you can skip this file and run:
--     alembic upgrade head
--   If you run THIS SQL first, you can mark migrations as applied via:
--     alembic stamp head

-- Needed for gen_random_uuid() on Supabase/Postgres
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subdomain TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table (role management; separate from Clerk user directory)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  clerk_user_id TEXT,
  role TEXT DEFAULT 'user' NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id);

-- Create sources table
CREATE TABLE IF NOT EXISTS sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  s3_key TEXT NOT NULL,
  type TEXT DEFAULT 'pdf' NOT NULL,
  status TEXT DEFAULT 'processing' NOT NULL,
  chunks_count INTEGER DEFAULT 0 NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create chats table
CREATE TABLE IF NOT EXISTS chats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations JSONB DEFAULT '[]',
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create notes table
CREATE TABLE IF NOT EXISTS notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  source_ref_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ
);

-- Guardrails: users blocked by safety filters / injection detection
CREATE TABLE IF NOT EXISTS guardrail_user_blocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  user_name TEXT,
  session_id UUID,
  block_count INTEGER DEFAULT 0 NOT NULL,
  block_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alerts: cost/token/security alert sessions
CREATE TABLE IF NOT EXISTS alert_user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  session_id UUID,
  alert_type TEXT NOT NULL,
  alert_message TEXT,
  severity TEXT DEFAULT 'medium' NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sources_tenant_id ON sources(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sources_user_id ON sources(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_tenant_id ON chats(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_notes_tenant_id ON notes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_user_blocks_tenant_id ON guardrail_user_blocks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_user_blocks_user_id ON guardrail_user_blocks(user_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_user_blocks_session_id ON guardrail_user_blocks(session_id);
CREATE INDEX IF NOT EXISTS idx_guardrail_user_blocks_created_at ON guardrail_user_blocks(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_user_sessions_tenant_id ON alert_user_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_alert_user_sessions_user_id ON alert_user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_user_sessions_session_id ON alert_user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_alert_user_sessions_alert_type ON alert_user_sessions(alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_user_sessions_created_at ON alert_user_sessions(created_at);

-- Insert a test tenant for development
INSERT INTO tenants (subdomain, name)
VALUES ('default', 'Default School')
ON CONFLICT (subdomain) DO NOTHING;

