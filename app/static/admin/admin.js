const state = {
  token: localStorage.getItem("be_admin_token"),
  username: localStorage.getItem("be_admin_username") || "",
  view: "dashboard",
  userPage: 1,
  voicePage: 1,
  users: new Map(),
  voices: new Map(),
  audioUrl: null,
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
const formatDate = (value) => new Intl.DateTimeFormat("vi-VN", {dateStyle:"short", timeStyle:"short"}).format(new Date(value));

async function api(path, options = {}) {
  const headers = {...(options.headers || {}), Authorization: `Bearer ${state.token}`};
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {...options, headers});
  if (response.status === 401 || response.status === 403) {
    if (response.status === 401) logout();
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.message || "Bạn không có quyền thực hiện thao tác này.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const details = Array.isArray(body.detail) ? body.detail.map(item => item.msg).join(", ") : body.detail;
    throw new Error(details || body.message || "Yêu cầu không thành công.");
  }
  if (response.status === 204) return null;
  return response.headers.get("content-type")?.includes("application/json") ? response.json() : response;
}

function showToast(message, error = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 3500);
}

function logout() {
  state.token = null;
  localStorage.removeItem("be_admin_token");
  localStorage.removeItem("be_admin_username");
  $("#appView").hidden = true;
  $("#loginView").hidden = false;
}

async function login(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const error = $("#loginError");
  error.textContent = "";
  try {
    const response = await fetch("/api/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({username:form.get("username"), password:form.get("password")})});
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Đăng nhập không thành công.");
    state.token = body.access_token;
    state.username = body.user.username;
    await api("/api/admin/dashboard");
    localStorage.setItem("be_admin_token", state.token);
    localStorage.setItem("be_admin_username", state.username);
    showApp();
  } catch (err) {
    state.token = null;
    error.textContent = err.message === "Administrator access required" ? "Tài khoản không có quyền quản trị." : err.message;
  }
}

function showApp() {
  $("#loginView").hidden = true;
  $("#appView").hidden = false;
  $("#adminName").textContent = state.username;
  switchView("dashboard");
}

const titles = {dashboard:"Tổng quan", users:"Tài khoản", voices:"Thư viện voice", audit:"Nhật ký hoạt động"};
function switchView(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach(el => { el.hidden = el.id !== `${view}View`; });
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $("#pageTitle").textContent = titles[view];
  loadCurrentView();
}

async function loadCurrentView() {
  try {
    if (state.view === "dashboard") await loadDashboard();
    if (state.view === "users") await loadUsers();
    if (state.view === "voices") await loadVoices();
    if (state.view === "audit") await loadAudit();
  } catch (err) { showToast(err.message, true); }
}

async function loadDashboard() {
  const data = await api("/api/admin/dashboard");
  const cards = [
    ["Tổng tài khoản", data.total_users, "accent"],
    ["Đang hoạt động", data.active_users, ""],
    ["Chưa kích hoạt / đã khóa", data.inactive_users, ""],
    ["Quản trị viên", data.admin_users, ""],
    ["Tổng số voice", data.total_voices, ""],
    ["Voice Clone", data.clone_voices, ""],
    ["Voice Design", data.design_voices, ""],
  ];
  $("#statsGrid").innerHTML = cards.map(([label,value,kind]) => `<article class="panel stat ${kind}"><span>${label}</span><strong>${value}</strong></article>`).join("");
}

function queryFromForm(formSelector, page) {
  const params = new URLSearchParams({page, pageSize:20});
  new FormData($(formSelector)).forEach((value, key) => { if (value !== "") params.set(key, value); });
  return params;
}

function renderPager(selector, data, callbackName) {
  const pager = $(selector);
  pager.innerHTML = `<span>Trang ${data.page || 1} / ${Math.max(data.total_pages, 1)} · ${data.total_items} mục</span><button data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>Trước</button><button data-page="${data.page + 1}" ${data.page >= data.total_pages ? "disabled" : ""}>Sau</button>`;
  pager.querySelectorAll("button:not(:disabled)").forEach(button => button.addEventListener("click", () => callbackName(Number(button.dataset.page))));
}

async function loadUsers(page = state.userPage) {
  state.userPage = page;
  const data = await api(`/api/admin/users?${queryFromForm("#userFilter", page)}`);
  state.users = new Map(data.items.map(user => [String(user.id), user]));
  $("#usersBody").innerHTML = data.items.length ? data.items.map(user => `<tr>
    <td><strong>${escapeHtml(user.username)} ${user.is_default ? '<span class="badge admin">Admin</span>' : ""}</strong><div class="subtext">${escapeHtml(user.email)}</div></td>
    <td><span class="badge ${user.is_active ? "good" : "warn"}">${user.is_active ? "Hoạt động" : "Đã khóa / chờ"}</span></td>
    <td><span class="subtext">${[user.clone_voice&&"Clone",user.design_voice&&"Design",user.gen_voice&&"Generate"].filter(Boolean).join(" · ") || "Không có"}</span></td>
    <td><strong>${user.clone_limit} / ${user.design_limit}</strong></td><td>${user.voice_count}</td>
    <td><div class="actions"><button class="action" data-edit-user="${user.id}">Chỉnh sửa</button><button class="action" data-reset-user="${user.id}">Đặt mật khẩu</button></div></td></tr>`).join("") : '<tr><td colspan="6" class="empty">Không có tài khoản phù hợp.</td></tr>';
  document.querySelectorAll("[data-edit-user]").forEach(button => button.addEventListener("click", () => openUserDialog(state.users.get(button.dataset.editUser))));
  document.querySelectorAll("[data-reset-user]").forEach(button => button.addEventListener("click", () => openPasswordDialog(state.users.get(button.dataset.resetUser))));
  renderPager("#usersPager", data, loadUsers);
}

function openUserDialog(user = null) {
  const form = $("#userForm"); form.reset(); $("#userFormError").textContent = "";
  form.elements.id.value = user?.id || "";
  $("#userDialogTitle").textContent = user ? "Chỉnh sửa tài khoản" : "Tạo tài khoản";
  form.elements.username.disabled = Boolean(user);
  form.elements.password.required = !user;
  $("#passwordField").hidden = Boolean(user);
  if (user) ["username","email","clone_limit","design_limit"].forEach(key => { form.elements[key].value = user[key]; });
  ["is_active","is_default","clone_voice","design_voice","gen_voice"].forEach(key => { form.elements[key].checked = user ? user[key] : ["is_active","design_voice","gen_voice"].includes(key); });
  $("#userDialog").showModal();
}

async function saveUser(event) {
  event.preventDefault(); const form = event.currentTarget; const id = form.elements.id.value;
  const payload = {};
  ["email","clone_limit","design_limit"].forEach(key => payload[key] = key.endsWith("limit") ? Number(form.elements[key].value) : form.elements[key].value);
  ["is_active","is_default","clone_voice","design_voice","gen_voice"].forEach(key => payload[key] = form.elements[key].checked);
  if (!id) { payload.username = form.elements.username.value; payload.password = form.elements.password.value; }
  try {
    await api(id ? `/api/admin/users/${id}` : "/api/admin/users", {method:id ? "PATCH" : "POST", body:JSON.stringify(payload)});
    $("#userDialog").close(); showToast(id ? "Đã cập nhật tài khoản." : "Đã tạo tài khoản."); await loadUsers(id ? state.userPage : 1);
  } catch (err) { $("#userFormError").textContent = err.message; }
}

function openPasswordDialog(user) {
  const form = $("#passwordForm"); form.reset(); form.elements.id.value = user.id;
  $("#passwordUser").textContent = `Tài khoản: ${user.username}`; $("#passwordFormError").textContent = ""; $("#passwordDialog").showModal();
}

async function resetPassword(event) {
  event.preventDefault(); const form = event.currentTarget;
  try { await api(`/api/admin/users/${form.elements.id.value}/reset-password`, {method:"POST", body:JSON.stringify({new_password:form.elements.new_password.value})}); $("#passwordDialog").close(); showToast("Đã đặt lại mật khẩu."); }
  catch (err) { $("#passwordFormError").textContent = err.message; }
}

async function loadVoices(page = state.voicePage) {
  state.voicePage = page; const data = await api(`/api/admin/voices?${queryFromForm("#voiceFilter", page)}`);
  state.voices = new Map(data.items.map(voice => [voice.id, voice]));
  $("#voicesBody").innerHTML = data.items.length ? data.items.map(voice => `<tr><td><strong>${escapeHtml(voice.voice_name)}</strong><div class="subtext">${escapeHtml(voice.original_file_name || voice.id)}</div></td><td>${escapeHtml(voice.owner_username)}</td><td><span class="badge ${voice.generation_method === "voice-clone" ? "good" : "admin"}">${voice.generation_method}</span></td><td><span class="subtext">${escapeHtml([voice.language,voice.gender,voice.style].filter(Boolean).join(" · ") || (voice.audio_size ? `${Math.ceil(voice.audio_size/1024)} KB` : "-") )}</span></td><td>${formatDate(voice.created_at)}</td><td><div class="actions">${voice.generation_method === "voice-clone" ? `<button class="action" data-play-voice="${voice.id}">Nghe</button>` : ""}<button class="action" data-rename-voice="${voice.id}">Đổi tên</button><button class="action danger" data-delete-voice="${voice.id}">Xóa</button></div></td></tr>`).join("") : '<tr><td colspan="6" class="empty">Không có voice phù hợp.</td></tr>';
  document.querySelectorAll("[data-play-voice]").forEach(button => button.addEventListener("click", () => playVoice(state.voices.get(button.dataset.playVoice))));
  document.querySelectorAll("[data-rename-voice]").forEach(button => button.addEventListener("click", () => renameVoice(state.voices.get(button.dataset.renameVoice))));
  document.querySelectorAll("[data-delete-voice]").forEach(button => button.addEventListener("click", () => deleteVoice(state.voices.get(button.dataset.deleteVoice))));
  renderPager("#voicesPager", data, loadVoices);
}

async function renameVoice(voice) {
  const name = window.prompt("Tên voice mới", voice.voice_name); if (!name || name === voice.voice_name) return;
  try { await api(`/api/admin/voices/${voice.id}`, {method:"PATCH", body:JSON.stringify({voiceName:name})}); showToast("Đã đổi tên voice."); loadVoices(); } catch (err) { showToast(err.message, true); }
}

async function deleteVoice(voice) {
  if (!window.confirm(`Xóa voice “${voice.voice_name}” của ${voice.owner_username}? Thao tác này không thể hoàn tác.`)) return;
  try { await api(`/api/admin/voices/${voice.id}`, {method:"DELETE"}); showToast("Đã xóa voice."); loadVoices(); } catch (err) { showToast(err.message, true); }
}

async function playVoice(voice) {
  try {
    const response = await api(`/api/admin/voices/${voice.id}/audio`);
    const blob = await response.blob(); if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
    state.audioUrl = URL.createObjectURL(blob); $("#audioTitle").textContent = voice.voice_name; $("#audioPlayer").src = state.audioUrl; $("#audioDialog").showModal();
  } catch (err) { showToast(err.message, true); }
}

async function loadAudit() {
  const data = await api("/api/admin/audit?limit=200");
  $("#auditBody").innerHTML = data.items.length ? data.items.map(item => `<tr><td>${formatDate(item.timestamp)}</td><td>${escapeHtml(item.username)}</td><td><strong>${escapeHtml(item.method)} ${escapeHtml(item.path)}</strong><div class="subtext">${escapeHtml(item.request_id || "")}</div></td><td><span class="badge ${item.status_code < 400 ? "good" : "danger"}">${item.status_code}</span></td><td>${item.duration_ms.toFixed(2)} ms</td></tr>`).join("") : '<tr><td colspan="5" class="empty">Chưa có audit log hoặc chức năng đang tắt.</td></tr>';
}

$("#loginForm").addEventListener("submit", login);
$("#logoutButton").addEventListener("click", logout);
$("#refreshButton").addEventListener("click", loadCurrentView);
$("#mainNav").addEventListener("click", event => { if (event.target.dataset.view) switchView(event.target.dataset.view); });
$("#userFilter").addEventListener("submit", event => { event.preventDefault(); loadUsers(1); });
$("#voiceFilter").addEventListener("submit", event => { event.preventDefault(); loadVoices(1); });
$("#createUserButton").addEventListener("click", () => openUserDialog());
$("#userForm").addEventListener("submit", saveUser);
$("#passwordForm").addEventListener("submit", resetPassword);
document.querySelectorAll("[data-close-dialog]").forEach(button => button.addEventListener("click", () => button.closest("dialog").close()));
$("#audioDialog").addEventListener("close", () => $("#audioPlayer").pause());

if (state.token) api("/api/admin/dashboard").then(showApp).catch(logout);
