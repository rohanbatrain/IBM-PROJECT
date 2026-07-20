const { app, BrowserWindow, shell, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const net = require("net");
const http = require("http");

const isDev = !app.isPackaged;
let backend = null;
let win = null;

/** Ask the OS for a free port so two instances never collide. */
function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

function backendPath() {
  const exe = process.platform === "win32" ? "password-analyzer.exe" : "password-analyzer";
  return isDev
    ? path.join(__dirname, "..", "dist", exe)
    : path.join(process.resourcesPath, "backend", exe);
}

function startBackend(port) {
  backend = spawn(backendPath(), [], {
    env: { ...process.env, PORT: String(port), HOST: "127.0.0.1", NO_BROWSER: "1" },
    stdio: isDev ? "inherit" : "ignore",
    windowsHide: true,
  });

  backend.on("error", (err) => fail(`Could not start the analyzer service.\n\n${err.message}`));

  backend.on("exit", (code) => {
    backend = null;
    // A crash before quit means the UI is dead weight — surface it instead of hanging.
    if (code !== 0 && code !== null && !app.isQuitting) {
      fail(`The analyzer service stopped unexpectedly (exit code ${code}).`);
    }
  });
}

/** Poll until the server answers, so we never show a blank window. */
function waitForServer(url, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;

  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        if (Date.now() > deadline) reject(new Error("Timed out waiting for the analyzer service."));
        else setTimeout(attempt, 200);
      });
    };
    attempt();
  });
}

function fail(message) {
  dialog.showErrorBox("Password Analyzer", message);
  app.exit(1);
}

function createWindow(url) {
  win = new BrowserWindow({
    width: 760,
    height: 900,
    minWidth: 420,
    minHeight: 560,
    show: false,
    backgroundColor: "#161c26",
    title: "Password Analyzer",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  });

  win.once("ready-to-show", () => win.show());

  // Keep the product name in the title bar rather than the page's <title>.
  win.on("page-title-updated", (event) => event.preventDefault());
  win.loadURL(url);

  // External links belong in the real browser, never in this window.
  win.webContents.setWindowOpenHandler(({ url: target }) => {
    shell.openExternal(target);
    return { action: "deny" };
  });

  win.webContents.on("will-navigate", (event, target) => {
    if (!target.startsWith(url)) {
      event.preventDefault();
      shell.openExternal(target);
    }
  });

  win.on("closed", () => (win = null));
}

// One instance only — a second launch focuses the existing window.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(async () => {
    try {
      const port = await freePort();
      const url = `http://127.0.0.1:${port}/`;
      startBackend(port);
      await waitForServer(url);
      createWindow(url);

      app.on("activate", () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow(url);
      });
    } catch (err) {
      fail(err.message);
    }
  });
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  app.isQuitting = true;
});

// Never leave an orphaned server process behind.
app.on("quit", () => backend && backend.kill());
process.on("exit", () => backend && backend.kill());
