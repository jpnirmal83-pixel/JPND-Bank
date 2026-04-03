// Transaction history page: guard session, render list, advanced date filters, delete

(function () {
  const session = getSession();
  let user = null;

  const tbody = document.getElementById("transactionsBody");
  const filterForm = document.getElementById("filterForm");
  const resetBtn = document.getElementById("resetFilters");

  const typeSelect = document.getElementById("filterType");
  const fromDay = document.getElementById("fromDay");
  const fromMonth = document.getElementById("fromMonth");
  const fromYear = document.getElementById("fromYear");
  const toDay = document.getElementById("toDay");
  const toMonth = document.getElementById("toMonth");
  const toYear = document.getElementById("toYear");
  const rangeRadios = document.querySelectorAll(
    'input[name="statementRange"]'
  );

  let allTxns = [];
  let currentFiltered = [];

  bootstrap();

  async function bootstrap() {
    user = await getCurrentUser();
    if (!session || !user || session.isAdmin) {
      window.location.href = "index.html";
      return;
    }
    allTxns = [...(user.transactions || [])].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
    currentFiltered = [...allTxns];
    initDateSelectors();
    render(allTxns);
    initFilters();
    initDownloads();
    autoDownloadIfRequested();
  }

  function initDateSelectors() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const years = [];
    for (let y = currentYear - 5; y <= currentYear + 1; y++) {
      years.push(y);
    }

    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];

    const days = [];
    for (let d = 1; d <= 31; d++) {
      days.push(d);
    }

    function populateSelect(select, values, placeholder) {
      if (!select) return;
      select.innerHTML = "";
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = placeholder;
      select.appendChild(opt);
      values.forEach((v, idx) => {
        const o = document.createElement("option");
        o.value = typeof v === "number" ? String(v) : String(idx + 1);
        o.textContent = String(v);
        select.appendChild(o);
      });
    }

    populateSelect(fromDay, days, "Day");
    populateSelect(toDay, days, "Day");

    // months should be 1-12 with text
    if (fromMonth) {
      fromMonth.innerHTML = `<option value="">Month</option>` +
        months
          .map(
            (m, idx) => `<option value="${idx + 1}">${m}</option>`
          )
          .join("");
    }
    if (toMonth) {
      toMonth.innerHTML = `<option value="">Month</option>` +
        months
          .map(
            (m, idx) => `<option value="${idx + 1}">${m}</option>`
          )
          .join("");
    }

    populateSelect(fromYear, years, "Year");
    populateSelect(toYear, years, "Year");
  }

  function initFilters() {
    if (filterForm) {
      filterForm.addEventListener("submit", (e) => {
        e.preventDefault();
        applyFilters();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        typeSelect.value = "all";
        [fromDay, fromMonth, fromYear, toDay, toMonth, toYear].forEach((s) => {
          if (s) s.value = "";
        });
        if (rangeRadios && rangeRadios.length) {
          rangeRadios.forEach((r) => {
            if (r.value === "all") {
              r.checked = true;
            } else {
              r.checked = false;
            }
          });
        }
        render(allTxns);
      });
    }
  }

  function applyFilters() {
    let filtered = [...allTxns];
    const typeVal = typeSelect ? typeSelect.value : "all";

    if (typeVal && typeVal !== "all") {
      filtered = filtered.filter((t) => t.type === typeVal);
    }

    // Determine range selection
    let range = "all";
    if (rangeRadios && rangeRadios.length) {
      const checked = Array.from(rangeRadios).find((r) => r.checked);
      if (checked) range = checked.value;
    }

    let fromDate = null;
    let toDate = null;

    const now = new Date();
    if (range === "one-month") {
      fromDate = new Date(now);
      fromDate.setMonth(fromDate.getMonth() - 1);
      toDate = now;
    } else if (range === "mini-10") {
      fromDate = new Date(now);
      fromDate.setDate(fromDate.getDate() - 10);
      toDate = now;
    } else {
      fromDate = buildDate(fromYear, fromMonth, fromDay, true);
      toDate = buildDate(toYear, toMonth, toDay, false);
    }

    if (fromDate) {
      filtered = filtered.filter(
        (t) => new Date(t.timestamp) >= fromDate
      );
    }
    if (toDate) {
      filtered = filtered.filter(
        (t) => new Date(t.timestamp) <= toDate
      );
    }

    currentFiltered = filtered;
    render(filtered);
  }

  function buildDate(yearSel, monthSel, daySel, isStart) {
    if (!yearSel || !monthSel || !daySel) return null;
    const y = Number(yearSel.value);
    const m = Number(monthSel.value);
    const d = Number(daySel.value);
    if (!y || !m || !d) return null;
    if (isStart) {
      return new Date(y, m - 1, d, 0, 0, 0, 0);
    }
    return new Date(y, m - 1, d, 23, 59, 59, 999);
  }

  function render(list) {
    if (!tbody) return;
    if (!list.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="muted text-center">No transactions found for the selected filters.</td></tr>';
      return;
    }

    tbody.innerHTML = list
      .map(
        (t) => `
        <tr data-id="${t.id}">
          <td>${formatType(t.type)}</td>
          <td>${formatMode(t)}</td>
          <td>${formatCounterpartyAccount(t)}</td>
          <td>${formatCounterpartyName(t)}</td>
          <td class="text-right">${formatCurrency(t.amount)}</td>
          <td class="text-right">${formatCurrency(t.prevBalance)}</td>
          <td class="text-right">${formatCurrency(t.newBalance)}</td>
          <td>${formatDateTime(t.timestamp)}</td>
          <td>
            <button class="icon-button" title="Delete transaction" data-delete>
              ✕
            </button>
          </td>
        </tr>
      `
      )
      .join("");

    // Attach delete handlers
    tbody.querySelectorAll("button[data-delete]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const tr = e.target.closest("tr");
        if (!tr) return;
        const id = tr.getAttribute("data-id");
        const confirmed = confirm(
          "Remove this transaction from your history? This will not change your balance."
        );
        if (!confirmed) return;
        removeTransactionEntry(id);
      });
    });
  }

  async function removeTransactionEntry(id) {
    // Only delete from history, don't recalc balance (per optional feature)
    const freshUser = await getCurrentUser();
    if (!freshUser) return;
    const updated = await removeTransaction(
      freshUser.accountNumber,
      id
    );
    allTxns = [...(updated.transactions || [])].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
    applyFilters();
  }

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

  function initDownloads() {
    const excelBtn = document.getElementById("downloadExcelBtn");
    const pdfBtn = document.getElementById("downloadPdfBtn");

    if (excelBtn) {
      excelBtn.addEventListener("click", () => {
        downloadExcelFromCurrent();
      });
    }

    if (pdfBtn) {
      pdfBtn.addEventListener("click", () => {
        if (!currentFiltered.length) {
          alert("No transactions to include in the PDF for the selected filters.");
          return;
        }

        // Simple printable view; users can choose "Save as PDF" in browser
        const popup = window.open("", "_blank", "width=900,height=700");
        if (!popup) return;
        const doc = popup.document;
        doc.write("<html><head><title>JPND Bank - Transaction Statement</title>");
        doc.write(
          '<style>body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:16px;} *{box-sizing:border-box;} table{width:100%;border-collapse:collapse;font-size:12px;} th,td{border:1px solid #ccc;padding:4px 6px;text-align:left;} th{background:#f3f4f6;font-weight:600;}</style>'
        );
        doc.write("</head><body>");
        doc.write("<h2>JPND Bank - Transaction Statement</h2>");
        doc.write(
          `<p><strong>Account:</strong> ${user.accountNumber} &nbsp;&nbsp; <strong>Name:</strong> ${user.name}</p>`
        );
        doc.write("<table><thead><tr>");
        [
          "Type",
          "Mode",
          "Account",
          "Name",
          "Amount",
          "Previous Balance",
          "New Balance",
          "Timestamp",
        ].forEach((h) => doc.write(`<th>${h}</th>`));
        doc.write("</tr></thead><tbody>");
        currentFiltered.forEach((t) => {
          doc.write("<tr>");
          doc.write(`<td>${formatType(t.type)}</td>`);
          doc.write(`<td>${formatMode(t)}</td>`);
          doc.write(`<td>${formatCounterpartyAccount(t)}</td>`);
          doc.write(`<td>${formatCounterpartyName(t)}</td>`);
          doc.write(`<td>${formatCurrency(t.amount)}</td>`);
          doc.write(`<td>${formatCurrency(t.prevBalance)}</td>`);
          doc.write(`<td>${formatCurrency(t.newBalance)}</td>`);
          doc.write(
            `<td>${new Date(t.timestamp).toLocaleString()}</td>`
          );
          doc.write("</tr>");
        });
        doc.write("</tbody></table>");
        doc.write("</body></html>");
        doc.close();
        popup.focus();
        popup.print();
      });
    }
  }

  function downloadExcelFromCurrent() {
    if (!currentFiltered.length) {
      alert("No transactions to download for the selected filters.");
      return;
    }
    const header = [
      "Type",
      "Mode",
      "Account",
      "Name",
      "Amount",
      "Previous Balance",
      "New Balance",
      "Timestamp",
    ];
    const rows = currentFiltered.map((t) => [
      formatType(t.type),
      formatMode(t),
      formatCounterpartyAccount(t),
      formatCounterpartyName(t),
      t.amount,
      t.prevBalance,
      t.newBalance,
      new Date(t.timestamp).toLocaleString(),
    ]);

    const csvContent =
      [header, ...rows]
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

    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "jaydee-bank-transactions.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function autoDownloadIfRequested() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("autoDownload") === "excel") {
      // ensure filters are applied first
      applyFilters();
      downloadExcelFromCurrent();
    }
  }
})();


