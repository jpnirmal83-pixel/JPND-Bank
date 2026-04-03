// User dashboard logic: session guard, basic display, profile modal, quick deposit/withdraw

(function () {
  let user = null;
  const session = getSession();

  async function bootstrap() {
    user = await getCurrentUser();
    if (!session || !user || session.isAdmin) {
      window.location.href = "index.html";
      return;
    }
    initHeader();
    initKycBanner();
    renderOverview();
    renderRecent();
    initQuickActions();
    initQuickServices();
    initCreditRiskEarlyWarning();
    initFinanceCopilot();
    initFinancePrefs();
    initChurnRisk();
    initAiAdvisor();
    initAiChat();
    initVoiceBanking();
    initViewStatement();
    initProfileModal();
    initLogout();
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
  const aiAdvisorForm = document.getElementById("aiAdvisorForm");
  const aiAdvisorError = document.getElementById("aiAdvisorError");
  const aiAdvisorDisclaimer = document.getElementById("aiAdvisorDisclaimer");
  const aiInsuranceList = document.getElementById("aiInsuranceList");
  const aiInvestmentList = document.getElementById("aiInvestmentList");
  const aiChatForm = document.getElementById("aiChatForm");
  const aiChatInput = document.getElementById("aiChatInput");
  const aiChatMessages = document.getElementById("aiChatMessages");
  const aiChatDisclaimer = document.getElementById("aiChatDisclaimer");
  const creditRiskBox = document.getElementById("creditRiskBox");
  const creditRiskActions = document.getElementById("creditRiskActions");
  const financeCopilotBox = document.getElementById("financeCopilotBox");
  const financePrefsForm = document.getElementById("financePrefsForm");
  const financePrefsMsg = document.getElementById("financePrefsMsg");
  const churnBox = document.getElementById("churnBox");
  const voiceStartBtn = document.getElementById("voiceStartBtn");
  const voiceStopBtn = document.getElementById("voiceStopBtn");
  const voiceUnblockShortcutBtn = document.getElementById("voiceUnblockShortcutBtn");
  const voiceTranscript = document.getElementById("voiceTranscript");
  const voiceAnalyzeBtn = document.getElementById("voiceAnalyzeBtn");
  const voiceExecuteBtn = document.getElementById("voiceExecuteBtn");
  const voiceResult = document.getElementById("voiceResult");
  const voiceCardStatus = document.getElementById("voiceCardStatus");
  const voiceStepUpBox = document.getElementById("voiceStepUpBox");
  const voiceStepUpPassword = document.getElementById("voiceStepUpPassword");
  const voiceStepUpBtn = document.getElementById("voiceStepUpBtn");

  const editProfileBtn = document.getElementById("editProfileBtn");
  const deleteAccountBtn = document.getElementById("deleteAccountBtn");
  const profileModal = document.getElementById("profileModal");
  const profileForm = document.getElementById("profileForm");
  const profileError = document.getElementById("profileError");

  bootstrap();

  function initHeader() {
    if (welcomeUserEl) {
      welcomeUserEl.textContent = user.name;
    }
  }

  function initKycBanner() {
    const el = document.getElementById("kycBanner");
    if (!el || !user) return;
    if (user.kycVerified) return;
    el.classList.remove("hidden");
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
    quickForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideBox(quickError);

      const type = document.getElementById("actionType").value;
      const rawAmount = (document.getElementById("actionAmount").value || "").trim();
      const amountVal = Number(rawAmount.replace(/[^0-9.\-]/g, ""));

      if (!rawAmount || !amountVal || isNaN(amountVal) || amountVal <= 0) {
        return showBox(quickError, "Enter a valid amount.");
      }

      const freshUser = await getCurrentUser();
      if (!freshUser) {
        window.location.href = "index.html";
        return;
      }

      try {
        const updated = await quickAction(
          freshUser.accountNumber,
          type === "deposit" ? "deposit" : "withdraw",
          amountVal
        );
        Object.assign(user, updated);
      } catch (err) {
        return showBox(quickError, err.message || "Action failed.");
      }
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
      if (value === "loan") {
        window.location.href = "loan-sanction.html";
        return;
      }

      alert(
        `${label} request screen can be implemented here. Currently this is a demo shortcut from Quick Services.`
      );

      // Reset after action
      serviceSelect.value = "";
    });
  }

  function initVoiceBanking() {
    if (!voiceTranscript || !voiceResult || !voiceAnalyzeBtn || !voiceExecuteBtn) return;

    let recognition = null;
    let activeChallengeId = null;
    let lastIntent = null;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition || null;

    function setStepUpVisible(visible) {
      if (!voiceStepUpBox) return;
      voiceStepUpBox.classList.toggle("hidden", !visible);
    }

    function setExecuteEnabled(enabled) {
      voiceExecuteBtn.disabled = !enabled;
    }

    function resetState() {
      activeChallengeId = null;
      lastIntent = null;
      setExecuteEnabled(false);
      setStepUpVisible(false);
      if (voiceStepUpPassword) voiceStepUpPassword.value = "";
    }

    async function refreshCardStatus() {
      if (!voiceCardStatus) return;
      try {
        const s = await voiceCardStatusMe();
        voiceCardStatus.textContent = s.cardBlocked ? "Card status: BLOCKED" : "Card status: ACTIVE";
      } catch (err) {
        voiceCardStatus.textContent = "Card status: unavailable";
      }
    }

    if (voiceStartBtn && SpeechRecognition) {
      voiceStartBtn.addEventListener("click", () => {
        try {
          recognition = new SpeechRecognition();
          recognition.lang = "en-IN";
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;

          recognition.onstart = () => {
            voiceResult.textContent = "Listening… speak now.";
            if (voiceStopBtn) voiceStopBtn.disabled = false;
            voiceStartBtn.disabled = true;
          };

          recognition.onerror = (e) => {
            voiceResult.textContent = `Voice error: ${e.error || "unknown error"}`;
            if (voiceStopBtn) voiceStopBtn.disabled = true;
            voiceStartBtn.disabled = false;
          };

          recognition.onresult = (event) => {
            const transcript = event.results?.[0]?.[0]?.transcript || "";
            voiceTranscript.value = transcript;
            voiceResult.textContent = "Captured transcript. Click Analyze.";
          };

          recognition.onend = () => {
            if (voiceStopBtn) voiceStopBtn.disabled = true;
            voiceStartBtn.disabled = false;
          };

          recognition.start();
        } catch (err) {
          voiceResult.textContent = err.message || "Unable to start voice recognition.";
        }
      });
    } else if (voiceStartBtn) {
      voiceStartBtn.disabled = true;
      voiceResult.textContent =
        "Voice recognition not supported in this browser. Type a command and click Analyze.";
    }

    if (voiceStopBtn) {
      voiceStopBtn.addEventListener("click", () => {
        try {
          recognition && recognition.stop && recognition.stop();
        } catch {}
      });
    }

    voiceAnalyzeBtn.addEventListener("click", async () => {
      resetState();
      const text = (voiceTranscript.value || "").trim();
      if (!text) {
        voiceResult.textContent = "Please speak or type a command first.";
        return;
      }
      try {
        const res = await voiceIntent(text);
        lastIntent = res.intent;
        activeChallengeId = res.challengeId || null;
        voiceResult.textContent = res.message || `Intent: ${res.intent}`;

        if (res.intent === "unknown") {
          setExecuteEnabled(false);
          return;
        }

        if (!activeChallengeId) {
          setExecuteEnabled(false);
          return;
        }

        if (res.requiresStepUp) {
          setStepUpVisible(true);
          setExecuteEnabled(false);
        } else {
          setStepUpVisible(false);
          setExecuteEnabled(true);
        }
      } catch (err) {
        voiceResult.textContent = err.message || "Voice analyze failed.";
      }
    });

    if (voiceUnblockShortcutBtn) {
      voiceUnblockShortcutBtn.addEventListener("click", () => {
        voiceTranscript.value = "unblock my card";
        voiceResult.textContent = "Command prepared: unblock my card. Click Analyze.";
      });
    }

    if (voiceStepUpBtn) {
      voiceStepUpBtn.addEventListener("click", async () => {
        if (!activeChallengeId) return;
        const pw = (voiceStepUpPassword?.value || "").trim();
        if (!pw) {
          voiceResult.textContent = "Enter your password to verify (step-up).";
          return;
        }
        try {
          const res = await voiceStepUp(activeChallengeId, pw);
          voiceResult.textContent = res.message || "Verified. You can Execute now.";
          setExecuteEnabled(true);
        } catch (err) {
          voiceResult.textContent = err.message || "Step-up failed.";
          setExecuteEnabled(false);
        }
      });
    }

    voiceExecuteBtn.addEventListener("click", async () => {
      if (!activeChallengeId) return;
      try {
        const res = await voiceExecute(activeChallengeId);
        if (res && typeof res.balance === "number") {
          voiceResult.textContent = `Balance: ₹${res.balance.toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`;
          // refresh header balance too
          const freshUser = await getCurrentUser();
          if (freshUser) Object.assign(user, freshUser);
          renderOverview();
        } else {
          voiceResult.textContent = res.message || "Done.";
        }
        await refreshCardStatus();
        resetState();
      } catch (err) {
        voiceResult.textContent = err.message || "Execute failed.";
      }
    });

    refreshCardStatus();
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

  function initAiAdvisor() {
    if (!aiAdvisorForm) return;
    aiAdvisorForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideBox(aiAdvisorError);
      const goal = document.getElementById("aiGoal")?.value || "wealth-creation";
      const riskLevel = document.getElementById("aiRiskLevel")?.value || "moderate";
      try {
        const data = await getAiRecommendations(goal, riskLevel);
        if (aiAdvisorDisclaimer) {
          aiAdvisorDisclaimer.textContent = data.disclaimer || "";
        }
        renderAiList(aiInsuranceList, data.insurance || []);
        renderAiList(aiInvestmentList, data.investment || []);
      } catch (err) {
        showBox(aiAdvisorError, err.message || "Unable to fetch recommendations.");
      }
    });
  }

  async function initCreditRiskEarlyWarning() {
    if (!creditRiskBox) return;
    try {
      const r = await getCreditRiskMe();
      const level = String(r.level || "low").toLowerCase();
      const score = Number(r.score || 0).toFixed(1);
      const badge =
        level === "high"
          ? `<span class="chip" style="background:#fee2e2;color:#991b1b;">HIGH</span>`
          : level === "medium"
          ? `<span class="chip" style="background:#fef3c7;color:#92400e;">MEDIUM</span>`
          : `<span class="chip" style="background:#dcfce7;color:#166534;">LOW</span>`;

      creditRiskBox.innerHTML = `
        <p class="muted"><strong>Risk Level:</strong> ${badge} <span class="muted">(Score: ${score}/100)</span></p>
        ${
          Array.isArray(r.reasons) && r.reasons.length
            ? `<ul>${r.reasons.slice(0, 4).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>`
            : `<p class="muted">No risk signals detected in the last 30 days.</p>`
        }
      `;
      if (creditRiskActions) {
        creditRiskActions.innerHTML =
          Array.isArray(r.recommendedActions) && r.recommendedActions.length
            ? `<p class="muted"><strong>Recommended actions</strong></p><ul>${r.recommendedActions
                .slice(0, 4)
                .map((x) => `<li>${escapeHtml(x)}</li>`)
                .join("")}</ul>`
            : "";
      }
    } catch (err) {
      creditRiskBox.textContent = err.message || "Unable to load risk status.";
    }
  }

  async function initFinanceCopilot() {
    if (!financeCopilotBox) return;
    try {
      const r = await getFinanceCopilotMe();
      const top = Array.isArray(r.topSpends) ? r.topSpends : [];
      const tips = Array.isArray(r.tips) ? r.tips : [];
      const budgetAlerts = Array.isArray(r.budgetAlerts) ? r.budgetAlerts : [];
      const goalAlerts = Array.isArray(r.goalAlerts) ? r.goalAlerts : [];
      financeCopilotBox.innerHTML = `
        <p class="muted"><strong>Last 30 days:</strong> Inflow ${formatCurrency(r.inflow)} · Outflow ${formatCurrency(
          r.outflow
        )} · Net ${formatCurrency(r.net)}</p>
        ${
          top.length
            ? `<p class="muted"><strong>Top spends</strong></p>
               <ul>${top
                 .slice(0, 5)
                 .map((c) => `<li>${escapeHtml(c.category)}: ${formatCurrency(c.amount)}</li>`)
                 .join("")}</ul>`
            : `<p class="muted">No spending categories detected yet.</p>`
        }
        ${
          tips.length
            ? `<p class="muted"><strong>Copilot tips</strong></p>
               <ul>${tips.slice(0, 6).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>`
            : ""
        }
        ${
          budgetAlerts.length
            ? `<p class="muted"><strong>Budget alerts</strong></p>
               <ul>${budgetAlerts.slice(0, 6).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>`
            : ""
        }
        ${
          goalAlerts.length
            ? `<p class="muted"><strong>Goal alerts</strong></p>
               <ul>${goalAlerts.slice(0, 6).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul>`
            : ""
        }
      `;
    } catch (err) {
      financeCopilotBox.textContent = err.message || "Unable to load insights.";
    }
  }

  async function initFinancePrefs() {
    if (!financePrefsForm) return;
    try {
      const prefs = await getFinancePrefsMe();
      const goal = prefs && prefs.savingsGoal ? prefs.savingsGoal : {};
      const goalAmountEl = document.getElementById("financeGoalAmount");
      const goalDueEl = document.getElementById("financeGoalDue");
      if (goalAmountEl && goal.targetAmount) goalAmountEl.value = String(goal.targetAmount);
      if (goalDueEl && goal.dueDate) goalDueEl.value = String(goal.dueDate);
    } catch {}

    financePrefsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (financePrefsMsg) financePrefsMsg.textContent = "";
      const cat = (document.getElementById("financeBudgetCategory")?.value || "").trim();
      const amt = Number(document.getElementById("financeBudgetAmount")?.value || 0);
      const goalAmount = Number(document.getElementById("financeGoalAmount")?.value || 0);
      const goalDue = (document.getElementById("financeGoalDue")?.value || "").trim();

      const payload = { budgets: {}, savingsGoal: {} };
      if (cat && amt > 0) payload.budgets[cat] = amt;
      if (goalAmount > 0) payload.savingsGoal.targetAmount = goalAmount;
      if (goalDue) payload.savingsGoal.dueDate = goalDue;

      try {
        await updateFinancePrefsMe(payload);
        if (financePrefsMsg) financePrefsMsg.textContent = "Saved successfully.";
        await initFinanceCopilot();
      } catch (err) {
        if (financePrefsMsg) financePrefsMsg.textContent = err.message || "Save failed.";
      }
    });
  }

  async function initChurnRisk() {
    if (!churnBox) return;
    try {
      const r = await getChurnMe();
      const level = String(r.level || "low").toLowerCase();
      const score = Number(r.score || 0).toFixed(1);
      const badge =
        level === "high"
          ? `<span class="chip" style="background:#fee2e2;color:#991b1b;">HIGH</span>`
          : level === "medium"
          ? `<span class="chip" style="background:#fef3c7;color:#92400e;">MEDIUM</span>`
          : `<span class="chip" style="background:#dcfce7;color:#166534;">LOW</span>`;
      const reasons = Array.isArray(r.reasons) ? r.reasons : [];
      const tips = Array.isArray(r.retentionTips) ? r.retentionTips : [];
      const offer = r.nextBestOffer ? String(r.nextBestOffer).replace(/_/g, " ") : "";
      const lift = r.expectedRetentionLift != null ? Number(r.expectedRetentionLift) : null;
      churnBox.innerHTML = `
        <p class="muted"><strong>Churn Risk:</strong> ${badge} <span class="muted">(Score: ${score}/100)</span></p>
        ${
          offer
            ? `<p class="muted"><strong>Next Best Action:</strong> ${escapeHtml(offer)}${
                lift != null ? ` <span class="chip">Expected retention lift: +${(lift * 100).toFixed(1)}%</span>` : ""
              }</p>`
            : ""
        }
        ${
          reasons.length
            ? `<p class="muted"><strong>Signals</strong></p><ul>${reasons
                .slice(0, 4)
                .map((x) => `<li>${escapeHtml(x)}</li>`)
                .join("")}</ul>`
            : ""
        }
        ${
          tips.length
            ? `<p class="muted"><strong>Retention tips</strong></p><ul>${tips
                .slice(0, 4)
                .map((x) => `<li>${escapeHtml(x)}</li>`)
                .join("")}</ul>`
            : ""
        }
      `;
    } catch (err) {
      churnBox.textContent = err.message || "Unable to load retention status.";
    }
  }

  function renderAiList(container, items) {
    if (!container) return;
    if (!items.length) {
      container.innerHTML = '<p class="muted">No recommendations available for this profile.</p>';
      return;
    }
    container.innerHTML = items
      .map(
        (p) => `
        <div class="card mt-sm">
          <p><strong>${p.name}</strong> <span class="muted">(Score: ${p.score})</span></p>
          <p class="muted">
            <span class="chip">${p.category}</span>
            <span class="chip">AI Match</span>
          </p>
          <p class="muted">${p.summary}</p>
          <p class="muted">${p.reason}</p>
          <div class="button-stack mt-sm">
            <button class="btn btn-ghost btn-sm" data-ai-action="saved" data-product-id="${p.productId}">Save</button>
            <button class="btn btn-ghost btn-sm" data-ai-action="accepted" data-product-id="${p.productId}">Interested</button>
            <button class="btn btn-ghost btn-sm" data-ai-action="rejected" data-product-id="${p.productId}">Not Relevant</button>
          </div>
        </div>
      `
      )
      .join("");

    container.querySelectorAll("button[data-ai-action]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.getAttribute("data-ai-action");
        const productId = Number(btn.getAttribute("data-product-id"));
        if (!action || !productId) return;
        try {
          await submitAiFeedback(productId, action);
          btn.textContent = "Saved";
        } catch (err) {
          showBox(aiAdvisorError, err.message || "Unable to save feedback.");
        }
      });
    });
  }

  function initAiChat() {
    if (!aiChatForm || !aiChatInput || !aiChatMessages) return;
    const forcedInput = document.getElementById("aiChatForcedTopicKey");
    const supportHints = [
      "faq",
      "policy",
      "terms",
      "charges",
      "fees",
      "eligibility",
      "cancel",
      "refund",
      "claim",
      "support",
      "customer care",
      "help",
    ];
    aiChatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const question = aiChatInput.value.trim();
      if (!question) return;
      appendChat("You", question);
      aiChatInput.value = "";
      const forcedTopicKey = forcedInput ? (forcedInput.value || "").trim() : "";

      const goal = document.getElementById("aiGoal")?.value || "wealth-creation";
      const riskLevel = document.getElementById("aiRiskLevel")?.value || "moderate";

      try {
        const qLower = String(question || "").toLowerCase();
        const useSupport = supportHints.some((k) => qLower.includes(k));
        const response = useSupport
          ? await supportAutoReply(question, 4)
          : await aiChat(
              question,
              goal,
              riskLevel,
              forcedTopicKey ? forcedTopicKey : null
            );
        appendChat("AI Advisor", response.reply || "No suggestion available.");
        if (aiChatDisclaimer) {
          aiChatDisclaimer.textContent = response.disclaimer || "";
        }
      } catch (err) {
        appendChat("AI Advisor", err.message || "Unable to process your question now.");
      } finally {
        if (forcedInput) forcedInput.value = "";
      }
    });

    const chipsWrap = document.getElementById("aiChatChips");
    if (chipsWrap) {
      chipsWrap.querySelectorAll("button[data-ai-chip]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const q = btn.getAttribute("data-ai-chip") || "";
          const tkey = btn.getAttribute("data-ai-topic-key") || "";
          if (!q) return;
          if (aiChatInput) aiChatInput.value = q;
          if (forcedInput) forcedInput.value = tkey;
          if (aiChatDisclaimer) aiChatDisclaimer.textContent = "";

          if (typeof aiChatForm.requestSubmit === "function") {
            aiChatForm.requestSubmit();
          } else {
            aiChatForm.dispatchEvent(
              new Event("submit", { bubbles: true, cancelable: true })
            );
          }
        });
      });
    }
  }

  function appendChat(sender, text) {
    if (!aiChatMessages) return;
    const row = document.createElement("p");
    row.innerHTML = `<strong>${escapeHtml(sender)}:</strong> <span class="ai-chat-msg">${escapeHtml(text)}</span>`;
    aiChatMessages.appendChild(row);
    aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
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

    profileForm.addEventListener("submit", async (e) => {
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

      const duplicateEmail = await emailExists(email, user.accountNumber);
      if (duplicateEmail) {
        return showBox(profileError, "Email is already used by another account.");
      }

      const latest = await getCurrentUser();
      const updatedUser = { ...latest, name, email, phone };
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

      const saved = await updateUser(updatedUser);
      Object.assign(user, saved);
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
    logoutBtn.addEventListener("click", async () => {
      await logoutSession();
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



