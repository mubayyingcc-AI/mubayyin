import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from sdk.python.mubayyin_client import MubayyinClient, MubayyinAPIError, MubayyinTransportError

class FakeResponse:
    def __init__(self, body=b'{"ok":true}'):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body

class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response or FakeResponse(), error, []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error: raise self.error
        return self.response

class MubayyinClientTests(unittest.TestCase):
    def test_requires_https_except_loopback(self):
        with self.assertRaises(ValueError):
            MubayyinClient("http://example.com", "x" * 40)
        self.assertIsInstance(MubayyinClient("http://127.0.0.1:8000", "x" * 40), MubayyinClient)
    def test_rejects_credentials_in_base_url_and_short_key(self):
        with self.assertRaises(ValueError):
            MubayyinClient("https://user:pass@example.com", "x" * 40)
        with self.assertRaises(ValueError):
            MubayyinClient("https://example.com", "short")
    def test_identity_sends_bearer_and_parses_json(self):
        client = MubayyinClient("https://example.com/", "k" * 40)
        fake = FakeOpener()
        with patch("sdk.python.mubayyin_client._NO_REDIRECT_OPENER", fake):
            result = client.identity()
        self.assertEqual(result, {"ok": True})
        request, timeout = fake.calls[0]
        self.assertEqual(request.full_url, "https://example.com/tenant/me")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + "k" * 40)
        self.assertEqual(timeout, 15.0)
    def test_trial_posts_json_once_without_retry(self):
        client = MubayyinClient("https://example.com", "k" * 40)
        fake = FakeOpener()
        with patch("sdk.python.mubayyin_client._NO_REDIRECT_OPENER", fake):
            result = client.run_trial("sys-1", "sc-1", "synthetic output")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(fake.calls), 1)
        request, _ = fake.calls[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("application/json", request.get_header("Content-type"))
    def test_http_error_does_not_expose_bearer(self):
        client = MubayyinClient("https://example.com", "secret-" + "x" * 40)
        error = HTTPError("https://example.com", 401, "Unauthorized", {}, BytesIO(b'{"detail":"Invalid key"}'))
        fake = FakeOpener(error=error)
        with patch("sdk.python.mubayyin_client._NO_REDIRECT_OPENER", fake):
            with self.assertRaises(MubayyinAPIError) as caught:
                client.identity()
        self.assertEqual(caught.exception.status_code, 401)
        self.assertNotIn("secret-", str(caught.exception))
    def test_redirect_is_not_followed(self):
        client = MubayyinClient("https://example.com", "k" * 40)
        error = HTTPError("https://example.com", 307, "Redirect", {"Location":"https://elsewhere.invalid"}, BytesIO(b""))
        fake = FakeOpener(error=error)
        with patch("sdk.python.mubayyin_client._NO_REDIRECT_OPENER", fake):
            with self.assertRaises(MubayyinAPIError):
                client.identity()
        self.assertEqual(len(fake.calls), 1)
    def test_rejects_path_traversal(self):
        client = MubayyinClient("https://example.com", "k" * 40)
        with self.assertRaises(ValueError):
            client._request("GET", "/tenant/../admin")

if __name__ == "__main__":
    unittest.main()
