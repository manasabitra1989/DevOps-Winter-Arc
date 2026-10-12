const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "dist");

const types = {
  ".html": "text/html",
  ".css": "text/css"
};

http.createServer((req, res) => {
  const pathname = new URL(req.url, "http://localhost").pathname;
  const requested = pathname === "/" ? "index.html" : pathname.slice(1);
  const file = path.join(root, requested);

  if (!file.startsWith(root + path.sep) && file !== path.join(root, "index.html")) {
    res.writeHead(403);
    return res.end("Forbidden");
  }

  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404);
      return res.end("Not Found");
    }

    res.writeHead(200, {
      "Content-Type": types[path.extname(file)] || "application/octet-stream"
    });
    res.end(data);
  });
}).listen(8080, "0.0.0.0", () => {
  console.log("Server listening on port 8080");
});
