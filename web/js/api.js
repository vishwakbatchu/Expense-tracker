const API = "/api";

class AuthError extends Error {
  constructor(message) {
    super(message);
    this.name = "AuthError";
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 401) {
    throw new AuthError("Not authenticated");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const type = res.headers.get("content-type") || "";
  if (type.includes("application/json")) return res.json();
  return res.text();
}

const api = {
  authStatus: () =>
    request("/auth/status", { cache: "no-store", headers: { "Cache-Control": "no-cache" } }),
  login: (username, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  register: (username, password, email) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, email }),
    }),
  logout: () => request("/auth/logout", { method: "POST" }),
  forgotPassword: (email) =>
    request("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token, password) =>
    request("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  getExpenses: (month, search) => {
    const params = new URLSearchParams();
    if (month) params.set("month", month);
    if (search) params.set("search", search);
    const q = params.toString();
    return request(`/expenses${q ? `?${q}` : ""}`);
  },
  createExpense: (data) =>
    request("/expenses", { method: "POST", body: JSON.stringify(data) }),
  updateExpense: (id, data) =>
    request(`/expenses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" }),

  getIncome: (month) => {
    const q = month ? `?month=${month}` : "";
    return request(`/income${q}`);
  },
  createIncome: (data) =>
    request("/income", { method: "POST", body: JSON.stringify(data) }),
  deleteIncome: (id) => request(`/income/${id}`, { method: "DELETE" }),

  getBudgets: () => request("/budgets"),
  setOverallBudget: (amount) =>
    request("/budgets/overall", { method: "PUT", body: JSON.stringify({ amount }) }),
  setCategoryBudget: (category, amount) =>
    request("/budgets/category", {
      method: "PUT",
      body: JSON.stringify({ category, amount }),
    }),

  getRecurring: () => request("/recurring"),
  createRecurring: (data) =>
    request("/recurring", { method: "POST", body: JSON.stringify(data) }),
  deleteRecurring: (id) => request(`/recurring/${id}`, { method: "DELETE" }),
  processRecurring: (month) =>
    request(`/recurring/process?month=${month}`, { method: "POST" }),

  getStats: (month) => {
    const q = month ? `?month=${month}` : "";
    return request(`/stats${q}`);
  },
  getComparison: (n) => request(`/comparison?n=${n}`),
  getMonths: () => request("/months"),

  restoreBackup: (file) =>
    request("/backup/restore", { method: "POST", body: JSON.stringify({ file }) }),

  exportCsvUrl: () => `${API}/export/csv`,
  reportUrl: (month) => {
    const q = month ? `?month=${month}` : "";
    return `${API}/report${q}`;
  },
};
