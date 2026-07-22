const state = {
  month: "",
  view: "dashboard",
  deferredInstall: null,
};

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => `₹${Number(n).toFixed(2)}`;
const today = () => new Date().toISOString().slice(0, 10);

function toast(message, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  $("#toast-container").appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function showWarnings(warnings) {
  (warnings || []).forEach((w) => toast(w, "warning"));
}

async function loadMonths() {
  const months = await api.getMonths();
  const select = $("#month-select");
  const current = state.month;
  select.innerHTML = '<option value="">All time</option>';
  months.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
  select.value = current;
}

function setView(name) {
  state.view = name;
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  $(`#view-${name}`).classList.add("active");
  document.querySelectorAll(".sidebar-link").forEach((link) => {
    const active = link.dataset.goto === name || (name === "recurring" || name === "compare") && link.dataset.goto === "more";
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  refreshCurrentView();
}

async function refreshCurrentView() {
  try {
    if (state.view === "dashboard") await renderDashboard();
    else if (state.view === "expenses") await renderExpenses();
    else if (state.view === "income") await renderIncome();
    else if (state.view === "budgets") await renderBudgets();
    else if (state.view === "recurring") await renderRecurring();
    else if (state.view === "compare") await renderComparison();
  } catch (err) {
    if (err.name === "AuthError") {
      showLogin();
      return;
    }
    toast(err.message, "error");
  }
}

async function renderDashboard() {
  if (state.month) {
    const { added } = await api.processRecurring(state.month);
    if (added.length) {
      toast(`Added ${added.length} recurring expense(s)`, "success");
    }
  }

  const data = await api.getStats(state.month || undefined);
  const grid = $("#stats-grid");
  const netClass = data.net_savings >= 0 ? "positive" : "negative";

  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Spent</div>
      <div class="stat-value">${fmt(data.total_spent)}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Income</div>
      <div class="stat-value">${fmt(data.total_income)}</div>
    </div>
    <div class="stat-card full">
      <div class="stat-label">Net savings</div>
      <div class="stat-value ${netClass}">${fmt(data.net_savings)}</div>
    </div>
    ${
      data.stats
        ? `<div class="stat-card">
            <div class="stat-label">Avg expense</div>
            <div class="stat-value">${fmt(data.stats.average)}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Top category</div>
            <div class="stat-value" style="font-size:1rem">${escapeHtml(data.stats.top_category)}</div>
          </div>`
        : ""
    }
  `;

  const budgetEl = $("#budget-status");
  const budgetCard = $("#budget-card");
  if (data.budget_status.length) {
    budgetCard.hidden = false;
    budgetEl.innerHTML = data.budget_status
      .map((b) => {
        const pct = Math.min(100, (b.spent / b.limit) * 100);
        return `
          <div class="budget-row">
            <div style="flex:1">
              <div>${escapeHtml(b.name)} <span class="badge ${b.over ? "over" : "ok"}">${b.over ? "Over" : "OK"}</span></div>
              <div class="hint">${fmt(b.spent)} / ${fmt(b.limit)}</div>
              <div class="budget-bar-wrap">
                <div class="budget-bar ${b.over ? "over" : ""}" style="width:${pct}%"></div>
              </div>
            </div>
          </div>`;
      })
      .join("");
  } else {
    budgetCard.hidden = !state.month;
    budgetEl.innerHTML = state.month
      ? '<p class="hint">No budgets set for this month.</p>'
      : '<p class="hint">Select a month to see budget status.</p>';
  }

  const cats = Object.entries(data.category_summary).sort((a, b) => b[1] - a[1]);
  $("#category-breakdown").innerHTML = cats.length
    ? cats
        .map(
          ([cat, amt]) =>
            `<div class="category-row"><span>${escapeHtml(cat)}</span><strong>${fmt(amt)}</strong></div>`
        )
        .join("")
    : '<p class="empty-state">No expenses yet.</p>';
}

function expenseItemHtml(e) {
  const recurring = e.recurring ? ' <span class="badge ok">Recurring</span>' : "";
  return `
    <div class="list-item" data-id="${e.id}">
      <div class="list-item-main">
        <div class="list-item-title">${escapeHtml(e.category)}${recurring}</div>
        <div class="list-item-meta">${escapeHtml(e.date)} · ${e.id}</div>
      </div>
      <div class="list-item-amount">${fmt(e.amount)}</div>
      <div class="list-item-actions">
        <button type="button" class="btn edit-expense">Edit</button>
        <button type="button" class="btn danger delete-expense">Del</button>
      </div>
    </div>`;
}

async function renderExpenses() {
  const search = $("#expense-search").value.trim();
  const items = await api.getExpenses(state.month || undefined, search || undefined);
  $("#expense-list").innerHTML = items.length
    ? items.map(expenseItemHtml).join("")
    : '<p class="empty-state">No expenses found.</p>';
}

async function renderIncome() {
  const items = await api.getIncome(state.month || undefined);
  $("#income-list").innerHTML = items.length
    ? items
        .map(
          (i) => `
        <div class="list-item" data-id="${i.id}">
          <div class="list-item-main">
            <div class="list-item-title">${escapeHtml(i.source)}</div>
            <div class="list-item-meta">${escapeHtml(i.date)} · ${i.id}</div>
          </div>
          <div class="list-item-amount">${fmt(i.amount)}</div>
          <div class="list-item-actions">
            <button type="button" class="btn danger delete-income">Del</button>
          </div>
        </div>`
        )
        .join("")
    : '<p class="empty-state">No income recorded.</p>';
}

async function renderBudgets() {
  const budgets = await api.getBudgets();
  $("#overall-budget-current").textContent = budgets.overall
    ? `Current: ${fmt(budgets.overall)}`
    : "Not set yet.";

  const cats = Object.entries(budgets.categories || {});
  $("#category-budgets-list").innerHTML = cats.length
    ? cats
        .map(
          ([cat, amt]) =>
            `<div class="category-row"><span>${escapeHtml(cat)}</span><strong>${fmt(amt)}</strong></div>`
        )
        .join("")
    : '<p class="hint">No category budgets yet.</p>';
}

async function renderRecurring() {
  const items = await api.getRecurring();
  $("#recurring-list").innerHTML = items.length
    ? items
        .map(
          (r) => `
        <div class="list-item" data-id="${r.id}">
          <div class="list-item-main">
            <div class="list-item-title">${escapeHtml(r.category)}</div>
            <div class="list-item-meta">Day ${r.day} of each month · ${r.id}</div>
          </div>
          <div class="list-item-amount">${fmt(r.amount)}</div>
          <div class="list-item-actions">
            <button type="button" class="btn danger delete-recurring">Del</button>
          </div>
        </div>`
        )
        .join("")
    : '<p class="empty-state">No recurring expenses.</p>';
}

async function renderComparison() {
  const n = Number($("#compare-months").value);
  const data = await api.getComparison(n);
  if (!data.length) {
    $("#comparison-chart").innerHTML = '<p class="empty-state">Not enough data yet.</p>';
    return;
  }
  const maxVal = Math.max(...data.flatMap((m) => [m.spent, m.earned]), 1);
  $("#comparison-chart").innerHTML = data
    .map((m) => {
      const sw = (m.spent / maxVal) * 100;
      const ew = (m.earned / maxVal) * 100;
      const netClass = m.net >= 0 ? "positive" : "negative";
      return `
        <div class="compare-row">
          <div class="compare-label">${m.month} · <span class="stat-value ${netClass}" style="font-size:0.9rem;display:inline">${fmt(m.net)}</span></div>
          <div class="compare-bars">
            <div class="compare-bar-line">
              <span>Spent</span>
              <div class="compare-bar spent" style="width:${sw}%"></div>
              <span>${fmt(m.spent)}</span>
            </div>
            <div class="compare-bar-line">
              <span>Income</span>
              <div class="compare-bar earned" style="width:${ew}%"></div>
              <span>${fmt(m.earned)}</span>
            </div>
          </div>
        </div>`;
    })
    .join("");
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

const modal = $("#modal");
const modalForm = $("#modal-form");
let modalMode = null;
let modalId = null;

function openModal(mode, item = null) {
  modalMode = mode;
  modalId = item?.id ?? null;
  const fields = $("#modal-fields");
  const title = $("#modal-title");

  if (mode === "expense") {
    title.textContent = item ? "Edit expense" : "Add expense";
    fields.innerHTML = `
      <label>Date<input type="date" name="date" value="${item?.date || today()}" required></label>
      <label>Category<input type="text" name="category" value="${escapeHtml(item?.category || "")}" required></label>
      <label>Amount<input type="number" name="amount" step="0.01" min="0.01" value="${item?.amount || ""}" required></label>`;
  } else if (mode === "income") {
    title.textContent = "Add income";
    fields.innerHTML = `
      <label>Date<input type="date" name="date" value="${today()}" required></label>
      <label>Source<input type="text" name="source" placeholder="Salary, Freelance…" required></label>
      <label>Amount<input type="number" name="amount" step="0.01" min="0.01" required></label>`;
  } else if (mode === "recurring") {
    title.textContent = "Add recurring expense";
    fields.innerHTML = `
      <label>Category<input type="text" name="category" required></label>
      <label>Amount<input type="number" name="amount" step="0.01" min="0.01" required></label>
      <label>Day of month (1–28)<input type="number" name="day" min="1" max="28" value="1" required></label>`;
  }
  modal.showModal();
}

modalForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(modalForm);
  try {
    if (modalMode === "expense") {
      const payload = {
        date: fd.get("date"),
        category: fd.get("category"),
        amount: Number(fd.get("amount")),
      };
      if (modalId) {
        const res = await api.updateExpense(modalId, payload);
        showWarnings(res.warnings);
        toast("Expense updated", "success");
      } else {
        const res = await api.createExpense(payload);
        showWarnings(res.warnings);
        toast("Expense added", "success");
      }
    } else if (modalMode === "income") {
      await api.createIncome({
        date: fd.get("date"),
        source: fd.get("source"),
        amount: Number(fd.get("amount")),
      });
      toast("Income added", "success");
    } else if (modalMode === "recurring") {
      await api.createRecurring({
        category: fd.get("category"),
        amount: Number(fd.get("amount")),
        day: Number(fd.get("day")),
      });
      toast("Recurring expense added", "success");
    }
    modal.close();
    await loadMonths();
    await refreshCurrentView();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#modal-cancel").addEventListener("click", () => modal.close());

document.querySelectorAll("[data-goto]").forEach((btn) => {
  btn.addEventListener("click", () => setView(btn.dataset.goto));
});

$("#month-select").addEventListener("change", (e) => {
  state.month = e.target.value;
  refreshCurrentView();
});

$("#expense-search").addEventListener(
  "input",
  debounce(() => renderExpenses(), 300)
);

$("#add-expense-btn").addEventListener("click", () => openModal("expense"));
$("#add-income-btn").addEventListener("click", () => openModal("income"));
$("#add-recurring-btn").addEventListener("click", () => openModal("recurring"));

$("#expense-list").addEventListener("click", async (e) => {
  const item = e.target.closest(".list-item");
  if (!item) return;
  const id = item.dataset.id;
  if (e.target.classList.contains("edit-expense")) {
    const expenses = await api.getExpenses();
    const exp = expenses.find((x) => x.id === id);
    if (exp) openModal("expense", exp);
  } else if (e.target.classList.contains("delete-expense")) {
    if (!confirm("Delete this expense?")) return;
    try {
      await api.deleteExpense(id);
      toast("Deleted", "success");
      await refreshCurrentView();
    } catch (err) {
      toast(err.message, "error");
    }
  }
});

$("#income-list").addEventListener("click", async (e) => {
  if (!e.target.classList.contains("delete-income")) return;
  const id = e.target.closest(".list-item").dataset.id;
  if (!confirm("Delete this income entry?")) return;
  try {
    await api.deleteIncome(id);
    toast("Deleted", "success");
    await loadMonths();
    await refreshCurrentView();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#recurring-list").addEventListener("click", async (e) => {
  if (!e.target.classList.contains("delete-recurring")) return;
  const id = e.target.closest(".list-item").dataset.id;
  if (!confirm("Delete this recurring expense?")) return;
  try {
    await api.deleteRecurring(id);
    toast("Deleted", "success");
    await refreshCurrentView();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#overall-budget-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const amount = Number(new FormData(e.target).get("amount"));
  try {
    await api.setOverallBudget(amount);
    toast("Overall budget saved", "success");
    e.target.reset();
    await renderBudgets();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#category-budget-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await api.setCategoryBudget(fd.get("category"), Number(fd.get("amount")));
    toast("Category budget saved", "success");
    e.target.reset();
    await renderBudgets();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#compare-months").addEventListener("change", () => renderComparison());

$("#export-csv-btn").addEventListener("click", () => {
  window.location.href = api.exportCsvUrl();
});

$("#open-report-btn").addEventListener("click", () => {
  window.open(api.reportUrl(state.month || undefined), "_blank");
});

document.querySelectorAll("[data-restore]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const file = btn.dataset.restore;
    if (!confirm(`Restore ${file} from the last backup? This overwrites current data.`)) return;
    try {
      await api.restoreBackup(file);
      toast("Restored from backup", "success");
      await loadMonths();
      await refreshCurrentView();
    } catch (err) {
      toast(err.message, "error");
    }
  });
});

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  state.deferredInstall = e;
  $("#install-btn").hidden = false;
});

$("#install-btn").addEventListener("click", async () => {
  if (!state.deferredInstall) return;
  state.deferredInstall.prompt();
  await state.deferredInstall.userChoice;
  state.deferredInstall = null;
  $("#install-btn").hidden = true;
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").then(() => {
    navigator.serviceWorker.getRegistrations().then((regs) =>
      regs.forEach((r) => r.update())
    );
  }).catch(() => {});
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && !$("#app").hidden) {
    api.authStatus().then((status) => {
      if (status.auth_required && !status.authenticated) showLogin();
    }).catch(() => showLogin());
  }
});

function showLogin() {
  document.body.classList.add("login-mode");
  $("#login-screen").hidden = false;
  $("#app").hidden = true;
}

function showApp() {
  document.body.classList.remove("login-mode");
  $("#login-screen").hidden = true;
  $("#app").hidden = false;
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const errEl = $("#login-error");
  errEl.hidden = true;
  try {
    await api.login(fd.get("username"), fd.get("password"));
    errEl.hidden = true;
    await bootApp();
  } catch (err) {
    errEl.textContent =
      err.name === "AuthError" || err.message.includes("Invalid")
        ? "Invalid username or password"
        : err.message;
    errEl.hidden = false;
  }
});

$("#logout-btn").addEventListener("click", async () => {
  try {
    await api.logout();
  } catch (_) {}
  showLogin();
});

let forgotUsername = null;

$("#forgot-password-btn").addEventListener("click", () => {
  $("#forgot-error").hidden = true;
  $("#forgot-success").hidden = true;
  $("#forgot-form").reset();
  $("#forgot-step-email").hidden = false;
  $("#forgot-step-reset").hidden = true;
  $("#forgot-submit").textContent = "Get reset code";
  forgotUsername = null;
  $("#forgot-dialog").showModal();
});
$("#forgot-close").addEventListener("click", () => {
  $("#forgot-dialog").close();
});
$("#forgot-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const errEl = $("#forgot-error");
  const successEl = $("#forgot-success");
  errEl.hidden = true;
  successEl.hidden = true;

  if (!forgotUsername) {
    // Step 1: look up the account and generate a code (no email is sent).
    try {
      const result = await api.forgotPassword(fd.get("email"));
      forgotUsername = result.username;
      $("#forgot-code-display").textContent = `Your reset code: ${result.code} (expires in 10 minutes)`;
      $("#forgot-step-email").hidden = true;
      $("#forgot-step-reset").hidden = false;
      $("#forgot-submit").textContent = "Reset password";
    } catch (err) {
      errEl.textContent = err.message;
      errEl.hidden = false;
    }
    return;
  }

  // Step 2: verify the code and set the new password.
  const password = fd.get("password");
  const confirmPassword = fd.get("confirm_password");
  if (password !== confirmPassword) {
    errEl.textContent = "Passwords do not match";
    errEl.hidden = false;
    return;
  }
  try {
    await api.resetPassword(forgotUsername, fd.get("code"), password);
    successEl.textContent = "Password reset! You can now sign in.";
    successEl.hidden = false;
    $("#forgot-step-reset").hidden = true;
    forgotUsername = null;
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

$("#create-account-btn").addEventListener("click", () => {
  $("#register-error").hidden = true;
  $("#register-dialog").showModal();
});
$("#register-cancel").addEventListener("click", () => {
  $("#register-dialog").close();
});
$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const errEl = $("#register-error");
  const password = fd.get("password");
  errEl.hidden = true;
  if (password !== fd.get("confirm_password")) {
    errEl.textContent = "Passwords do not match";
    errEl.hidden = false;
    return;
  }
  try {
    await api.register(fd.get("username"), password, fd.get("email"));
    $("#register-dialog").close();
    e.target.reset();
    await bootApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

async function bootApp() {
  const status = await api.authStatus();
  if (!status.authenticated) {
    showLogin();
    return;
  }
  $("#logout-btn").hidden = false;
  showApp();
  await loadMonths();
  setView("dashboard");
}

(async function init() {
  try {
    const status = await api.authStatus();
    if (!status.authenticated) {
      showLogin();
      return;
    }
    await bootApp();
  } catch (err) {
    showLogin();
    toast(err.message, "error");
  }
})();
