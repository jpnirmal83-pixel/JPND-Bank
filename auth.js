// Authentication & registration logic for JPND Bank
// Relies on helpers from storage.js

(function () {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");

  if (loginForm) {
    initLoginPage();
  }

  if (registerForm) {
    initRegisterPage();
  }

  function initLoginPage() {
    const tabs = document.querySelectorAll(".tab[data-role]");
    const loginRoleInput = document.getElementById("loginRole");
    const loginError = document.getElementById("loginError");
    const identifierInput = document.getElementById("loginEmail");
    const passwordInput = document.getElementById("loginPassword");
    const passwordToggle = document.getElementById("loginPasswordToggle");

    // Password toggle functionality
    if (passwordToggle && passwordInput) {
      passwordToggle.addEventListener("click", () => {
        const type =
          passwordInput.getAttribute("type") === "password" ? "text" : "password";
        passwordInput.setAttribute("type", type);
      });
    }

    // Configure role based on query (?role=admin for admin login)
    const params = new URLSearchParams(window.location.search);
    const roleFromUrl = (params.get("role") || "user").toLowerCase();
    if (loginRoleInput) {
      loginRoleInput.value = roleFromUrl === "admin" ? "admin" : "user";
    }
    const titleEl = document.querySelector(".auth-title");
    const subtitleEl = document.querySelector(".auth-subtitle");
    if (roleFromUrl === "admin") {
      if (titleEl) titleEl.textContent = "Admin Login";
      if (subtitleEl) subtitleEl.textContent = "Sign in to manage customer accounts.";
    }

    // Always clear fields on load so previous data is not kept
    if (identifierInput) identifierInput.value = "";
    if (passwordInput) passwordInput.value = "";

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        loginRoleInput.value = tab.getAttribute("data-role");
        // Clear fields and errors when switching role
        if (identifierInput) identifierInput.value = "";
        if (passwordInput) passwordInput.value = "";
        hideError(loginError);
      });
    });

    // Reset button to clear all login inputs and messages
    const resetBtn = document.getElementById("loginResetBtn");
    if (resetBtn && identifierInput && passwordInput) {
      resetBtn.addEventListener("click", () => {
        identifierInput.value = "";
        passwordInput.value = "";
        hideError(loginError);
        // revert to customer login tab
        tabs.forEach((t) => t.classList.remove("active"));
        const userTab = document.querySelector('.tab[data-role="user"]');
        if (userTab) userTab.classList.add("active");
        loginRoleInput.value = "user";
      });
    }

    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const identifier = identifierInput.value.trim();
      const password = passwordInput.value;
      const role = loginRoleInput.value || "user";

      hideError(loginError);

      if (!identifier || !password) {
        return showError(loginError, "Please enter both identifier and password.");
      }

      const user = getUserByAccountOrEmail(identifier);
      if (!user) {
        return showError(loginError, "Account not found. Please check details.");
      }

      const isAdminLogin = role === "admin";
      if (isAdminLogin && !user.isAdmin) {
        return showError(loginError, "This account is not an admin account.");
      }

      if (user.password !== password) {
        return showError(loginError, "Incorrect password. Try again.");
      }

      // Set session and redirect
      setSession({
        accountNumber: user.accountNumber,
        isAdmin: !!user.isAdmin,
      });

      if (isAdminLogin) {
        window.location.href = "admin.html";
      } else {
        window.location.href = "dashboard.html";
      }
    });
  }

  function initRegisterPage() {
    const errorBox = document.getElementById("registerError");
    const successBox = document.getElementById("registerSuccess");
    const titleEl = document.getElementById("registerTitle");
    const subtitleEl = document.getElementById("registerSubtitle");
    const depositGroup = document.getElementById("initialDepositGroup");
    const submitBtn = document.getElementById("registerSubmitBtn");
    const captchaQuestion = document.getElementById("captchaQuestion");
    const captchaInput = document.getElementById("captchaInput");
    const resetBtn = document.getElementById("registerResetBtn");

    // Simple captcha: a + b = ?
    function generateCaptcha() {
      if (!captchaQuestion || !captchaInput) return;
      const a = Math.floor(Math.random() * 10) + 1;
      const b = Math.floor(Math.random() * 10) + 1;
      captchaQuestion.textContent = ` (What is ${a} + ${b}?)`;
      captchaQuestion.dataset.answer = String(a + b);
      captchaInput.value = "";
    }

    // Configure UI based on mode (?mode=register or ?mode=open)
    const params = new URLSearchParams(window.location.search);
    const mode = (params.get("mode") || "register").toLowerCase();

    if (mode === "open") {
      if (titleEl) titleEl.textContent = "Open a new account";
      if (subtitleEl)
        subtitleEl.textContent =
          "Create your secure JPND Bank internet banking account.";
      if (depositGroup) depositGroup.classList.remove("hidden");
      if (submitBtn) submitBtn.textContent = "Submit";
    } else {
      if (titleEl) titleEl.textContent = "Registration form";
      if (subtitleEl) subtitleEl.textContent = "";
      if (depositGroup) depositGroup.classList.add("hidden");
      if (submitBtn) submitBtn.textContent = "Register";
    }

    generateCaptcha();

    // Password toggle functionality
    const passwordToggle = document.getElementById("passwordToggle");
    const confirmPasswordToggle = document.getElementById("confirmPasswordToggle");
    const passwordField = document.getElementById("password");
    const confirmPasswordField = document.getElementById("confirmPassword");

    if (passwordToggle && passwordField) {
      passwordToggle.addEventListener("click", () => {
        const type =
          passwordField.getAttribute("type") === "password" ? "text" : "password";
        passwordField.setAttribute("type", type);
      });
    }

    if (confirmPasswordToggle && confirmPasswordField) {
      confirmPasswordToggle.addEventListener("click", () => {
        const type =
          confirmPasswordField.getAttribute("type") === "password"
            ? "text"
            : "password";
        confirmPasswordField.setAttribute("type", type);
      });
    }

    // Reset button to clear all fields and messages
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (registerForm) registerForm.reset();
        hideError(errorBox);
        hideError(successBox);
        generateCaptcha();
      });
    }

    registerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      hideError(errorBox);
      hideError(successBox);

      const name = document.getElementById("name").value.trim();
      const email = document.getElementById("email").value.trim();
      const phone = document.getElementById("phone").value.trim();
      const password = document.getElementById("password").value;
      const confirmPassword = document.getElementById("confirmPassword").value;
      const depositInput = document.getElementById("initialDeposit");
      let initialDeposit = 0;
      if (depositInput && !depositInput.classList.contains("hidden")) {
        const raw = (depositInput.value || "").trim();
        if (raw) {
          const parsed = Number(raw.replace(/[^0-9.\-]/g, ""));
          if (!isNaN(parsed) && parsed > 0) {
            initialDeposit = parsed;
          }
        }
      }
      const captchaValue = captchaInput ? captchaInput.value.trim() : "";
      const captchaAnswer = captchaQuestion
        ? captchaQuestion.dataset.answer
        : null;

      if (!name || !email || !phone || !password || !confirmPassword) {
        return showError(errorBox, "Please fill in all required fields.");
      }

      if (password.length < 6) {
        return showError(errorBox, "Password must be at least 6 characters.");
      }

      if (password !== confirmPassword) {
        return showError(errorBox, "Passwords do not match.");
      }

      if (!captchaValue || captchaValue !== captchaAnswer) {
        showError(errorBox, "Captcha is incorrect. Please try again.");
        generateCaptcha();
        return;
      }

      try {
        const user = createUser({
          name,
          email,
          phone,
          password,
          initialDeposit,
          isAdmin: false,
        });

        showSuccess(
          successBox,
          "Registration Done successfully. Please login to view the Account No"
        );

        registerForm.reset();
        generateCaptcha();
      } catch (err) {
        showError(errorBox, err.message || "Failed to create account.");
      }
    });
  }

  function showError(el, message) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function showSuccess(el, message) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function hideError(el) {
    if (!el) return;
    el.textContent = "";
    el.classList.add("hidden");
  }
})();




