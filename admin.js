(function () {
  const session = getSession();
  const current = getCurrentUser();

  // Only allow signed-in admins
  if (!session || !current || !session.isAdmin) {
    window.location.href = "index.html";
    return;
  }

  const adminWelcome = document.getElementById("adminWelcome");
  const logoutBtn = document.getElementById("adminLogoutBtn");

  const totalAccountsEl = document.getElementById("totalAccounts");
  const totalBalanceEl = document.getElementById("totalBalance");

  const usersBody = document.getElementById("adminUsersBody");
  const createForm = document.getElementById("adminCreateForm");
  const createResetBtn = document.getElementById("adminCreateResetBtn");

  const editModal = document.getElementById("adminEditModal");
  const editForm = document.getElementById("adminEditForm");
  const editError = document.getElementById("adminEditError");

  initHeader();
  renderSummaryAndUsers();
  initLogout();
  initCreateForm();
  initEditModal();

  function initHeader() {
    if (adminWelcome) {
      adminWelcome.textContent = current.name || "Admin";
    }
  }

  function initLogout() {
    if (!logoutBtn) return;
    logoutBtn.addEventListener("click", () => {
      clearSession();
      window.location.href = "index.html";
    });
  }

  function getCustomerUsers() {
    return loadUsers().filter((u) => !u.isAdmin);
  }

  function renderSummaryAndUsers() {
    const customers = getCustomerUsers();
    const totalBalance = customers.reduce(
      (sum, u) => sum + Number(u.balance || 0),
      0
    );

    if (totalAccountsEl) totalAccountsEl.textContent = String(customers.length);
    if (totalBalanceEl)
      totalBalanceEl.textContent = `₹${totalBalance.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;

    renderUsersTable(customers);
  }

  function renderUsersTable(customers) {
    if (!usersBody) return;
    if (!customers.length) {
      usersBody.innerHTML =
        '<tr><td colspan="7" class="muted text-center">No accounts yet.</td></tr>';
      return;
    }

    usersBody.innerHTML = customers
      .map((u) => {
        const lastTxnTime = getLastTransactionTime(u);
        const displayTime = lastTxnTime || u.createdAt;
        return `
        <tr data-account="${u.accountNumber}">
          <td>${u.accountNumber}</td>
          <td>${u.name}</td>
          <td>${u.email}</td>
          <td>${u.phone}</td>
          <td>₹${Number(u.balance || 0).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}</td>
          <td>${formatDateTime(displayTime)}</td>
          <td>
            <button class="icon-button" title="Edit user" data-edit>✎</button>
            <button class="icon-button" title="Reset password" data-reset-pw>🔁</button>
            <button class="icon-button" title="Delete user" data-delete>🗑</button>
          </td>
        </tr>
      `;
      })
      .join("");

    // Wire up actions
    usersBody.querySelectorAll("tr").forEach((row) => {
      const acc = row.getAttribute("data-account");
      if (!acc) return;
      const user = getCustomerUsers().find((u) => u.accountNumber === acc);
      if (!user) return;

      const editBtn = row.querySelector("button[data-edit]");
      const resetPwBtn = row.querySelector("button[data-reset-pw]");
      const deleteBtn = row.querySelector("button[data-delete]");

      if (editBtn) {
        editBtn.addEventListener("click", () => openEditModal(user));
      }
      if (resetPwBtn) {
        resetPwBtn.addEventListener("click", () => resetPassword(user));
      }
      if (deleteBtn) {
        deleteBtn.addEventListener("click", () => deleteUserAccount(user));
      }
    });
  }

  function initCreateForm() {
    if (!createForm) return;

    // Password toggle functionality
    const adminPasswordToggle = document.getElementById("adminPasswordToggle");
    const adminPasswordField = document.getElementById("adminPassword");
    if (adminPasswordToggle && adminPasswordField) {
      adminPasswordToggle.addEventListener("click", () => {
        const type =
          adminPasswordField.getAttribute("type") === "password" ? "text" : "password";
        adminPasswordField.setAttribute("type", type);
      });
    }

    createForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const name = document.getElementById("adminName").value.trim();
      const email = document.getElementById("adminEmail").value.trim();
      const phone = document.getElementById("adminPhone").value.trim();
      const rawDeposit = (
        document.getElementById("adminInitialDeposit").value || ""
      ).trim();
      const initialDeposit = Number(rawDeposit.replace(/[^0-9.\-]/g, "")) || 0;
      const password = document.getElementById("adminPassword").value;

      if (!name || !email || !phone || !password) {
        alert("Please fill in all required fields.");
        return;
      }
      if (password.length < 6) {
        alert("Password must be at least 6 characters.");
        return;
      }

      try {
        const user = createUser({
          name,
          email,
          phone,
          initialDeposit,
          password,
          isAdmin: false,
        });
        alert(
          `Customer account created. Account number: ${user.accountNumber}`
        );
        createForm.reset();
        const depInput = document.getElementById("adminInitialDeposit");
        if (depInput) depInput.value = "1000";
        renderSummaryAndUsers();
      } catch (err) {
        alert(err.message || "Failed to create user.");
      }
    });

    if (createResetBtn) {
      createResetBtn.addEventListener("click", () => {
        createForm.reset();
        const depInput = document.getElementById("adminInitialDeposit");
        if (depInput) depInput.value = "1000";
      });
    }
  }

  function openEditModal(user) {
    if (!editModal || !editForm) return;
    hideEditError();
    document.getElementById("adminEditAccountNumber").value =
      user.accountNumber;
    document.getElementById("adminEditName").value = user.name;
    document.getElementById("adminEditEmail").value = user.email;
    document.getElementById("adminEditPhone").value = user.phone;
    document.getElementById("adminEditPassword").value = "";
    editModal.classList.remove("hidden");
  }

  function initEditModal() {
    if (!editModal || !editForm) return;

    // Password toggle functionality
    const adminEditPasswordToggle = document.getElementById("adminEditPasswordToggle");
    const adminEditPasswordField = document.getElementById("adminEditPassword");
    if (adminEditPasswordToggle && adminEditPasswordField) {
      adminEditPasswordToggle.addEventListener("click", () => {
        const type =
          adminEditPasswordField.getAttribute("type") === "password" ? "text" : "password";
        adminEditPasswordField.setAttribute("type", type);
      });
    }

    editModal.addEventListener("click", (e) => {
      if (
        e.target.classList.contains("modal-backdrop") ||
        e.target.hasAttribute("data-close-modal")
      ) {
        editModal.classList.add("hidden");
      }
    });

    editForm.addEventListener("submit", (e) => {
      e.preventDefault();
      hideEditError();

      const acc = document
        .getElementById("adminEditAccountNumber")
        .value.trim();
      const name = document.getElementById("adminEditName").value.trim();
      const email = document.getElementById("adminEditEmail").value.trim();
      const phone = document.getElementById("adminEditPhone").value.trim();
      const newPassword = document
        .getElementById("adminEditPassword")
        .value.trim();

      if (!name || !email || !phone) {
        return showEditError("Name, email and phone are required.");
      }

      const users = loadUsers();
      const userIndex = users.findIndex((u) => u.accountNumber === acc);
      if (userIndex === -1 || users[userIndex].isAdmin) {
        return showEditError("Customer not found.");
      }

      if (
        users.some(
          (u, idx) =>
            idx !== userIndex &&
            !u.isAdmin &&
            u.email.toLowerCase() === email.toLowerCase()
        )
      ) {
        return showEditError("Email already used by another customer.");
      }

      const updated = { ...users[userIndex], name, email, phone };
      if (newPassword) {
        if (newPassword.length < 6) {
          return showEditError("New password must be at least 6 characters.");
        }
        updated.password = newPassword;
      }

      users[userIndex] = updated;
      saveUsers(users);
      renderSummaryAndUsers();
      editModal.classList.add("hidden");
    });
  }

  function resetPassword(user) {
    const pwd = prompt(
      `Enter new password for ${user.name} (leave blank to cancel):`
    );
    if (!pwd) return;
    if (pwd.length < 6) {
      alert("Password must be at least 6 characters.");
      return;
    }
    user.password = pwd;
    updateUser(user);
    alert("Password updated.");
  }

  function deleteUserAccount(user) {
    const confirmed = confirm(
      `Delete account ${user.accountNumber} (${user.name})? This cannot be undone.`
    );
    if (!confirmed) return;
    deleteUser(user.accountNumber);
    renderSummaryAndUsers();
  }

  function showEditError(msg) {
    if (!editError) return;
    editError.textContent = msg;
    editError.classList.remove("hidden");
  }

  function hideEditError() {
    if (!editError) return;
    editError.textContent = "";
    editError.classList.add("hidden");
  }

  function formatDateTime(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "-";
    return d.toLocaleString();
  }

  function getLastTransactionTime(user) {
    if (!user || !Array.isArray(user.transactions) || !user.transactions.length) {
      return null;
    }
    const sorted = [...user.transactions].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
    return sorted[0]?.timestamp || null;
  }
})();



