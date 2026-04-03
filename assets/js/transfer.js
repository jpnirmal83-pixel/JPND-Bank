(function () {
  const session = getSession();
  let user = null;

  const form = document.getElementById("transferForm");
  const errorBox = document.getElementById("transferError");
  const successBox = document.getElementById("transferSuccess");

  if (!form) return;

  bootstrap();

  async function bootstrap() {
    user = await getCurrentUser();
    if (!session || !user || session.isAdmin) {
      window.location.href = "index.html";
      return;
    }
  }

  form.addEventListener("submit", async (e) => {
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

    const sender = await getCurrentUser();
    if (!sender) {
      window.location.href = "index.html";
      return;
    }

    if (sender.balance < amount) {
      return showBox(errorBox, "Insufficient balance for this transfer.");
    }

    const recipient = await getUserByAccountNumber(toAccount);
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

    try {
      await transferAmount({
        fromAccount: sender.accountNumber,
        toAccount,
        amount,
        mode,
        note: noteRaw,
      });
    } catch (err) {
      return showBox(errorBox, err.message || "Transfer failed.");
    }

    showBox(successBox, "Amount transferred. Please check the account.");
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


