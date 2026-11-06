"""A scripted stand-in for the Anthropic Messages API (test only).

POST /v1/messages: when the request offers a `Bash` tool, answer with the
next command from SCRIPT (one per tool_result already in the conversation),
then a final text. Requests without a Bash tool (side calls) get "ok".
Every request and every tool_result is logged as one JSON line on stdout.
Never logs a header value: only whether Authorization was present.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = json.load(open(os.environ.get("MOCK_SCRIPT", "/probe/mock_script.json")))
COUNTER = {"n": 0}


def log(**kw):
    print(json.dumps(kw), flush=True)


def blocks(message):
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content or []


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        log(event="request", method="GET", path=self.path)
        self._send_json(404, {"type": "error", "error": {"type": "not_found_error", "message": "mock"}})

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            body = {}
        path = self.path.split("?")[0]
        tools = [t.get("name") for t in body.get("tools", []) if isinstance(t, dict)]
        messages = body.get("messages", [])
        results = [b for m in messages if m.get("role") == "user" for b in blocks(m)
                   if isinstance(b, dict) and b.get("type") == "tool_result"]
        log(event="request", method="POST", path=path, model=body.get("model"),
            stream=bool(body.get("stream")), n_tools=len(tools), has_bash="Bash" in tools,
            n_messages=len(messages), n_tool_results=len(results),
            authorization_present=bool(self.headers.get("authorization")),
            beta=self.headers.get("anthropic-beta"))
        if path.endswith("/count_tokens"):
            return self._send_json(200, {"input_tokens": 10})
        if results:
            last = results[-1]
            content = last.get("content")
            if isinstance(content, list):
                content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
            log(event="tool_result", step=len(results), is_error=bool(last.get("is_error")),
                content=str(content)[:4000])
        step = len(results)
        if "Bash" in tools and step < len(SCRIPT):
            item = SCRIPT[step]
            if isinstance(item, str):
                item = {"name": "Bash", "input": {"command": item, "description": "mock step"}}
            block = {"type": "tool_use", "id": f"toolu_mock{COUNTER['n']:04d}", "name": item["name"], "input": {}}
            payload = json.dumps(item["input"])
            stop = "tool_use"
        else:
            block = {"type": "text", "text": ""}
            payload = "ok" if not ("Bash" in tools) else "mock: all scripted steps done"
            stop = "end_turn"
        COUNTER["n"] += 1
        model = body.get("model") or "mock-model"
        usage = {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 0,
                 "cache_read_input_tokens": 0}
        if not body.get("stream"):
            content = dict(block)
            if block["type"] == "tool_use":
                content["input"] = json.loads(payload)
            else:
                content["text"] = payload
            return self._send_json(200, {"id": f"msg_mock{COUNTER['n']}", "type": "message",
                                         "role": "assistant", "model": model, "content": [content],
                                         "stop_reason": stop, "stop_sequence": None, "usage": usage})
        delta = ({"type": "input_json_delta", "partial_json": payload} if block["type"] == "tool_use"
                 else {"type": "text_delta", "text": payload})
        events = [
            ("message_start", {"type": "message_start", "message": {
                "id": f"msg_mock{COUNTER['n']}", "type": "message", "role": "assistant", "model": model,
                "content": [], "stop_reason": None, "stop_sequence": None, "usage": usage}}),
            ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": block}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                               "usage": {"output_tokens": 5}}),
            ("message_stop", {"type": "message_stop"}),
        ]
        data = b"".join(f"event: {name}\ndata: {json.dumps(obj)}\n\n".encode() for name, obj in events)
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
