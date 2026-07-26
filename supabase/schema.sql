-- ============================================================
-- Card Benefit Activation Engine – Supabase Schema
-- Run this in the Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- Profiles (extends Supabase Auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  email TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, email)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    NEW.email
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- Cards
-- ============================================================
CREATE TABLE IF NOT EXISTS cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  card_name TEXT NOT NULL,
  card_type TEXT NOT NULL,
  last_four TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cards_user_id ON cards(user_id);

-- ============================================================
-- Transactions
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  card_id UUID REFERENCES cards(id),
  merchant_raw TEXT NOT NULL,
  merchant_normalized TEXT,
  amount DECIMAL(12,2) NOT NULL,
  currency TEXT DEFAULT 'INR',
  transaction_date TIMESTAMPTZ NOT NULL,
  mcc TEXT,
  category TEXT,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_card_id ON transactions(card_id);

-- ============================================================
-- Detected Benefits
-- ============================================================
CREATE TABLE IF NOT EXISTS detected_benefits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES profiles(id),
  benefit_type TEXT NOT NULL,
  confidence_score DECIMAL(3,2),
  status TEXT DEFAULT 'detected',
  explanation TEXT,
  policy_reference TEXT,
  coverage_window_days INT,
  max_coverage_amount DECIMAL(12,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_detected_benefits_user_id ON detected_benefits(user_id);
CREATE INDEX IF NOT EXISTS idx_detected_benefits_status ON detected_benefits(status);

-- ============================================================
-- Claims
-- ============================================================
CREATE TABLE IF NOT EXISTS claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detected_benefit_id UUID REFERENCES detected_benefits(id),
  user_id UUID REFERENCES profiles(id),
  status TEXT DEFAULT 'draft',
  prefilled_data JSONB,
  missing_documents TEXT[],
  customer_notes TEXT,
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_user_id ON claims(user_id);
CREATE INDEX IF NOT EXISTS idx_claims_detected_benefit_id ON claims(detected_benefit_id);

-- ============================================================
-- Documents (Receipts etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
  file_url TEXT NOT NULL,
  file_name TEXT,
  document_type TEXT DEFAULT 'receipt',
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_claim_id ON documents(claim_id);

-- ============================================================
-- Row Level Security
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE detected_benefits ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

-- Cards policies
CREATE POLICY "Users can view own cards" ON cards
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own cards" ON cards
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Transactions policies
CREATE POLICY "Users can view own transactions" ON transactions
  FOR SELECT USING (auth.uid() = user_id);

-- Detected benefits policies
CREATE POLICY "Users can view own benefits" ON detected_benefits
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own benefits" ON detected_benefits
  FOR UPDATE USING (auth.uid() = user_id);

-- Claims policies
CREATE POLICY "Users can view own claims" ON claims
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own claims" ON claims
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own claims" ON claims
  FOR UPDATE USING (auth.uid() = user_id);

-- Documents policies
CREATE POLICY "Users can view own documents" ON documents
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM claims c WHERE c.id = documents.claim_id AND c.user_id = auth.uid()
    )
  );
CREATE POLICY "Users can insert own documents" ON documents
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM claims c WHERE c.id = documents.claim_id AND c.user_id = auth.uid()
    )
  );

-- ============================================================
-- Storage bucket for receipts (run in SQL or via Dashboard)
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public) VALUES ('receipts', 'receipts', false);
--
-- CREATE POLICY "Users can upload receipts" ON storage.objects
--   FOR INSERT WITH CHECK (bucket_id = 'receipts' AND auth.uid()::text = (storage.foldername(name))[1]);
-- CREATE POLICY "Users can view own receipts" ON storage.objects
--   FOR SELECT USING (bucket_id = 'receipts' AND auth.uid()::text = (storage.foldername(name))[1]);

-- ============================================================
-- Confidence breakdown + agent audit (architecture: Sync & Audit)
-- ============================================================
ALTER TABLE detected_benefits
  ADD COLUMN IF NOT EXISTS confidence_breakdown JSONB;

CREATE TABLE IF NOT EXISTS agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  transaction_id UUID,
  merchant_raw TEXT,
  pipeline_status TEXT,
  eligible BOOLEAN,
  benefit_type TEXT,
  confidence_score DECIMAL(3,2),
  category TEXT,
  merchant_normalized TEXT,
  mode TEXT,
  llm_meta JSONB,
  rules_decision JSONB,
  confidence_breakdown JSONB,
  explanation TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);

-- Agent runs: backend service_role writes; users can read own rows
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can view own agent runs" ON agent_runs;
CREATE POLICY "Users can view own agent runs" ON agent_runs
  FOR SELECT USING (auth.uid() = user_id);

-- ============================================================
-- Service role bypass note:
-- Backend uses service_role key for seed + agent writes.
-- Frontend uses anon key + user JWT for RLS-protected reads.
-- ============================================================
