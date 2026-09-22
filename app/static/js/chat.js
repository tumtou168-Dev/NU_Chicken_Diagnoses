// Floating support chat popup. Polls the server every few seconds — no websocket dependency.
// The widget's DOM is rebuilt on every language switch (see lang-switch.js), so this must be
// safely re-runnable: initChatWidget() tears down any previous timers before wiring up the
// fresh elements.
function initChatWidget() {
  if (window.__chatPollTimer) clearInterval(window.__chatPollTimer);
  if (window.__chatUnreadTimer) clearInterval(window.__chatUnreadTimer);
  window.__chatPollTimer = null;
  window.__chatUnreadTimer = null;

  const widget = document.getElementById("chatWidget");
  if (!widget) return;

  const isStaff = widget.dataset.isStaff === "true";
  const csrfToken = widget.querySelector('input[name="csrf_token"]').value;

  const toggleBtn = document.getElementById("chatToggleBtn");
  const toggleIcon = document.getElementById("chatToggleIcon");
  const closeBtn = document.getElementById("chatCloseBtn");
  const backBtn = document.getElementById("chatBackBtn");
  const panel = document.getElementById("chatPanel");
  const panelTitle = document.getElementById("chatPanelTitle");
  const panelAvatar = document.getElementById("chatPanelAvatar");
  const panelIcon = document.getElementById("chatPanelIcon");
  const unreadBadge = document.getElementById("chatUnreadBadge");
  const threadList = document.getElementById("chatThreadList");
  const threadListEmpty = document.getElementById("chatThreadListEmpty");
  const conversation = document.getElementById("chatConversation");
  const messagesBox = document.getElementById("chatMessages");
  const messagesEmpty = document.getElementById("chatMessagesEmpty");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");

  const defaultTitle = panelTitle.textContent;
  let open = false;
  let activeUserId = isStaff ? null : parseInt(widget.dataset.userId, 10);

  function fetchJson(url, options) {
    return fetch(url, Object.assign({ headers: { "X-CSRFToken": csrfToken } }, options)).then((r) => r.json());
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  const CONTACT_LABELS = window.CHAT_I18N || {};

  function avatarInner(url, name) {
    if (url) return `<img src="${url}" alt="">`;
    return escapeHtml((name || "?").trim().charAt(0).toUpperCase());
  }

  function avatarHtml(url, name, extraClass) {
    return `<span class="chat-avatar ${extraClass || ""}">${avatarInner(url, name)}</span>`;
  }

  function renderContactCard(cr) {
    const rows = [
      ["bi-egg-fried", CONTACT_LABELS.flockSize, cr.flock_size],
      ["bi-calendar3", CONTACT_LABELS.flockAge, cr.flock_age_weeks],
      ["bi-shield-check", CONTACT_LABELS.vaccinated, cr.vaccinated_count],
      ["bi-heartbreak", CONTACT_LABELS.deaths, cr.death_count],
    ];
    let html = `<div class="chat-contact-card">`;
    html += `<div class="chat-contact-title"><i class="bi bi-clipboard2-pulse"></i>${escapeHtml(CONTACT_LABELS.title || "")}</div>`;
    html += `<div class="chat-contact-grid">`;
    for (const [icon, label, value] of rows) {
      html += `<div class="chat-contact-row"><span><i class="bi ${icon}"></i>${escapeHtml(label || "")}</span><strong>${value ?? "-"}</strong></div>`;
    }
    html += `</div>`;
    if (cr.image_url) {
      html += `<a href="${cr.image_url}" target="_blank" rel="noopener"><img class="chat-contact-image" src="${cr.image_url}" alt=""></a>`;
    }
    if (cr.case_id) {
      html += `<a class="chat-contact-link" href="/expert-system/cases/${cr.case_id}" target="_blank" rel="noopener"><i class="bi bi-file-earmark-medical"></i>${escapeHtml(CONTACT_LABELS.viewCase || "")}</a>`;
    }
    html += `</div>`;
    return html;
  }

  let lastMessagesKey = null;

  function renderMessages(items, force) {
    const key = activeUserId + ":" + items.map((m) => m.id).join(",");
    if (!force && key === lastMessagesKey) return;   // nothing new — don't touch the DOM or scroll position
    lastMessagesKey = key;

    // Only auto-scroll if the reader was already at (or near) the bottom, or this is a fresh open/send —
    // a background poll should never yank someone back down while they're reading older messages.
    const nearBottom = messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight < 80;
    const prevScrollTop = messagesBox.scrollTop;

    messagesEmpty.hidden = items.length !== 0;
    messagesBox.querySelectorAll(".chat-bubble, .chat-date-divider").forEach((el) => el.remove());
    let lastDate = null;
    for (const m of items) {
      // "YYYY-MM-DD HH:MM" -> group by day with a divider, show only the time on each bubble.
      const [date, time] = [m.created_at.slice(0, 10), m.created_at.slice(11)];
      if (date !== lastDate) {
        lastDate = date;
        const divider = document.createElement("div");
        divider.className = "chat-date-divider";
        divider.innerHTML = `<span>${escapeHtml(date)}</span>`;
        messagesBox.appendChild(divider);
      }

      const bubble = document.createElement("div");
      bubble.className = "chat-bubble " + (m.is_mine ? "chat-bubble-mine" : "chat-bubble-theirs") + (m.contact_request ? " chat-bubble-card" : "");
      let body = m.contact_request
        ? renderContactCard(m.contact_request) + (m.body && m.body !== "-" ? `<div class="chat-bubble-body">${escapeHtml(m.body)}</div>` : "")
        : `<div class="chat-bubble-body">${escapeHtml(m.body)}</div>`;
      // Show who sent it (with photo) for anything that isn't my own message.
      const senderRow = !m.is_mine
        ? `<div class="chat-bubble-sender">${avatarHtml(m.sender_avatar_url, m.sender_name, "chat-avatar-xs")}<span>${escapeHtml(m.sender_name)}</span>${m.sender_role ? `<span class="chat-role-badge">${escapeHtml(m.sender_role)}</span>` : ""}</div>`
        : "";
      bubble.innerHTML = senderRow + body + `<div class="chat-bubble-time">${time}</div>`;
      messagesBox.appendChild(bubble);
    }
    messagesBox.scrollTop = (force || nearBottom) ? messagesBox.scrollHeight : prevScrollTop;
  }

  function loadMessages(force) {
    if (!activeUserId) return;
    const url = isStaff ? `/chat/api/messages?user_id=${activeUserId}` : "/chat/api/messages";
    fetchJson(url).then((data) => {
      if (data.messages) renderMessages(data.messages, force);
      refreshUnreadBadge();
    });
  }

  function refreshUnreadBadge() {
    fetchJson("/chat/api/unread-count").then((data) => {
      const count = data.count || 0;
      unreadBadge.hidden = count === 0;
      unreadBadge.textContent = count > 99 ? "99+" : String(count);
    });
  }

  let lastThreadsKey = null;

  function loadThreads() {
    fetchJson("/chat/api/threads").then((data) => {
      const threads = data.threads || [];
      const key = threads.map((t) => `${t.user_id}:${t.last_at}:${t.unread_count}`).join("|");
      if (key === lastThreadsKey) return;   // nothing changed — don't rebuild and reset scroll
      lastThreadsKey = key;

      threadListEmpty.hidden = threads.length !== 0;
      threadList.querySelectorAll(".chat-thread-item").forEach((el) => el.remove());
      for (const t of threads) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "chat-thread-item";
        item.innerHTML =
          avatarHtml(t.avatar_url, t.full_name, "chat-avatar-sm") +
          `<div class="chat-thread-text">` +
          `<div class="chat-thread-name">${escapeHtml(t.full_name)}${t.unread_count ? `<span class="chat-thread-badge">${t.unread_count}</span>` : ""}</div>` +
          `<div class="chat-thread-preview">${escapeHtml(t.last_message)}</div>` +
          `</div>`;
        item.addEventListener("click", () => openThread(t.user_id, t.full_name, t.avatar_url));
        threadList.appendChild(item);
      }
    });
  }

  function openThread(userId, name, avatarUrl) {
    activeUserId = userId;
    panelTitle.textContent = name;
    if (panelAvatar) {
      panelAvatar.innerHTML = avatarInner(avatarUrl, name);
      panelAvatar.hidden = false;
    }
    if (panelIcon) panelIcon.hidden = true;
    threadList.hidden = true;
    conversation.hidden = false;
    backBtn.hidden = false;
    loadMessages(true);
    input.focus();
  }

  function showThreadList() {
    activeUserId = null;
    panelTitle.textContent = defaultTitle;
    if (panelAvatar) panelAvatar.hidden = true;
    if (panelIcon) panelIcon.hidden = false;
    conversation.hidden = true;
    threadList.hidden = false;
    backBtn.hidden = true;
    loadThreads();
  }

  function startPolling() {
    stopPolling();
    window.__chatPollTimer = setInterval(() => {
      if (isStaff && !activeUserId) {
        loadThreads();
      } else {
        loadMessages();
      }
    }, 4000);
  }

  function stopPolling() {
    if (window.__chatPollTimer) clearInterval(window.__chatPollTimer);
    window.__chatPollTimer = null;
  }

  function openPanel() {
    open = true;
    panel.hidden = false;
    toggleBtn.classList.add("is-open");
    if (toggleIcon) toggleIcon.className = "bi bi-x-lg";
    if (isStaff) {
      showThreadList();
    } else {
      loadMessages(true);
    }
    startPolling();
  }

  function closePanel() {
    open = false;
    panel.hidden = true;
    toggleBtn.classList.remove("is-open");
    if (toggleIcon) toggleIcon.className = "bi bi-chat-square-text-fill";
    stopPolling();
  }

  toggleBtn.addEventListener("click", () => (open ? closePanel() : openPanel()));
  closeBtn.addEventListener("click", closePanel);
  if (backBtn) backBtn.addEventListener("click", showThreadList);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const body = input.value.trim();
    if (!body || !activeUserId) return;
    const params = new URLSearchParams({ body });
    if (isStaff) params.set("user_id", activeUserId);
    input.value = "";
    fetchJson("/chat/api/send", { method: "POST", body: params }).then(() => {
      loadMessages(true);
      if (isStaff) loadThreads();
    });
  });

  refreshUnreadBadge();
  window.__chatUnreadTimer = setInterval(refreshUnreadBadge, 15000);

  // A "contact the doctor" submission redirects back here with ?open_chat=1.
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("open_chat") === "1") {
    openPanel();
    urlParams.delete("open_chat");
    const clean = window.location.pathname + (urlParams.toString() ? `?${urlParams}` : "") + window.location.hash;
    window.history.replaceState({}, "", clean);
  }
}

function destroyChatWidget() {
  if (window.__chatPollTimer) clearInterval(window.__chatPollTimer);
  if (window.__chatUnreadTimer) clearInterval(window.__chatUnreadTimer);
  window.__chatPollTimer = null;
  window.__chatUnreadTimer = null;
}

window.ChatWidget = { init: initChatWidget, destroy: destroyChatWidget };
window.onReady(initChatWidget);
