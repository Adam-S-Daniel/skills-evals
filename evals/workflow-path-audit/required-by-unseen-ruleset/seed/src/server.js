const http = require("node:http");
const { route } = require("./routes");

const server = http.createServer((req, res) => {
  const { status, body } = route(req.url);
  res.writeHead(status, { "content-type": "text/plain" });
  res.end(body);
});

server.listen(process.env.PORT || 8080);
