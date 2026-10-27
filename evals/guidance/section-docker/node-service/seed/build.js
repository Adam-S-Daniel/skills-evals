const fs = require("fs");
fs.mkdirSync("dist", { recursive: true });
fs.copyFileSync("server.js", "dist/server.js");
