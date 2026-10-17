"""Read-only Atlassian MCP client. Keeps fetch_jira_issue compatible with LangGraph."""
import argparse
import asyncio
import json
import os
import re
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
from dotenv import load_dotenv
from pydantic import AnyUrl
from mcp import ClientSession
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
MCP_URL = os.getenv('ATLASSIAN_MCP_URL', 'https://mcp.atlassian.com/v2/mcp').strip()
JIRA_URL = os.getenv('JIRA_SITE_URL', os.getenv('JIRA_URL', '')).strip()
CALLBACK_URL = 'http://localhost:3000/callback'
READ_TOOLS = {'getAccessibleAtlassianResources', 'getJiraIssue', 'searchJiraIssuesUsingJql'}


def validate_issue_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]*-\d+', value):
        raise ValueError('Expected a Jira issue key.')
    return value


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


async def handle_callback() -> AuthorizationCodeResult:
    print('Complete browser consent. A localhost connection error is expected in this manual flow.')
    print('Paste the full localhost callback URL here. Input will be visible; do not share it.')
    callback = urlparse(input('Callback URL: ').strip())
    expected = urlparse(CALLBACK_URL)
    if (callback.scheme, callback.hostname, callback.port, callback.path) != (
        expected.scheme, expected.hostname, expected.port, expected.path
    ):
        raise ValueError('Callback must match the configured localhost redirect.')
    params = parse_qs(callback.query)
    if params.get('error'):
        raise ValueError('Browser authorization was denied or failed; start again.')
    if not params.get('code') or not params.get('state'):
        raise ValueError('Callback has no authorization code or state; complete login first.')
    # The SDK validates the returned state and performs the PKCE token exchange.
    return AuthorizationCodeResult(code=params['code'][0], state=params['state'][0], iss=params.get('iss', [None])[0])


@asynccontextmanager
async def jira_session():
    if urlparse(JIRA_URL).scheme != 'https' or not urlparse(JIRA_URL).hostname:
        raise ValueError('Set JIRA_SITE_URL to your https://site.atlassian.net URL in .env.')
    oauth = OAuthClientProvider(
        server_url=MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name='AI-SDET Jira MCP Client',
            redirect_uris=[AnyUrl(CALLBACK_URL)],
            grant_types=['authorization_code', 'refresh_token'],
            response_types=['code'],
        ),
        storage=InMemoryTokenStorage(),
        redirect_handler=handle_redirect,
        callback_handler=handle_callback,
    )
    async with httpx2.AsyncClient(auth=oauth) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                print('Connecting to Atlassian MCP...')
                await session.initialize()
                yield session


async def get_cloud_id(session):
    data = await read_tool(session, 'getAccessibleAtlassianResources', {})
    resources = data.get('resources') if isinstance(data, dict) else data
    if not isinstance(resources, list):
        raise RuntimeError('Unexpected Atlassian resource response.')
    host = urlparse(JIRA_URL).hostname
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


async def get_child_issues(session, cloud_id, parent_key, page_size=50, max_pages=100):
    validate_issue_key(parent_key)
    return await search_jira_issues(session, cloud_id,
        f'parent = "{parent_key}" ORDER BY created ASC, key ASC', page_size, max_pages)


async def fetch_jira_issue(issue_key, include_children=False):
    validate_issue_key(issue_key)
    async with jira_session() as session:
        cloud_id = await get_cloud_id(session)
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

async def handle_redirect(
    auth_url: str
) -> None:

    print()
    print("Opening Atlassian login...")

    webbrowser.open(auth_url)

    print(
        "Complete login/consent in the browser."
    )

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
