-- Migration 002: Performance & Query Optimization Indexes

CREATE INDEX IF NOT EXISTS idx_cases_status_created ON cases (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_reviewed_by ON cases (reviewed_by_doctor_id);
CREATE INDEX IF NOT EXISTS idx_cases_prescribed_by ON cases (prescribed_by_doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctors_lower_user ON doctors (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_doctors_lower_email ON doctors (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_raw_vitals_received ON raw_vitals (received_at DESC);
