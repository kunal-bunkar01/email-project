const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const backend = path.join(root, "backend");
const frontend = path.join(root, "frontend");
const venvPython =
  process.platform === "win32"
    ? path.join(backend, "venv", "Scripts", "python.exe")
    : path.join(backend, "venv", "bin", "python");

function run(command, cwd) {
  const result = spawnSync(command, { cwd, stdio: "inherit", shell: true });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

if (!fs.existsSync(venvPython)) {
  const created = spawnSync("python -m venv venv", { cwd: backend, stdio: "inherit", shell: true });
  if (created.status !== 0) {
    run("py -3 -m venv venv", backend);
  }
}

run(`"${venvPython}" -m pip install --upgrade pip`, backend);
const pip = spawnSync(`"${venvPython}" -m pip install -r requirements.txt`, {
  cwd: backend,
  stdio: "inherit",
  shell: true,
});
if (pip.status !== 0) {
  console.log("pip could not finish (this happens if OneDrive locks a file). Retrying once.");
  run(`"${venvPython}" -m pip install -r requirements.txt`, backend);
}
run("npm install", frontend);
console.log("");
console.log("Setup complete. Start the app with: npm run dev");
console.log("Demo mode is on by default, so you do not need API keys yet.");
