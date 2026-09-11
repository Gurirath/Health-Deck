-- Migration 001: Initial Core Schema
-- Defines schema_migrations, doctors, session_uploads, cases, and raw_vitals

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    medical_license VARCHAR(100) NOT NULL DEFAULT '',
    department VARCHAR(100) NOT NULL DEFAULT 'General Physician',
    role VARCHAR(50) NOT NULL DEFAULT 'doctor',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS session_uploads (
    session_id VARCHAR(100) PRIMARY KEY,
    image_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    vitals JSONB NOT NULL DEFAULT '{}'::jsonb,
    chief_complaint TEXT NOT NULL,
    symptom_location VARCHAR(100) NOT NULL,
    transcript JSONB NOT NULL DEFAULT '[]'::jsonb,
    extracted JSONB NOT NULL DEFAULT '{}'::jsonb,
    red_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    diagnosis JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_llm_response JSONB NOT NULL DEFAULT '{}'::jsonb,
    solution_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    image_analysis JSONB,
    session_id VARCHAR(100) REFERENCES session_uploads(session_id) ON DELETE SET NULL,
    photo_path TEXT,
    confidence INTEGER NOT NULL DEFAULT 0,
    department VARCHAR(100) NOT NULL,
    department_override VARCHAR(100),
    escalate BOOLEAN NOT NULL DEFAULT FALSE,
    escalation_reason TEXT NOT NULL DEFAULT '',
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    doctor_name VARCHAR(200),
    prescription_medicines JSONB NOT NULL DEFAULT '[]'::jsonb,
    doctor_notes TEXT,
    prescribed_at TIMESTAMPTZ,
    report_pdf_path TEXT,
    reviewed_by_doctor_id BIGINT REFERENCES doctors(id) ON DELETE SET NULL,
    reviewed_by_doctor_name VARCHAR(200),
    prescribed_by_doctor_id BIGINT REFERENCES doctors(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS raw_vitals (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(100),
    spo2 DOUBLE PRECISION,
    temp_c DOUBLE PRECISION,
    hr DOUBLE PRECISION,
    systolic_bp DOUBLE PRECISION,
    diastolic_bp DOUBLE PRECISION,
    timestamp TIMESTAMPTZ
);
