from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=False, default="")
    gender = Column(String(20), nullable=False, default="")
    dob = Column(String(30), nullable=False, default="")
    address = Column(String(255), nullable=False, default="")
    open_account_type = Column(String(40), nullable=False, default="")
    account_number = Column(String(32), unique=True, index=True, nullable=False)
    balance = Column(Float, nullable=False, default=0)
    password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    card_blocked = Column(Boolean, nullable=False, default=False)
    kyc_verified = Column(Boolean, nullable=False, default=False)
    kyc_verified_at = Column(DateTime(timezone=True), nullable=True)
    transactions_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(30), nullable=False, index=True)  # insurance | investment
    risk_level = Column(String(20), nullable=False, default="moderate")
    min_age = Column(Integer, nullable=False, default=18)
    max_age = Column(Integer, nullable=False, default=100)
    min_balance = Column(Float, nullable=False, default=0)
    summary = Column(Text, nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # accepted | rejected | saved
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, default="")
    tags = Column(String(255), nullable=False, default="")  # comma-separated tags
    content = Column(Text, nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VoiceAuditLog(Base):
    __tablename__ = "voice_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    intent = Column(String(40), nullable=False, default="unknown")
    transcript = Column(Text, nullable=False, default="")
    confidence = Column(Float, nullable=False, default=0)
    requires_step_up = Column(Boolean, nullable=False, default=False)
    status = Column(String(30), nullable=False, default="requested")  # requested|verified|executed|failed
    detail_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupportChatLog(Base):
    __tablename__ = "support_chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    user_message = Column(Text, nullable=False, default="")
    reply = Column(Text, nullable=False, default="")
    blocked_for_privacy = Column(Boolean, nullable=False, default=False)
    source_count = Column(Integer, nullable=False, default=0)
    source_titles_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KycSubmission(Base):
    __tablename__ = "kyc_submissions"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="pending")  # pending|approved|rejected|manual_review
    selfie_path = Column(String(512), nullable=False, default="")
    id_path = Column(String(512), nullable=False, default="")
    liveness_score = Column(Float, nullable=False, default=0)
    face_distance = Column(Float, nullable=True)
    name_match_score = Column(Float, nullable=False, default=0)
    ocr_preview = Column(Text, nullable=False, default="")
    reasons_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoanDocumentAiLog(Base):
    __tablename__ = "loan_document_ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False, default="")
    document_type = Column(String(40), nullable=False, default="unknown")  # salary_slip | bank_statement | unknown
    monthly_income_extracted = Column(Float, nullable=True)
    emi_extracted = Column(Float, nullable=True)
    income_verification_status = Column(String(30), nullable=False, default="not_checked")
    confidence = Column(Float, nullable=False, default=0)
    corrected_document_type = Column(String(40), nullable=True)
    corrected_monthly_income = Column(Float, nullable=True)
    corrected_emi = Column(Float, nullable=True)
    review_status = Column(String(30), nullable=False, default="pending")  # pending | approved | needs_correction | rejected
    reviewer_notes = Column(Text, nullable=False, default="")
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    raw_text_preview = Column(Text, nullable=False, default="")
    extracted_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoanDocumentAiModel(Base):
    __tablename__ = "loan_document_ai_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    model_json = Column(Text, nullable=False, default="{}")
    metrics_json = Column(Text, nullable=False, default="{}")


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)

    dob = Column(String(30), nullable=False, default="")
    loan_type = Column(String(30), nullable=False)
    loan_amount = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    monthly_income = Column(Float, nullable=False)
    existing_emi_total = Column(Float, nullable=False)
    credit_score = Column(Integer, nullable=True)

    secured = Column(Boolean, nullable=False, default=False)
    collateral_value = Column(Float, nullable=True)

    estimated_emi = Column(Float, nullable=False)
    dti = Column(Float, nullable=False)
    sanction_score = Column(Float, nullable=False)
    recommendation = Column(String(30), nullable=False)  # approve | manual_review | decline
    actual_recommendation = Column(String(30), nullable=True)  # Phase-2 label: actual underwriting outcome
    reasons_json = Column(Text, nullable=False, default="[]")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoanSanctionModel(Base):
    __tablename__ = "loan_sanction_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    weights_json = Column(Text, nullable=False)  # logistic regression weights + feature order
    feature_means_json = Column(Text, nullable=False)
    feature_stds_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")


class CreditScorecardModel(Base):
    __tablename__ = "credit_scorecard_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    # LONGTEXT is required because serialized ML models can exceed TEXT size.
    model_blob = Column(LONGTEXT, nullable=False)  # base64/zlib payload
    feature_means_json = Column(Text, nullable=False, default="[]")
    metrics_json = Column(Text, nullable=False, default="{}")


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    transaction_type = Column(String(30), nullable=False)  # withdraw | transfer-out
    amount = Column(Float, nullable=False)
    phase1_score = Column(Float, nullable=False, default=0)
    risk_score = Column(Float, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="low")  # low | medium | high
    status = Column(String(20), nullable=False, default="open")  # open | reviewed | blocked
    actual_label = Column(String(20), nullable=True)  # fraud | legit (admin labeled)
    reasons_json = Column(Text, nullable=False, default="[]")
    context_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FraudRiskModel(Base):
    __tablename__ = "fraud_risk_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    weights_json = Column(Text, nullable=False)  # logistic regression weights + feature order
    feature_means_json = Column(Text, nullable=False)
    feature_stds_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")


class FraudRealtimeModel(Base):
    __tablename__ = "fraud_realtime_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    weights_json = Column(Text, nullable=False)
    feature_means_json = Column(Text, nullable=False)
    feature_stds_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")


class AmlGraphModel(Base):
    __tablename__ = "aml_graph_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    model_json = Column(Text, nullable=False, default="{}")
    metrics_json = Column(Text, nullable=False, default="{}")


class AmlCase(Base):
    __tablename__ = "aml_cases"

    id = Column(Integer, primary_key=True, index=True)
    ring_id = Column(String(64), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open")
    priority = Column(String(20), nullable=False, default="medium")
    watchlist = Column(Boolean, nullable=False, default=False)
    assignee = Column(String(120), nullable=False, default="")
    risk_score = Column(Float, nullable=False, default=0)
    account_count = Column(Integer, nullable=False, default=0)
    accounts_json = Column(Text, nullable=False, default="[]")
    reasons_json = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CreditRiskSnapshot(Base):
    __tablename__ = "credit_risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    phase1_score = Column(Float, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0)  # 0..100 (higher = higher risk)
    level = Column(String(20), nullable=False, default="low")  # low | medium | high
    actual_label = Column(String(20), nullable=True)  # defaulted | on_time (admin labeled)
    reasons_json = Column(Text, nullable=False, default="[]")
    features_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CreditRiskModel(Base):
    __tablename__ = "credit_risk_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    weights_json = Column(Text, nullable=False)
    feature_means_json = Column(Text, nullable=False)
    feature_stds_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")


class FinancePreference(Base):
    __tablename__ = "finance_preferences"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, unique=True, index=True)
    budgets_json = Column(Text, nullable=False, default="{}")  # { category: monthlyBudgetAmount }
    goal_json = Column(Text, nullable=False, default="{}")  # { targetAmount, dueDate(YYYY-MM-DD) }
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChurnSnapshot(Base):
    __tablename__ = "churn_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(32), ForeignKey("users.account_number"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0)  # 0..100 (higher = higher churn risk)
    level = Column(String(20), nullable=False, default="low")  # low | medium | high
    phase1_score = Column(Float, nullable=False, default=0)
    actual_label = Column(String(20), nullable=True)  # churned | retained (admin labeled)
    reasons_json = Column(Text, nullable=False, default="[]")
    features_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChurnModel(Base):
    __tablename__ = "churn_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    weights_json = Column(Text, nullable=False)
    feature_means_json = Column(Text, nullable=False)
    feature_stds_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")


class ChurnOfferModel(Base):
    __tablename__ = "churn_offer_models"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    model_json = Column(Text, nullable=False, default="{}")  # per-offer uplift weights/normalization
    metrics_json = Column(Text, nullable=False, default="{}")
