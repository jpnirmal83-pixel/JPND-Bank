(function () {
  const session = getSession();
  let current = null;

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
  const productForm = document.getElementById("adminProductForm");
  const productResetBtn = document.getElementById("adminProductResetBtn");
  const productsBody = document.getElementById("adminProductsBody");
  const aiFeedbackBody = document.getElementById("adminAiFeedbackBody");
  const topBoostedBody = document.getElementById("adminTopBoostedBody");
  const topPenalizedBody = document.getElementById("adminTopPenalizedBody");
  const feedbackTrendBody = document.getElementById("adminFeedbackTrendBody");
  const kpiAvgConversion = document.getElementById("adminKpiAvgConversion");
  const kpiMostImproved = document.getElementById("adminKpiMostImproved");
  const kpiMostDeclining = document.getElementById("adminKpiMostDeclining");
  const kpiTotalFeedback = document.getElementById("adminKpiTotalFeedback");
  const diagnosticsFilterForm = document.getElementById("adminDiagnosticsFilterForm");
  const diagDaysSelect = document.getElementById("adminDiagDays");
  const diagCategorySelect = document.getElementById("adminDiagCategory");
  const exportDiagnosticsBtn = document.getElementById("adminExportDiagnosticsBtn");
  const exportTrendBtn = document.getElementById("adminExportTrendBtn");
  const exportCombinedBtn = document.getElementById("adminExportCombinedBtn");
  const loanModelStatusEl = document.getElementById("adminLoanModelStatus");
  const loanScorecardModelStatusEl = document.getElementById("adminLoanScorecardModelStatus");
  const trainLoanBtn = document.getElementById("adminTrainLoanSanctionModelBtn");
  const trainLoanScorecardBtn = document.getElementById("adminTrainLoanScorecardModelBtn");
  const refreshLoanAppsBtn = document.getElementById("adminRefreshLoanAppsBtn");
  const loanAppsBody = document.getElementById("adminLoanAppsBody");
  const refreshCreditRiskBtn = document.getElementById("adminRefreshCreditRiskBtn");
  const creditRiskBody = document.getElementById("adminCreditRiskBody");
  const creditRiskModelStatusEl = document.getElementById("adminCreditRiskModelStatus");
  const trainCreditRiskModelBtn = document.getElementById("adminTrainCreditRiskModelBtn");
  const refreshCreditRiskSnapshotsBtn = document.getElementById("adminRefreshCreditRiskSnapshotsBtn");
  const creditRiskSnapshotsBody = document.getElementById("adminCreditRiskSnapshotsBody");
  const refreshChurnBtn = document.getElementById("adminRefreshChurnBtn");
  const churnBody = document.getElementById("adminChurnBody");
  const churnModelStatusEl = document.getElementById("adminChurnModelStatus");
  const churnNbaModelStatusEl = document.getElementById("adminChurnNbaModelStatus");
  const trainChurnModelBtn = document.getElementById("adminTrainChurnModelBtn");
  const trainChurnNbaModelBtn = document.getElementById("adminTrainChurnNbaModelBtn");
  const refreshChurnNbaPerfBtn = document.getElementById("adminRefreshChurnNbaPerfBtn");
  const churnNbaPerfChart = document.getElementById("adminChurnNbaPerfChart");
  const churnNbaPerfBody = document.getElementById("adminChurnNbaPerfBody");
  const refreshChurnSnapshotsBtn = document.getElementById("adminRefreshChurnSnapshotsBtn");
  const churnSnapshotsBody = document.getElementById("adminChurnSnapshotsBody");
  const fraudStatusFilter = document.getElementById("adminFraudStatusFilter");
  const fraudAccountFilter = document.getElementById("adminFraudAccountFilter");
  const fraudAlertsBody = document.getElementById("adminFraudAlertsBody");
  const fraudTotalEl = document.getElementById("adminFraudTotal");
  const fraudOpenEl = document.getElementById("adminFraudOpen");
  const fraudHighEl = document.getElementById("adminFraudHigh");
  const fraudBlockedEl = document.getElementById("adminFraudBlocked");
  const fraudModelStatusEl = document.getElementById("adminFraudModelStatus");
  const fraudRealtimeModelStatusEl = document.getElementById("adminFraudRealtimeModelStatus");
  const trainFraudModelBtn = document.getElementById("adminTrainFraudModelBtn");
  const trainFraudRealtimeModelBtn = document.getElementById("adminTrainFraudRealtimeModelBtn");
  const refreshFraudNetworkBtn = document.getElementById("adminRefreshFraudNetworkBtn");
  const fraudNetworkBody = document.getElementById("adminFraudNetworkBody");
  const adminAmlModelStatusEl = document.getElementById("adminAmlModelStatus");
  const adminTrainAmlModelBtn = document.getElementById("adminTrainAmlModelBtn");
  const adminRefreshAmlRingsBtn = document.getElementById("adminRefreshAmlRingsBtn");
  const adminRunAmlAutomationBtn = document.getElementById("adminRunAmlAutomationBtn");
  const adminAmlRingsBody = document.getElementById("adminAmlRingsBody");
  const adminRefreshAmlCasesBtn = document.getElementById("adminRefreshAmlCasesBtn");
  const adminAmlCaseStatusFilter = document.getElementById("adminAmlCaseStatusFilter");
  const adminAmlCasePriorityFilter = document.getElementById("adminAmlCasePriorityFilter");
  const adminAmlWatchlistOnly = document.getElementById("adminAmlWatchlistOnly");
  const adminAmlCasesBody = document.getElementById("adminAmlCasesBody");
  const adminRefreshAmlAlertLinksBtn = document.getElementById("adminRefreshAmlAlertLinksBtn");
  const adminAmlAlertLinksBody = document.getElementById("adminAmlAlertLinksBody");
  const kbForm = document.getElementById("adminKbForm");
  const kbResetBtn = document.getElementById("adminKbResetBtn");
  const kbRefreshBtn = document.getElementById("adminKbRefreshBtn");
  const kbBody = document.getElementById("adminKbBody");
  const voiceAccountFilter = document.getElementById("adminVoiceAccountFilter");
  const voiceIntentFilter = document.getElementById("adminVoiceIntentFilter");
  const voiceStatusFilter = document.getElementById("adminVoiceStatusFilter");
  const voiceRefreshBtn = document.getElementById("adminVoiceRefreshBtn");
  const voiceAuditBody = document.getElementById("adminVoiceAuditBody");
  const adminKycBody = document.getElementById("adminKycBody");
  const adminKycStatusFilter = document.getElementById("adminKycStatusFilter");
  const adminKycRefreshBtn = document.getElementById("adminKycRefreshBtn");
  const adminLoanDocAiBody = document.getElementById("adminLoanDocAiBody");
  const adminLoanDocReviewStatusFilter = document.getElementById("adminLoanDocReviewStatusFilter");
  const adminLoanDocAccountFilter = document.getElementById("adminLoanDocAccountFilter");
  const adminLoanDocRefreshBtn = document.getElementById("adminLoanDocRefreshBtn");
  const adminLoanDocModelStatus = document.getElementById("adminLoanDocModelStatus");
  const adminLoanDocTrainBtn = document.getElementById("adminLoanDocTrainBtn");
  const adminSupportTotal = document.getElementById("adminSupportTotal");
  const adminSupportBlocked = document.getElementById("adminSupportBlocked");
  const adminSupportSafe = document.getElementById("adminSupportSafe");
  const adminSupportAccountFilter = document.getElementById("adminSupportAccountFilter");
  const adminSupportBlockedOnly = document.getElementById("adminSupportBlockedOnly");
  const adminSupportFromDate = document.getElementById("adminSupportFromDate");
  const adminSupportToDate = document.getElementById("adminSupportToDate");
  const adminSupportRefreshBtn = document.getElementById("adminSupportRefreshBtn");
  const adminSupportExportCsvBtn = document.getElementById("adminSupportExportCsvBtn");
  const adminSupportChatsBody = document.getElementById("adminSupportChatsBody");
  const adminSupportBlockedIntentChart = document.getElementById("adminSupportBlockedIntentChart");
  let productCache = [];
  let latestDiagnostics = { topBoosted: [], topPenalized: [], trend: [] };

  bootstrap();

  async function bootstrap() {
    current = await getCurrentUser();
    if (!session || !current || !session.isAdmin) {
      window.location.href = "index.html";
      return;
    }
    initHeader();
    await renderSummaryAndUsers();
    await loadProductsAndFeedback();
    initLogout();
    initCreateForm();
    initEditModal();
    initProductForm();
    initDiagnosticsControls();
    initLoanTrainingControls();
    initFraudAlertControls();
    initCreditRiskControls();
    initChurnControls();
    initKbControls();
    initVoiceAuditControls();
    initKycAdminControls();
    initLoanDocumentAiAdminControls();
    initSupportAuditControls();
  }

  function initHeader() {
    if (adminWelcome) {
      adminWelcome.textContent = current.name || "Admin";
    }
  }

  function initLogout() {
    if (!logoutBtn) return;
    logoutBtn.addEventListener("click", async () => {
      await logoutSession();
      window.location.href = "index.html";
    });
  }

  async function getCustomerUsers() {
    const users = await loadUsers();
    return users.filter((u) => !u.isAdmin);
  }

  async function renderSummaryAndUsers() {
    const customers = await getCustomerUsers();
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
      const user = customers.find((u) => u.accountNumber === acc);
      if (!user) return;

      const editBtn = row.querySelector("button[data-edit]");
      const deleteBtn = row.querySelector("button[data-delete]");

      if (editBtn) {
        editBtn.addEventListener("click", () => openEditModal(user));
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

    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const name = document.getElementById("adminName").value.trim();
      const email = document.getElementById("adminEmail").value.trim();
      const phone = document.getElementById("adminPhone").value.trim();
      const gender = (document.getElementById("adminGender")?.value || "").trim();
      const openAccountType = (
        document.getElementById("adminOpenAccount")?.value || ""
      ).trim();
      const dob = (document.getElementById("adminDob")?.value || "").trim();
      const address = (document.getElementById("adminAddress")?.value || "").trim();
      const rawDeposit = (
        document.getElementById("adminInitialDeposit").value || ""
      ).trim();
      const initialDeposit = Number(rawDeposit.replace(/[^0-9.\-]/g, "")) || 0;
      const password = document.getElementById("adminPassword").value;

      if (
        !name ||
        !email ||
        !phone ||
        !gender ||
        !openAccountType ||
        !dob ||
        !address ||
        !password
      ) {
        alert("Please fill in all required fields.");
        return;
      }
      if (password.length < 6) {
        alert("Password must be at least 6 characters.");
        return;
      }

      try {
        const user = await createUser({
          name,
          email,
          phone,
          gender,
          dob,
          address,
          openAccountType,
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
        await renderSummaryAndUsers();
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

    editForm.addEventListener("submit", async (e) => {
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

      const users = await loadUsers();
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

      await updateUser(updated);
      await renderSummaryAndUsers();
      editModal.classList.add("hidden");
    });
  }

  async function deleteUserAccount(user) {
    const confirmed = confirm(
      `Delete account ${user.accountNumber} (${user.name})? This cannot be undone.`
    );
    if (!confirmed) return;
    await deleteUser(user.accountNumber);
    await renderSummaryAndUsers();
  }

  function initProductForm() {
    if (!productForm) return;
    productForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const productId = (document.getElementById("adminProductId").value || "").trim();
      const payload = {
        name: document.getElementById("adminProductName").value.trim(),
        category: document.getElementById("adminProductCategory").value,
        riskLevel: document.getElementById("adminProductRisk").value,
        minAge: Number(document.getElementById("adminProductMinAge").value),
        maxAge: Number(document.getElementById("adminProductMaxAge").value),
        minBalance: Number(document.getElementById("adminProductMinBalance").value),
        summary: document.getElementById("adminProductSummary").value.trim(),
        active: document.getElementById("adminProductActive").value === "true",
      };
      try {
        if (productId) {
          await adminUpdateProduct(productId, payload);
        } else {
          await adminCreateProduct(payload);
        }
        resetProductForm();
        await loadProductsAndFeedback();
      } catch (err) {
        alert(err.message || "Failed to save product.");
      }
    });

    if (productResetBtn) {
      productResetBtn.addEventListener("click", resetProductForm);
    }
  }

  function resetProductForm() {
    if (!productForm) return;
    productForm.reset();
    document.getElementById("adminProductId").value = "";
    document.getElementById("adminProductCategory").value = "insurance";
    document.getElementById("adminProductRisk").value = "moderate";
    document.getElementById("adminProductActive").value = "true";
  }

  async function loadProductsAndFeedback() {
    try {
      productCache = await adminListProducts();
      renderProductsTable(productCache);
      const summary = await adminFeedbackSummary();
      renderAiFeedback(summary);
      const days = Number(diagDaysSelect?.value || 7);
      const category = diagCategorySelect?.value || "all";
      const diagnostics = await adminAiDiagnostics(days, category);
      latestDiagnostics = diagnostics || { topBoosted: [], topPenalized: [], trend: [] };
      renderDiagnostics(latestDiagnostics);
    } catch (err) {
      console.error(err);
    }
  }

  function initDiagnosticsControls() {
    if (diagnosticsFilterForm) {
      diagnosticsFilterForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await loadProductsAndFeedback();
      });
    }
    if (exportDiagnosticsBtn) {
      exportDiagnosticsBtn.addEventListener("click", () => {
        const rows = [
          ...((latestDiagnostics && latestDiagnostics.topBoosted) || []).map((r) => ({
            bucket: "boosted",
            ...r,
          })),
          ...((latestDiagnostics && latestDiagnostics.topPenalized) || []).map((r) => ({
            bucket: "penalized",
            ...r,
          })),
        ];
        if (!rows.length) {
          alert("No diagnostics data to export.");
          return;
        }
        exportCsv(
          "jaydee-ai-diagnostics.csv",
          ["Bucket", "Product", "Category", "ScoreAdjustment", "Accepted", "Saved", "Rejected"],
          rows.map((r) => [
            r.bucket,
            r.productName,
            r.category,
            r.scoreAdjustment,
            r.accepted,
            r.saved,
            r.rejected,
          ])
        );
      });
    }
    if (exportTrendBtn) {
      exportTrendBtn.addEventListener("click", () => {
        const rows = (latestDiagnostics && latestDiagnostics.trend) || [];
        if (!rows.length) {
          alert("No trend data to export.");
          return;
        }
        exportCsv(
          "jaydee-ai-feedback-trend.csv",
          ["Date", "Interested", "Saved", "NotRelevant"],
          rows.map((r) => [r.date, r.accepted, r.saved, r.rejected])
        );
      });
    }
    if (exportCombinedBtn) {
      exportCombinedBtn.addEventListener("click", () => {
        const diagRows = [
          ...((latestDiagnostics && latestDiagnostics.topBoosted) || []).map((r) => ({
            bucket: "boosted",
            ...r,
          })),
          ...((latestDiagnostics && latestDiagnostics.topPenalized) || []).map((r) => ({
            bucket: "penalized",
            ...r,
          })),
        ];
        const trendRows = (latestDiagnostics && latestDiagnostics.trend) || [];
        if (!diagRows.length && !trendRows.length) {
          alert("No diagnostics/trend data to export.");
          return;
        }
        const combined = [
          ...diagRows.map((r) => [
            "diagnostics",
            r.bucket,
            r.productName,
            r.category,
            r.scoreAdjustment,
            r.conversionRate,
            r.trend7d,
            r.accepted,
            r.saved,
            r.rejected,
            "",
          ]),
          ...trendRows.map((r) => [
            "trend",
            "",
            "",
            "",
            "",
            "",
            "",
            r.accepted,
            r.saved,
            r.rejected,
            r.date,
          ]),
        ];
        exportCsv(
          "jaydee-ai-combined-report.csv",
          [
            "Section",
            "Bucket",
            "Product",
            "Category",
            "ScoreAdjustment",
            "ConversionPercent",
            "MiniTrendA_S_R",
            "Interested",
            "Saved",
            "NotRelevant",
            "Date",
          ],
          combined
        );
      });
    }
  }

  function renderProductsTable(products) {
    if (!productsBody) return;
    if (!products.length) {
      productsBody.innerHTML = '<tr><td colspan="7" class="muted text-center">No products yet.</td></tr>';
      return;
    }
    productsBody.innerHTML = products
      .map(
        (p) => `
      <tr data-product-id="${p.id}">
        <td>${p.name}</td>
        <td>${p.category}</td>
        <td>${p.riskLevel}</td>
        <td>${p.minAge} - ${p.maxAge}</td>
        <td>₹${Number(p.minBalance || 0).toLocaleString("en-IN")}</td>
        <td>${p.active ? "Active" : "Inactive"}</td>
        <td>
          <button class="icon-button" data-product-edit>✎</button>
          <button class="icon-button" data-product-delete>🗑</button>
        </td>
      </tr>
    `
      )
      .join("");

    productsBody.querySelectorAll("tr").forEach((row) => {
      const id = Number(row.getAttribute("data-product-id"));
      if (!id) return;
      const product = productCache.find((p) => Number(p.id) === id);
      if (!product) return;
      const editBtn = row.querySelector("button[data-product-edit]");
      const deleteBtn = row.querySelector("button[data-product-delete]");
      if (editBtn) editBtn.addEventListener("click", () => populateProductForm(product));
      if (deleteBtn) {
        deleteBtn.addEventListener("click", async () => {
          const ok = confirm(`Delete product "${product.name}"?`);
          if (!ok) return;
          await adminDeleteProduct(product.id);
          await loadProductsAndFeedback();
        });
      }
    });
  }

  function populateProductForm(p) {
    document.getElementById("adminProductId").value = String(p.id);
    document.getElementById("adminProductName").value = p.name || "";
    document.getElementById("adminProductCategory").value = p.category || "insurance";
    document.getElementById("adminProductRisk").value = p.riskLevel || "moderate";
    document.getElementById("adminProductMinAge").value = String(p.minAge ?? 18);
    document.getElementById("adminProductMaxAge").value = String(p.maxAge ?? 100);
    document.getElementById("adminProductMinBalance").value = String(p.minBalance ?? 0);
    document.getElementById("adminProductSummary").value = p.summary || "";
    document.getElementById("adminProductActive").value = p.active ? "true" : "false";
  }

  function renderAiFeedback(rows) {
    if (!aiFeedbackBody) return;
    if (!rows || !rows.length) {
      aiFeedbackBody.innerHTML = '<tr><td colspan="5" class="muted text-center">No feedback yet.</td></tr>';
      return;
    }
    aiFeedbackBody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.productName}</td>
        <td>${r.category}</td>
        <td>${r.accepted}</td>
        <td>${r.saved}</td>
        <td>${r.rejected}</td>
      </tr>
    `
      )
      .join("");
  }

  function renderDiagnostics(data) {
    renderAdjustmentTable(topBoostedBody, data?.topBoosted || [], "No boosted products yet.");
    renderAdjustmentTable(topPenalizedBody, data?.topPenalized || [], "No penalized products yet.");
    renderTrendTable(data?.trend || []);
    renderKpis(data);
  }

  function renderAdjustmentTable(container, rows, emptyMsg) {
    if (!container) return;
    if (!rows.length) {
      container.innerHTML = `<tr><td colspan="5" class="muted text-center">${emptyMsg}</td></tr>`;
      return;
    }
    container.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.productName}</td>
        <td>${r.category}</td>
        <td>${Number(r.scoreAdjustment || 0).toFixed(2)}</td>
        <td>${Number(r.conversionRate || 0).toFixed(2)}%</td>
        <td title="${r.trend7d || "-"}">
          ${toTrendSparkline(r.trend7d || "")}
          <span style="${getTrendDirectionStyle(getTrendDelta(r.trend7d || ""))}">
            ${getTrendDirectionArrow(getTrendDelta(r.trend7d || ""))}
          </span>
        </td>
      </tr>
    `
      )
      .join("");
  }

  function renderTrendTable(rows) {
    if (!feedbackTrendBody) return;
    if (!rows.length) {
      feedbackTrendBody.innerHTML =
        '<tr><td colspan="4" class="muted text-center">No trend data yet.</td></tr>';
      return;
    }
    feedbackTrendBody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.date}</td>
        <td>${r.accepted}</td>
        <td>${r.saved}</td>
        <td>${r.rejected}</td>
      </tr>
    `
      )
      .join("");
  }

  function exportCsv(filename, headers, rows) {
    const content = [headers, ...rows]
      .map((row) =>
        row
          .map((value) => {
            const v = String(value ?? "");
            if (v.includes(",") || v.includes("\"") || v.includes("\n")) {
              return `"${v.replace(/"/g, '""')}"`;
            }
            return v;
          })
          .join(",")
      )
      .join("\n");
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function renderKpis(data) {
    const boosted = (data && data.topBoosted) || [];
    const penalized = (data && data.topPenalized) || [];
    const allProducts = [...boosted, ...penalized];

    const avgConversion =
      allProducts.length > 0
        ? allProducts.reduce((sum, p) => sum + Number(p.conversionRate || 0), 0) / allProducts.length
        : 0;
    if (kpiAvgConversion) {
      kpiAvgConversion.textContent = `${avgConversion.toFixed(2)}%`;
    }

    const withDelta = allProducts.map((p) => ({
      ...p,
      trendDelta: getTrendDelta(p.trend7d || ""),
    }));
    const improved = withDelta.reduce(
      (best, p) => (p.trendDelta > best.trendDelta ? p : best),
      { productName: "-", trendDelta: Number.NEGATIVE_INFINITY }
    );
    const declining = withDelta.reduce(
      (worst, p) => (p.trendDelta < worst.trendDelta ? p : worst),
      { productName: "-", trendDelta: Number.POSITIVE_INFINITY }
    );

    if (kpiMostImproved) {
      kpiMostImproved.innerHTML =
        improved.productName && improved.productName !== "-"
          ? `${improved.productName} <span style="${getTrendDirectionStyle(improved.trendDelta)}">(${formatSigned(
              improved.trendDelta
            )} ${getTrendDirectionArrow(improved.trendDelta)})</span>`
          : "-";
    }
    if (kpiMostDeclining) {
      kpiMostDeclining.innerHTML =
        declining.productName && declining.productName !== "-"
          ? `${declining.productName} <span style="${getTrendDirectionStyle(declining.trendDelta)}">(${formatSigned(
              declining.trendDelta
            )} ${getTrendDirectionArrow(declining.trendDelta)})</span>`
          : "-";
    }

    const trendRows = (data && data.trend) || [];
    const totalFeedback = trendRows.reduce(
      (sum, r) => sum + Number(r.accepted || 0) + Number(r.saved || 0) + Number(r.rejected || 0),
      0
    );
    if (kpiTotalFeedback) {
      kpiTotalFeedback.textContent = String(totalFeedback);
    }
  }

  function toTrendSparkline(trend7d) {
    const values = parseTrendSeries(trend7d);
    if (!values.length) return "-";
    const min = Math.min(...values);
    const max = Math.max(...values);
    const blocks = "▁▂▃▄▅▆▇█";
    if (max === min) {
      return values.map(() => "▅").join("");
    }
    return values
      .map((v) => {
        const idx = Math.max(
          0,
          Math.min(blocks.length - 1, Math.round(((v - min) / (max - min)) * (blocks.length - 1)))
        );
        return blocks[idx];
      })
      .join("");
  }

  function parseTrendSeries(trend7d) {
    const parts = String(trend7d || "")
      .split("|")
      .map((p) => p.trim())
      .filter(Boolean);
    return parts.map((part) => {
      const [a, s, r] = part.split("/").map((n) => Number(n || 0));
      return (a * 2) + s - (r * 2);
    });
  }

  function getTrendDelta(trend7d) {
    const series = parseTrendSeries(trend7d);
    if (series.length < 2) return 0;
    return series[series.length - 1] - series[0];
  }

  function formatSigned(v) {
    const num = Number(v || 0);
    return `${num > 0 ? "+" : ""}${num.toFixed(2)}`;
  }

  function getTrendDirectionArrow(delta) {
    const d = Number(delta || 0);
    if (d > 0) return "↑";
    if (d < 0) return "↓";
    return "→";
  }

  function getTrendDirectionStyle(delta) {
    const d = Number(delta || 0);
    if (d > 0) return "color:#15803d;font-weight:600;"; // green
    if (d < 0) return "color:#b91c1c;font-weight:600;"; // red
    return "color:#6b7280;font-weight:600;"; // neutral
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

  function escapeHtml(s) {
    const str = String(s == null ? "" : s);
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
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

  async function initLoanTrainingControls() {
    if (!loanModelStatusEl || !trainLoanBtn || !loanAppsBody) return;

    async function refreshModelStatus() {
      try {
        const status = await adminLoanModelStatus();
        loanModelStatusEl.textContent = status.trained
          ? `Model trained: ${status.trainedAt ? new Date(status.trainedAt).toLocaleString() : ""} (samples: ${status.samples})`
          : `Model not trained yet (need labeled samples).`;
      } catch (err) {
        loanModelStatusEl.textContent = `Failed to load model status: ${err.message || "error"}`;
      }
      if (loanScorecardModelStatusEl) {
        try {
          const s = await adminLoanScorecardModelStatus();
          loanScorecardModelStatusEl.textContent = s.trained
            ? `Credit scorecard trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
            : "Credit scorecard not trained yet (need labeled samples).";
        } catch (err) {
          loanScorecardModelStatusEl.textContent = `Failed to load scorecard status: ${err.message || "error"}`;
        }
      }
    }

    async function loadLoanApps() {
      loanAppsBody.innerHTML = '<tr><td colspan="9" class="muted text-center">Loading...</td></tr>';
      try {
        const apps = await adminListLoanSanctionApplications(15);
        if (!apps || !apps.length) {
          loanAppsBody.innerHTML =
            '<tr><td colspan="9" class="muted text-center">No applications yet.</td></tr>';
          return;
        }

        loanAppsBody.innerHTML = apps
          .map((a) => {
            const actual = a.actualRecommendation || "";
            const actualVal = actual || "";
            return `
              <tr>
                <td>${a.id}</td>
                <td>${a.accountNumber}</td>
                <td>${a.loanType}</td>
                <td>₹${Number(a.loanAmount || 0).toLocaleString("en-IN")}</td>
                <td>${Number(a.dti || 0).toFixed(3)}</td>
                <td>${a.recommendation}</td>
                <td>
                  <select data-loan-id="${a.id}" class="select">
                    <option value="" ${actualVal === "" ? "selected" : ""}>Unlabeled</option>
                    <option value="approve" ${actualVal === "approve" ? "selected" : ""}>approve</option>
                    <option value="manual_review" ${actualVal === "manual_review" ? "selected" : ""}>manual_review</option>
                    <option value="decline" ${actualVal === "decline" ? "selected" : ""}>decline</option>
                  </select>
                </td>
                <td>
                  <button class="btn btn-ghost btn-sm" type="button" data-loan-explain="${a.id}">
                    Explain
                  </button>
                </td>
                <td>
                  <button class="btn btn-ghost btn-sm" type="button" data-save-loan-label="${a.id}">
                    Save
                  </button>
                </td>
              </tr>
            `;
          })
          .join("");

        loanAppsBody.querySelectorAll("button[data-save-loan-label]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-save-loan-label"));
            const select = loanAppsBody.querySelector(`select[data-loan-id="${id}"]`);
            if (!select) return;
            const val = select.value;
            if (!val) {
              alert("Please choose a label value (approve/manual_review/decline).");
              return;
            }
            await adminLabelLoanSanctionApplication(id, val);
            await refreshModelStatus();
            await loadLoanApps();
          });
        });
        loanAppsBody.querySelectorAll("button[data-loan-explain]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-loan-explain"));
            if (!id) return;
            try {
              const ex = await adminExplainLoanScorecard(id);
              const lines = (ex.topContributions || [])
                .map(
                  (c) =>
                    `- ${c.feature}: value=${Number(c.value || 0).toFixed(3)}, impact=${Number(c.impact || 0).toFixed(4)}`
                )
                .join("\n");
              alert(
                `${ex.summary}\n\nApprove Probability: ${(Number(ex.approveProbability || 0) * 100).toFixed(
                  2
                )}%\nReject Probability: ${(Number(ex.rejectProbability || 0) * 100).toFixed(
                  2
                )}%\n\nTop Contributions:\n${lines || "- no contribution data"}`
              );
            } catch (err) {
              alert(`Failed to explain scorecard decision: ${err.message || "error"}`);
            }
          });
        });
      } catch (err) {
        loanAppsBody.innerHTML =
          '<tr><td colspan="9" class="muted text-center">Failed to load applications.</td></tr>';
        loanModelStatusEl.textContent = err.message || "Failed to load loan applications.";
      }
    }

    if (trainLoanBtn) {
      trainLoanBtn.addEventListener("click", async () => {
        loanModelStatusEl.textContent = "Training model...";
        try {
          const res = await adminTrainLoanSanctionModel();
          loanModelStatusEl.textContent = res.trained
            ? `Training complete: ${res.message} (samples: ${res.samples}, approveRate: ${(res.approveRate * 100).toFixed(1)}%)`
            : `Training not completed: ${res.message}`;
          await loadLoanApps();
        } catch (err) {
          loanModelStatusEl.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }
    if (trainLoanScorecardBtn) {
      trainLoanScorecardBtn.addEventListener("click", async () => {
        if (loanScorecardModelStatusEl) loanScorecardModelStatusEl.textContent = "Training credit scorecard...";
        try {
          const res = await adminTrainLoanScorecardModel();
          if (loanScorecardModelStatusEl) {
            loanScorecardModelStatusEl.textContent = res.trained
              ? `Scorecard training complete: ${res.message} (samples: ${res.samples}, approveRate: ${(res.approveRate * 100).toFixed(1)}%)`
              : `Scorecard training not completed: ${res.message}`;
          }
          await refreshModelStatus();
          await loadLoanApps();
        } catch (err) {
          if (loanScorecardModelStatusEl) {
            loanScorecardModelStatusEl.textContent = `Scorecard training failed: ${err.message || "error"}`;
          }
        }
      });
    }

    if (refreshLoanAppsBtn) {
      refreshLoanAppsBtn.addEventListener("click", loadLoanApps);
    }

    await refreshModelStatus();
    await loadLoanApps();
  }

  async function initFraudAlertControls() {
    if (!fraudAlertsBody) return;

    async function refreshFraudModelStatus() {
      if (!fraudModelStatusEl) return;
      try {
        const s = await adminFraudModelStatus();
        fraudModelStatusEl.textContent = s.trained
          ? `Fraud model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "Fraud model not trained yet (label at least 20 alerts).";
      } catch (err) {
        fraudModelStatusEl.textContent = `Failed to load fraud model status: ${err.message || "error"}`;
      }
    }

    async function refreshFraudRealtimeModelStatus() {
      if (!fraudRealtimeModelStatusEl) return;
      try {
        const s = await adminFraudRealtimeModelStatus();
        fraudRealtimeModelStatusEl.textContent = s.trained
          ? `Realtime fraud model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "Realtime fraud model not trained yet (label at least 40 alerts).";
      } catch (err) {
        fraudRealtimeModelStatusEl.textContent = `Failed to load realtime model status: ${err.message || "error"}`;
      }
    }

    async function loadFraudSummary() {
      try {
        const s = await adminFraudAlertSummary();
        if (fraudTotalEl) fraudTotalEl.textContent = String(s.total ?? 0);
        if (fraudOpenEl) fraudOpenEl.textContent = String(s.open ?? 0);
        if (fraudHighEl) fraudHighEl.textContent = String(s.high ?? 0);
        if (fraudBlockedEl) fraudBlockedEl.textContent = String(s.blocked ?? 0);
      } catch {
        // Keep current values; table load has its own errors.
      }
    }

    async function loadFraudAlerts() {
      fraudAlertsBody.innerHTML = '<tr><td colspan="10" class="muted text-center">Loading...</td></tr>';
      try {
        const status = fraudStatusFilter?.value || "all";
        const account = (fraudAccountFilter?.value || "").trim();
        const rows = await adminListFraudAlerts(30, status, account);
        if (!rows || !rows.length) {
          fraudAlertsBody.innerHTML =
            '<tr><td colspan="10" class="muted text-center">No fraud alerts for this filter.</td></tr>';
          await loadFraudSummary();
          await refreshFraudModelStatus();
          return;
        }
        fraudAlertsBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.id}</td>
            <td>${r.accountNumber}</td>
            <td>${r.transactionType}</td>
            <td>₹${Number(r.amount || 0).toLocaleString("en-IN")}</td>
            <td>${r.riskLevel} (${Number(r.riskScore || 0).toFixed(1)}) / ${Number(
              r.phase1Score || 0
            ).toFixed(1)}</td>
            <td title="${(r.reasons || []).join("; ")}">${(r.reasons || []).slice(0, 2).join(" | ") || "-"}</td>
            <td>
              <select data-fraud-id="${r.id}">
                <option value="open" ${r.status === "open" ? "selected" : ""}>open</option>
                <option value="reviewed" ${r.status === "reviewed" ? "selected" : ""}>reviewed</option>
                <option value="blocked" ${r.status === "blocked" ? "selected" : ""}>blocked</option>
              </select>
            </td>
            <td>
              <select data-fraud-label-id="${r.id}">
                <option value="" ${!r.actualLabel ? "selected" : ""}>unlabeled</option>
                <option value="fraud" ${r.actualLabel === "fraud" ? "selected" : ""}>fraud</option>
                <option value="legit" ${r.actualLabel === "legit" ? "selected" : ""}>legit</option>
              </select>
            </td>
            <td>${formatDateTime(r.createdAt)}</td>
            <td>
              <button class="btn btn-ghost btn-sm" type="button" data-fraud-save="${r.id}">Save</button>
            </td>
          </tr>
        `
          )
          .join("");

        fraudAlertsBody.querySelectorAll("button[data-fraud-save]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-fraud-save"));
            const select = fraudAlertsBody.querySelector(`select[data-fraud-id="${id}"]`);
            const labelSelect = fraudAlertsBody.querySelector(
              `select[data-fraud-label-id="${id}"]`
            );
            if (!id || !select) return;
            await adminUpdateFraudAlertStatus(id, select.value);
            if (labelSelect && labelSelect.value) {
              await adminLabelFraudAlert(id, labelSelect.value);
            }
            await loadFraudAlerts();
          });
        });
        await loadFraudSummary();
        await refreshFraudModelStatus();
        await refreshFraudRealtimeModelStatus();
      } catch (err) {
        fraudAlertsBody.innerHTML =
          '<tr><td colspan="10" class="muted text-center">Failed to load fraud alerts.</td></tr>';
      }
    }

    async function loadFraudNetwork() {
      if (!fraudNetworkBody) return;
      fraudNetworkBody.innerHTML = '<tr><td colspan="8" class="muted text-center">Loading...</td></tr>';
      try {
        const rows = await adminFraudNetworkHighRisk(25);
        if (!rows || !rows.length) {
          fraudNetworkBody.innerHTML =
            '<tr><td colspan="8" class="muted text-center">No medium/high network-risk accounts currently.</td></tr>';
          return;
        }
        fraudNetworkBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.accountNumber}</td>
            <td>${escapeHtml(r.name || "-")}</td>
            <td>${Number(r.fanIn30d || 0)}</td>
            <td>${Number(r.fanOut30d || 0)}</td>
            <td>${Number(r.receiverFanIn30d || 0)}</td>
            <td>${r.level} (${Number(r.muleRiskScore || 0).toFixed(1)})</td>
            <td title="${(r.reasons || []).join("; ")}">${(r.reasons || []).slice(0, 2).join(" | ") || "-"}</td>
            <td>
              <button
                class="btn btn-ghost btn-sm"
                type="button"
                data-fraud-net-action-account="${r.accountNumber}"
                data-fraud-net-action="${r.cardBlocked ? "unfreeze" : "freeze"}"
              >
                ${r.cardBlocked ? "Unfreeze" : "Freeze"}
              </button>
            </td>
          </tr>
        `
          )
          .join("");
        fraudNetworkBody.querySelectorAll("button[data-fraud-net-action-account]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const accountNumber = String(btn.getAttribute("data-fraud-net-action-account") || "").trim();
            const action = String(btn.getAttribute("data-fraud-net-action") || "").trim();
            if (!accountNumber || !action) return;
            const reason = prompt(`Reason to ${action} ${accountNumber}:`, "Fraud network review");
            if (reason === null) return;
            await adminFraudAccountAction(accountNumber, action, reason || "");
            await loadFraudAlerts();
            await loadFraudNetwork();
          });
        });
      } catch (err) {
        fraudNetworkBody.innerHTML =
          '<tr><td colspan="8" class="muted text-center">Failed to load network-risk accounts.</td></tr>';
      }
    }

    async function refreshAmlModelStatus() {
      if (!adminAmlModelStatusEl) return;
      try {
        const s = await adminAmlModelStatus();
        adminAmlModelStatusEl.textContent = s.trained
          ? `AML graph model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "AML graph model not trained yet (requires transaction graph + fraud labels).";
      } catch (err) {
        adminAmlModelStatusEl.textContent = `Failed to load AML model status: ${err.message || "error"}`;
      }
    }

    async function loadAmlRings() {
      if (!adminAmlRingsBody) return;
      adminAmlRingsBody.innerHTML = '<tr><td colspan="9" class="muted text-center">Loading...</td></tr>';
      try {
        const rows = await adminAmlSuspiciousRings(20, 0.65);
        if (!rows || !rows.length) {
          adminAmlRingsBody.innerHTML =
            '<tr><td colspan="9" class="muted text-center">No suspicious rings detected currently.</td></tr>';
          return;
        }
        adminAmlRingsBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${escapeHtml(r.ringId || "-")}</td>
            <td>${Number(r.riskScore || 0).toFixed(1)}</td>
            <td>${Number(r.accountCount || 0)}</td>
            <td>${Number(r.beneficiaryCount || 0)}</td>
            <td>${Number(r.deviceCount || 0)}</td>
            <td>${Number(r.ipCount || 0)}</td>
            <td title="${(r.accounts || []).join(", ")}">${(r.accounts || []).slice(0, 4).join(", ") || "-"}</td>
            <td title="${(r.reasons || []).join("; ")}">${(r.reasons || []).slice(0, 2).join(" | ") || "-"}</td>
            <td>
              <button class="btn btn-ghost btn-sm" type="button" data-aml-create-case='${JSON.stringify({
                ringId: r.ringId || "",
                riskScore: Number(r.riskScore || 0),
                accounts: (r.accounts || []).slice(0, 50),
                reasons: (r.reasons || []).slice(0, 10),
              }).replace(/'/g, "&apos;")}'>Create/Upsert Case</button>
            </td>
          </tr>
        `
          )
          .join("");
        adminAmlRingsBody.querySelectorAll("button[data-aml-create-case]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const raw = String(btn.getAttribute("data-aml-create-case") || "");
            if (!raw) return;
            const payload = JSON.parse(raw.replace(/&apos;/g, "'"));
            await adminCreateAmlCaseFromRing(payload);
            await loadAmlCases();
          });
        });
      } catch (err) {
        adminAmlRingsBody.innerHTML =
          '<tr><td colspan="9" class="muted text-center">Failed to load suspicious rings.</td></tr>';
      }
    }

    async function loadAmlCases() {
      if (!adminAmlCasesBody) return;
      adminAmlCasesBody.innerHTML = '<tr><td colspan="9" class="muted text-center">Loading...</td></tr>';
      try {
        const status = adminAmlCaseStatusFilter?.value || "all";
        const priority = adminAmlCasePriorityFilter?.value || "all";
        const watchlistOnly = String(adminAmlWatchlistOnly?.value || "false") === "true";
        const rows = await adminListAmlCases(50, status, priority, watchlistOnly);
        if (!rows || !rows.length) {
          adminAmlCasesBody.innerHTML = '<tr><td colspan="9" class="muted text-center">No AML cases.</td></tr>';
          return;
        }
        adminAmlCasesBody.innerHTML = rows
          .map(
            (c) => `
          <tr>
            <td>${c.id}</td>
            <td>${escapeHtml(c.ringId || "-")}</td>
            <td>${escapeHtml(c.priority || "medium")}</td>
            <td>${escapeHtml(c.status || "open")}</td>
            <td>${c.watchlist ? "yes" : "no"}</td>
            <td>${Number(c.riskScore || 0).toFixed(1)}</td>
            <td>${escapeHtml(c.assignee || "-")}</td>
            <td title="${(c.accounts || []).join(", ")}">${(c.accounts || []).slice(0, 3).join(", ") || "-"}</td>
            <td>
              <button class="btn btn-ghost btn-sm" type="button" data-aml-case-edit="${c.id}">Update</button>
            </td>
          </tr>
        `
          )
          .join("");
        adminAmlCasesBody.querySelectorAll("button[data-aml-case-edit]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const caseId = Number(btn.getAttribute("data-aml-case-edit"));
            if (!caseId) return;
            const statusVal = prompt("Status (open/investigating/escalated/closed):", "investigating");
            if (statusVal === null) return;
            const priorityVal = prompt("Priority (low/medium/high/critical):", "high");
            if (priorityVal === null) return;
            const watchlistVal = prompt("Watchlist? (yes/no):", "yes");
            if (watchlistVal === null) return;
            const assigneeVal = prompt("Assignee:", "AML Team");
            if (assigneeVal === null) return;
            const notesVal = prompt("Notes:", "Phase-1.5 AML review");
            if (notesVal === null) return;
            await adminUpdateAmlCase({
              caseId,
              status: String(statusVal || "open").trim().toLowerCase(),
              priority: String(priorityVal || "medium").trim().toLowerCase(),
              watchlist: String(watchlistVal || "no").trim().toLowerCase().startsWith("y"),
              assignee: String(assigneeVal || "").trim(),
              notes: String(notesVal || "").trim(),
            });
            await loadAmlCases();
          });
        });
      } catch (err) {
        adminAmlCasesBody.innerHTML = '<tr><td colspan="9" class="muted text-center">Failed to load AML cases.</td></tr>';
      }
    }

    async function loadAmlAlertLinks() {
      if (!adminAmlAlertLinksBody) return;
      adminAmlAlertLinksBody.innerHTML = '<tr><td colspan="6" class="muted text-center">Loading...</td></tr>';
      try {
        const rows = await adminAmlCaseAlertLinks(80);
        if (!rows || !rows.length) {
          adminAmlAlertLinksBody.innerHTML = '<tr><td colspan="6" class="muted text-center">No linkage data.</td></tr>';
          return;
        }
        adminAmlAlertLinksBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.caseId}</td>
            <td>${escapeHtml(r.ringId || "-")}</td>
            <td>${Number(r.linkedAlerts || 0)}</td>
            <td>${Number(r.highRiskAlerts || 0)}</td>
            <td>${Number(r.blockedAlerts || 0)}</td>
            <td>${r.latestAlertAt ? formatDateTime(r.latestAlertAt) : "-"}</td>
          </tr>
        `
          )
          .join("");
      } catch {
        adminAmlAlertLinksBody.innerHTML =
          '<tr><td colspan="6" class="muted text-center">Failed to load linkage data.</td></tr>';
      }
    }

    if (fraudStatusFilter) {
      fraudStatusFilter.addEventListener("change", loadFraudAlerts);
    }
    if (fraudAccountFilter) {
      fraudAccountFilter.addEventListener("change", loadFraudAlerts);
      fraudAccountFilter.addEventListener("keyup", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          loadFraudAlerts();
        }
      });
    }
    if (trainFraudModelBtn) {
      trainFraudModelBtn.addEventListener("click", async () => {
        if (fraudModelStatusEl) fraudModelStatusEl.textContent = "Training fraud model...";
        try {
          const res = await adminTrainFraudModel();
          if (fraudModelStatusEl) {
            fraudModelStatusEl.textContent = res.trained
              ? `Training complete: ${res.message} (samples: ${res.samples}, fraudRate: ${(res.fraudRate * 100).toFixed(
                  1
                )}%)`
              : `Training not completed: ${res.message}`;
          }
          await refreshFraudModelStatus();
          await loadFraudAlerts();
        } catch (err) {
          if (fraudModelStatusEl) fraudModelStatusEl.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }
    if (trainFraudRealtimeModelBtn) {
      trainFraudRealtimeModelBtn.addEventListener("click", async () => {
        if (fraudRealtimeModelStatusEl) fraudRealtimeModelStatusEl.textContent = "Training realtime fraud model...";
        try {
          const res = await adminTrainFraudRealtimeModel();
          if (fraudRealtimeModelStatusEl) {
            fraudRealtimeModelStatusEl.textContent = res.trained
              ? `Realtime training complete: ${res.message} (samples: ${res.samples}, fraudRate: ${(res.fraudRate * 100).toFixed(
                  1
                )}%)`
              : `Realtime training not completed: ${res.message}`;
          }
          await refreshFraudRealtimeModelStatus();
          await loadFraudAlerts();
        } catch (err) {
          if (fraudRealtimeModelStatusEl) {
            fraudRealtimeModelStatusEl.textContent = `Realtime training failed: ${err.message || "error"}`;
          }
        }
      });
    }
    if (refreshFraudNetworkBtn) {
      refreshFraudNetworkBtn.addEventListener("click", loadFraudNetwork);
    }
    if (adminTrainAmlModelBtn) {
      adminTrainAmlModelBtn.addEventListener("click", async () => {
        if (adminAmlModelStatusEl) adminAmlModelStatusEl.textContent = "Training AML graph model...";
        try {
          const res = await adminTrainAmlModel();
          if (adminAmlModelStatusEl) {
            adminAmlModelStatusEl.textContent = res.trained
              ? `AML training complete: ${res.message}`
              : `AML training not completed: ${res.message}`;
          }
          await refreshAmlModelStatus();
          await loadAmlRings();
          await loadAmlCases();
        } catch (err) {
          if (adminAmlModelStatusEl) adminAmlModelStatusEl.textContent = `AML training failed: ${err.message || "error"}`;
        }
      });
    }
    if (adminRunAmlAutomationBtn) {
      adminRunAmlAutomationBtn.addEventListener("click", async () => {
        if (adminAmlModelStatusEl) adminAmlModelStatusEl.textContent = "Running AML automation...";
        try {
          const res = await adminRunAmlAutomation(0.75, 80, 24);
          if (adminAmlModelStatusEl) {
            adminAmlModelStatusEl.textContent = `AML automation done: ${res.message} (processed ${res.processedRings}, created ${res.createdCases}, updated ${res.updatedCases}, escalated ${res.escalatedCases})`;
          }
          await loadAmlCases();
          await loadAmlAlertLinks();
        } catch (err) {
          if (adminAmlModelStatusEl) adminAmlModelStatusEl.textContent = `AML automation failed: ${err.message || "error"}`;
        }
      });
    }
    if (adminRefreshAmlRingsBtn) {
      adminRefreshAmlRingsBtn.addEventListener("click", loadAmlRings);
    }
    if (adminRefreshAmlCasesBtn) {
      adminRefreshAmlCasesBtn.addEventListener("click", loadAmlCases);
    }
    if (adminRefreshAmlAlertLinksBtn) {
      adminRefreshAmlAlertLinksBtn.addEventListener("click", loadAmlAlertLinks);
    }
    if (adminAmlCaseStatusFilter) adminAmlCaseStatusFilter.addEventListener("change", loadAmlCases);
    if (adminAmlCasePriorityFilter) adminAmlCasePriorityFilter.addEventListener("change", loadAmlCases);
    if (adminAmlWatchlistOnly) adminAmlWatchlistOnly.addEventListener("change", loadAmlCases);
    await loadFraudSummary();
    await refreshFraudModelStatus();
    await refreshFraudRealtimeModelStatus();
    await loadFraudAlerts();
    await loadFraudNetwork();
    await refreshAmlModelStatus();
    await loadAmlRings();
    await loadAmlCases();
    await loadAmlAlertLinks();
  }

  async function initCreditRiskControls() {
    if (!creditRiskBody) return;

    async function refreshCreditRiskModelStatus() {
      if (!creditRiskModelStatusEl) return;
      try {
        const s = await adminCreditRiskModelStatus();
        creditRiskModelStatusEl.textContent = s.trained
          ? `Credit risk model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "Credit risk model not trained yet (label at least 30 snapshots).";
      } catch (err) {
        creditRiskModelStatusEl.textContent = `Failed to load credit risk model status: ${err.message || "error"}`;
      }
    }

    async function loadHighRisk() {
      creditRiskBody.innerHTML = '<tr><td colspan="6" class="muted text-center">Loading...</td></tr>';
      try {
        const rows = await adminCreditRiskHighRisk(25, "high");
        if (!rows || !rows.length) {
          creditRiskBody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">No high-risk accounts currently.</td></tr>';
          return;
        }
        creditRiskBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.accountNumber}</td>
            <td>${r.name}</td>
            <td>₹${Number(r.balance || 0).toLocaleString("en-IN")}</td>
            <td>${r.level} (${Number(r.score || 0).toFixed(1)})</td>
            <td title="${(r.reasons || []).join("; ")}">${(r.reasons || []).slice(0, 2).join(" | ") || "-"}</td>
            <td>${formatDateTime(r.periodEnd)}</td>
          </tr>
        `
          )
          .join("");
      } catch (err) {
        creditRiskBody.innerHTML =
          '<tr><td colspan="6" class="muted text-center">Failed to load credit risk.</td></tr>';
      }
    }

    async function loadSnapshots() {
      if (!creditRiskSnapshotsBody) return;
      creditRiskSnapshotsBody.innerHTML = '<tr><td colspan="6" class="muted text-center">Loading...</td></tr>';
      try {
        const snaps = await adminListCreditRiskSnapshots(40);
        if (!snaps || !snaps.length) {
          creditRiskSnapshotsBody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">No snapshots yet.</td></tr>';
          return;
        }
        creditRiskSnapshotsBody.innerHTML = snaps
          .map(
            (s) => `
          <tr>
            <td>${s.id}</td>
            <td>${s.accountNumber}</td>
            <td>${s.level} (${Number(s.score || 0).toFixed(1)}) / ${Number(s.phase1Score || 0).toFixed(1)}</td>
            <td>
              <select data-cr-snap="${s.id}">
                <option value="" ${!s.actualLabel ? "selected" : ""}>unlabeled</option>
                <option value="defaulted" ${s.actualLabel === "defaulted" ? "selected" : ""}>defaulted</option>
                <option value="on_time" ${s.actualLabel === "on_time" ? "selected" : ""}>on_time</option>
              </select>
            </td>
            <td>${formatDateTime(s.periodEnd)}</td>
            <td>
              <button class="btn btn-ghost btn-sm" type="button" data-cr-save="${s.id}">Save</button>
            </td>
          </tr>
        `
          )
          .join("");

        creditRiskSnapshotsBody.querySelectorAll("button[data-cr-save]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-cr-save"));
            const sel = creditRiskSnapshotsBody.querySelector(`select[data-cr-snap="${id}"]`);
            if (!id || !sel || !sel.value) return;
            await adminLabelCreditRiskSnapshot(id, sel.value);
            await refreshCreditRiskModelStatus();
            await loadSnapshots();
          });
        });
      } catch (err) {
        creditRiskSnapshotsBody.innerHTML =
          '<tr><td colspan="6" class="muted text-center">Failed to load snapshots.</td></tr>';
      }
    }

    if (refreshCreditRiskBtn) {
      refreshCreditRiskBtn.addEventListener("click", loadHighRisk);
    }
    if (refreshCreditRiskSnapshotsBtn) {
      refreshCreditRiskSnapshotsBtn.addEventListener("click", loadSnapshots);
    }
    if (trainCreditRiskModelBtn) {
      trainCreditRiskModelBtn.addEventListener("click", async () => {
        if (creditRiskModelStatusEl) creditRiskModelStatusEl.textContent = "Training credit risk model...";
        try {
          const res = await adminTrainCreditRiskModel();
          if (creditRiskModelStatusEl) {
            creditRiskModelStatusEl.textContent = res.trained
              ? `Training complete: ${res.message} (samples: ${res.samples}, defaultRate: ${(res.defaultRate * 100).toFixed(
                  1
                )}%)`
              : `Training not completed: ${res.message}`;
          }
          await refreshCreditRiskModelStatus();
          await loadSnapshots();
          await loadHighRisk();
        } catch (err) {
          if (creditRiskModelStatusEl) creditRiskModelStatusEl.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }

    await refreshCreditRiskModelStatus();
    await loadHighRisk();
    await loadSnapshots();
  }

  async function initChurnControls() {
    if (!churnBody) return;

    async function refreshChurnModelStatus() {
      if (!churnModelStatusEl) return;
      try {
        const s = await adminChurnModelStatus();
        churnModelStatusEl.textContent = s.trained
          ? `Churn model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "Churn model not trained yet (label at least 30 snapshots).";
      } catch (err) {
        churnModelStatusEl.textContent = `Failed to load churn model status: ${err.message || "error"}`;
      }
    }

    async function refreshChurnNbaModelStatus() {
      if (!churnNbaModelStatusEl) return;
      try {
        const s = await adminChurnNbaModelStatus();
        churnNbaModelStatusEl.textContent = s.trained
          ? `NBA model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "NBA model not trained yet (label at least 60 churn snapshots).";
      } catch (err) {
        churnNbaModelStatusEl.textContent = `Failed to load NBA model status: ${err.message || "error"}`;
      }
    }

    async function loadChurn() {
      churnBody.innerHTML = '<tr><td colspan="7" class="muted text-center">Loading...</td></tr>';
      try {
        const rows = await adminChurnHighRisk(25, "high");
        if (!rows || !rows.length) {
          churnBody.innerHTML =
            '<tr><td colspan="7" class="muted text-center">No high churn risk users currently.</td></tr>';
          return;
        }
        churnBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.accountNumber}</td>
            <td>${r.name}</td>
            <td>₹${Number(r.balance || 0).toLocaleString("en-IN")}</td>
            <td>${r.level} (${Number(r.score || 0).toFixed(1)})</td>
            <td>${r.lastActiveAt ? formatDateTime(r.lastActiveAt) : "-"}</td>
            <td title="${(r.reasons || []).join("; ")}">${(r.reasons || []).slice(0, 2).join(" | ") || "-"}</td>
            <td>${
              r.nextBestOffer
                ? `${escapeHtml(String(r.nextBestOffer).replace(/_/g, " "))}${
                    r.expectedRetentionLift != null ? ` (+${(Number(r.expectedRetentionLift) * 100).toFixed(1)}%)` : ""
                  }`
                : "-"
            }</td>
          </tr>
        `
          )
          .join("");
      } catch (err) {
        churnBody.innerHTML =
          '<tr><td colspan="7" class="muted text-center">Failed to load churn risk.</td></tr>';
      }
    }

    async function loadChurnSnapshots() {
      if (!churnSnapshotsBody) return;
      churnSnapshotsBody.innerHTML = '<tr><td colspan="6" class="muted text-center">Loading...</td></tr>';
      try {
        const snaps = await adminListChurnSnapshots(40);
        if (!snaps || !snaps.length) {
          churnSnapshotsBody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">No snapshots yet.</td></tr>';
          return;
        }
        churnSnapshotsBody.innerHTML = snaps
          .map(
            (s) => `
          <tr>
            <td>${s.id}</td>
            <td>${s.accountNumber}</td>
            <td>${s.level} (${Number(s.score || 0).toFixed(1)}) / ${Number(s.phase1Score || 0).toFixed(1)}</td>
            <td>
              <select data-churn-snap="${s.id}">
                <option value="" ${!s.actualLabel ? "selected" : ""}>unlabeled</option>
                <option value="churned" ${s.actualLabel === "churned" ? "selected" : ""}>churned</option>
                <option value="retained" ${s.actualLabel === "retained" ? "selected" : ""}>retained</option>
              </select>
            </td>
            <td>${formatDateTime(s.createdAt)}</td>
            <td>
              <button class="btn btn-ghost btn-sm" type="button" data-churn-save="${s.id}">Save</button>
            </td>
          </tr>
        `
          )
          .join("");

        churnSnapshotsBody.querySelectorAll("button[data-churn-save]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-churn-save"));
            const sel = churnSnapshotsBody.querySelector(`select[data-churn-snap="${id}"]`);
            if (!id || !sel || !sel.value) return;
            await adminLabelChurnSnapshot(id, sel.value);
            await refreshChurnModelStatus();
            await loadChurnSnapshots();
          });
        });
      } catch (err) {
        churnSnapshotsBody.innerHTML =
          '<tr><td colspan="6" class="muted text-center">Failed to load snapshots.</td></tr>';
      }
    }

    async function loadChurnNbaOfferPerf() {
      if (churnNbaPerfChart) churnNbaPerfChart.innerHTML = '<p class="muted">Loading offer performance...</p>';
      if (churnNbaPerfBody) {
        churnNbaPerfBody.innerHTML = '<tr><td colspan="5" class="muted text-center">Loading...</td></tr>';
      }
      try {
        const rows = await adminChurnNbaOfferPerformance(500);
        if (!rows || !rows.length) {
          if (churnNbaPerfChart) churnNbaPerfChart.innerHTML = '<p class="muted">No NBA offer data yet.</p>';
          if (churnNbaPerfBody) {
            churnNbaPerfBody.innerHTML = '<tr><td colspan="5" class="muted text-center">No offer performance yet.</td></tr>';
          }
          return;
        }
        const maxVal = Math.max(...rows.map((r) => Number(r.avgUplift || 0)), 0.0001);
        if (churnNbaPerfChart) {
          churnNbaPerfChart.innerHTML = rows
            .map((r) => {
              const name = String(r.offer || "").replace(/_/g, " ");
              const v = Number(r.avgUplift || 0);
              const pct = Math.max(4, Math.round((v / maxVal) * 100));
              return `
                <div class="mt-sm">
                  <div class="muted" style="display:flex;justify-content:space-between;gap:12px;">
                    <span>${escapeHtml(name)}</span><span>${(v * 100).toFixed(1)}%</span>
                  </div>
                  <div style="height:10px;background:#e5e7eb;border-radius:999px;overflow:hidden;">
                    <div style="height:100%;width:${pct}%;background:#2563eb;"></div>
                  </div>
                </div>
              `;
            })
            .join("");
        }
        if (churnNbaPerfBody) {
          churnNbaPerfBody.innerHTML = rows
            .map(
              (r) => `
              <tr>
                <td>${escapeHtml(String(r.offer || "").replace(/_/g, " "))}</td>
                <td>${(Number(r.avgUplift || 0) * 100).toFixed(2)}%</td>
                <td>${Number(r.recommendedUsers || 0)}</td>
                <td>${Number(r.highRiskUsers || 0)}</td>
                <td>${Number(r.mediumRiskUsers || 0)}</td>
              </tr>
            `
            )
            .join("");
        }
      } catch (err) {
        if (churnNbaPerfChart) churnNbaPerfChart.innerHTML = `<p class="muted">Failed to load offer performance: ${escapeHtml(err.message || "error")}.</p>`;
        if (churnNbaPerfBody) {
          churnNbaPerfBody.innerHTML = '<tr><td colspan="5" class="muted text-center">Failed to load offer performance.</td></tr>';
        }
      }
    }

    if (refreshChurnBtn) {
      refreshChurnBtn.addEventListener("click", loadChurn);
    }
    if (refreshChurnSnapshotsBtn) {
      refreshChurnSnapshotsBtn.addEventListener("click", loadChurnSnapshots);
    }
    if (refreshChurnNbaPerfBtn) {
      refreshChurnNbaPerfBtn.addEventListener("click", loadChurnNbaOfferPerf);
    }
    if (trainChurnModelBtn) {
      trainChurnModelBtn.addEventListener("click", async () => {
        if (churnModelStatusEl) churnModelStatusEl.textContent = "Training churn model...";
        try {
          const res = await adminTrainChurnModel();
          if (churnModelStatusEl) {
            churnModelStatusEl.textContent = res.trained
              ? `Training complete: ${res.message} (samples: ${res.samples}, churnRate: ${(res.churnRate * 100).toFixed(
                  1
                )}%)`
              : `Training not completed: ${res.message}`;
          }
          await refreshChurnModelStatus();
          await loadChurnSnapshots();
          await loadChurn();
        } catch (err) {
          if (churnModelStatusEl) churnModelStatusEl.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }
    if (trainChurnNbaModelBtn) {
      trainChurnNbaModelBtn.addEventListener("click", async () => {
        if (churnNbaModelStatusEl) churnNbaModelStatusEl.textContent = "Training churn NBA model...";
        try {
          const res = await adminTrainChurnNbaModel();
          if (churnNbaModelStatusEl) {
            churnNbaModelStatusEl.textContent = res.trained
              ? `Training complete: ${res.message} (samples: ${res.samples})`
              : `Training not completed: ${res.message}`;
          }
          await refreshChurnNbaModelStatus();
          await loadChurn();
          await loadChurnNbaOfferPerf();
        } catch (err) {
          if (churnNbaModelStatusEl) churnNbaModelStatusEl.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }

    await refreshChurnModelStatus();
    await refreshChurnNbaModelStatus();
    await loadChurn();
    await loadChurnSnapshots();
    await loadChurnNbaOfferPerf();
  }

  async function initKbControls() {
    if (!kbForm || !kbBody) return;

    kbForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = (document.getElementById("adminKbId").value || "").trim();
      const title = (document.getElementById("adminKbTitle").value || "").trim();
      const tags = (document.getElementById("adminKbTags").value || "").trim();
      const content = (document.getElementById("adminKbContent").value || "").trim();
      const active = (document.getElementById("adminKbActive").value || "true") === "true";

      if (!content || content.length < 10) {
        alert("Please enter KB content (at least 10 characters).");
        return;
      }

      try {
        if (id) {
          await adminUpdateKbDoc(id, { title, tags, content, active });
        } else {
          await adminCreateKbDoc({ title, tags, content, active });
        }
        resetKbForm();
        await refreshKb();
      } catch (err) {
        alert(err.message || "Failed to save KB document.");
      }
    });

    if (kbResetBtn) kbResetBtn.addEventListener("click", resetKbForm);
    if (kbRefreshBtn) kbRefreshBtn.addEventListener("click", refreshKb);
    await refreshKb();
  }

  function resetKbForm() {
    const idEl = document.getElementById("adminKbId");
    const titleEl = document.getElementById("adminKbTitle");
    const tagsEl = document.getElementById("adminKbTags");
    const contentEl = document.getElementById("adminKbContent");
    const activeEl = document.getElementById("adminKbActive");
    if (idEl) idEl.value = "";
    if (titleEl) titleEl.value = "";
    if (tagsEl) tagsEl.value = "";
    if (contentEl) contentEl.value = "";
    if (activeEl) activeEl.value = "true";
  }

  async function refreshKb() {
    if (!kbBody) return;
    try {
      const docs = await adminListKbDocs();
      renderKbTable(docs || []);
    } catch (err) {
      kbBody.innerHTML = `<tr><td colspan="6" class="muted text-center">${
        err.message || "Failed to load KB documents."
      }</td></tr>`;
    }
  }

  function renderKbTable(docs) {
    if (!kbBody) return;
    if (!docs.length) {
      kbBody.innerHTML =
        '<tr><td colspan="6" class="muted text-center">No KB documents yet.</td></tr>';
      return;
    }
    kbBody.innerHTML = docs
      .map((d) => {
        const created = d.createdAt ? formatDateTime(d.createdAt) : "";
        return `
        <tr data-kb-id="${d.id}">
          <td>${d.id}</td>
          <td>${escapeHtml(d.title || "")}</td>
          <td class="muted">${escapeHtml(d.tags || "")}</td>
          <td>${d.active ? "Active" : "Inactive"}</td>
          <td>${created}</td>
          <td>
            <button class="icon-button" title="Edit" data-kb-edit>✎</button>
            <button class="icon-button" title="Delete" data-kb-delete>🗑</button>
          </td>
        </tr>
      `;
      })
      .join("");

    kbBody.querySelectorAll("tr").forEach((row) => {
      const id = row.getAttribute("data-kb-id");
      if (!id) return;
      const doc = docs.find((x) => String(x.id) === String(id));
      if (!doc) return;
      const editBtn = row.querySelector("button[data-kb-edit]");
      const delBtn = row.querySelector("button[data-kb-delete]");
      if (editBtn) {
        editBtn.addEventListener("click", () => {
          document.getElementById("adminKbId").value = String(doc.id);
          document.getElementById("adminKbTitle").value = doc.title || "";
          document.getElementById("adminKbTags").value = doc.tags || "";
          document.getElementById("adminKbContent").value = doc.content || "";
          document.getElementById("adminKbActive").value = doc.active ? "true" : "false";
          window.scrollTo({ top: kbForm.offsetTop - 24, behavior: "smooth" });
        });
      }
      if (delBtn) {
        delBtn.addEventListener("click", async () => {
          if (!confirm("Delete this KB document?")) return;
          try {
            await adminDeleteKbDoc(doc.id);
            await refreshKb();
          } catch (err) {
            alert(err.message || "Failed to delete KB document.");
          }
        });
      }
    });
  }

  async function initVoiceAuditControls() {
    if (!voiceAuditBody) return;

    async function refreshVoiceAudit() {
      try {
        const logs = await adminVoiceAudit(
          80,
          (voiceAccountFilter && voiceAccountFilter.value.trim()) || "",
          (voiceIntentFilter && voiceIntentFilter.value) || "",
          (voiceStatusFilter && voiceStatusFilter.value) || ""
        );
        if (!logs || !logs.length) {
          voiceAuditBody.innerHTML =
            '<tr><td colspan="8" class="muted text-center">No voice logs found.</td></tr>';
          return;
        }
        voiceAuditBody.innerHTML = logs
          .map(
            (l) => `
          <tr>
            <td>${l.id}</td>
            <td>${l.accountNumber}</td>
            <td>${escapeHtml(l.intent || "")}</td>
            <td>${escapeHtml(l.status || "")}</td>
            <td>${l.requiresStepUp ? "Yes" : "No"}</td>
            <td>${Number(l.confidence || 0).toFixed(3)}</td>
            <td title="${escapeHtml(l.transcript || "")}">${escapeHtml(l.transcript || "").slice(0, 48)}</td>
            <td>${formatDateTime(l.createdAt)}</td>
          </tr>
        `
          )
          .join("");
      } catch (err) {
        voiceAuditBody.innerHTML =
          '<tr><td colspan="8" class="muted text-center">Failed to load voice logs.</td></tr>';
      }
    }

    if (voiceRefreshBtn) voiceRefreshBtn.addEventListener("click", refreshVoiceAudit);
    if (voiceIntentFilter) voiceIntentFilter.addEventListener("change", refreshVoiceAudit);
    if (voiceStatusFilter) voiceStatusFilter.addEventListener("change", refreshVoiceAudit);
    if (voiceAccountFilter) {
      voiceAccountFilter.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          refreshVoiceAudit();
        }
      });
    }

    await refreshVoiceAudit();
  }

  async function initKycAdminControls() {
    if (!adminKycBody) return;

    async function loadKyc() {
      const st = adminKycStatusFilter ? adminKycStatusFilter.value : "";
      try {
        const rows = await adminKycSubmissions(80, st);
        if (!rows || !rows.length) {
          adminKycBody.innerHTML =
            '<tr><td colspan="9" class="muted text-center">No KYC submissions yet.</td></tr>';
          return;
        }
        adminKycBody.innerHTML = rows
          .map(
            (r) => `
          <tr data-kyc-id="${r.id}">
            <td>${r.id}</td>
            <td>${escapeHtml(r.accountNumber)}</td>
            <td>${escapeHtml(r.name || "")}</td>
            <td>${escapeHtml(r.status)}</td>
            <td>${Number(r.livenessScore || 0).toFixed(2)}</td>
            <td>${r.faceDistance != null ? Number(r.faceDistance).toFixed(4) : "-"}</td>
            <td>${Number(r.nameMatchScore || 0).toFixed(2)}</td>
            <td>${formatDateTime(r.createdAt)}</td>
            <td>
              ${
                r.status === "manual_review" || r.status === "rejected"
                  ? `<button type="button" class="btn btn-ghost btn-sm" data-kyc-approve="${r.id}">Approve</button>`
                  : "-"
              }
            </td>
          </tr>
        `
          )
          .join("");

        adminKycBody.querySelectorAll("button[data-kyc-approve]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-kyc-approve"));
            if (!id || !confirm("Approve this KYC submission?")) return;
            try {
              await adminKycApprove(id);
              await loadKyc();
            } catch (err) {
              alert(err.message || "Approve failed.");
            }
          });
        });
      } catch {
        adminKycBody.innerHTML =
          '<tr><td colspan="9" class="muted text-center">Failed to load KYC submissions.</td></tr>';
      }
    }

    if (adminKycRefreshBtn) adminKycRefreshBtn.addEventListener("click", loadKyc);
    if (adminKycStatusFilter) adminKycStatusFilter.addEventListener("change", loadKyc);
    await loadKyc();
  }

  async function initLoanDocumentAiAdminControls() {
    if (!adminLoanDocAiBody) return;

    async function refreshModelStatus() {
      if (!adminLoanDocModelStatus) return;
      try {
        const s = await adminLoanDocumentAiModelStatus();
        adminLoanDocModelStatus.textContent = s.trained
          ? `Model trained: ${s.trainedAt ? new Date(s.trainedAt).toLocaleString() : ""} (samples: ${s.samples})`
          : "Model not trained yet (review and label document logs first).";
      } catch (err) {
        adminLoanDocModelStatus.textContent = `Failed to load model status: ${err.message || "error"}`;
      }
    }

    async function loadLogs() {
      const reviewStatus = (adminLoanDocReviewStatusFilter && adminLoanDocReviewStatusFilter.value) || "";
      const accountNumber = (adminLoanDocAccountFilter && adminLoanDocAccountFilter.value.trim()) || "";
      try {
        const rows = await adminListLoanDocumentAiLogs(80, reviewStatus, accountNumber);
        if (!rows || !rows.length) {
          adminLoanDocAiBody.innerHTML =
            '<tr><td colspan="8" class="muted text-center">No document AI logs found.</td></tr>';
          return;
        }
        adminLoanDocAiBody.innerHTML = rows
          .map(
            (r) => `
          <tr data-doc-log-id="${r.id}">
            <td>${r.id}</td>
            <td>${escapeHtml(r.accountNumber)}</td>
            <td title="${escapeHtml(r.fileName || "")}">${escapeHtml((r.fileName || "").slice(0, 22))}</td>
            <td>${escapeHtml(r.documentType || "-")}</td>
            <td>${r.monthlyIncomeExtracted != null ? Number(r.monthlyIncomeExtracted).toFixed(2) : "-"}</td>
            <td>${r.existingEmiExtracted != null ? Number(r.existingEmiExtracted).toFixed(2) : "-"}</td>
            <td>${escapeHtml(r.reviewStatus || "pending")}</td>
            <td><button type="button" class="btn btn-ghost btn-sm" data-doc-review="${r.id}">Review</button></td>
          </tr>
        `
          )
          .join("");

        adminLoanDocAiBody.querySelectorAll("button[data-doc-review]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const id = Number(btn.getAttribute("data-doc-review"));
            if (!id) return;
            const correctedDocumentType =
              prompt("Corrected document type? (salary_slip / bank_statement / unknown). Leave blank to keep.") || "";
            const correctedMonthlyIncomeRaw =
              prompt("Corrected monthly income (optional). Leave blank to keep.") || "";
            const correctedExistingEmiRaw =
              prompt("Corrected EMI total (optional). Leave blank to keep.") || "";
            const reviewStatusInput =
              (prompt("Review status? (approved / needs_correction / rejected)", "approved") || "approved").trim();
            const reviewerNotes = prompt("Reviewer notes (optional)") || "";

            const payload = {
              logId: id,
              correctedDocumentType: correctedDocumentType ? correctedDocumentType : null,
              correctedMonthlyIncome:
                correctedMonthlyIncomeRaw.trim() === "" ? null : Number(correctedMonthlyIncomeRaw),
              correctedExistingEmi:
                correctedExistingEmiRaw.trim() === "" ? null : Number(correctedExistingEmiRaw),
              reviewStatus: reviewStatusInput || "approved",
              reviewerNotes,
            };
            try {
              await adminReviewLoanDocumentAi(payload);
              await loadLogs();
            } catch (err) {
              alert(err.message || "Failed to save review.");
            }
          });
        });
      } catch (err) {
        adminLoanDocAiBody.innerHTML =
          '<tr><td colspan="8" class="muted text-center">Failed to load loan document AI logs.</td></tr>';
      }
    }

    if (adminLoanDocRefreshBtn) adminLoanDocRefreshBtn.addEventListener("click", loadLogs);
    if (adminLoanDocReviewStatusFilter) adminLoanDocReviewStatusFilter.addEventListener("change", loadLogs);
    if (adminLoanDocTrainBtn) {
      adminLoanDocTrainBtn.addEventListener("click", async () => {
        if (adminLoanDocModelStatus) adminLoanDocModelStatus.textContent = "Training document AI model...";
        try {
          const res = await adminTrainLoanDocumentAiModel();
          if (adminLoanDocModelStatus) {
            adminLoanDocModelStatus.textContent = res.trained
              ? `Training complete: ${res.message} (samples: ${res.samples})`
              : `Training not completed: ${res.message}`;
          }
          await refreshModelStatus();
        } catch (err) {
          if (adminLoanDocModelStatus) adminLoanDocModelStatus.textContent = `Training failed: ${err.message || "error"}`;
        }
      });
    }
    if (adminLoanDocAccountFilter) {
      adminLoanDocAccountFilter.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          loadLogs();
        }
      });
    }
    await refreshModelStatus();
    await loadLogs();
  }

  async function initSupportAuditControls() {
    if (!adminSupportChatsBody) return;

    async function loadSummary() {
      try {
        const fromDate = (adminSupportFromDate?.value || "").trim();
        const toDate = (adminSupportToDate?.value || "").trim();
        const s = await adminSupportChatsSummary(fromDate, toDate);
        if (adminSupportTotal) adminSupportTotal.textContent = String(s.total ?? 0);
        if (adminSupportBlocked) adminSupportBlocked.textContent = String(s.blocked ?? 0);
        if (adminSupportSafe) adminSupportSafe.textContent = String(s.safe ?? 0);
      } catch {
        // table loader handles errors
      }
    }

    async function loadRows() {
      adminSupportChatsBody.innerHTML = '<tr><td colspan="6" class="muted text-center">Loading...</td></tr>';
      try {
        const blockedOnly = String(adminSupportBlockedOnly?.value || "false") === "true";
        const account = (adminSupportAccountFilter?.value || "").trim();
        const fromDate = (adminSupportFromDate?.value || "").trim();
        const toDate = (adminSupportToDate?.value || "").trim();
        const rows = await adminSupportChats(60, blockedOnly, account, fromDate, toDate);
        if (!rows || !rows.length) {
          adminSupportChatsBody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">No support chats for this filter.</td></tr>';
          await loadSummary();
          return;
        }
        adminSupportChatsBody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${r.id}</td>
            <td>${escapeHtml(r.accountNumber || "-")}</td>
            <td>${r.blockedForPrivacy ? "yes" : "no"}</td>
            <td title="${(r.sourceTitles || []).join("; ")}">${Number(r.sourceCount || 0)}</td>
            <td title="${escapeHtml(r.userMessage || "-")}">${escapeHtml(String(r.userMessage || "-").slice(0, 140))}</td>
            <td>${formatDateTime(r.createdAt)}</td>
          </tr>
        `
          )
          .join("");
        await loadSummary();
        await loadBlockedIntentChart();
      } catch {
        adminSupportChatsBody.innerHTML =
          '<tr><td colspan="6" class="muted text-center">Failed to load support audit logs.</td></tr>';
      }
    }

    async function loadBlockedIntentChart() {
      if (!adminSupportBlockedIntentChart) return;
      adminSupportBlockedIntentChart.innerHTML = '<p class="muted">Loading blocked intent chart...</p>';
      try {
        const fromDate = (adminSupportFromDate?.value || "").trim();
        const toDate = (adminSupportToDate?.value || "").trim();
        const items = await adminSupportBlockedIntents(8, fromDate, toDate);
        if (!items || !items.length) {
          adminSupportBlockedIntentChart.innerHTML = '<p class="muted">No blocked intent data yet.</p>';
          return;
        }
        const maxCount = Math.max(...items.map((i) => Number(i.count || 0)), 1);
        adminSupportBlockedIntentChart.innerHTML = items
          .map((i) => {
            const label = String(i.intent || "").replace(/_/g, " ");
            const count = Number(i.count || 0);
            const pct = Math.max(4, Math.round((count / maxCount) * 100));
            return `
              <div class="mb-sm">
                <div class="muted" style="display:flex;justify-content:space-between;gap:10px;">
                  <span>${escapeHtml(label)}</span>
                  <span>${count}</span>
                </div>
                <div style="background:#e5e7eb;border-radius:6px;height:10px;overflow:hidden;">
                  <div style="width:${pct}%;height:10px;background:#ef4444;"></div>
                </div>
              </div>
            `;
          })
          .join("");
      } catch {
        adminSupportBlockedIntentChart.innerHTML = '<p class="muted">Failed to load blocked intent chart.</p>';
      }
    }

    if (adminSupportRefreshBtn) adminSupportRefreshBtn.addEventListener("click", loadRows);
    if (adminSupportExportCsvBtn) {
      adminSupportExportCsvBtn.addEventListener("click", async () => {
        const blockedOnly = String(adminSupportBlockedOnly?.value || "false") === "true";
        const account = (adminSupportAccountFilter?.value || "").trim();
        const fromDate = (adminSupportFromDate?.value || "").trim();
        const toDate = (adminSupportToDate?.value || "").trim();
        try {
          const blob = await adminSupportExportCsv(blockedOnly, account, fromDate, toDate);
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const ts = new Date().toISOString().replace(/[:.]/g, "-");
          a.href = url;
          a.download = `support_audit_${ts}.csv`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
        } catch (err) {
          alert(err.message || "CSV export failed.");
        }
      });
    }
    if (adminSupportBlockedOnly) adminSupportBlockedOnly.addEventListener("change", loadRows);
    if (adminSupportFromDate) adminSupportFromDate.addEventListener("change", loadRows);
    if (adminSupportToDate) adminSupportToDate.addEventListener("change", loadRows);
    if (adminSupportAccountFilter) {
      adminSupportAccountFilter.addEventListener("change", loadRows);
      adminSupportAccountFilter.addEventListener("keyup", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          loadRows();
        }
      });
    }
    await loadSummary();
    await loadRows();
    await loadBlockedIntentChart();
  }
})();



