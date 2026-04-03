(function () {
  const session = getSession();
  const kycForm = document.getElementById("kycForm");
  const kycError = document.getElementById("kycError");
  const kycSuccess = document.getElementById("kycSuccess");
  const kycStatusLine = document.getElementById("kycStatusLine");
  const kycResultDetail = document.getElementById("kycResultDetail");
  const kycSubmitBtn = document.getElementById("kycSubmitBtn");
  const kycStartLiveBtn = document.getElementById("kycStartLiveBtn");
  const kycLiveVideo = document.getElementById("kycLiveVideo");
  const kycSelfieReadyLine = document.getElementById("kycSelfieReadyLine");

  if (!session || !session.accountNumber || session.isAdmin) {
    window.location.href = "login.html";
    return;
  }

  const kycActiveFlow = document.getElementById("kycActiveFlow");

  async function refreshStatus() {
    if (!kycStatusLine) return;
    try {
      const s = await getKycStatus();
      const doneOrQueued =
        s.kycVerified || (s.lastStatus && s.lastStatus === "manual_review");

      if (doneOrQueued) {
        kycStatusLine.textContent = "Your KYC is Completed";
        if (kycActiveFlow) kycActiveFlow.classList.add("hidden");
        if (kycForm) kycForm.classList.add("hidden");
        showOk("Your KYC is Completed");
        if (kycResultDetail) {
          kycResultDetail.textContent =
            "Your live selfie and ID document have been captured and stored securely.";
          kycResultDetail.classList.remove("hidden");
        }
      } else {
        hideOk();
        if (kycResultDetail) {
          kycResultDetail.classList.add("hidden");
          kycResultDetail.textContent = "";
        }
        kycStatusLine.textContent = s.lastStatus
          ? `Last submission: ${s.lastStatus}. Complete the form below to try again or continue onboarding.`
          : "KYC not completed yet.";
      }
    } catch {
      kycStatusLine.textContent = "";
    }
  }

  function showErr(msg) {
    if (!kycError) return;
    kycError.textContent = msg;
    kycError.classList.remove("hidden");
  }
  function hideErr() {
    if (!kycError) return;
    kycError.textContent = "";
    kycError.classList.add("hidden");
  }
  function showOk(msg) {
    if (!kycSuccess) return;
    kycSuccess.textContent = msg;
    kycSuccess.classList.remove("hidden");
  }
  function hideOk() {
    if (!kycSuccess) return;
    kycSuccess.textContent = "";
    kycSuccess.classList.add("hidden");
  }

  if (kycStartLiveBtn && kycLiveVideo && window.KycLiveness) {
    kycStartLiveBtn.addEventListener("click", async () => {
      hideErr();
      hideOk();
      if (kycSelfieReadyLine) kycSelfieReadyLine.classList.add("hidden");
      try {
        await window.KycLiveness.start({
          videoEl: kycLiveVideo,
          statusEl: document.getElementById("kycLiveStatus"),
          startBtn: kycStartLiveBtn,
          onDone: () => {
            const sf = window.KycLiveness.getSelfieFile();
            const input = document.getElementById("kycSelfie");
            if (input && sf) {
              const dt = new DataTransfer();
              dt.items.add(sf);
              input.files = dt.files;
            }
            if (kycSelfieReadyLine) kycSelfieReadyLine.classList.remove("hidden");
          },
          onError: (e) => {
            showErr(e && e.message ? e.message : "Camera or liveness failed.");
          },
        });
      } catch (e) {
        showErr(e && e.message ? e.message : "Could not start camera.");
      }
    });
  }

  if (kycForm) {
    kycForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideErr();
      hideOk();
      if (kycResultDetail) {
        kycResultDetail.textContent = "";
        kycResultDetail.classList.add("hidden");
      }

      const idInput = document.getElementById("kycId");
      const idf = idInput && idInput.files && idInput.files[0];

      if (!window.KycLiveness) {
        showErr("KYC scripts did not load. Refresh the page and try again.");
        return;
      }

      let sf = window.KycLiveness.getSelfieFile();
      let proof = window.KycLiveness.getProof();

      if (!sf || !proof) {
        if (typeof window.KycLiveness.captureSnapshotForSubmit === "function") {
          if (kycSubmitBtn) {
            kycSubmitBtn.disabled = true;
            kycSubmitBtn.dataset.prevLabel = kycSubmitBtn.textContent;
            kycSubmitBtn.textContent = "Capturing photo…";
          }
          try {
            const snap = await window.KycLiveness.captureSnapshotForSubmit(
              kycLiveVideo,
              document.getElementById("kycLiveStatus")
            );
            if (snap && snap.file && snap.proof) {
              sf = snap.file;
              proof = snap.proof;
            }
          } finally {
            if (kycSubmitBtn && kycSubmitBtn.dataset.prevLabel) {
              kycSubmitBtn.textContent = kycSubmitBtn.dataset.prevLabel;
              delete kycSubmitBtn.dataset.prevLabel;
            }
            if (kycSubmitBtn) kycSubmitBtn.disabled = false;
          }
        }
      }

      if (!sf || !proof) {
        showErr(
          'Click "Start camera & liveness" first, keep your face in the frame, then click Submit for verification. You can submit without blinking — your photo will be captured when you submit.'
        );
        if (kycSubmitBtn) kycSubmitBtn.disabled = false;
        return;
      }
      if (!idf) {
        showErr("Please choose an ID document image.");
        return;
      }

      if (kycSubmitBtn) kycSubmitBtn.disabled = true;
      try {
        const res = await uploadKyc(sf, idf, proof);
        hideErr();

        // Upload succeeded: selfie and ID are stored on the server.
        if (kycStatusLine) kycStatusLine.textContent = "Your KYC is Completed";
        showOk("Your KYC is Completed");
        if (kycActiveFlow) kycActiveFlow.classList.add("hidden");

        if (kycResultDetail) {
          kycResultDetail.classList.remove("hidden");
          let detail =
            "Your live selfie and ID document have been captured and stored securely.";
          if (res.status === "rejected") {
            detail +=
              "\n\nAutomatic checks did not pass. You may try again with clearer photos.";
            if ((res.reasons || []).length) {
              detail += "\n\n" + res.reasons.join("\n");
            }
          } else if (res.status === "manual_review") {
            detail += "\n\nYour submission is pending manual review.";
          }
          kycResultDetail.textContent = detail;
        }
      } catch (err) {
        showErr(err.message || "KYC failed.");
      } finally {
        if (kycSubmitBtn) kycSubmitBtn.disabled = false;
      }
    });
  }

  refreshStatus();
})();
