import os

import json
import math
import re
import hashlib
import base64
import pickle
import zlib
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import Base, engine, get_db
from models import (
    CreditRiskSnapshot,
    CreditRiskModel,
    ChurnSnapshot,
    ChurnModel,
    ChurnOfferModel,
    FinancePreference,
    FraudAlert,
    FraudRiskModel,
    FraudRealtimeModel,
    AmlGraphModel,
    AmlCase,
    KnowledgeBaseDocument,
    LoanDocumentAiLog,
    LoanDocumentAiModel,
    VoiceAuditLog,
    SupportChatLog,
    LoanApplication,
    LoanSanctionModel,
    CreditScorecardModel,
    Product,
    RecommendationFeedback,
    User,
)
from schemas import (
    AiChatIn,
    AiChatOut,
    AiChatRagIn,
    AiChatRagOut,
    SupportChatIn,
    SupportChatOut,
    AdminSupportChatLogItem,
    AdminSupportChatSummaryOut,
    AdminSupportBlockedIntentItem,
    AiDiagnosticProductItem,
    AiDiagnosticsOut,
    AiFeedbackTrendItem,
    AdminProductIn,
    AdminProductOut,
    AiRecommendIn,
    AiRecommendOut,
    FeedbackSummaryItem,
    LoginIn,
    LoginOut,
    PasswordResetIn,
    PublicForgotPasswordIn,
    PublicForgotPasswordOut,
    PublicRecoverEmailIn,
    PublicRecoverEmailOut,
    QuickActionIn,
    RecommendationFeedbackIn,
    TransferIn,
    ProductSuggestion,
    UserCreate,
    UserOut,
    UserUpdate,
    LoanSanctionIn,
    LoanDocumentExtractOut,
    LoanDocumentItemOut,
    LoanDocumentMultiExtractOut,
    AdminLoanDocumentAiItemOut,
    AdminLoanDocumentAiReviewIn,
    LoanDocumentAiModelStatusOut,
    LoanDocumentAiTrainOut,
    LoanSanctionOut,
    LoanDecisionLabelIn,
    LoanTrainOut,
    LoanModelStatusOut,
    CreditScorecardModelStatusOut,
    CreditScorecardTrainOut,
    LoanScorecardExplainOut,
    FeatureContributionItem,
    LoanApplicationListItem,
    FraudAlertOut,
    FraudAlertLabelIn,
    FraudAlertStatusIn,
    FraudAlertSummaryOut,
    FraudModelStatusOut,
    FraudTrainOut,
    AdminFraudNetworkRiskItem,
    FraudAccountActionIn,
    FraudRealtimeModelStatusOut,
    FraudRealtimeTrainOut,
    AmlGraphModelStatusOut,
    AmlGraphTrainOut,
    AmlSuspiciousRingItem,
    AmlCaseCreateFromRingIn,
    AmlCaseUpdateIn,
    AmlCaseOut,
    AmlAutomationRunOut,
    AmlCaseAlertLinkOut,
    CreditRiskOut,
    AdminCreditRiskItem,
    CreditRiskSnapshotItem,
    CreditRiskLabelIn,
    CreditRiskModelStatusOut,
    CreditRiskTrainOut,
    FinanceCopilotOut,
    FinanceCategorySpend,
    FinancePrefsIn,
    FinancePrefsOut,
    ChurnRiskOut,
    AdminChurnRiskItem,
    ChurnSnapshotItem,
    ChurnLabelIn,
    ChurnModelStatusOut,
    ChurnTrainOut,
    ChurnNbaModelStatusOut,
    ChurnNbaTrainOut,
    ChurnNbaOfferPerformanceItem,
    KnowledgeBaseDocIn,
    KnowledgeBaseDocOut,
    KnowledgeBaseSource,
    VoiceIntentIn,
    VoiceIntentOut,
    VoiceStepUpIn,
    VoiceStepUpOut,
    VoiceExecuteIn,
    VoiceExecuteOut,
    VoiceCardStatusOut,
    AdminVoiceAuditItem,
)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    LogisticRegression = None
    GradientBoostingClassifier = None

app = FastAPI(title="JPND Bank API")

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:3000")
ALLOWED_CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
if not ALLOWED_CORS_ORIGINS:
    ALLOWED_CORS_ORIGINS = ["http://localhost:3000"]
if APP_ENV not in {"production", "prod"} and "null" not in ALLOWED_CORS_ORIGINS:
    # Browsers send Origin: null when opening pages via file://
    ALLOWED_CORS_ORIGINS.append("null")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS_ORIGINS,
    # In development, allow any localhost origin (e.g. Live Server 5500) while still supporting cookies.
    allow_origin_regex=(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if APP_ENV not in {"production", "prod"} else None),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "jaydee-bank-dev-secret")
JWT_ALG = "HS256"
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "180"))
DAILY_WITHDRAW_LIMIT = 1_000_000.0
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "jpnd_access_token")
AUTH_COOKIE_SECURE = APP_ENV in {"production", "prod"}

if APP_ENV in {"production", "prod"}:
    if (not JWT_SECRET) or (JWT_SECRET == "jaydee-bank-dev-secret") or (len(JWT_SECRET) < 32):
        raise RuntimeError(
            "Unsafe JWT_SECRET for production. Set a strong JWT_SECRET (>=32 chars) in backend/.env."
        )

# In-memory step-up challenges for Voice Banking (demo only).
_VOICE_CHALLENGES: dict[str, dict] = {}
_LOGIN_ATTEMPTS: dict[str, dict] = {}
_LOGIN_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCK_SECONDS = 15 * 60


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    # Minimal CSP suitable for current static pages.
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:8000 http://127.0.0.1:8000"
    return response


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _fmt_inr(amount: float) -> str:
    return f"₹{amount:,.2f}"


def _kb_require_ml():
    if TfidfVectorizer is None:
        raise HTTPException(
            status_code=500,
            detail="Knowledge Base ML is not available. Install backend requirements (scikit-learn) and restart.",
        )


def _voice_require_ml():
    if TfidfVectorizer is None or LogisticRegression is None:
        raise HTTPException(
            status_code=500,
            detail="Voice intent ML is not available. Install backend requirements (scikit-learn) and restart.",
        )


def _voice_normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().replace("-", " ").split())


def _voice_extract_amount(text: str) -> float | None:
    import re

    m = re.search(r"(?:rs\.?|inr|rupees)?\s*([0-9][0-9,]{1,})(?:\.\d+)?", text)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        v = float(raw)
    except Exception:
        return None
    if v <= 0:
        return None
    return float(v)


def _voice_extract_to_account(text: str) -> str | None:
    import re

    # Prefer explicit patterns like "to 1234567890" or "to account 123..."
    m = re.search(r"(?:to|beneficiary)\s+(?:account\s+)?(\d{6,32})", text)
    if m:
        return m.group(1)
    # Fallback: any long number in the transcript
    m2 = re.search(r"\b(\d{8,32})\b", text)
    return m2.group(1) if m2 else None


def _voice_intent_model_predict(text: str) -> tuple[str, float]:
    """
    Tiny ML classifier trained on built-in examples at runtime.
    Returns (intent, confidence 0..1).
    """
    t = _voice_normalize(text)
    # Keyword hard overrides for safety.
    if any(k in t for k in ["balance", "available balance", "check balance", "current balance"]):
        return "check_balance", 0.95
    if any(k in t for k in ["unblock card", "activate card", "enable card", "unfreeze card"]):
        return "card_unblock", 0.95
    if any(k in t for k in ["block card", "card block", "freeze card", "stop card", "disable card"]):
        return "card_block", 0.95
    if any(k in t for k in ["transfer", "send money", "pay", "imps", "neft", "rtgs", "upi"]):
        return "transfer", 0.9

    _voice_require_ml()
    train_texts = [
        "check my balance",
        "what is my account balance",
        "show current balance",
        "available balance please",
        "send money to account",
        "transfer 5000 to 9988776655",
        "make a transfer of 1200 rupees",
        "pay 2500 to beneficiary",
        "block my card",
        "freeze my debit card",
        "disable card now",
        "stop card usage",
        "unblock my card",
        "activate my card",
        "enable my debit card",
    ]
    train_labels = [
        "check_balance",
        "check_balance",
        "check_balance",
        "check_balance",
        "transfer",
        "transfer",
        "transfer",
        "transfer",
        "card_block",
        "card_block",
        "card_block",
        "card_block",
        "card_unblock",
        "card_unblock",
        "card_unblock",
    ]

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=1200)
    X = vectorizer.fit_transform(train_texts)
    clf = LogisticRegression(max_iter=250)
    clf.fit(X, train_labels)

    q = vectorizer.transform([t])
    probs = clf.predict_proba(q)[0]
    classes = list(clf.classes_)
    best_i = int(max(range(len(probs)), key=lambda i: probs[i]))
    intent = str(classes[best_i])
    conf = float(probs[best_i])
    if conf < 0.45:
        return "unknown", float(conf)
    return intent, float(conf)


def _loan_doc_extract_text_easyocr_image(file_path: str) -> str:
    try:
        import easyocr
    except Exception:
        return ""
    try:
        reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
        parts = reader.readtext(file_path, detail=0)
        return " ".join(str(p) for p in (parts or []) if p).strip()
    except Exception:
        return ""


def _loan_doc_extract_text_pdf(file_path: str, temp_dir: Path) -> str:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""
    doc = None
    try:
        doc = fitz.open(file_path)
        parts = [doc[i].get_text() or "" for i in range(len(doc))]
        plain = "\n".join(parts).strip()
        ocr_addon = ""
        if len(plain) < 40 and len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_path = temp_dir / f"_loan_ocr_{uuid4().hex}.png"
            png_path.write_bytes(pix.tobytes("png"))
            ocr_addon = _loan_doc_extract_text_easyocr_image(str(png_path))
            try:
                png_path.unlink(missing_ok=True)
            except Exception:
                pass
        return (plain + "\n" + ocr_addon).strip()
    except Exception:
        return ""
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def _load_latest_loan_doc_ai_model(db: Session) -> LoanDocumentAiModel | None:
    return db.execute(
        select(LoanDocumentAiModel).order_by(LoanDocumentAiModel.trained_at.desc()).limit(1)
    ).scalars().first()


def _loan_doc_tokenize(text_value: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{3,}", (text_value or "").lower()) if len(t) >= 3]


def _loan_doc_classify(document_text: str, file_name: str = "", db: Session | None = None) -> tuple[str, float]:
    txt = f"{(file_name or '').lower()} {(document_text or '').lower()}"
    salary_hits = sum(
        1
        for k in [
            "salary slip",
            "salary",
            "payslip",
            "pay slip",
            "net pay",
            "gross pay",
            "employer",
            "earnings",
            "deductions",
        ]
        if k in txt
    )
    statement_hits = sum(
        1
        for k in [
            "bank statement",
            "account statement",
            "opening balance",
            "closing balance",
            "debit",
            "credit",
            "txn",
            "transaction",
            "ifsc",
        ]
        if k in txt
    )

    if salary_hits == 0 and statement_hits == 0:
        rule_type, rule_conf = "unknown", 0.25
    elif salary_hits >= statement_hits:
        total = max(1, salary_hits + statement_hits)
        rule_type, rule_conf = "salary_slip", float(min(0.98, 0.55 + (salary_hits / total) * 0.4))
    else:
        total = max(1, salary_hits + statement_hits)
        rule_type, rule_conf = "bank_statement", float(min(0.98, 0.55 + (statement_hits / total) * 0.4))

    # Phase-2: blend with trained token model if available.
    if db is None:
        return rule_type, rule_conf
    model = _load_latest_loan_doc_ai_model(db)
    if not model:
        return rule_type, rule_conf
    try:
        mj = json.loads(model.model_json or "{}")
        priors = mj.get("priors") or {}
        token_log_probs = mj.get("token_log_probs") or {}
        classes = ["salary_slip", "bank_statement"]
        tokens = _loan_doc_tokenize(txt)
        scores = {}
        for c in classes:
            s = float(priors.get(c, -0.7))
            tok_map = token_log_probs.get(c, {})
            for t in tokens:
                s += float(tok_map.get(t, 0.0))
            scores[c] = s
        ml_type = max(classes, key=lambda c: scores[c])
        # Soft confidence from score gap
        gap = abs(scores["salary_slip"] - scores["bank_statement"])
        ml_conf = float(min(0.99, 0.55 + min(gap, 2.0) * 0.2))
        if rule_type == "unknown":
            return ml_type, ml_conf
        # Weighted blend of rule and model.
        if ml_type == rule_type:
            return rule_type, float(min(0.99, (rule_conf * 0.6) + (ml_conf * 0.4)))
        # Disagree: pick the one with stronger confidence.
        return (ml_type, ml_conf) if ml_conf > rule_conf else (rule_type, rule_conf)
    except Exception:
        return rule_type, rule_conf


def _loan_doc_amount_candidates(text_value: str) -> list[float]:
    vals: list[float] = []
    for m in re.findall(r"(?:inr|rs\.?|₹)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{4,9})(?:\.[0-9]{1,2})?", text_value, flags=re.I):
        raw = str(m).replace(",", "").strip()
        try:
            v = float(raw)
        except Exception:
            continue
        if 500 <= v <= 5_00_00_000:
            vals.append(v)
    return vals


def _loan_doc_extract_kv(document_type: str, text_value: str) -> tuple[float | None, float | None, dict, list[str]]:
    txt = (text_value or "").lower()
    reasons: list[str] = []
    extracted: dict = {"documentType": document_type}
    income: float | None = None
    emi: float | None = None

    # Pattern-based key-value extraction
    income_patterns = [
        r"(?:net\s*pay|net\s*salary|monthly\s*salary|gross\s*salary|gross\s*pay|salary)\s*[:\-]?\s*₹?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"(?:credited\s*salary|salary\s*credited)\s*[:\-]?\s*₹?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    emi_patterns = [
        r"(?:emi|loan\s*emi|installment|instalment|monthly\s*emi)\s*[:\-]?\s*₹?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]

    for p in income_patterns:
        m = re.search(p, txt, flags=re.I)
        if m:
            try:
                income = float(m.group(1).replace(",", ""))
                reasons.append("Income extracted from salary-related key-value field.")
                break
            except Exception:
                pass
    for p in emi_patterns:
        m = re.search(p, txt, flags=re.I)
        if m:
            try:
                emi = float(m.group(1).replace(",", ""))
                reasons.append("EMI extracted from installment field.")
                break
            except Exception:
                pass

    # Fallback from amount candidates if patterns are missing.
    amounts = _loan_doc_amount_candidates(txt)
    if income is None and amounts:
        plausible = [x for x in amounts if 5_000 <= x <= 8_00_000]
        if plausible:
            income = float(max(plausible))
            reasons.append("Income estimated from highest plausible amount in OCR text.")
    if emi is None and amounts:
        plausible_emi = [x for x in amounts if 500 <= x <= 2_00_000]
        if plausible_emi:
            emi = float(min(plausible_emi))
            reasons.append("EMI estimated from smallest plausible recurring amount.")

    if document_type == "bank_statement":
        # Statement-specific heuristic: mention that this is estimate from credits.
        if income is not None:
            reasons.append("Bank statement detected: income treated as estimated monthly credit.")

    extracted["monthlyIncome"] = income
    extracted["existingEmiTotal"] = emi
    return income, emi, extracted, reasons


def _loan_doc_verify_income(stated_monthly_income: float | None, extracted_income: float | None) -> tuple[str, list[str]]:
    if stated_monthly_income is None or extracted_income is None or stated_monthly_income <= 0:
        return "not_checked", []
    delta = abs(extracted_income - stated_monthly_income)
    ratio = delta / float(stated_monthly_income)
    if ratio <= 0.2:
        return "verified", [f"Document income is close to stated income (difference {ratio * 100.0:.1f}%)."]
    return "mismatch", [f"Document income differs from stated income by {ratio * 100.0:.1f}%."]


def _loan_doc_apply_calibration(
    db: Session, monthly_income: float | None, existing_emi: float | None
) -> tuple[float | None, float | None, list[str]]:
    reasons: list[str] = []
    model = _load_latest_loan_doc_ai_model(db)
    if not model:
        return monthly_income, existing_emi, reasons
    try:
        mj = json.loads(model.model_json or "{}")
        calib = mj.get("calibration") or {}
        income_mul = float(calib.get("incomeMultiplier", 1.0) or 1.0)
        emi_mul = float(calib.get("emiMultiplier", 1.0) or 1.0)
        if monthly_income is not None:
            monthly_income = float(monthly_income) * income_mul
        if existing_emi is not None:
            existing_emi = float(existing_emi) * emi_mul
        if abs(income_mul - 1.0) > 0.01:
            reasons.append(f"Phase-2 calibration applied on income (x{income_mul:.3f}).")
        if abs(emi_mul - 1.0) > 0.01:
            reasons.append(f"Phase-2 calibration applied on EMI (x{emi_mul:.3f}).")
    except Exception:
        return monthly_income, existing_emi, reasons
    return monthly_income, existing_emi, reasons


def _ensure_loan_doc_upload_dir(account_number: str) -> Path:
    d = Path(__file__).resolve().parent / "uploads" / "loan_documents" / str(account_number).strip()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _loan_doc_save_and_extract(
    *,
    file: UploadFile,
    account_number: str,
    stated_monthly_income: float | None,
    db: Session,
) -> tuple[LoanDocumentAiLog, dict]:
    allowed_ct = {"application/pdf"}
    ct = (file.content_type or "").split(";")[0].strip().lower()
    fname_lower = (file.filename or "").lower()
    is_pdf_name = fname_lower.endswith(".pdf")
    if ct not in allowed_ct and not (ct == "application/octet-stream" and is_pdf_name):
        raise HTTPException(status_code=400, detail="Only PDF loan documents are accepted.")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be 8MB or less.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF.")

    temp_dir = _ensure_loan_doc_upload_dir(account_number)
    fname = f"loan_doc_{uuid4().hex}.pdf"
    file_path = temp_dir / fname
    file_path.write_bytes(data)

    text_value = _loan_doc_extract_text_pdf(str(file_path), temp_dir)
    if not text_value:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to extract text from {file.filename or 'document'}. Upload clearer file.",
        )

    doc_type, doc_conf = _loan_doc_classify(text_value, file.filename or "", db=db)
    monthly_income, existing_emi, extracted_fields, reasons = _loan_doc_extract_kv(doc_type, text_value)
    monthly_income, existing_emi, calib_reasons = _loan_doc_apply_calibration(db, monthly_income, existing_emi)
    reasons.extend(calib_reasons)
    extracted_fields["fileName"] = str(file.filename or fname)
    verify_status, verify_reasons = _loan_doc_verify_income(stated_monthly_income, monthly_income)
    reasons.extend(verify_reasons)

    row = LoanDocumentAiLog(
        account_number=account_number,
        file_name=str(file.filename or fname),
        document_type=doc_type,
        monthly_income_extracted=float(monthly_income) if monthly_income is not None else None,
        emi_extracted=float(existing_emi) if existing_emi is not None else None,
        income_verification_status=verify_status,
        confidence=float(doc_conf),
        raw_text_preview=(text_value[:1000] + "…") if len(text_value) > 1000 else text_value,
        extracted_json=json.dumps(extracted_fields),
    )
    db.add(row)
    return row, {
        "documentType": doc_type,
        "monthlyIncomeExtracted": float(monthly_income) if monthly_income is not None else None,
        "existingEmiExtracted": float(existing_emi) if existing_emi is not None else None,
        "incomeVerificationStatus": verify_status,
        "confidence": float(round(doc_conf, 4)),
        "extractedFields": extracted_fields,
        "rawTextPreview": (text_value[:400] + "…") if len(text_value) > 400 else text_value,
        "reasons": reasons,
    }


def _loan_doc_reconcile(items: list[dict]) -> tuple[float | None, float | None, float, list[str]]:
    reasons: list[str] = []
    if not items:
        return None, None, 0.0, reasons

    # Weight salary slip more for income, statement more for EMI evidence.
    income_num = 0.0
    income_den = 0.0
    emi_num = 0.0
    emi_den = 0.0
    conf_sum = 0.0
    for it in items:
        dt = str(it.get("documentType") or "unknown")
        conf = float(it.get("confidence") or 0.0)
        conf_sum += conf
        inc = it.get("monthlyIncomeExtracted")
        emi = it.get("existingEmiExtracted")
        w_income = conf * (1.4 if dt == "salary_slip" else (1.0 if dt == "bank_statement" else 0.8))
        w_emi = conf * (1.3 if dt == "bank_statement" else (1.0 if dt == "salary_slip" else 0.8))
        if inc is not None:
            income_num += float(inc) * w_income
            income_den += w_income
        if emi is not None:
            emi_num += float(emi) * w_emi
            emi_den += w_emi

    reconciled_income = (income_num / income_den) if income_den > 0 else None
    reconciled_emi = (emi_num / emi_den) if emi_den > 0 else None
    confidence = conf_sum / float(len(items))
    reasons.append("Reconciled values computed using weighted multi-document fusion.")
    if reconciled_income is not None:
        reasons.append(f"Reconciled monthly income: {reconciled_income:.2f}")
    if reconciled_emi is not None:
        reasons.append(f"Reconciled EMI total: {reconciled_emi:.2f}")
    return reconciled_income, reconciled_emi, float(round(confidence, 4)), reasons


def _voice_audit(
    db: Session,
    *,
    account_number: str,
    intent: str,
    transcript: str,
    confidence: float,
    requires_step_up: bool,
    status: str,
    detail: dict | None = None,
):
    db.add(
        VoiceAuditLog(
            account_number=account_number,
            intent=intent,
            transcript=(transcript or "")[:500],
            confidence=float(confidence or 0.0),
            requires_step_up=bool(requires_step_up),
            status=status,
            detail_json=json.dumps(detail or {}),
        )
    )


def _kb_safe_snippet(text: str, max_len: int = 240) -> str:
    t = " ".join((text or "").replace("\n", " ").split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _kb_build_sources(message: str, docs: list[KnowledgeBaseDocument], top_k: int = 3):
    _kb_require_ml()
    if not docs:
        return []

    corpus = []
    for d in docs:
        corpus.append(f"{d.title}\n{d.tags}\n{d.content}")
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4000)
    X = vectorizer.fit_transform(corpus)
    q = vectorizer.transform([message])
    # cosine similarity for L2-normalized tf-idf vectors is dot product
    sims = (X @ q.T).toarray().reshape(-1).tolist()
    ranked = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)[: max(1, min(top_k, 6))]
    out: list[KnowledgeBaseSource] = []
    for idx, s in ranked:
        d = docs[idx]
        out.append(
            KnowledgeBaseSource(
                docId=int(d.id),
                title=str(d.title or "").strip() or f"KB Doc #{d.id}",
                score=float(round(float(s), 6)),
                snippet=_kb_safe_snippet(d.content or ""),
            )
        )
    return out


def _is_same_utc_day(iso_ts: str, ref_dt: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return dt.astimezone(timezone.utc).date() == ref_dt.astimezone(timezone.utc).date()


def _estimate_age_from_dob(dob: str) -> int:
    # Supports DD/MM/YYYY and ISO-style dates.
    dob = (dob or "").strip()
    if not dob:
        return 30
    parsed = None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(dob, fmt).date()
            break
        except ValueError:
            continue
    if not parsed:
        return 30
    today = datetime.now(timezone.utc).date()
    return max(18, today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day)))


def _to_transactions(raw: str):
    try:
        parsed = json.loads(raw or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _parse_iso_ts(ts_raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts_raw or "").replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _sum_txns(txns: list[dict], start: datetime, end: datetime, types: set[str]) -> float:
    total = 0.0
    for t in txns:
        if str(t.get("type") or "") not in types:
            continue
        ts = _parse_iso_ts(str(t.get("timestamp") or ""))
        if not ts:
            continue
        if start <= ts <= end:
            total += float(t.get("amount") or 0.0)
    return float(total)


def _count_txns(txns: list[dict], start: datetime, end: datetime, types: set[str]) -> int:
    n = 0
    for t in txns:
        if str(t.get("type") or "") not in types:
            continue
        ts = _parse_iso_ts(str(t.get("timestamp") or ""))
        if not ts:
            continue
        if start <= ts <= end:
            n += 1
    return int(n)


def _credit_risk_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _credit_risk_phase1(
    *,
    txns: list[dict],
    balance_now: float,
    period_start: datetime,
    period_end: datetime,
) -> tuple[float, str, list[str], dict, list[str]]:
    """
    Returns: (score 0..100, level, reasons[], features{}, recommendedActions[])
    """
    income = _sum_txns(txns, period_start, period_end, {"deposit", "transfer-in"})
    outgoing = _sum_txns(txns, period_start, period_end, {"withdraw", "transfer-out"})
    outgoing_cnt = _count_txns(txns, period_start, period_end, {"withdraw", "transfer-out"})

    ratio = (outgoing / income) if income > 0 else (1.5 if outgoing > 0 else 0.0)
    ratio = float(max(0.0, ratio))

    score = 0.0
    reasons: list[str] = []
    actions: list[str] = []

    if income <= 0 and outgoing > 0:
        score += 45
        reasons.append("No recorded inflow in last 30 days, but outgoing payments exist.")
        actions.append("Try to route salary/income credits into this account for stability.")
    elif ratio >= 1.2:
        score += 45
        reasons.append("Outflow is significantly higher than inflow in last 30 days.")
        actions.append("Reduce discretionary spending or increase inflows to improve cashflow.")
    elif ratio >= 0.9:
        score += 30
        reasons.append("Outflow is close to inflow in last 30 days (tight cashflow).")
        actions.append("Keep a buffer balance and avoid high-value non-essential transfers.")
    elif ratio >= 0.7:
        score += 15
        reasons.append("Moderate cashflow pressure observed in last 30 days.")

    if balance_now < 2_000:
        score += 20
        reasons.append("Low current balance buffer (< ₹2,000).")
        actions.append("Maintain a minimum buffer (e.g., ₹5,000+) to avoid stress.")
    elif balance_now < 10_000:
        score += 10
        reasons.append("Current balance buffer is modest (< ₹10,000).")

    if outgoing_cnt >= 20:
        score += 15
        reasons.append("High frequency of outgoing transactions in last 30 days.")
        actions.append("Consolidate small transfers; set monthly spending caps.")
    elif outgoing_cnt >= 12:
        score += 8
        reasons.append("Moderately high outgoing transaction frequency in last 30 days.")

    score = float(max(0.0, min(100.0, score)))
    level = _credit_risk_level(score)

    if level == "high":
        actions.append("Avoid taking new debt until cashflow stabilizes for 1-2 months.")
        actions.append("If you have EMIs, consider pre-paying small debts to reduce burden.")
    elif level == "medium":
        actions.append("Track next 30 days spending; aim to reduce outflow/inflow ratio below 0.8.")

    features = {
        "income30d": float(round(income, 2)),
        "outgoing30d": float(round(outgoing, 2)),
        "outgoingCount30d": int(outgoing_cnt),
        "outflowToInflowRatio30d": float(round(ratio, 4)),
        "balanceNow": float(round(balance_now, 2)),
    }
    return score, level, reasons, features, actions


def _finance_category_for_txn(t: dict) -> str:
    note = str(t.get("note") or "").lower()
    mode = str(t.get("mode") or "").lower()
    tx_type = str(t.get("type") or "")

    if tx_type in {"deposit", "transfer-in"}:
        if "salary" in note:
            return "Income - Salary"
        if "refund" in note:
            return "Income - Refund"
        return "Income - Other"

    if "rent" in note:
        return "Housing - Rent"
    if any(k in note for k in ["grocery", "supermarket", "mart", "provision"]):
        return "Food - Groceries"
    if any(k in note for k in ["restaurant", "hotel", "cafe", "swiggy", "zomato", "food"]):
        return "Food - Dining"
    if any(k in note for k in ["fuel", "petrol", "diesel"]):
        return "Transport - Fuel"
    if any(k in note for k in ["uber", "ola", "cab", "taxi", "bus", "train", "metro"]):
        return "Transport - Travel"
    if any(k in note for k in ["electric", "eb", "water", "gas", "broadband", "wifi", "recharge", "mobile"]):
        return "Bills - Utilities"
    if any(k in note for k in ["hospital", "medical", "pharmacy", "doctor", "clinic", "health"]):
        return "Health"
    if any(k in note for k in ["education", "school", "college", "tuition", "fees"]):
        return "Education"
    if any(k in note for k in ["emi", "loan"]):
        return "Debt/EMI"
    if any(k in note for k in ["insurance", "premium"]):
        return "Insurance"
    if "imps" in mode or "neft" in mode or "rtgs" in mode or "upi" in mode:
        return "Transfers"
    return "Other"


def _load_finance_prefs(db: Session, account_number: str) -> FinancePreference | None:
    return (
        db.execute(select(FinancePreference).where(FinancePreference.account_number == account_number))
        .scalars()
        .first()
    )


def _safe_json_obj(raw: str, default: dict) -> dict:
    try:
        parsed = json.loads(raw or "")
        return parsed if isinstance(parsed, dict) else default
    except Exception:
        return default


def _last_active_at_from_txns(txns: list[dict]) -> datetime | None:
    latest = None
    for t in txns:
        ts = _parse_iso_ts(str(t.get("timestamp") or ""))
        if not ts:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def _churn_level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _churn_phase1(*, txns: list[dict], balance_now: float, created_at: datetime | None) -> tuple[float, str, list[str], dict, list[str], datetime | None]:
    now_utc = datetime.now(timezone.utc)
    last_active = _last_active_at_from_txns(txns)
    if not last_active and created_at:
        last_active = created_at.astimezone(timezone.utc)

    days_inactive = None
    if last_active:
        days_inactive = (now_utc - last_active).days

    start_30d = now_utc - timedelta(days=30)
    txn_count_30d = _count_txns(txns, start_30d, now_utc, {"deposit", "withdraw", "transfer-in", "transfer-out"})

    score = 0.0
    reasons: list[str] = []
    tips: list[str] = []

    if days_inactive is None:
        score += 35
        reasons.append("No recent activity timestamp detected.")
        tips.append("Try a small deposit/transfer to keep the account active.")
    elif days_inactive >= 45:
        score += 55
        reasons.append(f"No transactions in last {days_inactive} days.")
        tips.append("Set a monthly auto-transfer or bill payment reminder.")
    elif days_inactive >= 21:
        score += 35
        reasons.append(f"Low recent activity (inactive {days_inactive} days).")
        tips.append("Enable account alerts and try weekly small savings.")
    elif days_inactive >= 10:
        score += 15
        reasons.append(f"Activity reduced recently (inactive {days_inactive} days).")

    if txn_count_30d <= 1:
        score += 25
        reasons.append("Very low transaction frequency in last 30 days.")
        tips.append("Link your salary/income credits for better account usage.")
    elif txn_count_30d <= 3:
        score += 15
        reasons.append("Low transaction frequency in last 30 days.")

    if balance_now <= 500:
        score += 15
        reasons.append("Very low balance; account may become dormant.")
        tips.append("Maintain a minimum buffer balance (e.g., ₹1,000+).")
    elif balance_now <= 2000:
        score += 8
        reasons.append("Low balance buffer.")

    score = float(max(0.0, min(100.0, score)))
    level = _churn_level(score)

    if level == "high":
        tips.append("Consider activating a recurring deposit or auto-savings to stay engaged.")
    elif level == "medium":
        tips.append("Try a weekly savings challenge to build habit and avoid dormancy.")

    features = {
        "daysInactive": int(days_inactive) if days_inactive is not None else None,
        "txnCount30d": int(txn_count_30d),
        "balanceNow": float(round(balance_now, 2)),
    }
    return score, level, reasons, features, tips[:6], last_active


_CHURN_MODEL_FEATURES = [
    "phase1_score",
    "days_inactive",
    "txn_count_30d",
    "balance_now",
]


def _churn_label_to_binary(actual_label: str | None) -> int:
    if not actual_label:
        return 0
    return 1 if str(actual_label).lower() == "churned" else 0


def _churn_features_from_snapshot(s: ChurnSnapshot) -> list[float]:
    try:
        f = json.loads(s.features_json or "{}")
        if not isinstance(f, dict):
            f = {}
    except Exception:
        f = {}
    return [
        float(s.phase1_score or 0.0),
        float((f.get("daysInactive") or 0) or 0.0),
        float((f.get("txnCount30d") or 0) or 0.0),
        float((f.get("balanceNow") or 0) or 0.0),
    ]


def _load_latest_churn_model(db: Session) -> ChurnModel | None:
    return db.execute(select(ChurnModel).order_by(ChurnModel.trained_at.desc())).scalars().first()


def _predict_churn_probability_with_model(
    model: ChurnModel, feature_vector: list[float]
) -> tuple[float, list[tuple[str, float, float]]]:
    weights_blob = json.loads(model.weights_json or "{}")
    bias = float(weights_blob.get("bias", 0.0))
    weights = weights_blob.get("weights", [])

    means = json.loads(model.feature_means_json or "[]")
    stds = json.loads(model.feature_stds_json or "[]")

    n = min(len(_CHURN_MODEL_FEATURES), len(feature_vector), len(weights), len(means), len(stds))
    if n <= 0:
        return 0.5, []

    contributions: list[tuple[str, float, float]] = []
    z = bias
    for i in range(n):
        std = float(stds[i] or 1.0)
        if std < 1e-6:
            std = 1.0
        x_std = (float(feature_vector[i]) - float(means[i])) / std
        w = float(weights[i])
        z += w * x_std
        contributions.append((_CHURN_MODEL_FEATURES[i], w * x_std, float(feature_vector[i])))

    prob = _sigmoid(z)
    return float(prob), contributions


def _blend_churn_scores(phase1_score: float, prob_churn: float) -> float:
    return float(round((0.6 * float(phase1_score)) + (0.4 * float(prob_churn) * 100.0), 2))


_CHURN_OFFERS = ["cashback", "fee_waiver", "smart_reminder"]
_CHURN_OFFER_LABELS = {
    "cashback": "Cashback offer on digital transactions",
    "fee_waiver": "Monthly fee waiver for active usage",
    "smart_reminder": "Personalized reminder nudges",
}


def _offer_assignment_for_snapshot(snapshot_id: int, account_number: str) -> str:
    seed = f"{snapshot_id}:{account_number}".encode("utf-8")
    idx = int(hashlib.sha256(seed).hexdigest(), 16) % len(_CHURN_OFFERS)
    return _CHURN_OFFERS[idx]


def _train_ridge_regression(
    X: list[list[float]],
    y: list[float],
    *,
    feature_means: list[float],
    feature_stds: list[float],
    lr: float = 0.02,
    steps: int = 700,
    l2_lambda: float = 0.08,
) -> tuple[list[float], float]:
    if not X:
        return [], 0.0
    m = len(X)
    n = len(X[0])
    w = [0.0 for _ in range(n)]
    b = 0.0
    for _ in range(steps):
        grad_w = [0.0 for _ in range(n)]
        grad_b = 0.0
        for i in range(m):
            xs: list[float] = []
            for j in range(n):
                std = float(feature_stds[j] or 1.0)
                if std < 1e-6:
                    std = 1.0
                val = (float(X[i][j]) - float(feature_means[j])) / std
                if val > 8:
                    val = 8
                elif val < -8:
                    val = -8
                xs.append(val)
            pred = b + sum(w[j] * xs[j] for j in range(n))
            err = pred - float(y[i])
            grad_b += err
            for j in range(n):
                grad_w[j] += err * xs[j]
        grad_b /= m
        for j in range(n):
            grad_w[j] = (grad_w[j] / m) + (l2_lambda * w[j] / m)
            w[j] -= lr * grad_w[j]
        b -= lr * grad_b
    return w, b


def _load_latest_churn_offer_model(db: Session) -> ChurnOfferModel | None:
    return db.execute(select(ChurnOfferModel).order_by(ChurnOfferModel.trained_at.desc())).scalars().first()


def _predict_churn_offer_uplift(
    model: ChurnOfferModel,
    feature_vector: list[float],
) -> tuple[str | None, float | None, dict[str, float]]:
    try:
        blob = json.loads(model.model_json or "{}")
    except Exception:
        blob = {}
    offers_blob = blob.get("offers", {})
    if not isinstance(offers_blob, dict):
        return None, None, {}

    scores: dict[str, float] = {}
    for offer in _CHURN_OFFERS:
        ob = offers_blob.get(offer)
        if not isinstance(ob, dict):
            continue
        weights = ob.get("weights", [])
        means = ob.get("means", [])
        stds = ob.get("stds", [])
        bias = float(ob.get("bias", 0.0))
        n = min(len(feature_vector), len(weights), len(means), len(stds), len(_CHURN_MODEL_FEATURES))
        if n <= 0:
            continue
        z = bias
        for i in range(n):
            std = float(stds[i] or 1.0)
            if std < 1e-6:
                std = 1.0
            xstd = (float(feature_vector[i]) - float(means[i])) / std
            if xstd > 8:
                xstd = 8
            elif xstd < -8:
                xstd = -8
            z += float(weights[i]) * xstd
        # Keep uplift bounded and interpretable as expected retention lift delta.
        score = float(max(-1.0, min(1.0, z)))
        scores[offer] = score

    if not scores:
        return None, None, {}
    best_offer = max(scores.items(), key=lambda kv: kv[1])[0]
    best_lift = float(scores.get(best_offer, 0.0))
    if best_lift <= 0.0:
        return None, None, scores
    return best_offer, best_lift, scores


_CREDIT_RISK_MODEL_FEATURES = [
    "phase1_score",
    "income30d",
    "outgoing30d",
    "outgoingCount30d",
    "outflowToInflowRatio30d",
    "balanceNow",
]


def _credit_features_from_snapshot(s: CreditRiskSnapshot) -> list[float]:
    try:
        f = json.loads(s.features_json or "{}")
        if not isinstance(f, dict):
            f = {}
    except Exception:
        f = {}
    return [
        float(s.phase1_score or 0.0),
        float(f.get("income30d") or 0.0),
        float(f.get("outgoing30d") or 0.0),
        float(f.get("outgoingCount30d") or 0.0),
        float(f.get("outflowToInflowRatio30d") or 0.0),
        float(f.get("balanceNow") or 0.0),
    ]


def _credit_label_to_binary(actual_label: str | None) -> int:
    if not actual_label:
        return 0
    return 1 if str(actual_label).lower() == "defaulted" else 0


def _load_latest_credit_risk_model(db: Session) -> CreditRiskModel | None:
    return db.execute(
        select(CreditRiskModel).order_by(CreditRiskModel.trained_at.desc())
    ).scalars().first()


def _predict_default_probability_with_model(
    model: CreditRiskModel, feature_vector: list[float]
) -> tuple[float, list[tuple[str, float, float]]]:
    weights_blob = json.loads(model.weights_json or "{}")
    bias = float(weights_blob.get("bias", 0.0))
    weights = weights_blob.get("weights", [])

    means = json.loads(model.feature_means_json or "[]")
    stds = json.loads(model.feature_stds_json or "[]")

    n = min(
        len(_CREDIT_RISK_MODEL_FEATURES),
        len(feature_vector),
        len(weights),
        len(means),
        len(stds),
    )
    if n <= 0:
        return 0.5, []

    contributions: list[tuple[str, float, float]] = []
    z = bias
    for i in range(n):
        std = float(stds[i] or 1.0)
        if std < 1e-6:
            std = 1.0
        x_std = (float(feature_vector[i]) - float(means[i])) / std
        w = float(weights[i])
        z += w * x_std
        contributions.append((_CREDIT_RISK_MODEL_FEATURES[i], w * x_std, float(feature_vector[i])))

    prob = _sigmoid(z)
    return float(prob), contributions


def _blend_credit_scores(phase1_score: float, prob_default: float) -> float:
    # Blend phase-1 score (0..100) with model probability (0..1 -> 0..100)
    return float(round((0.6 * float(phase1_score)) + (0.4 * float(prob_default) * 100.0), 2))


def _to_fraud_alert_out(a: FraudAlert) -> FraudAlertOut:
    try:
        reasons = json.loads(a.reasons_json or "[]")
        reasons = reasons if isinstance(reasons, list) else []
    except Exception:
        reasons = []
    return FraudAlertOut(
        id=int(a.id),
        accountNumber=a.account_number,
        transactionType=a.transaction_type,
        amount=float(a.amount or 0),
        phase1Score=float(a.phase1_score or 0),
        riskScore=float(a.risk_score or 0),
        riskLevel=(a.risk_level or "low"),
        status=(a.status or "open"),
        actualLabel=(a.actual_label if a.actual_label in {"fraud", "legit"} else None),
        reasons=[str(r) for r in reasons],
        createdAt=a.created_at,
    )


def _count_recent_outgoing(txns: list[dict], now_utc: datetime, minutes: int = 60) -> int:
    count = 0
    for t in txns:
        if t.get("type") not in {"withdraw", "transfer-out"}:
            continue
        ts_raw = str(t.get("timestamp") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        delta = now_utc - ts.astimezone(timezone.utc)
        if timedelta(minutes=0) <= delta <= timedelta(minutes=minutes):
            count += 1
    return count


def _has_prior_beneficiary(txns: list[dict], to_account: str) -> bool:
    to_account = (to_account or "").strip()
    if not to_account:
        return False
    for t in txns:
        if t.get("type") != "transfer-out":
            continue
        if str(t.get("counterpartyAccount") or "").strip() == to_account:
            return True
    return False


def _fraud_phase1_score(
    *,
    tx_type: str,
    amount: float,
    balance_before: float,
    now_utc: datetime,
    recent_outgoing_count: int,
    is_new_beneficiary: bool,
) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if amount >= 500_000:
        score += 40
        reasons.append("High amount transaction (>= ₹5,00,000)")
    elif amount >= 200_000:
        score += 25
        reasons.append("Large amount transaction (>= ₹2,00,000)")

    if balance_before > 0 and (amount / balance_before) >= 0.60:
        score += 20
        reasons.append("Amount is >= 60% of available balance")

    if now_utc.hour < 6 or now_utc.hour >= 22:
        score += 15
        reasons.append("Unusual transaction hour")

    if recent_outgoing_count >= 3:
        score += 20
        reasons.append("Multiple outgoing transactions in last 60 minutes")

    if tx_type == "transfer-out" and is_new_beneficiary:
        score += 20
        reasons.append("First transfer to this beneficiary account")

    score = float(max(0.0, min(100.0, score)))
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"
    return score, level, reasons


_FRAUD_MODEL_FEATURES = [
    "phase1_score",
    "amount",
    "tx_is_transfer",
    "new_beneficiary",
    "recent_outgoing_60m",
    "hour_utc",
    "amount_to_balance_ratio",
    "daily_outgoing_before_ratio",
]


_FRAUD_REALTIME_MODEL_FEATURES = [
    "risk_score_base",
    "phase1_score",
    "amount",
    "tx_is_transfer",
    "new_beneficiary",
    "recent_outgoing_60m",
    "hour_utc",
    "amount_to_balance_ratio",
    "daily_outgoing_before_ratio",
    "sequence_score",
    "graph_score",
    "fan_in_30d",
    "fan_out_30d",
    "receiver_fan_in_30d",
    "receiver_fan_out_30d",
]


def _fraud_features_from_alert(a: FraudAlert) -> list[float]:
    try:
        ctx = json.loads(a.context_json or "{}")
        if not isinstance(ctx, dict):
            ctx = {}
    except Exception:
        ctx = {}

    tx_is_transfer = 1.0 if (a.transaction_type or "") == "transfer-out" else 0.0
    new_beneficiary = 1.0 if bool(ctx.get("newBeneficiary")) else 0.0
    recent_outgoing_60m = float(ctx.get("recentOutgoing60m") or 0.0)
    hour_utc = float(ctx.get("hourUtc") or 0.0)
    amount_to_balance_ratio = float(ctx.get("amountToBalanceRatio") or 0.0)
    daily_outgoing_before_ratio = float(ctx.get("dailyOutgoingBeforeRatio") or 0.0)

    return [
        float(a.phase1_score or 0.0),
        float(a.amount or 0.0),
        tx_is_transfer,
        new_beneficiary,
        recent_outgoing_60m,
        hour_utc,
        amount_to_balance_ratio,
        daily_outgoing_before_ratio,
    ]


def _fraud_realtime_features_from_alert(a: FraudAlert) -> list[float]:
    try:
        ctx = json.loads(a.context_json or "{}")
        if not isinstance(ctx, dict):
            ctx = {}
    except Exception:
        ctx = {}
    gm = ctx.get("graphMetrics") or {}
    if not isinstance(gm, dict):
        gm = {}
    tx_is_transfer = 1.0 if (a.transaction_type or "") == "transfer-out" else 0.0
    new_beneficiary = 1.0 if bool(ctx.get("newBeneficiary")) else 0.0
    return [
        float(ctx.get("riskScoreBase") or a.risk_score or 0.0),
        float(a.phase1_score or 0.0),
        float(a.amount or 0.0),
        tx_is_transfer,
        new_beneficiary,
        float(ctx.get("recentOutgoing60m") or 0.0),
        float(ctx.get("hourUtc") or 0.0),
        float(ctx.get("amountToBalanceRatio") or 0.0),
        float(ctx.get("dailyOutgoingBeforeRatio") or 0.0),
        float(ctx.get("sequenceScore") or 0.0),
        float(ctx.get("graphScore") or 0.0),
        float(gm.get("fanIn30d") or 0.0),
        float(gm.get("fanOut30d") or 0.0),
        float(gm.get("receiverFanIn30d") or 0.0),
        float(gm.get("receiverFanOut30d") or 0.0),
    ]


def _fraud_label_to_binary(actual_label: str | None) -> int:
    if not actual_label:
        return 0
    return 1 if str(actual_label).lower() == "fraud" else 0


def _load_latest_fraud_model(db: Session) -> FraudRiskModel | None:
    return db.execute(select(FraudRiskModel).order_by(FraudRiskModel.trained_at.desc())).scalars().first()


def _load_latest_fraud_realtime_model(db: Session) -> FraudRealtimeModel | None:
    return (
        db.execute(select(FraudRealtimeModel).order_by(FraudRealtimeModel.trained_at.desc()))
        .scalars()
        .first()
    )


def _predict_fraud_probability_with_model(
    model: FraudRiskModel, feature_vector: list[float]
) -> tuple[float, list[tuple[str, float, float]]]:
    weights_blob = json.loads(model.weights_json or "{}")
    bias = float(weights_blob.get("bias", 0.0))
    weights = weights_blob.get("weights", [])

    means = json.loads(model.feature_means_json or "[]")
    stds = json.loads(model.feature_stds_json or "[]")

    n = min(len(_FRAUD_MODEL_FEATURES), len(feature_vector), len(weights), len(means), len(stds))
    if n <= 0:
        return 0.5, []

    contributions: list[tuple[str, float, float]] = []
    z = bias
    for i in range(n):
        std = float(stds[i] or 1.0)
        if std < 1e-6:
            std = 1.0
        x_std = (float(feature_vector[i]) - float(means[i])) / std
        w = float(weights[i])
        z += w * x_std
        contributions.append((_FRAUD_MODEL_FEATURES[i], w * x_std, float(feature_vector[i])))

    prob = _sigmoid(z)
    return float(prob), contributions


def _predict_fraud_probability_with_realtime_model(
    model: FraudRealtimeModel, feature_vector: list[float]
) -> tuple[float, list[tuple[str, float, float]]]:
    weights_blob = json.loads(model.weights_json or "{}")
    bias = float(weights_blob.get("bias", 0.0))
    weights = weights_blob.get("weights", [])
    means = json.loads(model.feature_means_json or "[]")
    stds = json.loads(model.feature_stds_json or "[]")

    n = min(
        len(_FRAUD_REALTIME_MODEL_FEATURES),
        len(feature_vector),
        len(weights),
        len(means),
        len(stds),
    )
    if n <= 0:
        return 0.5, []
    contributions: list[tuple[str, float, float]] = []
    z = bias
    for i in range(n):
        std = float(stds[i] or 1.0)
        if std < 1e-6:
            std = 1.0
        x_std = (float(feature_vector[i]) - float(means[i])) / std
        w = float(weights[i])
        z += w * x_std
        contributions.append((_FRAUD_REALTIME_MODEL_FEATURES[i], w * x_std, float(feature_vector[i])))
    return float(_sigmoid(z)), contributions


def _blend_fraud_scores(phase1_score: float, prob_fraud: float) -> float:
    # Phase-2 gives probability in [0,1]. Convert to a 0..100 scale and blend.
    return float(round((0.65 * float(phase1_score)) + (0.35 * float(prob_fraud) * 100.0), 2))


def _fraud_level_from_score(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _fraud_sequence_score(txns: list[dict], now_utc: datetime, amount: float, balance_before: float) -> tuple[float, list[str]]:
    """
    Lightweight sequence anomaly score inspired by stream models (LSTM/Transformer-style signals).
    Output 0..100.
    """
    recent = []
    for t in txns:
        if t.get("type") not in {"withdraw", "transfer-out"}:
            continue
        ts = _parse_iso_ts(str(t.get("timestamp") or ""))
        if not ts:
            continue
        if now_utc - ts <= timedelta(days=7):
            recent.append((ts, float(t.get("amount") or 0.0)))
    recent.sort(key=lambda x: x[0], reverse=True)
    amounts = [a for _, a in recent[:12]]
    score = 0.0
    reasons: list[str] = []

    if amounts:
        avg = sum(amounts) / float(len(amounts))
        mx = max(amounts)
        if avg > 0 and amount > (avg * 2.5):
            score += 25
            reasons.append("Sequence spike: current amount is much higher than recent outgoing pattern.")
        if len(amounts) >= 5:
            # Burst indicator in last 2 hours.
            burst_cnt = 0
            for ts, _ in recent[:12]:
                if now_utc - ts <= timedelta(hours=2):
                    burst_cnt += 1
            if burst_cnt >= 4:
                score += 20
                reasons.append("Sequence burst: unusually high outgoing frequency in 2 hours.")
        if mx > 0 and amount > (mx * 1.4):
            score += 10
            reasons.append("Sequence max-break: amount exceeds prior max by large margin.")

    if balance_before > 0:
        ratio = amount / balance_before
        if ratio >= 0.75:
            score += 18
            reasons.append("Sequence ratio anomaly: transaction drains major share of balance.")

    if now_utc.hour < 5 or now_utc.hour >= 23:
        score += 12
        reasons.append("Sequence timing anomaly: odd-hour transaction pattern.")

    return float(max(0.0, min(100.0, score))), reasons


def _fraud_graph_metrics(
    db: Session,
    now_utc: datetime,
    src_account: str,
    to_account: str | None = None,
) -> tuple[dict, float, list[str]]:
    """
    Graph/mule-network signals computed from 30-day transfer graph.
    """
    users = db.execute(select(User).where(User.is_admin.is_(False))).scalars().all()
    window_start = now_utc - timedelta(days=30)
    inbound_from: dict[str, set[str]] = {}
    outbound_to: dict[str, set[str]] = {}
    for u in users:
        uacc = str(u.account_number or "")
        txns = _to_transactions(u.transactions_json)
        for t in txns:
            if t.get("type") != "transfer-out":
                continue
            ts = _parse_iso_ts(str(t.get("timestamp") or ""))
            if not ts or ts < window_start:
                continue
            dst = str(t.get("counterpartyAccount") or "").strip()
            if not dst:
                continue
            outbound_to.setdefault(uacc, set()).add(dst)
            inbound_from.setdefault(dst, set()).add(uacc)

    src_fan_out = len(outbound_to.get(src_account, set()))
    src_fan_in = len(inbound_from.get(src_account, set()))
    receiver_fan_in = len(inbound_from.get(to_account, set())) if to_account else 0
    receiver_fan_out = len(outbound_to.get(to_account, set())) if to_account else 0

    score = 0.0
    reasons: list[str] = []
    if src_fan_out >= 8:
        score += 18
        reasons.append("Graph fan-out anomaly: sender pushes funds to many beneficiaries.")
    if src_fan_in >= 5 and src_fan_out >= 5:
        score += 20
        reasons.append("Graph mule pattern: account has both high fan-in and fan-out.")
    if to_account and receiver_fan_in >= 10:
        score += 22
        reasons.append("Beneficiary network anomaly: receiver has high inbound fan-in from multiple senders.")
    if to_account and receiver_fan_in >= 6 and receiver_fan_out >= 6:
        score += 18
        reasons.append("Receiver transit behavior: high fan-in + fan-out (possible layering node).")

    return (
        {
            "fanOut30d": int(src_fan_out),
            "fanIn30d": int(src_fan_in),
            "receiverFanIn30d": int(receiver_fan_in),
            "receiverFanOut30d": int(receiver_fan_out),
        },
        float(max(0.0, min(100.0, score))),
        reasons,
    )


def _blend_fraud_realtime_scores(base_score: float, sequence_score: float, graph_score: float) -> float:
    # Blend: existing model/rules + sequence stream + graph network.
    return float(
        round(
            (0.55 * float(base_score)) + (0.25 * float(sequence_score)) + (0.20 * float(graph_score)),
            2,
        )
    )


def _fraud_should_auto_freeze(*, risk_score: float, sequence_score: float, graph_score: float) -> bool:
    # Phase-1.5 escalation policy for likely mule/compromised behavior.
    return bool(
        (float(risk_score) >= 92.0)
        or (float(graph_score) >= 80.0 and float(sequence_score) >= 60.0)
        or (float(graph_score) >= 88.0)
    )


def _graph_add_edge(adj: dict[str, set[str]], a: str, b: str):
    if not a or not b or a == b:
        return
    adj.setdefault(a, set()).add(b)
    adj.setdefault(b, set()).add(a)


def _txn_ip(tx: dict) -> str:
    raw = str(tx.get("ipAddress") or "").strip()
    if not raw:
        return ""
    return raw.split(",")[0].strip()[:64]


def _txn_device(tx: dict) -> str:
    raw = str(tx.get("deviceId") or tx.get("userAgent") or "").strip()
    return raw[:160]


def _build_aml_graph(db: Session, lookback_days: int = 90) -> tuple[dict[str, set[str]], set[str]]:
    adj: dict[str, set[str]] = {}
    account_nodes: set[str] = set()
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=max(7, int(lookback_days or 90)))
    users = db.execute(select(User).where(User.is_admin.is_(False))).scalars().all()
    for u in users:
        acc = f"acc:{u.account_number}"
        account_nodes.add(acc)
        txns = _to_transactions(u.transactions_json)
        for t in txns:
            ts = _parse_iso_ts(str(t.get("timestamp") or ""))
            if not ts or ts < window_start:
                continue
            tx_type = str(t.get("type") or "")
            if tx_type in {"transfer-out", "transfer-in"}:
                cp = str(t.get("counterpartyAccount") or "").strip()
                if cp:
                    _graph_add_edge(adj, acc, f"ben:{cp}")
            dev = _txn_device(t)
            if dev:
                _graph_add_edge(adj, acc, f"dev:{dev}")
            ip = _txn_ip(t)
            if ip:
                _graph_add_edge(adj, acc, f"ip:{ip}")
    return adj, account_nodes


def _load_latest_aml_graph_model(db: Session) -> AmlGraphModel | None:
    return db.execute(select(AmlGraphModel).order_by(AmlGraphModel.trained_at.desc())).scalars().first()


def _aml_account_score(model: AmlGraphModel | None, account_number: str) -> float | None:
    if not model:
        return None
    try:
        mj = json.loads(model.model_json or "{}")
    except Exception:
        return None
    account_scores = mj.get("accountScores") or {}
    if not isinstance(account_scores, dict):
        return None
    val = account_scores.get(str(account_number))
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def _aml_train_graph_message_passing(
    adj: dict[str, set[str]], account_nodes: set[str], seed_scores: dict[str, float], iters: int = 4
) -> dict[str, float]:
    if not adj:
        return {}
    scores: dict[str, float] = {}
    for n in adj.keys():
        scores[n] = float(max(0.0, min(1.0, seed_scores.get(n, 0.0))))
    for _ in range(max(1, int(iters or 4))):
        nxt = dict(scores)
        for n, nbrs in adj.items():
            if not nbrs:
                continue
            neigh_avg = sum(float(scores.get(m, 0.0)) for m in nbrs) / float(len(nbrs))
            seed = float(seed_scores.get(n, 0.0))
            nxt[n] = float(max(0.0, min(1.0, (0.30 * seed) + (0.70 * neigh_avg))))
        scores = nxt
    # keep account scores only for model payload size
    out: dict[str, float] = {}
    for n in account_nodes:
        if not n.startswith("acc:"):
            continue
        out[n.replace("acc:", "", 1)] = float(round(scores.get(n, 0.0), 6))
    return out


def _aml_priority_from_score(score: float) -> str:
    s = float(score or 0.0)
    if s >= 90:
        return "critical"
    if s >= 75:
        return "high"
    if s >= 55:
        return "medium"
    return "low"


def _to_aml_case_out(c: AmlCase) -> AmlCaseOut:
    try:
        accounts = json.loads(c.accounts_json or "[]")
        if not isinstance(accounts, list):
            accounts = []
    except Exception:
        accounts = []
    try:
        reasons = json.loads(c.reasons_json or "[]")
        if not isinstance(reasons, list):
            reasons = []
    except Exception:
        reasons = []
    status = str(c.status or "open")
    if status not in {"open", "investigating", "escalated", "closed"}:
        status = "open"
    pr = str(c.priority or "medium")
    if pr not in {"low", "medium", "high", "critical"}:
        pr = "medium"
    return AmlCaseOut(
        id=int(c.id),
        ringId=str(c.ring_id or ""),
        status=status,  # type: ignore[arg-type]
        priority=pr,  # type: ignore[arg-type]
        watchlist=bool(c.watchlist),
        assignee=str(c.assignee or ""),
        riskScore=float(c.risk_score or 0.0),
        accountCount=int(c.account_count or 0),
        accounts=[str(a) for a in accounts],
        reasons=[str(r) for r in reasons],
        notes=str(c.notes or ""),
        createdAt=c.created_at,
        updatedAt=c.updated_at,
    )


def _aml_compute_suspicious_rings(
    db: Session,
    *,
    limit: int = 20,
    min_score: float = 0.65,
) -> list[AmlSuspiciousRingItem]:
    limit = max(1, min(int(limit or 20), 200))
    min_score = float(max(0.30, min(0.98, float(min_score or 0.65))))
    model = _load_latest_aml_graph_model(db)
    if not model:
        return []
    try:
        mj = json.loads(model.model_json or "{}")
        account_scores = mj.get("accountScores") or {}
    except Exception:
        return []
    if not isinstance(account_scores, dict) or not account_scores:
        return []
    adj, _account_nodes = _build_aml_graph(db, lookback_days=90)
    risky_accounts = [f"acc:{a}" for a, s in account_scores.items() if float(s or 0.0) >= min_score]
    risky_set = set(risky_accounts)
    visited: set[str] = set()
    rings: list[AmlSuspiciousRingItem] = []

    for start in risky_accounts:
        if start in visited:
            continue
        queue = [start]
        comp_accounts: set[str] = set()
        comp_nodes: set[str] = set()
        while queue:
            n = queue.pop(0)
            if n in visited:
                continue
            visited.add(n)
            comp_nodes.add(n)
            if n.startswith("acc:"):
                comp_accounts.add(n)
            for m in adj.get(n, set()):
                if m.startswith("acc:"):
                    if m in risky_set and m not in visited:
                        queue.append(m)
                else:
                    comp_nodes.add(m)
                    for x in adj.get(m, set()):
                        if x.startswith("acc:") and x in risky_set and x not in visited:
                            queue.append(x)
        if not comp_accounts:
            continue
        acc_ids = sorted(a.replace("acc:", "", 1) for a in comp_accounts)
        ben_cnt = len([n for n in comp_nodes if n.startswith("ben:")])
        dev_cnt = len([n for n in comp_nodes if n.startswith("dev:")])
        ip_cnt = len([n for n in comp_nodes if n.startswith("ip:")])
        score_vals = [float(account_scores.get(a, 0.0)) for a in acc_ids]
        ring_score = float(round((sum(score_vals) / float(len(score_vals))) * 100.0, 2))
        reasons = [
            "Accounts connected through shared beneficiaries/devices/IPs.",
            "High propagated risk from graph-message-passing AML model.",
        ]
        if dev_cnt > 0:
            reasons.append("Shared devices detected across linked accounts.")
        if ip_cnt > 0:
            reasons.append("Shared IP patterns detected across linked accounts.")
        rings.append(
            AmlSuspiciousRingItem(
                ringId=f"RING-{len(rings)+1:03d}",
                riskScore=ring_score,
                accountCount=len(acc_ids),
                beneficiaryCount=int(ben_cnt),
                deviceCount=int(dev_cnt),
                ipCount=int(ip_cnt),
                accounts=acc_ids[:20],
                reasons=reasons[:4],
            )
        )
    rings.sort(key=lambda r: float(r.riskScore), reverse=True)
    return rings[:limit]


def _create_fraud_alert_if_needed(
    *,
    db: Session,
    account_number: str,
    tx_type: str,
    amount: float,
    risk_score: float,
    risk_level: str,
    reasons: list[str],
    context: dict,
    status: str = "open",
    phase1_score: float = 0.0,
):
    if risk_level not in {"medium", "high"}:
        return
    db.add(
        FraudAlert(
            account_number=account_number,
            transaction_type=tx_type,
            amount=float(amount),
            phase1_score=float(phase1_score),
            risk_score=float(risk_score),
            risk_level=risk_level,
            status=status,
            actual_label=None,
            reasons_json=json.dumps(reasons),
            context_json=json.dumps(context),
        )
    )


def _to_user_out(u: User) -> UserOut:
    return UserOut(
        name=u.name,
        email=u.email,
        phone=u.phone,
        gender=u.gender or "",
        dob=u.dob or "",
        address=u.address or "",
        openAccountType=getattr(u, "open_account_type", "") or "",
        accountNumber=u.account_number,
        balance=float(u.balance or 0),
        isAdmin=bool(u.is_admin),
        cardBlocked=bool(getattr(u, "card_blocked", False)),
        transactions=_to_transactions(u.transactions_json),
        createdAt=u.created_at,
    )


def _to_admin_product_out(p: Product) -> AdminProductOut:
    return AdminProductOut(
        id=p.id,
        name=p.name,
        category=p.category,
        riskLevel=p.risk_level,
        minAge=p.min_age,
        maxAge=p.max_age,
        minBalance=float(p.min_balance or 0),
        summary=p.summary,
        active=bool(p.active),
    )


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def _is_bcrypt_hash(value: str) -> bool:
    return isinstance(value, str) and value.startswith("$2")


def _create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.account_number,
        "is_admin": bool(user.is_admin),
        "exp": now + timedelta(minutes=JWT_EXP_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _auth_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token.")
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid auth token.")
    account_number = data.get("sub")
    if not account_number:
        raise HTTPException(status_code=401, detail="Invalid auth token.")
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found for token.")
    return user


def _auth_admin(user: User = Depends(_auth_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return str(request.client.host)[:64]
    return "unknown"


def _login_key(identifier: str, ip: str) -> str:
    return f"{(identifier or '').strip().lower()}|{(ip or 'unknown').strip().lower()}"


def _check_login_rate_limit(identifier: str, ip: str):
    now = datetime.now(timezone.utc)
    key = _login_key(identifier, ip)
    row = _LOGIN_ATTEMPTS.get(key)
    if not row:
        return
    locked_until = row.get("locked_until")
    if isinstance(locked_until, datetime) and now < locked_until:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please try again after 15 minutes.",
        )
    window_start = row.get("window_start")
    if isinstance(window_start, datetime) and (now - window_start).total_seconds() > _LOGIN_WINDOW_SECONDS:
        _LOGIN_ATTEMPTS.pop(key, None)


def _record_login_failure(identifier: str, ip: str):
    now = datetime.now(timezone.utc)
    key = _login_key(identifier, ip)
    row = _LOGIN_ATTEMPTS.get(key) or {"count": 0, "window_start": now, "locked_until": None}
    window_start = row.get("window_start")
    if not isinstance(window_start, datetime) or (now - window_start).total_seconds() > _LOGIN_WINDOW_SECONDS:
        row = {"count": 0, "window_start": now, "locked_until": None}
    row["count"] = int(row.get("count", 0) or 0) + 1
    if row["count"] >= _LOGIN_MAX_ATTEMPTS:
        row["locked_until"] = now + timedelta(seconds=_LOGIN_LOCK_SECONDS)
    _LOGIN_ATTEMPTS[key] = row


def _record_login_success(identifier: str, ip: str):
    _LOGIN_ATTEMPTS.pop(_login_key(identifier, ip), None)


@app.get("/api/finance/prefs/me", response_model=FinancePrefsOut)
def finance_prefs_me(current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    row = _load_finance_prefs(db, current.account_number)
    if not row:
        return FinancePrefsOut(budgets={}, savingsGoal={})
    budgets = _safe_json_obj(row.budgets_json, {})
    goal = _safe_json_obj(row.goal_json, {})
    return FinancePrefsOut(budgets={k: float(v or 0) for k, v in budgets.items()}, savingsGoal=goal)


@app.post("/api/finance/prefs/me", response_model=FinancePrefsOut)
def finance_prefs_update(
    payload: FinancePrefsIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    budgets_in = payload.budgets or {}
    budgets_clean: dict[str, float] = {}
    for k, v in budgets_in.items():
        key = str(k or "").strip()
        if not key:
            continue
        try:
            amt = float(v)
        except Exception:
            amt = 0.0
        if amt < 0:
            amt = 0.0
        budgets_clean[key] = float(round(amt, 2))

    goal_in = payload.savingsGoal or {}
    goal_clean = goal_in if isinstance(goal_in, dict) else {}

    row = _load_finance_prefs(db, current.account_number)
    if row:
        row.budgets_json = json.dumps(budgets_clean)
        row.goal_json = json.dumps(goal_clean)
    else:
        db.add(
            FinancePreference(
                account_number=current.account_number,
                budgets_json=json.dumps(budgets_clean),
                goal_json=json.dumps(goal_clean),
            )
        )
    db.commit()
    return FinancePrefsOut(budgets=budgets_clean, savingsGoal=goal_clean)


@app.get("/api/finance/copilot/me", response_model=FinanceCopilotOut)
def finance_copilot_me(current: User = Depends(_auth_user)):
    txns = _to_transactions(current.transactions_json)
    now_utc = datetime.now(timezone.utc)
    period_end = now_utc
    period_start = now_utc - timedelta(days=30)

    inflow = 0.0
    outflow = 0.0
    cat_totals: dict[str, dict] = {}

    for t in txns:
        ts = _parse_iso_ts(str(t.get("timestamp") or ""))
        if not ts or not (period_start <= ts <= period_end):
            continue
        amt = float(t.get("amount") or 0.0)
        tx_type = str(t.get("type") or "")
        if tx_type in {"deposit", "transfer-in"}:
            inflow += amt
        elif tx_type in {"withdraw", "transfer-out"}:
            outflow += amt

        cat = _finance_category_for_txn(t)
        if cat not in cat_totals:
            cat_totals[cat] = {"amount": 0.0, "count": 0}
        cat_totals[cat]["amount"] += amt if tx_type in {"withdraw", "transfer-out"} else 0.0
        cat_totals[cat]["count"] += 1

    net = inflow - outflow

    top = sorted(
        [
            FinanceCategorySpend(category=k, amount=float(v["amount"]), count=int(v["count"]))
            for k, v in cat_totals.items()
            if float(v["amount"]) > 0
        ],
        key=lambda x: x.amount,
        reverse=True,
    )[:5]

    tips: list[str] = []
    if inflow <= 0 and outflow > 0:
        tips.append("No inflow detected in last 30 days. Consider routing salary/credits to this account.")
    if inflow > 0:
        ratio = outflow / inflow
        if ratio >= 1.2:
            tips.append("Your outflow is higher than inflow. Consider reducing discretionary spends this month.")
        elif ratio >= 0.9:
            tips.append("Your cashflow is tight (outflow close to inflow). Keep a buffer and avoid big spends.")
        elif ratio <= 0.6:
            tips.append("Good cashflow buffer. Consider setting up an auto-savings plan for long-term goals.")
    if float(current.balance or 0) < 5000:
        tips.append("Balance buffer is low. Maintain at least ₹5,000+ to avoid last-minute stress.")
    if top:
        tips.append(f"Top spend category: {top[0].category}. Set a weekly cap for better control.")

    budgets: dict[str, float] = {}
    savings_goal: dict = {}
    budget_alerts: list[str] = []
    goal_alerts: list[str] = []
    try:
        # Use a short DB session only when needed (preferences are stored).
        db = next(get_db())
        prefs = _load_finance_prefs(db, current.account_number)
        if prefs:
            budgets_raw = _safe_json_obj(prefs.budgets_json, {})
            budgets = {str(k): float(v or 0) for k, v in budgets_raw.items()}
            savings_goal = _safe_json_obj(prefs.goal_json, {})
    except Exception:
        budgets = {}
        savings_goal = {}

    # Budget alerts (compare category spends vs monthly budgets)
    if budgets:
        for c in top:
            b = float(budgets.get(c.category) or 0.0)
            if b > 0 and c.amount > b:
                budget_alerts.append(
                    f"Budget exceeded for {c.category}: spent {_fmt_inr(c.amount)} vs budget {_fmt_inr(b)}."
                )
            elif b > 0 and c.amount >= 0.9 * b:
                budget_alerts.append(
                    f"Near budget limit for {c.category}: spent {_fmt_inr(c.amount)} of {_fmt_inr(b)}."
                )

    # Savings goal alerts (simple: compare positive net vs target)
    try:
        target = float(savings_goal.get("targetAmount") or 0.0) if isinstance(savings_goal, dict) else 0.0
        due = str(savings_goal.get("dueDate") or "").strip() if isinstance(savings_goal, dict) else ""
        if target > 0:
            if net <= 0:
                goal_alerts.append("Savings goal is set, but net cashflow is negative. Try reducing outflow first.")
            else:
                goal_alerts.append(f"Progress toward savings goal: net {_fmt_inr(net)} / target {_fmt_inr(target)}.")
        if due and target > 0:
            goal_alerts.append(f"Savings goal due date: {due}.")
    except Exception:
        pass

    return FinanceCopilotOut(
        accountNumber=current.account_number,
        periodStart=period_start,
        periodEnd=period_end,
        inflow=float(round(inflow, 2)),
        outflow=float(round(outflow, 2)),
        net=float(round(net, 2)),
        topSpends=top,
        tips=tips[:6],
        budgets=budgets,
        budgetAlerts=budget_alerts[:6],
        savingsGoal=savings_goal,
        goalAlerts=goal_alerts[:6],
    )


@app.get("/api/churn/me", response_model=ChurnRiskOut)
def churn_me(current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    txns = _to_transactions(current.transactions_json)
    score, level, reasons, features, tips, last_active = _churn_phase1(
        txns=txns,
        balance_now=float(current.balance or 0.0),
        created_at=current.created_at,
    )
    phase1_score = float(score)
    used_model = False
    prob_churn: float | None = None
    next_best_offer: str | None = None
    expected_retention_lift: float | None = None
    uplift_scores: dict[str, float] = {}
    try:
        model = _load_latest_churn_model(db)
        if model:
            dummy = ChurnSnapshot(
                account_number=current.account_number,
                phase1_score=float(phase1_score),
                score=float(phase1_score),
                level=str(level),
                reasons_json=json.dumps(reasons),
                features_json=json.dumps(features),
            )
            prob, _ = _predict_churn_probability_with_model(model, _churn_features_from_snapshot(dummy))
            prob_churn = float(prob)
            score = _blend_churn_scores(float(phase1_score), float(prob))
            level = _churn_level(float(score))
            reasons = [
                *reasons,
                f"Phase-2 model: P(churn)={prob * 100.0:.1f}% (logistic regression).",
            ]
            used_model = True
    except Exception:
        used_model = False
    try:
        offer_model = _load_latest_churn_offer_model(db)
        if offer_model:
            dummy = ChurnSnapshot(
                account_number=current.account_number,
                phase1_score=float(phase1_score),
                score=float(score),
                level=str(level),
                reasons_json=json.dumps(reasons),
                features_json=json.dumps(features),
            )
            best_offer, best_lift, all_scores = _predict_churn_offer_uplift(
                offer_model, _churn_features_from_snapshot(dummy)
            )
            uplift_scores = {k: float(round(v, 4)) for k, v in all_scores.items()}
            if best_offer and best_lift is not None and best_lift > 0:
                next_best_offer = best_offer
                expected_retention_lift = float(round(best_lift, 4))
                tips = [
                    f"Recommended retention action: {_CHURN_OFFER_LABELS.get(best_offer, best_offer)}.",
                    *tips,
                ]
    except Exception:
        pass
    db.add(
        ChurnSnapshot(
            account_number=current.account_number,
            phase1_score=float(phase1_score),
            score=float(score),
            level=str(level),
            actual_label=None,
            reasons_json=json.dumps(reasons),
            features_json=json.dumps(features),
        )
    )
    db.commit()
    return ChurnRiskOut(
        accountNumber=current.account_number,
        score=float(score),
        level=level,  # type: ignore[arg-type]
        reasons=reasons,
        retentionTips=tips,
        usedPhase2Model=bool(used_model),
        modelChurnProbability=prob_churn,
        nextBestOffer=next_best_offer,
        expectedRetentionLift=expected_retention_lift,
        upliftScores=uplift_scores,
    )


@app.get("/api/admin/churn/high-risk", response_model=list[AdminChurnRiskItem])
def admin_churn_high_risk(
    limit: int = 25,
    level: str = "high",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 200))
    level_norm = (level or "high").strip().lower()
    if level_norm not in {"high", "medium"}:
        level_norm = "high"

    users = db.execute(select(User).where(User.is_admin.is_(False))).scalars().all()
    offer_model = _load_latest_churn_offer_model(db)
    rows: list[AdminChurnRiskItem] = []
    for u in users:
        txns = _to_transactions(u.transactions_json)
        score, lvl, reasons, _features, _tips, last_active = _churn_phase1(
            txns=txns,
            balance_now=float(u.balance or 0.0),
            created_at=u.created_at,
        )
        if lvl != level_norm:
            continue
        next_best_offer: str | None = None
        expected_retention_lift: float | None = None
        if offer_model:
            try:
                dummy = ChurnSnapshot(
                    account_number=u.account_number,
                    phase1_score=float(score),
                    score=float(score),
                    level=str(lvl),
                    reasons_json=json.dumps(reasons),
                    features_json=json.dumps(_features),
                )
                best_offer, best_lift, _scores = _predict_churn_offer_uplift(
                    offer_model, _churn_features_from_snapshot(dummy)
                )
                if best_offer and best_lift is not None and best_lift > 0:
                    next_best_offer = best_offer
                    expected_retention_lift = float(round(best_lift, 4))
            except Exception:
                pass
        rows.append(
            AdminChurnRiskItem(
                accountNumber=u.account_number,
                name=u.name,
                email=u.email,
                phone=u.phone,
                balance=float(u.balance or 0.0),
                score=float(score),
                level=lvl,  # type: ignore[arg-type]
                lastActiveAt=last_active,
                reasons=reasons,
                nextBestOffer=next_best_offer,
                expectedRetentionLift=expected_retention_lift,
            )
        )
    rows.sort(key=lambda r: float(r.score), reverse=True)
    return rows[:limit]


@app.get("/api/admin/churn/snapshots", response_model=list[ChurnSnapshotItem])
def admin_list_churn_snapshots(
    limit: int = 50,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 200))
    snaps = db.execute(
        select(ChurnSnapshot).order_by(ChurnSnapshot.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        ChurnSnapshotItem(
            id=int(s.id),
            accountNumber=s.account_number,
            score=float(s.score or 0),
            level=(s.level or "low"),  # type: ignore[arg-type]
            phase1Score=float(s.phase1_score or 0),
            actualLabel=(s.actual_label if s.actual_label in {"churned", "retained"} else None),
            createdAt=s.created_at,
        )
        for s in snaps
    ]


@app.post("/api/admin/churn/label")
def admin_label_churn_snapshot(
    payload: ChurnLabelIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(select(ChurnSnapshot).where(ChurnSnapshot.id == payload.snapshotId)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Churn snapshot not found.")
    row.actual_label = payload.actualLabel
    db.commit()
    return {"ok": True}


@app.get("/api/admin/churn/model-status", response_model=ChurnModelStatusOut)
def admin_churn_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_churn_model(db)
    if not model:
        return ChurnModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return ChurnModelStatusOut(
        trained=True, trainedAt=model.trained_at, version=int(model.version or 1), samples=samples
    )


@app.post("/api/admin/churn/train", response_model=ChurnTrainOut)
def admin_train_churn_model(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    labeled = db.execute(
        select(ChurnSnapshot)
        .where(ChurnSnapshot.actual_label.is_not(None))
        .order_by(ChurnSnapshot.created_at.desc())
        .limit(5000)
    ).scalars().all()

    if not labeled or len(labeled) < 30:
        return ChurnTrainOut(
            trained=False,
            samples=len(labeled or []),
            churnedCount=sum(_churn_label_to_binary(s.actual_label) for s in labeled or []),
            churnRate=0.0,
            message="Not enough labeled churn snapshots yet. Label at least 30 snapshots (churned/retained) to train.",
        )

    X: list[list[float]] = []
    y: list[int] = []
    for s in labeled:
        X.append(_churn_features_from_snapshot(s))
        y.append(_churn_label_to_binary(s.actual_label))

    samples = len(y)
    n_features = len(_CHURN_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in X) / float(samples)
    stds: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        var = sum((fv[j] - means[j]) ** 2 for fv in X) / float(samples)
        st = math.sqrt(var) if var > 0 else 0.0
        stds[j] = st if st >= 1e-3 else 1.0

    weights, bias = _train_logistic_regression(X=X, y=y, feature_means=means, feature_stds=stds)

    churned_count = sum(y)
    churn_rate = float(churned_count) / float(samples or 1)
    metrics = {"samples": samples, "churnedCount": int(churned_count), "churnRate": churn_rate}

    db.add(
        ChurnModel(
            version=1,
            weights_json=json.dumps({"bias": bias, "weights": weights}),
            feature_means_json=json.dumps(means),
            feature_stds_json=json.dumps(stds),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()

    return ChurnTrainOut(
        trained=True,
        samples=samples,
        churnedCount=int(churned_count),
        churnRate=churn_rate,
        message=f"Churn model trained successfully with {samples} labeled snapshots.",
    )


@app.get("/api/admin/churn/nba/model-status", response_model=ChurnNbaModelStatusOut)
def admin_churn_nba_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_churn_offer_model(db)
    if not model:
        return ChurnNbaModelStatusOut(trained=False, trainedAt=None, version=None, samples=0, offers=_CHURN_OFFERS)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return ChurnNbaModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
        offers=_CHURN_OFFERS,
    )


@app.post("/api/admin/churn/nba/train", response_model=ChurnNbaTrainOut)
def admin_train_churn_nba_model(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    labeled = db.execute(
        select(ChurnSnapshot)
        .where(ChurnSnapshot.actual_label.is_not(None))
        .order_by(ChurnSnapshot.created_at.desc())
        .limit(5000)
    ).scalars().all()

    if not labeled or len(labeled) < 60:
        return ChurnNbaTrainOut(
            trained=False,
            samples=len(labeled or []),
            offers=_CHURN_OFFERS,
            message="Not enough labeled churn snapshots for uplift modeling. Label at least 60 snapshots.",
        )

    X: list[list[float]] = []
    retention_y: list[float] = []
    assigned_offer: list[str] = []
    for s in labeled:
        X.append(_churn_features_from_snapshot(s))
        churned = _churn_label_to_binary(s.actual_label)
        retention_y.append(1.0 - float(churned))
        assigned_offer.append(_offer_assignment_for_snapshot(int(s.id or 0), s.account_number))

    n_features = len(_CHURN_MODEL_FEATURES)
    samples = len(X)
    model_blob: dict[str, dict] = {}
    trained_offers = 0

    for offer in _CHURN_OFFERS:
        t = [1 if o == offer else 0 for o in assigned_offer]
        p = float(sum(t)) / float(samples or 1)
        if p <= 0.03 or p >= 0.97:
            continue
        transformed_y = [
            float(retention_y[i]) * ((t[i] / p) - ((1 - t[i]) / (1.0 - p)))
            for i in range(samples)
        ]
        means = [0.0 for _ in range(n_features)]
        stds = [1.0 for _ in range(n_features)]
        for j in range(n_features):
            means[j] = sum(fv[j] for fv in X) / float(samples)
        for j in range(n_features):
            var = sum((fv[j] - means[j]) ** 2 for fv in X) / float(samples)
            st = math.sqrt(var) if var > 0 else 0.0
            stds[j] = st if st >= 1e-3 else 1.0
        w, b = _train_ridge_regression(
            X,
            transformed_y,
            feature_means=means,
            feature_stds=stds,
            lr=0.02,
            steps=800,
            l2_lambda=0.12,
        )
        model_blob[offer] = {"weights": w, "bias": b, "means": means, "stds": stds, "treatmentRate": p}
        trained_offers += 1

    if trained_offers == 0:
        return ChurnNbaTrainOut(
            trained=False,
            samples=samples,
            offers=_CHURN_OFFERS,
            message="Unable to fit uplift models from current data distribution. Try adding more varied snapshots.",
        )

    metrics = {
        "samples": samples,
        "offersTrained": trained_offers,
        "offers": _CHURN_OFFERS,
    }
    db.add(
        ChurnOfferModel(
            version=1,
            model_json=json.dumps({"offers": model_blob, "features": _CHURN_MODEL_FEATURES}),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()
    return ChurnNbaTrainOut(
        trained=True,
        samples=samples,
        offers=_CHURN_OFFERS,
        message=f"Churn Next-Best-Action uplift model trained with {samples} labeled snapshots.",
    )


@app.get("/api/admin/churn/nba/offer-performance", response_model=list[ChurnNbaOfferPerformanceItem])
def admin_churn_nba_offer_performance(
    limit: int = 400,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    offer_model = _load_latest_churn_offer_model(db)
    if not offer_model:
        return []
    limit = max(50, min(int(limit), 3000))
    snaps = db.execute(
        select(ChurnSnapshot).order_by(ChurnSnapshot.created_at.desc()).limit(limit)
    ).scalars().all()
    if not snaps:
        return []
    agg = {
        k: {"sum": 0.0, "count": 0, "high": 0, "medium": 0, "recommended": 0}
        for k in _CHURN_OFFERS
    }
    for s in snaps:
        fv = _churn_features_from_snapshot(s)
        best_offer, best_lift, all_scores = _predict_churn_offer_uplift(offer_model, fv)
        for offer, score in all_scores.items():
            if offer not in agg:
                continue
            agg[offer]["sum"] += float(score)
            agg[offer]["count"] += 1
            lvl = str(s.level or "").lower()
            if lvl == "high":
                agg[offer]["high"] += 1
            elif lvl == "medium":
                agg[offer]["medium"] += 1
        if best_offer in agg and best_lift is not None and best_lift > 0:
            agg[best_offer]["recommended"] += 1
    out: list[ChurnNbaOfferPerformanceItem] = []
    for offer in _CHURN_OFFERS:
        row = agg[offer]
        cnt = int(row["count"] or 0)
        avg = float(row["sum"]) / float(cnt or 1)
        out.append(
            ChurnNbaOfferPerformanceItem(
                offer=offer,
                avgUplift=float(round(avg, 4)),
                highRiskUsers=int(row["high"] or 0),
                mediumRiskUsers=int(row["medium"] or 0),
                recommendedUsers=int(row["recommended"] or 0),
            )
        )
    out.sort(key=lambda x: (x.avgUplift, x.recommendedUsers), reverse=True)
    return out


def _ensure_default_admin(db: Session):
    # Keep schema in sync for existing databases.
    existing_columns = {
        row[0]
        for row in db.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'users'
                """
            )
        ).all()
    }

    if "gender" not in existing_columns:
        db.execute(text("ALTER TABLE users ADD COLUMN gender VARCHAR(20) NOT NULL DEFAULT ''"))
    if "dob" not in existing_columns:
        db.execute(text("ALTER TABLE users ADD COLUMN dob VARCHAR(30) NOT NULL DEFAULT ''"))
    if "address" not in existing_columns:
        db.execute(text("ALTER TABLE users ADD COLUMN address VARCHAR(255) NOT NULL DEFAULT ''"))
    if "open_account_type" not in existing_columns:
        db.execute(text("ALTER TABLE users ADD COLUMN open_account_type VARCHAR(40) NOT NULL DEFAULT ''"))
    if "card_blocked" not in existing_columns:
        db.execute(text("ALTER TABLE users ADD COLUMN card_blocked BOOLEAN NOT NULL DEFAULT 0"))
    db.commit()

    # One-time migration for loan sanction training label column.
    loan_existing_columns = {
        row[0]
        for row in db.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'loan_applications'
                """
            )
        ).all()
    }
    if "actual_recommendation" not in loan_existing_columns:
        db.execute(
            text("ALTER TABLE loan_applications ADD COLUMN actual_recommendation VARCHAR(30) NULL")
        )
        db.commit()
    if "dob" not in loan_existing_columns:
        db.execute(text("ALTER TABLE loan_applications ADD COLUMN dob VARCHAR(30) NOT NULL DEFAULT ''"))
        db.commit()

    # Fraud alerts table migrations (Phase-2 ML fields).
    fraud_tables = {
        row[0]
        for row in db.execute(
            text(
                """
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                """
            )
        ).all()
    }
    if "fraud_alerts" in fraud_tables:
        fraud_cols = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'fraud_alerts'
                    """
                )
            ).all()
        }
        if "phase1_score" not in fraud_cols:
            db.execute(text("ALTER TABLE fraud_alerts ADD COLUMN phase1_score FLOAT NOT NULL DEFAULT 0"))
            db.commit()
        if "actual_label" not in fraud_cols:
            db.execute(text("ALTER TABLE fraud_alerts ADD COLUMN actual_label VARCHAR(20) NULL"))
            db.commit()

    # Credit risk snapshots migrations (Phase-2 ML fields).
    if "credit_risk_snapshots" in fraud_tables:
        cr_cols = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'credit_risk_snapshots'
                    """
                )
            ).all()
        }
        if "phase1_score" not in cr_cols:
            db.execute(text("ALTER TABLE credit_risk_snapshots ADD COLUMN phase1_score FLOAT NOT NULL DEFAULT 0"))
            db.commit()
        if "actual_label" not in cr_cols:
            db.execute(text("ALTER TABLE credit_risk_snapshots ADD COLUMN actual_label VARCHAR(20) NULL"))
            db.commit()

    # Churn snapshots migrations (Phase-2 ML fields).
    if "churn_snapshots" in fraud_tables:
        churn_cols = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'churn_snapshots'
                    """
                )
            ).all()
        }
        if "phase1_score" not in churn_cols:
            db.execute(text("ALTER TABLE churn_snapshots ADD COLUMN phase1_score FLOAT NOT NULL DEFAULT 0"))
            db.commit()
        if "actual_label" not in churn_cols:
            db.execute(text("ALTER TABLE churn_snapshots ADD COLUMN actual_label VARCHAR(20) NULL"))
            db.commit()

    # Loan Document AI logs migrations (Phase-1.5 review fields).
    if "loan_document_ai_logs" in fraud_tables:
        doc_cols = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT COLUMN_NAME
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'loan_document_ai_logs'
                    """
                )
            ).all()
        }
        if "corrected_document_type" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN corrected_document_type VARCHAR(40) NULL"))
            db.commit()
        if "corrected_monthly_income" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN corrected_monthly_income FLOAT NULL"))
            db.commit()
        if "corrected_emi" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN corrected_emi FLOAT NULL"))
            db.commit()
        if "review_status" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN review_status VARCHAR(30) NOT NULL DEFAULT 'pending'"))
            db.commit()
        if "reviewer_notes" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN reviewer_notes TEXT NOT NULL"))
            db.execute(text("UPDATE loan_document_ai_logs SET reviewer_notes = '' WHERE reviewer_notes IS NULL"))
            db.commit()
        if "reviewed_at" not in doc_cols:
            db.execute(text("ALTER TABLE loan_document_ai_logs ADD COLUMN reviewed_at DATETIME NULL"))
            db.commit()

    # Credit Scorecard model payload can exceed TEXT; enforce LONGTEXT permanently.
    if "credit_scorecard_models" in fraud_tables:
        db.execute(
            text(
                """
                ALTER TABLE credit_scorecard_models
                MODIFY COLUMN model_blob LONGTEXT NOT NULL
                """
            )
        )
        db.commit()

    # Seed product catalog once for AI recommendation phase-1.
    product_count = db.execute(select(func.count(Product.id))).scalar_one()
    if product_count == 0:
        db.add_all(
            [
                Product(
                    name="Secure Health Shield",
                    category="insurance",
                    risk_level="low",
                    min_age=18,
                    max_age=60,
                    min_balance=1000,
                    summary="Base health insurance plan with hospitalization cover.",
                ),
                Product(
                    name="Family Life Protect Plus",
                    category="insurance",
                    risk_level="moderate",
                    min_age=23,
                    max_age=55,
                    min_balance=20000,
                    summary="Term insurance suitable for family protection needs.",
                ),
                Product(
                    name="Wealth ULIP Edge",
                    category="insurance",
                    risk_level="high",
                    min_age=21,
                    max_age=50,
                    min_balance=50000,
                    summary="Insurance + market-linked growth for long-term goals.",
                ),
                Product(
                    name="Conservative Debt Basket",
                    category="investment",
                    risk_level="low",
                    min_age=18,
                    max_age=100,
                    min_balance=1000,
                    summary="Low-volatility debt-oriented investment basket.",
                ),
                Product(
                    name="Balanced Growth Portfolio",
                    category="investment",
                    risk_level="moderate",
                    min_age=21,
                    max_age=100,
                    min_balance=20000,
                    summary="Balanced mix of equity and debt for steady growth.",
                ),
                Product(
                    name="Equity Accelerator Fund",
                    category="investment",
                    risk_level="high",
                    min_age=21,
                    max_age=100,
                    min_balance=50000,
                    summary="High-growth equity-focused portfolio for aggressive investors.",
                ),
            ]
        )
        db.commit()

    # One-time migration for legacy plain-text passwords.
    users = db.execute(select(User)).scalars().all()
    migrated = False
    for u in users:
        if u.password and not _is_bcrypt_hash(u.password):
            u.password = _hash_password(u.password)
            migrated = True
    if migrated:
        db.commit()

    admin = db.execute(select(User).where(User.is_admin.is_(True))).scalar_one_or_none()
    if admin:
        # Never overwrite existing admin credentials at startup.
        if not admin.name:
            admin.name = "Administrator"
        db.commit()
        return

    bootstrap_email = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "admin@localhost").strip()
    bootstrap_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "").strip()
    if APP_ENV in {"production", "prod"} and (not bootstrap_password or len(bootstrap_password) < 12):
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD must be set (>=12 chars) for first admin creation in production.")
    if not bootstrap_password:
        # Development fallback only.
        bootstrap_password = "ChangeMeNow@123"

    db.add(
        User(
            name="Administrator",
            email=bootstrap_email,
            phone="0000000000",
            gender="",
            dob="",
            address="",
            account_number="9999999999",
            balance=0,
            password=_hash_password(bootstrap_password),
            is_admin=True,
            transactions_json="[]",
        )
    )
    db.commit()


@app.on_event("startup")
def startup_seed_admin():
    db = next(get_db())
    try:
        _ensure_default_admin(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/users", response_model=list[UserOut])
def list_users(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    users = db.execute(select(User)).scalars().all()
    return [_to_user_out(u) for u in users]


@app.post("/api/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.isAdmin:
        raise HTTPException(status_code=403, detail="Public signup cannot create admin.")
    existing_email = db.execute(
        select(User).where(func.lower(User.email) == payload.email.lower())
    ).scalar_one_or_none()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    max_acc = db.execute(
        select(func.max(User.account_number)).where(User.is_admin.is_(False))
    ).scalar_one_or_none()
    next_acc = "700010001"
    if max_acc and str(max_acc).isdigit():
        next_acc = str(int(max_acc) + 1)

    txns = []
    initial_deposit = float(payload.initialDeposit or 0)
    if initial_deposit > 0:
        txns.append(
            {
                "id": f"txn_{uuid4().hex}",
                "type": "deposit",
                "amount": initial_deposit,
                "prevBalance": 0,
                "newBalance": initial_deposit,
                "note": "Initial deposit",
                "timestamp": _now_iso(),
            }
        )

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        gender=(payload.gender or "").strip(),
        dob=(payload.dob or "").strip(),
        address=(payload.address or "").strip(),
        open_account_type=(payload.openAccountType or "").strip(),
        account_number="9999999999" if payload.isAdmin else next_acc,
        balance=initial_deposit,
        password=_hash_password(payload.password),
        is_admin=payload.isAdmin,
        transactions_json=json.dumps(txns),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.post("/api/auth/login", response_model=LoginOut)
def check_user(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    ip = _client_ip(request)
    _check_login_rate_limit(identifier, ip)
    phone_normalized = identifier.replace(" ", "")
    candidates = db.execute(select(User)).scalars().all()
    user = next(
        (
            u
            for u in candidates
            if (u.email and u.email.lower().strip() == identifier.lower())
            or u.account_number == identifier
            or (u.phone and u.phone.replace(" ", "") == phone_normalized)
        ),
        None,
    )
    if not user:
        _record_login_failure(identifier, ip)
        raise HTTPException(status_code=404, detail="Account not found.")
    if not _verify_password(payload.password, user.password):
        _record_login_failure(identifier, ip)
        raise HTTPException(status_code=401, detail="Incorrect password.")
    _record_login_success(identifier, ip)
    token = _create_token(user)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=JWT_EXP_MINUTES * 60,
        path="/",
    )
    return LoginOut(accessToken=token, user=_to_user_out(user))


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"ok": True}


def _normalize_phone_digits(value: str) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def _phones_match(stored: str | None, given: str) -> bool:
    a = _normalize_phone_digits(stored or "")
    b = _normalize_phone_digits(given)
    return bool(a and b and a == b)


def _dob_match(stored: str | None, given: str) -> bool:
    s = (stored or "").strip().replace(" ", "")
    g = (given or "").strip().replace(" ", "")
    if not s or not g:
        return False
    return s.lower() == g.lower()


@app.post("/api/auth/recover-email", response_model=PublicRecoverEmailOut)
def public_recover_email(payload: PublicRecoverEmailIn, db: Session = Depends(get_db)):
    """Verify account number + registered phone + date of birth; return registered email (customer accounts only)."""
    acc = (payload.accountNumber or "").strip()
    user = db.execute(select(User).where(User.account_number == acc)).scalar_one_or_none()
    if not user or user.is_admin:
        raise HTTPException(
            status_code=404,
            detail="No matching customer record. Check account number, phone, and date of birth.",
        )
    if not _phones_match(user.phone, payload.phone):
        raise HTTPException(
            status_code=404,
            detail="No matching customer record. Check account number, phone, and date of birth.",
        )
    if not _dob_match(user.dob, payload.dob):
        raise HTTPException(
            status_code=404,
            detail="No matching customer record. Check account number, phone, and date of birth.",
        )
    return PublicRecoverEmailOut(email=user.email or "")


@app.post("/api/auth/forgot-password", response_model=PublicForgotPasswordOut)
def public_forgot_password(payload: PublicForgotPasswordIn, db: Session = Depends(get_db)):
    """Verify account number + registered phone; set new password (customer accounts only)."""
    acc = (payload.accountNumber or "").strip()
    user = db.execute(select(User).where(User.account_number == acc)).scalar_one_or_none()
    if not user or user.is_admin:
        raise HTTPException(
            status_code=404,
            detail="No matching customer record. Check account number and phone.",
        )
    if not _phones_match(user.phone, payload.phone):
        raise HTTPException(
            status_code=404,
            detail="No matching customer record. Check account number and phone.",
        )
    user.password = _hash_password(payload.newPassword)
    db.commit()
    return PublicForgotPasswordOut()


@app.get("/api/users/me", response_model=UserOut)
def get_me(current: User = Depends(_auth_user)):
    return _to_user_out(current)


@app.get("/api/users/by-account/{account_number}", response_model=UserOut)
def get_user_by_account(account_number: str, _: User = Depends(_auth_user), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _to_user_out(user)


@app.get("/api/users/email-exists")
def email_exists(
    email: str,
    excludeAccount: str | None = None,
    _: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    q = select(User).where(func.lower(User.email) == email.lower())
    if excludeAccount:
        q = q.where(User.account_number != excludeAccount)
    existing = db.execute(q).scalar_one_or_none()
    return {"exists": bool(existing)}


@app.put("/api/users/{account_number}", response_model=UserOut)
def update_user(
    account_number: str,
    payload: UserUpdate,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if (not current.is_admin) and current.account_number != account_number:
        raise HTTPException(status_code=403, detail="Not allowed.")

    duplicate = db.execute(
        select(User).where(
            and_(
                func.lower(User.email) == payload.email.lower(),
                User.account_number != account_number,
            )
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=400, detail="Email already used by another account.")

    user.name = payload.name
    user.email = payload.email
    user.phone = payload.phone
    if payload.password:
        user.password = _hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.delete("/api/users/{account_number}")
def remove_user(account_number: str, _: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)
    db.commit()
    return {"ok": True}


@app.post("/api/users/{account_number}/reset-password", response_model=UserOut)
def reset_password(
    account_number: str,
    payload: PasswordResetIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if (not current.is_admin) and current.account_number != account_number:
        raise HTTPException(status_code=403, detail="Not allowed.")
    user.password = _hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.post("/api/users/{account_number}/quick-action", response_model=UserOut)
def quick_action(
    account_number: str,
    payload: QuickActionIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if current.account_number != account_number:
        raise HTTPException(status_code=403, detail="Not allowed.")
    prev = float(user.balance or 0)
    amount = float(payload.amount)
    txns = _to_transactions(user.transactions_json)
    now_utc = datetime.now(timezone.utc)
    if payload.type == "withdraw" and bool(getattr(user, "card_blocked", False)):
        raise HTTPException(
            status_code=403,
            detail="Outgoing transactions are temporarily frozen by Fraud Shield. Please contact admin/support.",
        )

    if payload.type == "withdraw":
        today_withdraw_total = sum(
            float(t.get("amount") or 0)
            for t in txns
            if t.get("type") == "withdraw"
            and _is_same_utc_day(str(t.get("timestamp") or ""), now_utc)
        )
        if today_withdraw_total + amount > DAILY_WITHDRAW_LIMIT:
            remaining = max(0.0, DAILY_WITHDRAW_LIMIT - today_withdraw_total)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Daily withdrawal limit reached. Max {_fmt_inr(DAILY_WITHDRAW_LIMIT)} per day; "
                    f"remaining today {_fmt_inr(remaining)}."
                ),
            )

    if payload.type == "withdraw" and amount > prev:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available {_fmt_inr(prev)}; requested {_fmt_inr(amount)}.",
        )
    new_balance = prev + amount if payload.type == "deposit" else prev - amount
    if payload.type == "withdraw":
        recent_count = _count_recent_outgoing(txns, now_utc, minutes=60)
        phase1_score, _phase1_level, risk_reasons = _fraud_phase1_score(
            tx_type="withdraw",
            amount=amount,
            balance_before=prev,
            now_utc=now_utc,
            recent_outgoing_count=recent_count,
            is_new_beneficiary=False,
        )
        risk_score = float(phase1_score)
        used_model = False
        try:
            model = _load_latest_fraud_model(db)
            if model:
                dummy_alert = FraudAlert(
                    transaction_type="withdraw",
                    amount=float(amount),
                    phase1_score=float(phase1_score),
                    context_json=json.dumps(
                        {
                            "recentOutgoing60m": recent_count,
                            "hourUtc": int(now_utc.hour),
                            "amountToBalanceRatio": (float(amount) / float(prev)) if float(prev) > 0 else 0.0,
                            "dailyOutgoingBeforeRatio": (
                                (float(today_withdraw_total) / float(prev)) if float(prev) > 0 else 0.0
                            ),
                        }
                    ),
                )
                prob, _ = _predict_fraud_probability_with_model(model, _fraud_features_from_alert(dummy_alert))
                risk_score = _blend_fraud_scores(float(phase1_score), float(prob))
                risk_reasons = [
                    *risk_reasons,
                    f"Phase-2 model: P(fraud)={prob * 100.0:.1f}% (logistic regression).",
                ]
                used_model = True
        except Exception:
            used_model = False
        seq_score, seq_reasons = _fraud_sequence_score(txns=txns, now_utc=now_utc, amount=amount, balance_before=prev)
        graph_metrics, graph_score, graph_reasons = _fraud_graph_metrics(
            db=db, now_utc=now_utc, src_account=user.account_number, to_account=None
        )
        risk_score = _blend_fraud_realtime_scores(risk_score, seq_score, graph_score)
        risk_score_base = float(risk_score)
        risk_reasons = [
            *risk_reasons,
            f"Sequence model score={seq_score:.1f} (stream anomaly encoder).",
            *seq_reasons,
            f"Graph model score={graph_score:.1f} (beneficiary network risk).",
            *graph_reasons,
        ]
        used_realtime_model = False
        try:
            rt_model = _load_latest_fraud_realtime_model(db)
            if rt_model:
                dummy_alert_rt = FraudAlert(
                    transaction_type="withdraw",
                    amount=float(amount),
                    phase1_score=float(phase1_score),
                    risk_score=float(risk_score_base),
                    context_json=json.dumps(
                        {
                            "riskScoreBase": float(risk_score_base),
                            "recentOutgoing60m": recent_count,
                            "hourUtc": int(now_utc.hour),
                            "amountToBalanceRatio": (float(amount) / float(prev)) if float(prev) > 0 else 0.0,
                            "dailyOutgoingBeforeRatio": (
                                (float(today_withdraw_total) / float(prev)) if float(prev) > 0 else 0.0
                            ),
                            "sequenceScore": float(seq_score),
                            "graphScore": float(graph_score),
                            "graphMetrics": graph_metrics,
                        }
                    ),
                )
                rt_prob, _ = _predict_fraud_probability_with_realtime_model(
                    rt_model, _fraud_realtime_features_from_alert(dummy_alert_rt)
                )
                risk_score = float(round((0.7 * float(risk_score_base)) + (0.3 * float(rt_prob) * 100.0), 2))
                risk_reasons = [
                    *risk_reasons,
                    f"Phase-2 real-time model: P(fraud)={rt_prob * 100.0:.1f}% (sequence+graph).",
                ]
                used_realtime_model = True
        except Exception:
            used_realtime_model = False
        aml_score = _aml_account_score(_load_latest_aml_graph_model(db), user.account_number)
        if aml_score is not None:
            risk_score = float(round((0.80 * float(risk_score)) + (0.20 * float(aml_score) * 100.0), 2))
            risk_reasons = [
                *risk_reasons,
                f"AML Graph ML score={aml_score * 100.0:.1f}% (account-device-ip-beneficiary network).",
            ]
        risk_level = _fraud_level_from_score(risk_score)
        auto_freeze = _fraud_should_auto_freeze(
            risk_score=float(risk_score),
            sequence_score=float(seq_score),
            graph_score=float(graph_score),
        )
        if auto_freeze:
            user.card_blocked = True
            risk_reasons = [
                *risk_reasons,
                "Phase-1.5 safeguard: account auto-frozen due to severe sequence+graph fraud risk.",
            ]
        _create_fraud_alert_if_needed(
            db=db,
            account_number=user.account_number,
            tx_type="withdraw",
            amount=amount,
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=risk_reasons,
            phase1_score=float(phase1_score),
            status="blocked" if auto_freeze else "open",
            context={
                "dailyWithdrawTotalBefore": today_withdraw_total,
                "recentOutgoing60m": recent_count,
                "hourUtc": int(now_utc.hour),
                "amountToBalanceRatio": (float(amount) / float(prev)) if float(prev) > 0 else 0.0,
                "dailyOutgoingBeforeRatio": ((float(today_withdraw_total) / float(prev)) if float(prev) > 0 else 0.0),
                "usedPhase2Model": bool(used_model),
                "usedRealtimeModel": bool(used_realtime_model),
                "riskScoreBase": float(risk_score_base),
                "sequenceScore": float(seq_score),
                "graphScore": float(graph_score),
                "graphMetrics": graph_metrics,
                "autoFrozen": bool(auto_freeze),
                "amlGraphScore": float(aml_score) if aml_score is not None else None,
                "ipAddress": (str(x_forwarded_for or "").split(",")[0].strip() if x_forwarded_for else ""),
                "deviceId": str(user_agent or "")[:160],
            },
        )
        if auto_freeze:
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=(
                    "Transaction blocked and account temporarily frozen by Fraud Shield (Phase-1.5). "
                    "Please contact admin/support after verification."
                ),
            )
    txns.append(
        {
            "id": f"txn_{uuid4().hex}",
            "type": payload.type,
            "amount": amount,
            "prevBalance": prev,
            "newBalance": new_balance,
            "ipAddress": (str(x_forwarded_for or "").split(",")[0].strip() if x_forwarded_for else ""),
            "deviceId": str(user_agent or "")[:160],
            "userAgent": str(user_agent or "")[:160],
            "timestamp": _now_iso(),
        }
    )
    user.balance = new_balance
    user.transactions_json = json.dumps(txns)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.post("/api/transfers")
def transfer(
    payload: TransferIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
):
    if current.account_number != payload.fromAccount:
        raise HTTPException(status_code=403, detail="Not allowed.")
    sender = db.execute(select(User).where(User.account_number == payload.fromAccount)).scalar_one_or_none()
    receiver = db.execute(select(User).where(User.account_number == payload.toAccount)).scalar_one_or_none()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found.")
    if not receiver or receiver.is_admin:
        raise HTTPException(status_code=404, detail="Recipient account not found.")
    if sender.account_number == receiver.account_number:
        raise HTTPException(status_code=400, detail="You cannot transfer to your own account.")
    if bool(getattr(sender, "card_blocked", False)):
        raise HTTPException(
            status_code=403,
            detail="Outgoing transactions are temporarily frozen by Fraud Shield. Please contact admin/support.",
        )
    amount = float(payload.amount)
    sender_tx = _to_transactions(sender.transactions_json)
    now_utc = datetime.now(timezone.utc)
    today_outgoing_total = sum(
        float(t.get("amount") or 0)
        for t in sender_tx
        if t.get("type") in {"withdraw", "transfer-out"}
        and _is_same_utc_day(str(t.get("timestamp") or ""), now_utc)
    )
    if today_outgoing_total + amount > DAILY_WITHDRAW_LIMIT:
        remaining = max(0.0, DAILY_WITHDRAW_LIMIT - today_outgoing_total)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Daily withdrawal/transfer limit reached. Max {_fmt_inr(DAILY_WITHDRAW_LIMIT)} per day; "
                f"remaining today {_fmt_inr(remaining)}."
            ),
        )
    if float(sender.balance or 0) < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance.")

    recent_count = _count_recent_outgoing(sender_tx, now_utc, minutes=60)
    is_new_beneficiary = not _has_prior_beneficiary(sender_tx, receiver.account_number)
    phase1_score, _phase1_level, risk_reasons = _fraud_phase1_score(
        tx_type="transfer-out",
        amount=amount,
        balance_before=float(sender.balance or 0),
        now_utc=now_utc,
        recent_outgoing_count=recent_count,
        is_new_beneficiary=is_new_beneficiary,
    )
    risk_score = float(phase1_score)
    used_model = False
    try:
        model = _load_latest_fraud_model(db)
        if model:
            prev_bal = float(sender.balance or 0)
            dummy_alert = FraudAlert(
                transaction_type="transfer-out",
                amount=float(amount),
                phase1_score=float(phase1_score),
                context_json=json.dumps(
                    {
                        "recentOutgoing60m": recent_count,
                        "hourUtc": int(now_utc.hour),
                        "newBeneficiary": bool(is_new_beneficiary),
                        "amountToBalanceRatio": (float(amount) / float(prev_bal)) if float(prev_bal) > 0 else 0.0,
                        "dailyOutgoingBeforeRatio": (
                            (float(today_outgoing_total) / float(prev_bal)) if float(prev_bal) > 0 else 0.0
                        ),
                    }
                ),
            )
            prob, _ = _predict_fraud_probability_with_model(model, _fraud_features_from_alert(dummy_alert))
            risk_score = _blend_fraud_scores(float(phase1_score), float(prob))
            risk_reasons = [
                *risk_reasons,
                f"Phase-2 model: P(fraud)={prob * 100.0:.1f}% (logistic regression).",
            ]
            used_model = True
    except Exception:
        used_model = False
    seq_score, seq_reasons = _fraud_sequence_score(
        txns=sender_tx, now_utc=now_utc, amount=amount, balance_before=float(sender.balance or 0)
    )
    graph_metrics, graph_score, graph_reasons = _fraud_graph_metrics(
        db=db,
        now_utc=now_utc,
        src_account=sender.account_number,
        to_account=receiver.account_number,
    )
    risk_score = _blend_fraud_realtime_scores(risk_score, seq_score, graph_score)
    risk_score_base = float(risk_score)
    risk_reasons = [
        *risk_reasons,
        f"Sequence model score={seq_score:.1f} (stream anomaly encoder).",
        *seq_reasons,
        f"Graph model score={graph_score:.1f} (beneficiary network risk).",
        *graph_reasons,
    ]
    used_realtime_model = False
    try:
        rt_model = _load_latest_fraud_realtime_model(db)
        if rt_model:
            prev_bal_rt = float(sender.balance or 0)
            dummy_alert_rt = FraudAlert(
                transaction_type="transfer-out",
                amount=float(amount),
                phase1_score=float(phase1_score),
                risk_score=float(risk_score_base),
                context_json=json.dumps(
                    {
                        "riskScoreBase": float(risk_score_base),
                        "recentOutgoing60m": recent_count,
                        "hourUtc": int(now_utc.hour),
                        "newBeneficiary": bool(is_new_beneficiary),
                        "amountToBalanceRatio": (float(amount) / float(prev_bal_rt)) if float(prev_bal_rt) > 0 else 0.0,
                        "dailyOutgoingBeforeRatio": (
                            (float(today_outgoing_total) / float(prev_bal_rt)) if float(prev_bal_rt) > 0 else 0.0
                        ),
                        "sequenceScore": float(seq_score),
                        "graphScore": float(graph_score),
                        "graphMetrics": graph_metrics,
                    }
                ),
            )
            rt_prob, _ = _predict_fraud_probability_with_realtime_model(
                rt_model, _fraud_realtime_features_from_alert(dummy_alert_rt)
            )
            risk_score = float(round((0.7 * float(risk_score_base)) + (0.3 * float(rt_prob) * 100.0), 2))
            risk_reasons = [
                *risk_reasons,
                f"Phase-2 real-time model: P(fraud)={rt_prob * 100.0:.1f}% (sequence+graph).",
            ]
            used_realtime_model = True
    except Exception:
        used_realtime_model = False
    aml_score = _aml_account_score(_load_latest_aml_graph_model(db), sender.account_number)
    if aml_score is not None:
        risk_score = float(round((0.80 * float(risk_score)) + (0.20 * float(aml_score) * 100.0), 2))
        risk_reasons = [
            *risk_reasons,
            f"AML Graph ML score={aml_score * 100.0:.1f}% (account-device-ip-beneficiary network).",
        ]
    risk_level = _fraud_level_from_score(risk_score)
    auto_freeze = _fraud_should_auto_freeze(
        risk_score=float(risk_score),
        sequence_score=float(seq_score),
        graph_score=float(graph_score),
    )
    if auto_freeze:
        sender.card_blocked = True
        risk_reasons = [
            *risk_reasons,
            "Phase-1.5 safeguard: account auto-frozen due to severe sequence+graph fraud risk.",
        ]
    _create_fraud_alert_if_needed(
        db=db,
        account_number=sender.account_number,
        tx_type="transfer-out",
        amount=amount,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=risk_reasons,
        phase1_score=float(phase1_score),
        status="blocked" if (risk_score >= 85.0 or auto_freeze) else "open",
        context={
            "toAccount": receiver.account_number,
            "dailyOutgoingTotalBefore": today_outgoing_total,
            "recentOutgoing60m": recent_count,
            "newBeneficiary": is_new_beneficiary,
            "hourUtc": int(now_utc.hour),
            "amountToBalanceRatio": (float(amount) / float(sender.balance or 0))
            if float(sender.balance or 0) > 0
            else 0.0,
            "dailyOutgoingBeforeRatio": ((float(today_outgoing_total) / float(sender.balance or 0)) if float(sender.balance or 0) > 0 else 0.0),
            "usedPhase2Model": bool(used_model),
            "usedRealtimeModel": bool(used_realtime_model),
            "riskScoreBase": float(risk_score_base),
            "sequenceScore": float(seq_score),
            "graphScore": float(graph_score),
            "graphMetrics": graph_metrics,
            "autoFrozen": bool(auto_freeze),
            "amlGraphScore": float(aml_score) if aml_score is not None else None,
            "ipAddress": (str(x_forwarded_for or "").split(",")[0].strip() if x_forwarded_for else ""),
            "deviceId": str(user_agent or "")[:160],
        },
    )
    if risk_score >= 85.0 or auto_freeze:
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=(
                "Transfer blocked by Fraud Shield (Phase-1.5). "
                "High-risk pattern detected; please contact support/admin."
            ),
        )
    sender_prev = float(sender.balance or 0)
    receiver_prev = float(receiver.balance or 0)
    sender_new = sender_prev - amount
    receiver_new = receiver_prev + amount
    ts = _now_iso()
    mode = (payload.mode or "IMPS").upper()
    full_note = f"{mode} - {payload.note}" if payload.note else f"{mode} transfer"

    receiver_tx = _to_transactions(receiver.transactions_json)
    sender_tx.append(
        {
            "id": f"txn_{uuid4().hex}",
            "type": "transfer-out",
            "mode": mode,
            "counterpartyAccount": receiver.account_number,
            "counterpartyName": receiver.name,
            "amount": amount,
            "prevBalance": sender_prev,
            "newBalance": sender_new,
            "note": f"To {receiver.account_number} - {receiver.name} | {full_note}",
            "ipAddress": (str(x_forwarded_for or "").split(",")[0].strip() if x_forwarded_for else ""),
            "deviceId": str(user_agent or "")[:160],
            "userAgent": str(user_agent or "")[:160],
            "timestamp": ts,
        }
    )
    receiver_tx.append(
        {
            "id": f"txn_{uuid4().hex}",
            "type": "transfer-in",
            "mode": mode,
            "counterpartyAccount": sender.account_number,
            "counterpartyName": sender.name,
            "amount": amount,
            "prevBalance": receiver_prev,
            "newBalance": receiver_new,
            "note": f"From {sender.account_number} - {sender.name} | {full_note}",
            "ipAddress": (str(x_forwarded_for or "").split(",")[0].strip() if x_forwarded_for else ""),
            "deviceId": str(user_agent or "")[:160],
            "userAgent": str(user_agent or "")[:160],
            "timestamp": ts,
        }
    )

    sender.balance = sender_new
    receiver.balance = receiver_new
    sender.transactions_json = json.dumps(sender_tx)
    receiver.transactions_json = json.dumps(receiver_tx)
    db.commit()
    db.refresh(sender)
    db.refresh(receiver)
    return {"sender": _to_user_out(sender), "recipient": _to_user_out(receiver)}


@app.post("/api/voice/intent", response_model=VoiceIntentOut)
def voice_intent(payload: VoiceIntentIn, current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    transcript = _voice_normalize(payload.transcript)
    intent, conf = _voice_intent_model_predict(transcript)

    if intent == "check_balance":
        challenge_id = uuid4().hex
        _VOICE_CHALLENGES[challenge_id] = {
            "account": current.account_number,
            "intent": "check_balance",
            "transcript": transcript,
            "confidence": conf,
            "verified": True,
            "createdAt": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=2),
        }
        _voice_audit(
            db,
            account_number=current.account_number,
            intent="check_balance",
            transcript=transcript,
            confidence=conf,
            requires_step_up=False,
            status="requested",
            detail={"challengeId": challenge_id},
        )
        db.commit()
        return VoiceIntentOut(
            intent="check_balance",
            confidence=float(round(conf, 4)),
            message="Balance check detected. Press Execute to show your current balance.",
            requiresStepUp=False,
            challengeId=challenge_id,
        )

    if intent in {"transfer", "card_block", "card_unblock"}:
        amount = _voice_extract_amount(transcript) if intent == "transfer" else None
        to_acc = _voice_extract_to_account(transcript) if intent == "transfer" else None
        challenge_id = uuid4().hex
        _VOICE_CHALLENGES[challenge_id] = {
            "account": current.account_number,
            "intent": intent,
            "transcript": transcript,
            "confidence": conf,
            "amount": amount,
            "toAccount": to_acc,
            "verified": False,
            "createdAt": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        _voice_audit(
            db,
            account_number=current.account_number,
            intent=intent,
            transcript=transcript,
            confidence=conf,
            requires_step_up=True,
            status="requested",
            detail={"challengeId": challenge_id, "toAccount": to_acc, "amount": amount},
        )
        db.commit()

        if intent == "transfer":
            msg = "Transfer detected."
            if not amount or not to_acc:
                msg = (
                    "Transfer detected, but I need both amount and recipient account number. "
                    "Example: 'Transfer 5000 to 9988776655'."
                )
            return VoiceIntentOut(
                intent="transfer",
                confidence=float(round(conf, 4)),
                message=msg + " For security, confirm with your password (step-up).",
                requiresStepUp=True,
                challengeId=challenge_id,
                toAccount=to_acc,
                amount=float(amount) if amount else None,
            )
        if intent == "card_block":
            return VoiceIntentOut(
                intent="card_block",
                confidence=float(round(conf, 4)),
                message="Card block request detected. For security, confirm with your password (step-up).",
                requiresStepUp=True,
                challengeId=challenge_id,
            )
        return VoiceIntentOut(
            intent="card_unblock",
            confidence=float(round(conf, 4)),
            message="Card unblock request detected. For security, confirm with your password (step-up).",
            requiresStepUp=True,
            challengeId=challenge_id,
        )

    _voice_audit(
        db,
        account_number=current.account_number,
        intent="unknown",
        transcript=transcript,
        confidence=conf,
        requires_step_up=False,
        status="failed",
        detail={"reason": "unsupported_intent"},
    )
    db.commit()
    return VoiceIntentOut(
        intent="unknown",
        confidence=float(round(conf, 4)),
        message="Sorry, I can only handle: check balance, transfer money, block card, or unblock card.",
        requiresStepUp=False,
    )


@app.post("/api/voice/step-up", response_model=VoiceStepUpOut)
def voice_step_up(payload: VoiceStepUpIn, current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    ch = _VOICE_CHALLENGES.get(payload.challengeId)
    if not ch or ch.get("account") != current.account_number:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    if datetime.now(timezone.utc) > ch.get("expiresAt"):
        _VOICE_CHALLENGES.pop(payload.challengeId, None)
        raise HTTPException(status_code=400, detail="Challenge expired. Try again.")
    if not _verify_password(payload.password, current.password):
        _voice_audit(
            db,
            account_number=current.account_number,
            intent=str(ch.get("intent") or "unknown"),
            transcript=str(ch.get("transcript") or ""),
            confidence=float(ch.get("confidence") or 0.0),
            requires_step_up=True,
            status="failed",
            detail={"reason": "step_up_failed"},
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Step-up verification failed.")
    ch["verified"] = True
    _voice_audit(
        db,
        account_number=current.account_number,
        intent=str(ch.get("intent") or "unknown"),
        transcript=str(ch.get("transcript") or ""),
        confidence=float(ch.get("confidence") or 0.0),
        requires_step_up=True,
        status="verified",
        detail={"challengeId": payload.challengeId},
    )
    db.commit()
    return VoiceStepUpOut(verified=True, message="Step-up verified. You can now execute the voice action.")


@app.get("/api/voice/card-status/me", response_model=VoiceCardStatusOut)
def voice_card_status_me(current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    fresh = db.execute(select(User).where(User.account_number == current.account_number)).scalar_one()
    return VoiceCardStatusOut(cardBlocked=bool(fresh.card_blocked))


@app.post("/api/voice/execute", response_model=VoiceExecuteOut)
def voice_execute(payload: VoiceExecuteIn, current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    ch = _VOICE_CHALLENGES.get(payload.challengeId)
    if not ch or ch.get("account") != current.account_number:
        raise HTTPException(status_code=404, detail="Challenge not found.")
    if datetime.now(timezone.utc) > ch.get("expiresAt"):
        _VOICE_CHALLENGES.pop(payload.challengeId, None)
        raise HTTPException(status_code=400, detail="Challenge expired. Try again.")

    intent = str(ch.get("intent") or "unknown")
    verified = bool(ch.get("verified"))

    if intent == "check_balance":
        _VOICE_CHALLENGES.pop(payload.challengeId, None)
        fresh = db.execute(select(User).where(User.account_number == current.account_number)).scalar_one()
        _voice_audit(
            db,
            account_number=current.account_number,
            intent=intent,
            transcript=str(ch.get("transcript") or ""),
            confidence=float(ch.get("confidence") or 0.0),
            requires_step_up=False,
            status="executed",
            detail={"balanceRead": True},
        )
        db.commit()
        return VoiceExecuteOut(ok=True, message="Your current balance is ready.", balance=float(fresh.balance or 0.0))

    if not verified:
        raise HTTPException(status_code=403, detail="Step-up verification required.")

    if intent == "transfer":
        to_acc = ch.get("toAccount")
        amount = ch.get("amount")
        if not to_acc or not amount:
            raise HTTPException(status_code=400, detail="Missing recipient account or amount.")
        _VOICE_CHALLENGES.pop(payload.challengeId, None)
        transfer(
            TransferIn(
                fromAccount=current.account_number,
                toAccount=str(to_acc),
                amount=float(amount),
                mode="IMPS",
                note="Voice Banking",
            ),
            current=current,
            db=db,
        )
        _voice_audit(
            db,
            account_number=current.account_number,
            intent=intent,
            transcript=str(ch.get("transcript") or ""),
            confidence=float(ch.get("confidence") or 0.0),
            requires_step_up=True,
            status="executed",
            detail={"toAccount": to_acc, "amount": amount},
        )
        db.commit()
        return VoiceExecuteOut(ok=True, message="Transfer executed successfully.")

    if intent in {"card_block", "card_unblock"}:
        _VOICE_CHALLENGES.pop(payload.challengeId, None)
        u = db.execute(select(User).where(User.account_number == current.account_number)).scalar_one()
        u.card_blocked = intent == "card_block"
        _voice_audit(
            db,
            account_number=current.account_number,
            intent=intent,
            transcript=str(ch.get("transcript") or ""),
            confidence=float(ch.get("confidence") or 0.0),
            requires_step_up=True,
            status="executed",
            detail={"cardBlocked": bool(u.card_blocked)},
        )
        db.commit()
        return VoiceExecuteOut(
            ok=True,
            message="Your card is now blocked for safety."
            if intent == "card_block"
            else "Your card is now unblocked and active.",
        )

    raise HTTPException(status_code=400, detail="Unsupported voice action.")


@app.delete("/api/users/{account_number}/transactions/{txn_id}", response_model=UserOut)
def remove_transaction(
    account_number: str,
    txn_id: str,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.account_number == account_number)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if current.account_number != account_number:
        raise HTTPException(status_code=403, detail="Not allowed.")
    txns = [t for t in _to_transactions(user.transactions_json) if t.get("id") != txn_id]
    user.transactions_json = json.dumps(txns)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


def _estimate_emi(principal: float, annual_rate: float, n_months: int) -> float:
    """
    Standard EMI formula (reducing balance loans).
    """
    P = float(principal or 0)
    if P <= 0 or n_months <= 0:
        return 0.0

    r = float(annual_rate or 0) / 12.0 / 100.0
    if r == 0:
        return P / float(n_months)

    pow_term = (1 + r) ** n_months
    return (P * r * pow_term) / (pow_term - 1)


def _interest_apr_for_loan_type(loan_type: str) -> float:
    # Phase-1 rules-based defaults (assumptions for a pre-check).
    lt = (loan_type or "").lower()
    mapping = {
        "personal": 14.0,
        "home": 8.5,
        "vehicle": 10.0,
        "business": 12.0,
    }
    return mapping.get(lt, 12.0)


_LOAN_MODEL_FEATURES = [
    "phase1_sanction_score",
    "dti",
    "estimated_emi",
    "monthly_income",
    "existing_emi_total",
    "credit_score",
    "age_end",
    "secured",
    "ltv",
]


def _sigmoid(x: float) -> float:
    # Numerically stable sigmoid.
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _loan_feature_vector_from_values(
    *,
    phase1_sanction_score: float,
    dti: float,
    estimated_emi: float,
    monthly_income: float,
    existing_emi_total: float,
    credit_score: int | None,
    age_end: float,
    secured: bool,
    ltv: float,
) -> list[float]:
    return [
        float(phase1_sanction_score),
        float(dti),
        float(estimated_emi),
        float(monthly_income),
        float(existing_emi_total),
        float(credit_score if credit_score is not None else 0),
        float(age_end),
        1.0 if secured else 0.0,
        float(ltv),
    ]


def _load_latest_loan_model(db: Session) -> LoanSanctionModel | None:
    return db.execute(
        select(LoanSanctionModel).order_by(LoanSanctionModel.trained_at.desc())
    ).scalars().first()


def _scorecard_require_ml():
    if GradientBoostingClassifier is None:
        raise HTTPException(
            status_code=500,
            detail="Credit Scorecard ML is not available. Install backend requirements (scikit-learn) and restart.",
        )


def _load_latest_credit_scorecard_model(db: Session) -> CreditScorecardModel | None:
    return db.execute(
        select(CreditScorecardModel).order_by(CreditScorecardModel.trained_at.desc())
    ).scalars().first()


def _decode_scorecard_model(model: CreditScorecardModel):
    raw = base64.b64decode((model.model_blob or "").encode("utf-8"))
    try:
        data = zlib.decompress(raw)
    except Exception:
        # Backwards compatibility: uncompressed payloads.
        data = raw
    return pickle.loads(data)


def _scorecard_predict_with_explainability(
    model: CreditScorecardModel,
    feature_vector: list[float],
) -> tuple[float, list[tuple[str, float, float]]]:
    """
    Returns (P(approve), contributions) where contributions are SHAP-style one-feature perturbations.
    """
    clf = _decode_scorecard_model(model)
    means = json.loads(model.feature_means_json or "[]")
    n = min(len(_LOAN_MODEL_FEATURES), len(feature_vector), len(means))
    if n <= 0:
        return 0.5, []
    x = [float(feature_vector[i]) for i in range(n)]
    base_p = float(clf.predict_proba([x])[0][1])
    contributions: list[tuple[str, float, float]] = []
    for i in range(n):
        x_ref = list(x)
        x_ref[i] = float(means[i] or 0.0)
        p_ref = float(clf.predict_proba([x_ref])[0][1])
        impact = base_p - p_ref
        contributions.append((_LOAN_MODEL_FEATURES[i], impact, float(x[i])))
    return base_p, contributions


def _predict_approve_probability_with_model(
    model: LoanSanctionModel,
    feature_vector: list[float],
) -> tuple[float, list[tuple[str, float, float]]]:
    """
    Returns:
      prob_approve in [0,1]
      contributions list of (featureName, contribution, rawValue)
    """
    weights_blob = json.loads(model.weights_json or "{}")
    bias = float(weights_blob.get("bias", 0.0))
    weights = weights_blob.get("weights", [])

    means = json.loads(model.feature_means_json or "[]")
    stds = json.loads(model.feature_stds_json or "[]")

    n = min(
        len(_LOAN_MODEL_FEATURES),
        len(feature_vector),
        len(weights),
        len(means),
        len(stds),
    )
    if n <= 0:
        return 0.5, []

    contributions: list[tuple[str, float, float]] = []
    z = bias
    for i in range(n):
        std = float(stds[i] or 1.0)
        # Avoid exploding standardized features when std is extremely small.
        if std < 1e-6:
            std = 1.0
        x_std = (float(feature_vector[i]) - float(means[i])) / std
        w = float(weights[i])
        z += w * x_std
        contributions.append((_LOAN_MODEL_FEATURES[i], w * x_std, float(feature_vector[i])))

    prob = _sigmoid(z)
    return float(prob), contributions


def _train_logistic_regression(
    X: list[list[float]],
    y: list[int],
    feature_means: list[float],
    feature_stds: list[float],
    lr: float = 0.03,
    steps: int = 900,
    l2_lambda: float = 0.05,
) -> tuple[list[float], float]:
    """
    Train binary logistic regression with L2 regularization (pure Python).
    Returns (weights, bias).
    """
    if not X:
        return [], 0.0
    m = len(X)
    n = len(X[0])
    weights = [0.0 for _ in range(n)]
    bias = 0.0

    for _ in range(steps):
        grad_w = [0.0 for _ in range(n)]
        grad_b = 0.0
        for i in range(m):
            xi = X[i]
            # Standardize sample
            x_std = []
            for j in range(n):
                std = float(feature_stds[j] or 1.0)
                if std < 1e-6:
                    std = 1.0
                val = (float(xi[j]) - float(feature_means[j])) / std
                # Clip standardized features to keep log-odds numerically stable.
                if val > 8:
                    val = 8
                elif val < -8:
                    val = -8
                x_std.append(val)

            z = bias
            for j in range(n):
                z += weights[j] * x_std[j]
            p = _sigmoid(z)
            err = p - float(y[i])  # dL/dz
            grad_b += err
            for j in range(n):
                grad_w[j] += err * x_std[j]

        grad_b /= m
        for j in range(n):
            grad_w[j] = grad_w[j] / m + l2_lambda * float(weights[j])

        bias -= lr * grad_b
        for j in range(n):
            weights[j] -= lr * grad_w[j]

    return weights, bias


@app.post("/api/loan/document-ai/extract", response_model=LoanDocumentExtractOut)
async def loan_document_ai_extract(
    file: UploadFile = File(...),
    statedMonthlyIncome: float | None = None,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    if current.is_admin:
        raise HTTPException(status_code=400, detail="Document AI is for customer accounts only.")
    _row, result = _loan_doc_save_and_extract(
        file=file,
        account_number=current.account_number,
        stated_monthly_income=statedMonthlyIncome,
        db=db,
    )
    db.commit()
    return LoanDocumentExtractOut(**result)


@app.post("/api/loan/document-ai/extract-multi", response_model=LoanDocumentMultiExtractOut)
async def loan_document_ai_extract_multi(
    files: list[UploadFile] = File(...),
    statedMonthlyIncome: float | None = None,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    if current.is_admin:
        raise HTTPException(status_code=400, detail="Document AI is for customer accounts only.")
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one document.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="You can upload up to 5 documents.")

    items: list[dict] = []
    logs: list[LoanDocumentAiLog] = []
    combined_reasons: list[str] = []
    for f in files:
        row, result = _loan_doc_save_and_extract(
            file=f,
            account_number=current.account_number,
            stated_monthly_income=statedMonthlyIncome,
            db=db,
        )
        logs.append(row)
        items.append(result)
        combined_reasons.extend([f"{f.filename or 'document'}: {r}" for r in (result.get("reasons") or [])])

    reconciled_income, reconciled_emi, conf, reconcile_reasons = _loan_doc_reconcile(items)
    verify_status, verify_reasons = _loan_doc_verify_income(statedMonthlyIncome, reconciled_income)
    combined_reasons.extend(reconcile_reasons + verify_reasons)

    # Update logs with final verification status from reconciled result.
    for row in logs:
        row.income_verification_status = verify_status
    db.commit()

    docs_out = [
        LoanDocumentItemOut(
            logId=int(logs[i].id),
            fileName=str(it.get("extractedFields", {}).get("fileName") or logs[i].file_name),
            documentType=str(it.get("documentType") or "unknown"),  # type: ignore[arg-type]
            monthlyIncomeExtracted=it.get("monthlyIncomeExtracted"),
            existingEmiExtracted=it.get("existingEmiExtracted"),
            confidence=float(it.get("confidence") or 0.0),
            rawTextPreview=str(it.get("rawTextPreview") or ""),
        )
        for i, it in enumerate(items)
    ]

    return LoanDocumentMultiExtractOut(
        documents=docs_out,
        reconciledMonthlyIncome=float(reconciled_income) if reconciled_income is not None else None,
        reconciledExistingEmi=float(reconciled_emi) if reconciled_emi is not None else None,
        incomeVerificationStatus=verify_status,  # type: ignore[arg-type]
        confidence=float(conf),
        reasons=combined_reasons[:60],
    )


@app.post("/api/loan/sanction/predict", response_model=LoanSanctionOut)
def loan_sanction_predict(
    payload: LoanSanctionIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    # Phase-1 rules-based pre-check: compute affordability score + recommendation.
    dob_used = (payload.dob or "").strip() or (current.dob or "").strip()
    age = _estimate_age_from_dob(dob_used)

    loan_amount = float(payload.loanAmount)
    tenure_months = int(payload.tenureMonths)
    monthly_income = float(payload.monthlyIncome)
    existing_emi_total = float(payload.existingEmiTotal)
    credit_score = payload.creditScore

    if monthly_income <= 0:
        raise HTTPException(status_code=400, detail="Monthly income must be greater than 0.")

    apr = _interest_apr_for_loan_type(payload.loanType)
    estimated_emi = _estimate_emi(loan_amount, apr, tenure_months)

    dti = (existing_emi_total + estimated_emi) / monthly_income
    dti = round(float(dti), 4)

    reasons: list[str] = []
    used_model = False

    # Affordability score (0-55) from DTI.
    if dti <= 0.3:
        affordability_score = 55.0
        reasons.append(f"DTI {dti} <= 0.30: strong affordability bucket")
    elif dti <= 0.45:
        affordability_score = 35.0
        reasons.append(f"DTI {dti} in 0.30-0.45: moderate affordability bucket")
    elif dti <= 0.6:
        affordability_score = 15.0
        reasons.append(f"DTI {dti} in 0.45-0.60: weak affordability bucket")
    else:
        affordability_score = 0.0
        reasons.append(f"DTI {dti} > 0.60: likely not affordable without changes")

    # Credit score component (0-20).
    credit_score_score = 0.0
    if credit_score is not None:
        credit_score_clamped = max(300, min(850, int(credit_score)))
        credit_score_score = ((credit_score_clamped - 300) / (850 - 300)) * 20.0
        credit_score_score = round(float(credit_score_score), 2)
        reasons.append(f"Credit score input used: {credit_score_clamped}")
    else:
        reasons.append("Credit score not provided: neutral impact used")

    # Age component (0-15): penalty if age at end exceeds 70.
    tenure_years = tenure_months / 12.0
    age_end = age + tenure_years
    age_score = 15.0
    if age_end > 70:
        over = age_end - 70
        age_score = max(0.0, 15.0 - (over * 5.0))
        reasons.append(f"Age-at-end {age_end:.1f} exceeds 70: age penalty applied")
    else:
        reasons.append(f"Age-at-end {age_end:.1f} within 70-year comfort band")
    age_score = round(float(age_score), 2)

    # Collateral/LTV component (0-10) when secured.
    collateral_score = 0.0
    if bool(payload.secured) and payload.collateralValue is not None:
        collateral_value = float(payload.collateralValue)
        if collateral_value > 0:
            ltv = loan_amount / collateral_value
            if ltv <= 0.8:
                collateral_score = 10.0
                reasons.append(f"LTV {ltv:.2f} <= 0.80: collateral strength supports sanction")
            elif ltv <= 0.95:
                collateral_score = 6.0
                reasons.append(f"LTV {ltv:.2f} in 0.80-0.95: moderate collateral strength")
            else:
                collateral_score = 2.0
                reasons.append(f"LTV {ltv:.2f} > 0.95: higher collateral risk")
        else:
            reasons.append("Collateral value <= 0: collateral component ignored")
    else:
        if payload.secured:
            reasons.append("Secured loan selected but collateral value missing: collateral component ignored")
        else:
            reasons.append("Unsecured (or collateral not provided): collateral component ignored")

    sanction_score = round(
        float(affordability_score + credit_score_score + age_score + collateral_score),
        2,
    )

    if dti <= 0.45 and sanction_score >= 65:
        recommendation = "approve"
    elif dti <= 0.6 and sanction_score >= 45:
        recommendation = "manual_review"
    else:
        recommendation = "decline"

    # Phase-2: model-based override if a trained model is available.
    # If not available (no training yet), we keep the Phase-1 rules output.
    try:
        model = _load_latest_loan_model(db)
        if model:
            collateral_value = (
                float(payload.collateralValue)
                if payload.collateralValue is not None
                else None
            )
            ltv = 0.0
            if bool(payload.secured) and collateral_value and collateral_value > 0:
                ltv = loan_amount / collateral_value

            feature_vector = _loan_feature_vector_from_values(
                phase1_sanction_score=float(sanction_score),
                dti=dti,
                estimated_emi=estimated_emi,
                monthly_income=monthly_income,
                existing_emi_total=existing_emi_total,
                credit_score=credit_score,
                age_end=age_end,
                secured=bool(payload.secured),
                ltv=ltv,
            )
            prob, contributions = _predict_approve_probability_with_model(
                model=model,
                feature_vector=feature_vector,
            )

            sanction_score = round(prob * 100.0, 2)
            if prob >= 0.7:
                recommendation = "approve"
            elif prob >= 0.4:
                recommendation = "manual_review"
            else:
                recommendation = "decline"

            # Build reasons from model contributions (top 3 by absolute impact).
            contributions_sorted = sorted(contributions, key=lambda x: abs(x[1]), reverse=True)[:3]
            reasons = [f"Phase-2 model: P(approve)={prob * 100.0:.1f}% using trained logistic regression."]
            for fname, contrib, rawv in contributions_sorted:
                reasons.append(
                    f"Model feature impact: {fname} (value={rawv:.3f}) contribution to log-odds={contrib:.4f}."
                )
            reasons.append("Decision is a statistical estimate; final approval depends on bank underwriting, KYC, and credit bureau checks.")
            used_model = True
    except Exception:
        # Never block prediction; fallback to Phase-1 rules.
        pass

    # Phase-3: Credit Scorecard (Gradient Boosting) with SHAP-style explainability.
    try:
        scorecard = _load_latest_credit_scorecard_model(db)
        if scorecard:
            collateral_value = (
                float(payload.collateralValue)
                if payload.collateralValue is not None
                else None
            )
            ltv = 0.0
            if bool(payload.secured) and collateral_value and collateral_value > 0:
                ltv = loan_amount / collateral_value
            feature_vector = _loan_feature_vector_from_values(
                phase1_sanction_score=float(sanction_score),
                dti=dti,
                estimated_emi=estimated_emi,
                monthly_income=monthly_income,
                existing_emi_total=existing_emi_total,
                credit_score=credit_score,
                age_end=age_end,
                secured=bool(payload.secured),
                ltv=ltv,
            )
            prob_gb, shap_like = _scorecard_predict_with_explainability(
                model=scorecard,
                feature_vector=feature_vector,
            )
            sanction_score = round(prob_gb * 100.0, 2)
            if prob_gb >= 0.7:
                recommendation = "approve"
            elif prob_gb >= 0.4:
                recommendation = "manual_review"
            else:
                recommendation = "decline"
            top_impacts = sorted(shap_like, key=lambda x: abs(x[1]), reverse=True)[:4]
            reasons = [f"Credit Scorecard: P(approve)={prob_gb * 100.0:.1f}% (Gradient Boosting)."]
            for fname, impact, rawv in top_impacts:
                direction = "supports approval" if impact >= 0 else "supports rejection"
                reasons.append(
                    f"SHAP-style impact: {fname} (value={rawv:.3f}) {direction} with contribution {impact:.4f}."
                )
            reasons.append("Scorecard explanation is model-driven; final sanction still depends on underwriting policy and document verification.")
            used_model = True
    except Exception:
        pass

    # Append user-friendly next steps for explainability.
    # Note: when Phase-2 model is used, `reasons` is already overwritten above; when Phase-2
    # is not used, `reasons` still contains Phase-1 drivers.
    try:
        if dti >= 0.6:
            reasons.append(
                "Next steps: DTI is high. Improve affordability by reducing EMI (smaller loan/shorter tenure/lower existing EMIs) or increasing monthly income."
            )
        elif dti >= 0.45:
            reasons.append(
                "Next steps: DTI is borderline. A smaller loan or shorter tenure, or a better credit score, can move you closer to approval."
            )
        else:
            reasons.append(
                "Next steps: Affordability looks comparatively better. Focus on clean documentation and steady cash flows to support underwriting."
            )

        if credit_score is not None:
            cs = int(credit_score)
            if cs < 680:
                reasons.append(
                    f"Credit guidance: credit score {cs} is moderate—reduce utilization, clear dues, and avoid new credit applications before applying."
                )
            elif cs >= 750:
                reasons.append(
                    f"Credit guidance: credit score {cs} is strong—ensure stable income proof and a clear purpose of funds."
                )

        if not bool(payload.secured):
            reasons.append(
                "Secured option: if eligible, secured borrowing (with collateral) may improve underwriting perception compared to unsecured loans."
            )
        else:
            if payload.collateralValue is not None and float(payload.collateralValue) > 0:
                collateral_value = float(payload.collateralValue)
                ltv_now = loan_amount / collateral_value if collateral_value else 0.0
                if ltv_now > 0.95:
                    reasons.append(
                        f"Collateral guidance: LTV is high ({ltv_now:.2f}). Better collateral coverage/negotiation can help."
                    )
    except Exception:
        pass

    db.add(
        LoanApplication(
            account_number=current.account_number,
            dob=dob_used,
            loan_type=payload.loanType,
            loan_amount=loan_amount,
            tenure_months=tenure_months,
            monthly_income=monthly_income,
            existing_emi_total=existing_emi_total,
            credit_score=credit_score,
            secured=bool(payload.secured),
            collateral_value=float(payload.collateralValue) if payload.collateralValue is not None else None,
            estimated_emi=float(estimated_emi),
            dti=float(dti),
            sanction_score=float(sanction_score),
            recommendation=recommendation,
            reasons_json=json.dumps(reasons),
        )
    )
    db.commit()

    return LoanSanctionOut(
        estimatedEmi=float(round(estimated_emi, 2)),
        dti=float(dti),
        sanctionScore=float(sanction_score),
        recommendation=recommendation,
        reasons=reasons,
        disclaimer=(
            "Phase-2 model-based pre-check only (logistic regression). "
            "Actual loan sanction depends on bank underwriting, KYC, credit bureau, documents, and bank policy."
            if used_model
            else "Phase-1 rules-based pre-check only. Actual loan sanction depends on underwriting, KYC, credit bureau, documents, and bank policy."
        ),
    )


def _loan_label_to_binary(actual: str | None) -> int:
    if not actual:
        return 0
    return 1 if str(actual).lower() == "approve" else 0


@app.get("/api/admin/loan/sanction/model-status", response_model=LoanModelStatusOut)
def loan_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_loan_model(db)
    if not model:
        return LoanModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return LoanModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.get("/api/admin/loan/scorecard/model-status", response_model=CreditScorecardModelStatusOut)
def loan_scorecard_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_credit_scorecard_model(db)
    if not model:
        return CreditScorecardModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return CreditScorecardModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.get("/api/admin/loan/sanction-applications", response_model=list[LoanApplicationListItem])
def list_loan_applications(
    limit: int = 20,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 100))
    apps = db.execute(
        select(LoanApplication)
        .order_by(LoanApplication.created_at.desc())
        .limit(limit)
    ).scalars().all()

    # Map with account/created_at fields expected by the UI.
    return [
        LoanApplicationListItem(
            id=int(a.id),
            accountNumber=a.account_number,
            dob=a.dob or "",
            loanType=a.loan_type,
            loanAmount=float(a.loan_amount),
            tenureMonths=int(a.tenure_months),
            monthlyIncome=float(a.monthly_income),
            existingEmiTotal=float(a.existing_emi_total),
            creditScore=int(a.credit_score) if a.credit_score is not None else None,
            secured=bool(a.secured),
            collateralValue=float(a.collateral_value) if a.collateral_value is not None else None,
            estimatedEmi=float(a.estimated_emi),
            dti=float(a.dti),
            sanctionScore=float(a.sanction_score),
            recommendation=a.recommendation,
            actualRecommendation=a.actual_recommendation,
            createdAt=a.created_at,
        )
        for a in apps
    ]


@app.get("/api/admin/loan/scorecard/explain", response_model=LoanScorecardExplainOut)
def explain_loan_scorecard(
    applicationId: int,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    app_row = (
        db.execute(select(LoanApplication).where(LoanApplication.id == int(applicationId)))
        .scalars()
        .first()
    )
    if not app_row:
        raise HTTPException(status_code=404, detail="Loan application not found.")
    model = _load_latest_credit_scorecard_model(db)
    if not model:
        raise HTTPException(status_code=400, detail="Credit scorecard model not trained yet.")
    user = db.execute(select(User).where(User.account_number == app_row.account_number)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Applicant profile not found.")

    dob_used = (app_row.dob or "").strip() or (user.dob or "").strip()
    age = _estimate_age_from_dob(dob_used)
    tenure_years = int(app_row.tenure_months or 0) / 12.0
    age_end = age + tenure_years
    ltv = 0.0
    if bool(app_row.secured) and app_row.collateral_value and float(app_row.collateral_value) > 0:
        ltv = float(app_row.loan_amount) / float(app_row.collateral_value)
    fv = _loan_feature_vector_from_values(
        phase1_sanction_score=float(app_row.sanction_score or 0.0),
        dti=float(app_row.dti or 0.0),
        estimated_emi=float(app_row.estimated_emi or 0.0),
        monthly_income=float(app_row.monthly_income or 0.0),
        existing_emi_total=float(app_row.existing_emi_total or 0.0),
        credit_score=int(app_row.credit_score) if app_row.credit_score is not None else None,
        age_end=float(age_end),
        secured=bool(app_row.secured),
        ltv=float(ltv),
    )
    prob, contribs = _scorecard_predict_with_explainability(model, fv)
    recommendation = "approve" if prob >= 0.7 else ("manual_review" if prob >= 0.4 else "decline")
    top = sorted(contribs, key=lambda x: abs(x[1]), reverse=True)[:5]
    out_top = [
        FeatureContributionItem(feature=f, value=float(v), impact=float(round(i, 6)))
        for f, i, v in top
    ]
    summary = (
        f"Approve probability {prob*100.0:.1f}%. "
        f"Decision: {recommendation}. "
        f"Top drivers computed with SHAP-style feature perturbation."
    )
    return LoanScorecardExplainOut(
        applicationId=int(app_row.id),
        recommendation=recommendation,  # type: ignore[arg-type]
        approveProbability=float(round(prob, 6)),
        rejectProbability=float(round(1.0 - prob, 6)),
        summary=summary,
        topContributions=out_top,
    )


@app.post("/api/admin/loan/sanction/label")
def label_loan_application(
    payload: LoanDecisionLabelIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    app_row = (
        db.execute(select(LoanApplication).where(LoanApplication.id == payload.applicationId))
        .scalars()
        .first()
    )
    if not app_row:
        raise HTTPException(status_code=404, detail="Loan application not found.")
    app_row.actual_recommendation = payload.actualRecommendation
    db.commit()
    return {"ok": True}


@app.post("/api/admin/loan/sanction/train", response_model=LoanTrainOut)
def train_loan_sanction_model(
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    # Gather labeled data.
    labeled_apps = db.execute(
        select(LoanApplication)
        .where(LoanApplication.actual_recommendation.is_not(None))
        .order_by(LoanApplication.created_at.desc())
        .limit(500)
    ).scalars().all()

    if not labeled_apps or len(labeled_apps) < 10:
        return LoanTrainOut(
            trained=False,
            samples=len(labeled_apps or []),
            labeledApproveCount=sum(
                _loan_label_to_binary(a.actual_recommendation) for a in labeled_apps or []
            ),
            approveRate=0.0,
            message="Not enough labeled samples yet. Label at least 10 loan applications to train.",
        )

    # Build feature matrix X and target y (binary approve vs not-approve).
    feature_vectors: list[list[float]] = []
    y: list[int] = []

    for a in labeled_apps:
        user = db.execute(select(User).where(User.account_number == a.account_number)).scalars().first()
        if not user:
            continue
        dob_used = (a.dob or "").strip() or (user.dob or "").strip()
        age = _estimate_age_from_dob(dob_used)
        tenure_months = int(a.tenure_months or 0)
        tenure_years = tenure_months / 12.0
        age_end = age + tenure_years

        ltv = 0.0
        if bool(a.secured) and a.collateral_value and float(a.collateral_value) > 0:
            ltv = float(a.loan_amount) / float(a.collateral_value)

        fv = _loan_feature_vector_from_values(
            phase1_sanction_score=float(a.sanction_score),
            dti=float(a.dti),
            estimated_emi=float(a.estimated_emi),
            monthly_income=float(a.monthly_income),
            existing_emi_total=float(a.existing_emi_total),
            credit_score=int(a.credit_score) if a.credit_score is not None else None,
            age_end=float(age_end),
            secured=bool(a.secured),
            ltv=float(ltv),
        )
        feature_vectors.append(fv)
        y.append(_loan_label_to_binary(a.actual_recommendation))

    samples = len(y)
    if samples < 10:
        return LoanTrainOut(
            trained=False,
            samples=samples,
            labeledApproveCount=sum(y),
            approveRate=float(sum(y)) / float(samples or 1),
            message="Not enough usable rows after joining user profiles.",
        )

    # Standardize features.
    n_features = len(_LOAN_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in feature_vectors) / float(samples)
    stds: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        var = sum((fv[j] - means[j]) ** 2 for fv in feature_vectors) / float(samples)
        st = math.sqrt(var) if var > 0 else 0.0
        # Clamp minimum std to avoid exploding standardized features.
        stds[j] = st if st >= 1e-3 else 1.0

    weights, bias = _train_logistic_regression(
        X=feature_vectors,
        y=y,
        feature_means=means,
        feature_stds=stds,
    )

    labeled_approve = sum(y)
    approve_rate = float(labeled_approve) / float(samples)

    metrics = {
        "samples": samples,
        "labeledApproveCount": int(labeled_approve),
        "approveRate": approve_rate,
    }

    # Persist model.
    db.add(
        LoanSanctionModel(
            version=1,
            weights_json=json.dumps({"bias": bias, "weights": weights}),
            feature_means_json=json.dumps(means),
            feature_stds_json=json.dumps(stds),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()

    return LoanTrainOut(
        trained=True,
        samples=samples,
        labeledApproveCount=int(labeled_approve),
        approveRate=approve_rate,
        message=f"Model trained successfully with {samples} labeled samples.",
    )


@app.post("/api/admin/loan/scorecard/train", response_model=CreditScorecardTrainOut)
def train_loan_credit_scorecard(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    _scorecard_require_ml()
    labeled_apps = db.execute(
        select(LoanApplication)
        .where(LoanApplication.actual_recommendation.is_not(None))
        .order_by(LoanApplication.created_at.desc())
        .limit(5000)
    ).scalars().all()
    if not labeled_apps or len(labeled_apps) < 30:
        return CreditScorecardTrainOut(
            trained=False,
            samples=len(labeled_apps or []),
            approveRate=0.0,
            message="Not enough labeled samples yet. Label at least 30 applications.",
        )
    X: list[list[float]] = []
    y: list[int] = []
    for a in labeled_apps:
        user = db.execute(select(User).where(User.account_number == a.account_number)).scalars().first()
        if not user:
            continue
        dob_used = (a.dob or "").strip() or (user.dob or "").strip()
        age = _estimate_age_from_dob(dob_used)
        tenure_years = int(a.tenure_months or 0) / 12.0
        age_end = age + tenure_years
        ltv = 0.0
        if bool(a.secured) and a.collateral_value and float(a.collateral_value) > 0:
            ltv = float(a.loan_amount) / float(a.collateral_value)
        X.append(
            _loan_feature_vector_from_values(
                phase1_sanction_score=float(a.sanction_score or 0.0),
                dti=float(a.dti or 0.0),
                estimated_emi=float(a.estimated_emi or 0.0),
                monthly_income=float(a.monthly_income or 0.0),
                existing_emi_total=float(a.existing_emi_total or 0.0),
                credit_score=int(a.credit_score) if a.credit_score is not None else None,
                age_end=float(age_end),
                secured=bool(a.secured),
                ltv=float(ltv),
            )
        )
        y.append(_loan_label_to_binary(a.actual_recommendation))
    samples = len(y)
    if samples < 30:
        return CreditScorecardTrainOut(
            trained=False,
            samples=samples,
            approveRate=float(sum(y)) / float(samples or 1),
            message="Not enough usable rows after joins.",
        )
    n_features = len(_LOAN_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in X) / float(samples)
    clf = GradientBoostingClassifier(
        random_state=42,
        n_estimators=180,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
    )
    clf.fit(X, y)
    compressed = zlib.compress(pickle.dumps(clf), level=6)
    payload = base64.b64encode(compressed).decode("utf-8")
    approve_rate = float(sum(y)) / float(samples or 1)
    metrics = {"samples": samples, "approveRate": approve_rate}
    db.add(
        CreditScorecardModel(
            version=1,
            model_blob=payload,
            feature_means_json=json.dumps(means),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()
    return CreditScorecardTrainOut(
        trained=True,
        samples=samples,
        approveRate=approve_rate,
        message=f"Credit scorecard trained successfully with {samples} samples.",
    )


@app.get("/api/admin/fraud-alerts", response_model=list[FraudAlertOut])
def admin_list_fraud_alerts(
    limit: int = 25,
    status: str = "all",
    accountNumber: str = "",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 200))
    q = select(FraudAlert)
    status_norm = (status or "all").strip().lower()
    if status_norm in {"open", "reviewed", "blocked"}:
        q = q.where(FraudAlert.status == status_norm)
    account = (accountNumber or "").strip()
    if account:
        q = q.where(FraudAlert.account_number == account)
    rows = db.execute(q.order_by(FraudAlert.created_at.desc()).limit(limit)).scalars().all()
    return [_to_fraud_alert_out(r) for r in rows]


@app.post("/api/admin/fraud-alerts/status")
def admin_update_fraud_alert_status(
    payload: FraudAlertStatusIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(select(FraudAlert).where(FraudAlert.id == payload.alertId)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Fraud alert not found.")
    row.status = payload.status
    if payload.status == "blocked":
        u = db.execute(select(User).where(User.account_number == row.account_number)).scalar_one_or_none()
        if u and not u.is_admin:
            u.card_blocked = True
    db.commit()
    db.refresh(row)
    return {"ok": True, "alert": _to_fraud_alert_out(row)}


@app.post("/api/admin/fraud-alerts/label")
def admin_label_fraud_alert(
    payload: FraudAlertLabelIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(select(FraudAlert).where(FraudAlert.id == payload.alertId)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Fraud alert not found.")
    row.actual_label = payload.actualLabel
    db.commit()
    db.refresh(row)
    return {"ok": True, "alert": _to_fraud_alert_out(row)}


@app.get("/api/admin/fraud/model-status", response_model=FraudModelStatusOut)
def admin_fraud_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_fraud_model(db)
    if not model:
        return FraudModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return FraudModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.post("/api/admin/fraud/train", response_model=FraudTrainOut)
def admin_train_fraud_model(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    labeled = db.execute(
        select(FraudAlert)
        .where(FraudAlert.actual_label.is_not(None))
        .order_by(FraudAlert.created_at.desc())
        .limit(2000)
    ).scalars().all()

    if not labeled or len(labeled) < 20:
        return FraudTrainOut(
            trained=False,
            samples=len(labeled or []),
            fraudCount=sum(_fraud_label_to_binary(a.actual_label) for a in labeled or []),
            fraudRate=0.0,
            message="Not enough labeled fraud alerts yet. Label at least 20 alerts (fraud/legit) to train.",
        )

    X: list[list[float]] = []
    y: list[int] = []
    for a in labeled:
        X.append(_fraud_features_from_alert(a))
        y.append(_fraud_label_to_binary(a.actual_label))

    samples = len(y)
    if samples < 20:
        return FraudTrainOut(
            trained=False,
            samples=samples,
            fraudCount=sum(y),
            fraudRate=float(sum(y)) / float(samples or 1),
            message="Not enough usable labeled samples.",
        )

    # Standardize features
    n_features = len(_FRAUD_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in X) / float(samples)
    stds: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        var = sum((fv[j] - means[j]) ** 2 for fv in X) / float(samples)
        st = math.sqrt(var) if var > 0 else 0.0
        stds[j] = st if st >= 1e-3 else 1.0

    weights, bias = _train_logistic_regression(X=X, y=y, feature_means=means, feature_stds=stds)

    fraud_count = sum(y)
    fraud_rate = float(fraud_count) / float(samples)
    metrics = {"samples": samples, "fraudCount": int(fraud_count), "fraudRate": fraud_rate}

    db.add(
        FraudRiskModel(
            version=1,
            weights_json=json.dumps({"bias": bias, "weights": weights}),
            feature_means_json=json.dumps(means),
            feature_stds_json=json.dumps(stds),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()

    return FraudTrainOut(
        trained=True,
        samples=samples,
        fraudCount=int(fraud_count),
        fraudRate=fraud_rate,
        message=f"Fraud model trained successfully with {samples} labeled alerts.",
    )


@app.get("/api/admin/fraud/realtime/model-status", response_model=FraudRealtimeModelStatusOut)
def admin_fraud_realtime_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_fraud_realtime_model(db)
    if not model:
        return FraudRealtimeModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return FraudRealtimeModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.post("/api/admin/fraud/realtime/train", response_model=FraudRealtimeTrainOut)
def admin_train_fraud_realtime_model(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    labeled = db.execute(
        select(FraudAlert)
        .where(FraudAlert.actual_label.is_not(None))
        .order_by(FraudAlert.created_at.desc())
        .limit(4000)
    ).scalars().all()

    if not labeled or len(labeled) < 40:
        return FraudRealtimeTrainOut(
            trained=False,
            samples=len(labeled or []),
            fraudCount=sum(_fraud_label_to_binary(a.actual_label) for a in labeled or []),
            fraudRate=0.0,
            message="Not enough labeled fraud alerts yet. Label at least 40 alerts to train realtime model.",
        )

    X: list[list[float]] = []
    y: list[int] = []
    for a in labeled:
        X.append(_fraud_realtime_features_from_alert(a))
        y.append(_fraud_label_to_binary(a.actual_label))

    samples = len(y)
    if samples < 40:
        return FraudRealtimeTrainOut(
            trained=False,
            samples=samples,
            fraudCount=sum(y),
            fraudRate=float(sum(y)) / float(samples or 1),
            message="Not enough usable realtime feature rows.",
        )

    n_features = len(_FRAUD_REALTIME_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in X) / float(samples)
    stds: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        var = sum((fv[j] - means[j]) ** 2 for fv in X) / float(samples)
        st = math.sqrt(var) if var > 0 else 0.0
        stds[j] = st if st >= 1e-3 else 1.0

    weights, bias = _train_logistic_regression(X=X, y=y, feature_means=means, feature_stds=stds)

    fraud_count = sum(y)
    fraud_rate = float(fraud_count) / float(samples)
    metrics = {"samples": samples, "fraudCount": int(fraud_count), "fraudRate": fraud_rate}
    db.add(
        FraudRealtimeModel(
            version=1,
            weights_json=json.dumps({"bias": bias, "weights": weights}),
            feature_means_json=json.dumps(means),
            feature_stds_json=json.dumps(stds),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()
    return FraudRealtimeTrainOut(
        trained=True,
        samples=samples,
        fraudCount=int(fraud_count),
        fraudRate=fraud_rate,
        message=f"Realtime fraud model trained successfully with {samples} labeled alerts.",
    )


@app.get("/api/admin/aml/model-status", response_model=AmlGraphModelStatusOut)
def admin_aml_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_aml_graph_model(db)
    if not model:
        return AmlGraphModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return AmlGraphModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.post("/api/admin/aml/train", response_model=AmlGraphTrainOut)
def admin_aml_train(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    adj, account_nodes = _build_aml_graph(db, lookback_days=90)
    if not adj or not account_nodes:
        return AmlGraphTrainOut(
            trained=False,
            samples=0,
            fraudSeedCount=0,
            message="Not enough graph activity yet (transactions/devices/IPs) to train AML model.",
        )

    seed_scores: dict[str, float] = {}
    fraud_labeled = db.execute(
        select(FraudAlert).where(FraudAlert.actual_label == "fraud").order_by(FraudAlert.created_at.desc()).limit(5000)
    ).scalars().all()
    legit_labeled = db.execute(
        select(FraudAlert).where(FraudAlert.actual_label == "legit").order_by(FraudAlert.created_at.desc()).limit(5000)
    ).scalars().all()
    for a in fraud_labeled:
        seed_scores[f"acc:{a.account_number}"] = max(0.8, seed_scores.get(f"acc:{a.account_number}", 0.0))
    for a in legit_labeled:
        k = f"acc:{a.account_number}"
        seed_scores[k] = min(seed_scores.get(k, 0.0), 0.2) if k in seed_scores else 0.1
    blocked_accounts = db.execute(select(User).where(User.card_blocked.is_(True), User.is_admin.is_(False))).scalars().all()
    for u in blocked_accounts:
        k = f"acc:{u.account_number}"
        seed_scores[k] = max(0.7, seed_scores.get(k, 0.0))

    account_scores = _aml_train_graph_message_passing(adj, account_nodes, seed_scores, iters=4)
    samples = len(account_scores)
    if samples < 10:
        return AmlGraphTrainOut(
            trained=False,
            samples=samples,
            fraudSeedCount=len(fraud_labeled),
            message="Graph has too few account nodes for stable AML training.",
        )

    model_json = {
        "algo": "graph-message-passing-v1",
        "accountScores": account_scores,
    }
    metrics = {
        "samples": samples,
        "fraudSeedCount": len(fraud_labeled),
        "lookbackDays": 90,
    }
    db.add(
        AmlGraphModel(
            version=1,
            model_json=json.dumps(model_json),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()
    return AmlGraphTrainOut(
        trained=True,
        samples=samples,
        fraudSeedCount=len(fraud_labeled),
        message=f"AML Graph ML model trained with {samples} account nodes and {len(fraud_labeled)} fraud seeds.",
    )


@app.get("/api/admin/aml/suspicious-rings", response_model=list[AmlSuspiciousRingItem])
def admin_aml_suspicious_rings(
    limit: int = 20,
    minScore: float = 0.65,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    return _aml_compute_suspicious_rings(db, limit=limit, min_score=minScore)


@app.post("/api/admin/aml/cases/from-ring", response_model=AmlCaseOut)
def admin_aml_case_from_ring(
    payload: AmlCaseCreateFromRingIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    ring_id = str(payload.ringId or "").strip()
    if not ring_id:
        raise HTTPException(status_code=400, detail="ringId is required.")
    existing = db.execute(select(AmlCase).where(AmlCase.ring_id == ring_id)).scalars().first()
    if existing:
        existing.risk_score = float(payload.riskScore or existing.risk_score or 0.0)
        existing.account_count = int(len(payload.accounts or []))
        existing.accounts_json = json.dumps(payload.accounts or [])
        existing.reasons_json = json.dumps(payload.reasons or [])
        existing.priority = _aml_priority_from_score(float(existing.risk_score))
        if str(existing.status or "") == "closed":
            existing.status = "open"
        db.commit()
        db.refresh(existing)
        return _to_aml_case_out(existing)

    row = AmlCase(
        ring_id=ring_id,
        status="open",
        priority=_aml_priority_from_score(float(payload.riskScore or 0.0)),
        watchlist=True if float(payload.riskScore or 0.0) >= 80 else False,
        assignee="",
        risk_score=float(payload.riskScore or 0.0),
        account_count=int(len(payload.accounts or [])),
        accounts_json=json.dumps(payload.accounts or []),
        reasons_json=json.dumps(payload.reasons or []),
        notes="Created from AML suspicious ring.",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_aml_case_out(row)


@app.get("/api/admin/aml/cases", response_model=list[AmlCaseOut])
def admin_aml_cases(
    limit: int = 50,
    status: str = "all",
    priority: str = "all",
    watchlistOnly: bool = False,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 50), 500))
    q = select(AmlCase)
    status_norm = (status or "all").strip().lower()
    if status_norm in {"open", "investigating", "escalated", "closed"}:
        q = q.where(AmlCase.status == status_norm)
    pr_norm = (priority or "all").strip().lower()
    if pr_norm in {"low", "medium", "high", "critical"}:
        q = q.where(AmlCase.priority == pr_norm)
    if bool(watchlistOnly):
        q = q.where(AmlCase.watchlist.is_(True))
    rows = db.execute(q.order_by(AmlCase.updated_at.desc()).limit(limit)).scalars().all()
    return [_to_aml_case_out(r) for r in rows]


@app.post("/api/admin/aml/cases/update", response_model=AmlCaseOut)
def admin_aml_case_update(
    payload: AmlCaseUpdateIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(select(AmlCase).where(AmlCase.id == payload.caseId)).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="AML case not found.")
    if payload.status is not None:
        row.status = str(payload.status)
    if payload.priority is not None:
        row.priority = str(payload.priority)
    if payload.watchlist is not None:
        row.watchlist = bool(payload.watchlist)
    if payload.assignee is not None:
        row.assignee = str(payload.assignee or "")[:120]
    if payload.notes is not None:
        row.notes = str(payload.notes or "")[:2000]
    db.commit()
    db.refresh(row)
    return _to_aml_case_out(row)


@app.post("/api/admin/aml/automation/run", response_model=AmlAutomationRunOut)
def admin_aml_automation_run(
    minScore: float = 0.75,
    autoWatchlistScore: float = 80.0,
    escalateAfterHours: int = 24,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    rings = _aml_compute_suspicious_rings(db, limit=200, min_score=float(minScore or 0.75))
    created = 0
    updated = 0
    now_utc = datetime.now(timezone.utc)
    for r in rings:
        existing = db.execute(select(AmlCase).where(AmlCase.ring_id == r.ringId)).scalars().first()
        if existing:
            existing.risk_score = float(r.riskScore)
            existing.account_count = int(r.accountCount)
            existing.accounts_json = json.dumps(r.accounts or [])
            existing.reasons_json = json.dumps(r.reasons or [])
            existing.priority = _aml_priority_from_score(float(r.riskScore))
            if float(r.riskScore) >= float(autoWatchlistScore or 80.0):
                existing.watchlist = True
            if str(existing.status or "") == "closed" and float(r.riskScore) >= 85.0:
                existing.status = "open"
            updated += 1
        else:
            db.add(
                AmlCase(
                    ring_id=str(r.ringId),
                    status="open",
                    priority=_aml_priority_from_score(float(r.riskScore)),
                    watchlist=True if float(r.riskScore) >= float(autoWatchlistScore or 80.0) else False,
                    assignee="",
                    risk_score=float(r.riskScore),
                    account_count=int(r.accountCount),
                    accounts_json=json.dumps(r.accounts or []),
                    reasons_json=json.dumps(r.reasons or []),
                    notes="Auto-created by AML automation run.",
                )
            )
            created += 1
    db.commit()

    escalated = 0
    stale_threshold = now_utc - timedelta(hours=max(1, int(escalateAfterHours or 24)))
    open_rows = db.execute(
        select(AmlCase).where(AmlCase.status.in_(["open", "investigating"])).order_by(AmlCase.updated_at.asc())
    ).scalars().all()
    for c in open_rows:
        updated_at = c.updated_at.astimezone(timezone.utc) if c.updated_at else now_utc
        if updated_at <= stale_threshold and float(c.risk_score or 0.0) >= 85.0:
            c.status = "escalated"
            c.priority = "critical"
            c.watchlist = True
            escalated += 1
    db.commit()

    return AmlAutomationRunOut(
        processedRings=len(rings),
        createdCases=int(created),
        updatedCases=int(updated),
        escalatedCases=int(escalated),
        message="AML automation completed: rings synced into cases and stale high-risk cases escalated.",
    )


@app.get("/api/admin/aml/cases/alert-links", response_model=list[AmlCaseAlertLinkOut])
def admin_aml_case_alert_links(
    limit: int = 50,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 50), 300))
    rows = db.execute(select(AmlCase).order_by(AmlCase.updated_at.desc()).limit(limit)).scalars().all()
    out: list[AmlCaseAlertLinkOut] = []
    for c in rows:
        try:
            accs = json.loads(c.accounts_json or "[]")
            if not isinstance(accs, list):
                accs = []
        except Exception:
            accs = []
        accs = [str(a) for a in accs if str(a or "").strip()]
        if not accs:
            out.append(
                AmlCaseAlertLinkOut(
                    caseId=int(c.id),
                    ringId=str(c.ring_id or ""),
                    linkedAlerts=0,
                    highRiskAlerts=0,
                    blockedAlerts=0,
                    latestAlertAt=None,
                )
            )
            continue
        alerts = db.execute(
            select(FraudAlert)
            .where(FraudAlert.account_number.in_(accs))
            .order_by(FraudAlert.created_at.desc())
            .limit(500)
        ).scalars().all()
        linked = len(alerts)
        high = sum(1 for a in alerts if str(a.risk_level or "").lower() == "high")
        blocked = sum(1 for a in alerts if str(a.status or "").lower() == "blocked")
        latest_at = alerts[0].created_at if alerts else None
        out.append(
            AmlCaseAlertLinkOut(
                caseId=int(c.id),
                ringId=str(c.ring_id or ""),
                linkedAlerts=int(linked),
                highRiskAlerts=int(high),
                blockedAlerts=int(blocked),
                latestAlertAt=latest_at,
            )
        )
    return out


@app.get("/api/admin/fraud/network-high-risk", response_model=list[AdminFraudNetworkRiskItem])
def admin_fraud_network_high_risk(
    limit: int = 25,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 25), 200))
    now_utc = datetime.now(timezone.utc)
    users = db.execute(select(User).where(User.is_admin.is_(False))).scalars().all()
    out: list[AdminFraudNetworkRiskItem] = []
    for u in users:
        metrics, graph_score, reasons = _fraud_graph_metrics(
            db=db, now_utc=now_utc, src_account=u.account_number, to_account=None
        )
        level = "high" if graph_score >= 70 else ("medium" if graph_score >= 40 else "low")
        if level == "low":
            continue
        out.append(
            AdminFraudNetworkRiskItem(
                accountNumber=u.account_number,
                name=u.name,
                cardBlocked=bool(getattr(u, "card_blocked", False)),
                fanIn30d=int(metrics.get("fanIn30d") or 0),
                fanOut30d=int(metrics.get("fanOut30d") or 0),
                receiverFanIn30d=int(metrics.get("receiverFanIn30d") or 0),
                muleRiskScore=float(graph_score),
                level=level,  # type: ignore[arg-type]
                reasons=reasons[:4],
            )
        )
    out.sort(key=lambda x: float(x.muleRiskScore), reverse=True)
    return out[:limit]


@app.post("/api/admin/fraud/account-action")
def admin_fraud_account_action(
    payload: FraudAccountActionIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    account = (payload.accountNumber or "").strip()
    if not account:
        raise HTTPException(status_code=400, detail="Account number is required.")
    u = db.execute(select(User).where(User.account_number == account)).scalar_one_or_none()
    if not u or u.is_admin:
        raise HTTPException(status_code=404, detail="User account not found.")

    action = str(payload.action or "").strip().lower()
    if action == "freeze":
        u.card_blocked = True
    elif action == "unfreeze":
        u.card_blocked = False
    else:
        raise HTTPException(status_code=400, detail="Invalid action.")

    db.add(
        FraudAlert(
            account_number=u.account_number,
            transaction_type="admin-action",
            amount=0.0,
            phase1_score=0.0,
            risk_score=0.0,
            risk_level="low",
            status="reviewed",
            actual_label="legit",
            reasons_json=json.dumps(
                [
                    f"Admin action: {action} account.",
                    (payload.reason or "").strip() or "No reason provided.",
                ]
            ),
            context_json=json.dumps(
                {
                    "adminAction": action,
                    "reason": (payload.reason or "").strip(),
                }
            ),
        )
    )
    db.commit()
    return {"ok": True, "accountNumber": u.account_number, "cardBlocked": bool(u.card_blocked)}


@app.get("/api/credit-risk/me", response_model=CreditRiskOut)
def credit_risk_me(current: User = Depends(_auth_user), db: Session = Depends(get_db)):
    txns = _to_transactions(current.transactions_json)
    now_utc = datetime.now(timezone.utc)
    period_end = now_utc
    period_start = now_utc - timedelta(days=30)

    score, level, reasons, features, actions = _credit_risk_phase1(
        txns=txns,
        balance_now=float(current.balance or 0.0),
        period_start=period_start,
        period_end=period_end,
    )

    phase1_score = float(score)
    used_model = False
    prob_default: float | None = None
    try:
        model = _load_latest_credit_risk_model(db)
        if model:
            dummy = CreditRiskSnapshot(
                account_number=current.account_number,
                period_start=period_start,
                period_end=period_end,
                phase1_score=float(phase1_score),
                score=float(phase1_score),
                level=str(level),
                reasons_json=json.dumps(reasons),
                features_json=json.dumps(features),
            )
            prob, _ = _predict_default_probability_with_model(model, _credit_features_from_snapshot(dummy))
            prob_default = float(prob)
            score = _blend_credit_scores(float(phase1_score), float(prob))
            level = _credit_risk_level(float(score))
            reasons = [
                *reasons,
                f"Phase-2 model: P(default)={prob * 100.0:.1f}% (logistic regression).",
            ]
            used_model = True
    except Exception:
        used_model = False

    db.add(
        CreditRiskSnapshot(
            account_number=current.account_number,
            period_start=period_start,
            period_end=period_end,
            phase1_score=float(phase1_score),
            score=float(score),
            level=str(level),
            actual_label=None,
            reasons_json=json.dumps(reasons),
            features_json=json.dumps(features),
        )
    )
    db.commit()

    return CreditRiskOut(
        accountNumber=current.account_number,
        periodStart=period_start,
        periodEnd=period_end,
        score=float(score),
        level=level,  # type: ignore[arg-type]
        reasons=reasons,
        recommendedActions=actions,
        usedPhase2Model=bool(used_model),
        modelDefaultProbability=prob_default,
    )


@app.get("/api/admin/credit-risk/high-risk", response_model=list[AdminCreditRiskItem])
def admin_credit_risk_high_risk(
    limit: int = 25,
    level: str = "high",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 200))
    level_norm = (level or "high").strip().lower()
    if level_norm not in {"high", "medium"}:
        level_norm = "high"

    users = db.execute(select(User).where(User.is_admin.is_(False))).scalars().all()
    rows: list[AdminCreditRiskItem] = []
    now_utc = datetime.now(timezone.utc)
    period_end = now_utc
    period_start = now_utc - timedelta(days=30)

    for u in users:
        txns = _to_transactions(u.transactions_json)
        score, lvl, reasons, _features, _actions = _credit_risk_phase1(
            txns=txns,
            balance_now=float(u.balance or 0.0),
            period_start=period_start,
            period_end=period_end,
        )
        if lvl != level_norm:
            continue
        rows.append(
            AdminCreditRiskItem(
                accountNumber=u.account_number,
                name=u.name,
                email=u.email,
                phone=u.phone,
                balance=float(u.balance or 0.0),
                score=float(score),
                level=lvl,  # type: ignore[arg-type]
                periodEnd=period_end,
                reasons=reasons,
            )
        )

    rows.sort(key=lambda r: float(r.score), reverse=True)
    return rows[:limit]


@app.get("/api/admin/credit-risk/snapshots", response_model=list[CreditRiskSnapshotItem])
def admin_list_credit_risk_snapshots(
    limit: int = 50,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit), 200))
    snaps = db.execute(
        select(CreditRiskSnapshot).order_by(CreditRiskSnapshot.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        CreditRiskSnapshotItem(
            id=int(s.id),
            accountNumber=s.account_number,
            score=float(s.score or 0),
            level=(s.level or "low"),  # type: ignore[arg-type]
            phase1Score=float(s.phase1_score or 0),
            actualLabel=(s.actual_label if s.actual_label in {"defaulted", "on_time"} else None),
            periodEnd=s.period_end,
        )
        for s in snaps
    ]


@app.post("/api/admin/credit-risk/label")
def admin_label_credit_risk_snapshot(
    payload: CreditRiskLabelIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.execute(select(CreditRiskSnapshot).where(CreditRiskSnapshot.id == payload.snapshotId))
        .scalars()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Credit risk snapshot not found.")
    row.actual_label = payload.actualLabel
    db.commit()
    return {"ok": True}


@app.get("/api/admin/credit-risk/model-status", response_model=CreditRiskModelStatusOut)
def admin_credit_risk_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_credit_risk_model(db)
    if not model:
        return CreditRiskModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return CreditRiskModelStatusOut(
        trained=True, trainedAt=model.trained_at, version=int(model.version or 1), samples=samples
    )


@app.post("/api/admin/credit-risk/train", response_model=CreditRiskTrainOut)
def admin_train_credit_risk_model(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    labeled = db.execute(
        select(CreditRiskSnapshot)
        .where(CreditRiskSnapshot.actual_label.is_not(None))
        .order_by(CreditRiskSnapshot.created_at.desc())
        .limit(5000)
    ).scalars().all()

    if not labeled or len(labeled) < 30:
        return CreditRiskTrainOut(
            trained=False,
            samples=len(labeled or []),
            defaultedCount=sum(_credit_label_to_binary(s.actual_label) for s in labeled or []),
            defaultRate=0.0,
            message="Not enough labeled snapshots yet. Label at least 30 snapshots (defaulted/on_time) to train.",
        )

    X: list[list[float]] = []
    y: list[int] = []
    for s in labeled:
        X.append(_credit_features_from_snapshot(s))
        y.append(_credit_label_to_binary(s.actual_label))

    samples = len(y)
    n_features = len(_CREDIT_RISK_MODEL_FEATURES)
    means: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        means[j] = sum(fv[j] for fv in X) / float(samples)
    stds: list[float] = [0.0 for _ in range(n_features)]
    for j in range(n_features):
        var = sum((fv[j] - means[j]) ** 2 for fv in X) / float(samples)
        st = math.sqrt(var) if var > 0 else 0.0
        stds[j] = st if st >= 1e-3 else 1.0

    weights, bias = _train_logistic_regression(X=X, y=y, feature_means=means, feature_stds=stds)

    defaulted_count = sum(y)
    default_rate = float(defaulted_count) / float(samples or 1)
    metrics = {"samples": samples, "defaultedCount": int(defaulted_count), "defaultRate": default_rate}

    db.add(
        CreditRiskModel(
            version=1,
            weights_json=json.dumps({"bias": bias, "weights": weights}),
            feature_means_json=json.dumps(means),
            feature_stds_json=json.dumps(stds),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()

    return CreditRiskTrainOut(
        trained=True,
        samples=samples,
        defaultedCount=int(defaulted_count),
        defaultRate=default_rate,
        message=f"Credit risk model trained successfully with {samples} labeled snapshots.",
    )


@app.get("/api/admin/fraud-alerts/summary", response_model=FraudAlertSummaryOut)
def admin_fraud_alert_summary(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    total = int(db.execute(select(func.count(FraudAlert.id))).scalar() or 0)
    open_count = int(
        db.execute(select(func.count(FraudAlert.id)).where(FraudAlert.status == "open")).scalar()
        or 0
    )
    high = int(
        db.execute(select(func.count(FraudAlert.id)).where(FraudAlert.risk_level == "high")).scalar()
        or 0
    )
    blocked = int(
        db.execute(select(func.count(FraudAlert.id)).where(FraudAlert.status == "blocked")).scalar()
        or 0
    )
    return FraudAlertSummaryOut(total=total, open=open_count, high=high, blocked=blocked)


@app.post("/api/ai/recommendations", response_model=AiRecommendOut)
def ai_recommendations(
    payload: AiRecommendIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    user_age = _estimate_age_from_dob(current.dob)
    risk = (payload.riskLevel or "moderate").lower()
    goal = (payload.goal or "").strip().lower()
    balance = float(current.balance or 0)

    products = db.execute(select(Product).where(Product.active.is_(True))).scalars().all()
    # Phase-2: learning signals from global and user-specific feedback.
    global_feedback_rows = db.execute(
        select(
            RecommendationFeedback.product_id,
            func.sum(case((RecommendationFeedback.action == "accepted", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "saved", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "rejected", 1), else_=0)),
        ).group_by(RecommendationFeedback.product_id)
    ).all()
    global_feedback = {
        int(r[0]): {
            "accepted": int(r[1] or 0),
            "saved": int(r[2] or 0),
            "rejected": int(r[3] or 0),
        }
        for r in global_feedback_rows
    }

    user_feedback_rows = db.execute(
        select(
            RecommendationFeedback.product_id,
            func.sum(case((RecommendationFeedback.action == "accepted", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "saved", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "rejected", 1), else_=0)),
        )
        .where(RecommendationFeedback.account_number == current.account_number)
        .group_by(RecommendationFeedback.product_id)
    ).all()
    user_feedback = {
        int(r[0]): {
            "accepted": int(r[1] or 0),
            "saved": int(r[2] or 0),
            "rejected": int(r[3] or 0),
        }
        for r in user_feedback_rows
    }

    suggestions: list[ProductSuggestion] = []
    for p in products:
        if not (p.min_age <= user_age <= p.max_age):
            continue
        if balance < float(p.min_balance or 0):
            continue

        score = 50.0
        reasons: list[str] = []
        if p.risk_level == risk:
            score += 25.0
            reasons.append("Risk match")
        elif (risk, p.risk_level) in {("moderate", "low"), ("moderate", "high")}:
            score += 10.0
            reasons.append("Close risk match")
        else:
            score -= 10.0

        if goal:
            if "retire" in goal and "growth" in p.name.lower():
                score += 8.0
                reasons.append("Goal: retirement")
            if "tax" in goal and p.category == "insurance":
                score += 6.0
                reasons.append("Goal: tax saving")
            if "wealth" in goal and p.category == "investment":
                score += 8.0
                reasons.append("Goal: wealth creation")

        # Global feedback signal (bounded to avoid overfitting early data).
        gf = global_feedback.get(int(p.id), {"accepted": 0, "saved": 0, "rejected": 0})
        global_weighted = (gf["accepted"] * 2.0) + (gf["saved"] * 1.0) - (gf["rejected"] * 1.5)
        global_adjustment = 12.0 * math.tanh(global_weighted / 10.0)
        score += global_adjustment
        if global_adjustment > 2:
            reasons.append("Popular with similar users")
        elif global_adjustment < -2:
            reasons.append("Lower recent interest")

        # User-personalized feedback signal.
        uf = user_feedback.get(int(p.id), {"accepted": 0, "saved": 0, "rejected": 0})
        personal_adjustment = (uf["accepted"] * 7.0) + (uf["saved"] * 3.0) - (uf["rejected"] * 8.0)
        score += personal_adjustment
        if uf["accepted"] > 0:
            reasons.append("You showed interest before")
        if uf["rejected"] > 0:
            reasons.append("You marked similar offer as not relevant")

        # Light exploration bonus for low-feedback products.
        total_feedback = gf["accepted"] + gf["saved"] + gf["rejected"]
        if total_feedback < 3:
            score += 1.5

        reason = (
            f"Matches {risk} profile, age {user_age}, and balance eligibility."
            + (f" Signals: {', '.join(reasons[:3])}." if reasons else "")
        )
        suggestions.append(
            ProductSuggestion(
                productId=p.id,
                name=p.name,
                category=p.category,
                score=round(score, 2),
                reason=reason,
                summary=p.summary,
            )
        )

    insurance = sorted(
        [s for s in suggestions if s.category == "insurance"],
        key=lambda x: x.score,
        reverse=True,
    )[:3]
    investment = sorted(
        [s for s in suggestions if s.category == "investment"],
        key=lambda x: x.score,
        reverse=True,
    )[:3]

    return AiRecommendOut(
        riskProfile=risk,
        insurance=insurance,
        investment=investment,
        disclaimer="AI-based suggestions for guidance only; this is not financial advice.",
    )


def _ai_chat_templates(message: str) -> dict[str, bool]:
    return {
        "compare": any(
            phrase in message
            for phrase in (
                "compare",
                "comparison",
                "difference",
                "different",
                "versus",
                " vs ",
                "which is better",
                "better between",
                "or should i",
                "which one",
            )
        ),
        "benefits": any(
            phrase in message
            for phrase in (
                "benefit",
                "advantage",
                "advantages",
                "feature",
                "features",
                "what does it offer",
                "what do i get",
                "explain the",
                "tell me about",
            )
        ),
        "eligibility": any(
            phrase in message
            for phrase in (
                "eligible",
                "eligibility",
                "qualify",
                "qualification",
                "minimum balance",
                "requirements",
                "requirement",
                "can i get",
                "am i eligible",
                "do i qualify",
            )
        ),
    }


def _pick_compare_pair(
    insurance_items: list,
    investment_items: list,
    top_matches: list,
    asks_insurance: bool,
    asks_investment: bool,
):
    if asks_insurance and not asks_investment and len(insurance_items) >= 2:
        return insurance_items[0], insurance_items[1]
    if asks_investment and not asks_insurance and len(investment_items) >= 2:
        return investment_items[0], investment_items[1]
    if len(top_matches) >= 2:
        return top_matches[0], top_matches[1]
    if insurance_items and investment_items:
        return insurance_items[0], investment_items[0]
    return None


def _ai_chat_reply_compare(
    message: str,
    insurance_items: list,
    investment_items: list,
    top_matches: list,
    asks_insurance: bool,
    asks_investment: bool,
) -> str | None:
    if not _ai_chat_templates(message)["compare"]:
        return None
    pair = _pick_compare_pair(
        insurance_items, investment_items, top_matches, asks_insurance, asks_investment
    )
    if not pair:
        return (
            "To compare products, mention insurance or investment—or ask again after "
            "refreshing recommendations so at least two options appear."
        )
    a, b = pair
    stronger = a if a.score >= b.score else b
    weaker = b if stronger is a else a
    return (
        f"Compare — '{a.name}' (model {a.score}) vs '{b.name}' (model {b.score}). "
        f"Positioning: '{a.name}' — {a.summary}; '{b.name}' — {b.summary}. "
        f"Relative fit: '{stronger.name}' ranks ahead for your stated goal/risk and feedback-weighted scoring "
        f"versus '{weaker.name}'. Before deciding, map charges, lock-in, and liquidity to your cash-flow plan."
    )


def _ai_chat_reply_benefits(
    message: str,
    top_matches: list,
    insurance_items: list,
    investment_items: list,
    asks_insurance: bool,
    asks_investment: bool,
) -> str | None:
    if not _ai_chat_templates(message)["benefits"]:
        return None
    p = None
    if asks_insurance and insurance_items:
        p = insurance_items[0]
    elif asks_investment and investment_items:
        p = investment_items[0]
    elif top_matches:
        p = top_matches[0]
    elif insurance_items:
        p = insurance_items[0]
    elif investment_items:
        p = investment_items[0]
    if not p:
        return None
    return (
        f"Benefits & fit — '{p.name}' ({p.category}): {p.summary} "
        f"Engine rationale: {p.reason} "
        "Validate benefits, exclusions, and illustrations against the official product literature."
    )


def _ai_chat_reply_eligibility(
    db: Session,
    message: str,
    top_matches: list,
    insurance_items: list,
    investment_items: list,
    asks_insurance: bool,
    asks_investment: bool,
    age: int,
    balance: float,
) -> str | None:
    if not _ai_chat_templates(message)["eligibility"]:
        return None
    p = None
    if asks_insurance and insurance_items:
        p = insurance_items[0]
    elif asks_investment and investment_items:
        p = investment_items[0]
    elif top_matches:
        p = top_matches[0]
    elif insurance_items:
        p = insurance_items[0]
    elif investment_items:
        p = investment_items[0]
    if not p:
        return "Eligibility — No product matched your profile in this session."
    row = db.execute(select(Product).where(Product.id == p.productId)).scalar_one_or_none()
    if not row:
        return (
            f"Eligibility — '{p.name}': {p.reason} "
            "(Exact rules: confirm with branch or advisor.)"
        )
    ok_age = row.min_age <= age <= row.max_age
    ok_bal = balance >= float(row.min_balance or 0)
    status = (
        "You appear within typical age and balance rules for this catalog item."
        if (ok_age and ok_bal)
        else "You may fall outside typical age or minimum balance for this catalog sample—verify with the bank."
    )
    return (
        f"Eligibility — '{p.name}' ({p.category}): catalogue sample rules show ages {row.min_age}-{row.max_age}, "
        f"minimum balance {_fmt_inr(float(row.min_balance))}. "
        f"Your profile: age {age}, balance {_fmt_inr(balance)}. {status} "
        "Final underwriting/KYC may impose additional conditions."
    )


def _goal_display_name(goal_key: str) -> str:
    key = (goal_key or "").strip().lower().replace(" ", "-")
    mapping = {
        "wealth-creation": "Wealth creation",
        "retirement-planning": "Retirement / long-horizon accumulation",
        "tax-saving": "Tax-efficient planning",
        "family-protection": "Family protection",
    }
    if key in mapping:
        return mapping[key]
    return (goal_key or "General objective").replace("-", " ").title()


def _goal_expert_note(goal_key: str, risk: str) -> str:
    g = (goal_key or "").lower()
    if "retire" in g:
        return (
            "Retirement outcomes improve with an early, steady savings rate, periodic rebalancing, "
            "and gradually de-risking as the target date approaches."
        )
    if "tax" in g:
        return (
            "Tax-led choices should respect lock-ins and section limits each financial year; "
            "liquidity needs must sit alongside deductions (e.g. 80C/80D-style considerations)."
        )
    if "family" in g or "protect" in g:
        return (
            "Protection planning usually starts with adequate pure risk cover and contingencies "
            "before allocating to market-linked wealth products."
        )
    if "wealth" in g:
        return (
            "Growth-oriented paths assume a longer horizon and tolerance for interim volatility; "
            f"keep the sleeve consistent with your stated '{risk}' preference."
        )
    return (
        f"Align product liquidity and tenor with a '{risk}' risk stance and document the purpose "
        "of each allocation."
    )


def _product_expert_one_liner(db: Session, item: ProductSuggestion) -> str:
    row = db.execute(select(Product).where(Product.id == item.productId)).scalar_one_or_none()
    if not row:
        return (
            f"{item.name} ({item.category}) — model score {item.score}. {item.summary} "
            f"Rationale: {item.reason}"
        )
    return (
        f"{item.name} ({item.category}, catalog risk: {row.risk_level}) — score {item.score}. "
        f"Typical parameters: ages {row.min_age}-{row.max_age}, "
        f"minimum balance {_fmt_inr(float(row.min_balance))}. "
        f"Positioning: {item.summary} Engine notes: {item.reason}"
    )


def _ai_expert_finalize(
    core_reply: str,
    *,
    db: Session,
    rec: AiRecommendOut,
    insurance_items: list,
    investment_items: list,
    age: int,
    balance: float,
    goal_key: str,
    include_catalog: bool = True,
) -> str:
    """Wrap core chat logic in an institutional-style brief (still non-binding guidance)."""
    goal_line = _goal_display_name(goal_key)
    context_note = _goal_expert_note(goal_key, rec.riskProfile)
    brief = (
        f"【Advisor brief】\n"
        f"Stated goal: {goal_line}. Risk preference: {rec.riskProfile}. "
        f"Estimated age (from DOB if captured): {age}. Available balance: {_fmt_inr(balance)}.\n"
        f"Context: {context_note}\n"
    )
    answer = f"【Answer】\n{core_reply.strip()}\n"

    positioning = ""
    shortlist = ""
    if include_catalog:
        detail_items = list(insurance_items[:2]) + list(investment_items[:2])
        if detail_items:
            positioning = "【Top picks — catalog detail】\n" + "\n".join(
                f"• {_product_expert_one_liner(db, item)}" for item in detail_items
            )
            positioning += "\n"
        else:
            positioning = (
                "【Top picks — catalog detail】\n"
                "• No eligible catalogue items for this profile under current age/balance filters.\n"
            )

        ins_rank = ", ".join(f"{p.name} ({p.score})" for p in insurance_items) or "—"
        inv_rank = ", ".join(f"{p.name} ({p.score})" for p in investment_items) or "—"
        shortlist = (
            f"【Shortlist (model scores)】\n"
            f"Insurance: {ins_rank}\n"
            f"Investment: {inv_rank}\n"
        )
    caveats = (
        "【Caveats & next steps】\n"
        "• Educational, rules-based guidance only—not an offer, solicitation, or regulated investment/insurance advice.\n"
        "• Insist on official illustrations, scheme documents, and KIM/factsheets; underwriting and pricing vary by case.\n"
        "• Stress-test premiums/SIPs vs cash flow; retain an emergency buffer before illiquid or long lock-in commitments.\n"
        "• Escalate to your relationship manager; add a qualified tax practitioner where 80C/80D/LTCG or exemptions matter.\n"
    )
    return f"{brief}\n{answer}\n{positioning}\n{shortlist}\n{caveats}"


def _ai_chat_reply_risk_enriched(
    db: Session,
    message: str,
    rec,
    insurance_items: list,
    investment_items: list,
) -> str | None:
    risk_triggers = (
        "risk",
        "safe",
        "safety",
        "aggressive",
        "conservative",
        "volatile",
        "volatility",
        "loss",
        "downside",
    )
    if not any(t in message for t in risk_triggers):
        return None
    parts = [
        f"Risk framing — Your selected preference is '{rec.riskProfile}'. "
        "Low emphasis: capital preservation; moderate: balance of growth and drawdown control; "
        "high: return seeking with higher path volatility."
    ]
    for item in (insurance_items[:1] + investment_items[:1]):
        row = db.execute(select(Product).where(Product.id == item.productId)).scalar_one_or_none()
        label = row.risk_level if row else "see catalog"
        parts.append(
            f"Catalogue tag for '{item.name}': {label} risk—pair this with your horizon and capacity for loss."
        )
    return " ".join(parts)


def _ai_detect_health_topic(message: str) -> str | None:
    """
    Template+KB intent detector for insurance/health topics.
    This is intentionally keyword-based (no external model calls).
    """
    msg = (message or "").lower()

    if any(k in msg for k in ["coverage", "benefits", "included", "what is covered", "cover", "includes"]):
        return "coverage_benefits"
    if any(k in msg for k in ["premium", "cost", "price", "expense", "how much", "expensive", "afford"]):
        return "premium_cost"
    if any(k in msg for k in ["claim", "cashless", "reimbursement", "settlement", "hospitalization"]):
        return "claim_process"
    if any(k in msg for k in ["network", "hospital", "access", "cashless network", "nearby", "coverage area"]):
        return "network_accessibility"
    if any(k in msg for k in ["sum insured", "coverage amount", "limit", "how much cover", "maximum cover"]):
        return "sum_insured"
    if any(
        k in msg
        for k in [
            "waiting period",
            "waiting",
            "pre-existing",
            "pre existing",
            "maternity",
            "pcod",
            "disease waiting",
        ]
    ):
        return "waiting_periods"
    if any(k in msg for k in ["renewal", "renew", "lifetime", "guaranteed renewal", "lifelong", "premium increase"]):
        return "renewal_lifetime"
    if any(k in msg for k in ["exclusion", "exclusions", "not covered", "limitations", "limit", "wont cover", "not include", "sub-limit"]):
        return "exclusions_limitations"
    if any(k in msg for k in ["flexible", "policy flexibility", "switch", "upgrade", "change plan", "top up", "top-up", "port"]):
        return "policy_flexibility"
    if any(k in msg for k in ["tax", "80d", "80c", "deduction", "rebate", "itr", "income tax"]):
        return "tax_benefits_india"
    return None


def _ai_detect_health_topics(message: str) -> list[str]:
    """
    Multi-label topic detector.
    Returns up to the number of detected topics (order preserved).
    """
    msg = (message or "").lower()
    topics: list[str] = []

    def add_if(key: str, condition: bool):
        if condition and key not in topics:
            topics.append(key)

    add_if(
        "coverage_benefits",
        any(k in msg for k in ["coverage", "benefits", "included", "what is covered", "cover", "includes"]),
    )
    add_if(
        "premium_cost",
        any(k in msg for k in ["premium", "cost", "price", "expense", "how much", "expensive", "afford"]),
    )
    add_if(
        "claim_process",
        any(k in msg for k in ["claim", "cashless", "reimbursement", "settlement", "hospitalization"]),
    )
    add_if(
        "network_accessibility",
        any(k in msg for k in ["network", "hospital", "access", "cashless network", "nearby", "coverage area"]),
    )
    add_if(
        "sum_insured",
        any(k in msg for k in ["sum insured", "coverage amount", "limit", "how much cover", "maximum cover"]),
    )
    add_if(
        "waiting_periods",
        any(
            k in msg
            for k in [
                "waiting period",
                "waiting",
                "pre-existing",
                "pre existing",
                "maternity",
                "pcod",
                "disease waiting",
            ]
        ),
    )
    add_if(
        "renewal_lifetime",
        any(
            k in msg
            for k in [
                "renewal",
                "renew",
                "lifetime",
                "guaranteed renewal",
                "lifelong",
                "premium increase",
            ]
        ),
    )
    add_if(
        "exclusions_limitations",
        any(
            k in msg
            for k in [
                "exclusion",
                "exclusions",
                "not covered",
                "limitations",
                "limit",
                "wont cover",
                "not include",
                "sub-limit",
            ]
        ),
    )
    add_if(
        "policy_flexibility",
        any(
            k in msg
            for k in [
                "flexible",
                "policy flexibility",
                "switch",
                "upgrade",
                "change plan",
                "top up",
                "top-up",
                "port",
            ]
        ),
    )
    add_if(
        "tax_benefits_india",
        any(k in msg for k in ["tax", "80d", "80c", "deduction", "rebate", "itr", "income tax"]),
    )

    return topics


def _ai_chat_reply_health_topic(
    topic_key: str,
    message: str,
    rec,
    insurance_items: list,
    investment_items: list,
    age: int,
    balance: float,
) -> str:
    selected_ins = insurance_items[0] if insurance_items else None
    selected_inv = investment_items[0] if investment_items else None

    ins_name = selected_ins.name if selected_ins else "an eligible health/insurance product"
    ins_score = selected_ins.score if selected_ins else None
    ins_reason = selected_ins.reason if selected_ins else ""
    ins_summary = selected_ins.summary if selected_ins else ""

    inv_name = selected_inv.name if selected_inv else "an eligible investment plan"
    inv_reason = selected_inv.reason if selected_inv else ""

    common_anchor = (
        f"Based on your profile (age {age}, balance {_fmt_inr(balance)}) and current catalog matching, "
        f"your top insurance pick is '{ins_name}'"
        + (f" (score {ins_score})" if ins_score is not None else "")
        + (f". Rationale: {ins_reason}." if ins_reason else ".")
    )

    verify_line = "Exact inclusions, sub-limits, and wording vary by plan—confirm in the policy brochure/terms."

    if topic_key == "coverage_benefits":
        return (
            "Coverage & Benefits (what it typically covers)\n"
            f"{common_anchor}\n"
            f"Plan positioning: {ins_summary}\n"
            "How to read benefits in the policy:\n"
            "• Coverage types (what events/procedures are eligible)\n"
            "• Benefit limits and sub-limits (caps per illness/procedure)\n"
            "• Waiting periods that must be completed before certain claims\n"
            "• Cost-sharing rules (deductibles/co-pays, if any)\n"
            f"{verify_line}\n"
        )

    if topic_key == "premium_cost":
        return (
            "Premium & Cost (what drives premium)\n"
            f"{common_anchor}\n"
            "Premium is usually influenced by:\n"
            "• Age at entry and age band progression over time\n"
            "• Sum insured / coverage level\n"
            "• Risk factors (medical history + underwriting rules)\n"
            "• Plan features (room rent limits, sub-limits, network choice)\n"
            "• Claim history and renewal rules (as defined by the insurer)\n"
            "For best certainty:\n"
            "• Use the insurer/agent quote for your exact profile and coverage amount\n"
            f"{verify_line}\n"
        )

    if topic_key == "claim_process":
        return (
            "Claim Process (how claims usually work)\n"
            f"{common_anchor}\n"
            "Typical steps:\n"
            "• Intimation: inform the insurer promptly after hospitalization/diagnosis\n"
            "• Cashless path (if hospital is in-network): pre-authorization request\n"
            "• Reimbursement path (out-of-network): submit bills + documents after treatment\n"
            "• Settlement: insurer evaluates documents and policy terms; settlement amount follows rules\n"
            "Documents often include:\n"
            "• KYC, policy number\n"
            "• Hospital bills, diagnosis/procedure records\n"
            "• Discharge summary, prescriptions\n"
            f"{verify_line}\n"
        )

    if topic_key == "network_accessibility":
        return (
            "Network & Accessibility (Health Insurance)\n"
            f"{common_anchor}\n"
            "What to check:\n"
            "• Cashless hospital list in your city/region\n"
            "• Distance/access for planned and emergency care\n"
            "• Whether the plan supports cashless only for network hospitals and reimbursement otherwise\n"
            "Practical tip:\n"
            "• Before you buy, confirm that nearby hospitals you may need are listed for cashless.\n"
            f"{verify_line}\n"
        )

    if topic_key == "sum_insured":
        return (
            "Sum Insured / Coverage Amount\n"
            f"{common_anchor}\n"
            "Meaning:\n"
            "• Sum insured is the maximum amount the insurer will pay under the policy terms for covered claims.\n"
            "• It directly affects both coverage strength and premium (usually).\n"
            "What to validate:\n"
            "• Policy’s definition of “covered expenses” and any exclusions\n"
            "• Whether claims reduce remaining sum insured (and if restoration/top-up exists)\n"
            "• Sub-limits per procedure/illness\n"
            f"{verify_line}\n"
        )

    if topic_key == "waiting_periods":
        return (
            "Waiting Periods (how long you may wait before coverage starts)\n"
            f"{common_anchor}\n"
            "Common patterns in health insurance:\n"
            "• Initial waiting period: general waiting for many coverages\n"
            "• Pre-existing disease waiting: conditions diagnosed before buying (as defined by the plan)\n"
            "• Maternity/related waiting (if included)\n"
            "• Different waiting schedules for different benefits\n"
            "How to act:\n"
            "• Check the waiting-period table in the brochure/terms for exact days.\n"
            f"{verify_line}\n"
        )

    if topic_key == "renewal_lifetime":
        return (
            "Renewal & Lifetime Benefits\n"
            f"{common_anchor}\n"
            "Key ideas:\n"
            "• Renewal is usually annual/term-based, not “one-time life coverage”.\n"
            "• Insurers may change premiums at renewal based on rules (age band/claims/risk factors).\n"
            "• “Lifetime” wording (if any) depends entirely on the product and definitions.\n"
            "What to verify:\n"
            "• Renewal conditions (cancellation/non-payment rules)\n"
            "• Re-instatement/restoration, and what happens to waiting-period completion\n"
            f"{verify_line}\n"
        )

    if topic_key == "exclusions_limitations":
        return (
            "Exclusions & Limitations (what is not covered / capped)\n"
            f"{common_anchor}\n"
            "Common exclusion themes (varies by plan):\n"
            "• Pre-existing conditions during the waiting period\n"
            "• Non-medically necessary expenses\n"
            "• Cosmetic treatments (if not covered)\n"
            "• Injuries from certain activities (as defined)\n"
            "• War/illegal acts and other policy-defined events\n"
            "Also watch for limitations:\n"
            "• Sub-limits per disease/procedure\n"
            "• Co-pay/deductible mechanics\n"
            "Action:\n"
            "• Confirm exclusions + limits in the policy document wording.\n"
            f"{verify_line}\n"
        )

    if topic_key == "policy_flexibility":
        return (
            "Policy Flexibility (how adaptable the plan is)\n"
            f"{common_anchor}\n"
            "Typical flexibility levers:\n"
            "• Add-ons/riders (if available)\n"
            "• Top-up / increasing coverage over time (subject to rules)\n"
            "• Changing insured members (family eligibility rules)\n"
            "• Portability/switching (if the insurer/product allows)\n"
            "Best practice:\n"
            "• Check whether upgrades change waiting periods or trigger new underwriting.\n"
            f"{verify_line}\n"
        )

    if topic_key == "tax_benefits_india":
        # Use catalog hint: insurance + investment both can be relevant.
        return (
            "Tax Benefits (India-specific, framework)\n"
            f"{common_anchor}\n"
            f"Insurance angle: '{ins_name}' can be relevant for health insurance tax treatment (commonly Section 80D for eligible individuals/families, subject to conditions).\n"
            "Investment angle: if you also consider market-linked options, some investments can qualify under Section 80C (e.g., ELSS-style instruments), subject to your eligibility and the rules in that tax year.\n"
            "What to check (important):\n"
            "• Premium eligibility (who is covered: self/spouse/children/parents)\n"
            "• Deduction limits as per the current tax year\n"
            "• Whether it is health insurance vs life insurance vs investment (rules differ)\n"
            "• Proof: keep premium receipts and policy documentation\n"
            "Rules change year to year—confirm with latest guidance or a CA.\n"
        )

    # Fallback: topic not recognized.
    return "I can help with that topic—try wording like coverage, premium, claim, network, sum insured, waiting period, renewal, exclusions, flexibility, or tax."


def _ai_detect_investment_topics(message: str) -> list[str]:
    """
    Multi-label detector for investment topics (keyword-based; no external AI).
    """
    msg = (message or "").lower()
    topics: list[str] = []

    def add_if(key: str, condition: bool):
        if condition and key not in topics:
            topics.append(key)

    add_if(
        "goal_clarity",
        any(
            k in msg
            for k in [
                "goal",
                "purpose",
                "retirement",
                "house",
                "home",
                "emergency",
                "wealth",
                "time horizon",
                "short term",
                "short-term",
                "long term",
                "long-term",
                "income",
                "growth",
            ]
        ),
    )
    add_if(
        "returns_expectations",
        any(
            k in msg
            for k in [
                "return",
                "expected return",
                "guaranteed",
                "market linked",
                "market-linked",
                "historical",
                "performance",
                "cagr",
                "5 years",
                "10 years",
            ]
        ),
    )
    add_if(
        "risk_level",
        any(
            k in msg
            for k in [
                "risk",
                "low risk",
                "medium risk",
                "high risk",
                "loss",
                "drawdown",
                "downturn",
                "worst case",
                "worst-case",
                "volatility",
            ]
        ),
    )
    add_if(
        "liquidity",
        any(
            k in msg
            for k in [
                "liquid",
                "liquidity",
                "withdraw",
                "withdrawal",
                "lock in",
                "lock-in",
                "penalty",
                "early exit",
                "exit load",
            ]
        ),
    )
    add_if(
        "how_it_works",
        any(
            k in msg
            for k in [
                "how it works",
                "how does it work",
                "working",
                "mechanism",
                "factors affect",
                "interest rates",
                "economy",
                "market",
                "regulated",
                "sebi",
                "rbi",
            ]
        ),
    )
    add_if(
        "costs_charges",
        any(
            k in msg
            for k in [
                "fee",
                "fees",
                "charges",
                "expense ratio",
                "brokerage",
                "exit load",
                "hidden charges",
                "commission",
            ]
        ),
    )
    add_if(
        "tax_india",
        any(
            k in msg
            for k in [
                "tax",
                "taxation",
                "capital gains",
                "ltcg",
                "stcg",
                "dividend",
                "interest income",
                "post tax",
                "post-tax",
                "80c",
                "itr",
            ]
        ),
    )
    add_if(
        "flexibility",
        any(
            k in msg
            for k in [
                "flexible",
                "increase",
                "decrease",
                "switch",
                "switch funds",
                "sip",
                "systematic investment",
                "monthly",
                "step up",
                "step-up",
            ]
        ),
    )
    add_if(
        "diversification",
        any(
            k in msg
            for k in [
                "diversify",
                "diversification",
                "all money",
                "all in one",
                "allocation",
                "portfolio",
                "percentage",
            ]
        ),
    )
    add_if(
        "safety_credibility",
        any(
            k in msg
            for k in [
                "safe",
                "safety",
                "trust",
                "trustworthy",
                "company",
                "fund manager",
                "track record",
                "trackrecord",
                "who manages",
                "credit",
                "rating",
            ]
        ),
    )
    add_if(
        "inflation",
        any(
            k in msg
            for k in [
                "inflation",
                "beat inflation",
                "real return",
                "real returns",
                "after inflation",
            ]
        ),
    )

    return topics


def _ai_chat_reply_investment_topic(
    topic_key: str,
    message: str,
    rec,
    investment_items: list,
    age: int,
    balance: float,
) -> str:
    top_inv = investment_items[0] if investment_items else None
    inv_name = top_inv.name if top_inv else "an eligible investment product"
    inv_score = top_inv.score if top_inv else None
    inv_reason = top_inv.reason if top_inv else ""
    inv_summary = top_inv.summary if top_inv else ""

    anchor = (
        f"Anchor (from current catalog match): '{inv_name}'"
        + (f" (score {inv_score})." if inv_score is not None else ".")
        + (f" Rationale: {inv_reason}." if inv_reason else "")
    )
    profile_line = f"Profile context: goal '{(rec and rec.riskProfile) or ''}', age {age}, balance {_fmt_inr(balance)}."
    verify = "Validate exact features, charges, lock-in, and taxation in official documents; rules vary by product type."

    if topic_key == "goal_clarity":
        return (
            "Goal Clarity (purpose, horizon, income vs growth)\n"
            f"{anchor}\n"
            "Checklist:\n"
            "• Purpose: retirement / house / emergency / wealth creation\n"
            "• Horizon: short-term vs long-term (match volatility to horizon)\n"
            "• Need: regular income vs growth accumulation\n"
            "Decision rule:\n"
            "• Short horizon + low loss tolerance → prefer lower volatility instruments\n"
            "• Long horizon + growth goal → higher equity exposure may be appropriate\n"
            f"{verify}\n"
        )

    if topic_key == "returns_expectations":
        return (
            "Returns & Expectations\n"
            f"{anchor}\n"
            "What to clarify:\n"
            "• Is return guaranteed or market-linked?\n"
            "• Expected return should be a range, not a single number\n"
            "• Historical performance (5–10 years) is useful but not a promise\n"
            "Practical approach:\n"
            "• Compare net-of-fee returns across similar risk categories\n"
            "• Stress test: what happens in a bad year?\n"
            f"{verify}\n"
        )

    if topic_key == "risk_level":
        return (
            "Risk Level (loss tolerance, worst case)\n"
            f"{anchor}\n"
            "Questions to answer:\n"
            "• Can you stay invested during market drawdowns without panic-selling?\n"
            "• Worst case: temporary losses, longer recovery time, and return shortfall vs target\n"
            "• Match risk capacity (cash-flow stability + emergency fund) with risk willingness\n"
            "Rule of thumb:\n"
            "• Higher equity → higher volatility; debt/cash-like → lower volatility but lower return potential\n"
            f"{verify}\n"
        )

    if topic_key == "liquidity":
        return (
            "Liquidity (access to money)\n"
            f"{anchor}\n"
            "Check:\n"
            "• Can you withdraw anytime? If yes, what is the exit load/penalty?\n"
            "• Lock-in period: does it exist and when does it end?\n"
            "• Settlement time: how many days to receive funds after redemption?\n"
            "Best practice:\n"
            "• Keep emergency money in highly liquid instruments; invest surplus for longer horizons\n"
            f"{verify}\n"
        )

    if topic_key == "how_it_works":
        return (
            "Investment Type Understanding (how it works, regulation)\n"
            f"{anchor}\n"
            f"Product positioning: {inv_summary}\n"
            "Factors that usually affect returns:\n"
            "• Market movement (equity exposure), interest rates (debt exposure), credit risk, inflation\n"
            "• Fund strategy, asset allocation, and rebalancing discipline\n"
            "Regulation (India):\n"
            "• Mutual funds/portfolio products are typically under SEBI; banks/deposits under RBI; insurers under IRDAI (depends on product)\n"
            f"{verify}\n"
        )

    if topic_key == "costs_charges":
        return (
            "Costs & Charges (fees, loads, impact)\n"
            f"{anchor}\n"
            "Common cost buckets:\n"
            "• Expense ratio (fund management)\n"
            "• Brokerage/transaction costs\n"
            "• Exit load/early withdrawal penalties\n"
            "Impact guidance:\n"
            "• Fees compound negatively over time—compare net returns after costs\n"
            f"{verify}\n"
        )

    if topic_key == "tax_india":
        return (
            "Tax Implications (India)\n"
            f"{anchor}\n"
            "Framework questions:\n"
            "• Is the return treated as capital gains, interest income, or dividend?\n"
            "• Holding period rules: STCG vs LTCG thresholds depend on instrument type\n"
            "• Any tax-saving eligibility (e.g., some 80C-eligible products like ELSS) depends on instrument and rules\n"
            "Compute:\n"
            "• Post-tax return = expected return - taxes - fees (use realistic assumptions)\n"
            "Tax rules change—confirm with the latest FY guidance or a CA.\n"
        )

    if topic_key == "flexibility":
        return (
            "Flexibility (SIP, switches, change amount)\n"
            f"{anchor}\n"
            "Check:\n"
            "• Can you increase/decrease contributions (SIP step-up/step-down)?\n"
            "• Can you switch funds/plans without triggering penalties or resets?\n"
            "• Minimum amounts and frequency constraints\n"
            f"{verify}\n"
        )

    if topic_key == "diversification":
        return (
            "Diversification (portfolio allocation)\n"
            f"{anchor}\n"
            "Guidance:\n"
            "• Avoid concentration in one product/sector/issuer\n"
            "• Diversify across asset classes (equity/debt/cash) based on horizon and risk\n"
            "• Allocation % depends on your total net worth, income stability, and goals\n"
            "Practical step:\n"
            "• Start with a core diversified allocation, then add satellites for specific themes\n"
            f"{verify}\n"
        )

    if topic_key == "safety_credibility":
        return (
            "Safety & Credibility (who manages it, track record)\n"
            f"{anchor}\n"
            "Due diligence checklist:\n"
            "• Who manages: AMC/issuer, fund manager tenure, process consistency\n"
            "• Track record across cycles (not just recent outperformance)\n"
            "• Governance and risk controls\n"
            "• For debt: credit quality and concentration\n"
            f"{verify}\n"
        )

    if topic_key == "inflation":
        return (
            "Inflation Impact (real return)\n"
            f"{anchor}\n"
            "Core idea:\n"
            "• Real return ≈ nominal return − inflation (roughly)\n"
            "What to check:\n"
            "• Will expected net return likely beat inflation over your horizon?\n"
            "• Higher inflation periods can reduce real purchasing power even with positive nominal returns\n"
            "Action:\n"
            "• Combine growth assets (for inflation-beating potential) with stable assets (for near-term needs)\n"
            f"{verify}\n"
        )

    return "Ask about goal, returns, risk, liquidity, how it works/regulation, charges, India tax, flexibility/SIP, diversification, credibility, or inflation."


def _ai_detect_commercial_bank_topics(message: str) -> list[str]:
    """
    Multi-label keyword detector for commercial banking topics.
    """
    msg = (message or "").lower()
    topics: list[str] = []

    def add_if(key: str, condition: bool):
        if condition and key not in topics:
            topics.append(key)

    add_if(
        "basics_commercial_banks",
        any(k in msg for k in ["commercial bank", "what is a commercial bank", "difference from central bank", "central bank like", "reserve bank"]),
    )
    add_if(
        "core_banking_functions",
        any(k in msg for k in ["primary functions", "secondary functions", "agency services", "utility services", "money creation", "money-creation"]),
    )
    add_if(
        "types_of_deposits",
        any(k in msg for k in ["savings account", "current account", "fixed deposit", "fd", "recurring deposit", "rd", "types of deposits"]),
    )
    add_if(
        "loans_and_advances",
        any(k in msg for k in ["personal loan", "home loan", "vehicle loan", "business loan", "secured", "unsecured", "interest calculated", "interest calculation", "loans and advances"]),
    )
    add_if(
        "interest_rates_policies",
        any(k in msg for k in ["repo rate", "reverse repo", "reverse-repo", "mclr", "base rate", "base rate / mclr", "rbi control", "bank interest rates", "interest rates"]),
    )
    add_if(
        "regulatory_framework",
        any(k in msg for k in ["crr", "slr", "basel", "basel norms", "who regulates", "regulates commercial banks"]),
    )
    add_if(
        "safety_security",
        any(k in msg for k in ["deposit insurance", "dicgc", "is my money safe", "bank fails", "what happens if a bank fails", "fail"]),
    )
    add_if(
        "digital_banking",
        any(k in msg for k in ["internet banking", "mobile banking", "upi", "how does upi", "upi works", "digital transactions", "risks in digital", "phishing", "otp", "upi pin"]),
    )

    return topics


def _ai_chat_reply_commercial_bank_topic(
    topic_key: str,
) -> str:
    verify = "Note: exact rules, coverage limits, and procedures vary by bank/product and can change—confirm on official sources."

    if topic_key == "basics_commercial_banks":
        return (
            "Basics of Commercial Banks\n"
            "• What is a commercial bank?\n"
            "  A commercial bank is a customer-facing financial institution that accepts deposits and provides loans/credit to individuals and businesses.\n"
            "• Primary functions\n"
            "  Deposit-taking and lending (credit creation in the economy).\n"
            "• Difference from a central bank (RBI)\n"
            "  Commercial bank: operates with customer deposits and lends/earns income.\n"
            "  Central bank: conducts monetary policy, manages liquidity, and regulates/oversees the banking system stability (e.g., RBI).\n"
            f"{verify}\n"
        )

    if topic_key == "core_banking_functions":
        return (
            "Core Banking Functions\n"
            "• Primary functions\n"
            "  - Accepting deposits\n"
            "  - Giving loans / advances\n"
            "• Secondary functions (agency & utility services)\n"
            "  - Payments and remittances (bill collections, fund transfers)\n"
            "  - Cards/locker services and other fee-based utilities\n"
            "• Role of banks in money creation\n"
            "  Deposits and lending interact: when banks lend, money can re-circulate as deposits, subject to regulatory buffers and liquidity/reserve requirements.\n"
            f"{verify}\n"
        )

    if topic_key == "types_of_deposits":
        return (
            "Types of Deposits\n"
            "• Savings account\n"
            "  - Designed for personal savings and regular use.\n"
            "  - Transaction limits may apply compared to current accounts.\n\n"
            "• Current account\n"
            "  - Designed for business/operational banking with frequent transactions.\n"
            "  - Typically lower/zero interest; may require minimum balance.\n\n"
            "• Fixed Deposit (FD)\n"
            "  - Term-based deposit; usually offers higher interest than savings.\n"
            "  - Early withdrawal may attract penalties/interest loss.\n\n"
            "• Recurring Deposit (RD)\n"
            "  - You deposit a fixed amount periodically for a fixed tenure.\n"
            "  - Suitable for disciplined saving; maturity payout depends on tenure and rate.\n"
            f"{verify}\n"
        )

    if topic_key == "loans_and_advances":
        return (
            "Loans & Advances\n"
            "• Types of loans\n"
            "  - Personal loan\n"
            "  - Home loan\n"
            "  - Vehicle loan\n"
            "  - Business loan\n\n"
            "• Secured vs unsecured\n"
            "  - Secured loan: backed by collateral (e.g., property for home loans).\n"
            "  - Unsecured loan: without specific collateral; typically higher risk premium and interest.\n\n"
            "• How interest is calculated (high-level)\n"
            "  - Depends on principal, tenure, and the rate.\n"
            "  - Many retail loans are repaid via EMI with interest on the outstanding reducing balance.\n"
            "  - Exact computation is as per loan agreement (and may include fees/charges).\n"
            f"{verify}\n"
        )

    if topic_key == "interest_rates_policies":
        return (
            "Interest Rates & Policies (RBI signals)\n"
            "• Repo rate\n"
            "  - RBI’s lending rate to banks against collateral. Influences bank funding costs.\n"
            "• Reverse repo rate\n"
            "  - RBI’s rate at which RBI absorbs liquidity by accepting funds from banks.\n\n"
            "• Base rate / MCLR\n"
            "  - Banks use internal benchmarks to price loan interest.\n"
            "  - MCLR links to marginal cost of funds; changes in benchmark can move loan rates.\n"
            "• How RBI controls interest rates\n"
            "  - RBI uses monetary policy tools to shape liquidity and funding costs, which transmit to lending rates.\n"
            f"{verify}\n"
        )

    if topic_key == "regulatory_framework":
        return (
            "Regulatory Framework\n"
            "• Who regulates commercial banks in India?\n"
            "  - Primary regulator: RBI.\n\n"
            "• CRR (Cash Reserve Ratio)\n"
            "  - Portion of deposits banks must hold with RBI in cash.\n\n"
            "• SLR (Statutory Liquidity Ratio)\n"
            "  - Portion of deposits banks must hold in approved liquid assets (e.g., government securities).\n\n"
            "• Basel norms\n"
            "  - Capital adequacy and risk management standards; adopted/adapted by regulators to strengthen bank resilience.\n"
            f"{verify}\n"
        )

    if topic_key == "safety_security":
        return (
            "Safety & Security\n"
            "• Is my money safe in a bank?\n"
            "  - Safety depends on bank soundness and regulatory protections.\n\n"
            "• Deposit insurance (DICGC coverage)\n"
            "  - DICGC insures eligible bank deposits up to the coverage limit per depositor per bank (as per current DICGC rules).\n\n"
            "• What happens if a bank fails?\n"
            "  - Resolution processes exist to protect depositors and manage failure scenarios; timelines and steps depend on the resolution arrangement.\n"
            f"{verify}\n"
        )

    if topic_key == "digital_banking":
        return (
            "Digital Banking\n"
            "• Internet banking & mobile banking\n"
            "  - Platforms to view balances, transfer funds, pay bills, and manage accounts.\n\n"
            "• UPI and how it works (high-level)\n"
            "  - You use a Virtual Payment Address (VPA) linked to your bank account.\n"
            "  - Your app initiates a collect/send request; authentication uses your UPI PIN.\n"
            "  - Payment settlement happens through UPI rails managed by the ecosystem.\n\n"
            "• Risks in digital transactions\n"
            "  - Phishing/scams, OTP/UPI PIN theft, SIM/device compromise, and unauthorized access.\n\n"
            "• Best practices\n"
            "  - Never share OTP/UPI PIN; use official apps; enable alerts and device security.\n"
            f"{verify}\n"
        )

    return "I can help with commercial bank basics, deposits, loans, RBI policy, regulation (CRR/SLR/Basel), deposit safety (DICGC), and digital banking."


@app.post("/api/ai/chat", response_model=AiChatOut)
def ai_chat(
    payload: AiChatIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    rec = ai_recommendations(
        AiRecommendIn(goal=payload.goal, riskLevel=payload.riskLevel),
        current=current,
        db=db,
    )

    include_catalog_products = True

    message = (payload.message or "").strip().lower()
    insurance_items = list(rec.insurance or [])
    investment_items = list(rec.investment or [])
    all_items = insurance_items + investment_items
    insurance_names = [p.name for p in insurance_items]
    investment_names = [p.name for p in investment_items]
    age = _estimate_age_from_dob(current.dob)
    balance = float(current.balance or 0)
    message_tokens = [t for t in message.replace("-", " ").split() if len(t) > 2]

    # Product-aware matching:
    # rank recommendations by direct product-name mention and keyword overlap.
    scored_items = []
    for item in all_items:
        name_l = item.name.lower()
        summary_l = (item.summary or "").lower()
        reason_l = (item.reason or "").lower()
        name_tokens = [t for t in name_l.replace("-", " ").split() if len(t) > 2]

        name_hit = 1 if name_l in message else 0
        token_hits = sum(1 for t in message_tokens if t in name_tokens)
        context_hits = sum(1 for t in message_tokens if t in summary_l or t in reason_l)
        score = (name_hit * 100) + (token_hits * 8) + (context_hits * 2) + float(item.score)
        scored_items.append((score, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    top_matches = [x[1] for x in scored_items[:2]]
    has_product_question = any(
        k in message
        for k in [
            "product",
            "plan",
            "which",
            "best",
            "better",
            "difference",
            "compare",
            "recommend",
            "suitable",
        ]
    )
    asks_insurance = any(k in message for k in ["insurance", "cover", "policy", "health", "life"])
    asks_investment = any(
        k in message for k in ["investment", "invest", "return", "wealth", "portfolio"]
    )
    asks_tax = any(k in message for k in ["tax", "save tax", "80c"])

    reply = None

    # Chip-perfect mode: if a UI chip provides a forced topic key,
    # generate exactly one unique topic template (no detection / no duplication).
    forced_key = (payload.forcedTopicKey or "").strip() if payload.forcedTopicKey else None
    if forced_key:
        health_keys = {
            "coverage_benefits",
            "premium_cost",
            "claim_process",
            "network_accessibility",
            "sum_insured",
            "waiting_periods",
            "renewal_lifetime",
            "exclusions_limitations",
            "policy_flexibility",
            "tax_benefits_india",
        }
        investment_keys = {
            "goal_clarity",
            "returns_expectations",
            "risk_level",
            "liquidity",
            "how_it_works",
            "costs_charges",
            "tax_india",
            "flexibility",
            "diversification",
            "safety_credibility",
            "inflation",
        }
        bank_keys = {
            "basics_commercial_banks",
            "core_banking_functions",
            "types_of_deposits",
            "loans_and_advances",
            "interest_rates_policies",
            "regulatory_framework",
            "safety_security",
            "digital_banking",
        }

        if forced_key in health_keys:
            reply = _ai_chat_reply_health_topic(
                forced_key,
                message,
                rec,
                insurance_items,
                investment_items,
                age,
                balance,
            )
        elif forced_key in investment_keys:
            reply = _ai_chat_reply_investment_topic(
                forced_key,
                message,
                rec,
                investment_items,
                age,
                balance,
            )
        elif forced_key in bank_keys:
            include_catalog_products = False
            reply = _ai_chat_reply_commercial_bank_topic(forced_key)
    # Structured templates (compare, eligibility, benefits, risk) — try before generic branches.
    reply = _ai_chat_reply_compare(
        message, insurance_items, investment_items, top_matches, asks_insurance, asks_investment
    )
    if reply is None:
        reply = _ai_chat_reply_eligibility(
            db,
            message,
            top_matches,
            insurance_items,
            investment_items,
            asks_insurance,
            asks_investment,
            age,
            balance,
        )
    if reply is None:
        reply = _ai_chat_reply_benefits(
            message,
            top_matches,
            insurance_items,
            investment_items,
            asks_insurance,
            asks_investment,
        )
    if reply is None:
        reply = _ai_chat_reply_risk_enriched(db, message, rec, insurance_items, investment_items)

    if reply is None:
        topic_keys = _ai_detect_health_topics(message)
        if topic_keys:
            # Avoid extremely long replies when user includes many keywords.
            topic_keys = topic_keys[:3]
            sections = []
            for tkey in topic_keys:
                sections.append(
                    _ai_chat_reply_health_topic(
                        tkey,
                        message,
                        rec,
                        insurance_items,
                        investment_items,
                        age,
                        balance,
                    )
                )
            # Return only the core topic content; the function-level expert wrapper will format it once.
            reply = "\n\n---\n\n".join(sections)

    if reply is None:
        inv_topic_keys = _ai_detect_investment_topics(message)
        if inv_topic_keys:
            inv_topic_keys = inv_topic_keys[:4]
            inv_sections = []
            for tkey in inv_topic_keys:
                inv_sections.append(
                    _ai_chat_reply_investment_topic(
                        tkey,
                        message,
                        rec,
                        investment_items,
                        age,
                        balance,
                    )
                )
            reply = "\n\n---\n\n".join(inv_sections)

    if reply is None:
        bank_topic_keys = _ai_detect_commercial_bank_topics(message)
        if bank_topic_keys:
            include_catalog_products = False
            bank_topic_keys = bank_topic_keys[:3]
            bank_sections = []
            for bkey in bank_topic_keys:
                bank_sections.append(_ai_chat_reply_commercial_bank_topic(bkey))
            reply = "\n\n---\n\n".join(bank_sections)

    if reply is None and has_product_question and top_matches:
        primary = top_matches[0]
        secondary = top_matches[1] if len(top_matches) > 1 else None
        reply = (
            f"Most relevant for your question is '{primary.name}' ({primary.category}, score {primary.score}). "
            f"Why: {primary.reason} Summary: {primary.summary}"
        )
        if secondary:
            reply += (
                f" Next option: '{secondary.name}' ({secondary.category}, score {secondary.score}) "
                f"because {secondary.reason.lower()}"
            )
    elif reply is None and asks_insurance:
        if insurance_items:
            top = insurance_items[0]
            reply = (
                f"Based on your profile (age {age}, risk {rec.riskProfile}), "
                f"best insurance match is {top.name} (score {top.score}). "
                f"Reason: {top.reason}"
            )
        else:
            reply = (
                "I could not find an eligible insurance product for your current profile. "
                "Try a lower risk preference or improve balance eligibility."
            )
    elif reply is None and asks_investment:
        if investment_items:
            top = investment_items[0]
            reply = (
                f"With current balance {_fmt_inr(balance)} and risk {rec.riskProfile}, "
                f"best investment fit is {top.name} (score {top.score}). "
                f"Reason: {top.reason}"
            )
        else:
            reply = (
                "No eligible investment product matched your current profile. "
                "You can try adjusting risk preference or increasing monthly surplus."
            )
    elif reply is None and asks_tax:
        insurance_hint = insurance_names[0] if insurance_names else "a term/health policy"
        invest_hint = investment_names[0] if investment_names else "a balanced investment plan"
        reply = (
            f"Tax angle — From our catalog, pair {insurance_hint} with {invest_hint} for goal-based planning. "
            "ELSS/PPF/NPS and certain insurance premiums may qualify under Indian tax rules in some years; "
            "confirm with a tax professional for your situation."
        )
    elif reply is None:
        top_ins = insurance_items[0] if insurance_items else None
        top_inv = investment_items[0] if investment_items else None
        ins_line = (
            f"Insurance: {top_ins.name} (score {top_ins.score}) - {top_ins.reason}"
            if top_ins
            else "Insurance: No eligible recommendation now."
        )
        inv_line = (
            f"Investment: {top_inv.name} (score {top_inv.score}) - {top_inv.reason}"
            if top_inv
            else "Investment: No eligible recommendation now."
        )
        reply = (
            "Based on your profile, here are the most relevant products for your question. "
            f"{ins_line} {inv_line} "
            "You can ask follow-ups like compare, benefits, eligibility, risk, or tax impact."
        )

    reply = _ai_expert_finalize(
        reply,
        db=db,
        rec=rec,
        insurance_items=insurance_items,
        investment_items=investment_items,
        age=age,
        balance=balance,
        goal_key=payload.goal,
        include_catalog=include_catalog_products,
    )

    return AiChatOut(
        reply=reply,
        suggestedInsurance=insurance_names[:3],
        suggestedInvestment=investment_names[:3],
        disclaimer=(
            "Institutional-style, rules-based guidance only—not an offer or personalised regulated advice. "
            "Validate suitability, pricing, and tax treatment with licensed professionals before acting."
        ),
    )


def _to_kb_doc_out(d: KnowledgeBaseDocument) -> KnowledgeBaseDocOut:
    return KnowledgeBaseDocOut(
        id=int(d.id),
        title=str(d.title or ""),
        tags=str(d.tags or ""),
        content=str(d.content or ""),
        active=bool(d.active),
        createdAt=d.created_at,
    )


_SUPPORT_SENSITIVE_KEYWORDS = {
    "balance",
    "account number",
    "account no",
    "mini statement",
    "statement",
    "transactions",
    "last transaction",
    "beneficiary",
    "transfer",
    "withdraw",
    "deposit",
    "otp",
    "pin",
    "password",
    "cvv",
    "card number",
    "ifsc",
    "upi pin",
}


def _support_is_sensitive_request(msg: str) -> bool:
    m = (msg or "").lower()
    if any(k in m for k in _SUPPORT_SENSITIVE_KEYWORDS):
        return True
    # Avoid handling account-number-like explicit numeric sequences in support auto replies.
    if re.search(r"\b\d{6,}\b", m):
        return True
    return False


def _support_redact(text: str) -> str:
    t = str(text or "")
    t = re.sub(r"\b\d{6,}\b", "[redacted]", t)
    t = re.sub(r"(?i)\b(account\s*(no|number)?|otp|pin|password|cvv)\b\s*[:=-]?\s*\S+", r"\1 [redacted]", t)
    return t


def _support_classify_blocked_intent(msg: str) -> str:
    m = (msg or "").lower()
    if any(k in m for k in ["balance", "statement", "transactions", "last transaction"]):
        return "account_info_request"
    if any(k in m for k in ["transfer", "beneficiary", "withdraw", "deposit"]):
        return "transaction_execution_request"
    if any(k in m for k in ["otp", "pin", "password", "cvv", "card number"]):
        return "credential_disclosure_risk"
    if re.search(r"\b\d{6,}\b", m):
        return "account_identifier_exposure"
    return "other_sensitive_request"


def _support_date_bounds(from_date: str | None, to_date: str | None) -> tuple[datetime | None, datetime | None]:
    start = None
    end = None
    try:
        if from_date and str(from_date).strip():
            d = datetime.strptime(str(from_date).strip(), "%Y-%m-%d").date()
            start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    except Exception:
        start = None
    try:
        if to_date and str(to_date).strip():
            d = datetime.strptime(str(to_date).strip(), "%Y-%m-%d").date()
            end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        end = None
    return start, end


def _support_log(
    db: Session,
    *,
    account_number: str,
    user_message: str,
    reply: str,
    blocked_for_privacy: bool,
    source_titles: list[str],
):
    db.add(
        SupportChatLog(
            account_number=account_number,
            user_message=str(user_message or "")[:2000],
            reply=str(reply or "")[:5000],
            blocked_for_privacy=bool(blocked_for_privacy),
            source_count=int(len(source_titles or [])),
            source_titles_json=json.dumps([str(s) for s in (source_titles or [])[:12]]),
        )
    )


@app.post("/api/support/auto-reply", response_model=SupportChatOut)
def support_auto_reply(
    payload: SupportChatIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    msg = (payload.message or "").strip()
    if _support_is_sensitive_request(msg):
        safe_reply = (
            "I can help with product, FAQ, and policy guidance, but I cannot access or disclose account-specific data in this chat. "
            "For account balance, statements, transfers, or credential-related requests, use secure logged-in features "
            "(Dashboard, Transactions, Transfer) or contact official support."
        )
        _support_log(
            db,
            account_number=current.account_number,
            user_message=msg,
            reply=safe_reply,
            blocked_for_privacy=True,
            source_titles=[],
        )
        db.commit()
        return SupportChatOut(
            reply=safe_reply,
            safeResponse=True,
            blockedForPrivacy=True,
            sources=[],
            disclaimer=(
                "Safe-response policy active: no account data disclosure in support auto-replies. "
                "Never share OTP, PIN, password, or card details."
            ),
        )

    docs = (
        db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.active == True))  # noqa: E712
        .scalars()
        .all()
    )
    # Prefer support-oriented docs first by tag/title hints.
    support_docs = []
    for d in docs:
        tags = (d.tags or "").lower()
        title = (d.title or "").lower()
        if any(k in tags or k in title for k in ["support", "faq", "policy", "terms", "product"]):
            support_docs.append(d)
    if not support_docs:
        support_docs = docs

    sources: list[KnowledgeBaseSource] = []
    try:
        sources = _kb_build_sources(msg, support_docs, top_k=int(payload.topK or 4)) if support_docs else []
    except HTTPException:
        sources = []

    if sources:
        bullets = "\n".join([f"- {s.title}: {s.snippet}" for s in sources[:4]])
        reply = (
            "Customer Support Auto-Reply (RAG)\n"
            "Based on current FAQ/product/policy notes, here is the best matched guidance:\n"
            f"{bullets}\n\n"
            "If your issue is unresolved, share only non-sensitive details (product name, policy type, error text) and I can refine this guidance."
        )
    else:
        reply = (
            "I could not find a strong FAQ/policy match yet. "
            "Please rephrase with product name, policy name, or issue category (fees, eligibility, cancellation, claims, limits), "
            "without sharing account numbers or credentials."
        )

    safe_final = _support_redact(reply)
    _support_log(
        db,
        account_number=current.account_number,
        user_message=msg,
        reply=safe_final,
        blocked_for_privacy=False,
        source_titles=[s.title for s in sources],
    )
    db.commit()
    return SupportChatOut(
        reply=safe_final,
        safeResponse=True,
        blockedForPrivacy=False,
        sources=sources,
        disclaimer=(
            "Safe-response policy: this support assistant does not disclose account-specific data. "
            "Use secure in-app flows for account operations."
        ),
    )


@app.get("/api/admin/support/chats", response_model=list[AdminSupportChatLogItem])
def admin_support_chats(
    limit: int = 50,
    blockedOnly: bool = False,
    accountNumber: str = "",
    fromDate: str = "",
    toDate: str = "",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 50), 200))
    q = select(SupportChatLog)
    if bool(blockedOnly):
        q = q.where(SupportChatLog.blocked_for_privacy == True)  # noqa: E712
    account = (accountNumber or "").strip()
    if account:
        q = q.where(SupportChatLog.account_number == account)
    start, end = _support_date_bounds(fromDate, toDate)
    if start is not None:
        q = q.where(SupportChatLog.created_at >= start)
    if end is not None:
        q = q.where(SupportChatLog.created_at <= end)
    rows = db.execute(q.order_by(SupportChatLog.created_at.desc()).limit(limit)).scalars().all()
    out: list[AdminSupportChatLogItem] = []
    for r in rows:
        try:
            titles = json.loads(r.source_titles_json or "[]")
            if not isinstance(titles, list):
                titles = []
        except Exception:
            titles = []
        out.append(
            AdminSupportChatLogItem(
                id=int(r.id),
                accountNumber=str(r.account_number or ""),
                userMessage=str(r.user_message or ""),
                blockedForPrivacy=bool(r.blocked_for_privacy),
                sourceCount=int(r.source_count or 0),
                sourceTitles=[str(t) for t in titles],
                createdAt=r.created_at,
            )
        )
    return out


@app.get("/api/admin/support/chats/summary", response_model=AdminSupportChatSummaryOut)
def admin_support_chat_summary(
    fromDate: str = "",
    toDate: str = "",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    q_total = select(func.count(SupportChatLog.id))
    q_blocked = select(func.count(SupportChatLog.id)).where(SupportChatLog.blocked_for_privacy == True)  # noqa: E712
    start, end = _support_date_bounds(fromDate, toDate)
    if start is not None:
        q_total = q_total.where(SupportChatLog.created_at >= start)
        q_blocked = q_blocked.where(SupportChatLog.created_at >= start)
    if end is not None:
        q_total = q_total.where(SupportChatLog.created_at <= end)
        q_blocked = q_blocked.where(SupportChatLog.created_at <= end)
    total = int(db.execute(q_total).scalar() or 0)
    blocked = int(
        db.execute(q_blocked).scalar()
        or 0
    )
    safe = max(0, total - blocked)
    return AdminSupportChatSummaryOut(total=total, blocked=blocked, safe=safe)


@app.get("/api/admin/support/chats/blocked-intents", response_model=list[AdminSupportBlockedIntentItem])
def admin_support_blocked_intents(
    limit: int = 10,
    fromDate: str = "",
    toDate: str = "",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 10), 20))
    q = (
        select(SupportChatLog)
        .where(SupportChatLog.blocked_for_privacy == True)  # noqa: E712
        .order_by(SupportChatLog.created_at.desc())
        .limit(5000)
    )
    start, end = _support_date_bounds(fromDate, toDate)
    if start is not None:
        q = q.where(SupportChatLog.created_at >= start)
    if end is not None:
        q = q.where(SupportChatLog.created_at <= end)
    rows = db.execute(q).scalars().all()
    counts: dict[str, int] = {}
    for r in rows:
        k = _support_classify_blocked_intent(str(r.user_message or ""))
        counts[k] = int(counts.get(k, 0) + 1)
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [AdminSupportBlockedIntentItem(intent=k, count=v) for k, v in sorted_items]


@app.get("/api/admin/support/chats/export.csv")
def admin_support_chats_export_csv(
    blockedOnly: bool = False,
    accountNumber: str = "",
    fromDate: str = "",
    toDate: str = "",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    q = select(SupportChatLog).order_by(SupportChatLog.created_at.desc()).limit(10000)
    if bool(blockedOnly):
        q = q.where(SupportChatLog.blocked_for_privacy == True)  # noqa: E712
    account = (accountNumber or "").strip()
    if account:
        q = q.where(SupportChatLog.account_number == account)
    start, end = _support_date_bounds(fromDate, toDate)
    if start is not None:
        q = q.where(SupportChatLog.created_at >= start)
    if end is not None:
        q = q.where(SupportChatLog.created_at <= end)
    rows = db.execute(q).scalars().all()

    sio = io.StringIO()
    w = csv.writer(sio)
    w.writerow(
        [
            "id",
            "account_number",
            "blocked_for_privacy",
            "blocked_intent",
            "source_count",
            "source_titles",
            "user_message",
            "reply",
            "created_at",
        ]
    )
    for r in rows:
        try:
            titles = json.loads(r.source_titles_json or "[]")
            if not isinstance(titles, list):
                titles = []
        except Exception:
            titles = []
        blocked_intent = _support_classify_blocked_intent(str(r.user_message or "")) if bool(r.blocked_for_privacy) else ""
        w.writerow(
            [
                int(r.id),
                str(r.account_number or ""),
                "true" if bool(r.blocked_for_privacy) else "false",
                blocked_intent,
                int(r.source_count or 0),
                " | ".join([str(t) for t in titles[:12]]),
                str(r.user_message or ""),
                str(r.reply or ""),
                (r.created_at.isoformat() if r.created_at else ""),
            ]
        )
    sio.seek(0)
    filename = f"support_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([sio.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/ai/chat-rag", response_model=AiChatRagOut)
def ai_chat_rag(
    payload: AiChatRagIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    # Fallback to existing templates if KB is empty/unavailable.
    docs = (
        db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.active == True))  # noqa: E712
        .scalars()
        .all()
    )
    sources: list[KnowledgeBaseSource] = []
    try:
        sources = _kb_build_sources(payload.message, docs, top_k=int(payload.topK or 3)) if docs else []
    except HTTPException:
        sources = []

    base = ai_chat(
        AiChatIn(
            message=payload.message,
            goal=payload.goal,
            riskLevel=payload.riskLevel,
            forcedTopicKey=payload.forcedTopicKey,
        ),
        current=current,
        db=db,
    )

    if sources:
        kb_block = "Knowledge Base (most relevant notes)\n" + "\n".join(
            [f"• {s.title}: {s.snippet}" for s in sources]
        )
        merged_reply = f"{kb_block}\n\n---\n\n{base.reply}"
    else:
        merged_reply = base.reply

    return AiChatRagOut(
        reply=merged_reply,
        sources=sources,
        suggestedInsurance=base.suggestedInsurance,
        suggestedInvestment=base.suggestedInvestment,
        disclaimer=base.disclaimer,
    )


@app.post("/api/ai/feedback")
def ai_feedback(
    payload: RecommendationFeedbackIn,
    current: User = Depends(_auth_user),
    db: Session = Depends(get_db),
):
    product = db.execute(select(Product).where(Product.id == payload.productId)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    db.add(
        RecommendationFeedback(
            account_number=current.account_number,
            product_id=payload.productId,
            action=payload.action,
        )
    )
    db.commit()
    return {"ok": True}


@app.get("/api/admin/kb/docs", response_model=list[KnowledgeBaseDocOut])
def admin_list_kb_docs(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    docs = db.execute(select(KnowledgeBaseDocument).order_by(KnowledgeBaseDocument.id.desc())).scalars().all()
    return [_to_kb_doc_out(d) for d in docs]


@app.post("/api/admin/kb/docs", response_model=KnowledgeBaseDocOut)
def admin_create_kb_doc(
    payload: KnowledgeBaseDocIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    doc = KnowledgeBaseDocument(
        title=(payload.title or "").strip(),
        tags=(payload.tags or "").strip(),
        content=(payload.content or "").strip(),
        active=bool(payload.active),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _to_kb_doc_out(doc)


@app.put("/api/admin/kb/docs/{doc_id}", response_model=KnowledgeBaseDocOut)
def admin_update_kb_doc(
    doc_id: int,
    payload: KnowledgeBaseDocIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    doc = db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KB document not found.")
    doc.title = (payload.title or "").strip()
    doc.tags = (payload.tags or "").strip()
    doc.content = (payload.content or "").strip()
    doc.active = bool(payload.active)
    db.commit()
    db.refresh(doc)
    return _to_kb_doc_out(doc)


@app.delete("/api/admin/kb/docs/{doc_id}")
def admin_delete_kb_doc(doc_id: int, _: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    doc = db.execute(select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.id == doc_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KB document not found.")
    db.delete(doc)
    db.commit()
    return {"ok": True}


@app.get("/api/admin/voice/audit", response_model=list[AdminVoiceAuditItem])
def admin_voice_audit(
    limit: int = 50,
    accountNumber: str | None = None,
    intent: str | None = None,
    status: str | None = None,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 50), 200))
    q = select(VoiceAuditLog)
    if accountNumber:
        q = q.where(VoiceAuditLog.account_number == str(accountNumber).strip())
    if intent:
        q = q.where(VoiceAuditLog.intent == str(intent).strip().lower())
    if status:
        q = q.where(VoiceAuditLog.status == str(status).strip().lower())
    rows = db.execute(q.order_by(VoiceAuditLog.id.desc()).limit(limit)).scalars().all()
    out: list[AdminVoiceAuditItem] = []
    for r in rows:
        out.append(
            AdminVoiceAuditItem(
                id=int(r.id),
                accountNumber=str(r.account_number or ""),
                intent=str(r.intent or ""),
                transcript=str(r.transcript or ""),
                confidence=float(r.confidence or 0.0),
                requiresStepUp=bool(r.requires_step_up),
                status=str(r.status or ""),
                detail=_safe_json_obj(r.detail_json, {}),
                createdAt=r.created_at,
            )
        )
    return out


@app.get("/api/admin/loan/document-ai/logs", response_model=list[AdminLoanDocumentAiItemOut])
def admin_loan_document_ai_logs(
    limit: int = 50,
    reviewStatus: str | None = None,
    accountNumber: str | None = None,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(int(limit or 50), 200))
    q = select(LoanDocumentAiLog)
    if reviewStatus:
        q = q.where(LoanDocumentAiLog.review_status == str(reviewStatus).strip().lower())
    if accountNumber:
        q = q.where(LoanDocumentAiLog.account_number == str(accountNumber).strip())
    rows = db.execute(q.order_by(LoanDocumentAiLog.id.desc()).limit(limit)).scalars().all()
    out: list[AdminLoanDocumentAiItemOut] = []
    for r in rows:
        out.append(
            AdminLoanDocumentAiItemOut(
                id=int(r.id),
                accountNumber=str(r.account_number or ""),
                fileName=str(r.file_name or ""),
                documentType=str(r.document_type or "unknown"),
                monthlyIncomeExtracted=(float(r.monthly_income_extracted) if r.monthly_income_extracted is not None else None),
                existingEmiExtracted=(float(r.emi_extracted) if r.emi_extracted is not None else None),
                correctedMonthlyIncome=(float(r.corrected_monthly_income) if r.corrected_monthly_income is not None else None),
                correctedExistingEmi=(float(r.corrected_emi) if r.corrected_emi is not None else None),
                reviewStatus=str(r.review_status or "pending"),
                confidence=float(r.confidence or 0.0),
                incomeVerificationStatus=str(r.income_verification_status or "not_checked"),
                createdAt=r.created_at,
            )
        )
    return out


@app.post("/api/admin/loan/document-ai/review")
def admin_loan_document_ai_review(
    payload: AdminLoanDocumentAiReviewIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    row = db.execute(select(LoanDocumentAiLog).where(LoanDocumentAiLog.id == payload.logId)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Document AI log not found.")
    if payload.correctedDocumentType is not None:
        row.corrected_document_type = payload.correctedDocumentType
    if payload.correctedMonthlyIncome is not None:
        row.corrected_monthly_income = float(payload.correctedMonthlyIncome)
    if payload.correctedExistingEmi is not None:
        row.corrected_emi = float(payload.correctedExistingEmi)
    row.review_status = payload.reviewStatus
    row.reviewer_notes = (payload.reviewerNotes or "").strip()
    row.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@app.get("/api/admin/loan/document-ai/model-status", response_model=LoanDocumentAiModelStatusOut)
def admin_loan_document_ai_model_status(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    model = _load_latest_loan_doc_ai_model(db)
    if not model:
        return LoanDocumentAiModelStatusOut(trained=False, trainedAt=None, version=None, samples=0)
    samples = 0
    try:
        metrics = json.loads(model.metrics_json or "{}")
        samples = int(metrics.get("samples", 0) or 0)
    except Exception:
        samples = 0
    return LoanDocumentAiModelStatusOut(
        trained=True,
        trainedAt=model.trained_at,
        version=int(model.version or 1),
        samples=samples,
    )


@app.post("/api/admin/loan/document-ai/train", response_model=LoanDocumentAiTrainOut)
def admin_loan_document_ai_train(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    rows = (
        db.execute(
            select(LoanDocumentAiLog)
            .where(LoanDocumentAiLog.review_status.in_(["approved", "needs_correction"]))
            .order_by(LoanDocumentAiLog.created_at.desc())
            .limit(5000)
        )
        .scalars()
        .all()
    )

    samples: list[tuple[str, str]] = []
    income_ratios: list[float] = []
    emi_ratios: list[float] = []
    salary_count = 0
    bank_count = 0
    for r in rows:
        label = (r.corrected_document_type or r.document_type or "unknown").strip().lower()
        if label not in {"salary_slip", "bank_statement"}:
            continue
        text_blob = f"{r.file_name or ''} {r.raw_text_preview or ''}".lower()
        samples.append((text_blob, label))
        if label == "salary_slip":
            salary_count += 1
        else:
            bank_count += 1

        if r.corrected_monthly_income is not None and r.monthly_income_extracted and float(r.monthly_income_extracted) > 0:
            income_ratios.append(float(r.corrected_monthly_income) / float(r.monthly_income_extracted))
        if r.corrected_emi is not None and r.emi_extracted and float(r.emi_extracted) > 0:
            emi_ratios.append(float(r.corrected_emi) / float(r.emi_extracted))

    if len(samples) < 20 or salary_count < 5 or bank_count < 5:
        return LoanDocumentAiTrainOut(
            trained=False,
            samples=len(samples),
            salarySlipCount=salary_count,
            bankStatementCount=bank_count,
            message="Not enough reviewed samples. Need at least 20 total with >=5 per class.",
        )

    # Naive Bayes style token log-prob model.
    cls = ["salary_slip", "bank_statement"]
    token_counts = {c: {} for c in cls}
    class_counts = {c: 0 for c in cls}
    vocab: set[str] = set()
    for text_blob, label in samples:
        class_counts[label] += 1
        for t in _loan_doc_tokenize(text_blob):
            vocab.add(t)
            token_counts[label][t] = int(token_counts[label].get(t, 0)) + 1

    vocab_size = max(1, len(vocab))
    token_log_probs = {c: {} for c in cls}
    priors = {}
    for c in cls:
        priors[c] = math.log((class_counts[c] + 1) / (len(samples) + len(cls)))
        denom = sum(token_counts[c].values()) + vocab_size
        # Keep top informative tokens to keep model compact.
        top_tokens = sorted(token_counts[c].items(), key=lambda x: x[1], reverse=True)[:1200]
        for tok, cnt in top_tokens:
            token_log_probs[c][tok] = math.log((cnt + 1) / denom)

    def _median(values: list[float], default: float = 1.0) -> float:
        if not values:
            return default
        xs = sorted(values)
        mid = len(xs) // 2
        if len(xs) % 2 == 1:
            return float(xs[mid])
        return float((xs[mid - 1] + xs[mid]) / 2.0)

    model_json = {
        "priors": priors,
        "token_log_probs": token_log_probs,
        "calibration": {
            "incomeMultiplier": _median(income_ratios, 1.0),
            "emiMultiplier": _median(emi_ratios, 1.0),
        },
    }
    metrics = {
        "samples": len(samples),
        "salarySlipCount": salary_count,
        "bankStatementCount": bank_count,
        "vocabSize": vocab_size,
    }
    db.add(
        LoanDocumentAiModel(
            version=2,
            model_json=json.dumps(model_json),
            metrics_json=json.dumps(metrics),
        )
    )
    db.commit()
    return LoanDocumentAiTrainOut(
        trained=True,
        samples=len(samples),
        salarySlipCount=salary_count,
        bankStatementCount=bank_count,
        message=f"Loan Document AI Phase-2 model trained with {len(samples)} reviewed samples.",
    )


@app.get("/api/admin/products", response_model=list[AdminProductOut])
def admin_list_products(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    products = db.execute(select(Product).order_by(Product.category, Product.id)).scalars().all()
    return [_to_admin_product_out(p) for p in products]


@app.post("/api/admin/products", response_model=AdminProductOut)
def admin_create_product(
    payload: AdminProductIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    if payload.minAge > payload.maxAge:
        raise HTTPException(status_code=400, detail="Min age cannot exceed max age.")
    product = Product(
        name=payload.name.strip(),
        category=payload.category,
        risk_level=payload.riskLevel,
        min_age=payload.minAge,
        max_age=payload.maxAge,
        min_balance=float(payload.minBalance),
        summary=payload.summary.strip(),
        active=payload.active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_admin_product_out(product)


@app.put("/api/admin/products/{product_id}", response_model=AdminProductOut)
def admin_update_product(
    product_id: int,
    payload: AdminProductIn,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if payload.minAge > payload.maxAge:
        raise HTTPException(status_code=400, detail="Min age cannot exceed max age.")
    product.name = payload.name.strip()
    product.category = payload.category
    product.risk_level = payload.riskLevel
    product.min_age = payload.minAge
    product.max_age = payload.maxAge
    product.min_balance = float(payload.minBalance)
    product.summary = payload.summary.strip()
    product.active = payload.active
    db.commit()
    db.refresh(product)
    return _to_admin_product_out(product)


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(
    product_id: int,
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    db.delete(product)
    db.commit()
    return {"ok": True}


@app.get("/api/admin/ai-feedback-summary", response_model=list[FeedbackSummaryItem])
def admin_ai_feedback_summary(_: User = Depends(_auth_admin), db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Product.id,
            Product.name,
            Product.category,
            func.sum(case((RecommendationFeedback.action == "accepted", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "saved", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "rejected", 1), else_=0)),
        )
        .select_from(Product)
        .join(
            RecommendationFeedback,
            RecommendationFeedback.product_id == Product.id,
            isouter=True,
        )
        .group_by(Product.id, Product.name, Product.category)
        .order_by(Product.category, Product.name)
    ).all()

    return [
        FeedbackSummaryItem(
            productId=int(r[0]),
            productName=r[1],
            category=r[2],
            accepted=int(r[3] or 0),
            saved=int(r[4] or 0),
            rejected=int(r[5] or 0),
        )
        for r in rows
    ]


@app.get("/api/admin/ai-diagnostics", response_model=AiDiagnosticsOut)
def admin_ai_diagnostics(
    days: int = 7,
    category: str = "all",
    _: User = Depends(_auth_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 90))
    category = (category or "all").lower()
    valid_categories = {"all", "insurance", "investment"}
    if category not in valid_categories:
        category = "all"

    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=days - 1)

    product_filters = []
    if category in {"insurance", "investment"}:
        product_filters.append(Product.category == category)

    feedback_join_filters = [
        RecommendationFeedback.created_at
        >= datetime.combine(from_date, datetime.min.time())
    ]

    rows = db.execute(
        select(
            Product.id,
            Product.name,
            Product.category,
            func.sum(case((RecommendationFeedback.action == "accepted", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "saved", 1), else_=0)),
            func.sum(case((RecommendationFeedback.action == "rejected", 1), else_=0)),
        )
        .select_from(Product)
        .join(
            RecommendationFeedback,
            and_(
                RecommendationFeedback.product_id == Product.id,
                *feedback_join_filters,
            ),
            isouter=True,
        )
        .where(*product_filters)
        .group_by(Product.id, Product.name, Product.category)
    ).all()

    trend_window_days = 7
    trend_from = today - timedelta(days=trend_window_days - 1)
    per_product_trend_rows = db.execute(
        select(
            RecommendationFeedback.product_id,
            RecommendationFeedback.action,
            RecommendationFeedback.created_at,
        )
        .where(RecommendationFeedback.created_at >= datetime.combine(trend_from, datetime.min.time()))
        .where(
            *(
                []
                if category == "all"
                else [
                    RecommendationFeedback.product_id.in_(
                        select(Product.id).where(Product.category == category)
                    )
                ]
            )
        )
    ).all()

    per_product_day = {}
    for product_id, action, created_at in per_product_trend_rows:
        if not product_id or not created_at or action not in {"accepted", "saved", "rejected"}:
            continue
        key = int(product_id)
        if key not in per_product_day:
            per_product_day[key] = {
                (trend_from + timedelta(days=i)).isoformat(): {"accepted": 0, "saved": 0, "rejected": 0}
                for i in range(trend_window_days)
            }
        day_key = created_at.date().isoformat()
        if day_key in per_product_day[key]:
            per_product_day[key][day_key][action] += 1

    diag_items: list[AiDiagnosticProductItem] = []
    for r in rows:
        accepted = int(r[3] or 0)
        saved = int(r[4] or 0)
        rejected = int(r[5] or 0)
        weighted = (accepted * 2.0) + (saved * 1.0) - (rejected * 1.5)
        adjustment = round(12.0 * math.tanh(weighted / 10.0), 2)
        total_feedback = accepted + saved + rejected
        conversion = round((accepted / total_feedback) * 100.0, 2) if total_feedback else 0.0
        product_daily = per_product_day.get(int(r[0]), {})
        trend_parts = []
        for d in sorted(product_daily.keys()):
            vals = product_daily[d]
            trend_parts.append(f"{vals['accepted']}/{vals['saved']}/{vals['rejected']}")
        trend7d = " | ".join(trend_parts) if trend_parts else "0/0/0"
        diag_items.append(
            AiDiagnosticProductItem(
                productId=int(r[0]),
                productName=r[1],
                category=r[2],
                scoreAdjustment=adjustment,
                accepted=accepted,
                saved=saved,
                rejected=rejected,
                totalFeedback=total_feedback,
                conversionRate=conversion,
                trend7d=trend7d,
            )
        )

    boosted = sorted(
        [d for d in diag_items if d.scoreAdjustment > 0],
        key=lambda x: x.scoreAdjustment,
        reverse=True,
    )[:5]
    penalized = sorted(
        [d for d in diag_items if d.scoreAdjustment < 0],
        key=lambda x: x.scoreAdjustment,
    )[:5]

    feedback_rows = db.execute(
        select(RecommendationFeedback.action, RecommendationFeedback.created_at, Product.category)
        .select_from(RecommendationFeedback)
        .join(Product, Product.id == RecommendationFeedback.product_id)
        .where(RecommendationFeedback.created_at >= datetime.combine(from_date, datetime.min.time()))
        .where(*([] if category == "all" else [Product.category == category]))
    ).all()

    trend_map = {
        (from_date + timedelta(days=i)).isoformat(): {"accepted": 0, "saved": 0, "rejected": 0}
        for i in range(days)
    }
    for action, created_at, _product_category in feedback_rows:
        if not created_at:
            continue
        day_key = created_at.date().isoformat()
        if day_key in trend_map and action in trend_map[day_key]:
            trend_map[day_key][action] += 1

    trend = [
        AiFeedbackTrendItem(
            date=day,
            accepted=vals["accepted"],
            saved=vals["saved"],
            rejected=vals["rejected"],
        )
        for day, vals in sorted(trend_map.items())
    ]

    return AiDiagnosticsOut(topBoosted=boosted, topPenalized=penalized, trend=trend)
