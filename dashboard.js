// User dashboard logic: session guard, basic display, profile modal, quick deposit/withdraw

(function () {
  const user = getCurrentUser();
  const session = getSession();

  // Only allow signed-in non-admin users
  if (!session || !user || session.isAdmin) {
    window.location.href = "index.html";
    return;
  }

  const welcomeUserEl = document.getElementById("welcomeUser");
  const accountNumberEl = document.getElementById("accountNumber");
  const balanceEl = document.getElementById("currentBalance");
  const lastUpdatedEl = document.getElementById("lastUpdated");
  const recentBody = document.getElementById("recentTransactionsBody");
  const logoutBtn = document.getElementById("logoutBtn");

  const quickForm = document.getElementById("quickActionsForm");
  const quickError = document.getElementById("quickActionError");
  const quickServicesForm = document.getElementById("quickServicesForm");
  const viewStatementBtn = document.getElementById("viewStatementBtn");

  const editProfileBtn = document.getElementById("editProfileBtn");
  const deleteAccountBtn = document.getElementById("deleteAccountBtn");
  const profileModal = document.getElementById("profileModal");
  const profileForm = document.getElementById("profileForm");
  const profileError = document.getElementById("profileError");

  initHeader();
  renderOverview();
  renderRecent();
  initQuickActions();
  initQuickServices();
  initViewStatement();
  initProfileModal();
  initLogout();

  function initHeader() {
    if (welcomeUserEl) {
      welcomeUserEl.textContent = user.name;
    }
  }

  function renderOverview() {
    if (accountNumberEl) accountNumberEl.textContent = user.accountNumber;
    if (balanceEl) balanceEl.textContent = formatCurrency(user.balance);

    const lastTxn = [...(user.transactions || [])].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    )[0];
    if (lastTxn && lastUpdatedEl) {
      lastUpdatedEl.textContent = formatDateTime(lastTxn.timestamp);
    }
  }

  function renderRecent() {
    if (!recentBody) return;
    const txns = [...(user.transactions || [])]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 5);

    if (!txns.length) {
      recentBody.innerHTML =
        '<tr><td colspan="8" class="muted text-center">No transactions yet.</td></tr>';
      return;
    }

    recentBody.innerHTML = txns
      .map(
        (t) => `
        <tr>
          <td>${formatType(t.type)}</td>
          <td>${formatMode(t)}</td>
          <td>${formatCounterpartyAccount(t)}</td>
          <td>${formatCounterpartyName(t)}</td>
          <td>${formatCurrency(t.amount)}</td>
          <td>${formatCurrency(t.prevBalance)}</td>
          <td>${formatCurrency(t.newBalance)}</td>
          <td>${formatDateTime(t.timestamp)}</td>
        </tr>
      `
      )
      .join("");
  }

  function initQuickActions() {
    if (!quickForm) return;
    quickForm.addEventListener("submit", (e) => {
      e.preventDefault();
      hideBox(quickError);

      const type = document.getElementById("actionType").value;
      const rawAmount = (document.getElementById("actionAmount").value || "").trim();
      const amountVal = Number(rawAmount.replace(/[^0-9.\-]/g, ""));

      if (!rawAmount || !amountVal || isNaN(amountVal) || amountVal <= 0) {
        return showBox(quickError, "Enter a valid amount.");
      }

      const freshUser = getCurrentUser();
      if (!freshUser) {
        window.location.href = "index.html";
        return;
      }

      const prevBalance = freshUser.balance;

      if (type === "withdraw" && amountVal > prevBalance) {
        return showBox(quickError, "Insufficient balance.");
      }

      const newBalance =
        type === "deposit" ? prevBalance + amountVal : prevBalance - amountVal;

      freshUser.balance = newBalance;
      freshUser.transactions = freshUser.transactions || [];
      freshUser.transactions.push({
        id: generateId("txn"),
        type: type === "deposit" ? "deposit" : "withdraw",
        amount: amountVal,
        prevBalance,
        newBalance,
        timestamp: new Date().toISOString(),
      });

      updateUser(freshUser);

      // Re-render with updated data
      Object.assign(user, freshUser);
      quickForm.reset();
      renderOverview();
      renderRecent();
    });
  }

  function initQuickServices() {
    if (!quickServicesForm) return;
    quickServicesForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const serviceSelect = document.getElementById("serviceType");
      const value = serviceSelect ? serviceSelect.value : "";
      if (!value) {
        alert("Please select a service from the list.");
        return;
      }

      const labels = {
        "general-banking": "General Banking",
        insurance: "Insurance",
        investment: "Investment",
        cards: "Cards",
        loan: "Loan",
        demat: "Demat",
      };

      const label = labels[value] || "Selected Service";
      alert(
        `${label} request screen can be implemented here. Currently this is a demo shortcut from Quick Services.`
      );

      // Reset after action
      serviceSelect.value = "";
    });
  }

  function initViewStatement() {
    if (!viewStatementBtn) return;
    viewStatementBtn.addEventListener("click", () => {
      const choice = confirm(
        "Do you want to VIEW your statement on screen?\n\nClick OK to View, or Cancel to Download as Excel."
      );
      if (choice) {
        window.location.href = "transactions.html";
      } else {
        window.location.href = "transactions.html?autoDownload=excel";
      }
    });
  }

  function initProfileModal() {
    if (!profileModal || !profileForm) return;

    // Password toggle functionality
    const profilePasswordToggle = document.getElementById("profilePasswordToggle");
    const profilePasswordField = document.getElementById("profilePassword");
    if (profilePasswordToggle && profilePasswordField) {
      profilePasswordToggle.addEventListener("click", () => {
        const type =
          profilePasswordField.getAttribute("type") === "password" ? "text" : "password";
        profilePasswordField.setAttribute("type", type);
      });
    }

    if (editProfileBtn) {
      editProfileBtn.addEventListener("click", () => {
        hideBox(profileError);
        document.getElementById("profileName").value = user.name;
        document.getElementById("profileEmail").value = user.email;
        document.getElementById("profilePhone").value = user.phone;
        document.getElementById("profilePassword").value = "";
        profileModal.classList.remove("hidden");
      });
    }

    profileModal.addEventListener("click", (e) => {
      if (
        e.target.classList.contains("modal-backdrop") ||
        e.target.hasAttribute("data-close-modal")
      ) {
        profileModal.classList.add("hidden");
      }
    });

    profileForm.addEventListener("submit", (e) => {
      e.preventDefault();
      hideBox(profileError);

      const name = document.getElementById("profileName").value.trim();
      const email = document.getElementById("profileEmail").value.trim();
      const phone = document.getElementById("profilePhone").value.trim();
      const newPassword = document
        .getElementById("profilePassword")
        .value.trim();

      if (!name || !email || !phone) {
        return showBox(profileError, "All fields except password are required.");
      }

      const users = loadUsers();
      if (
        users.some(
          (u) =>
            u.accountNumber !== user.accountNumber &&
            u.email.toLowerCase() === email.toLowerCase()
        )
      ) {
        return showBox(profileError, "Email is already used by another account.");
      }

      const updatedUser = { ...getCurrentUser(), name, email, phone };
      const changedPassword = !!newPassword;
      if (newPassword) {
        if (newPassword.length < 6) {
          return showBox(
            profileError,
            "New password must be at least 6 characters."
          );
        }
        updatedUser.password = newPassword;
      }

      updateUser(updatedUser);
      Object.assign(user, updatedUser);
      initHeader();
      profileModal.classList.add("hidden");

      if (changedPassword) {
        alert("Password changed. Please check");
      }
    });

    if (deleteAccountBtn) {
      deleteAccountBtn.addEventListener("click", () => {
        alert("Account closure will be done in branch only.");
      });
    }
  }

  function initLogout() {
    if (!logoutBtn) return;
    logoutBtn.addEventListener("click", () => {
      clearSession();
      window.location.href = "index.html";
    });
  }

  // Helpers
  function formatCurrency(num) {
    return `₹${Number(num || 0).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  function formatDateTime(iso) {
    const d = new Date(iso);
    return d.toLocaleString();
  }

  function formatType(type) {
    switch (type) {
      case "deposit":
        return "Deposit";
      case "withdraw":
        return "Withdrawal";
      case "transfer-in":
        return "Transfer In";
      case "transfer-out":
        return "Transfer Out";
      default:
        return type;
    }
  }

  function formatMode(tx) {
    if (!tx || !tx.mode) return "-";
    return tx.mode;
  }

  function formatCounterpartyAccount(tx) {
    if (!tx || !tx.counterpartyAccount) return "-";
    return tx.counterpartyAccount;
  }

  function formatCounterpartyName(tx) {
    if (!tx || !tx.counterpartyName) return "-";
    return tx.counterpartyName;
  }

  function showBox(el, message) {
    if (!el) return;
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function hideBox(el) {
    if (!el) return;
    el.textContent = "";
    el.classList.add("hidden");
  }
})();



