const http = require("http");
const { Client } = require("pg");

const port = 3000;

async function queryDatabase() {
  const client = new Client({
    host: process.env.DB_HOST || "db",
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER || "appuser",
    password: process.env.DB_PASSWORD || "devpass123",
    database: process.env.DB_NAME || "appdb",
    connectionTimeoutMillis: 3000
  });

  await client.connect();

  try {
    const result = await client.query(
      "SELECT id, message FROM messages ORDER BY id DESC LIMIT 5"
    );
    return result.rows;
  } finally {
    await client.end();
  }
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.url === "/health") {
      await queryDatabase();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", database: "connected" }));
      return;
    }

    if (req.url !== "/") {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const rows = await queryDatabase();
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(
      `<h1>Docker Task 4</h1>
       <p>App connected to PostgreSQL using Docker DNS hostname: db</p>
       <h2>Messages</h2>
       <ul>${rows.map(row =>
         `<li>${row.id}: ${row.message.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</li>`
       ).join("")}</ul>`
    );
  } catch (error) {
    console.error(error);
    res.writeHead(503, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Database unavailable" }));
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`App listening on port ${port}`);
});
