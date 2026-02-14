-- Database schema for Proof of Life Authentication System

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL,
    status TEXT NOT NULL,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verification results table
CREATE TABLE IF NOT EXISTS verification_results (
    result_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    liveness_score REAL NOT NULL,
    deepfake_score REAL NOT NULL,
    emotion_score REAL NOT NULL,
    final_score REAL NOT NULL,
    passed BOOLEAN NOT NULL,
    timestamp REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Tokens table
CREATE TABLE IF NOT EXISTS tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Nonces table (for replay attack prevention)
CREATE TABLE IF NOT EXISTS nonces (
    nonce TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp REAL NOT NULL,
    details TEXT,  -- JSON string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_nonces_expires ON nonces(expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_time ON audit_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON tokens(expires_at);
