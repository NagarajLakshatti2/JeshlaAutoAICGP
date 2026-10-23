"""Bounded, approval-controlled browser discovery. No form actions or user profile."""
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import uuid
from agent.config.paths import APPLICATION_ROOT
from agent.tools.web_pages import url_location

TIMEOUT_SECONDS = 55


def evidence_directory(tools, relative_folder):
    from agent.tools.project_tools import SKIP_DIRS, SKIP_FILES
    if not isinstance(relative_folder, str) or not relative_folder.strip():
        raise ValueError('Choose a relative browser-evidence folder.')
    requested = Path(relative_folder)
    path = (tools.root / requested).resolve()
    if requested.is_absolute() or '..' in requested.parts or not path.is_relative_to(tools.root):
        raise ValueError('Browser evidence must stay inside the selected project.')
    if any(part in SKIP_DIRS or part in SKIP_FILES or part.startswith('.env')
           for part in path.relative_to(tools.root).parts):
        raise ValueError('Excluded browser-evidence folder.')
    if path.exists() and not path.is_dir():
        raise ValueError('Browser evidence destination must be a folder.')
    return path


def allow_request(url, method, selected_url):
    """Only ordinary reads on the selected origin; root DNS is pinned at launch."""
    try:
        parts, host, port = url_location(url)
        root, selected_host, selected_port = url_location(selected_url)
        return (method in {'GET', 'HEAD'} and host == selected_host and port == selected_port
                and parts.scheme == root.scheme)
    except (ValueError, TypeError, UnicodeError):
        return False


def validate_public_browser_address(address):
    """Check the chosen pinned IP, including IPv4 embedded in NAT64/6to4."""
    ip=ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or getattr(ip,'ipv4_mapped',None):
        raise ValueError('A public browser address is required.')
    embedded=getattr(ip,'sixtofour',None)
    if ip.version==6 and ip in ipaddress.ip_network('64:ff9b::/96'):
        embedded=ipaddress.IPv4Address(int(ip)&0xffffffff)
    if embedded is not None and not embedded.is_global:
        raise ValueError('Private IPv4 embedded in a transition address is blocked.')
    return str(ip)


def inspect_browser_page(tools, url, evidence_folder='test-output/agent-web', limit=20):
    """Run a killable isolated worker and return bounded visible element evidence."""
    parts, host, port = url_location(url)
    if parts.scheme != 'https':
        raise ValueError('This browser pilot requires an explicit public HTTPS URL.')
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError('Browser field limit must be 1-40.')
    parent = evidence_directory(tools, evidence_folder)
    folder = parent / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    payload = {'url': url, 'limit': limit, 'screenshot': str(folder / 'inspection.png')}
    process = None
    try:
        process = subprocess.Popen([sys.executable, '-m', 'integrations.web.inspection_worker'],
            cwd=str(APPLICATION_ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        output, error = process.communicate(json.dumps(payload), timeout=TIMEOUT_SECONDS)
        if process.returncode != 0 or len(output) > 65000:
            raise RuntimeError('Browser inspection worker failed; no inspected elements are claimed.')
        result = json.loads(output)
        if not isinstance(result, dict):
            raise RuntimeError('Browser inspection returned invalid data.')
        if result.get('status') != 'inspected':
            raise RuntimeError('Browser inspection did not finish: ' + str(result.get('error', 'unknown failure'))[:300])
        if not isinstance(result.get('fields'), list) or len(result['fields']) > limit:
            raise RuntimeError('Browser returned invalid discovery data.')
        result['inspection_file'] = (folder / 'inspection.json').relative_to(tools.root).as_posix()
        result['screenshot'] = (folder / 'inspection.png').relative_to(tools.root).as_posix()
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        (folder / 'inspection.json').write_text(encoded, encoding='utf-8')
        result['inspection_sha256'] = hashlib.sha256((folder / 'inspection.json').read_bytes()).hexdigest()
        return result
    except subprocess.TimeoutExpired:
        raise RuntimeError('Browser inspection exceeded its total deadline; no page inspection is claimed.') from None
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: pass
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None: stream.close()
