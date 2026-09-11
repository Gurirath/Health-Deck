"""Central configuration and environment validation for Health Deck.

Provides typed access to configuration parameters and validates production
invariants (database connectivity, secret entropy, CORS origins, and paths)
at application startup to prevent misconfigured deployments.
"""

import os
from typing import List, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load any local .env file if present
load_dotenv()

# Environment identifiers
ENV_DEVELOPMENT = "development"
ENV_PRODUCTION = "production"
ENV_TEST = "test"


def get_environment() -> str:
    """Return the normalized runtime environment string."""
    env = os.environ.get("HEALTHDECK_ENV", os.environ.get("ENVIRONMENT", ENV_DEVELOPMENT))
    cleaned = env.strip().lower()
    if cleaned in ("production", "prod"):
        return ENV_PRODUCTION
    if cleaned in ("test", "testing"):
        return ENV_TEST
    return ENV_DEVELOPMENT


def is_production() -> bool:
    """Return True if operating in production mode."""
    return get_environment() == ENV_PRODUCTION


def is_development() -> bool:
    """Return True if operating in development mode."""
    return get_environment() == ENV_DEVELOPMENT


def is_test() -> bool:
    """Return True if operating in test mode."""
    return get_environment() == ENV_TEST


def get_database_url() -> Optional[str]:
    """Return cleaned DATABASE_URL or None."""
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url and url.strip() else None


def get_jwt_secret() -> str:
    """Return configured JWT secret or raise ValueError if missing."""
    secret = os.environ.get("HEALTHDECK_JWT_SECRET")
    if not secret or not secret.strip():
        raise ValueError(
            "HEALTHDECK_JWT_SECRET is not configured in environment variables. "
            "Configure HEALTHDECK_JWT_SECRET before starting or using authentication."
        )
    return secret.strip()


def get_jwt_expiration_hours() -> int:
    """Return JWT expiration duration in hours."""
    val = os.environ.get("HEALTHDECK_JWT_EXPIRATION_HOURS", "12")
    try:
        return max(1, int(val))
    except ValueError:
        return 12


def get_public_base_url() -> str:
    """Return the public base URL of the Health Deck deployment."""
    url = os.environ.get("HEALTHDECK_PUBLIC_BASE_URL", os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000"))
    return url.strip().rstrip("/")


def get_allowed_origins() -> List[str]:
    """Return list of allowed CORS origins.
    
    In development, if unset, defaults to ['*'].
    In production, must be explicitly configured and non-wildcard.
    """
    raw = os.environ.get("HEALTHDECK_ALLOWED_ORIGINS", os.environ.get("ALLOWED_ORIGINS", ""))
    if raw and raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    if is_production():
        return []
    return ["*"]


def get_uploads_dir() -> str:
    """Return directory path for temporary and session uploads."""
    return os.environ.get("HEALTHDECK_UPLOADS_DIR", "uploads").strip()


def get_reports_dir() -> str:
    """Return directory path for generated patient PDF reports."""
    return os.environ.get("HEALTHDECK_REPORTS_DIR", "reports").strip()


def is_rate_limiting_enabled() -> bool:
    """Return True if rate limiting is active."""
    val = os.environ.get("HEALTHDECK_RATE_LIMIT_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def is_behind_proxy() -> bool:
    """Return True if the application is operating behind a trusted reverse proxy."""
    val = os.environ.get("HEALTHDECK_BEHIND_PROXY")
    if val is not None:
        return val.strip().lower() in ("true", "1", "yes", "on")
    # In production, PaaS deployments (Render/Fly/Railway) are behind a reverse proxy by default
    return is_production()


def get_trusted_proxy_count() -> int:
    """Return the number of trusted reverse proxies in front of the application."""
    val = os.environ.get("HEALTHDECK_TRUSTED_PROXY_COUNT", "1")
    try:
        return max(1, int(val.strip()))
    except ValueError:
        return 1


def validate_production_config() -> List[str]:
    """Validate all mandatory requirements when HEALTHDECK_ENV=production.
    
    Returns a list of error strings (empty if valid).
    Never logs or exposes secret values.
    """
    if not is_production():
        return []

    errors: List[str] = []

    # 1. Database URL check
    db_url = get_database_url()
    if not db_url:
        errors.append(
            "DATABASE_URL is missing. Production mode strictly requires a PostgreSQL database connection string."
        )
    elif not (db_url.startswith("postgresql://") or db_url.startswith("postgres://")):
        errors.append(
            "DATABASE_URL is invalid. Production requires a PostgreSQL URL starting with postgresql:// or postgres://."
        )

    # 2. JWT Secret check (existence and entropy)
    try:
        secret = get_jwt_secret()
        if len(secret) < 32:
            errors.append(
                f"HEALTHDECK_JWT_SECRET is too short ({len(secret)} chars). Production requires at least 32 characters of high-entropy secret."
            )
        # Check against trivial or placeholder secrets
        lowered = secret.lower()
        if any(p in lowered for p in ("replace", "secret", "password", "123456", "example")):
            errors.append(
                "HEALTHDECK_JWT_SECRET contains insecure placeholder or obvious patterns. Generate a secure cryptographic secret (e.g. openssl rand -hex 32)."
            )
    except ValueError as e:
        errors.append(str(e))

    # 3. Public Base URL check
    public_url = get_public_base_url()
    if not public_url:
        errors.append("HEALTHDECK_PUBLIC_BASE_URL (or PUBLIC_BASE_URL) must be set in production.")
    else:
        parsed = urlparse(public_url)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"HEALTHDECK_PUBLIC_BASE_URL '{public_url}' is not a valid absolute URL.")
        elif parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            errors.append(
                f"HEALTHDECK_PUBLIC_BASE_URL is set to local host '{parsed.hostname}'. Production requires a public domain or routable IP."
            )

    # 4. CORS Allowed Origins check
    origins = get_allowed_origins()
    if not origins:
        errors.append(
            "HEALTHDECK_ALLOWED_ORIGINS (or ALLOWED_ORIGINS) must be explicitly configured in production with comma-separated domains."
        )
    else:
        if "*" in origins:
            errors.append(
                "Wildcard origin ('*') is strictly prohibited in production CORS configuration."
            )
        for origin in origins:
            if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
                errors.append(f"CORS origin '{origin}' must include scheme (http:// or https://).")

    return errors


def ensure_production_ready():
    """Raise RuntimeError if operating in production with invalid configuration."""
    if is_production():
        errors = validate_production_config()
        if errors:
            formatted = "\n  - ".join(errors)
            raise RuntimeError(
                f"FATAL: Production configuration validation failed with {len(errors)} error(s):\n  - {formatted}\n"
                "Please configure mandatory environment variables before starting Health Deck in production."
            )
