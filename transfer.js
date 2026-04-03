(function () {
  const session = getSession();
  const user = getCurrentUser();

  // Only allow signed-in non-admin users to access transfer page
  if (!session || !user || session.isAdmin) {
    window.location.href = "index.html";
    return;
  }

  const form = document.getElementById("transferForm");
  const errorBox = document.getElementById("transferError");
  const successBox = document.getElementById("transferSuccess");

  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    hideBox(errorBox);
    hideBox(successBox);

    const mode = (document.getElementById("transferMode").value || "").trim();
    const toAccount = (document.getElementById("toAccount").value || "").trim();
    const toName = (document.getElementById("toName").value || "").trim();
    const amountRaw =
      (document.getElementById("transferAmount").value || "").trim();
    const noteRaw =
      (document.getElementById("transferNote").value || "").trim();

    if (!mode || !toAccount || !amountRaw) {
      return showBox(
        errorBox,
        "Please select transfer mode and enter account and amount."
      );
    }

    const amount = Number(amountRaw.replace(/[^0-9.\-]/g, ""));
    if (!amount || isNaN(amount) || amount <= 0) {
      return showBox(errorBox, "Please enter a valid amount.");
    }

    if (toAccount === user.accountNumber) {
      return showBox(errorBox, "You cannot transfer to your own account.");
    }

    const sender = getCurrentUser();
    if (!sender) {
      window.location.href = "index.html";
      return;
    }

    if (sender.balance < amount) {
      return showBox(errorBox, "Insufficient balance for this transfer.");
    }

    const recipient = getUserByAccountNumber(toAccount);
    if (!recipient || recipient.isAdmin) {
      return showBox(errorBox, "Recipient account not found.");
    }

    // OTP confirmation
    const otp = prompt(
      "Enter the OTP sent to your registered mobile number (sample: 1234):"
    );
    if (!otp) {
      return showBox(errorBox, "OTP is required to complete the transfer.");
    }
    if (otp.trim() !== "1234") {
      return showBox(errorBox, "Invalid OTP. Please try again.");
    }

    // Perform transfer
    const prevSenderBal = Number(sender.balance || 0);
    const prevRecipientBal = Number(recipient.balance || 0);

    const newSenderBal = prevSenderBal - amount;
    const newRecipientBal = prevRecipientBal + amount;

    sender.balance = newSenderBal;
    recipient.balance = newRecipientBal;

    const timestamp = new Date().toISOString();
    const modeLabel = mode.toUpperCase();
    const fullNote = noteRaw
      ? `${modeLabel} - ${noteRaw}`
      : `${modeLabel} transfer`;

    sender.transactions = sender.transactions || [];
    recipient.transactions = recipient.transactions || [];

    const txOut = {
      id: generateId("txn"),
      type: "transfer-out",
      mode: modeLabel,
      counterpartyAccount: toAccount,
      counterpartyName: toName || "",
      amount,
      prevBalance: prevSenderBal,
      newBalance: newSenderBal,
      note: `To ${toAccount}${toName ? " - " + toName : ""} | ${fullNote}`,
      timestamp,
    };

    const txIn = {
      id: generateId("txn"),
      type: "transfer-in",
      mode: modeLabel,
      counterpartyAccount: sender.accountNumber,
      counterpartyName: sender.name,
      amount,
      prevBalance: prevRecipientBal,
      newBalance: newRecipientBal,
      note: `From ${sender.accountNumber} - ${sender.name} | ${fullNote}`,
      timestamp,
    };

    sender.transactions.push(txOut);
    recipient.transactions.push(txIn);

    updateUser(sender);
    updateUser(recipient);

    showBox(successBox, "Amount tranferred. Please check the account");
    form.reset();
  });

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


