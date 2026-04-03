from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    id: str
    type: Literal["deposit", "withdraw", "transfer-in", "transfer-out"]
    amount: float
    prevBalance: float
    newBalance: float
    note: Optional[str] = ""
    mode: Optional[str] = ""
    counterpartyAccount: Optional[str] = ""
    counterpartyName: Optional[str] = ""
    timestamp: datetime


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    phone: str = Field(min_length=1)
    gender: str = ""
    dob: str = ""
    address: str = ""
    openAccountType: str = ""
    password: str = Field(min_length=6)
    initialDeposit: float = 0
    isAdmin: bool = False


class UserUpdate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    phone: str = Field(min_length=1)
    password: Optional[str] = None


class UserOut(BaseModel):
    name: str
    email: str
    phone: str
    gender: str
    dob: str
    address: str
    openAccountType: str = ""
    accountNumber: str
    balance: float
    isAdmin: bool
    cardBlocked: bool
    kycVerified: bool = False
    kycVerifiedAt: datetime | None = None
    transactions: list[Transaction]
    createdAt: datetime


class KycSubmitOut(BaseModel):
    status: Literal["approved", "rejected", "manual_review"]
    message: str
    livenessScore: float
    faceDistance: float | None = None
    nameMatchScore: float
    ocrPreview: str
    reasons: list[str]
    clientLivenessOk: bool = True
    antiSpoofReal: bool | None = None
    antiSpoofScore: float | None = None
    sharpnessScore: float | None = None


class KycStatusOut(BaseModel):
    kycVerified: bool
    kycVerifiedAt: datetime | None = None
    lastStatus: str | None = None
    lastSubmittedAt: datetime | None = None


class AdminKycSubmissionOut(BaseModel):
    id: int
    accountNumber: str
    name: str
    status: str
    livenessScore: float
    faceDistance: float | None
    nameMatchScore: float
    ocrPreview: str
    reasons: list[str]
    createdAt: datetime


class VoiceIntentIn(BaseModel):
    transcript: str = Field(min_length=2)


class VoiceIntentOut(BaseModel):
    intent: Literal["check_balance", "transfer", "card_block", "card_unblock", "unknown"]
    confidence: float
    message: str
    requiresStepUp: bool = False
    challengeId: str | None = None
    toAccount: str | None = None
    amount: float | None = None


class VoiceStepUpIn(BaseModel):
    challengeId: str = Field(min_length=6)
    password: str = Field(min_length=1)


class VoiceStepUpOut(BaseModel):
    verified: bool
    message: str


class VoiceExecuteIn(BaseModel):
    challengeId: str = Field(min_length=6)


class VoiceExecuteOut(BaseModel):
    ok: bool
    message: str
    balance: float | None = None


class VoiceCardStatusOut(BaseModel):
    cardBlocked: bool


class AdminVoiceAuditItem(BaseModel):
    id: int
    accountNumber: str
    intent: str
    transcript: str
    confidence: float
    requiresStepUp: bool
    status: str
    detail: dict
    createdAt: datetime


class LoginIn(BaseModel):
    identifier: str
    password: str


class LoginOut(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: UserOut


class QuickActionIn(BaseModel):
    type: Literal["deposit", "withdraw"]
    amount: float = Field(gt=0)


class TransferIn(BaseModel):
    fromAccount: str
    toAccount: str
    amount: float = Field(gt=0)
    mode: str = "IMPS"
    note: str = ""


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=6)


class PublicRecoverEmailIn(BaseModel):
    accountNumber: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    dob: str = Field(min_length=1)


class PublicRecoverEmailOut(BaseModel):
    email: str


class PublicForgotPasswordIn(BaseModel):
    accountNumber: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    newPassword: str = Field(min_length=6)


class PublicForgotPasswordOut(BaseModel):
    ok: bool = True
    message: str = "Password updated. You can sign in with your new password."


class AiRecommendIn(BaseModel):
    goal: str = "wealth-creation"
    riskLevel: str = "moderate"  # low | moderate | high


class ProductSuggestion(BaseModel):
    productId: int
    name: str
    category: str
    score: float
    reason: str
    summary: str


class AiRecommendOut(BaseModel):
    riskProfile: str
    insurance: list[ProductSuggestion]
    investment: list[ProductSuggestion]
    disclaimer: str


class AiChatIn(BaseModel):
    message: str = Field(min_length=2)
    goal: str = "wealth-creation"
    riskLevel: str = "moderate"
    forcedTopicKey: str | None = None


class AiChatOut(BaseModel):
    reply: str
    suggestedInsurance: list[str]
    suggestedInvestment: list[str]
    disclaimer: str


class KnowledgeBaseDocIn(BaseModel):
    title: str = Field(default="", max_length=200)
    tags: str = Field(default="", max_length=255)  # comma-separated
    content: str = Field(min_length=10)
    active: bool = True


class KnowledgeBaseDocOut(BaseModel):
    id: int
    title: str
    tags: str
    content: str
    active: bool
    createdAt: datetime


class KnowledgeBaseSource(BaseModel):
    docId: int
    title: str
    score: float
    snippet: str


class AiChatRagIn(BaseModel):
    message: str = Field(min_length=2)
    goal: str = "wealth-creation"
    riskLevel: str = "moderate"
    forcedTopicKey: str | None = None
    topK: int = Field(default=3, ge=1, le=6)


class AiChatRagOut(BaseModel):
    reply: str
    sources: list[KnowledgeBaseSource]
    suggestedInsurance: list[str]
    suggestedInvestment: list[str]
    disclaimer: str


class SupportChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=1200)
    topK: int = Field(default=4, ge=1, le=8)


class SupportChatOut(BaseModel):
    reply: str
    safeResponse: bool = True
    blockedForPrivacy: bool = False
    sources: list[KnowledgeBaseSource]
    disclaimer: str


class AdminSupportChatLogItem(BaseModel):
    id: int
    accountNumber: str
    userMessage: str
    blockedForPrivacy: bool
    sourceCount: int
    sourceTitles: list[str]
    createdAt: datetime


class AdminSupportChatSummaryOut(BaseModel):
    total: int
    blocked: int
    safe: int


class AdminSupportBlockedIntentItem(BaseModel):
    intent: str
    count: int


class RecommendationFeedbackIn(BaseModel):
    productId: int
    action: Literal["accepted", "rejected", "saved"]


class AdminProductIn(BaseModel):
    name: str = Field(min_length=2)
    category: Literal["insurance", "investment"]
    riskLevel: Literal["low", "moderate", "high"]
    minAge: int = Field(ge=18, le=100)
    maxAge: int = Field(ge=18, le=100)
    minBalance: float = Field(ge=0)
    summary: str = Field(min_length=5)
    active: bool = True


class AdminProductOut(BaseModel):
    id: int
    name: str
    category: str
    riskLevel: str
    minAge: int
    maxAge: int
    minBalance: float
    summary: str
    active: bool


class FeedbackSummaryItem(BaseModel):
    productId: int
    productName: str
    category: str
    accepted: int
    saved: int
    rejected: int


class AiDiagnosticProductItem(BaseModel):
    productId: int
    productName: str
    category: str
    scoreAdjustment: float
    accepted: int
    saved: int
    rejected: int
    totalFeedback: int
    conversionRate: float
    trend7d: str


class AiFeedbackTrendItem(BaseModel):
    date: str
    accepted: int
    saved: int
    rejected: int


class AiDiagnosticsOut(BaseModel):
    topBoosted: list[AiDiagnosticProductItem]
    topPenalized: list[AiDiagnosticProductItem]
    trend: list[AiFeedbackTrendItem]


class LoanSanctionIn(BaseModel):
    loanType: Literal["personal", "home", "vehicle", "business"] = "personal"
    dob: str = ""
    loanAmount: float = Field(gt=0)
    tenureMonths: int = Field(gt=0, le=600)
    monthlyIncome: float = Field(gt=0)
    existingEmiTotal: float = Field(ge=0)
    creditScore: Optional[int] = Field(default=None, ge=300, le=850)

    secured: bool = False
    collateralValue: Optional[float] = Field(default=None, gt=0)


class LoanSanctionOut(BaseModel):
    estimatedEmi: float
    dti: float
    sanctionScore: float
    recommendation: Literal["approve", "manual_review", "decline"]
    reasons: list[str]
    disclaimer: str


class LoanDocumentExtractOut(BaseModel):
    documentType: Literal["salary_slip", "bank_statement", "unknown"]
    monthlyIncomeExtracted: float | None = None
    existingEmiExtracted: float | None = None
    incomeVerificationStatus: Literal["verified", "mismatch", "not_checked"]
    confidence: float
    extractedFields: dict
    rawTextPreview: str
    reasons: list[str]


class LoanDocumentItemOut(BaseModel):
    logId: int
    fileName: str
    documentType: Literal["salary_slip", "bank_statement", "unknown"]
    monthlyIncomeExtracted: float | None = None
    existingEmiExtracted: float | None = None
    confidence: float
    rawTextPreview: str


class LoanDocumentMultiExtractOut(BaseModel):
    documents: list[LoanDocumentItemOut]
    reconciledMonthlyIncome: float | None = None
    reconciledExistingEmi: float | None = None
    incomeVerificationStatus: Literal["verified", "mismatch", "not_checked"]
    confidence: float
    reasons: list[str]


class AdminLoanDocumentAiItemOut(BaseModel):
    id: int
    accountNumber: str
    fileName: str
    documentType: str
    monthlyIncomeExtracted: float | None = None
    existingEmiExtracted: float | None = None
    correctedMonthlyIncome: float | None = None
    correctedExistingEmi: float | None = None
    reviewStatus: str
    confidence: float
    incomeVerificationStatus: str
    createdAt: datetime


class AdminLoanDocumentAiReviewIn(BaseModel):
    logId: int
    correctedDocumentType: Literal["salary_slip", "bank_statement", "unknown"] | None = None
    correctedMonthlyIncome: float | None = Field(default=None, ge=0)
    correctedExistingEmi: float | None = Field(default=None, ge=0)
    reviewStatus: Literal["approved", "needs_correction", "rejected"] = "approved"
    reviewerNotes: str = ""


class LoanDocumentAiModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class LoanDocumentAiTrainOut(BaseModel):
    trained: bool
    samples: int
    salarySlipCount: int
    bankStatementCount: int
    message: str


class LoanDecisionLabelIn(BaseModel):
    applicationId: int
    actualRecommendation: Literal["approve", "manual_review", "decline"]


class LoanTrainOut(BaseModel):
    trained: bool
    samples: int
    labeledApproveCount: int
    approveRate: float
    message: str


class LoanModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class CreditScorecardModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class CreditScorecardTrainOut(BaseModel):
    trained: bool
    samples: int
    approveRate: float
    message: str


class FeatureContributionItem(BaseModel):
    feature: str
    value: float
    impact: float


class LoanScorecardExplainOut(BaseModel):
    applicationId: int
    recommendation: Literal["approve", "manual_review", "decline"]
    approveProbability: float
    rejectProbability: float
    summary: str
    topContributions: list[FeatureContributionItem]


class LoanApplicationListItem(BaseModel):
    id: int
    accountNumber: str
    dob: str
    loanType: str
    loanAmount: float
    tenureMonths: int
    monthlyIncome: float
    existingEmiTotal: float
    creditScore: int | None
    secured: bool
    collateralValue: float | None
    estimatedEmi: float
    dti: float
    sanctionScore: float
    recommendation: Literal["approve", "manual_review", "decline"]
    actualRecommendation: str | None
    createdAt: datetime


class FraudAlertOut(BaseModel):
    id: int
    accountNumber: str
    transactionType: str
    amount: float
    phase1Score: float
    riskScore: float
    riskLevel: Literal["low", "medium", "high"]
    status: Literal["open", "reviewed", "blocked"]
    actualLabel: Literal["fraud", "legit"] | None = None
    reasons: list[str]
    createdAt: datetime


class FraudAlertStatusIn(BaseModel):
    alertId: int
    status: Literal["open", "reviewed", "blocked"]


class FraudAlertSummaryOut(BaseModel):
    total: int
    open: int
    high: int
    blocked: int


class FraudAlertLabelIn(BaseModel):
    alertId: int
    actualLabel: Literal["fraud", "legit"]


class FraudModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class FraudTrainOut(BaseModel):
    trained: bool
    samples: int
    fraudCount: int
    fraudRate: float
    message: str


class FraudRealtimeModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class FraudRealtimeTrainOut(BaseModel):
    trained: bool
    samples: int
    fraudCount: int
    fraudRate: float
    message: str


class AmlGraphModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class AmlGraphTrainOut(BaseModel):
    trained: bool
    samples: int
    fraudSeedCount: int
    message: str


class AmlSuspiciousRingItem(BaseModel):
    ringId: str
    riskScore: float
    accountCount: int
    beneficiaryCount: int
    deviceCount: int
    ipCount: int
    accounts: list[str]
    reasons: list[str]


class AmlCaseCreateFromRingIn(BaseModel):
    ringId: str
    riskScore: float = Field(ge=0, le=100)
    accounts: list[str]
    reasons: list[str] = []


class AmlCaseUpdateIn(BaseModel):
    caseId: int
    status: Literal["open", "investigating", "escalated", "closed"] | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    watchlist: bool | None = None
    assignee: str | None = None
    notes: str | None = None


class AmlCaseOut(BaseModel):
    id: int
    ringId: str
    status: Literal["open", "investigating", "escalated", "closed"]
    priority: Literal["low", "medium", "high", "critical"]
    watchlist: bool
    assignee: str
    riskScore: float
    accountCount: int
    accounts: list[str]
    reasons: list[str]
    notes: str
    createdAt: datetime
    updatedAt: datetime


class AmlAutomationRunOut(BaseModel):
    processedRings: int
    createdCases: int
    updatedCases: int
    escalatedCases: int
    message: str


class AmlCaseAlertLinkOut(BaseModel):
    caseId: int
    ringId: str
    linkedAlerts: int
    highRiskAlerts: int
    blockedAlerts: int
    latestAlertAt: datetime | None = None


class AdminFraudNetworkRiskItem(BaseModel):
    accountNumber: str
    name: str
    cardBlocked: bool
    fanIn30d: int
    fanOut30d: int
    receiverFanIn30d: int
    muleRiskScore: float
    level: Literal["low", "medium", "high"]
    reasons: list[str]


class FraudAccountActionIn(BaseModel):
    accountNumber: str
    action: Literal["freeze", "unfreeze"]
    reason: str = ""


class CreditRiskOut(BaseModel):
    accountNumber: str
    periodStart: datetime
    periodEnd: datetime
    score: float
    level: Literal["low", "medium", "high"]
    reasons: list[str]
    recommendedActions: list[str]
    usedPhase2Model: bool = False
    modelDefaultProbability: float | None = None


class AdminCreditRiskItem(BaseModel):
    accountNumber: str
    name: str
    email: str
    phone: str
    balance: float
    score: float
    level: Literal["low", "medium", "high"]
    periodEnd: datetime
    reasons: list[str]


class CreditRiskSnapshotItem(BaseModel):
    id: int
    accountNumber: str
    score: float
    level: Literal["low", "medium", "high"]
    phase1Score: float
    actualLabel: Literal["defaulted", "on_time"] | None = None
    periodEnd: datetime


class CreditRiskLabelIn(BaseModel):
    snapshotId: int
    actualLabel: Literal["defaulted", "on_time"]


class CreditRiskModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class CreditRiskTrainOut(BaseModel):
    trained: bool
    samples: int
    defaultedCount: int
    defaultRate: float
    message: str


class FinanceCategorySpend(BaseModel):
    category: str
    amount: float
    count: int


class FinanceCopilotOut(BaseModel):
    accountNumber: str
    periodStart: datetime
    periodEnd: datetime
    inflow: float
    outflow: float
    net: float
    topSpends: list[FinanceCategorySpend]
    tips: list[str]
    budgets: dict[str, float] = {}
    budgetAlerts: list[str] = []
    savingsGoal: dict = {}
    goalAlerts: list[str] = []


class FinancePrefsIn(BaseModel):
    budgets: dict[str, float] = {}
    savingsGoal: dict = {}


class FinancePrefsOut(BaseModel):
    budgets: dict[str, float]
    savingsGoal: dict


class ChurnRiskOut(BaseModel):
    accountNumber: str
    score: float
    level: Literal["low", "medium", "high"]
    reasons: list[str]
    retentionTips: list[str]
    usedPhase2Model: bool = False
    modelChurnProbability: float | None = None
    nextBestOffer: str | None = None
    expectedRetentionLift: float | None = None
    upliftScores: dict[str, float] = Field(default_factory=dict)


class AdminChurnRiskItem(BaseModel):
    accountNumber: str
    name: str
    email: str
    phone: str
    balance: float
    score: float
    level: Literal["low", "medium", "high"]
    lastActiveAt: datetime | None = None
    reasons: list[str]
    nextBestOffer: str | None = None
    expectedRetentionLift: float | None = None


class ChurnSnapshotItem(BaseModel):
    id: int
    accountNumber: str
    score: float
    level: Literal["low", "medium", "high"]
    phase1Score: float
    actualLabel: Literal["churned", "retained"] | None = None
    createdAt: datetime


class ChurnLabelIn(BaseModel):
    snapshotId: int
    actualLabel: Literal["churned", "retained"]


class ChurnModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None


class ChurnTrainOut(BaseModel):
    trained: bool
    samples: int
    churnedCount: int
    churnRate: float
    message: str


class ChurnNbaModelStatusOut(BaseModel):
    trained: bool
    trainedAt: datetime | None = None
    version: int | None = None
    samples: int | None = None
    offers: list[str] = []


class ChurnNbaTrainOut(BaseModel):
    trained: bool
    samples: int
    message: str
    offers: list[str] = []


class ChurnNbaOfferPerformanceItem(BaseModel):
    offer: str
    avgUplift: float
    highRiskUsers: int
    mediumRiskUsers: int
    recommendedUsers: int
