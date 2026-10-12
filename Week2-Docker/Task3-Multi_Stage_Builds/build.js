const fs = require("fs");
const path = require("path");

const source = path.join(__dirname, "src");
const output = path.join(__dirname, "dist");

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
fs.cpSync(source, output, { recursive: true });

console.log("Build complete: website files copied to dist/");
