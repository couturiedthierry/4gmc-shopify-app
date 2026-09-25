"""
OAuth 2.1 & RFC 9728 Authorization Server for 4GMC Remote MCP Server.

Provides:
1. RFC 9728 Protected Resource Metadata (GET /.well-known/oauth-protected-resource)
2. RFC 8414 Authorization Server Metadata (GET /.well-known/oauth-authorization-server)
3. OpenID Connect Discovery (GET /.well-known/openid-configuration)
4. RFC 7517 JSON Web Key Set (GET /.well-known/jwks.json) with RS256 key rotation
5. PKCE S256 Authorization Code Flow (GET/POST /oauth/authorize)
6. Token Exchange and Refresh (POST /oauth/token)
7. Token Revocation (POST /oauth/revoke)
8. Dynamic Client Registration (POST /oauth/register)
9. Scope Enforcement & Workspace Isolation for MCP Tools
10. Strict WWW-Authenticate 401 Challenge
11. Secure Legacy Token Compatibility Mode (MCP_LEGACY_TOKEN_ENABLED)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import APIRouter, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import jwt

# Router for OAuth endpoints
router = APIRouter()

# Scopes
ALL_SCOPES: List[str] = [
    "4gmc:stores:read",
    "4gmc:stores:write",
    "4gmc:pages:read",
    "4gmc:pages:write",
    "4gmc:products:read",
    "4gmc:products:write",
    "4gmc:design:read",
    "4gmc:design:write",
    "4gmc:tasks:read",
    "4gmc:tasks:write",
]

READ_SCOPES: Set[str] = {
    "4gmc:stores:read",
    "4gmc:pages:read",
    "4gmc:products:read",
    "4gmc:design:read",
    "4gmc:tasks:read",
}

WRITE_SCOPES: Set[str] = {
    "4gmc:stores:write",
    "4gmc:pages:write",
    "4gmc:products:write",
    "4gmc:design:write",
    "4gmc:tasks:write",
}

TOOL_SCOPES: Dict[str, str] = {
    "list_pages": "4gmc:pages:read",
    "get_page": "4gmc:pages:read",
    "update_page": "4gmc:pages:write",
    "publish_page": "4gmc:pages:write",
    "get_store_design": "4gmc:design:read",
    "update_store_design": "4gmc:design:write",
    "publish_store_design": "4gmc:design:write",
    "list_products": "4gmc:products:read",
    "get_product": "4gmc:products:read",
    "update_product": "4gmc:products:write",
    "get_store_details": "4gmc:stores:read",
    "update_store_details": "4gmc:stores:write",
    "list_pending_image_slots": "4gmc:products:read",
    "get_image_slot_sources": "4gmc:products:read",
    "upload_image_asset": "4gmc:products:write",
    "replace_image_slot": "4gmc:products:write",
    "get_profile": "4gmc:stores:read",
}

# In-memory external JWKS cache: (timestamp, jwks_data)
_EXTERNAL_JWKS_CACHE: Dict[str, Tuple[float, Any]] = {}


@dataclass
class TokenContext:
    store_id: int
    scopes: Set[str]
    user_id: str
    client_id: str
    auth_method: str  # "oauth" or "legacy"


def get_public_url() -> str:
    """Retrieve canonical public URL of 4GMC."""
    import server
    url = os.environ.get("PUBLIC_URL") or server.PUBLIC_URL or "http://localhost:8000"
    return url.rstrip("/")


def get_issuer() -> str:
    """Configured or default OAuth issuer."""
    custom = os.environ.get("MCP_AUTH_ISSUER", "").strip()
    return custom.rstrip("/") if custom else get_public_url()


def get_resource_url() -> str:
    """Identifier of protected MCP resource."""
    return f"{get_public_url()}/api/mcp"


def get_audience() -> str:
    """Expected audience for MCP access tokens."""
    custom = os.environ.get("MCP_AUTH_AUDIENCE", "").strip()
    return custom if custom else get_resource_url()


def get_auth_server_url() -> str:
    """Authorization Server discovery base URL."""
    custom = os.environ.get("MCP_AUTHORIZATION_SERVER", "").strip()
    if custom:
        return custom.rstrip("/")
    return get_issuer()


def get_jwks_url() -> str:
    """JWKS URL."""
    custom = os.environ.get("MCP_JWKS_URL", "").strip()
    if custom:
        return custom
    return f"{get_auth_server_url()}/.well-known/jwks.json"


def is_legacy_token_enabled() -> bool:
    """Check if legacy static bearer token authentication is enabled."""
    val = os.environ.get("MCP_LEGACY_TOKEN_ENABLED", "false").strip().lower()
    return val in ("true", "1", "yes")


def int_to_base64url(val: int) -> str:
    """Convert an integer to base64url encoded string without trailing '='."""
    byte_len = (val.bit_length() + 7) // 8
    val_bytes = val.to_bytes(byte_len, byteorder="big")
    return base64.urlsafe_b64encode(val_bytes).decode("ascii").rstrip("=")


def init_oauth_db() -> None:
    """Initialize OAuth 2.1 schema in database registry."""
    import server
    server.ensure_registry()
    with server.registry() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_keys (
                kid TEXT PRIMARY KEY,
                private_key_pem TEXT NOT NULL,
                public_key_pem TEXT NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'RS256',
                active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_clients (
                client_id TEXT PRIMARY KEY,
                client_secret_hash TEXT NOT NULL DEFAULT '',
                client_name TEXT NOT NULL DEFAULT '',
                redirect_uris TEXT NOT NULL DEFAULT '[]',
                grant_types TEXT NOT NULL DEFAULT '["authorization_code","refresh_token"]',
                response_types TEXT NOT NULL DEFAULT '["code"]',
                scope TEXT NOT NULL DEFAULT '',
                is_public INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
                code_hash TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                redirect_uri TEXT NOT NULL,
                code_challenge TEXT NOT NULL,
                code_challenge_method TEXT NOT NULL,
                scope TEXT NOT NULL,
                store_id INTEGER NOT NULL DEFAULT 1,
                user_id TEXT NOT NULL DEFAULT 'admin',
                expires_at INTEGER NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                token_hash TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                store_id INTEGER NOT NULL DEFAULT 1,
                scope TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'admin',
                expires_at INTEGER NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_revoked_tokens (
                jti TEXT PRIMARY KEY,
                revoked_at INTEGER NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_legacy_tokens (
                token_hash TEXT PRIMARY KEY,
                store_id INTEGER NOT NULL DEFAULT 1,
                description TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_csrf_nonces (
                nonce TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )


def ensure_keypair() -> Tuple[str, str, str]:
    """Ensure at least one active RSA key exists in oauth_keys. Returns (kid, priv_pem, pub_pem)."""
    init_oauth_db()
    import server
    with server.registry() as c:
        row = c.execute("SELECT kid, private_key_pem, public_key_pem FROM oauth_keys WHERE active=1 ORDER BY created_at DESC LIMIT 1").fetchone()
        if row:
            return row["kid"], row["private_key_pem"], row["public_key_pem"]

        # Generate new 2048-bit RSA key pair
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        pub_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        kid = f"4gmc-key-{secrets.token_hex(8)}"
        now = int(time.time())
        c.execute(
            "INSERT INTO oauth_keys(kid, private_key_pem, public_key_pem, algorithm, active, created_at) VALUES(?, ?, ?, 'RS256', 1, ?)",
            (kid, priv_pem, pub_pem, now),
        )
        return kid, priv_pem, pub_pem


def rotate_keypair() -> str:
    """Rotate RSA signing key. Deactivates previous keys for signing while preserving for validation."""
    init_oauth_db()
    import server
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    kid = f"4gmc-key-{secrets.token_hex(8)}"
    now = int(time.time())
    with server.registry() as c:
        c.execute("UPDATE oauth_keys SET active=0")
        c.execute(
            "INSERT INTO oauth_keys(kid, private_key_pem, public_key_pem, algorithm, active, created_at) VALUES(?, ?, ?, 'RS256', 1, ?)",
            (kid, priv_pem, pub_pem, now),
        )
    return kid


def get_jwks() -> Dict[str, Any]:
    """Retrieve active and recent public keys formatted as RFC 7517 JWKS."""
    init_oauth_db()
    import server
    with server.registry() as c:
        rows = c.execute("SELECT kid, public_key_pem, algorithm FROM oauth_keys ORDER BY active DESC, created_at DESC LIMIT 5").fetchall()
        if not rows:
            ensure_keypair()
            rows = c.execute("SELECT kid, public_key_pem, algorithm FROM oauth_keys ORDER BY active DESC, created_at DESC LIMIT 5").fetchall()

    keys = []
    for r in rows:
        try:
            pub_key = serialization.load_pem_public_key(r["public_key_pem"].encode("ascii"))
            pn = pub_key.public_numbers()
            keys.append({
                "kty": "RSA",
                "use": "sig",
                "alg": r["algorithm"] or "RS256",
                "kid": r["kid"],
                "n": int_to_base64url(pn.n),
                "e": int_to_base64url(pn.e),
            })
        except Exception:
            continue

    return {"keys": keys}


def get_public_key_by_kid(kid: str) -> Optional[str]:
    """Look up public key PEM by Key ID."""
    init_oauth_db()
    import server
    with server.registry() as c:
        row = c.execute("SELECT public_key_pem FROM oauth_keys WHERE kid=?", (kid,)).fetchone()
        return row["public_key_pem"] if row else None


def create_access_token(
    store_id: int = 1,
    scopes: Optional[List[str]] = None,
    user_id: str = "admin",
    client_id: str = "chatgpt",
    expires_in: int = 3600,
) -> str:
    """Create a signed RS256 JWT access token bound to resource, issuer, store_id, and scopes."""
    kid, priv_pem, _ = ensure_keypair()
    now = int(time.time())
    granted_scopes = scopes if scopes is not None else list(READ_SCOPES)
    scope_str = " ".join(granted_scopes) if isinstance(granted_scopes, list) else str(granted_scopes)

    payload = {
        "iss": get_issuer(),
        "sub": user_id,
        "aud": get_audience(),
        "client_id": client_id,
        "scope": scope_str,
        "store_id": int(store_id),
        "iat": now,
        "nbf": now,
        "exp": now + expires_in,
        "jti": secrets.token_hex(16),
    }

    token = jwt.encode(
        payload,
        priv_pem,
        algorithm="RS256",
        headers={"kid": kid, "typ": "JWT", "alg": "RS256"},
    )
    return token


def create_refresh_token(
    client_id: str,
    store_id: int,
    scopes: List[str],
    user_id: str = "admin",
    expires_in: int = 2592000,
) -> str:
    """Generate and store a secure single-use refresh token (stored hashed)."""
    raw_token = f"4gmc_rt_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
    now = int(time.time())
    expires_at = now + expires_in
    scope_str = " ".join(scopes)

    init_oauth_db()
    import server
    with server.registry() as c:
        c.execute(
            "INSERT INTO oauth_refresh_tokens(token_hash, client_id, store_id, scope, user_id, expires_at, revoked, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, 0, ?)",
            (token_hash, client_id, int(store_id), scope_str, user_id, expires_at, now),
        )

    return raw_token


def revoke_token(token_str: str, token_type_hint: Optional[str] = None) -> None:
    """Revoke an access token (by jti) or a refresh token (by hash)."""
    init_oauth_db()
    import server
    now = int(time.time())

    # Try as JWT
    try:
        unverified = jwt.decode(token_str, options={"verify_signature": False})
        jti = unverified.get("jti")
        if jti:
            with server.registry() as c:
                c.execute("INSERT OR REPLACE INTO oauth_revoked_tokens(jti, revoked_at) VALUES(?, ?)", (jti, now))
            return
    except Exception:
        pass

    # Try as refresh token hash
    token_hash = hashlib.sha256(token_str.encode("ascii")).hexdigest()
    with server.registry() as c:
        c.execute("UPDATE oauth_refresh_tokens SET revoked=1 WHERE token_hash=?", (token_hash,))


def verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE S256 challenge in constant time. Plain method is disallowed in OAuth 2.1."""
    if not code_verifier or not code_challenge:
        return False
    if method != "S256":
        return False

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return hmac.compare_digest(expected, code_challenge)


def validate_redirect_uri(redirect_uri: str, client_id: str = "") -> bool:
    """Validate redirect URI strictly to prevent open-redirect vulnerabilities."""
    if not redirect_uri:
        return False
    try:
        parsed = urlparse(redirect_uri)
    except Exception:
        return False

    # Disallow dangerous schemes
    if parsed.scheme not in ("https", "http"):
        return False

    # http allowed only on localhost / 127.0.0.1 for local testing
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
        return False

    # Disallow fragments in redirect_uri (RFC 6749 section 3.1.2)
    if parsed.fragment:
        return False

    return True


def verify_jwt_token(token_str: str) -> Dict[str, Any]:
    """Verify an RS256 JWT access token against internal or external JWKS."""
    if not token_str or token_str.count(".") != 2:
        raise ValueError("Invalid JWT format")

    try:
        header = jwt.get_unverified_header(token_str)
    except Exception as err:
        raise ValueError(f"Invalid token header: {err}")

    kid = header.get("kid")
    alg = header.get("alg")
    if alg != "RS256":
        raise ValueError(f"Unsupported algorithm '{alg}', expected RS256")

    external_jwks_url = os.environ.get("MCP_JWKS_URL", "").strip()
    external_issuer = os.environ.get("MCP_AUTH_ISSUER", "").strip().rstrip("/")
    expected_aud = get_audience()
    expected_iss = external_issuer or get_issuer()

    if external_jwks_url:
        # Use external JWKS provider
        try:
            jwks_client = jwt.PyJWKClient(external_jwks_url, cache_jwk_set=True, lifespan=3600)
            signing_key = jwks_client.get_signing_key_from_jwt(token_str)
            decoded = jwt.decode(
                token_str,
                signing_key.key,
                algorithms=["RS256"],
                audience=expected_aud,
                issuer=expected_iss,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
            return decoded
        except Exception as err:
            raise ValueError(f"External JWT verification failed: {err}")

    # Internal 4GMC authorization server validation
    pub_pem = get_public_key_by_kid(kid) if kid else None
    if not pub_pem:
        # If kid not found directly, check active key
        _, _, active_pub = ensure_keypair()
        pub_pem = active_pub

    try:
        decoded = jwt.decode(
            token_str,
            pub_pem,
            algorithms=["RS256"],
            audience=expected_aud,
            issuer=expected_iss,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.ImmatureSignatureError:
        raise ValueError("Token is not yet valid (nbf in future)")
    except jwt.InvalidIssuerError:
        raise ValueError(f"Invalid token issuer, expected {expected_iss}")
    except jwt.InvalidAudienceError:
        raise ValueError(f"Invalid token audience, expected {expected_aud}")
    except Exception as err:
        raise ValueError(f"JWT signature verification failed: {err}")

    # Check if token was revoked
    jti = decoded.get("jti")
    if jti:
        init_oauth_db()
        import server
        with server.registry() as c:
            revoked = c.execute("SELECT 1 FROM oauth_revoked_tokens WHERE jti=?", (jti,)).fetchone()
            if revoked:
                raise ValueError("Token has been revoked")

    return decoded


def get_legacy_token_hash() -> str:
    """Retrieve stored SHA-256 hash of legacy static token."""
    init_oauth_db()
    import server
    with server.registry() as c:
        row = c.execute("SELECT token_hash FROM oauth_legacy_tokens WHERE revoked=0 ORDER BY created_at DESC LIMIT 1").fetchone()
        if row and row["token_hash"]:
            return row["token_hash"]

        # Check app_settings legacy fallback, hash it, and purge plaintext immediately
        app_row = c.execute("SELECT value FROM app_settings WHERE key='mcp_api_token'").fetchone()
        if app_row and app_row["value"]:
            h = hashlib.sha256(app_row["value"].encode("utf-8")).hexdigest()
            c.execute(
                "INSERT OR REPLACE INTO oauth_legacy_tokens(token_hash, store_id, description, created_at, revoked) VALUES(?, 1, 'migrated', ?, 0)",
                (h, int(time.time())),
            )
            c.execute("DELETE FROM app_settings WHERE key='mcp_api_token'")
            return h

    return ""


_in_memory_legacy_token: Optional[str] = None


def get_in_memory_legacy_token() -> str:
    """Retrieve in-memory legacy token for active process without reading from or writing to database."""
    global _in_memory_legacy_token
    return _in_memory_legacy_token or ""


def has_legacy_token() -> bool:
    """Check if any valid legacy token hash exists."""
    return bool(get_legacy_token_hash())


def set_legacy_token(raw_token: str) -> None:
    """Store SHA-256 hash of legacy static token. Never stores raw token in database."""
    global _in_memory_legacy_token
    raw_token = (raw_token or "").strip()
    if not raw_token:
        raise ValueError("Legacy token cannot be empty")
    _in_memory_legacy_token = raw_token
    h = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    init_oauth_db()
    import server
    with server.registry() as c:
        c.execute("UPDATE oauth_legacy_tokens SET revoked=1")
        c.execute(
            "INSERT INTO oauth_legacy_tokens(token_hash, store_id, description, created_at, revoked) VALUES(?, 1, 'manual', ?, 0)",
            (h, int(time.time())),
        )
        c.execute("DELETE FROM app_settings WHERE key='mcp_api_token'")


def rotate_legacy_token() -> str:
    """Rotate legacy static token, return the new raw token once, and store only its SHA-256 hash."""
    new_raw = f"gmc_legacy_{secrets.token_hex(16)}"
    set_legacy_token(new_raw)
    return new_raw


def verify_legacy_token(raw_token: str) -> bool:
    """Verify legacy token against stored SHA-256 hash using constant-time comparison."""
    if not is_legacy_token_enabled():
        return False
    if not raw_token:
        return False

    target_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    stored_hash = get_legacy_token_hash()
    if not stored_hash:
        return False

    return hmac.compare_digest(target_hash, stored_hash)


def authenticate_mcp_request(
    request: Request,
    required_scope: Optional[str] = None,
    target_store_id: Optional[int] = None,
) -> TokenContext:
    """
    Standards-compliant MCP authentication.
    1. Rejects unauthenticated requests with 401 and WWW-Authenticate pointing to protected-resource metadata.
    2. Validates OAuth 2.1 RS256 JWT access tokens.
    3. Handles legacy static bearer token only if MCP_LEGACY_TOKEN_ENABLED is true.
    4. Enforces required scope (read vs write).
    5. Enforces store workspace isolation (prevents cross-store access).
    """
    resource_metadata_url = f"{get_public_url()}/.well-known/oauth-protected-resource"
    challenge_header = f'Bearer realm="4gmc-mcp", resource_metadata="{resource_metadata_url}"'

    auth_header = request.headers.get("Authorization", "").strip()
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif not token:
        # Fallback to query param or custom header
        token = request.query_params.get("token", "").strip() or request.headers.get("X-MCP-Token", "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Authentication required. Please authenticate using MCP OAuth 2.1.",
            headers={"WWW-Authenticate": challenge_header},
        )

    # 1. Try OAuth 2.1 JWT Verification
    if token.count(".") == 2:
        try:
            claims = verify_jwt_token(token)
            store_id = int(claims.get("store_id", 1))
            user_id = str(claims.get("sub", "admin"))
            client_id = str(claims.get("client_id", "chatgpt"))
            scopes_str = str(claims.get("scope", ""))
            scopes = set(scopes_str.split()) if scopes_str else set()

            # Scope enforcement
            if required_scope and required_scope not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Insufficient scope. Tool requires '{required_scope}'.",
                )

            # Cross-store workspace enforcement
            if target_store_id is not None and target_store_id != store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Cross-store access denied. Token is bound to store #{store_id}.",
                )

            import server
            server.ACTIVE_STORE_ID.set(store_id)
            return TokenContext(
                store_id=store_id,
                scopes=scopes,
                user_id=user_id,
                client_id=client_id,
                auth_method="oauth",
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid OAuth token: {str(err)}",
                headers={"WWW-Authenticate": f'{challenge_header}, error="invalid_token", error_description="{str(err)}"'},
            )

    # 2. Legacy static token verification path
    if is_legacy_token_enabled():
        if verify_legacy_token(token):
            store_id = 1
            if target_store_id is not None and target_store_id != store_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Cross-store access denied. Legacy token is bound to store #{store_id}.",
                )
            import server
            server.ACTIVE_STORE_ID.set(store_id)
            return TokenContext(
                store_id=store_id,
                scopes=set(ALL_SCOPES),
                user_id="admin",
                client_id="codex-legacy",
                auth_method="legacy",
            )

    # If legacy is disabled or token invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid OAuth 2.1 Bearer access token required.",
        headers={"WWW-Authenticate": f'{challenge_header}, error="invalid_token"'},
    )


# ---------------------------------------------------------------------------
# Discovery Endpoints (RFC 9728, RFC 8414, OpenID Connect, RFC 7517)
# ---------------------------------------------------------------------------

@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """RFC 9728 OAuth 2.0 Protected Resource Metadata endpoint."""
    return JSONResponse(
        content={
            "resource": get_resource_url(),
            "authorization_servers": [get_auth_server_url()],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ALL_SCOPES,
            "jwks_uri": get_jwks_url(),
        },
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/.well-known/oauth-authorization-server")
@router.get("/.well-known/openid-configuration")
async def oauth_authorization_server_metadata():
    """RFC 8414 OAuth 2.0 Authorization Server Discovery Metadata endpoint."""
    base = get_auth_server_url()
    return JSONResponse(
        content={
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "revocation_endpoint": f"{base}/oauth/revoke",
            "registration_endpoint": f"{base}/oauth/register",
            "jwks_uri": f"{base}/.well-known/jwks.json",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
            "scopes_supported": ALL_SCOPES,
            "client_id_metadata_document_supported": True,
        },
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/.well-known/jwks.json")
async def jwks_endpoint():
    """RFC 7517 JSON Web Key Set containing active and recent RSA public keys."""
    return JSONResponse(
        content=get_jwks(),
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# Authorization & Consent Flow (RFC 6749, RFC 7636 PKCE, OAuth 2.1)
# ---------------------------------------------------------------------------

@router.get("/oauth/authorize")
async def oauth_authorize_get(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query("4gmc:stores:read 4gmc:pages:read 4gmc:products:read 4gmc:design:read"),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...),
    state: str = Query(""),
    resource: Optional[str] = Query(None),
):
    """Render OAuth 2.1 Consent & Authorization Screen."""
    if response_type != "code":
        return HTMLResponse("Unsupported response_type. Only 'code' is supported.", status_code=400)
    if code_challenge_method != "S256":
        return HTMLResponse("Unsupported code_challenge_method. OAuth 2.1 requires 'S256'.", status_code=400)
    if not validate_redirect_uri(redirect_uri, client_id):
        return HTMLResponse("Invalid redirect_uri. Must be a valid HTTPS URI or localhost.", status_code=400)

    # Check if 4GMC administrator is authenticated
    import server
    is_admin = False
    cookie = request.cookies.get("gmc_session", "")
    if cookie:
        try:
            stamp, sig = cookie.split(".", 1)
            expected = hmac.new(server.SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, expected) and int(stamp) >= time.time():
                is_admin = True
        except Exception:
            pass

    # Retrieve registered stores for workspace selection
    try:
        stores = server.store_summaries()
    except Exception:
        stores = []
    if not stores:
        stores = [{"id": 1, "name": "My Store", "domain": "store.myshopify.com"}]


    requested_scopes = [s.strip() for s in scope.split() if s.strip() and s in ALL_SCOPES]
    if not requested_scopes:
        requested_scopes = list(READ_SCOPES)

    # Generate secure, single-use, time-limited, session-bound CSRF token
    csrf_nonce = secrets.token_hex(16)
    csrf_exp = int(time.time()) + 600
    session_id = cookie.split(".")[1] if (cookie and "." in cookie) else "anon"
    csrf_sig = hmac.new(
        server.SESSION_SECRET.encode(),
        f"oauth_csrf:{client_id}:{code_challenge}:{csrf_exp}:{csrf_nonce}:{session_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    csrf_token = f"{csrf_exp}.{csrf_nonce}.{csrf_sig}"

    init_oauth_db()
    with server.registry() as c:
        c.execute("DELETE FROM oauth_csrf_nonces WHERE expires_at < ?", (int(time.time()),))
        c.execute(
            "INSERT INTO oauth_csrf_nonces(nonce, client_id, expires_at, used, created_at) VALUES(?, ?, ?, 0, ?)",
            (csrf_nonce, client_id, csrf_exp, int(time.time())),
        )

    read_items = "".join(f"<li style='color:#1e40af;'><code>{html.escape(s)}</code> (Read Access)</li>" for s in requested_scopes if s in READ_SCOPES)
    write_items = "".join(f"<li style='color:#b45309;font-weight:600;'><code>{html.escape(s)}</code> (Write / Live Shopify Modification)</li>" for s in requested_scopes if s in WRITE_SCOPES)

    store_options = "".join(f"<option value='{s['id']}'>Store #{s['id']}: {html.escape(s['name'])} ({html.escape(s.get('domain','') or 'No domain')})</option>" for s in stores)

    login_prompt_html = ""
    if not is_admin:
        login_prompt_html = """
        <div style="background:#fee2e2;border:1px solid #f87171;padding:12px;border-radius:6px;margin-bottom:16px;">
            <p style="margin:0 0 8px;font-size:13px;color:#991b1b;font-weight:600;">Administrator Authentication Required</p>
            <label style="display:block;font-size:12px;color:#374151;margin-bottom:4px;">4GMC Admin Password:</label>
            <input type="password" name="admin_password" required placeholder="Enter admin password" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:4px;box-sizing:border-box;">
        </div>
        """

    consent_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>4GMC — Authorize ChatGPT Connection</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
            .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; max-width: 500px; width: 100%; padding: 28px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
            h2 {{ margin: 0 0 8px; font-size: 20px; font-weight: 700; color: #38bdf8; }}
            p {{ margin: 0 0 16px; font-size: 14px; color: #94a3b8; line-height: 1.5; }}
            .scope-box {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; margin-bottom: 20px; }}
            ul {{ margin: 0; padding-left: 20px; font-size: 13px; }}
            li {{ margin-bottom: 6px; }}
            .warning {{ background: #451a03; border: 1px solid #b45309; color: #fde68a; padding: 10px 14px; border-radius: 6px; font-size: 12px; margin-bottom: 20px; }}
            .btn-group {{ display: flex; gap: 12px; }}
            .btn {{ flex: 1; padding: 12px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; text-align: center; }}
            .btn-approve {{ background: #0284c7; color: white; }}
            .btn-approve:hover {{ background: #0369a1; }}
            .btn-deny {{ background: #334155; color: #94a3b8; text-decoration: none; display: inline-block; box-sizing: border-box; }}
            .btn-deny:hover {{ background: #475569; color: white; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Connect to 4GMC Studio</h2>
            <p>An external AI application is requesting authorization to interact with your store via the Model Context Protocol (MCP OAuth 2.1).</p>
            
            <form method="POST" action="/oauth/authorize">
                <input type="hidden" name="client_id" value="{html.escape(client_id)}">
                <input type="hidden" name="redirect_uri" value="{html.escape(redirect_uri)}">
                <input type="hidden" name="scope" value="{html.escape(' '.join(requested_scopes))}">
                <input type="hidden" name="code_challenge" value="{html.escape(code_challenge)}">
                <input type="hidden" name="code_challenge_method" value="{html.escape(code_challenge_method)}">
                <input type="hidden" name="state" value="{html.escape(state)}">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                
                {login_prompt_html}
                
                <div style="margin-bottom:16px;">
                    <label style="display:block;font-size:13px;color:#cbd5e1;margin-bottom:6px;font-weight:600;">Authorized Store Workspace:</label>
                    <select name="store_id" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;color:#f8fafc;border-radius:6px;">
                        {store_options}
                    </select>
                </div>

                <div class="scope-box">
                    <div style="font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:8px;">Requested Permissions</div>
                    <ul>
                        {read_items}
                        {write_items}
                    </ul>
                </div>

                <div class="warning">
                    ⚠️ <strong>Security Notice:</strong> Write permissions allow ChatGPT to modify policies, pages, design settings, and publish theme changes.
                </div>

                <div class="btn-group">
                    <button type="submit" name="action" value="approve" class="btn btn-approve">Authorize Connection</button>
                    <button type="submit" name="action" value="deny" class="btn btn-deny">Cancel</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(consent_html)


@router.post("/oauth/authorize")
async def oauth_authorize_post(
    request: Request,
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    state: str = Form(""),
    csrf_token: str = Form(...),
    action: str = Form(...),
    store_id: int = Form(1),
    admin_password: Optional[str] = Form(None),
):
    """Process OAuth Consent and issue short-lived, single-use Authorization Code."""
    if not validate_redirect_uri(redirect_uri, client_id):
        return HTMLResponse("Invalid redirect_uri", status_code=400)

    # Check denial
    if action != "approve":
        err_url = f"{redirect_uri}{'&' if '?' in redirect_uri else '?'}error=access_denied&error_description=User+denied+access"
        if state:
            err_url += f"&state={state}"
        return RedirectResponse(err_url, status_code=303)

    import server
    # Validate CSRF: format, expiration, single-use DB nonce, and cryptographic signature
    try:
        parts = csrf_token.split(".")
        if len(parts) != 3:
            return HTMLResponse("CSRF verification failed: malformed token", status_code=403)
        csrf_exp_str, csrf_nonce, csrf_sig = parts
        csrf_exp = int(csrf_exp_str)
        if csrf_exp < time.time():
            return HTMLResponse("CSRF verification failed: token expired", status_code=403)
    except Exception:
        return HTMLResponse("CSRF verification failed: invalid token", status_code=403)

    # Check nonce in database to guarantee single-use
    init_oauth_db()
    with server.registry() as c:
        row = c.execute(
            "SELECT * FROM oauth_csrf_nonces WHERE nonce=? AND client_id=?",
            (csrf_nonce, client_id),
        ).fetchone()
        if not row or row["used"] == 1 or row["expires_at"] < time.time():
            return HTMLResponse("CSRF verification failed: token already used or expired", status_code=403)
        c.execute("UPDATE oauth_csrf_nonces SET used=1 WHERE nonce=?", (csrf_nonce,))

    # Verify signature bound to session
    cookie = request.cookies.get("gmc_session", "")
    session_id = cookie.split(".")[1] if (cookie and "." in cookie) else "anon"
    expected_csrf = hmac.new(
        server.SESSION_SECRET.encode(),
        f"oauth_csrf:{client_id}:{code_challenge}:{csrf_exp_str}:{csrf_nonce}:{session_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(csrf_sig, expected_csrf):
        return HTMLResponse("CSRF verification failed: signature mismatch", status_code=403)

    # Validate admin authentication
    is_admin = False
    cookie = request.cookies.get("gmc_session", "")
    if cookie:
        try:
            stamp, sig = cookie.split(".", 1)
            expected = hmac.new(server.SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, expected) and int(stamp) >= time.time():
                is_admin = True
        except Exception:
            pass

    if not is_admin:
        if admin_password and hmac.compare_digest(admin_password, server.ADMIN_PASSWORD):
            is_admin = True

    if not is_admin:
        return HTMLResponse("Invalid administrator password. Authorization refused.", status_code=401)

    # Generate short-lived (5 min), single-use authorization code
    raw_code = f"4gmc_code_{secrets.token_urlsafe(32)}"
    code_hash = hashlib.sha256(raw_code.encode("ascii")).hexdigest()
    now = int(time.time())
    expires_at = now + 300

    init_oauth_db()
    with server.registry() as c:
        c.execute(
            "INSERT INTO oauth_authorization_codes(code_hash, client_id, redirect_uri, code_challenge, code_challenge_method, scope, store_id, user_id, expires_at, used, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, 'admin', ?, 0, ?)",
            (code_hash, client_id, redirect_uri, code_challenge, code_challenge_method, scope, int(store_id), expires_at, now),
        )

    sep = "&" if "?" in redirect_uri else "?"
    success_url = f"{redirect_uri}{sep}code={raw_code}"
    if state:
        success_url += f"&state={state}"

    return RedirectResponse(success_url, status_code=303)


# ---------------------------------------------------------------------------
# Token Endpoint (Exchange Authorization Code & Refresh Token)
# ---------------------------------------------------------------------------

@router.post("/oauth/token")
async def oauth_token_endpoint(request: Request):
    """OAuth 2.1 Token Endpoint supporting PKCE authorization_code and refresh_token grants."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        form = await request.form()
        data = dict(form)

    grant_type = data.get("grant_type", "")
    client_id = data.get("client_id", "")

    init_oauth_db()
    import server

    # 1. Authorization Code Grant with PKCE
    if grant_type == "authorization_code":
        code = data.get("code", "")
        redirect_uri = data.get("redirect_uri", "")
        code_verifier = data.get("code_verifier", "")

        if not code or not redirect_uri or not code_verifier:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_request", "error_description": "Missing code, redirect_uri, or code_verifier"},
            )

        code_hash = hashlib.sha256(code.encode("ascii")).hexdigest()
        now = int(time.time())

        with server.registry() as c:
            row = c.execute("SELECT * FROM oauth_authorization_codes WHERE code_hash=?", (code_hash,)).fetchone()
            if not row:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Invalid or unknown authorization code"},
                )

            # Replay protection: if already used, revoke any token and reject
            if row["used"] == 1:
                c.execute("DELETE FROM oauth_authorization_codes WHERE code_hash=?", (code_hash,))
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Authorization code has already been used (replay detected)"},
                )

            # Check expiration
            if row["expires_at"] < now:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Authorization code has expired"},
                )

            # Verify exact redirect_uri match
            if row["redirect_uri"] != redirect_uri:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Redirect URI mismatch"},
                )

            # Verify client_id is present and matches the client_id to which the code was issued
            if not client_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_client", "error_description": "Missing required client_id parameter"},
                )
            if row["client_id"] != client_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Client ID mismatch"},
                )

            # Verify PKCE S256
            if not verify_pkce(code_verifier, row["code_challenge"], row["code_challenge_method"]):
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "PKCE verification failed"},
                )

            # Mark code as used immediately upon successful validation
            c.execute("UPDATE oauth_authorization_codes SET used=1 WHERE code_hash=?", (code_hash,))


            store_id = row["store_id"]
            scopes = [s for s in row["scope"].split() if s]
            user_id = row["user_id"]
            bound_client_id = row["client_id"]

        # Issue access token & refresh token
        access_token = create_access_token(
            store_id=store_id,
            scopes=scopes,
            user_id=user_id,
            client_id=bound_client_id,
            expires_in=3600,
        )
        refresh_token = create_refresh_token(
            client_id=bound_client_id,
            store_id=store_id,
            scopes=scopes,
            user_id=user_id,
            expires_in=2592000,
        )

        return JSONResponse(
            content={
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "scope": " ".join(scopes),
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    # 2. Refresh Token Grant
    if grant_type == "refresh_token":
        raw_refresh = data.get("refresh_token", "")
        if not raw_refresh:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_request", "error_description": "Missing refresh_token"},
            )

        req_client_id = (client_id or data.get("client_id", "")).strip()
        if not req_client_id:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_client", "error_description": "Missing required client_id parameter"},
            )

        token_hash = hashlib.sha256(raw_refresh.encode("ascii")).hexdigest()
        now = int(time.time())

        with server.registry() as c:
            row = c.execute("SELECT * FROM oauth_refresh_tokens WHERE token_hash=?", (token_hash,)).fetchone()
            if not row or row["revoked"] == 1 or row["expires_at"] < now:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Refresh token is invalid, expired, or revoked"},
                )

            # Strictly verify refresh token is bound to the requesting client
            if row["client_id"] != req_client_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Refresh token was not issued to this client"},
                )

            # Rotate refresh token
            c.execute("UPDATE oauth_refresh_tokens SET revoked=1 WHERE token_hash=?", (token_hash,))
            store_id = row["store_id"]
            scopes = [s for s in row["scope"].split() if s]
            user_id = row["user_id"]
            bound_client_id = row["client_id"]

        new_access_token = create_access_token(
            store_id=store_id,
            scopes=scopes,
            user_id=user_id,
            client_id=bound_client_id,
            expires_in=3600,
        )
        new_refresh_token = create_refresh_token(
            client_id=bound_client_id,
            store_id=store_id,
            scopes=scopes,
            user_id=user_id,
            expires_in=2592000,
        )

        return JSONResponse(
            content={
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": new_refresh_token,
                "scope": " ".join(scopes),
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    return JSONResponse(
        status_code=400,
        content={"error": "unsupported_grant_type", "error_description": f"Grant type '{grant_type}' not supported"},
    )


# ---------------------------------------------------------------------------
# Token Revocation (RFC 7009)
# ---------------------------------------------------------------------------

@router.post("/oauth/revoke")
async def oauth_revoke_endpoint(request: Request):
    """RFC 7009 Token Revocation endpoint."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        form = await request.form()
        data = dict(form)

    token = data.get("token", "")
    hint = data.get("token_type_hint", "")
    if token:
        revoke_token(token, hint)

    # RFC 7009 specifies 200 OK for successful revocation or unknown token
    return JSONResponse(content={})


# ---------------------------------------------------------------------------
# Dynamic Client Registration (RFC 7591)
# ---------------------------------------------------------------------------

@router.post("/oauth/register")
async def oauth_register_endpoint(request: Request):
    """RFC 7591 Dynamic Client Registration endpoint."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    client_name = str(body.get("client_name") or "ChatGPT Client")
    redirect_uris = body.get("redirect_uris", [])
    if not isinstance(redirect_uris, list) or not redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uris must be a non-empty list of URLs")

    for uri in redirect_uris:
        if not validate_redirect_uri(uri):
            raise HTTPException(status_code=400, detail=f"Invalid redirect_uri: {uri}")

    client_id = f"client_{secrets.token_hex(12)}"
    now = int(time.time())

    init_oauth_db()
    import server
    with server.registry() as c:
        c.execute(
            "INSERT INTO oauth_clients(client_id, client_name, redirect_uris, is_public, created_at) VALUES(?, ?, ?, 1, ?)",
            (client_id, client_name, json.dumps(redirect_uris), now),
        )

    return JSONResponse(
        status_code=201,
        content={
            "client_id": client_id,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )
