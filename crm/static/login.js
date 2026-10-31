document
  .querySelector("#login-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.target.querySelector("button");
    button.disabled = true;
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          password: new FormData(event.target).get("password"),
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "Não foi possível entrar");
      location.href = "/";
    } catch (e) {
      document.querySelector("#login-error").textContent = e.message;
    } finally {
      button.disabled = false;
    }
  });
