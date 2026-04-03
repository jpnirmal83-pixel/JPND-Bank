// Core storage + model utilities for JPND Bank

const BANK_STORAGE_KEY = "jaydee_bank_users";
const BANK_SESSION_KEY = "jaydee_bank_session";

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

function loadUsers() {
  const raw = localStorage.getItem(BANK_STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    return [];
  } catch (e) {
    console.error("Failed to parse bank storage", e);
    return [];
  }
}

function saveUsers(users) {
  localStorage.setItem(BANK_STORAGE_KEY, JSON.stringify(users));
}

function generateAccountNumber(existingUsers) {
  const base = 700010000;
  const offset = existingUsers.length + 1;
  return String(base + offset);
}

function generateId(prefix = "id") {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
}

function getUserByAccountOrEmail(identifier) {
  const users = loadUsers();
  const trimmed = (identifier || "").trim();
  const phoneNormalized = trimmed.replace(/\s+/g, "");
  return users.find((u) => {
    const emailMatch =
      u.email &&
      u.email.toLowerCase().trim() === trimmed.toLowerCase();
    const accountMatch = u.accountNumber === trimmed;
    const phoneMatch =
      u.phone &&
      u.phone.replace(/\s+/g, "") === phoneNormalized;
    return emailMatch || accountMatch || phoneMatch;
  });
}

function getUserByAccountNumber(accountNumber) {
  const users = loadUsers();
  return users.find((u) => u.accountNumber === accountNumber);
}

function updateUser(updatedUser) {
  const users = loadUsers();
  const index = users.findIndex((u) => u.accountNumber === updatedUser.accountNumber);
  if (index === -1) return;
  users[index] = updatedUser;
  saveUsers(users);
}

function deleteUser(accountNumber) {
  const users = loadUsers().filter((u) => u.accountNumber !== accountNumber);
  saveUsers(users);
}

function createUser({
  name,
  email,
  phone,
  password,
  initialDeposit = 0,
  isAdmin = false,
  accountType = "",
}) {
  const users = loadUsers();
  if (users.some((u) => u.email.toLowerCase() === email.toLowerCase())) {
    throw new Error("Email is already registered.");
  }
  const accountNumber = generateAccountNumber(users);
  const user = {
    id: generateId("user"),
    name,
    email,
    phone,
    accountNumber,
    balance: Number(initialDeposit) || 0,
    password,
    isAdmin,
    transactions: [],
    accountType,
    createdAt: new Date().toISOString(),
  };

  if (user.balance > 0) {
    user.transactions.push({
      id: generateId("txn"),
      type: "deposit",
      amount: user.balance,
      prevBalance: 0,
      newBalance: user.balance,
      note: "Initial deposit",
      timestamp: new Date().toISOString(),
    });
  }

  users.push(user);
  saveUsers(users);
  return user;
}

// Session helpers

function setSession(session) {
  sessionStorage.setItem(BANK_SESSION_KEY, JSON.stringify(session));
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

function getCurrentUser() {
  const session = getSession();
  if (!session || !session.accountNumber) return null;
  return getUserByAccountNumber(session.accountNumber);
}

function ensureDefaultAdmin() {
  const users = loadUsers();
  // Ensure there is an admin with the default credentials.
  let admin = users.find((u) => u.isAdmin);

  if (admin) {
    // Update existing admin to follow the requested default email/password.
    admin.name = "Jpnirmal (Administrator)";
    admin.email = "nirmala@gmail.com";
    admin.password = "nirmala@123";
    if (!admin.createdAt) {
      admin.createdAt = new Date().toISOString();
    }
  } else {
    admin = {
      id: generateId("admin"),
      name: "Jpnirmal (Administrator)",
      email: "nirmala@gmail.com",
      phone: "0000000000",
      accountNumber: "9999999999",
      balance: 0,
      password: "nirmala@123",
      isAdmin: true,
      transactions: [],
      createdAt: new Date().toISOString(),
    };
    users.push(admin);
  }

  saveUsers(users);
}

// Ensure default admin exists when storage utilities are first loaded
ensureDefaultAdmin();



