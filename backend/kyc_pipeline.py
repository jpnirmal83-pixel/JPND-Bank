"""
KYC: selfie liveness (DeepFace FasNet anti-spoofing) + ID OCR (EasyOCR) + face match (DeepFace.verify).
Optional: client-side blink + motion proof (browser) combined with server-side checks.
Optional dependencies: deepface, tensorflow, easyocr, opencv-python-headless.
"""
from __future__ import annotations

import os

# Apply before any lazy import of tensorflow/deepface (e.g. scripts that import only this module).
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import difflib
import re
from pathlib import Path
from typing import Any

UPLOAD_ROOT = Path(__file__).resolve().parent / "uploads" / "kyc"

# Laplacian variance: very low values often indicate blur or photo-of-screen.
_SHARPNESS_WARN = 80.0
_SHARPNESS_REJECT = 35.0
# Anti-spoof score is model-specific; values are typically in [0, 1].
_ANTISPOOF_MIN = 0.35


def ensure_upload_dir(account_number: str) -> Path:
    d = UPLOAD_ROOT / str(account_number).strip()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", (s or "").lower()).strip()


def _laplacian_sharpness(img_path: Path) -> float:
    """Higher = sharper (more high-frequency detail)."""
    try:
        import cv2  # type: ignore

        img = cv2.imread(str(img_path))
        if img is None:
            return 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return 0.0


def _parse_client_liveness(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _client_liveness_ok(proof: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validates browser proof from kyc_liveness.js (blink + motion).
    Proof version 1: blinkDetected, blinkCount, motionScore, framesAnalyzed.
    Optional proofType submit_snapshot: frame captured at submit when the camera is live (no blink).
    """
    msgs: list[str] = []
    if not proof:
        return False, ["Client liveness: complete the webcam step or use submit with camera active."]
    ver = int(proof.get("version") or 0)
    if ver != 1:
        return False, ["Client liveness: unsupported or missing proof version."]
    proof_type = str(proof.get("proofType") or "")

    if proof_type == "submit_snapshot":
        frames = int(proof.get("framesAnalyzed") or 0)
        motion = float(proof.get("motionScore") or 0.0)
        if frames < 8:
            return False, ["Client liveness: submit snapshot session too short; keep your face in frame."]
        if motion < 0.00015:
            return False, ["Client liveness: face motion too low on submit capture."]
        msgs.append(
            f"Client liveness OK (submit snapshot): frames={frames}, motion={motion:.4f}."
        )
        return True, msgs

    blink = bool(proof.get("blinkDetected"))
    blink_count = int(proof.get("blinkCount") or 0)
    if not blink or blink_count < 1:
        return False, ["Client liveness: at least one blink must be detected in the live capture."]
    motion = float(proof.get("motionScore") or 0.0)
    frames = int(proof.get("framesAnalyzed") or 0)
    if frames < 15:
        return False, ["Client liveness: tracking session too short; keep your face in frame."]
    if motion < 0.0004:
        return False, ["Client liveness: face motion too low (avoid holding up a static photo)."]
    msgs.append(
        f"Client liveness OK: blinks={blink_count}, motion={motion:.4f}, frames={frames}."
    )
    return True, msgs


def name_match_score(registered_name: str, ocr_text: str) -> float:
    reg = _norm_name(registered_name)
    ocr = _norm_name(ocr_text)
    if not reg or not ocr:
        return 0.0
    # Token coverage: how many name tokens appear in OCR
    tokens = [t for t in reg.split() if len(t) > 1]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in ocr)
    token_score = hits / len(tokens)
    # Overall fuzzy ratio on longest window
    ratio = difflib.SequenceMatcher(None, reg, ocr[: min(len(ocr), 2000)]).ratio()
    return float(max(token_score, ratio * 0.9))


def _fallback_ocr_text(id_path: Path, reasons: list[str]) -> str:
    ocr_text = ""
    try:
        import easyocr

        reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
        parts = reader.readtext(str(id_path), detail=0)
        ocr_text = " ".join(str(p) for p in parts if p)
        reasons.append("ID OCR: text extracted (fallback path).")
    except Exception as e:
        reasons.append(f"OCR warning (fallback): {e!s}")
    return ocr_text


def _fallback_face_features(img_path: Path):
    import cv2  # type: ignore

    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Unable to read image: {img_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(64, 64))
    if len(faces) == 0:
        raise ValueError("No face detected.")
    # Select the largest face.
    x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
    face = gray[y : y + h, x : x + w]
    face = cv2.resize(face, (112, 112))
    vec = face.astype("float32").reshape(-1)
    norm = float((vec**2).sum() ** 0.5)
    if norm <= 1e-6:
        raise ValueError("Invalid face vector.")
    vec = vec / norm
    return vec, float(w * h)


def _run_kyc_fallback(
    selfie_path: Path,
    id_path: Path,
    registered_name: str,
    import_error: Exception,
    client_liveness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = [
        "Deep learning KYC stack unavailable; using OpenCV fallback checks.",
        f"DL import error: {import_error!s}",
    ]
    client_ok, client_msgs = _client_liveness_ok(_parse_client_liveness(client_liveness))
    reasons.extend(client_msgs)
    sharp = _laplacian_sharpness(selfie_path)
    reasons.append(f"Selfie sharpness (Laplacian variance): {sharp:.1f}.")
    if sharp < _SHARPNESS_WARN:
        reasons.append("Warning: low sharpness — use a direct camera capture, not a photo of a screen.")
    if not client_ok:
        return {
            "ok_ml": True,
            "liveness_ok": False,
            "liveness_score": 0.0,
            "face_verified": False,
            "face_distance": None,
            "name_match_score": 0.0,
            "ocr_preview": "",
            "status": "rejected",
            "reasons": reasons,
            "error": str(import_error),
            "client_liveness_ok": False,
            "anti_spoof_real": None,
            "antispoof_score": None,
            "sharpness_score": float(round(sharp, 2)),
        }

    try:
        selfie_vec, selfie_area = _fallback_face_features(selfie_path)
        id_vec, id_area = _fallback_face_features(id_path)
    except Exception as e:
        reasons.append(f"Fallback face detection failed: {e!s}")
        ocr_text = _fallback_ocr_text(id_path, reasons)
        return {
            "ok_ml": False,
            "liveness_ok": False,
            "liveness_score": 0.0,
            "face_verified": False,
            "face_distance": None,
            "name_match_score": float(round(name_match_score(registered_name, ocr_text), 4)),
            "ocr_preview": (ocr_text[:400] + "…") if len(ocr_text) > 400 else ocr_text,
            "status": "rejected",
            "reasons": reasons,
            "error": str(import_error),
            "client_liveness_ok": client_ok,
            "anti_spoof_real": None,
            "antispoof_score": None,
            "sharpness_score": float(round(sharp, 2)),
        }

    # Weak liveness proxy in fallback: client blink+motion + clear face region.
    liveness_ok = bool(selfie_area >= 64 * 64) and client_ok
    liveness_score = 0.48 if liveness_ok else 0.0
    if liveness_ok:
        reasons.append("Fallback liveness: client challenge passed + selfie face detected (moderate confidence).")

    # Cosine similarity between normalized grayscale face crops.
    similarity = float((selfie_vec * id_vec).sum())
    face_distance = float(max(0.0, 1.0 - similarity))
    face_verified = bool(similarity >= 0.70)
    reasons.append(
        f"Fallback face match: cosine_similarity={similarity:.4f}, distance={face_distance:.4f}, verified={face_verified}"
    )

    ocr_text = _fallback_ocr_text(id_path, reasons)
    nm_score = name_match_score(registered_name, ocr_text)

    sharp_block = sharp < _SHARPNESS_REJECT
    if sharp_block:
        reasons.append("Rejected: selfie sharpness too low for fallback approval.")
    approved = (
        not sharp_block
        and liveness_ok
        and face_verified
        and nm_score >= 0.55
        and face_distance <= 0.30
    )
    manual = (
        not sharp_block
        and ((liveness_ok and face_verified and nm_score >= 0.35) or (liveness_ok and nm_score >= 0.65))
    )
    if approved:
        status = "approved"
    elif manual:
        status = "manual_review"
        reasons.append("Fallback result is borderline; sent for manual review.")
    else:
        status = "rejected"
        reasons.append("Fallback checks are not strong enough for auto-approval.")

    return {
        "ok_ml": True,
        "liveness_ok": liveness_ok,
        "liveness_score": float(round(liveness_score, 4)),
        "face_verified": face_verified,
        "face_distance": float(round(face_distance, 6)),
        "name_match_score": float(round(nm_score, 4)),
        "ocr_preview": (ocr_text[:400] + "…") if len(ocr_text) > 400 else ocr_text,
        "status": status,
        "reasons": reasons,
        "fallback_mode": True,
        "client_liveness_ok": client_ok,
        "anti_spoof_real": None,
        "antispoof_score": None,
        "sharpness_score": float(round(sharp, 2)),
    }


def run_kyc_checks(
    selfie_path: str | Path,
    id_path: str | Path,
    registered_name: str,
    client_liveness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns dict with keys:
      ok_ml (bool), liveness_ok, liveness_score, face_verified, face_distance,
      name_match_score, ocr_preview, status (approved|rejected|manual_review),
      reasons (list[str]), error (optional),
      client_liveness_ok, anti_spoof_real, antispoof_score, sharpness_score
    """
    selfie_path = Path(selfie_path)
    id_path = Path(id_path)
    reasons: list[str] = []

    proof = _parse_client_liveness(client_liveness)
    client_ok, client_msgs = _client_liveness_ok(proof)
    reasons.extend(client_msgs)
    sharp = _laplacian_sharpness(selfie_path)
    reasons.append(f"Selfie sharpness (Laplacian variance): {sharp:.1f}.")
    if sharp < _SHARPNESS_WARN:
        reasons.append("Warning: low sharpness — prefer a direct camera capture.")
    if sharp < _SHARPNESS_REJECT:
        reasons.append("Sharpness below minimum — image may be a photo of a screen or out of focus.")

    if not client_ok:
        return {
            "ok_ml": True,
            "liveness_ok": False,
            "liveness_score": 0.0,
            "face_verified": False,
            "face_distance": None,
            "name_match_score": 0.0,
            "ocr_preview": "",
            "status": "rejected",
            "reasons": reasons,
            "client_liveness_ok": False,
            "anti_spoof_real": None,
            "antispoof_score": None,
            "sharpness_score": float(round(sharp, 2)),
        }

    try:
        from deepface import DeepFace
    except Exception as e:
        return _run_kyc_fallback(selfie_path, id_path, registered_name, e, client_liveness=proof)

    liveness_ok = False
    liveness_score = 0.0
    anti_spoof_real: bool | None = None
    antispoof_score: float | None = None

    # --- Selfie liveness: DeepFace FasNet anti-spoof + sharpness gate ---
    try:
        faces = DeepFace.extract_faces(
            img_path=str(selfie_path),
            anti_spoofing=True,
            enforce_detection=True,
            detector_backend="opencv",
        )
        if not faces:
            raise ValueError("No face regions returned from extract_faces.")
        face0 = faces[0]
        anti_spoof_real = bool(face0.get("is_real", True))
        raw_score = face0.get("antispoof_score")
        antispoof_score = float(raw_score) if raw_score is not None else None
        score_f = float(antispoof_score or 0.0)
        # Map model score + is_real into a single 0–1 liveness score for display.
        if anti_spoof_real and score_f >= _ANTISPOOF_MIN:
            liveness_score = float(min(1.0, 0.45 + 0.55 * score_f))
        elif anti_spoof_real:
            liveness_score = float(min(1.0, 0.25 + 0.45 * score_f))
        else:
            liveness_score = float(max(0.0, 0.45 * score_f))
        liveness_ok = bool(anti_spoof_real and score_f >= _ANTISPOOF_MIN)
        reasons.append(
            f"Selfie liveness: anti-spoof is_real={anti_spoof_real}, "
            f"antispoof_score={score_f:.3f} (threshold {_ANTISPOOF_MIN})."
        )
        if not liveness_ok:
            reasons.append("Selfie liveness: failed anti-spoof model (possible spoof or screen replay).")
    except Exception:
        try:
            DeepFace.extract_faces(
                img_path=str(selfie_path),
                anti_spoofing=False,
                enforce_detection=True,
                detector_backend="opencv",
            )
            liveness_ok = bool(client_ok and sharp >= _SHARPNESS_WARN)
            liveness_score = 0.52 if liveness_ok else 0.0
            anti_spoof_real = None
            antispoof_score = None
            reasons.append(
                "Selfie liveness: face detected but anti-spoof model unavailable or failed; "
                "using client proof + sharpness only (weaker)."
            )
            if not liveness_ok:
                reasons.append("Rejected: anti-spoof failed and sharpness/client checks insufficient.")
        except Exception as e2:
            reasons.append(f"Selfie face detection failed: {e2!s}")
            return {
                "ok_ml": True,
                "liveness_ok": False,
                "liveness_score": 0.0,
                "face_verified": False,
                "face_distance": None,
                "name_match_score": 0.0,
                "ocr_preview": "",
                "status": "rejected",
                "reasons": reasons,
                "client_liveness_ok": True,
                "anti_spoof_real": None,
                "antispoof_score": None,
                "sharpness_score": float(round(sharp, 2)),
            }

    # --- OCR on ID ---
    ocr_text = ""
    try:
        import easyocr

        reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
        parts = reader.readtext(str(id_path), detail=0)
        ocr_text = " ".join(str(p) for p in parts if p)
        reasons.append("ID OCR: text extracted.")
    except Exception as e:
        reasons.append(f"OCR warning: {e!s}")

    nm_score = name_match_score(registered_name, ocr_text)

    # --- Face match: selfie vs ID (try several DeepFace models + detectors if weights fail) ---
    face_verified = False
    distance: float | None = None
    last_success: dict[str, Any] | None = None
    last_err: Exception | None = None
    face_models = ("Facenet", "VGG-Face", "OpenFace", "DeepFace")
    detectors = ("opencv", "ssd", "mtcnn")

    for model_name in face_models:
        for det in detectors:
            try:
                res = DeepFace.verify(
                    img1_path=str(selfie_path),
                    img2_path=str(id_path),
                    model_name=model_name,
                    distance_metric="cosine",
                    enforce_detection=True,
                    detector_backend=det,
                )
                last_success = res
                face_verified = bool(res.get("verified"))
                distance = float(res.get("distance")) if res.get("distance") is not None else None
                thresh = float(res.get("threshold", 0.4))
                reasons.append(
                    f"Face match ({model_name}/{det}): verified={face_verified}, "
                    f"distance={distance}, threshold≈{thresh:.3f}"
                )
                break
            except Exception as e:
                last_err = e
                continue
        if last_success is not None:
            break

    could_not_compare = last_success is None
    if could_not_compare and last_err:
        reasons.append(
            f"Face match could not run (all models failed). Last error: {last_err!s} "
            "If weights are corrupted, delete incomplete files under ~/.deepface/weights/ "
            "(especially facenet_weights.h5) and retry so DeepFace can re-download them."
        )

    # --- Decision (sharpness gate for auto-approve) ---
    sharp_ok = sharp >= _SHARPNESS_REJECT
    core_match = (
        liveness_ok
        and face_verified
        and nm_score >= 0.45
        and (distance is None or distance <= 0.55)
    )
    approved = core_match and sharp_ok
    manual = (
        (core_match and not sharp_ok)
        or (liveness_ok and face_verified and nm_score < 0.45)
        or (liveness_ok and not face_verified and nm_score >= 0.6)
        or (could_not_compare and liveness_ok)
    )

    if approved:
        status = "approved"
    elif manual:
        status = "manual_review"
        if could_not_compare and liveness_ok:
            reasons.append(
                "Manual review: face comparison models failed to load or run; "
                "documents are stored for staff review. Fix DeepFace weights or verify manually."
            )
        elif core_match and not sharp_ok:
            reasons.append("Manual review: sharpness borderline (possible screen capture).")
        else:
            reasons.append("Manual review: name OCR or face match borderline.")
    else:
        status = "rejected"
        if not liveness_ok:
            reasons.append("Rejected: liveness not satisfied.")
        if not face_verified and not could_not_compare:
            reasons.append("Rejected: selfie does not match ID photo.")
        if nm_score < 0.35 and not could_not_compare:
            reasons.append("Rejected: name on ID does not match profile name.")

    return {
        "ok_ml": True,
        "liveness_ok": liveness_ok,
        "liveness_score": float(round(liveness_score, 4)),
        "face_verified": face_verified,
        "face_distance": float(round(distance, 6)) if distance is not None else None,
        "name_match_score": float(round(nm_score, 4)),
        "ocr_preview": (ocr_text[:400] + "…") if len(ocr_text) > 400 else ocr_text,
        "status": status,
        "reasons": reasons,
        "client_liveness_ok": True,
        "anti_spoof_real": anti_spoof_real,
        "antispoof_score": antispoof_score,
        "sharpness_score": float(round(sharp, 2)),
    }
