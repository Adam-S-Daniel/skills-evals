const http = require("http");

http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.end("ok");
    return;
  }
  res.end(JSON.stringify({ status: "green" }));
}).listen(8080);
