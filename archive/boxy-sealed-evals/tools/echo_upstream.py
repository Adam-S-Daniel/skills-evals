import http.server, json, sys
want = "Bearer " + open("/run/secrets/oauth.env").read().strip().split("=", 1)[1]
class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0); self.rfile.read(n)
        a = self.headers.get("authorization")
        rep = {"authorization_equals_sidecar_file": a == want, "authorization_equals_dummy": a == "Bearer dummy-not-a-token", "x_api_key_present": bool(self.headers.get("x-api-key")), "host": self.headers.get("host")}
        print(json.dumps(rep), flush=True)
        body = json.dumps(rep).encode(); self.send_response(200); self.send_header("content-type", "application/json"); self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
http.server.HTTPServer(("0.0.0.0", 8443), H).serve_forever()
