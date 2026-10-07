const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const backend = path.join(__dirname, "..", "backend");
const python =
  process.platform === "win32"
    ? path.join(backend, "venv", "Scripts", "python.exe")
    : path.join(backend, "venv", "bin", "python");

if (!fs.existsSync(python)) {
  console.error("");
  console.error("Python virtualenv not found.");
  console.error("From the project root, run: npm run setup");
  console.error("Or create it manually:");
  console.error("  cd backend");
  console.error("  python -m venv venv");
  console.error("  venv\\Scripts\\activate");
  console.error("  pip install -r requirements.txt");
  console.error("");
  process.exit(1);
}

const child = spawnSync(python, ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], {
  cwd: backend,
  stdio: "inherit",
});

process.exit(child.status ?? 1);
