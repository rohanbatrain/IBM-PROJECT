const passwordInput = document.getElementById("password");
const toggleButton = document.getElementById("togglePassword");

toggleButton.addEventListener("click", () => {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        toggleButton.innerText = "Hide Password";
    } else {
        passwordInput.type = "password";
        toggleButton.innerText = "Show Password";
    }
});

async function analyzePassword() {
    const password = passwordInput.value;

    if (password.length === 0) {
        alert("Please enter a password.");
        return;
    }

    const resultPanel = document.querySelector(".result");
    resultPanel.classList.add("loading");

    const response = await fetch("/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ password })
    });

    const data = await response.json();

    setTimeout(() => {
        document.getElementById("score").innerText = data.score + " / 100";
        document.getElementById("strength").innerText = data.strength;
        document.getElementById("entropy").innerText = data.entropy + " bits";
        document.getElementById("crackTime").innerText = data.crack_time;

        if (data.breached) {
            document.getElementById("breach").innerHTML = "<span class='danger'>BREACHED</span>";
        } else {
            document.getElementById("breach").innerHTML = "<span class='safe'>SAFE</span>";
        }

        document.getElementById("count").innerText = data.count;

        const suggestions = document.getElementById("suggestions");
        suggestions.innerHTML = "";

        if (data.suggestions.length === 0) {
            suggestions.innerHTML = "<li>Excellent password.</li>";
        } else {
            data.suggestions.forEach((item) => {
                const li = document.createElement("li");
                li.innerText = item;
                suggestions.appendChild(li);
            });
        }

        const bar = document.getElementById("strengthBar");
        bar.style.width = data.score + "%";

        if (data.score < 40) {
            bar.style.background = "#ef4444";
        } else if (data.score < 70) {
            bar.style.background = "#f59e0b";
        } else {
            bar.style.background = "#22c55e";
        }

        resultPanel.classList.remove("loading");
    }, 250);

    /*
    document.getElementById("score").innerText = data.score + " / 100";
    */
}
