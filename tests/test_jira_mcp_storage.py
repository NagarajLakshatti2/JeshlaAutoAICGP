"""Offline tests for encrypted Atlassian MCP OAuth storage."""
from pathlib import Path
import tempfile
import unittest
from contextlib import asynccontextmanager
from unittest.mock import ANY, AsyncMock, patch

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from agent.storage.connections import ConnectionCatalog
from agent.storage.projects import ProjectConfigurationError
from integrations.jira.oauth_browser import CALLBACK_URL, parse_callback_target
from integrations.jira import jira_mcp_client
from integrations.jira.jira_mcp_client import CatalogOAuthTokenStorage, MCP_URL, validate_site_url


def fixture_protect(value, decrypt=False):
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    if decrypt:
        if not raw.startswith(b"test-sealed:"):
            raise ValueError("not a fixture secret")
        return raw[len(b"test-sealed:"):]
    return b"test-sealed:" + raw


def run_storage_coroutine(coroutine):
    """Drive the OAuth storage coroutine without opening a restricted Windows socket loop."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError("The storage operation unexpectedly suspended.")


class CatalogOAuthTokenStorageTests(unittest.TestCase):
    def test_jira_site_url_is_canonical_and_rejects_non_site_targets(self):
        self.assertEqual(validate_site_url(" HTTPS://Example.atlassian.net/ "),"https://example.atlassian.net")
        for value in ("","http://example.atlassian.net","https://example.com",
                      "https://user:pass@example.atlassian.net","https://example.atlassian.net:bad",
                      "https://example.atlassian.net/browse/DEMO-1","https://example.atlassian.net?x=1"):
            with self.subTest(value=value),self.assertRaises(ValueError):validate_site_url(value)

    def test_profile_scoped_issue_read_uses_the_selected_site_and_oauth_storage(self):
        token_storage=object();site="https://profile-a.atlassian.net";captured={}
        @asynccontextmanager
        async def session(*,token_storage=None,jira_site_url=None):
            captured.update(storage=token_storage,site=jira_site_url)
            yield object()
        cloud=AsyncMock(return_value="cloud-a")
        issue=AsyncMock(return_value={"key":"DEMO-1","fields":{}})
        with patch.object(jira_mcp_client,"jira_session",side_effect=session), \
             patch.object(jira_mcp_client,"get_cloud_id",cloud), \
             patch.object(jira_mcp_client,"get_jira_issue",issue):
            result=run_storage_coroutine(jira_mcp_client.fetch_jira_issue(
                "DEMO-1",token_storage=token_storage,jira_site_url=site))
        self.assertEqual(result,{"key":"DEMO-1","fields":{}})
        self.assertIs(captured["storage"],token_storage)
        self.assertEqual(captured["site"],site)
        cloud.assert_awaited_once_with(ANY,jira_site_url=site)
        issue.assert_awaited_once_with(ANY,"cloud-a","DEMO-1")

    def test_profile_scoped_read_cannot_fall_back_to_global_site_or_read_hierarchy(self):
        with patch.object(jira_mcp_client,"jira_session") as session:
            with self.assertRaisesRegex(ValueError,"own site URL"):
                run_storage_coroutine(jira_mcp_client.fetch_jira_issue("DEMO-1",token_storage=object()))
            with self.assertRaisesRegex(ValueError,"hierarchy reads are disabled"):
                run_storage_coroutine(jira_mcp_client.fetch_jira_issue("DEMO-1",include_children=True,
                    token_storage=object(),jira_site_url="https://profile-a.atlassian.net"))
            session.assert_not_called()

    def test_browser_callback_accepts_one_code_and_state_without_logging_them(self):
        result = parse_callback_target("/callback?code=fixture-code&state=fixture-state&iss=https%3A%2F%2Fauth.atlassian.com")
        self.assertEqual(result.code, "fixture-code")
        self.assertEqual(result.state, "fixture-state")
        self.assertEqual(result.iss, "https://auth.atlassian.com")
        self.assertEqual(CALLBACK_URL, "http://localhost:3000/callback")

    def test_browser_callback_rejects_wrong_targets_denials_and_ambiguous_parameters(self):
        for target in (
            "https://evil.example/callback?code=x&state=y",
            "//evil.example/callback?code=x&state=y",
            "/wrong?code=x&state=y",
            "/callback?code=x&code=y&state=z",
            "/callback?code=x&state=y&error=access_denied",
            "/callback?code=x",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                parse_callback_target(target)

    def test_oauth_client_and_tokens_roundtrip_without_public_or_plaintext_storage(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "agent.storage.connections.protect_token", side_effect=fixture_protect
        ):
            database = Path(folder) / "connections.sqlite3"
            catalog = ConnectionCatalog(database, "user-a", "space-a")
            connection = catalog.save("jira_mcp", "Work Jira", MCP_URL)
            storage = CatalogOAuthTokenStorage(catalog, connection["id"])
            client_info = OAuthClientInformationFull(
                client_id="fixture-client-id",
                client_secret="fixture-client-secret",
            )
            tokens = OAuthToken(
                access_token="fixture-access-token",
                refresh_token="fixture-refresh-token",
                expires_in=3600,
            )
            run_storage_coroutine(storage.set_client_info(client_info))
            run_storage_coroutine(storage.set_tokens(tokens))
            site="https://example.atlassian.net"
            catalog.checked(connection["id"],{"jira_site_url":site,"cloud_id":"fixture-cloud"})
            refreshed=OAuthToken(access_token="fixture-refreshed-access-token",
                                 refresh_token="fixture-refreshed-refresh-token",expires_in=3600)
            run_storage_coroutine(storage.set_tokens(refreshed))

            restored = CatalogOAuthTokenStorage(catalog, connection["id"])
            self.assertEqual(run_storage_coroutine(restored.get_client_info()), client_info)
            self.assertEqual(run_storage_coroutine(restored.get_tokens()), refreshed)
            self.assertEqual(restored.endpoint, MCP_URL)
            self.assertEqual(catalog.get(connection["id"])["status"],"verified")
            self.assertEqual(catalog.get(connection["id"])["details"],{"jira_site_url":site,"cloud_id":"fixture-cloud"})
            self.assertNotIn("fixture-access-token", str(catalog.list()))
            self.assertNotIn("fixture-client-secret", str(catalog.list()))
            raw_database = database.read_bytes()
            self.assertNotIn(b"fixture-refreshed-access-token", raw_database)
            self.assertNotIn(b"fixture-client-secret", raw_database)

    def test_catalog_storage_rejects_non_jira_and_non_atlassian_connections(self):
        with tempfile.TemporaryDirectory() as folder:
            catalog = ConnectionCatalog(Path(folder) / "c.sqlite3", "user-a", "space-a")
            git = catalog.save("github", "GitHub", "https://api.github.com")
            custom = catalog.save("jira_mcp", "Wrong endpoint", "https://example.org/mcp")
            with self.assertRaisesRegex(ProjectConfigurationError, "Jira MCP connection"):
                CatalogOAuthTokenStorage(catalog, git["id"])
            with self.assertRaisesRegex(ProjectConfigurationError, "official Atlassian endpoint"):
                CatalogOAuthTokenStorage(catalog, custom["id"])

    def test_replacing_secret_clears_env_source_and_verified_status(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            "agent.storage.connections.protect_token", side_effect=fixture_protect
        ):
            catalog = ConnectionCatalog(Path(folder) / "c.sqlite3", "user-a", "space-a")
            connection = catalog.save("jira_mcp", "Work Jira", MCP_URL, env_name="JIRA_MCP_TOKEN")
            catalog.checked(connection["id"], {"site_count": 1})
            updated = catalog.replace_credential(connection["id"], "fixture-oauth-payload")
            self.assertEqual(updated["status"], "configured")
            self.assertEqual(updated["env_name"], "")
            self.assertTrue(updated["credential_present"])
            self.assertEqual(catalog.credential(connection["id"]), "fixture-oauth-payload")


if __name__ == "__main__":
    unittest.main()
