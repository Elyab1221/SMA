document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("form");
    if (!form) return;

    const textarea = document.getElementById("text");
    const charCount = document.getElementById("charCount");
    const submitBtn = document.getElementById("submitBtn");
    const statusBox = document.getElementById("status");
    const remainingCount = document.getElementById("remainingCount");

    // Real-time character counter
    if (textarea && charCount) {
        textarea.addEventListener("input", () => {
            const len = textarea.value.length;
            charCount.textContent = len;
            if (len > 950) {
                charCount.style.color = "#dc2626";
                charCount.style.fontWeight = "600";
            } else {
                charCount.style.color = "";
                charCount.style.fontWeight = "";
            }
        });
    }

    // AJAX form submission
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const messageText = textarea.value.trim();
        if (!messageText) {
            showStatus("Please write a message before submitting.", false);
            return;
        }

        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = "Delivering anonymously...";
        hideStatus();

        try {
            const res = await fetch("/api/messages", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF": form.dataset.csrf
                },
                body: JSON.stringify({ text: messageText })
            });

            if (res.redirected) {
                window.location = res.url;
                return;
            }

            const data = await res.json();

            if (res.ok) {
                showStatus("✓ " + (data.message || "Message sent anonymously. Your identity was not attached."), true);
                form.reset();
                if (charCount) charCount.textContent = "0";
                
                if (typeof data.remaining !== "undefined" && remainingCount) {
                    remainingCount.textContent = data.remaining;
                    if (data.remaining <= 0) {
                        submitBtn.disabled = true;
                        submitBtn.textContent = "Daily limit reached";
                        return;
                    }
                }
            } else {
                showStatus("✕ " + (data.error || "Failed to deliver message. Please try again."), false);
            }
        } catch (err) {
            showStatus("Network connection issue. Please check your network and try again.", false);
        } finally {
            if (submitBtn.textContent !== "Daily limit reached") {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    });

    function showStatus(msg, isSuccess) {
        if (!statusBox) return;
        statusBox.textContent = msg;
        statusBox.className = "status-box " + (isSuccess ? "status-success" : "status-error");
        statusBox.style.display = "block";
    }

    function hideStatus() {
        if (!statusBox) return;
        statusBox.style.display = "none";
    }
});