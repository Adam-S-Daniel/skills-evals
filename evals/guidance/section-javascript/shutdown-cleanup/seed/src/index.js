"use strict";

const http = require("node:http");
const { closeServer } = require("./shutdown");

const server = http.createServer((req, res) => res.end("ok"));
server.listen(8080);

process.on("SIGTERM", async () => {
  await closeServer(server);
  process.exit(0);
});
