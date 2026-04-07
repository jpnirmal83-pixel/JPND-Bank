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
      const recoveryLinks = document.getElementById("loginRecoveryLinks");
      if (recoveryLinks) recoveryLinks.classList.add("hidden");
      if (identifierInput) {
        identifierInput.placeholder = "admin@localhost or your admin email";
      }
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

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const identifier = identifierInput.value.trim();
      const password = passwordInput.value;
      const role = loginRoleInput.value || "user";

      hideError(loginError);

      if (!identifier || !password) {
        return showError(loginError, "Please enter both identifier and password.");
      }

      let auth = null;
      try {
        auth = await getUserByAccountOrEmail(identifier, password);
      } catch (err) {
        return showError(loginError, err.message || "Account not found. Please check details.");
      }

      const user = auth?.user;
      if (!user) {
        return showError(loginError, "Account not found. Please check details.");
      }

      const isAdminLogin = role === "admin";
      if (isAdminLogin && !user.isAdmin) {
        return showError(loginError, "This account is not an admin account.");
      }

      // Set session and redirect
      setSession({
        // Dev/file:// fallback: store token for Authorization header-based auth.
        // Cookie auth may be blocked by the browser for file:// origins.
        accessToken: auth.accessToken,
        accountNumber: user.accountNumber,
        isAdmin: !!user.isAdmin,
      });

      if (isAdminLogin) {
        window.location.href = "admin.html";
      } else {
        window.location.href = "dashboard.html";
      }
    });

    initLoginRecoveryModals();
  }

  function initLoginRecoveryModals() {
    const modalEmail = document.getElementById("modalForgotEmail");
    const modalPw = document.getElementById("modalForgotPassword");
    const linkEmail = document.getElementById("linkForgotEmail");
    const linkPw = document.getElementById("linkForgotPassword");
    const formEmail = document.getElementById("forgotEmailForm");
    const formPw = document.getElementById("forgotPasswordForm");
    const errEmail = document.getElementById("forgotEmailError");
    const okEmail = document.getElementById("forgotEmailSuccess");
    const errPw = document.getElementById("forgotPasswordError");
    const okPw = document.getElementById("forgotPasswordSuccess");

    function openModal(el) {
      if (!el) return;
      el.classList.remove("hidden");
      el.setAttribute("aria-hidden", "false");
    }

    function closeModal(el) {
      if (!el) return;
      el.classList.add("hidden");
      el.setAttribute("aria-hidden", "true");
    }

    function clearAlerts() {
      [errEmail, okEmail, errPw, okPw].forEach((box) => {
        if (!box) return;
        box.textContent = "";
        box.classList.add("hidden");
      });
    }

    function showAlert(box, msg) {
      if (!box) return;
      box.textContent = msg;
      box.classList.remove("hidden");
    }

    if (linkEmail && modalEmail) {
      linkEmail.addEventListener("click", (e) => {
        e.preventDefault();
        clearAlerts();
        if (formEmail) formEmail.reset();
        openModal(modalEmail);
      });
    }

    if (linkPw && modalPw) {
      linkPw.addEventListener("click", (e) => {
        e.preventDefault();
        clearAlerts();
        if (formPw) formPw.reset();
        openModal(modalPw);
      });
    }

    if (modalEmail) {
      modalEmail.querySelectorAll("[data-close-forgot-email]").forEach((node) => {
        node.addEventListener("click", () => {
          closeModal(modalEmail);
          clearAlerts();
        });
      });
    }

    if (modalPw) {
      modalPw.querySelectorAll("[data-close-forgot-password]").forEach((node) => {
        node.addEventListener("click", () => {
          closeModal(modalPw);
          clearAlerts();
        });
      });
    }

    if (formEmail) {
      formEmail.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlerts();
        const accountNumber = (
          document.getElementById("recoverAccount")?.value || ""
        ).trim();
        const phone = (document.getElementById("recoverPhone")?.value || "").trim();
        const dob = (document.getElementById("recoverDob")?.value || "").trim();
        if (!accountNumber || !phone || !dob) {
          return showAlert(errEmail, "Please fill in all fields.");
        }
        const otp = prompt(
          "Enter the OTP sent to your registered mobile (demo: 1234):"
        );
        if (!otp || otp.trim() !== "1234") {
          return showAlert(
            errEmail,
            otp ? "Invalid OTP." : "OTP is required to continue."
          );
        }
        try {
          const res = await recoverEmailWithVerification({
            accountNumber,
            phone,
            dob,
          });
          showAlert(
            okEmail,
            `Your registered email is: ${res.email}`
          );
        } catch (err) {
          showAlert(errEmail, err.message || "Could not verify your details.");
        }
      });
    }

    if (formPw) {
      formPw.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlerts();
        const accountNumber = (
          document.getElementById("fpAccount")?.value || ""
        ).trim();
        const phone = (document.getElementById("fpPhone")?.value || "").trim();
        const newPassword = document.getElementById("fpNewPassword")?.value || "";
        const confirm = document.getElementById("fpConfirmPassword")?.value || "";
        if (!accountNumber || !phone || !newPassword) {
          return showAlert(errPw, "Please fill in all fields.");
        }
        if (newPassword.length < 6) {
          return showAlert(errPw, "Password must be at least 6 characters.");
        }
        if (newPassword !== confirm) {
          return showAlert(errPw, "Passwords do not match.");
        }
        const otp = prompt(
          "Enter the OTP sent to your registered mobile (demo: 1234):"
        );
        if (!otp || otp.trim() !== "1234") {
          return showAlert(
            errPw,
            otp ? "Invalid OTP." : "OTP is required to continue."
          );
        }
        try {
          const res = await forgotPasswordWithVerification({
            accountNumber,
            phone,
            newPassword,
          });
          showAlert(
            okPw,
            res.message || "Password updated. You can sign in now."
          );
          formPw.reset();
        } catch (err) {
          showAlert(errPw, err.message || "Could not reset password.");
        }
      });
    }
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

    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideError(errorBox);
      hideError(successBox);

      const name = document.getElementById("name").value.trim();
      const email = document.getElementById("email").value.trim();
      const phone = document.getElementById("phone").value.trim();
      const gender = document.getElementById("gender").value.trim();
      const dob = document.getElementById("dob").value.trim();
      const address = document.getElementById("address").value.trim();
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

      if (
        !name ||
        !email ||
        !phone ||
        !gender ||
        !dob ||
        !address ||
        !password ||
        !confirmPassword
      ) {
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

      const legalConsent = document.getElementById("registerLegalConsent");
      if (legalConsent && !legalConsent.checked) {
        return showError(
          errorBox,
          "Please confirm that you have read and agree to the Privacy statement, Disclosure, and Terms & conditions."
        );
      }

      try {
        await createUser({
          name,
          email,
          phone,
          gender,
          dob,
          address,
          password,
          initialDeposit,
          isAdmin: false,
        });

        showSuccess(
          successBox,
          "Registration completed successfully. Please log in to view your account number."
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




