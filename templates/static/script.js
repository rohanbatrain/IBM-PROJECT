const $ = (id) => document.getElementById(id);

const input = $("password");
const results = $("results");
const errorBox = $("error");
const meter = document.querySelector(".meter");

const LEVELS = { Weak: 1, Medium: 2, Strong: 3, "Very Strong": 4 };

// Theme -------------------------------------------------------------------
const root = document.documentElement;
root.dataset.theme = localStorage.getItem("theme") || "dark";

$("themeToggle").addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", root.dataset.theme);
});

// Show / hide -------------------------------------------------------------
$("togglePassword").addEventListener("click", (e) => {
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    e.currentTarget.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    input.focus();
});

// Live analysis -----------------------------------------------------------
let timer;
let latest = 0;

input.addEventListener("input", () => {
    clearTimeout(timer);
    if (!input.value) return reset();
    timer = setTimeout(analyze, 300);
});

function reset() {
    results.hidden = true;
    errorBox.hidden = true;
    meter.removeAttribute("data-level");
    $("strength").innerText = "—";
    $("score").innerText = "0 / 100";
}

async function analyze() {
    const password = input.value;
    const ticket = ++latest;

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password }),
        });
        const data = await response.json();

        if (ticket !== latest) return;   // a newer keystroke already won

        if (!response.ok) {
            errorBox.innerText = data.error || "Analysis failed.";
            errorBox.hidden = false;
            results.hidden = true;
            return;
        }

        errorBox.hidden = true;
        render(data);
    } catch {
        if (ticket !== latest) return;
        errorBox.innerText = "Could not reach the analyzer service.";
        errorBox.hidden = false;
    }
}

function render(data) {
    $("strength").innerText = data.strength;
    $("score").innerText = `${data.score} / 100`;
    meter.dataset.level = LEVELS[data.strength] || 1;

    $("entropy").innerText = `${data.entropy} bits`;
    $("crackTime").innerText = data.crack_time;

    renderBreach(data);
    renderSuggestions(data.suggestions);

    results.hidden = false;
}

function renderBreach({ breach_check_available, breached, count }) {
    const banner = $("breachBanner");
    banner.hidden = false;

    if (!breach_check_available) {
        banner.className = "banner warn";
        banner.innerHTML = "<strong>Breach status unknown</strong>Could not reach Have I Been Pwned — check your connection.";
    } else if (breached) {
        banner.className = "banner danger";
        banner.innerHTML = `<strong>Found in ${count.toLocaleString()} data breaches</strong>This password is publicly known. Do not use it anywhere.`;
    } else {
        banner.className = "banner safe";
        banner.innerHTML = "<strong>No known breaches</strong>This password was not found in any exposed dataset.";
    }
}

function renderSuggestions(items) {
    const list = $("suggestions");
    list.innerHTML = "";

    const entries = items.length ? items : ["Nothing to improve — this is a strong password."];
    for (const text of entries) {
        const li = document.createElement("li");
        li.innerText = text;
        list.appendChild(li);
    }
}
