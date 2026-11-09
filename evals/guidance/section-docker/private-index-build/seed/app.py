from http.server import BaseHTTPRequestHandler, HTTPServer

import acme_metrics  # served by the team's private package index


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(acme_metrics.render().encode())


HTTPServer(("", 8000), Handler).serve_forever()
