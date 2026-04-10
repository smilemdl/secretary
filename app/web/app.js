const elements = {
  form: document.querySelector("#command-form"),
  input: document.querySelector("#command-input"),
  replyBox: document.querySelector("#reply-box"),
  focusCard: document.querySelector("#focus-card"),
  summaryGrid: document.querySelector("#summary-grid"),
  todayList: document.querySelector("#today-list"),
  pendingList: document.querySelector("#pending-list"),
  currentList: document.querySelector("#current-list"),
  overdueList: document.querySelector("#overdue-list"),
  serverTime: document.querySelector("#server-time"),
  pollNote: document.querySelector("#poll-note"),
  helpButton: document.querySelector("#help-button"),
};

let pollTimer = null;
let pollSeconds = 15;

async function fetchState() {
  const response = await fetch("/api/state");
  if (!response.ok) {
    throw new Error("加载状态失败");
  }
  return response.json();
}

async function sendCommand(text) {
  const response = await fetch("/api/commands", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new Error("发送指令失败");
  }

  return response.json();
}

function renderTaskList(target, tasks, emptyText) {
  if (!tasks || tasks.length === 0) {
    target.innerHTML = `<div class="empty-list">${emptyText}</div>`;
    return;
  }

  target.innerHTML = tasks.map((task) => `
    <article class="task-item">
      <div>
        <h3>${escapeHtml(task.title)}</h3>
        <p>${task.scheduled_at}</p>
      </div>
      <div class="task-meta">
        <span>${task.status}</span>
        <span>提醒 ${task.remind_count} 次</span>
      </div>
    </article>
  `).join("");
}

function renderFocus(task) {
  if (!task) {
    elements.focusCard.className = "focus-card empty";
    elements.focusCard.innerHTML = "当前没有需要立刻处理的事务。";
    return;
  }

  elements.focusCard.className = "focus-card";
  elements.focusCard.innerHTML = `
    <div class="focus-title-row">
      <h3>${escapeHtml(task.title)}</h3>
      <span class="badge">${task.status}</span>
    </div>
    <p class="focus-time">计划时间：${task.scheduled_at}</p>
    <p class="focus-time">上次提醒：${task.last_reminded_at}</p>
    <p class="focus-detail">看到提醒不算完成，只有你执行了完成、延后、改期或取消，事务才会闭环。</p>
  `;
}

function renderSummary(summary) {
  const cards = [
    { label: "今日事务", value: summary.today_count },
    { label: "未完成", value: summary.pending_count },
    { label: "逾期", value: summary.overdue_count },
  ];

  elements.summaryGrid.innerHTML = cards.map((card) => `
    <article class="summary-card">
      <span>${card.label}</span>
      <strong>${card.value}</strong>
    </article>
  `).join("");
}

function renderState(state) {
  pollSeconds = state.poll_interval_seconds || pollSeconds;
  elements.serverTime.textContent = `服务器时间 ${formatIso(state.server_time)}`;
  elements.pollNote.textContent = `每 ${pollSeconds} 秒刷新`;
  renderFocus(state.focus_task);
  renderSummary(state.summary);
  renderTaskList(elements.todayList, state.today_tasks, "今天还没有未完成的事务。");
  renderTaskList(elements.pendingList, state.pending_tasks, "当前没有未完成事务。");
  renderTaskList(elements.currentList, state.current_tasks, "当前没有处于提醒链路中的事务。");
  renderTaskList(elements.overdueList, state.overdue_tasks, "当前没有逾期事务。");
  startPolling();
}

function renderReply(text, kind = "normal") {
  elements.replyBox.className = `reply-box ${kind}`;
  elements.replyBox.textContent = text;
}

function startPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  pollTimer = window.setInterval(async () => {
    try {
      const state = await fetchState();
      renderState(state);
    } catch (error) {
      renderReply(error.message, "error");
    }
  }, pollSeconds * 1000);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatIso(value) {
  if (!value) {
    return "--";
  }
  return value.replace("T", " ").slice(0, 16);
}

async function handleSubmit(text) {
  const content = text.trim();
  if (!content) {
    renderReply("请输入一句明确的指令。", "error");
    return;
  }

  renderReply("处理中...", "muted");
  try {
    const result = await sendCommand(content);
    renderReply(result.reply_text, "success");
    renderState(result.state);
  } catch (error) {
    renderReply(error.message, "error");
  }
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await handleSubmit(elements.input.value);
  elements.input.value = "";
  elements.input.focus();
});

elements.helpButton.addEventListener("click", async () => {
  await handleSubmit("帮助");
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", async () => {
    await handleSubmit(button.dataset.command || "");
  });
});

window.addEventListener("load", async () => {
  renderReply("加载中...", "muted");
  try {
    const state = await fetchState();
    renderState(state);
    renderReply("可以开始输入事务指令了。", "muted");
  } catch (error) {
    renderReply(error.message, "error");
  }
});
