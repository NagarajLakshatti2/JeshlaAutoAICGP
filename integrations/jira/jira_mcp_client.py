"""Read-only Atlassian MCP client. Keeps fetch_jira_issue compatible with LangGraph."""
import argparse
import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
from dotenv import load_dotenv
from pydantic import AnyUrl
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from agent.config.paths import DATA_ROOT
from integrations.jira.oauth_browser import BrowserOAuthFlow, CALLBACK_URL
load_dotenv(DATA_ROOT / '.env')
MCP_URL = os.getenv('ATLASSIAN_MCP_URL', 'https://mcp.atlassian.com/v2/mcp').strip()
JIRA_URL = os.getenv('JIRA_SITE_URL', os.getenv('JIRA_URL', '')).strip()
READ_TOOLS = {'getAccessibleAtlassianResources', 'getJiraIssue', 'searchJiraIssuesUsingJql'}


def validate_issue_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]*-\d+', value):
        raise ValueError('Expected a Jira issue key.')
    return value


def validate_site_url(value):
    """Accept a Jira Cloud site URL, never an MCP endpoint or credential URL."""
    from urllib.parse import urlsplit
    try:
        parsed=urlsplit(value.strip() if isinstance(value,str) else "")
        port=parsed.port
    except ValueError:
        raise ValueError("Expected a Jira Cloud site URL such as https://example.atlassian.net.") from None
    host=(parsed.hostname or "").lower()
    labels=host.split(".")
    valid_host=(len(labels)>=3 and labels[-2:]==["atlassian","net"] and
                all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",label) for label in labels))
    if (parsed.scheme!="https" or not valid_host or parsed.username or parsed.password or
        port not in (None,443) or parsed.path not in ("","/") or parsed.query or parsed.fragment):
        raise ValueError("Expected a Jira Cloud site URL such as https://example.atlassian.net.")
    return f"https://{host}"


def extract_issue_key(value):
    if re.fullmatch(r'[A-Z][A-Z0-9_]*-\d+', value or ''):
        return value
    parsed = urlparse(value)
    selected = parse_qs(parsed.query).get('selectedIssue', [None])[0]
    if selected:
        return validate_issue_key(selected)
    match = re.search(r'/browse/([A-Z][A-Z0-9_]*-\d+)(?:/|$)', parsed.path)
    if match:
        return match.group(1)
    raise ValueError('Set JIRA_ISSUE_KEY or provide an issue key / browse URL.')


def get_result_text(result):
    return '\n'.join(item.text for item in result.content if isinstance(getattr(item, 'text', None), str))


def response_payloads(result):
    """Read JSON representations only; never interpret text as instructions."""
    if getattr(result, 'is_error', False) or getattr(result, 'isError', False):
        raise RuntimeError('Atlassian MCP reported a tool error.')
    values = []
    structured = getattr(result, 'structured_content', None)
    if structured is None:
        structured = getattr(result, 'structuredContent', None)
    if structured is not None:
        values.append(('structured', structured))
    for index, block in enumerate(getattr(result, 'content', []) or []):
        text = getattr(block, 'text', None)
        if not isinstance(text, str):
            continue
        try:
            values.append((f'text[{index}]', json.loads(text)))
        except ValueError:
            continue
    payloads = []
    for label, value in values:
        if isinstance(value, dict) and value.get('error'):
            raise RuntimeError('Atlassian returned an error object.')
        data = value.get('data', value) if isinstance(value, dict) else value
        if isinstance(data, dict) and data.get('error'):
            raise RuntimeError('Atlassian returned a nested error object.')
        if isinstance(data, (dict, list)):
            payloads.append((label, data))
    if not payloads:
        raise RuntimeError('No JSON response data could be decoded.')
    return payloads


def merge_issue_fields(primary, other):
    if primary.get('key') != other.get('key'):
        raise RuntimeError('Conflicting issue keys across MCP response representations.')

    def merge(left, right):
        if isinstance(left, dict) and isinstance(right, dict):
            combined = dict(left)
            for key, value in right.items():
                combined[key] = merge(combined[key], value) if key in combined else value
            return combined
        if type(left) is not type(right) or left != right:
            # Even null versus populated metadata is a conflict, not proof.
            raise RuntimeError('Conflicting issue fields across MCP response representations.')
        return left

    merged = dict(primary)
    merged['fields'] = merge(primary['fields'], other['fields'])
    return merged


def decode_result(result):
    payloads = response_payloads(result)
    primary = payloads[0][1]
    for _, other in payloads[1:]:
        if not isinstance(primary, dict) or not isinstance(other, dict):
            continue
        if isinstance(primary.get('fields'), dict) and isinstance(other.get('fields'), dict):
            primary = merge_issue_fields(primary, other)
        elif isinstance(primary.get('issues'), list) and isinstance(other.get('issues'), list):
            # Merge only matching search pages; never add unobserved search members.
            first_keys = [x.get('key') for x in primary['issues']]
            other_keys = [x.get('key') for x in other['issues']]
            if len(set(first_keys)) != len(first_keys) or set(first_keys) != set(other_keys):
                raise RuntimeError('Conflicting issue sets across MCP search representations.')
            for key in ('isLast', 'nextPageToken'):
                if key in primary and key in other and primary[key] != other[key]:
                    raise RuntimeError('Conflicting pagination across MCP response representations.')
            lookup = {x['key']: x for x in other['issues']}
            primary = {**primary, 'issues': [
                merge_issue_fields(x, lookup[x['key']])
                if isinstance(x.get('fields'), dict) and isinstance(lookup[x['key']].get('fields'), dict)
                else x for x in primary['issues']
            ]}
    return primary


async def read_tool(session, name, arguments):
    if name not in READ_TOOLS:
        raise ValueError('Only Jira read tools are enabled in this client.')
    result = await session.call_tool(name, arguments=arguments)
    try:
        decoded = decode_result(result)
    except RuntimeError as error:
        # These decoder errors contain fixed messages, never response values.
        print('MCP RESPONSE CHECK:', str(error))
        raise
    if name == 'getJiraIssue':
        fields = decoded.get('fields', {}) if isinstance(decoded, dict) else {}
        issue_type = fields.get('issuetype') if isinstance(fields, dict) else None
        if not isinstance(issue_type, dict) or type(issue_type.get('subtask')) is not bool:
            shapes = []
            for label, data in response_payloads(result):
                shapes.append({
                    'channel': label,
                    'payload_type': type(data).__name__,
                    'top_level_keys': sorted(data) if isinstance(data, dict) else [],
                    'field_names': sorted(data['fields'])
                        if isinstance(data, dict) and isinstance(data.get('fields'), dict) else [],
                })
            print('MCP RESPONSE SHAPES:', json.dumps(shapes))
    return decoded


@asynccontextmanager
async def jira_session(token_storage=None, jira_site_url=None):
    site_url=validate_site_url(jira_site_url if jira_site_url is not None else JIRA_URL)
    server_url = getattr(token_storage, 'endpoint', MCP_URL)
    browser_flow = BrowserOAuthFlow()
    oauth = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name='AI-SDET Jira MCP Client',
            redirect_uris=[AnyUrl(CALLBACK_URL)],
            grant_types=['authorization_code', 'refresh_token'],
            response_types=['code'],
        ),
        storage=token_storage or InMemoryTokenStorage(),
        redirect_handler=browser_flow.redirect_handler,
        callback_handler=browser_flow.callback_handler,
    )
    async with httpx2.AsyncClient(auth=oauth) as http_client:
        async with streamable_http_client(server_url, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                print('Connecting to Atlassian MCP...')
                await session.initialize()
                yield session


async def get_cloud_id(session, jira_site_url=None):
    data = await read_tool(session, 'getAccessibleAtlassianResources', {})
    resources = data.get('resources') if isinstance(data, dict) else data
    if not isinstance(resources, list):
        raise RuntimeError('Unexpected Atlassian resource response.')
    host = urlparse(validate_site_url(jira_site_url if jira_site_url is not None else JIRA_URL)).hostname
    matches = [r for r in resources if isinstance(r, dict) and urlparse(r.get('url', '')).hostname == host]
    ids = {r.get('cloudId') or r.get('id') for r in matches}
    ids.discard(None)
    if len(ids) != 1:
        raise RuntimeError('Could not uniquely select the configured Jira site from accessible resources.')
    return ids.pop()


async def get_jira_issue(session, cloud_id, issue_key, fields=None):
    validate_issue_key(issue_key)
    requested_fields = fields if fields is not None else [
        "summary", "description", "issuetype", "parent", "status", "priority",
    ]
    issue = await read_tool(session, "getJiraIssue", {
        "cloudId": cloud_id,
        "issueIdOrKey": issue_key,
        "fields": requested_fields,
    })
    if not isinstance(issue, dict) or issue.get("key") != issue_key or not isinstance(issue.get("fields"), dict):
        raise RuntimeError(f"No matching issue data returned for {issue_key}.")
    return issue


async def search_jira_issues(session, cloud_id, jql, page_size=50, max_pages=100, fields=None):
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError('page_size must be between 1 and 100.')
    if type(max_pages) is not int or not 1 <= max_pages <= 1000:
        raise ValueError('max_pages must be between 1 and 1000.')
    if not isinstance(jql, str) or not jql.strip():
        raise ValueError('jql is required.')
    issues, tokens, token = {}, set(), None
    for page in range(1, max_pages + 1):
        args = {'cloudId': cloud_id, 'jql': jql, 'searchResultMode': 'issues', 'maxResults': page_size}
        if fields is not None:
            args['fields'] = fields
        if token is not None:
            args['nextPageToken'] = token
        data = await read_tool(session, 'searchJiraIssuesUsingJql', args)
        if not isinstance(data, dict) or not isinstance(data.get('issues'), list):
            raise RuntimeError('Search did not return an issues list.')
        for issue in data['issues']:
            if not isinstance(issue, dict) or not issue.get('key'):
                raise RuntimeError('Search returned an issue without a key.')
            issues[validate_issue_key(issue['key'])] = issue
        print(f'Jira page {page}: {len(data["issues"])} issues')
        next_token = data.get('nextPageToken')
        if data.get('isLast') is True:
            return list(issues.values())
        if data.get('isLast') is not False:
            raise RuntimeError('Search pagination completeness is unverified: missing isLast flag.')
        if not isinstance(next_token, str) or not next_token or next_token in tokens:
            raise RuntimeError('Missing or repeated pagination token; results are incomplete.')
        tokens.add(next_token)
        token = next_token
    raise RuntimeError('Search page limit reached; results are incomplete.')


async def search_jira_project_issues(project_key, *, token_storage, jira_site_url, limit=5):
    """Return a bounded, read-only summary of recent issues in one assigned project."""
    if not isinstance(project_key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", project_key):
        raise ValueError("Expected a Jira project key.")
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("Project search limit must be between 1 and 5.")
    site_url = validate_site_url(jira_site_url)
    jql = f"project = {project_key} ORDER BY created DESC"
    async with jira_session(token_storage=token_storage, jira_site_url=site_url) as session:
        cloud_id = await get_cloud_id(session, jira_site_url=site_url)
        data = await read_tool(session, "searchJiraIssuesUsingJql", {
            "cloudId": cloud_id,
            "jql": jql,
            "searchResultMode": "issues",
            "maxResults": limit,
            "fields": ["summary", "status"],
        })
    issues = data.get("issues") if isinstance(data, dict) else None
    if not isinstance(issues, list):
        raise RuntimeError("Jira project search did not return an issues list.")
    result = []
    for issue in issues[:limit]:
        if not isinstance(issue, dict):
            raise RuntimeError("Jira project search returned an invalid issue.")
        key = validate_issue_key(issue.get("key"))
        if not key.startswith(project_key + "-"):
            raise RuntimeError("Jira project search returned an issue outside the assigned project.")
        fields = issue.get("fields")
        if not isinstance(fields, dict) or not isinstance(fields.get("summary"), str):
            raise RuntimeError("Jira project search omitted an issue summary.")
        status = fields.get("status")
        status_name = status.get("name") if isinstance(status, dict) else None
        if not isinstance(status_name, str):
            raise RuntimeError("Jira project search omitted an issue status.")
        result.append({"key": key, "summary": fields["summary"], "status": status_name})
    return result


async def get_child_issues(session, cloud_id, parent_key, page_size=50, max_pages=100):
    validate_issue_key(parent_key)
    return await search_jira_issues(session, cloud_id,
        f'parent = "{parent_key}" ORDER BY created ASC, key ASC', page_size, max_pages)


async def fetch_jira_issue(issue_key, include_children=False, *, token_storage=None, jira_site_url=None):
    validate_issue_key(issue_key)
    if token_storage is not None:
        if jira_site_url is None:
            raise ValueError("A saved Jira MCP profile must supply its own site URL.")
        if include_children:
            raise ValueError("Profile-scoped reads currently allow only one Jira issue; hierarchy reads are disabled.")
    site_url=validate_site_url(jira_site_url if jira_site_url is not None else JIRA_URL)
    async with jira_session(token_storage=token_storage,jira_site_url=site_url) as session:
        cloud_id = await get_cloud_id(session,jira_site_url=site_url)
        issue = await get_jira_issue(session, cloud_id, issue_key)
        if include_children:
            return await read_issue_hierarchy(session, cloud_id, issue)
        return issue


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', default=os.getenv('JIRA_ISSUE_KEY', ''))
    parser.add_argument('--children', action='store_true')
    args = parser.parse_args()
    issue_key = extract_issue_key(args.issue or JIRA_URL)
    result = await fetch_jira_issue(issue_key, include_children=args.children)
    print(json.dumps(result, indent=2, ensure_ascii=False))
class InMemoryTokenStorage:

    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(
        self,
        tokens: OAuthToken
    ) -> None:
        self.tokens = tokens

    async def get_client_info(
        self
    ) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(
        self,
        client_info: OAuthClientInformationFull
    ) -> None:
        self.client_info = client_info


class CatalogOAuthTokenStorage:
    """Persist one Atlassian OAuth client/token pair in the encrypted connection catalog."""

    def __init__(self, catalog, connection_id):
        from agent.storage.projects import ProjectConfigurationError

        row = catalog.get(connection_id)
        if not row or row.get('kind') != 'jira_mcp':
            raise ProjectConfigurationError('Choose a Jira MCP connection in this workspace.')
        parsed = urlparse(row.get('endpoint', ''))
        if (parsed.scheme, parsed.hostname, parsed.port, parsed.path, parsed.query, parsed.fragment) != (
            'https', 'mcp.atlassian.com', None, '/v2/mcp', '', ''
        ) or parsed.username or parsed.password:
            raise ProjectConfigurationError('Jira MCP connections must use the official Atlassian endpoint.')
        if row.get('env_name'):
            raise ProjectConfigurationError('This connection uses a different credential source. Reconfigure it for browser OAuth.')
        self.catalog = catalog
        self.connection_id = connection_id
        self.endpoint = row['endpoint']
        self.tokens = None
        self.client_info = None
        if row.get('credential_present'):
            try:
                saved = json.loads(catalog.credential(connection_id))
                if not isinstance(saved, dict):
                    raise ValueError
                if saved.get('tokens') is not None:
                    self.tokens = OAuthToken.model_validate(saved['tokens'])
                if saved.get('client_info') is not None:
                    self.client_info = OAuthClientInformationFull.model_validate(saved['client_info'])
            except Exception:
                raise ProjectConfigurationError('Saved Jira OAuth data is invalid. Disconnect and reconnect the account.') from None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens
        self._persist()

    async def get_client_info(self):
        return self.client_info

    async def set_client_info(self, client_info):
        self.client_info = client_info
        self._persist()

    def _persist(self):
        if self.tokens is None and self.client_info is None:
            return
        payload = {
            'tokens': self.tokens.model_dump(mode='json') if self.tokens is not None else None,
            'client_info': self.client_info.model_dump(mode='json') if self.client_info is not None else None,
        }
        self.catalog.update_jira_oauth_data(self.connection_id, json.dumps(payload, separators=(',', ':')))

async def read_issue_hierarchy(
    session: ClientSession,
    cloud_id: str,
    root_issue: dict,
    max_issues: int = 30,
) -> dict:
    """Read the root issue and two child levels."""

    visited = {root_issue["key"]}

    async def build_node(issue: dict, depth: int) -> dict:
        node = {
            "issue": issue,
            "children": [],
        }

        if depth >= 2:
            return node

        children = await get_child_issues(
            session,
            cloud_id,
            issue["key"],
        )

        for child in children:
            child_key = child.get("key")

            if not child_key:
                raise RuntimeError("Child issue has no key.")

            if child_key in visited:
                continue

            if len(visited) >= max_issues:
                raise RuntimeError(
                    f"Hierarchy exceeded {max_issues} issues."
                )

            visited.add(child_key)

            full_issue = await get_jira_issue(
                session,
                cloud_id,
                child_key,
            )

            if not full_issue:
                raise RuntimeError(
                    f"Could not read {child_key}."
                )

            node["children"].append(
                await build_node(full_issue, depth + 1)
            )

        return node

    hierarchy = await build_node(root_issue, depth=0)

    return {
        "root_key": root_issue["key"],
        "retrieved_issue_count": len(visited),
        "coverage_note": (
            "All search pages were retrieved for each queried parent. "
            "Traversal covers two child levels and only issues visible "
            "to the authenticated account."
        ),
        "hierarchy": hierarchy,
    }

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Stopped.')
    except Exception as error:
        print(f'Jira read failed ({type(error).__name__}). Check configuration and browser consent. No result confirmed.')
        raise SystemExit(1)
