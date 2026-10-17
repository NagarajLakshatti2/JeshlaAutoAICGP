"""Verify accidental external access fails before a real request is sent."""
import socket
import unittest
import webbrowser
import requests
from run_offline import offline_guard, is_loopback


class OfflineGuardTests(unittest.TestCase):
    def test_external_socket_is_blocked(self):
        with offline_guard(), socket.socket() as sock:
            with self.assertRaisesRegex(RuntimeError, "external socket"):
                sock.connect(("203.0.113.1", 443))
            with self.assertRaisesRegex(RuntimeError, "external socket"):
                sock.connect_ex(("203.0.113.1", 443))

    def test_unmocked_http_and_browser_are_blocked(self):
        with offline_guard():
            with self.assertRaisesRegex(RuntimeError, "require a mock"):
                requests.get("https://example.invalid", timeout=1)
            with self.assertRaisesRegex(RuntimeError, "require a mock"):
                webbrowser.open("https://example.invalid")

    def test_loopback_classification(self):
        self.assertTrue(is_loopback(("127.0.0.1", 80)))
        self.assertTrue(is_loopback(("::1", 80)))
        self.assertFalse(is_loopback(("203.0.113.1", 443)))
        self.assertFalse(is_loopback(("example.invalid", 443)))
