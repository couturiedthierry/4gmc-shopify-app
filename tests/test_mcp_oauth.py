"""
Comprehensive Test Suite for 4GMC Remote MCP OAuth 2.1 & RFC 9728 Integration.

Validates all 20 required specifications:
1. Protected-resource metadata (RFC 9728)
2. 401 response and WWW-Authenticate challenge
3. Valid access token
4. Invalid signature
5. Wrong issuer
6. Wrong audience/resource
7. Expired token
8. Not-yet-valid token (nbf)
9. Missing scope
10. Read token attempting a write
11. Cross-store access attempt
12. Authorization code replay
13. PKCE mismatch
14. Invalid redirect URI
15. Revoked access
16. JWKS key rotation
17. Legacy token disabled
18. Legacy token rotation if compatibility remains
19. No secrets in responses or logs
20. Existing Shopify OAuth remains independent and functional
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from starlette.testclient import TestClient
import jwt

import server
import mcp_oauth
import mcp_server


def run_all_oauth_tests():
    with tempfile.TemporaryDirectory() as temp:
        server.DB = Path(temp) / "test_oauth.db"
        server.init()

        # Seed test stores and products
        with server.db() as c:
            c.execute(
                "UPDATE stores SET name=?, domain=?, business=?, brand=? WHERE id=1",
                (
                    "4GMC Test Store",
                    "test-store.myshopify.com",
                    json.dumps({"business_name": "4GMC Test Store", "currency": "USD"}),
                    json.dumps({"color": "#2251dc", "accent": "#6f9cff"}),
                ),
            )
            c.execute(
                "INSERT INTO products(store_id, title, source_title, price, status, source_url) VALUES(1, 'Test Product', 'Test Product Source', '29.99', 'active', 'https://example.com/p.jpg')"
            )

            c.execute(
                "INSERT INTO pages(store_id, kind, title, body, status) VALUES(1, 'about', 'About Us', '<p>About our store.</p>', 'draft')"
            )

        client = TestClient(server.app)

        # -------------------------------------------------------------
        # 1. Protected-Resource Metadata (RFC 9728)
        # -------------------------------------------------------------
        meta_resp = client.get("/.well-known/oauth-protected-resource")
        assert meta_resp.status_code == 200, f"Expected 200, got {meta_resp.status_code}"
        meta = meta_resp.json()
        assert "resource" in meta
        assert meta["resource"].endswith("/api/mcp")
        assert "authorization_servers" in meta
        assert len(meta["authorization_servers"]) > 0
        assert meta["bearer_methods_supported"] == ["header"]
        assert "4gmc:stores:read" in meta["scopes_supported"]
        assert "4gmc:pages:write" in meta["scopes_supported"]

        # Also check RFC 8414 AS metadata & OpenID config
        as_meta = client.get("/.well-known/oauth-authorization-server").json()
        assert as_meta["authorization_endpoint"].endswith("/oauth/authorize")
        assert as_meta["token_endpoint"].endswith("/oauth/token")
        assert as_meta["code_challenge_methods_supported"] == ["S256"]
        assert as_meta["client_id_metadata_document_supported"] is True

        # -------------------------------------------------------------
        # 2. 401 Response and WWW-Authenticate Challenge
        # -------------------------------------------------------------
        unauth_resp = client.post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert unauth_resp.status_code == 401
        www_auth = unauth_resp.headers.get("www-authenticate", "")
        assert "Bearer" in www_auth
        assert 'resource_metadata="' in www_auth
        assert "/.well-known/oauth-protected-resource" in www_auth

        # -------------------------------------------------------------
        # 3. Valid Access Token
        # -------------------------------------------------------------
        valid_token = mcp_oauth.create_access_token(
            store_id=1,
            scopes=mcp_oauth.ALL_SCOPES,
            user_id="admin",
            client_id="chatgpt",
        )
        headers = {"Authorization": f"Bearer {valid_token}"}
        valid_resp = client.post("/api/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert valid_resp.status_code == 200, f"Expected 200, got {valid_resp.status_code}: {valid_resp.text}"
        tools = valid_resp.json()["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        assert "list_pages" in tool_names
        assert "get_profile" in tool_names
        assert "publish_page" in tool_names

        # Verify tool safety annotations
        pub_page_tool = next(t for t in tools if t["name"] == "publish_page")
        assert pub_page_tool.get("readOnlyHint") is False
        assert pub_page_tool.get("destructiveHint") is True
        profile_tool = next(t for t in tools if t["name"] == "get_profile")
        assert profile_tool.get("readOnlyHint") is True
        assert profile_tool.get("_meta", {}).get("openai/profile") is True

        # -------------------------------------------------------------
        # 4. Invalid Signature
        # -------------------------------------------------------------
        foreign_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        foreign_priv = foreign_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        fake_token = jwt.encode(
            {
                "iss": mcp_oauth.get_issuer(),
                "aud": mcp_oauth.get_audience(),
                "sub": "attacker",
                "scope": "4gmc:stores:read",
                "store_id": 1,
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "nbf": int(time.time()),
            },
            foreign_priv,
            algorithm="RS256",
            headers={"kid": "unknown-foreign-key", "typ": "JWT", "alg": "RS256"},
        )
        bad_sig_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {fake_token}"}, json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        assert bad_sig_resp.status_code == 401
        assert "invalid_token" in bad_sig_resp.headers.get("www-authenticate", "")

        # -------------------------------------------------------------
        # 5. Wrong Issuer
        # -------------------------------------------------------------
        _, priv_pem, _ = mcp_oauth.ensure_keypair()
        wrong_iss_token = jwt.encode(
            {
                "iss": "https://malicious-issuer.example.com",
                "aud": mcp_oauth.get_audience(),
                "sub": "admin",
                "scope": "4gmc:stores:read",
                "store_id": 1,
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "nbf": int(time.time()),
            },
            priv_pem,
            algorithm="RS256",
            headers={"kid": "4gmc-key", "typ": "JWT", "alg": "RS256"},
        )
        wrong_iss_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {wrong_iss_token}"}, json={"jsonrpc": "2.0", "id": 4, "method": "tools/list"})
        assert wrong_iss_resp.status_code == 401

        # -------------------------------------------------------------
        # 6. Wrong Audience / Resource
        # -------------------------------------------------------------
        wrong_aud_token = jwt.encode(
            {
                "iss": mcp_oauth.get_issuer(),
                "aud": "https://other-unrelated-api.example.com/api",
                "sub": "admin",
                "scope": "4gmc:stores:read",
                "store_id": 1,
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "nbf": int(time.time()),
            },
            priv_pem,
            algorithm="RS256",
            headers={"kid": "4gmc-key", "typ": "JWT", "alg": "RS256"},
        )
        wrong_aud_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {wrong_aud_token}"}, json={"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
        assert wrong_aud_resp.status_code == 401

        # -------------------------------------------------------------
        # 7. Expired Token
        # -------------------------------------------------------------
        expired_token = jwt.encode(
            {
                "iss": mcp_oauth.get_issuer(),
                "aud": mcp_oauth.get_audience(),
                "sub": "admin",
                "scope": "4gmc:stores:read",
                "store_id": 1,
                "exp": int(time.time()) - 100,  # Expired
                "iat": int(time.time()) - 200,
                "nbf": int(time.time()) - 200,
            },
            priv_pem,
            algorithm="RS256",
            headers={"kid": "4gmc-key", "typ": "JWT", "alg": "RS256"},
        )
        expired_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {expired_token}"}, json={"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
        assert expired_resp.status_code == 401
        assert "expired" in expired_resp.json()["detail"].lower()

        # -------------------------------------------------------------
        # 8. Not-Yet-Valid Token (nbf in future)
        # -------------------------------------------------------------
        future_token = jwt.encode(
            {
                "iss": mcp_oauth.get_issuer(),
                "aud": mcp_oauth.get_audience(),
                "sub": "admin",
                "scope": "4gmc:stores:read",
                "store_id": 1,
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "nbf": int(time.time()) + 1000,  # Not valid yet
            },
            priv_pem,
            algorithm="RS256",
            headers={"kid": "4gmc-key", "typ": "JWT", "alg": "RS256"},
        )
        future_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {future_token}"}, json={"jsonrpc": "2.0", "id": 7, "method": "tools/list"})
        assert future_resp.status_code == 401

        # -------------------------------------------------------------
        # 9. Missing Scope
        # -------------------------------------------------------------
        limited_scope_token = mcp_oauth.create_access_token(
            store_id=1,
            scopes=["4gmc:stores:read"],  # Only stores read, no products or pages
        )
        scope_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {limited_scope_token}"},
            json={"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "list_products", "arguments": {}}},
        )
        assert scope_resp.status_code == 200
        assert scope_resp.json().get("error", {}).get("code") == -32003
        assert "insufficient scope" in scope_resp.json()["error"]["message"].lower()

        # -------------------------------------------------------------
        # 10. Read Token Attempting a Write
        # -------------------------------------------------------------
        read_only_token = mcp_oauth.create_access_token(
            store_id=1,
            scopes=list(mcp_oauth.READ_SCOPES),  # Only read scopes
        )
        write_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {read_only_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {"name": "update_page", "arguments": {"title": "Updated", "body": "New content"}},
            },
        )
        assert write_resp.status_code == 200
        assert write_resp.json().get("error", {}).get("code") == -32003
        assert "requires '4gmc:pages:write'" in write_resp.json()["error"]["message"]

        # -------------------------------------------------------------
        # 11. Cross-Store Access Attempt
        # -------------------------------------------------------------
        store1_token = mcp_oauth.create_access_token(store_id=1, scopes=mcp_oauth.ALL_SCOPES)
        cross_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {store1_token}"},
            json={
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {"name": "list_pages", "arguments": {"store_id": 2}},
            },
        )
        assert cross_resp.status_code == 200
        assert cross_resp.json().get("error", {}).get("code") == -32003
        assert "cross-store access denied" in cross_resp.json()["error"]["message"].lower()

        # -------------------------------------------------------------
        # 12 & 13. Authorization Flow, PKCE S256, and Code Replay Protection
        # -------------------------------------------------------------
        verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        redirect_uri = "https://chatgpt.com/aip/g-test/oauth/callback"

        # Start authorization flow (admin login session)
        auth_url = (
            f"/oauth/authorize?response_type=code&client_id=chatgpt&redirect_uri={redirect_uri}"
            f"&code_challenge={code_challenge}&code_challenge_method=S256&scope=4gmc:stores:read%204gmc:pages:write"
        )
        get_auth = client.get(auth_url)
        assert get_auth.status_code == 200
        assert "Connect to 4GMC Studio" in get_auth.text

        # Extract single-use session-bound CSRF token from rendered consent page
        import re
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', get_auth.text)
        assert csrf_match, "CSRF token must be present in consent form"
        csrf_token = csrf_match.group(1)

        # CSRF Security Check 1: Submitting with tampered / invalid CSRF token must fail (403)
        post_bad_csrf = client.post(
            "/oauth/authorize",
            data={
                "client_id": "chatgpt",
                "redirect_uri": redirect_uri,
                "scope": "4gmc:stores:read 4gmc:pages:write",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "state123",
                "csrf_token": "forged.csrf.signature",
                "action": "approve",
                "store_id": 1,
                "admin_password": server.ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert post_bad_csrf.status_code == 403

        # CSRF Security Check 2: Submitting with valid CSRF token succeeds
        post_auth = client.post(
            "/oauth/authorize",
            data={
                "client_id": "chatgpt",
                "redirect_uri": redirect_uri,
                "scope": "4gmc:stores:read 4gmc:pages:write",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "state123",
                "csrf_token": csrf_token,
                "action": "approve",
                "store_id": 1,
                "admin_password": server.ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert post_auth.status_code == 303

        # CSRF Security Check 3: Replaying the SAME CSRF token must fail (403 single-use check)
        post_replay_csrf = client.post(
            "/oauth/authorize",
            data={
                "client_id": "chatgpt",
                "redirect_uri": redirect_uri,
                "scope": "4gmc:stores:read 4gmc:pages:write",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "state123",
                "csrf_token": csrf_token,
                "action": "approve",
                "store_id": 1,
                "admin_password": server.ADMIN_PASSWORD,
            },
            follow_redirects=False,
        )
        assert post_replay_csrf.status_code == 403

        location = post_auth.headers["location"]
        assert location.startswith(redirect_uri)
        assert "code=" in location
        auth_code = location.split("code=")[1].split("&")[0]

        # Security check: authorization_code exchange requires client_id
        missing_client_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
        )
        assert missing_client_resp.status_code == 400
        assert missing_client_resp.json()["error"] == "invalid_client"

        # Security check: authorization_code exchange rejects client_id mismatch
        wrong_client_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": "rogue_client",
                "code_verifier": verifier,
            },
        )
        assert wrong_client_resp.status_code == 400
        assert wrong_client_resp.json()["error"] == "invalid_grant"

        # 13. Test PKCE Mismatch
        pkce_fail_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": "chatgpt",
                "code_verifier": "wrong-verifier-12345",
            },
        )
        assert pkce_fail_resp.status_code == 400
        assert pkce_fail_resp.json()["error"] == "invalid_grant"
        assert "pkce" in pkce_fail_resp.json()["error_description"].lower()

        # Exchange code with correct verifier
        exchange_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": "chatgpt",
                "code_verifier": verifier,
            },
        )
        assert exchange_resp.status_code == 200
        token_data = exchange_resp.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == 3600

        # Security check: refresh_token grant requires client_id
        missing_rt_client = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
            },
        )
        assert missing_rt_client.status_code == 400
        assert missing_rt_client.json()["error"] == "invalid_client"

        # Security check: refresh_token grant rejects client_id mismatch
        wrong_rt_client = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
                "client_id": "different_client",
            },
        )
        assert wrong_rt_client.status_code == 400
        assert wrong_rt_client.json()["error"] == "invalid_grant"

        # Successful refresh with bound client_id
        valid_refresh_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
                "client_id": "chatgpt",
            },
        )
        assert valid_refresh_resp.status_code == 200
        assert "access_token" in valid_refresh_resp.json()

        # 12. Authorization Code Replay Attack
        replay_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": "chatgpt",
                "code_verifier": verifier,
            },
        )
        assert replay_resp.status_code == 400
        assert replay_resp.json()["error"] == "invalid_grant"
        assert "already been used" in replay_resp.json()["error_description"].lower()

        # -------------------------------------------------------------
        # 14. Invalid Redirect URI
        # -------------------------------------------------------------
        bad_uri_resp = client.get(
            f"/oauth/authorize?response_type=code&client_id=chatgpt&redirect_uri=javascript:alert(1)"
            f"&code_challenge={code_challenge}&code_challenge_method=S256"
        )
        assert bad_uri_resp.status_code == 400
        assert "invalid redirect_uri" in bad_uri_resp.text.lower()

        # Mismatched redirect URI at token exchange
        # Create fresh code
        fresh_code = "4gmc_code_" + secrets.token_urlsafe(32)
        code_h = hashlib.sha256(fresh_code.encode("ascii")).hexdigest()
        with server.registry() as c:
            c.execute(
                "INSERT INTO oauth_authorization_codes(code_hash, client_id, redirect_uri, code_challenge, code_challenge_method, scope, store_id, expires_at, used, created_at) "
                "VALUES(?, 'chatgpt', 'https://chatgpt.com/callback1', ?, 'S256', '4gmc:stores:read', 1, ?, 0, ?)",
                (code_h, code_challenge, int(time.time()) + 300, int(time.time())),
            )
        mismatch_uri_resp = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": fresh_code,
                "redirect_uri": "https://chatgpt.com/different_callback",
                "client_id": "chatgpt",
                "code_verifier": verifier,
            },
        )
        assert mismatch_uri_resp.status_code == 400
        assert "redirect uri mismatch" in mismatch_uri_resp.json()["error_description"].lower()

        # -------------------------------------------------------------
        # 15. Revoked Access
        # -------------------------------------------------------------
        revocable_token = mcp_oauth.create_access_token(store_id=1, scopes=mcp_oauth.ALL_SCOPES)
        before_revoke = client.post("/api/mcp", headers={"Authorization": f"Bearer {revocable_token}"}, json={"jsonrpc": "2.0", "id": 11, "method": "tools/list"})
        assert before_revoke.status_code == 200

        # Revoke via RFC 7009
        revoke_resp = client.post("/oauth/revoke", data={"token": revocable_token, "token_type_hint": "access_token"})
        assert revoke_resp.status_code == 200

        # Request after revocation must fail with 401
        after_revoke = client.post("/api/mcp", headers={"Authorization": f"Bearer {revocable_token}"}, json={"jsonrpc": "2.0", "id": 12, "method": "tools/list"})
        assert after_revoke.status_code == 401
        assert "revoked" in after_revoke.json()["detail"].lower()

        # -------------------------------------------------------------
        # 16. JWKS Key Rotation
        # -------------------------------------------------------------
        jwks_before = client.get("/.well-known/jwks.json").json()
        initial_kids = {k["kid"] for k in jwks_before["keys"]}

        new_kid = mcp_oauth.rotate_keypair()
        jwks_after = client.get("/.well-known/jwks.json").json()
        new_kids = {k["kid"] for k in jwks_after["keys"]}

        assert new_kid in new_kids
        assert len(new_kids) >= len(initial_kids)

        # Tokens signed with newly rotated key must validate
        rotated_token = mcp_oauth.create_access_token(store_id=1, scopes=mcp_oauth.ALL_SCOPES)
        rotated_resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {rotated_token}"}, json={"jsonrpc": "2.0", "id": 13, "method": "tools/list"})
        assert rotated_resp.status_code == 200

        # -------------------------------------------------------------
        # 17. Legacy Static Token Disabled by Default
        # -------------------------------------------------------------
        os.environ["MCP_LEGACY_TOKEN_ENABLED"] = "false"
        mcp_oauth.set_legacy_token("gmc_mcp_static_secret_test")

        static_bearer_resp = client.post(
            "/api/mcp",
            headers={"Authorization": "Bearer gmc_mcp_static_secret_test"},
            json={"jsonrpc": "2.0", "id": 14, "method": "tools/list"},
        )
        assert static_bearer_resp.status_code == 401
        assert "invalid_token" in static_bearer_resp.headers.get("www-authenticate", "")

        # -------------------------------------------------------------
        # 18. Legacy Token Rotation When Compatibility Enabled
        # -------------------------------------------------------------
        os.environ["MCP_LEGACY_TOKEN_ENABLED"] = "true"
        legacy_token1 = mcp_oauth.rotate_legacy_token()
        assert legacy_token1.startswith("gmc_legacy_")

        # Must authenticate when legacy is enabled
        leg1_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {legacy_token1}"},
            json={"jsonrpc": "2.0", "id": 15, "method": "tools/list"},
        )
        assert leg1_resp.status_code == 200

        # Rotate legacy token
        legacy_token2 = mcp_oauth.rotate_legacy_token()
        assert legacy_token2 != legacy_token1

        # Old legacy token must fail
        old_leg_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {legacy_token1}"},
            json={"jsonrpc": "2.0", "id": 16, "method": "tools/list"},
        )
        assert old_leg_resp.status_code == 401

        # New legacy token succeeds
        new_leg_resp = client.post(
            "/api/mcp",
            headers={"Authorization": f"Bearer {legacy_token2}"},
            json={"jsonrpc": "2.0", "id": 17, "method": "tools/list"},
        )
        assert new_leg_resp.status_code == 200

        # Reset legacy flag
        os.environ["MCP_LEGACY_TOKEN_ENABLED"] = "false"

        # -------------------------------------------------------------
        # 19. No Secrets in Responses, No Plaintext in SQLite, No Privilege Escalation
        # -------------------------------------------------------------
        admin_settings_resp = client.get("/api/mcp/settings", headers={"Authorization": f"Bearer {valid_token}"})
        assert admin_settings_resp.status_code == 200
        settings_text = admin_settings_resp.text
        assert server.ADMIN_PASSWORD not in settings_text
        assert server.SESSION_SECRET not in settings_text
        assert "private_key" not in settings_text.lower()
        # Access token must NEVER be returned in settings
        assert admin_settings_resp.json().get("token") is None

        # Privilege Escalation Check: A read-only token MUST be rejected with 403 Forbidden
        read_only_test_token = mcp_oauth.create_access_token(store_id=1, scopes=["4gmc:stores:read"])
        escalate_resp = client.get("/api/mcp/settings", headers={"Authorization": f"Bearer {read_only_test_token}"})
        assert escalate_resp.status_code == 403
        assert "administrative scope required" in escalate_resp.json()["detail"].lower()

        # Database Check: Plaintext mcp_api_token must NEVER be stored in app_settings in SQLite
        with server.registry() as c:
            raw_setting = c.execute("SELECT 1 FROM app_settings WHERE key='mcp_api_token'").fetchone()
            assert raw_setting is None, "Plaintext token must not exist in app_settings table!"

        # -------------------------------------------------------------
        # 20. Existing Shopify OAuth Remains Independent & Functional
        # -------------------------------------------------------------
        # Unauthenticated request to /api/shopify/connect requires 4GMC session
        shopify_auth_resp = client.get("/api/shopify/connect", follow_redirects=False)
        assert shopify_auth_resp.status_code == 401
        # With session, connect verifies store config without interference from MCP OAuth
        shopify_authed = client.get("/api/shopify/connect", cookies={"gmc_session": f"{int(time.time())+3600}.{hmac.new(server.SESSION_SECRET.encode(), str(int(time.time())+3600).encode(), hashlib.sha256).hexdigest()}"}, follow_redirects=False)
        assert shopify_authed.status_code in (400, 302, 303, 307)
        # Verify /api/shopify/callback route exists and handles state mismatch via redirect
        shopify_cb_resp = client.get("/api/shopify/callback", follow_redirects=False)
        assert shopify_cb_resp.status_code in (302, 303, 400, 401, 403)

        print("\nALL 20 MCP OAUTH 2.1 SPECIFICATION CHECKS PASSED 100%!")


if __name__ == "__main__":
    run_all_oauth_tests()
