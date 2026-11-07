"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");

function closeServer(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

module.exports = { closeServer };
