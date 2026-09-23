// Floating support chat popup. Polls the server every few seconds — no websocket dependency.
// The widget's DOM is rebuilt on every language switch (see lang-switch.js), so this must be
// safely re-runnable: initChatWidget() tears down any previous timers before wiring up the
// fresh elements.
// Phone photos routinely exceed the server's 2 MB image cap, so large pictures are downscaled
// and re-encoded as JPEG in the browser before upload. Small files pass through untouched.
const CHAT_IMAGE_MAX_BYTES = 2 * 1024 * 1024;
const CHAT_IMAGE_MAX_SIDE = 1600;

function shrinkImageFile(file) {
  if (!file || file.size <= CHAT_IMAGE_MAX_BYTES) return Promise.resolve(file);
  // Always settles: any failure (or a stalled decode) falls back to the original file, and the
  // server shrinks it instead.
  return new Promise((resolve) => {
    let settled = false;
    const done = (result) => {
      if (settled) return;
      settled = true;
      resolve(result || file);
    };
    setTimeout(() => done(file), 10000);
    try {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        try {
          URL.revokeObjectURL(url);
          const scale = Math.min(1, CHAT_IMAGE_MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
          const canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
          canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
          const ctx = canvas.getContext("2d");
          ctx.fillStyle = "#fff"; // transparent PNG areas would otherwise turn black in JPEG
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const tryQuality = (q) => {
            canvas.toBlob((blob) => {
              if (!blob) return done(file);
              if (blob.size > CHAT_IMAGE_MAX_BYTES && q > 0.5) return tryQuality(q - 0.15);
              const name = (file.name || "photo").replace(/\.[^.]+$/, "") + ".jpg";
              done(new File([blob], name, { type: "image/jpeg" }));
            }, "image/jpeg", q);
          };
          tryQuality(0.85);
        } catch (err) {
          console.error("Image shrink failed", err);
          done(file);
        }
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        done(file);
      };
      img.src = url;
    } catch (err) {
      console.error("Image shrink failed", err);
      done(file);
    }
  });
}
window.shrinkImageFile = shrinkImageFile;

// File inputs marked data-shrink-image (e.g. the "contact the doctor" form) get the same treatment.
document.addEventListener("change", (e) => {
  const input = e.target;
  if (!(input instanceof HTMLInputElement) || !input.hasAttribute("data-shrink-image")) return;
  const file = input.files && input.files[0];
  if (!file || file.size <= CHAT_IMAGE_MAX_BYTES || typeof DataTransfer === "undefined") return;
  shrinkImageFile(file).then((smaller) => {
    if (smaller === file) return;
    const dt = new DataTransfer();
    dt.items.add(smaller);
    input.files = dt.files;
  });
});

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
  const panelPresence = document.getElementById("chatPanelPresence");
  const panelSubtitle = document.getElementById("chatPanelSubtitle");
  const unreadBadge = document.getElementById("chatUnreadBadge");
  const threadList = document.getElementById("chatThreadList");
  const threadListEmpty = document.getElementById("chatThreadListEmpty");
  const conversation = document.getElementById("chatConversation");
  const messagesBox = document.getElementById("chatMessages");
  const messagesEmpty = document.getElementById("chatMessagesEmpty");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const micBtn = document.getElementById("chatMicBtn");
  const recordingBar = document.getElementById("chatRecordingBar");
  const recordingTime = document.getElementById("chatRecordingTime");
  const recordingCancelBtn = document.getElementById("chatRecordingCancel");
  const recordingSendBtn = document.getElementById("chatRecordingSend");
  const attachBtn = document.getElementById("chatAttachBtn");
  const imageInput = document.getElementById("chatImageInput");
  const deleteDialog = document.getElementById("chatDeleteDialog");
  const deleteEveryoneBtn = document.getElementById("chatDeleteEveryoneBtn");
  const deleteMeBtn = document.getElementById("chatDeleteMeBtn");
  const deleteCancelBtn = document.getElementById("chatDeleteCancelBtn");
  const imageDialog = document.getElementById("chatImageDialog");
  const imageDialogTitle = document.getElementById("chatImageDialogTitle");
  const imagePreviews = document.getElementById("chatImagePreviews");
  const imageCaption = document.getElementById("chatImageCaption");
  const imageAddBtn = document.getElementById("chatImageAddBtn");
  const imageCancelBtn = document.getElementById("chatImageCancelBtn");
  const imageSendBtn = document.getElementById("chatImageSendBtn");

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

  // Green dot on an avatar for someone active in the last couple of minutes.
  function presenceAvatarHtml(url, name, extraClass, online) {
    const title = online ? ` title="${escapeHtml(CONTACT_LABELS.online || "Online")}"` : "";
    return `<span class="chat-presence${online ? " is-online" : ""}"${title}>${avatarHtml(url, name, extraClass)}</span>`;
  }

  function setPeerOnline(online) {
    if (panelPresence) panelPresence.classList.toggle("is-online", !!online);
    if (panelSubtitle) panelSubtitle.textContent = online ? panelSubtitle.dataset.online : panelSubtitle.dataset.offline;
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
    // Include the deleted flag so a "delete for everyone" from the other side re-renders on the next poll.
    const key = activeUserId + ":" + items.map((m) => m.id + (m.is_deleted ? "d" : "")).join(",");
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
      bubble.className = "chat-bubble " + (m.is_mine ? "chat-bubble-mine" : "chat-bubble-theirs") +
        (m.contact_request ? " chat-bubble-card" : "") + (m.image_url ? " chat-bubble-photo" : "") + (m.caption ? " has-caption" : "");
      bubble.dataset.messageId = m.id;
      let body;
      if (m.is_deleted) {
        body = `<div class="chat-bubble-deleted"><i class="bi bi-slash-circle"></i>${escapeHtml(m.body)}</div>`;
      } else if (m.contact_request) {
        body = renderContactCard(m.contact_request) + (m.body && m.body !== "-" ? `<div class="chat-bubble-body">${escapeHtml(m.body)}</div>` : "");
      } else if (m.image_url) {
        body = `<a href="${m.image_url}" target="_blank" rel="noopener"><img class="chat-bubble-image" src="${m.image_url}" alt=""></a>` +
          (m.caption ? `<div class="chat-bubble-caption">${escapeHtml(m.caption)}</div>` : "");
      } else if (m.audio_url) {
        const fallbackTime = m.audio_duration ? formatElapsed(m.audio_duration) : "0:00";
        body =
          `<div class="voice-player">` +
          `<button type="button" class="voice-play-btn"><i class="bi bi-play-fill"></i></button>` +
          `<div class="voice-progress"><div class="voice-progress-track"></div><div class="voice-progress-fill"></div><div class="voice-progress-handle"></div></div>` +
          `<span class="voice-time">${fallbackTime}</span>` +
          `<audio preload="metadata" src="${m.audio_url}"></audio>` +
          `</div>`;
      } else {
        body = `<div class="chat-bubble-body">${escapeHtml(m.body)}</div>`;
      }
      // Show who sent it (with photo) for anything that isn't my own message.
      const senderRow = !m.is_mine
        ? `<div class="chat-bubble-sender">${avatarHtml(m.sender_avatar_url, m.sender_name, "chat-avatar-xs")}<span>${escapeHtml(m.sender_name)}</span>${m.sender_role ? `<span class="chat-role-badge">${escapeHtml(m.sender_role)}</span>` : ""}</div>`
        : "";
      const editedTag = m.is_edited && !m.is_deleted ? `<span class="chat-bubble-edited-tag">(${escapeHtml(CONTACT_LABELS.editedTag || "edited")})</span>` : "";
      // Every message can at least be deleted "for me"; can_delete means "for everyone" is also offered.
      const actions =
        `<div class="chat-bubble-actions">` +
        (m.can_edit ? `<button type="button" class="chat-bubble-action-btn chat-bubble-edit-btn" title="${escapeHtml(CONTACT_LABELS.editTitle || "Edit")}"><i class="bi bi-pencil-fill"></i></button>` : "") +
        `<button type="button" class="chat-bubble-action-btn is-danger chat-bubble-delete-btn" title="${escapeHtml(CONTACT_LABELS.deleteTitle || "Delete")}"><i class="bi bi-trash3-fill"></i></button>` +
        `</div>`;
      const timeHtml = `<div class="chat-bubble-time">${time}${editedTag}</div>`;
      const timeOverlay = m.image_url && !m.caption;
      bubble.innerHTML = actions + senderRow + body + (timeOverlay ? "" : timeHtml);
      if (timeOverlay) {
        const overlay = document.createElement("div");
        overlay.className = "chat-bubble-photo-time";
        overlay.textContent = time;
        bubble.appendChild(overlay);
      }
      messagesBox.appendChild(bubble);
      if (m.audio_url && !m.is_deleted) wireVoicePlayer(bubble.querySelector(".voice-player"));
      if (m.can_edit) {
        const editBtn = bubble.querySelector(".chat-bubble-edit-btn");
        if (editBtn) editBtn.addEventListener("click", () => startEditingBubble(bubble, m));
      }
      bubble.querySelector(".chat-bubble-delete-btn").addEventListener("click", () => openDeleteDialog(m));
    }
    const stickToBottom = force || nearBottom;
    messagesBox.scrollTop = stickToBottom ? messagesBox.scrollHeight : prevScrollTop;
    if (stickToBottom) {
      // Photos have no height until they load, so the scroll above lands short of the real
      // bottom — follow each one down as it arrives.
      messagesBox.querySelectorAll(".chat-bubble img").forEach((img) => {
        if (!img.complete) img.addEventListener("load", () => { messagesBox.scrollTop = messagesBox.scrollHeight; }, { once: true });
      });
    }
  }

  // One shared "now playing" ref so starting a new clip pauses whichever one was already playing.
  let activeVoiceAudio = null;

  function wireVoicePlayer(player) {
    const audio = player.querySelector("audio");
    const playBtn = player.querySelector(".voice-play-btn");
    const icon = playBtn.querySelector("i");
    const fill = player.querySelector(".voice-progress-fill");
    const handle = player.querySelector(".voice-progress-handle");
    const progress = player.querySelector(".voice-progress");
    const timeLabel = player.querySelector(".voice-time");
    const fallbackTime = timeLabel.textContent;

    function setProgress(ratio) {
      const pct = Math.max(0, Math.min(1, ratio)) * 100;
      fill.style.width = pct + "%";
      handle.style.left = pct + "%";
    }

    audio.addEventListener("play", () => {
      if (activeVoiceAudio && activeVoiceAudio !== audio) activeVoiceAudio.pause();
      activeVoiceAudio = audio;
      icon.className = "bi bi-pause-fill";
    });
    audio.addEventListener("pause", () => {
      icon.className = "bi bi-play-fill";
    });
    audio.addEventListener("ended", () => {
      icon.className = "bi bi-play-fill";
      setProgress(0);
      timeLabel.textContent = fallbackTime;
    });
    audio.addEventListener("timeupdate", () => {
      if (!audio.duration) return;
      setProgress(audio.currentTime / audio.duration);
      timeLabel.textContent = formatElapsed(Math.round(audio.currentTime));
    });
    audio.addEventListener("loadedmetadata", () => {
      if (isFinite(audio.duration)) timeLabel.textContent = formatElapsed(Math.round(audio.duration));
    });

    playBtn.addEventListener("click", () => {
      if (audio.paused) audio.play(); else audio.pause();
    });

    function seekFromEvent(e) {
      const rect = progress.getBoundingClientRect();
      const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
      const ratio = Math.max(0, Math.min(1, x / rect.width));
      if (audio.duration) audio.currentTime = ratio * audio.duration;
      setProgress(ratio);
    }
    progress.addEventListener("click", seekFromEvent);
  }

  function startEditingBubble(bubble, m) {
    const bodyEl = bubble.querySelector(".chat-bubble-body");
    if (!bodyEl) return;

    const wrapper = document.createElement("div");
    wrapper.className = "chat-bubble-edit-form";
    wrapper.innerHTML =
      `<textarea class="chat-bubble-edit-input" rows="2" maxlength="1000"></textarea>` +
      `<div class="chat-bubble-edit-actions">` +
      `<button type="button" class="chat-bubble-edit-cancel">${escapeHtml(CONTACT_LABELS.cancel || "Cancel")}</button>` +
      `<button type="button" class="chat-bubble-edit-save">${escapeHtml(CONTACT_LABELS.save || "Save")}</button>` +
      `</div>`;
    const textarea = wrapper.querySelector("textarea");
    textarea.value = m.body;
    bodyEl.replaceWith(wrapper);
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    function cancelEdit() {
      loadMessages(true);
    }
    function saveEdit() {
      const value = textarea.value.trim();
      if (!value) return;
      const params = new URLSearchParams({ message_id: m.id, body: value });
      fetchJson("/chat/api/edit", { method: "POST", body: params }).then((data) => {
        if (data.error) return;
        loadMessages(true);
      });
    }
    wrapper.querySelector(".chat-bubble-edit-cancel").addEventListener("click", cancelEdit);
    wrapper.querySelector(".chat-bubble-edit-save").addEventListener("click", saveEdit);
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        saveEdit();
      } else if (e.key === "Escape") {
        cancelEdit();
      }
    });
  }

  let pendingDeleteId = null;

  function openDeleteDialog(m) {
    pendingDeleteId = m.id;
    deleteEveryoneBtn.hidden = !m.can_delete;
    deleteDialog.hidden = false;
  }

  function closeDeleteDialog() {
    pendingDeleteId = null;
    deleteDialog.hidden = true;
  }

  function deleteMessage(scope) {
    if (!pendingDeleteId) return;
    const params = new URLSearchParams({ message_id: pendingDeleteId, scope: scope });
    closeDeleteDialog();
    fetchJson("/chat/api/delete", { method: "POST", body: params }).then(() => {
      loadMessages(true);
      if (isStaff) loadThreads();
    });
  }

  deleteEveryoneBtn.addEventListener("click", () => deleteMessage("everyone"));
  deleteMeBtn.addEventListener("click", () => deleteMessage("me"));
  deleteCancelBtn.addEventListener("click", closeDeleteDialog);
  deleteDialog.addEventListener("click", (e) => { if (e.target === deleteDialog) closeDeleteDialog(); });

  function loadMessages(force) {
    if (!activeUserId) return;
    const url = isStaff ? `/chat/api/messages?user_id=${activeUserId}` : "/chat/api/messages";
    fetchJson(url).then((data) => {
      if (data.messages) renderMessages(data.messages, force);
      if ("peer_online" in data) setPeerOnline(data.peer_online);
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
      const key = threads.map((t) => `${t.user_id}:${t.last_at}:${t.unread_count}:${t.is_online}`).join("|");
      if (key === lastThreadsKey) return;   // nothing changed — don't rebuild and reset scroll
      lastThreadsKey = key;

      threadListEmpty.hidden = threads.length !== 0;
      threadList.querySelectorAll(".chat-thread-item").forEach((el) => el.remove());
      for (const t of threads) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "chat-thread-item";
        item.innerHTML =
          presenceAvatarHtml(t.avatar_url, t.full_name, "chat-avatar-sm", t.is_online) +
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
    if (mediaRecorder) finishRecording(false);
    activeUserId = null;
    panelTitle.textContent = defaultTitle;
    if (panelAvatar) panelAvatar.hidden = true;
    if (panelIcon) panelIcon.hidden = false;
    setPeerOnline(false);
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
    if (mediaRecorder) finishRecording(false);
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

  // --- Voice messages -------------------------------------------------
  const MAX_RECORDING_SECONDS = 120;
  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];
  let recordingStartedAt = null;
  let recordingTimer = null;
  let recordingSendRequested = false;

  function formatElapsed(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function showRecordingBar(show) {
    recordingBar.hidden = !show;
    form.hidden = show;
  }

  function stopRecordingUI() {
    if (recordingTimer) clearInterval(recordingTimer);
    recordingTimer = null;
    if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
    mediaRecorder = null;
    micBtn.classList.remove("is-recording");
    showRecordingBar(false);
  }

  function uploadRecording(blob) {
    if (!activeUserId) return;
    const duration = Math.round((Date.now() - recordingStartedAt) / 1000);
    const ext = (blob.type.split("/")[1] || "webm").split(";")[0];
    const fd = new FormData();
    fd.append("audio", blob, `voice.${ext}`);
    fd.append("duration", duration);
    if (isStaff) fd.append("user_id", activeUserId);
    fetch("/chat/api/send-audio", { method: "POST", headers: { "X-CSRFToken": csrfToken }, body: fd })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          alert(typeof data.error === "string" ? data.error : (CONTACT_LABELS.audioSendError || "Failed to send."));
          return;
        }
        loadMessages(true);
        if (isStaff) loadThreads();
      })
      .catch(() => alert(CONTACT_LABELS.audioSendError || "Failed to send."));
  }

  function startRecording() {
    if (!activeUserId || mediaRecorder) return;
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      mediaStream = stream;
      audioChunks = [];
      recordingSendRequested = false;
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.addEventListener("dataavailable", (e) => {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      });
      mediaRecorder.addEventListener("stop", () => {
        const type = mediaRecorder ? mediaRecorder.mimeType : "audio/webm";
        const blob = new Blob(audioChunks, { type });
        audioChunks = [];
        if (recordingSendRequested && blob.size > 0) uploadRecording(blob);
        stopRecordingUI();
      });
      mediaRecorder.start();
      recordingStartedAt = Date.now();
      micBtn.classList.add("is-recording");
      showRecordingBar(true);
      recordingTime.textContent = "0:00";
      recordingTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
        recordingTime.textContent = formatElapsed(elapsed);
        if (elapsed >= MAX_RECORDING_SECONDS) {
          recordingSendRequested = true;
          mediaRecorder.stop();
        }
      }, 250);
    }).catch(() => {
      alert(CONTACT_LABELS.micPermission || "Please allow microphone access.");
    });
  }

  function finishRecording(send) {
    if (!mediaRecorder) return;
    recordingSendRequested = send;
    if (mediaRecorder.state !== "inactive") mediaRecorder.stop();
    else stopRecordingUI();
  }

  micBtn.addEventListener("click", startRecording);
  recordingCancelBtn.addEventListener("click", () => finishRecording(false));
  recordingSendBtn.addEventListener("click", () => finishRecording(true));

  // --- Images: pick / drop / paste -> preview dialog with caption -> send -------
  const MAX_IMAGES_PER_SEND = 10;
  const IMAGE_TYPE_RE = /^image\/(png|jpe?g|webp)$/;
  let pendingImages = [];   // [{ file, url }]
  let sendingImages = false;

  function formatLabel(template, n) {
    return (template || "").replace("{n}", n);
  }

  function renderImagePreviews() {
    const count = pendingImages.length;
    imageDialogTitle.textContent = count > 1
      ? formatLabel(CONTACT_LABELS.sendImages || "Send {n} images", count)
      : (CONTACT_LABELS.sendImage || "Send an image");
    imagePreviews.classList.toggle("is-single", count === 1);
    imagePreviews.innerHTML = "";
    pendingImages.forEach((item, index) => {
      const tile = document.createElement("div");
      tile.className = "chat-image-preview";
      tile.innerHTML =
        `<img src="${item.url}" alt="">` +
        `<button type="button" class="chat-image-preview-remove" title="${escapeHtml(CONTACT_LABELS.removeImage || "Remove")}"><i class="bi bi-x-lg"></i></button>`;
      tile.querySelector("button").addEventListener("click", () => {
        URL.revokeObjectURL(item.url);
        pendingImages.splice(index, 1);
        if (pendingImages.length) renderImagePreviews();
        else closeImageDialog();
      });
      imagePreviews.appendChild(tile);
    });
    imageAddBtn.hidden = count >= MAX_IMAGES_PER_SEND;
  }

  function addPendingImages(files) {
    const images = Array.from(files || []).filter((f) => IMAGE_TYPE_RE.test(f.type));
    if (!images.length) {
      if (files && files.length) alert(CONTACT_LABELS.imageTypeError || "Only JPG, PNG or WebP images can be sent.");
      return;
    }
    const room = MAX_IMAGES_PER_SEND - pendingImages.length;
    if (images.length > room) alert(formatLabel(CONTACT_LABELS.tooManyImages || "You can send up to {n} images at a time.", MAX_IMAGES_PER_SEND));
    images.slice(0, Math.max(0, room)).forEach((file) => pendingImages.push({ file, url: URL.createObjectURL(file) }));
    if (!pendingImages.length) return;
    renderImagePreviews();
    imageDialog.hidden = false;
    imageCaption.focus();
  }

  function closeImageDialog() {
    if (sendingImages) return;
    pendingImages.forEach((item) => URL.revokeObjectURL(item.url));
    pendingImages = [];
    imagePreviews.innerHTML = "";
    imageCaption.value = "";
    imageDialog.hidden = true;
  }

  function uploadImage(file, caption) {
    return shrinkImageFile(file).then((upload) => {
      const fd = new FormData();
      fd.append("image", upload);
      if (caption) fd.append("caption", caption);
      if (isStaff) fd.append("user_id", activeUserId);
      return fetch("/chat/api/send-image", { method: "POST", headers: { "X-CSRFToken": csrfToken }, body: fd })
        .then((r) => r.json().catch(() => ({ error: true })))
        .then((data) => {
          if (data.error) throw new Error(typeof data.error === "string" ? data.error : "");
        });
    });
  }

  function sendPendingImages() {
    if (!pendingImages.length || !activeUserId || sendingImages) return;
    const files = pendingImages.map((item) => item.file);
    const caption = imageCaption.value.trim();
    sendingImages = true;
    imageSendBtn.disabled = true;
    // One request per image keeps each upload under the server's request-size cap, and sending
    // them in order keeps them in order in the chat. The caption rides on the last one so it
    // reads underneath the set.
    let chain = Promise.resolve();
    files.forEach((file, i) => {
      chain = chain.then(() => uploadImage(file, i === files.length - 1 ? caption : ""));
    });
    chain
      .then(() => {
        sendingImages = false;
        closeImageDialog();
      })
      .catch((err) => {
        console.error("Image upload failed", err);
        sendingImages = false;
        alert(err.message || CONTACT_LABELS.imageSendError || "Failed to send.");
      })
      .finally(() => {
        imageSendBtn.disabled = false;
        loadMessages(true);
        if (isStaff) loadThreads();
      });
  }

  attachBtn.addEventListener("click", () => imageInput.click());
  imageAddBtn.addEventListener("click", () => imageInput.click());
  imageInput.addEventListener("change", () => {
    const files = Array.from(imageInput.files);
    imageInput.value = "";
    addPendingImages(files);
  });
  imageCancelBtn.addEventListener("click", closeImageDialog);
  imageSendBtn.addEventListener("click", sendPendingImages);
  imageCaption.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); sendPendingImages(); }
    if (e.key === "Escape") { e.preventDefault(); closeImageDialog(); }
  });
  imageDialog.addEventListener("click", (e) => { if (e.target === imageDialog) closeImageDialog(); });

  // Paste a screenshot / copied image straight into the message box.
  input.addEventListener("paste", (e) => {
    const files = Array.from((e.clipboardData && e.clipboardData.files) || []).filter((f) => IMAGE_TYPE_RE.test(f.type));
    if (!files.length) return;
    e.preventDefault();
    addPendingImages(files);
  });

  // Drag & drop an image from the desktop / file manager onto the open conversation.
  const isFileDrag = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
  let dragDepth = 0;
  conversation.addEventListener("dragenter", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth += 1;
    conversation.classList.add("is-dragover");
  });
  conversation.addEventListener("dragover", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  });
  conversation.addEventListener("dragleave", () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) conversation.classList.remove("is-dragover");
  });
  conversation.addEventListener("drop", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth = 0;
    conversation.classList.remove("is-dragover");
    addPendingImages(e.dataTransfer.files);
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
