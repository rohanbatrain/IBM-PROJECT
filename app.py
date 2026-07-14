from flask import Flask, render_template, request, jsonify
import hashlib
import requests
import math
import re
import os

app = Flask(__name__, template_folder="templates", static_folder="templates/static")

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

    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 25
    else:
        suggestions.append("Add special characters.")

    if score < 40:
        strength = "Weak"
    elif score < 70:
        strength = "Medium"
    elif score < 90:
        strength = "Strong"
    else:
        strength = "Very Strong"

    return score, strength, suggestions


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

    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        charset += 32

    if charset == 0:
        return 0

    entropy = len(password) * math.log2(charset)

    return round(entropy, 2)


# -----------------------------
# Crack Time Estimation
# -----------------------------
def crack_time(entropy):

    guesses_per_second = 1_000_000_000

    seconds = (2 ** entropy) / guesses_per_second

    if seconds < 60:
        return f"{int(seconds)} seconds"

    elif seconds < 3600:
        return f"{int(seconds/60)} minutes"

    elif seconds < 86400:
        return f"{int(seconds/3600)} hours"

    elif seconds < 31536000:
        return f"{int(seconds/86400)} days"

    else:
        return f"{int(seconds/31536000)} years"


# -----------------------------
# Breach Detection
# -----------------------------
def check_breach(password):

    sha1password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()

    prefix = sha1password[:5]
    suffix = sha1password[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return False, 0

    hashes = (line.split(":") for line in response.text.splitlines())

    for h, count in hashes:
        if h == suffix:
            return True, count

    return False, 0


# -----------------------------
# Home Page
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# Analyze Password
# -----------------------------
@app.route("/analyze", methods=["POST"])
def analyze():

    data = request.get_json()

    password = data["password"]

    score, strength, suggestions = calculate_strength(password)

    entropy = calculate_entropy(password)

    time = crack_time(entropy)

    breached, count = check_breach(password)

    return jsonify({

        "score": score,
        "strength": strength,
        "entropy": entropy,
        "crack_time": time,
        "breached": breached,
        "count": count,
        "suggestions": suggestions

    })


if __name__ == "__main__":
    app.run(debug=True)

