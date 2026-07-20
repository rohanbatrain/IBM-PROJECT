"""Password strength & breach detection — Flask app.

Runs as a normal script (`python app.py`) or as a frozen PyInstaller binary.
"""

from flask import Flask, render_template, request, jsonify
import hashlib
import requests
import math
import re
import os
import sys


def resource_path(relative):
    """Resolve a bundled data file, both frozen and from source."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("templates/static"),
)

MAX_PASSWORD_LENGTH = 256

# Patterns that make a password far weaker than its raw character mix suggests.
COMMON_PASSWORDS = {
    "password", "123456", "123456789", "qwerty", "abc123", "letmein",
    "monkey", "iloveyou", "admin", "welcome", "login", "passw0rd",
    "football", "dragon", "sunshine", "master", "hello", "freedom",
}

KEYBOARD_RUNS = ("qwerty", "asdfgh", "zxcvbn", "qazwsx", "1qaz2wsx")


# -----------------------------
# Password Strength Calculator
# -----------------------------
def calculate_strength(password):
    score = 0
    suggestions = []

    length = len(password)

    if length >= 8:
        score += 15
    else:
        suggestions.append("Use at least 8 characters.")

    if length >= 12:
        score += 15
    else:
        suggestions.append("12 or more characters is significantly stronger.")

    if re.search(r"[A-Z]", password):
        score += 15
    else:
        suggestions.append("Add uppercase letters.")

    if re.search(r"[a-z]", password):
        score += 15
    else:
        suggestions.append("Add lowercase letters.")

    if re.search(r"\d", password):
        score += 15
    else:
        suggestions.append("Add numbers.")

    if re.search(r"[^A-Za-z0-9]", password):
        score += 25
    else:
        suggestions.append("Add special characters.")

    # Penalties: a password can satisfy every rule above and still be guessable.
    score -= penalty_for_patterns(password, suggestions)
    score = max(0, min(100, score))

    if score < 40:
        strength = "Weak"
    elif score < 70:
        strength = "Medium"
    elif score < 90:
        strength = "Strong"
    else:
        strength = "Very Strong"

    return score, strength, suggestions


def penalty_for_patterns(password, suggestions):
    """Subtract points for dictionary words, repeats, sequences and keyboard runs."""
    penalty = 0
    lowered = password.lower()
    letters_only = re.sub(r"[^a-z]", "", lowered)

    if lowered in COMMON_PASSWORDS or letters_only in COMMON_PASSWORDS:
        penalty += 40
        suggestions.append("This is a very common password — pick something unique.")
    elif any(word in lowered for word in COMMON_PASSWORDS if len(word) >= 5):
        penalty += 20
        suggestions.append("Avoid dictionary words and common passwords.")

    if re.search(r"(.)\1{2,}", password):
        penalty += 10
        suggestions.append("Avoid repeating the same character.")

    if has_sequence(lowered):
        penalty += 10
        suggestions.append("Avoid sequences like 'abcd' or '1234'.")

    if any(run in lowered for run in KEYBOARD_RUNS):
        penalty += 15
        suggestions.append("Avoid keyboard patterns like 'qwerty'.")

    if re.fullmatch(r"[A-Za-z]+\d{1,4}!?", password):
        penalty += 10
        suggestions.append("'Word + digits' is a pattern attackers try first.")

    return penalty


def has_sequence(text, run=4):
    """True if `text` contains `run` consecutive ascending/descending characters."""
    streak = 1
    direction = 0

    for i in range(1, len(text)):
        delta = ord(text[i]) - ord(text[i - 1])
        if delta in (1, -1) and delta == direction:
            streak += 1
        elif delta in (1, -1):
            direction, streak = delta, 2
        else:
            direction, streak = 0, 1

        if streak >= run:
            return True

    return False


# -----------------------------
# Entropy Calculator
# -----------------------------
def calculate_entropy(password):
    charset = 0

    if re.search(r"[a-z]", password):
        charset += 26

    if re.search(r"[A-Z]", password):
        charset += 26

    if re.search(r"\d", password):
        charset += 10

    if re.search(r"[^A-Za-z0-9]", password):
        charset += 33

    if charset == 0:
        return 0

    return round(len(password) * math.log2(charset), 2)


# -----------------------------
# Crack Time Estimation
# -----------------------------
GUESSES_PER_SECOND = 1_000_000_000

TIME_UNITS = (
    (1, "seconds"),
    (60, "minutes"),
    (3600, "hours"),
    (86400, "days"),
    (31536000, "years"),
)


def crack_time(entropy):
    """Human-readable crack time.

    Works in log space so long passwords don't overflow on 2 ** entropy.
    """
    if entropy <= 0:
        return "instantly"

    log10_seconds = entropy * math.log10(2) - math.log10(GUESSES_PER_SECOND)

    if log10_seconds > 15:  # past this the exact figure is meaningless anyway
        return "longer than the age of the universe"

    seconds = 10 ** log10_seconds
    if seconds < 1:
        return "instantly"

    divisor, unit = TIME_UNITS[0]
    for limit, name in TIME_UNITS:
        if seconds >= limit:
            divisor, unit = limit, name

    value = int(seconds / divisor)
    return f"{value:,} {unit[:-1] if value == 1 else unit}"


# -----------------------------
# Breach Detection
# -----------------------------
def check_breach(password):
    """Query HaveIBeenPwned via k-anonymity — only a 5-char hash prefix is sent.

    Returns (breached, count, check_succeeded).
    """
    sha1password = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1password[:5], sha1password[5:]

    try:
        response = requests.get(
            f"https://api.pwnedpasswords.com/range/{prefix}", timeout=10
        )
        response.raise_for_status()
    except requests.RequestException:
        return False, 0, False

    for line in response.text.splitlines():
        h, _, count = line.partition(":")
        if h == suffix:
            return True, int(count) if count.strip().isdigit() else 0, True

    return False, 0, True


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not isinstance(data.get("password"), str):
        return jsonify({"error": "Body must be JSON with a 'password' string."}), 400

    password = data["password"]

    if not password:
        return jsonify({"error": "Password must not be empty."}), 400

    if len(password) > MAX_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at most {MAX_PASSWORD_LENGTH} characters."}), 400

    score, strength, suggestions = calculate_strength(password)
    entropy = calculate_entropy(password)
    breached, count, checked = check_breach(password)

    # A password in a public breach corpus is guessable regardless of its shape.
    if breached:
        score = min(score, 20)
        strength = "Weak"
        suggestions.insert(0, "This password has been exposed in a breach — change it everywhere.")

    return jsonify({
        "score": score,
        "strength": strength,
        "entropy": entropy,
        "crack_time": crack_time(entropy),
        "breached": breached,
        "count": count,
        "breach_check_available": checked,
        "suggestions": suggestions,
    })


def main():
    """Entry point for the packaged binary: serve locally, then open a browser."""
    import threading
    import webbrowser
    from waitress import serve

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://{host}:{port}/"

    print(f"Password Analyzer running at {url}\nPress Ctrl+C to stop.")

    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        serve(app, host=host, port=port, threads=8)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
