// API + session utilities for JPND Bank
// Loads after assets/js/config.js, which sets window.JAYDEE_API_BASE_URL

const BANK_SESSION_KEY = "jaydee_bank_session";
const BANK_API_BASE_URL =
  window.JAYDEE_API_BASE_URL || "http://localhost:8000/api";

function apiUnreachableMessage() {
  return (
    "Unable to reach the API at " +
    BANK_API_BASE_URL +
    ". Check the network and that the backend is running."
  );
}

/**
 * User shape (for reference):
 * {
 *   id: string,
 *   name: string,
 *   email: string,
 *   phone: string,
 *   accountNumber: string,
 *   balance: number,
 *   password: string,
 *   isAdmin: boolean,
 *   transactions: Array<{
 *     id: string,
 *     type: 'deposit'|'withdraw'|'transfer-in'|'transfer-out',
 *     amount: number,
 *     prevBalance: number,
 *     newBalance: number,
 *     note?: string,
 *     timestamp: string
 *   }>
 * }
 */

async function apiRequest(path, options = {}) {
  const session = getSession();
  const authHeaders =
    session && session.accessToken
      ? { Authorization: `Bearer ${session.accessToken}` }
      : {};
  let response;
  try {
    response = await fetch(`${BANK_API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...(options.headers || {}),
      },
      credentials: "include",
      ...options,
    });
  } catch {
    throw new Error(apiUnreachableMessage());
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }
  return data;
}

async function loadUsers() {
  return apiRequest("/users");
}

async function emailExists(email, excludeAccount = "") {
  const params = new URLSearchParams({ email });
  if (excludeAccount) {
    params.set("excludeAccount", excludeAccount);
  }
  const res = await apiRequest(`/users/email-exists?${params.toString()}`);
  return !!res.exists;
}

function generateId(prefix = "id") {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
}

async function getUserByAccountOrEmail(identifier, password) {
  const auth = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
  return auth;
}

/** Public recovery: verify account + phone + DOB; returns { email }. */
async function recoverEmailWithVerification({ accountNumber, phone, dob }) {
  return apiRequest("/auth/recover-email", {
    method: "POST",
    body: JSON.stringify({ accountNumber, phone, dob }),
  });
}

/** Public recovery: verify account + phone; sets new password. */
async function forgotPasswordWithVerification({ accountNumber, phone, newPassword }) {
  return apiRequest("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ accountNumber, phone, newPassword }),
  });
}

async function getUserByAccountNumber(accountNumber) {
  return apiRequest(`/users/by-account/${encodeURIComponent(accountNumber)}`);
}

async function updateUser(updatedUser) {
  return apiRequest(`/users/${encodeURIComponent(updatedUser.accountNumber)}`, {
    method: "PUT",
    body: JSON.stringify({
      name: updatedUser.name,
      email: updatedUser.email,
      phone: updatedUser.phone,
      password: updatedUser.password || null,
    }),
  });
}

async function deleteUser(accountNumber) {
  return apiRequest(`/users/${encodeURIComponent(accountNumber)}`, {
    method: "DELETE",
  });
}

async function createUser({
  name,
  email,
  phone,
  gender = "",
  dob = "",
  address = "",
  openAccountType = "",
  password,
  initialDeposit = 0,
  isAdmin = false,
}) {
  return apiRequest("/users", {
    method: "POST",
    body: JSON.stringify({
      name,
      email,
      phone,
      gender,
      dob,
      address,
      openAccountType,
      password,
      initialDeposit,
      isAdmin,
    }),
  });
}

async function quickAction(accountNumber, type, amount) {
  return apiRequest(`/users/${encodeURIComponent(accountNumber)}/quick-action`, {
    method: "POST",
    body: JSON.stringify({ type, amount }),
  });
}

async function transferAmount({ fromAccount, toAccount, amount, mode, note }) {
  return apiRequest("/transfers", {
    method: "POST",
    body: JSON.stringify({ fromAccount, toAccount, amount, mode, note }),
  });
}

async function removeTransaction(accountNumber, txnId) {
  return apiRequest(
    `/users/${encodeURIComponent(accountNumber)}/transactions/${encodeURIComponent(txnId)}`,
    { method: "DELETE" }
  );
}

async function resetUserPassword(accountNumber, password) {
  return apiRequest(`/users/${encodeURIComponent(accountNumber)}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

async function getAiRecommendations(goal, riskLevel) {
  return apiRequest("/ai/recommendations", {
    method: "POST",
    body: JSON.stringify({ goal, riskLevel }),
  });
}

async function submitAiFeedback(productId, action) {
  return apiRequest("/ai/feedback", {
    method: "POST",
    body: JSON.stringify({ productId, action }),
  });
}

async function aiChat(message, goal, riskLevel, forcedTopicKey = null) {
  // Prefer KB-grounded RAG endpoint; fall back to templates if backend lacks it.
  try {
    const res = await apiRequest("/ai/chat-rag", {
      method: "POST",
      body: JSON.stringify({
        message,
        goal,
        riskLevel,
        forcedTopicKey,
        topK: 3,
      }),
    });
    // Keep backwards compatibility for existing UI.
    return {
      reply: res.reply,
      suggestedInsurance: res.suggestedInsurance || [],
      suggestedInvestment: res.suggestedInvestment || [],
      disclaimer: res.disclaimer || "",
      sources: res.sources || [],
    };
  } catch (e) {
    return apiRequest("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message, goal, riskLevel, forcedTopicKey }),
    });
  }
}

async function supportAutoReply(message, topK = 4) {
  return apiRequest("/support/auto-reply", {
    method: "POST",
    body: JSON.stringify({ message, topK }),
  });
}

async function adminSupportChats(limit = 50, blockedOnly = false, accountNumber = "", fromDate = "", toDate = "") {
  const params = new URLSearchParams({ limit: String(limit), blockedOnly: String(Boolean(blockedOnly)) });
  if (accountNumber) params.set("accountNumber", String(accountNumber));
  if (fromDate) params.set("fromDate", String(fromDate));
  if (toDate) params.set("toDate", String(toDate));
  return apiRequest(`/admin/support/chats?${params.toString()}`);
}

async function adminSupportChatsSummary(fromDate = "", toDate = "") {
  const params = new URLSearchParams();
  if (fromDate) params.set("fromDate", String(fromDate));
  if (toDate) params.set("toDate", String(toDate));
  return apiRequest(`/admin/support/chats/summary${params.toString() ? `?${params.toString()}` : ""}`);
}

async function adminSupportBlockedIntents(limit = 10, fromDate = "", toDate = "") {
  const params = new URLSearchParams({ limit: String(limit) });
  if (fromDate) params.set("fromDate", String(fromDate));
  if (toDate) params.set("toDate", String(toDate));
  return apiRequest(`/admin/support/chats/blocked-intents?${params.toString()}`);
}

async function adminSupportExportCsv(blockedOnly = false, accountNumber = "", fromDate = "", toDate = "") {
  const session = getSession();
  if (!session || !session.accountNumber) {
    throw new Error("Please login first.");
  }
  const params = new URLSearchParams({ blockedOnly: String(Boolean(blockedOnly)) });
  if (accountNumber) params.set("accountNumber", String(accountNumber));
  if (fromDate) params.set("fromDate", String(fromDate));
  if (toDate) params.set("toDate", String(toDate));
  let response;
  try {
    response = await fetch(`${BANK_API_BASE_URL}/admin/support/chats/export.csv?${params.toString()}`, {
      method: "GET",
      headers: session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {},
      credentials: "include",
    });
  } catch {
    throw new Error(apiUnreachableMessage());
  }
  if (!response.ok) {
    let msg = "CSV export failed.";
    try {
      const tx = await response.text();
      if (tx) {
        const j = JSON.parse(tx);
        msg = j.detail || msg;
      }
    } catch {
      // ignore parse failures
    }
    throw new Error(msg);
  }
  const blob = await response.blob();
  return blob;
}

async function adminListKbDocs() {
  return apiRequest("/admin/kb/docs");
}

async function adminCreateKbDoc(payload) {
  return apiRequest("/admin/kb/docs", { method: "POST", body: JSON.stringify(payload) });
}

async function adminUpdateKbDoc(docId, payload) {
  return apiRequest(`/admin/kb/docs/${encodeURIComponent(docId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

async function adminDeleteKbDoc(docId) {
  return apiRequest(`/admin/kb/docs/${encodeURIComponent(docId)}`, { method: "DELETE" });
}

async function voiceIntent(transcript) {
  return apiRequest("/voice/intent", {
    method: "POST",
    body: JSON.stringify({ transcript }),
  });
}

async function voiceStepUp(challengeId, password) {
  return apiRequest("/voice/step-up", {
    method: "POST",
    body: JSON.stringify({ challengeId, password }),
  });
}

async function voiceExecute(challengeId) {
  return apiRequest("/voice/execute", {
    method: "POST",
    body: JSON.stringify({ challengeId }),
  });
}

async function voiceCardStatusMe() {
  return apiRequest("/voice/card-status/me");
}

async function getKycStatus() {
  return apiRequest("/kyc/status/me");
}

async function uploadKyc(selfieFile, idFile, livenessProof) {
  const session = getSession();
  if (!session || !session.accountNumber) {
    throw new Error("Please log in to complete KYC.");
  }
  const fd = new FormData();
  fd.append("selfie", selfieFile);
  fd.append("id_document", idFile);
  if (livenessProof && typeof livenessProof === "object") {
    fd.append("liveness_proof", JSON.stringify(livenessProof));
  }
  let response;
  try {
    response = await fetch(`${BANK_API_BASE_URL}/kyc/upload`, {
      method: "POST",
      headers: session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {},
      credentials: "include",
      body: fd,
    });
  } catch {
    throw new Error(apiUnreachableMessage());
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || "KYC upload failed.");
  }
  return data;
}

async function adminKycSubmissions(limit = 50, status = "") {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", String(status));
  return apiRequest(`/admin/kyc/submissions?${params.toString()}`);
}

async function adminKycApprove(submissionId) {
  return apiRequest(`/admin/kyc/${encodeURIComponent(submissionId)}/approve`, { method: "POST" });
}

async function adminVoiceAudit(limit = 50, accountNumber = "", intent = "", status = "") {
  const params = new URLSearchParams({
    limit: String(limit),
  });
  if (accountNumber) params.set("accountNumber", String(accountNumber));
  if (intent) params.set("intent", String(intent));
  if (status) params.set("status", String(status));
  return apiRequest(`/admin/voice/audit?${params.toString()}`);
}

async function predictLoanSanction(payload) {
  return apiRequest("/loan/sanction/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function extractLoanDocumentAi(file, statedMonthlyIncome = null) {
  const session = getSession();
  if (!session || !session.accountNumber) {
    throw new Error("Please login first.");
  }
  const fd = new FormData();
  fd.append("file", file);
  if (statedMonthlyIncome !== null && statedMonthlyIncome !== undefined && !Number.isNaN(Number(statedMonthlyIncome))) {
    fd.append("statedMonthlyIncome", String(statedMonthlyIncome));
  }
  let response;
  try {
    response = await fetch(`${BANK_API_BASE_URL}/loan/document-ai/extract`, {
      method: "POST",
      headers: {
        ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
      },
      credentials: "include",
      body: fd,
    });
  } catch {
    throw new Error(apiUnreachableMessage());
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || "Document AI extraction failed.");
  }
  return data;
}

async function extractLoanDocumentAiMulti(files, statedMonthlyIncome = null) {
  const session = getSession();
  if (!session || !session.accountNumber) {
    throw new Error("Please login first.");
  }
  const fd = new FormData();
  (files || []).forEach((f) => {
    if (f) fd.append("files", f);
  });
  if (statedMonthlyIncome !== null && statedMonthlyIncome !== undefined && !Number.isNaN(Number(statedMonthlyIncome))) {
    fd.append("statedMonthlyIncome", String(statedMonthlyIncome));
  }
  let response;
  try {
    response = await fetch(`${BANK_API_BASE_URL}/loan/document-ai/extract-multi`, {
      method: "POST",
      headers: {
        ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
      },
      credentials: "include",
      body: fd,
    });
  } catch {
    throw new Error(apiUnreachableMessage());
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || "Document AI multi extraction failed.");
  }
  return data;
}

async function adminListLoanDocumentAiLogs(limit = 50, reviewStatus = "", accountNumber = "") {
  const params = new URLSearchParams({ limit: String(limit) });
  if (reviewStatus) params.set("reviewStatus", String(reviewStatus));
  if (accountNumber) params.set("accountNumber", String(accountNumber));
  return apiRequest(`/admin/loan/document-ai/logs?${params.toString()}`);
}

async function adminReviewLoanDocumentAi(payload) {
  return apiRequest("/admin/loan/document-ai/review", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function adminLoanDocumentAiModelStatus() {
  return apiRequest("/admin/loan/document-ai/model-status");
}

async function adminTrainLoanDocumentAiModel() {
  return apiRequest("/admin/loan/document-ai/train", { method: "POST" });
}

async function adminListProducts() {
  return apiRequest("/admin/products");
}

async function adminCreateProduct(payload) {
  return apiRequest("/admin/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function adminUpdateProduct(productId, payload) {
  return apiRequest(`/admin/products/${encodeURIComponent(productId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

async function adminDeleteProduct(productId) {
  return apiRequest(`/admin/products/${encodeURIComponent(productId)}`, {
    method: "DELETE",
  });
}

async function adminFeedbackSummary() {
  return apiRequest("/admin/ai-feedback-summary");
}

async function adminAiDiagnostics(days = 7, category = "all") {
  const params = new URLSearchParams({
    days: String(days),
    category: String(category || "all"),
  });
  return apiRequest(`/admin/ai-diagnostics?${params.toString()}`);
}

// Loan sanction (Phase-2) training helpers
async function adminLoanModelStatus() {
  return apiRequest("/admin/loan/sanction/model-status");
}

async function adminListLoanSanctionApplications(limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/loan/sanction-applications?${params.toString()}`);
}

async function adminLabelLoanSanctionApplication(applicationId, actualRecommendation) {
  return apiRequest("/admin/loan/sanction/label", {
    method: "POST",
    body: JSON.stringify({ applicationId, actualRecommendation }),
  });
}

async function adminTrainLoanSanctionModel() {
  return apiRequest("/admin/loan/sanction/train", { method: "POST" });
}

async function adminLoanScorecardModelStatus() {
  return apiRequest("/admin/loan/scorecard/model-status");
}

async function adminTrainLoanScorecardModel() {
  return apiRequest("/admin/loan/scorecard/train", { method: "POST" });
}

async function adminExplainLoanScorecard(applicationId) {
  const params = new URLSearchParams({ applicationId: String(applicationId) });
  return apiRequest(`/admin/loan/scorecard/explain?${params.toString()}`);
}

async function adminListFraudAlerts(limit = 25, status = "all", accountNumber = "") {
  const params = new URLSearchParams({ limit: String(limit), status: String(status || "all") });
  if (accountNumber) params.set("accountNumber", String(accountNumber));
  return apiRequest(`/admin/fraud-alerts?${params.toString()}`);
}

async function adminUpdateFraudAlertStatus(alertId, status) {
  return apiRequest("/admin/fraud-alerts/status", {
    method: "POST",
    body: JSON.stringify({ alertId, status }),
  });
}

async function adminFraudAlertSummary() {
  return apiRequest("/admin/fraud-alerts/summary");
}

async function adminLabelFraudAlert(alertId, actualLabel) {
  return apiRequest("/admin/fraud-alerts/label", {
    method: "POST",
    body: JSON.stringify({ alertId, actualLabel }),
  });
}

async function adminFraudModelStatus() {
  return apiRequest("/admin/fraud/model-status");
}

async function adminTrainFraudModel() {
  return apiRequest("/admin/fraud/train", { method: "POST" });
}

async function adminFraudRealtimeModelStatus() {
  return apiRequest("/admin/fraud/realtime/model-status");
}

async function adminTrainFraudRealtimeModel() {
  return apiRequest("/admin/fraud/realtime/train", { method: "POST" });
}

async function adminAmlModelStatus() {
  return apiRequest("/admin/aml/model-status");
}

async function adminTrainAmlModel() {
  return apiRequest("/admin/aml/train", { method: "POST" });
}

async function adminAmlSuspiciousRings(limit = 20, minScore = 0.65) {
  const params = new URLSearchParams({ limit: String(limit), minScore: String(minScore) });
  return apiRequest(`/admin/aml/suspicious-rings?${params.toString()}`);
}

async function adminCreateAmlCaseFromRing(payload) {
  return apiRequest("/admin/aml/cases/from-ring", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function adminListAmlCases(limit = 50, status = "all", priority = "all", watchlistOnly = false) {
  const params = new URLSearchParams({
    limit: String(limit),
    status: String(status || "all"),
    priority: String(priority || "all"),
    watchlistOnly: String(Boolean(watchlistOnly)),
  });
  return apiRequest(`/admin/aml/cases?${params.toString()}`);
}

async function adminUpdateAmlCase(payload) {
  return apiRequest("/admin/aml/cases/update", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function adminRunAmlAutomation(minScore = 0.75, autoWatchlistScore = 80, escalateAfterHours = 24) {
  const params = new URLSearchParams({
    minScore: String(minScore),
    autoWatchlistScore: String(autoWatchlistScore),
    escalateAfterHours: String(escalateAfterHours),
  });
  return apiRequest(`/admin/aml/automation/run?${params.toString()}`, {
    method: "POST",
  });
}

async function adminAmlCaseAlertLinks(limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/aml/cases/alert-links?${params.toString()}`);
}

async function adminFraudNetworkHighRisk(limit = 25) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/fraud/network-high-risk?${params.toString()}`);
}

async function adminFraudAccountAction(accountNumber, action, reason = "") {
  return apiRequest("/admin/fraud/account-action", {
    method: "POST",
    body: JSON.stringify({ accountNumber, action, reason }),
  });
}

async function getCreditRiskMe() {
  return apiRequest("/credit-risk/me");
}

async function adminCreditRiskHighRisk(limit = 25, level = "high") {
  const params = new URLSearchParams({ limit: String(limit), level: String(level || "high") });
  return apiRequest(`/admin/credit-risk/high-risk?${params.toString()}`);
}

async function adminListCreditRiskSnapshots(limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/credit-risk/snapshots?${params.toString()}`);
}

async function adminLabelCreditRiskSnapshot(snapshotId, actualLabel) {
  return apiRequest("/admin/credit-risk/label", {
    method: "POST",
    body: JSON.stringify({ snapshotId, actualLabel }),
  });
}

async function adminCreditRiskModelStatus() {
  return apiRequest("/admin/credit-risk/model-status");
}

async function adminTrainCreditRiskModel() {
  return apiRequest("/admin/credit-risk/train", { method: "POST" });
}

async function getFinanceCopilotMe() {
  return apiRequest("/finance/copilot/me");
}

async function getFinancePrefsMe() {
  return apiRequest("/finance/prefs/me");
}

async function updateFinancePrefsMe(payload) {
  return apiRequest("/finance/prefs/me", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function getChurnMe() {
  return apiRequest("/churn/me");
}

async function adminChurnHighRisk(limit = 25, level = "high") {
  const params = new URLSearchParams({ limit: String(limit), level: String(level || "high") });
  return apiRequest(`/admin/churn/high-risk?${params.toString()}`);
}

async function adminListChurnSnapshots(limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/churn/snapshots?${params.toString()}`);
}

async function adminLabelChurnSnapshot(snapshotId, actualLabel) {
  return apiRequest("/admin/churn/label", {
    method: "POST",
    body: JSON.stringify({ snapshotId, actualLabel }),
  });
}

async function adminChurnModelStatus() {
  return apiRequest("/admin/churn/model-status");
}

async function adminTrainChurnModel() {
  return apiRequest("/admin/churn/train", { method: "POST" });
}

async function adminChurnNbaModelStatus() {
  return apiRequest("/admin/churn/nba/model-status");
}

async function adminTrainChurnNbaModel() {
  return apiRequest("/admin/churn/nba/train", { method: "POST" });
}

async function adminChurnNbaOfferPerformance(limit = 400) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiRequest(`/admin/churn/nba/offer-performance?${params.toString()}`);
}

// Session helpers

function setSession(session) {
  const nextSession = {
    accountNumber: session?.accountNumber || "",
    isAdmin: !!session?.isAdmin,
    // Keep optional token only for temporary backward compatibility.
    accessToken: session?.accessToken || null,
  };
  sessionStorage.setItem(BANK_SESSION_KEY, JSON.stringify(nextSession));
}

function getSession() {
  const raw = sessionStorage.getItem(BANK_SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function clearSession() {
  sessionStorage.removeItem(BANK_SESSION_KEY);
}

async function getCurrentUser() {
  const session = getSession();
  if (!session || !session.accountNumber) return null;
  try {
    return await apiRequest("/users/me");
  } catch {
    clearSession();
    return null;
  }
}

async function logoutSession() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch {
    // Ignore logout API failures and still clear local session.
  } finally {
    clearSession();
  }
}



