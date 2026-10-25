#!/usr/bin/env python3
"""Optional standalone chat client. Offline by default; no agent tools executed."""
import argparse
import http.client
import json
import os
import re
import sys
from urllib.parse import urlsplit


def endpoint(value):
    if not isinstance(value, str) or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("invalid endpoint")
    p = urlsplit(value)
    if (p.scheme not in {"http", "https"} or p.hostname not in {"127.0.0.1", "::1"}
            or p.username is not None or p.password is not None
            or p.path != "/v1" or p.query or p.fragment
            or any(c in value for c in "\\%?#")):
        raise ValueError("invalid endpoint")
    port = p.port or (443 if p.scheme == "https" else 80)
    if not 1 <= port <= 65535 or p.port == 0 or p.netloc.endswith(":"):
        raise ValueError("invalid port")
    authority = "[::1]" if p.hostname == "::1" else "127.0.0.1"
    if p.port is not None:
        authority += ":" + str(p.port)
    if p.netloc != authority:
        raise ValueError("ambiguous endpoint")
    return p.scheme, p.hostname, port


def request_chat(base, model, prompt, token="", factory=None):
    scheme, host, port = endpoint(base)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", model):
        raise ValueError("invalid model")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > 8192:
        raise ValueError("invalid prompt")
    if token and (len(token) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        raise ValueError("invalid token")
    # http.client ignores proxy environment variables and does not follow redirects.
    transport = factory or (http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection)
    conn = transport(host, port, timeout=15)
    try:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                           "stream": False, "max_tokens": 256}).encode("utf-8")
        conn.request("POST", "/v1/chat/completions", body=body, headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("request rejected")
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("response too large")
        payload = json.loads(raw)
        text = payload["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("unsupported response")
        return text
    finally:
        conn.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    p.add_argument("--model", required=True)
    p.add_argument("--request", action="store_true", help="Read a prompt from stdin and explicitly call the local endpoint")
    a = p.parse_args(argv)
    try:
        endpoint(a.base_url)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", a.model):
            raise ValueError("invalid model")
        if not a.request:
            print(json.dumps({"mode": "offline", "network_called": False,
                              "runtime_required": "Python 3.10+; no Ruflo or FreeLLMAPI imports",
                              "inference_verified": False,
                              "limitation": "A loopback server may forward data to cloud; billing and privacy are unverified."}))
            return 0
        if os.environ.get("AGENT_LOCAL_PROCESSING_CONFIRMED") != "1":
            raise ValueError("local processing must be reviewed and confirmed")
        prompt = sys.stdin.buffer.read(8193)
        if len(prompt) > 8192:
            raise ValueError("prompt too large")
        result = request_chat(a.base_url, a.model, prompt.decode("utf-8"), os.environ.get("AGENT_API_KEY", ""))
        print(json.dumps({"content": result}, ensure_ascii=True))
        return 0
    except (ValueError, OSError, http.client.HTTPException, KeyError, IndexError, TypeError, RecursionError):
        # Never echo prompt, token, server body, endpoint or exception text.
        print(json.dumps({"error": "request_or_configuration_rejected", "retry_attempted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
