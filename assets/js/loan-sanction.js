(function () {
  let user = null;
  const session = getSession();

  const form = document.getElementById("loanSanctionForm");
  const errorBox = document.getElementById("loanSanctionError");
  const resultBox = document.getElementById("loanSanctionResult");
  const loanDocFileEl = document.getElementById("loanDocFile");
  const loanDocStatedIncomeEl = document.getElementById("loanDocStatedIncome");
  const loanDocExtractBtn = document.getElementById("loanDocExtractBtn");
  const loanDocAiMsg = document.getElementById("loanDocAiMsg");
  const loanDocAiResult = document.getElementById("loanDocAiResult");

  const securedLoanEl = document.getElementById("securedLoan");
  const collateralGroupEl = document.getElementById("collateralGroup");

  if (!form) return;

  bootstrap();

  async function bootstrap() {
    user = await getCurrentUser();
    if (!session || !user || session.isAdmin) {
      window.location.href = "index.html";
      return;
    }

    if (securedLoanEl) {
      collateralGroupEl && toggleCollateral();
      securedLoanEl.addEventListener("change", () => {
        toggleCollateral();
      });
    }
    initLoanDocumentAi();
  }

  function toggleCollateral() {
    if (!collateralGroupEl) return;
    collateralGroupEl.classList.toggle("hidden", !securedLoanEl.checked);
  }

  function isPdfFile(file) {
    if (!file) return false;
    const name = String(file.name || "").toLowerCase();
    const type = String(file.type || "").toLowerCase();
    return type === "application/pdf" || name.endsWith(".pdf");
  }

  function initLoanDocumentAi() {
    if (!loanDocExtractBtn || !loanDocFileEl) return;
    loanDocExtractBtn.addEventListener("click", async () => {
      if (loanDocAiMsg) loanDocAiMsg.textContent = "";
      if (loanDocAiResult) loanDocAiResult.textContent = "";

      const files = Array.from((loanDocFileEl.files || []));
      if (!files.length) {
        if (loanDocAiMsg) loanDocAiMsg.textContent = "Please choose a loan document first.";
        return;
      }
      if (files.length > 5) {
        if (loanDocAiMsg) loanDocAiMsg.textContent = "Please upload up to 5 documents.";
        return;
      }
      const nonPdf = files.find((f) => !isPdfFile(f));
      if (nonPdf) {
        if (loanDocAiMsg) {
          loanDocAiMsg.textContent =
            "Only PDF files are accepted. Use your app’s “Download PDF” or Print → Save as PDF (see tips under the file field).";
        }
        return;
      }
      const statedIncome = loanDocStatedIncomeEl ? parseMoney(loanDocStatedIncomeEl.value) : 0;
      const statedIncomePayload = statedIncome > 0 ? statedIncome : null;

      loanDocExtractBtn.disabled = true;
      if (loanDocAiMsg) loanDocAiMsg.textContent = "Analyzing document with OCR and document classifier...";

      try {
        const res =
          files.length === 1
            ? await extractLoanDocumentAi(files[0], statedIncomePayload)
            : await extractLoanDocumentAiMulti(files, statedIncomePayload);
        const usingMulti = Array.isArray(res.documents);
        const docTypeLabel = usingMulti
          ? `${res.documents.length} docs (reconciled)`
          : res.documentType;
        const confValue = Number(res.confidence || 0);
        const verifyStatus = res.incomeVerificationStatus || "not_checked";
        if (loanDocAiMsg) {
          loanDocAiMsg.textContent = `Detected: ${docTypeLabel} (confidence ${(confValue * 100).toFixed(
            1
          )}%) | Income verification: ${verifyStatus}`;
        }

        const monthlyIncomeEl = document.getElementById("monthlyIncome");
        const existingEmiEl = document.getElementById("existingEmiTotal");
        const incomeValue = usingMulti ? res.reconciledMonthlyIncome : res.monthlyIncomeExtracted;
        const emiValue = usingMulti ? res.reconciledExistingEmi : res.existingEmiExtracted;
        if (monthlyIncomeEl && incomeValue && Number(incomeValue) > 0) {
          monthlyIncomeEl.value = String(Math.round(Number(incomeValue)));
        }
        if (existingEmiEl && emiValue && Number(emiValue) > 0) {
          existingEmiEl.value = String(Math.round(Number(emiValue)));
        }

        const details = [
          `Extracted monthly income: ${incomeValue != null ? `₹${Number(incomeValue).toLocaleString("en-IN")}` : "-"}`,
          `Extracted EMI total: ${emiValue != null ? `₹${Number(emiValue).toLocaleString("en-IN")}` : "-"}`,
          usingMulti
            ? `Per-document summary: ${(res.documents || [])
                .map((d) => `${d.fileName} => ${d.documentType}, income=${d.monthlyIncomeExtracted ?? "-"}, emi=${d.existingEmiExtracted ?? "-"}`)
                .join(" | ")}`
            : `Raw OCR preview: ${res.rawTextPreview || "-"}`,
          (Array.isArray(res.reasons) && res.reasons.length ? `Reasons:\n- ${res.reasons.join("\n- ")}` : ""),
        ]
          .filter(Boolean)
          .join("\n");
        if (loanDocAiResult) loanDocAiResult.textContent = details;
      } catch (err) {
        if (loanDocAiMsg) loanDocAiMsg.textContent = err.message || "Document AI extraction failed.";
      } finally {
        loanDocExtractBtn.disabled = false;
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideBox(errorBox);
    hideBox(resultBox);

    const loanType = (document.getElementById("loanType").value || "").trim();
    const loanAmount = parseMoney(document.getElementById("loanAmount").value);
    const tenureMonths = Number(document.getElementById("tenureMonths").value);
    const monthlyIncome = parseMoney(document.getElementById("monthlyIncome").value);
    const existingEmiTotal = parseMoney(document.getElementById("existingEmiTotal").value);
    const creditScoreRaw = document.getElementById("creditScore").value;
    const creditScore = creditScoreRaw ? Number(creditScoreRaw) : null;
    const dob = (document.getElementById("loanDob")?.value || "").trim();

    const secured = !!securedLoanEl?.checked;
    const collateralValueRaw = document.getElementById("collateralValue").value;
    const collateralValue =
      secured && collateralValueRaw ? parseMoney(collateralValueRaw) : null;

    if (!loanType || !loanAmount || isNaN(loanAmount) || loanAmount <= 0) {
      return showBox(errorBox, "Enter a valid loan amount.");
    }
    if (!tenureMonths || isNaN(tenureMonths) || tenureMonths <= 0) {
      return showBox(errorBox, "Enter a valid tenure (months).");
    }
    if (!monthlyIncome || isNaN(monthlyIncome) || monthlyIncome <= 0) {
      return showBox(errorBox, "Enter a valid monthly income.");
    }
    if (existingEmiTotal < 0 || isNaN(existingEmiTotal)) {
      return showBox(errorBox, "Existing EMIs total must be >= 0.");
    }
    if (secured && (collateralValue === null || collateralValue <= 0)) {
      return showBox(errorBox, "For secured loans, provide a valid collateral value.");
    }
    if (creditScore !== null && (isNaN(creditScore) || creditScore < 300 || creditScore > 850)) {
      return showBox(errorBox, "Credit score (if provided) must be between 300 and 850.");
    }

    try {
      const data = await predictLoanSanction({
        loanType,
        dob,
        loanAmount,
        tenureMonths,
        monthlyIncome,
        existingEmiTotal,
        creditScore,
        secured,
        collateralValue,
      });

      renderResult(data);
    } catch (err) {
      showBox(errorBox, err.message || "Prediction failed.");
    }
  });

  function renderResult(data) {
    if (!data) return;

    const recommendation = data.recommendation || "-";
    const score = data.sanctionScore ?? "-";
    const emi = data.estimatedEmi ?? "-";
    const dti = data.dti ?? "-";
    // Deduplicate identical lines to avoid repeated answers in UI.
    const reasonsRaw = Array.isArray(data.reasons) ? data.reasons : [];
    const reasons = Array.from(new Set(reasonsRaw.filter((r) => typeof r === "string")));

    const usedPhase2 = reasonsRaw.some(
      (r) => typeof r === "string" && r.startsWith("Phase-2 model:")
    );

    const drivers = [];
    const nextSteps = [];
    const other = [];

    for (const r of reasons) {
      if (
        r.startsWith("Phase-2 model:") ||
        r.startsWith("Model feature impact:") ||
        r.startsWith("Decision is a statistical estimate") ||
        r.startsWith("DTI ") ||
        r.startsWith("Credit score") ||
        r.startsWith("Age-at-end") ||
        r.startsWith("LTV ") ||
        r.startsWith("Credit score input used")
      ) {
        drivers.push(r);
      } else if (
        r.startsWith("Next steps:") ||
        r.startsWith("Credit guidance:") ||
        r.startsWith("Secured option:") ||
        r.startsWith("Collateral guidance:")
      ) {
        nextSteps.push(r);
      } else {
        other.push(r);
      }
    }

    function bullets(list) {
      if (!list.length) return "";
      return "<ul>" + list.map((x) => `<li>${escapeHtml(x)}</li>`).join("") + "</ul>";
    }

    resultBox.innerHTML = `
      <div class="card-header">
        <h2 class="card-title">Prediction Result</h2>
      </div>
      <p class="muted">
        <strong>Model used:</strong> ${escapeHtml(usedPhase2 ? "Phase-2 ML model" : "Phase-1 rules")}
      </p>
      <div class="alert ${
        recommendation === "approve"
          ? "alert-success"
          : recommendation === "decline"
          ? "alert-error"
          : "alert-neutral"
      }">
        <strong>Recommendation:</strong> ${escapeHtml(recommendation)}
      </div>
      <p class="muted"><strong>Sanction Score:</strong> ${escapeHtml(String(score))} / 100</p>
      <p class="muted"><strong>Estimated EMI:</strong> ${escapeHtml(formatCurrency(emi))}</p>
      <p class="muted"><strong>DTI (Debt-to-Income):</strong> ${escapeHtml(String(dti))}</p>
      <div class="mt-sm">
        ${drivers.length ? `<p class="muted"><strong>Decision Drivers</strong></p>${bullets(drivers)}` : ""}
        ${nextSteps.length ? `<p class="muted mt-sm"><strong>Next Steps</strong></p>${bullets(nextSteps)}` : ""}
        ${other.length ? `<p class="muted mt-sm"><strong>Notes</strong></p>${bullets(other)}` : ""}
      </div>
      <p class="muted mt-sm">${escapeHtml(data.disclaimer || "")}</p>
    `;
    showBox(resultBox);
  }

  function showBox(el, message) {
    if (!el) return;
    if (message !== undefined) el.textContent = message;
    el.classList.remove("hidden");
  }

  function hideBox(el) {
    if (!el) return;
    if (el.textContent) el.textContent = "";
    el.classList.add("hidden");
  }

  function parseMoney(raw) {
    const n = Number(String(raw || "").replace(/[^0-9.\-]/g, ""));
    return isNaN(n) ? 0 : n;
  }

  function formatCurrency(num) {
    const v = Number(num || 0);
    return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();

