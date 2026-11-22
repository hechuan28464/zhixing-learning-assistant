"""Check the configured model API without printing credentials.

Default: list models. A generation request requires --smoke.
Uses only Python's standard library. No student or project data is sent.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def config() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / '.env.local'
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    for name in ('LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL', 'LLM_ENABLE_THINKING'):
        if name in os.environ:
            values[name] = os.environ[name]
    return values


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, 'Redirect refused', headers, fp)


def request(values: dict[str, str], route: str, payload=None, *, timeout=40):
    key = values.get('LLM_API_KEY', '')
    base = values.get('LLM_BASE_URL', '').rstrip('/')
    if not key or not base.startswith('https://'):
        raise ValueError('Configure an HTTPS LLM_BASE_URL and LLM_API_KEY first.')
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(base + route, data=data, headers={
        'Authorization': 'Bearer ' + key,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'LearningAgent-ConnectivityCheck/1.0',
    })
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=max(5,min(300,timeout))) as response:
            result = json.load(response)
            return result, round(time.monotonic() - started, 3)
    except urllib.error.HTTPError as exc:
        # Error responses sometimes echo request details. Never print raw bodies.
        try:
            body = json.loads(exc.read(32768))
            error = body.get('error', {})
            message = error.get('message', 'HTTP request failed') if isinstance(error, dict) else 'HTTP request failed'
        except Exception:
            message = 'HTTP request failed'
        message = str(message).replace(key, '[REDACTED]')
        message = re.sub(r'sk[_-][A-Za-z0-9_-]+', '[REDACTED]', message)
        raise RuntimeError(f'HTTP {exc.code}: {message[:240]}') from None
    except urllib.error.URLError:
        raise RuntimeError('Network connection failed; credentials were not logged.') from None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Send one short generation request.')
    parser.add_argument('--model', help='Override the configured model for this check.')
    parser.add_argument('--max-tokens', type=int, default=128, help='Small output budget for the smoke check.')
    parser.add_argument('--timeout-seconds', type=int, default=40, help='Network wait in seconds (5-300); use 240 for a four-minute probe.')
    parser.add_argument('--disable-thinking', action='store_true', help='Request the optional enable_thinking=false extension.')
    args = parser.parse_args()
    values = config()
    if args.smoke:
        model = args.model or values.get('LLM_MODEL')
        if not model:
            raise ValueError('Select an available model with --model or LLM_MODEL.')
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': 'Reply with exactly OK.'}],
            'max_tokens': max(16, min(args.max_tokens, 512)),
            'stream': False,
        }
        if args.disable_thinking or values.get('LLM_ENABLE_THINKING', '').lower() == 'false':
            payload['enable_thinking'] = False
        result, seconds = request(values, '/chat/completions', payload,timeout=args.timeout_seconds)
        choices = result.get('choices') or []
        reply = str(choices[0].get('message', {}).get('content', '')) if choices else ''
        key = values.get('LLM_API_KEY', '')
        reply = reply.replace(key, '[REDACTED]') if key else reply
        report = {'ok': bool(reply.strip()), 'model': result.get('model', model),
                  'reply': reply[:80], 'seconds': seconds,
                  'finish_reason': choices[0].get('finish_reason') if choices else None,
                  'usage': result.get('usage'),'timeout_seconds':max(5,min(300,args.timeout_seconds))}
    else:
        result, seconds = request(values, '/models',timeout=args.timeout_seconds)
        models = [item['id'] for item in result.get('data', [])
                  if isinstance(item, dict) and isinstance(item.get('id'), str)]
        report = {'ok': bool(models), 'model_count': len(models), 'models': models, 'seconds': seconds}
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True))
        raise SystemExit(1)
