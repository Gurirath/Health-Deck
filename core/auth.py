"""Authentication and authorization utilities for Health Deck.

Provides secure password hashing (bcrypt), JWT token issuance and validation (pyjwt),
and FastAPI dependency get_current_doctor() for role-based clinician endpoint protection.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core import db

JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRATION_HOURS = 12

_bearer_scheme = HTTPBearer(auto_error=False)


def get_jwt_secret() -> str:
    """Retrieve the JWT secret from environment variables.

    Fails explicitly if HEALTHDECK_JWT_SECRET is not configured.
    No automatic or fallback secret is permitted.
    """
    secret = os.environ.get("HEALTHDECK_JWT_SECRET")
    if not secret or not secret.strip():
        raise RuntimeError(
            "HEALTHDECK_JWT_SECRET is not configured in environment variables. "
            "Configure HEALTHDECK_JWT_SECRET before starting or using authentication."
        )
    return secret.strip()


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with a cryptographic salt."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt salt-hashed password."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with expiration."""
    secret = get_jwt_secret()
    to_encode = data.copy()

    try:
        hours = int(os.environ.get("HEALTHDECK_JWT_EXPIRATION_HOURS", DEFAULT_EXPIRATION_HOURS))
    except (ValueError, TypeError):
        hours = DEFAULT_EXPIRATION_HOURS

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=hours))
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, secret, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_doctor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """FastAPI dependency: Authenticate doctor from Bearer token.

    Verifies token, confirms doctor exists in database and is active.
    Returns safe doctor profile dictionary (without password hash).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    doctor_id = payload.get("sub")
    if not doctor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        doc_id_int = int(doctor_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid doctor identity in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    doctor = db.get_doctor_by_id(doc_id_int, include_password_hash=False)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not doctor.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return doctor


if __name__ == "__main__":
    import argparse
    import getpass
    from dotenv import load_dotenv

    load_dotenv()
    db.init_db()

    parser = argparse.ArgumentParser(description="Health Deck Doctor Account Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create-doctor", help="Create or update a doctor account")
    create_parser.add_argument("--username", required=True, help="Doctor login username")
    create_parser.add_argument("--email", help="Doctor login email (defaults to username@hospital.internal)")
    create_parser.add_argument("--password", help="Doctor password (prompted interactively if omitted)")
    create_parser.add_argument("--name", help="Full name, e.g. Dr. Sarah Chen, MD")
    create_parser.add_argument("--license", default="MD-GENERAL", help="Medical license number")
    create_parser.add_argument("--department", default="General Physician", help="Assigned medical department")
    create_parser.add_argument("--role", default="doctor", help="User role (doctor, admin)")

    reset_parser = subparsers.add_parser("reset-password", help="Reset password for an existing doctor")
    reset_parser.add_argument("--username", required=True, help="Doctor login username or email")
    reset_parser.add_argument("--password", help="New doctor password (prompted interactively if omitted)")

    list_parser = subparsers.add_parser("list-doctors", help="List existing local doctor accounts")

    args = parser.parse_args()

    if args.command == "create-doctor":
        clean_user = args.username.strip().lower()
        clean_email = (args.email or f"{clean_user}@hospital.internal").strip().lower()
        full_name = (args.name or f"Dr. {clean_user.capitalize()}").strip()

        password = args.password
        if not password:
            password = getpass.getpass(f"Enter password for {clean_user}: ")
            if not password:
                print("Error: Password cannot be empty.")
                exit(1)

        pw_hash = hash_password(password)
        doc_id, was_created = db.create_or_update_doctor(
            username=clean_user,
            email=clean_email,
            password_hash=pw_hash,
            full_name=full_name,
            medical_license=args.license,
            department=args.department,
            role=args.role,
        )
        action_verb = "created" if was_created else "updated"
        print(f"Doctor account {action_verb} successfully: ID={doc_id}, Username={clean_user}, Department={args.department}")

    elif args.command == "reset-password":
        clean_ident = args.username.strip().lower()
        password = args.password
        if not password:
            password = getpass.getpass(f"Enter new password for {clean_ident}: ")
            if not password:
                print("Error: Password cannot be empty.")
                exit(1)

        pw_hash = hash_password(password)
        success = db.update_doctor_password(clean_ident, pw_hash)
        if success:
            print(f"Password reset successfully for doctor: {clean_ident}")
        else:
            print(f"Error: Doctor '{clean_ident}' not found.")
            exit(1)

    elif args.command == "list-doctors":
        doctors = db.list_doctors(include_password_hash=False)
        if not doctors:
            print("No doctor accounts found in database.")
        else:
            print(f"{'ID':<4} {'Username':<15} {'Department':<24} {'Full Name':<25} {'Active'}")
            print("-" * 75)
            for d in doctors:
                print(f"{d['id']:<4} {d['username']:<15} {d['department']:<24} {d['full_name']:<25} {'Yes' if d['is_active'] else 'No'}")

    else:
        parser.print_help()
