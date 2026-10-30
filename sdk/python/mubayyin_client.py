"""Small, dependency-free client for Mubayyin's tenant-scoped pilot API.

Run this client inside the customer's own environment. The customer's model
credentials and model execution remain outside Mubayyin; only the scenario
and the resulting model output are submitted to the tenant API.
"""
from __future__ import annotations
import json
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

class MubayyinAPIError(RuntimeError):
    """An HTTP/API failure. Never includes the request Authorization header."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Mubayyin API returned HTTP {status_code}: {detail}")

class MubayyinTransportError(RuntimeError):
    """A network/transport failure without request secrets or payloads."""

class _NoRedirect(HTTPRedirectHandler):
    """Bearer credentials must never be forwarded to a redirect target."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_NO_REDIRECT_OPENER = build_opener(_NoRedirect)

class MubayyinClient:
    """Client for the invited-pilot tenant API.

    base_url must use HTTPS, except localhost/loopback HTTP for local tests.
    Requests are deliberately not retried: trial/release POSTs are not yet
    protected by a server-side idempotency-key contract.
    """
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0):
        parsed = urlsplit(base_url.strip())
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not local_http:
            raise ValueError("base_url must use HTTPS (HTTP is allowed only for loopback testing).")
        if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url must be an absolute origin/path without credentials, query, or fragment.")
        if not isinstance(api_key, str) or len(api_key.strip()) < 32 or any(ch.isspace() for ch in api_key.strip()):
            raise ValueError("api_key must be a non-empty tenant bearer key.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        self.base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self.timeout = float(timeout)

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        if not path.startswith("/") or ".." in path.split("/"):
            raise ValueError("API path must be an absolute path without traversal segments.")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._api_key}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with _NO_REDIRECT_OPENER.open(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            try:
                error_body = exc.read(8192).decode("utf-8", errors="replace")
                parsed_error = json.loads(error_body) if error_body else {}
                detail = parsed_error.get("detail") or parsed_error.get("message") or "Request rejected"
                if not isinstance(detail, str):
                    detail = json.dumps(detail, ensure_ascii=False)
            except Exception:
                detail = "Request rejected"
            raise MubayyinAPIError(exc.code, detail) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise MubayyinTransportError(f"Could not reach Mubayyin API ({type(exc).__name__}).") from None
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise MubayyinTransportError("Mubayyin API returned a non-JSON response.") from None

    def identity(self) -> dict[str, Any]:
        return self._request("GET", "/tenant/me")
    def create_system(self, **system: Any) -> dict[str, Any]:
        return self._request("POST", "/tenant/systems", system)
    def create_scenario(self, **scenario: Any) -> dict[str, Any]:
        return self._request("POST", "/tenant/scenarios", scenario)
    def run_trial(self, system_id: str, scenario_id: str, model_output: str) -> dict[str, Any]:
        return self._request("POST", "/tenant/trials", {"system_id": system_id, "scenario_id": scenario_id, "model_output": model_output})
    def review_trial(self, result_id: str, reviewer: str, agrees_with_automation: bool, override_severity: str | None = None, comment: str = "") -> dict[str, Any]:
        return self._request("POST", f"/tenant/trials/{result_id}/review", {"reviewer": reviewer, "agrees_with_automation": agrees_with_automation, "override_severity": override_severity, "comment": comment})
    def create_release(self, **release: Any) -> dict[str, Any]:
        return self._request("POST", "/tenant/releases", release)
    def get_release(self, record_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tenant/releases/{record_id}")
    def export_release(self, record_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tenant/releases/{record_id}/export")
    def create_action_mandate(self, **mandate: Any) -> dict[str, Any]:
        """Store a tenant-scoped, immutable Action Mandate snapshot."""
        return self._request("POST", "/tenant/action-mandates", mandate)
    def revoke_action_mandate(self, mandate_id: str) -> dict[str, Any]:
        return self._request("POST", f"/tenant/action-mandates/{quote(mandate_id, safe='')}/revoke")
    def assess_action(self, **proposal: Any) -> dict[str, Any]:
        """Assess a proposed action; server supplies the evaluation timestamp."""
        return self._request("POST", "/tenant/action-assessments", proposal)
    def get_action_assessment(self, assessment_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tenant/action-assessments/{quote(assessment_id, safe='')}")
    def verify_bundle(self, bundle: Mapping[str, Any]) -> dict[str, Any]:
        """Ask the public verifier to check a downloaded JSON evidence bundle."""
        return self._request("POST", "/releases/verify", bundle)
