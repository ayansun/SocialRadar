// SocialRadar frontend.
// Plain JavaScript, no libraries. Every number and list on the page comes
// from the FastAPI backend through fetch().

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

const $ = (selector) => document.querySelector(selector);

const PLATFORM_NAMES = { bluesky: "Bluesky", threads: "Threads" };
const STATUS_NAMES = { new: "New", saved: "Saved", contacted: "Contacted", dismissed: "Dismissed" };
// Button text for moving a lead to a status.
const STATUS_ACTIONS = { new: "Restore", saved: "Save", contacted: "Mark contacted", dismissed: "Dismiss" };

/** Call the API and return parsed JSON. Throws an Error with a readable message. */
async function api(path, options = {}) {
  const config = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(path, config);
  } catch (error) {
    throw new Error("Cannot reach the server. Is it running?");
  }

  if (response.status === 204) return null; // No Content

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readError(data, response.status));
  return data;
}

/** Turn a FastAPI error body into one line of text. */
function readError(data, status) {
  if (data && typeof data.detail === "string") {
    return data.detail; // business error: {"detail": "Tracker not found"}
  }
  if (data && Array.isArray(data.detail)) {
    // validation error: {"detail": [{"loc": [...], "msg": "..."}]}
    return data.detail
      .map((item) => {
        const field = item.loc.filter((part) => part !== "body").join(".");
        const message = item.msg.replace(/^Value error, /, "");
        return field ? `${field}: ${message}` : message;
      })
      .join("; ");
  }
  return `Request failed (${status})`;
}

/** Escape text before putting it into innerHTML. */
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTime(isoString) {
  return new Date(isoString).toLocaleString([], {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "a, b\nc" -> ["a", "b", "c"] */
function parseList(text) {
  return text
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

// --- notice line (result of the last action) --------------------------------

let noticeTimer = null;

function showNotice(text, isError = false) {
  const notice = $("#notice");
  clearTimeout(noticeTimer);
  notice.textContent = text;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
  if (!isError) noticeTimer = setTimeout(clearNotice, 6000);
}

function clearNotice() {
  clearTimeout(noticeTimer);
  $("#notice").hidden = true;
}

// --- loading / error / empty states -----------------------------------------

function showLoading(container) {
  // Only on the first load, so the page does not flicker on every refresh.
  if (container.innerHTML === "") {
    container.innerHTML = '<p class="state">Loading…</p>';
  }
}

function showLoadError(container, error) {
  container.innerHTML = `<p class="state error">Could not load data<span>${escapeHtml(error.message)}</span></p>`;
}

/** A short title and, optionally, a second line that says what to do next. */
function emptyState(title, hint = "") {
  return `<p class="state">${title}${hint ? `<span>${hint}</span>` : ""}</p>`;
}

function showFormError(element, message) {
  element.textContent = message;
  element.hidden = message === "";
}

/**
 * Two-step confirmation for delete buttons instead of a popup.
 * First click: the button changes to "Confirm delete" and we return false.
 * Second click within 4 seconds: we return true.
 */
function confirmClick(button) {
  if (button.dataset.armed === "yes") return true;
  const originalText = button.textContent;
  button.dataset.armed = "yes";
  button.textContent = "Confirm delete";
  button.classList.add("danger-armed");
  setTimeout(() => {
    if (!button.isConnected) return;
    button.dataset.armed = "";
    button.textContent = originalText;
    button.classList.remove("danger-armed");
  }, 4000);
  return false;
}

/** Run an action that changes data, then refresh the current view. */
async function runAction(action, successMessage) {
  try {
    const result = await action();
    const message = typeof successMessage === "function" ? successMessage(result) : successMessage;
    if (message) showNotice(message);
  } catch (error) {
    showNotice(error.message, true);
  }
  await refresh();
}

// ---------------------------------------------------------------------------
// Shared rendering
// ---------------------------------------------------------------------------

function platformLabel(platform) {
  return `<span class="meta">${PLATFORM_NAMES[platform]}</span>`;
}

function demoTag(post) {
  return post.source === "demo" ? '<span class="tag tag-demo">demo</span>' : "";
}

/**
 * Escape the post text and wrap the matched keywords in <mark>.
 * Keywords are stored in lowercase with single spaces, so the search
 * ignores case and allows any whitespace between the words.
 */
function highlightKeywords(text, keywords) {
  if (keywords.length === 0) return escapeHtml(text);

  const patterns = keywords.map((keyword) =>
    keyword
      .split(" ")
      .map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .join("\\s+")
  );
  const regex = new RegExp(patterns.join("|"), "giu");

  let result = "";
  let position = 0;
  for (const found of text.matchAll(regex)) {
    result += escapeHtml(text.slice(position, found.index));
    result += `<mark>${escapeHtml(found[0])}</mark>`;
    position = found.index + found[0].length;
  }
  return result + escapeHtml(text.slice(position));
}

function postLink(post) {
  const label = post.source === "demo" ? "Demo link" : "Original post";
  return `<a href="${escapeHtml(post.url)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
}

/** One matched post. `withActions` adds the lead status buttons. */
function renderMatch(match, withActions) {
  const keywords = escapeHtml(match.matched_keywords.join(", "));
  const buttons = withActions
    ? match.allowed_statuses
        .map(
          (status) =>
            `<button type="button" data-action="set-status" data-id="${match.id}" data-status="${status}">${STATUS_ACTIONS[status]}</button>`
        )
        .join("")
    : "";

  return `
    <li class="lead-${match.status}">
      <div class="row-head">
        <span class="author">${escapeHtml(match.post.author)}</span>
        ${platformLabel(match.post.platform)}
        <span class="time">${formatTime(match.created_at)}</span>
        ${demoTag(match.post)}
        <span class="status status-${match.status}">${STATUS_NAMES[match.status]}</span>
      </div>
      <p class="post-text">${highlightKeywords(match.post.text, match.matched_keywords)}</p>
      <p class="match-line">${escapeHtml(match.tracker_name)}<span class="meta">${keywords}</span></p>
      <div class="actions ${withActions ? "" : "actions-bare"}">
        ${buttons}
        ${postLink(match.post)}
      </div>
    </li>`;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

async function loadDashboard() {
  const statsBox = $("#dashboard-stats");
  const recentBox = $("#dashboard-recent");
  showLoading(statsBox);

  let stats;
  let matches;
  try {
    // The pipeline needs every lead, not only the five recent ones.
    [stats, matches] = await Promise.all([api("/api/stats"), api("/api/matches")]);
  } catch (error) {
    showLoadError(statsBox, error);
    $("#dashboard-pipeline").innerHTML = "";
    recentBox.innerHTML = "";
    return;
  }

  $("#dashboard-pipeline").innerHTML = renderPipeline(matches);

  statsBox.innerHTML = `
    <dl class="stats">
      <div><dt>Trackers</dt><dd>${stats.trackers_total}</dd></div>
      <div><dt>Active trackers</dt><dd>${stats.trackers_active}</dd></div>
      <div><dt>Matches found</dt><dd>${stats.matches_total}</dd></div>
      <div><dt>Unread notifications</dt><dd>${stats.notifications_unread}</dd></div>
    </dl>`;

  if (stats.recent_matches.length === 0) {
    recentBox.innerHTML = emptyState(
      "No matches yet",
      'Create a tracker in <a href="#trackers">Trackers</a>, then import demo posts in <a href="#feed">Feed</a>'
    );
  } else {
    const items = stats.recent_matches.map((match) => renderMatch(match, false)).join("");
    recentBox.innerHTML = `<ul class="list">${items}</ul>`;
  }
}

/**
 * Lead pipeline: one stacked bar that shows how many leads are in each
 * status. The width of a segment is its share of all leads.
 */
function renderPipeline(matches) {
  if (matches.length === 0) return "";

  const statuses = ["new", "saved", "contacted", "dismissed"];
  const counts = {};
  statuses.forEach((status) => {
    counts[status] = matches.filter((match) => match.status === status).length;
  });

  const segments = statuses
    .filter((status) => counts[status] > 0)
    .map((status) => `<span class="seg-${status}" style="flex-grow: ${counts[status]}"></span>`)
    .join("");
  const legend = statuses
    .map(
      (status) => `
      <div>
        <dt><i class="seg-${status}"></i>${STATUS_NAMES[status]}</dt>
        <dd>${counts[status]}</dd>
      </div>`
    )
    .join("");

  return `
    <section class="panel pipeline">
      <div class="pipeline-head">
        <h2>Lead pipeline</h2>
        <span class="meta">${matches.length} leads</span>
      </div>
      <div class="pipeline-bar">${segments}</div>
      <dl class="pipeline-legend">${legend}</dl>
    </section>`;
}

// ---------------------------------------------------------------------------
// Trackers
// ---------------------------------------------------------------------------

let trackers = []; // last loaded list, used to fill the edit form
let editingTrackerId = null; // null = the form creates a new tracker

async function loadTrackers() {
  const box = $("#tracker-list");
  showLoading(box);

  try {
    trackers = await api("/api/trackers");
  } catch (error) {
    showLoadError(box, error);
    return;
  }

  if (trackers.length === 0) {
    box.innerHTML = emptyState("No trackers yet", "Use the form to create the first one");
    return;
  }

  box.innerHTML = `<ul class="list">${trackers.map(renderTracker).join("")}</ul>`;
}

function renderTracker(tracker) {
  const tags = (words, className) =>
    words.map((word) => `<span class="tag ${className}">${escapeHtml(word)}</span>`).join("");
  const platforms = tracker.platforms.map((platform) => PLATFORM_NAMES[platform]).join(", ");
  const excluded = tracker.excluded_keywords.length
    ? tags(tracker.excluded_keywords, "tag-excluded")
    : '<span class="meta">none</span>';
  const state = tracker.is_active
    ? '<span class="status status-active">Active</span>'
    : '<span class="status status-paused">Paused</span>';

  return `
    <li class="${tracker.is_active ? "" : "tracker-paused"}">
      <div class="row-head">
        <h3>${escapeHtml(tracker.name)}</h3>
        ${state}
      </div>
      <dl class="details">
        <dt>Keywords</dt><dd class="tags">${tags(tracker.keywords, "")}</dd>
        <dt>Excluded</dt><dd class="tags">${excluded}</dd>
        <dt>Platforms</dt><dd>${platforms}</dd>
        <dt>Matches</dt><dd class="number">${tracker.match_count}</dd>
      </dl>
      <div class="actions">
        <button type="button" data-action="edit-tracker" data-id="${tracker.id}">Edit</button>
        <button type="button" data-action="toggle-tracker" data-id="${tracker.id}">${tracker.is_active ? "Pause" : "Activate"}</button>
        <button type="button" data-action="delete-tracker" data-id="${tracker.id}">Delete</button>
      </div>
    </li>`;
}

function readTrackerForm() {
  const platforms = [...document.querySelectorAll('input[name="platform"]:checked')].map(
    (input) => input.value
  );
  return {
    name: $("#tracker-name").value,
    keywords: parseList($("#tracker-keywords").value),
    excluded_keywords: parseList($("#tracker-excluded").value),
    platforms: platforms,
    is_active: $("#tracker-active").checked,
  };
}

function startEditingTracker(tracker) {
  editingTrackerId = tracker.id;
  $("#tracker-name").value = tracker.name;
  $("#tracker-keywords").value = tracker.keywords.join("\n");
  $("#tracker-excluded").value = tracker.excluded_keywords.join("\n");
  document.querySelectorAll('input[name="platform"]').forEach((input) => {
    input.checked = tracker.platforms.includes(input.value);
  });
  $("#tracker-active").checked = tracker.is_active;

  $("#tracker-form-title").textContent = `Edit "${tracker.name}"`;
  $("#tracker-submit").textContent = "Save changes";
  $("#tracker-cancel").hidden = false;
  showFormError($("#tracker-form-error"), "");
  $("#tracker-form").scrollIntoView({ block: "nearest" });
  $("#tracker-name").focus();
}

function resetTrackerForm() {
  editingTrackerId = null;
  $("#tracker-form").reset();
  $("#tracker-form-title").textContent = "New tracker";
  $("#tracker-submit").textContent = "Create tracker";
  $("#tracker-cancel").hidden = true;
  showFormError($("#tracker-form-error"), "");
}

$("#tracker-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorBox = $("#tracker-form-error");
  const submitButton = $("#tracker-submit");
  const data = readTrackerForm();
  const isEditing = editingTrackerId !== null;

  submitButton.disabled = true;
  try {
    if (isEditing) {
      await api(`/api/trackers/${editingTrackerId}`, { method: "PATCH", body: data });
    } else {
      await api("/api/trackers", { method: "POST", body: data });
    }
  } catch (error) {
    // Validation and conflict errors are shown next to the form.
    showFormError(errorBox, error.message);
    submitButton.disabled = false;
    return;
  }
  submitButton.disabled = false;

  resetTrackerForm();
  showNotice(isEditing ? "Tracker updated, stored posts re-checked" : "Tracker created");
  await refresh();
});

$("#tracker-cancel").addEventListener("click", resetTrackerForm);

$("#tracker-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  const tracker = trackers.find((item) => item.id === id);
  if (!tracker) return;

  if (button.dataset.action === "edit-tracker") {
    startEditingTracker(tracker);
  }

  if (button.dataset.action === "toggle-tracker") {
    const body = { is_active: !tracker.is_active };
    await runAction(
      () => api(`/api/trackers/${id}`, { method: "PATCH", body: body }),
      tracker.is_active ? "Tracker paused" : "Tracker activated"
    );
  }

  if (button.dataset.action === "delete-tracker") {
    if (!confirmClick(button)) return;
    if (editingTrackerId === id) resetTrackerForm();
    await runAction(
      () => api(`/api/trackers/${id}`, { method: "DELETE" }),
      "Tracker deleted with its matches and notifications"
    );
  }
});

// ---------------------------------------------------------------------------
// Feed
// ---------------------------------------------------------------------------

async function loadFeed() {
  await Promise.all([loadTrackerFilter(), loadPosts()]);
  await loadMatches();
}

/** Fill the "Tracker" filter with the current trackers. */
async function loadTrackerFilter() {
  const select = $("#filter-tracker");
  const selected = select.value;
  try {
    const list = await api("/api/trackers");
    const options = list
      .map((tracker) => `<option value="${tracker.id}">${escapeHtml(tracker.name)}</option>`)
      .join("");
    select.innerHTML = `<option value="">All</option>${options}`;
    // Keep the previous choice if that tracker still exists.
    select.value = list.some((tracker) => String(tracker.id) === selected) ? selected : "";
  } catch (error) {
    // The match list below will show the error.
  }
}

async function loadMatches() {
  const box = $("#feed-list");
  showLoading(box);

  // Filters are sent to the API as query parameters.
  const params = new URLSearchParams();
  if ($("#filter-platform").value) params.set("platform", $("#filter-platform").value);
  if ($("#filter-tracker").value) params.set("tracker_id", $("#filter-tracker").value);
  if ($("#filter-status").value) params.set("status", $("#filter-status").value);

  let matches;
  try {
    matches = await api(`/api/matches?${params}`);
  } catch (error) {
    showLoadError(box, error);
    return;
  }

  if (matches.length === 0) {
    const hasFilters = params.toString() !== "";
    box.innerHTML = hasFilters
      ? emptyState("No matches for these filters")
      : emptyState(
          "No matches yet",
          "A match appears when a post contains a keyword of an active tracker"
        );
    return;
  }

  box.innerHTML = `<ul class="list">${matches.map((match) => renderMatch(match, true)).join("")}</ul>`;
}

async function loadPosts() {
  const box = $("#post-list");
  showLoading(box);

  let posts;
  try {
    posts = await api("/api/posts");
  } catch (error) {
    showLoadError(box, error);
    return;
  }

  if (posts.length === 0) {
    box.innerHTML = emptyState("No posts yet", "Import the demo posts or add one manually");
    return;
  }

  const rows = posts
    .map(
      (post) => `
      <tr>
        <td>${PLATFORM_NAMES[post.platform]}</td>
        <td>${escapeHtml(post.author)}</td>
        <td class="text-cell">${escapeHtml(post.text)}</td>
        <td class="meta">${post.source}</td>
        <td class="number">${post.match_count}</td>
        <td><button type="button" data-action="delete-post" data-id="${post.id}">Delete</button></td>
      </tr>`
    )
    .join("");

  box.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Platform</th><th>Author</th><th>Text</th><th>Source</th><th class="number">Matches</th><th></th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

["#filter-platform", "#filter-tracker", "#filter-status"].forEach((selector) => {
  $(selector).addEventListener("change", loadMatches);
});

$("#feed-list").addEventListener("click", async (event) => {
  const button = event.target.closest('button[data-action="set-status"]');
  if (!button) return;
  const status = button.dataset.status;
  await runAction(
    () => api(`/api/matches/${button.dataset.id}/status`, { method: "PATCH", body: { status: status } }),
    `Lead marked as ${STATUS_NAMES[status].toLowerCase()}`
  );
});

$("#post-list").addEventListener("click", async (event) => {
  const button = event.target.closest('button[data-action="delete-post"]');
  if (!button) return;
  if (!confirmClick(button)) return;
  await runAction(
    () => api(`/api/posts/${button.dataset.id}`, { method: "DELETE" }),
    "Post deleted with its matches and notifications"
  );
});

$("#seed-button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Importing…";
  await runAction(
    () => api("/api/demo/seed", { method: "POST" }),
    (result) =>
      `${result.imported} demo posts imported, ${result.skipped} already there, ${result.matches_created} new matches`
  );
  button.disabled = false;
  button.textContent = "Import demo posts";
});

$("#post-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorBox = $("#post-form-error");
  const data = {
    platform: $("#post-platform").value,
    author: $("#post-author").value,
    external_id: $("#post-external-id").value,
    text: $("#post-text").value,
    url: $("#post-url").value,
  };

  let result;
  try {
    result = await api("/api/posts", { method: "POST", body: data });
  } catch (error) {
    showFormError(errorBox, error.message);
    return;
  }

  showFormError(errorBox, "");
  $("#post-form").reset();
  showNotice(
    result.matches_created === 0
      ? "Post added, no active tracker matched it"
      : `Post added, ${result.matches_created} ${result.matches_created === 1 ? "match" : "matches"} created`
  );
  await refresh();
});

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

async function loadNotifications() {
  const box = $("#notification-list");
  showLoading(box);

  const filter = $("#filter-read").value;
  const query = filter === "" ? "" : `?is_read=${filter}`;

  let notifications;
  try {
    notifications = await api(`/api/notifications${query}`);
  } catch (error) {
    showLoadError(box, error);
    return;
  }

  if (notifications.length === 0) {
    box.innerHTML =
      filter === ""
        ? emptyState("No notifications yet", "One is created for every new match")
        : emptyState("No notifications for this filter");
    return;
  }

  box.innerHTML = `<ul class="list">${notifications.map(renderNotification).join("")}</ul>`;
}

function renderNotification(notification) {
  const isRead = notification.is_read;
  return `
    <li class="notification ${isRead ? "" : "unread"}">
      <div class="row-head">
        <span class="time">${formatTime(notification.created_at)}</span>
        ${demoTag(notification.post)}
        <span class="status ${isRead ? "status-read" : "status-unread"}">${isRead ? "Read" : "Unread"}</span>
      </div>
      <p class="notification-message">${escapeHtml(notification.message)}</p>
      <blockquote>${escapeHtml(notification.post.text)}</blockquote>
      <div class="actions">
        <button type="button" data-action="toggle-read" data-id="${notification.id}" data-read="${!isRead}">
          ${isRead ? "Mark as unread" : "Mark as read"}
        </button>
        <button type="button" data-action="delete-notification" data-id="${notification.id}">Delete</button>
        ${postLink(notification.post)}
      </div>
    </li>`;
}

$("#filter-read").addEventListener("change", loadNotifications);

$("#notification-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = button.dataset.id;

  if (button.dataset.action === "toggle-read") {
    const isRead = button.dataset.read === "true";
    await runAction(
      () => api(`/api/notifications/${id}`, { method: "PATCH", body: { is_read: isRead } }),
      ""
    );
  }

  if (button.dataset.action === "delete-notification") {
    if (!confirmClick(button)) return;
    await runAction(() => api(`/api/notifications/${id}`, { method: "DELETE" }), "Notification deleted");
  }
});

// ---------------------------------------------------------------------------
// Theme (light / dark)
// ---------------------------------------------------------------------------
// The theme is the data-theme attribute on <html>; style.css has a set of
// colours for each value. The choice is saved in the browser, so it stays
// after a reload. The first value is set by a small script in index.html.

const THEME_KEY = "socialradar-theme";

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  $("#theme-toggle").setAttribute("aria-label", label);
  $("#theme-toggle").title = label;
}

$("#theme-toggle").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (error) {
    // Storage can be blocked (private mode). The theme still changes for this visit.
  }
});

applyTheme(document.documentElement.dataset.theme || "dark");

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

const VIEWS = {
  dashboard: loadDashboard,
  trackers: loadTrackers,
  feed: loadFeed,
  notifications: loadNotifications,
};

function currentView() {
  const name = window.location.hash.replace("#", "");
  return VIEWS[name] ? name : "dashboard";
}

/** Show the unread count next to "Notifications" in the navigation. */
async function loadUnreadCount() {
  try {
    const stats = await api("/api/stats");
    $("#nav-unread").textContent = stats.notifications_unread > 0 ? stats.notifications_unread : "";
  } catch (error) {
    $("#nav-unread").textContent = "";
  }
}

/** Reload the data of the visible view. Called after every action. */
async function refresh() {
  await Promise.all([VIEWS[currentView()](), loadUnreadCount()]);
}

function showView() {
  const name = currentView();
  document.querySelectorAll(".view").forEach((section) => {
    section.hidden = section.id !== `view-${name}`;
  });
  document.querySelectorAll(".site-nav a").forEach((link) => {
    if (link.dataset.view === name) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
  clearNotice();
  refresh();
}

window.addEventListener("hashchange", showView);
showView();
