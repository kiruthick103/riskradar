/**
 * RiskRadar Unified Local Runner
 * Concurrently boots both the FastAPI backend and Vite frontend with unified logging.
 */
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Locate backend and frontend directories
let backendDir = path.resolve(__dirname, "backend");
let frontendDir = path.resolve(__dirname, "frontend");

if (!fs.existsSync(backendDir)) {
  backendDir = path.resolve(__dirname, "RISK DEMO", "backend");
}
if (!fs.existsSync(frontendDir)) {
  frontendDir = path.resolve(__dirname, "RISK DEMO", "frontend");
}

console.log("\x1b[36m%s\x1b[0m", "=============================================================");
console.log("\x1b[36m%s\x1b[0m", " 🛡️  RiskRadar AI Platform - Local Full-Stack Orchestration");
console.log("\x1b[36m%s\x1b[0m", " Backend:  http://127.0.0.1:8000  (FastAPI + SQLite)");
console.log("\x1b[36m%s\x1b[0m", " Frontend: http://127.0.0.1:5173  (React + Vite)");
console.log("\x1b[36m%s\x1b[0m", " Swagger:  http://127.0.0.1:8000/docs");
console.log("\x1b[36m%s\x1b[0m", "=============================================================");

const children = [];

function killChildren() {
  console.log("\n\x1b[33mShutting down RiskRadar services...\x1b[0m");
  for (const child of children) {
    if (child && !child.killed) {
      try {
        if (process.platform === "win32" && child.pid) {
          spawn("taskkill", ["/pid", child.pid.toString(), "/T", "/F"], { stdio: "ignore" });
        } else {
          child.kill("SIGTERM");
        }
      } catch (err) {
        // ignore
      }
    }
  }
  process.exit(0);
}

process.on("SIGINT", killChildren);
process.on("SIGTERM", killChildren);

// Start Python Backend
console.log("\x1b[32m[RiskRadar]\x1b[0m Starting FastAPI backend on http://127.0.0.1:8000 ...");
const pythonCmd = process.platform === "win32" ? "python" : "python3";
const backendProcess = spawn(
  pythonCmd,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
  {
    cwd: backendDir,
    shell: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, PYTHONUNBUFFERED: "1" }
  }
);
children.push(backendProcess);

backendProcess.stdout.on("data", (data) => {
  const lines = data.toString().trim().split("\n");
  lines.forEach((line) => {
    if (line) console.log(`\x1b[34m[Backend]\x1b[0m ${line}`);
  });
});

backendProcess.stderr.on("data", (data) => {
  const lines = data.toString().trim().split("\n");
  lines.forEach((line) => {
    if (line) console.error(`\x1b[31m[Backend Error]\x1b[0m ${line}`);
  });
});

backendProcess.on("exit", (code) => {
  console.log(`\x1b[33m[Backend]\x1b[0m Process exited with code ${code}`);
});

// Start Vite Frontend
console.log("\x1b[32m[RiskRadar]\x1b[0m Starting Vite frontend on http://127.0.0.1:5173 ...");
const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";
const frontendProcess = spawn(
  npmCmd,
  ["run", "dev", "--", "--host", "127.0.0.1"],
  {
    cwd: frontendDir,
    shell: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env
  }
);
children.push(frontendProcess);

frontendProcess.stdout.on("data", (data) => {
  const lines = data.toString().trim().split("\n");
  lines.forEach((line) => {
    if (line) console.log(`\x1b[32m[Frontend]\x1b[0m ${line}`);
  });
});

frontendProcess.stderr.on("data", (data) => {
  const lines = data.toString().trim().split("\n");
  lines.forEach((line) => {
    if (line) console.error(`\x1b[33m[Frontend Info]\x1b[0m ${line}`);
  });
});

frontendProcess.on("exit", (code) => {
  console.log(`\x1b[33m[Frontend]\x1b[0m Process exited with code ${code}`);
});
