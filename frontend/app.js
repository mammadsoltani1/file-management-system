const API_BASE = "/api/v1";

let accessToken = sessionStorage.getItem("accessToken");
let currentUser = null;

// breadcrumb is a stack of {id, name}; null id means root
let breadcrumb = [{ id: null, name: "Home" }];

// selected file ids in the current folder listing (files only, bulk ops don't cover folders)
let selectedFileIds = new Set();

// clipboard is null or { mode: "move" | "copy", fileIds: [...] }
let clipboard = null;

const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const trashSection = document.getElementById("trash-section");
const searchSection = document.getElementById("search-section");
const sharesSection = document.getElementById("shares-section");
const receivedSection = document.getElementById("received-section");
const sideSections = [trashSection, searchSection, sharesSection, receivedSection];
const userBar = document.getElementById("user-bar");
const userEmailLabel = document.getElementById("user-email");

const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const registerForm = document.getElementById("register-form");
const registerError = document.getElementById("register-error");

const logoutButton = document.getElementById("logout-button");
const logoutAllButton = document.getElementById("logout-all-button");
const createFolderForm = document.getElementById("create-folder-form");
const uploadForm = document.getElementById("upload-form");
const appError = document.getElementById("app-error");
const breadcrumbNav = document.getElementById("breadcrumb");
const listingBody = document.getElementById("listing-body");
const emptyMessage = document.getElementById("empty-message");

const bulkMoveButton = document.getElementById("bulk-move-button");
const bulkCopyButton = document.getElementById("bulk-copy-button");
const bulkDeleteButton = document.getElementById("bulk-delete-button");
const pasteButton = document.getElementById("paste-button");
const clipboardStatus = document.getElementById("clipboard-status");

const trashButton = document.getElementById("trash-button");
const backToFilesButton = document.getElementById("back-to-files-button");
const trashError = document.getElementById("trash-error");
const trashBody = document.getElementById("trash-body");
const trashEmptyMessage = document.getElementById("trash-empty-message");

const searchForm = document.getElementById("search-form");
const searchQueryInput = document.getElementById("search-query");
const searchBackButton = document.getElementById("search-back-button");
const searchError = document.getElementById("search-error");
const searchBody = document.getElementById("search-body");
const searchEmptyMessage = document.getElementById("search-empty-message");

const sharedButton = document.getElementById("shared-button");
const sharesFileName = document.getElementById("shares-file-name");
const sharesBackButton = document.getElementById("shares-back-button");
const addShareForm = document.getElementById("add-share-form");
const shareRecipientEmailInput = document.getElementById("share-recipient-email");
const sharesError = document.getElementById("shares-error");
const sharesBody = document.getElementById("shares-body");
const sharesEmptyMessage = document.getElementById("shares-empty-message");
let currentSharingFileId = null;

const receivedBackButton = document.getElementById("received-back-button");
const receivedError = document.getElementById("received-error");
const receivedBody = document.getElementById("received-body");
const receivedEmptyMessage = document.getElementById("received-empty-message");

function currentFolderId() {
    return breadcrumb[breadcrumb.length - 1].id;
}

function showError(element, message) {
    element.textContent = message;
}

function clearErrors() {
    loginError.textContent = "";
    registerError.textContent = "";
    appError.textContent = "";
    trashError.textContent = "";
    searchError.textContent = "";
    sharesError.textContent = "";
    receivedError.textContent = "";
}

function showSideSection(section) {
    appSection.classList.add("hidden");
    for (const sideSection of sideSections) {
        sideSection.classList.toggle("hidden", sideSection !== section);
    }
}

async function backToFiles() {
    for (const sideSection of sideSections) {
        sideSection.classList.add("hidden");
    }
    appSection.classList.remove("hidden");
    await loadDirectory();
}

async function apiFetch(path, options = {}, retry = true) {
    const headers = options.headers ? { ...options.headers } : {};
    if (accessToken) {
        headers["Authorization"] = "Bearer " + accessToken;
    }

    const response = await fetch(API_BASE + path, {
        ...options,
        headers,
        credentials: "same-origin",
    });

    if (response.status === 401 && retry) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
            return apiFetch(path, options, false);
        }
    }

    return response;
}

async function tryRefreshToken() {
    const response = await fetch(API_BASE + "/auth/refresh", {
        method: "POST",
        credentials: "same-origin",
    });

    if (!response.ok) {
        return false;
    }

    const data = await response.json();
    accessToken = data.access_token;
    sessionStorage.setItem("accessToken", accessToken);
    return true;
}

function showApp() {
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    for (const sideSection of sideSections) {
        sideSection.classList.add("hidden");
    }
    userBar.classList.remove("hidden");
}

function showAuth() {
    authSection.classList.remove("hidden");
    appSection.classList.add("hidden");
    for (const sideSection of sideSections) {
        sideSection.classList.add("hidden");
    }
    userBar.classList.add("hidden");
}

async function loadCurrentUser() {
    const response = await apiFetch("/users/me");
    if (!response.ok) {
        throw new Error("could not load user");
    }
    currentUser = await response.json();
    userEmailLabel.textContent = currentUser.email;
}

async function startSession() {
    try {
        await loadCurrentUser();
        showApp();
        breadcrumb = [{ id: null, name: "Home" }];
        resetClipboard();
        await loadDirectory();
    } catch (err) {
        accessToken = null;
        sessionStorage.removeItem("accessToken");
        showAuth();
    }
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    const response = await fetch(API_BASE + "/auth/login", {
        method: "POST",
        body,
        credentials: "same-origin",
    });

    if (!response.ok) {
        showError(loginError, "incorrect email or password");
        return;
    }

    const data = await response.json();
    accessToken = data.access_token;
    sessionStorage.setItem("accessToken", accessToken);
    loginForm.reset();
    await startSession();
});

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;

    const response = await fetch(API_BASE + "/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(registerError, data.detail || "registration failed");
        return;
    }

    registerForm.reset();
    showError(registerError, "account created, you can now log in");
});

logoutButton.addEventListener("click", async () => {
    await apiFetch("/auth/logout", { method: "POST" }, false);
    accessToken = null;
    currentUser = null;
    sessionStorage.removeItem("accessToken");
    showAuth();
});

logoutAllButton.addEventListener("click", async () => {
    if (!confirm("Log out of all devices? Every other session will be signed out too.")) {
        return;
    }

    await apiFetch("/auth/logout-all", { method: "POST" }, false);
    accessToken = null;
    currentUser = null;
    sessionStorage.removeItem("accessToken");
    showAuth();
});

function renderBreadcrumb() {
    breadcrumbNav.innerHTML = "";
    breadcrumb.forEach((entry, index) => {
        if (index > 0) {
            breadcrumbNav.appendChild(document.createTextNode(" / "));
        }
        const link = document.createElement("a");
        link.textContent = entry.name;
        link.addEventListener("click", async () => {
            breadcrumb = breadcrumb.slice(0, index + 1);
            await loadDirectory();
        });
        breadcrumbNav.appendChild(link);
    });
}

async function loadDirectory() {
    clearErrors();
    renderBreadcrumb();
    selectedFileIds.clear();

    const folderId = currentFolderId();
    const query = folderId ? "?folder_id=" + encodeURIComponent(folderId) : "";
    const response = await apiFetch("/files" + query);

    if (!response.ok) {
        showError(appError, "could not load this folder");
        return;
    }

    const data = await response.json();
    renderListing(data.folders, data.files);
    renderClipboardStatus();
}

function renderListing(folders, files) {
    listingBody.innerHTML = "";
    emptyMessage.classList.toggle("hidden", folders.length + files.length > 0);

    for (const folder of folders) {
        const row = document.createElement("tr");

        row.appendChild(makeCell(""));

        const nameCell = document.createElement("td");
        nameCell.className = "name";
        const link = document.createElement("a");
        link.textContent = folder.name;
        link.addEventListener("click", async () => {
            breadcrumb.push({ id: folder.id, name: folder.name });
            await loadDirectory();
        });
        nameCell.appendChild(link);
        row.appendChild(nameCell);

        row.appendChild(makeCell("Folder"));
        row.appendChild(makeCell(""));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Rename", () => renameFolder(folder.id, folder.name))
        );
        actionsCell.appendChild(
            makeButton("Delete", () => deleteFolder(folder.id, folder.name))
        );
        row.appendChild(actionsCell);

        listingBody.appendChild(row);
    }

    for (const file of files) {
        const row = document.createElement("tr");

        const checkboxCell = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedFileIds.has(file.id);
        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                selectedFileIds.add(file.id);
            } else {
                selectedFileIds.delete(file.id);
            }
        });
        checkboxCell.appendChild(checkbox);
        row.appendChild(checkboxCell);

        row.appendChild(makeCell(file.name));
        row.appendChild(makeCell("File"));
        row.appendChild(makeCell(formatSize(file.size_bytes)));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Download", () => downloadFile(file.id, file.name))
        );
        actionsCell.appendChild(
            makeButton("Rename", () => renameFile(file.id, file.name))
        );
        actionsCell.appendChild(makeButton("Share", () => openShares(file.id, file.name)));
        actionsCell.appendChild(
            makeButton("Delete", () => deleteFile(file.id, file.name))
        );
        row.appendChild(actionsCell);

        listingBody.appendChild(row);
    }
}

function makeCell(text) {
    const cell = document.createElement("td");
    cell.textContent = text;
    return cell;
}

function makeButton(label, onClick) {
    const button = document.createElement("button");
    button.textContent = label;
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return Math.round(bytes / (1024 * 1024)) + " MB";
}

function formatDate(isoString) {
    return new Date(isoString).toLocaleString();
}

createFolderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const nameInput = document.getElementById("new-folder-name");
    const response = await apiFetch("/folders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: nameInput.value,
            parent_id: currentFolderId(),
        }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(appError, data.detail || "could not create folder");
        return;
    }

    nameInput.value = "";
    await loadDirectory();
});

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const fileInput = document.getElementById("upload-input");
    const file = fileInput.files[0];
    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("upload", file);
    const folderId = currentFolderId();
    if (folderId) {
        formData.append("folder_id", folderId);
    }

    const response = await apiFetch("/files/upload", {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(appError, data.detail || "could not upload file");
        return;
    }

    fileInput.value = "";
    await loadDirectory();
});

async function downloadFile(fileId, name) {
    clearErrors();
    const response = await apiFetch("/files/" + fileId + "/download");

    if (!response.ok) {
        showError(appError, "could not download this file");
        return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

async function deleteFile(fileId, name) {
    if (!confirm("Delete file \"" + name + "\"?")) {
        return;
    }

    clearErrors();
    const response = await apiFetch("/files/" + fileId, { method: "DELETE" });

    if (!response.ok) {
        showError(appError, "could not delete this file");
        return;
    }

    await loadDirectory();
}

async function deleteFolder(folderId, name) {
    if (!confirm("Delete folder \"" + name + "\" and everything inside it?")) {
        return;
    }

    clearErrors();
    const response = await apiFetch("/folders/" + folderId + "?recursive=true", {
        method: "DELETE",
    });

    if (!response.ok) {
        showError(appError, "could not delete this folder");
        return;
    }

    await loadDirectory();
}

async function renameFile(fileId, currentName) {
    const name = prompt("Rename file to:", currentName);
    if (!name || name === currentName) {
        return;
    }

    clearErrors();
    const response = await apiFetch("/files/" + fileId + "/rename", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(appError, data.detail || "could not rename this file");
        return;
    }

    await loadDirectory();
}

async function renameFolder(folderId, currentName) {
    const name = prompt("Rename folder to:", currentName);
    if (!name || name === currentName) {
        return;
    }

    clearErrors();
    const response = await apiFetch("/folders/" + folderId + "/rename", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(appError, data.detail || "could not rename this folder");
        return;
    }

    await loadDirectory();
}

function resetClipboard() {
    clipboard = null;
    renderClipboardStatus();
}

function renderClipboardStatus() {
    if (!clipboard) {
        clipboardStatus.textContent = "";
        pasteButton.classList.add("hidden");
        return;
    }

    const verb = clipboard.mode === "move" ? "move" : "copy";
    clipboardStatus.textContent =
        clipboard.fileIds.length +
        " file(s) ready to " +
        verb +
        " — open the destination folder and click Paste here";
    pasteButton.classList.remove("hidden");
}

bulkMoveButton.addEventListener("click", () => {
    clearErrors();
    if (selectedFileIds.size === 0) {
        showError(appError, "select at least one file first");
        return;
    }
    clipboard = { mode: "move", fileIds: Array.from(selectedFileIds) };
    renderClipboardStatus();
});

bulkCopyButton.addEventListener("click", () => {
    clearErrors();
    if (selectedFileIds.size === 0) {
        showError(appError, "select at least one file first");
        return;
    }
    clipboard = { mode: "copy", fileIds: Array.from(selectedFileIds) };
    renderClipboardStatus();
});

pasteButton.addEventListener("click", async () => {
    clearErrors();
    if (!clipboard) {
        return;
    }

    const path = clipboard.mode === "move" ? "/files/bulk/move" : "/files/bulk/copy";
    const response = await apiFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            file_ids: clipboard.fileIds,
            folder_id: currentFolderId(),
        }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(
            appError,
            data.detail || "could not " + clipboard.mode + " the selected files"
        );
        return;
    }

    resetClipboard();
    await loadDirectory();
});

bulkDeleteButton.addEventListener("click", async () => {
    clearErrors();
    if (selectedFileIds.size === 0) {
        showError(appError, "select at least one file first");
        return;
    }

    if (!confirm("Delete " + selectedFileIds.size + " selected file(s)?")) {
        return;
    }

    const response = await apiFetch("/files/bulk/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: Array.from(selectedFileIds) }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(appError, data.detail || "could not delete the selected files");
        return;
    }

    resetClipboard();
    await loadDirectory();
});

trashButton.addEventListener("click", async () => {
    showSideSection(trashSection);
    await loadTrash();
});

backToFilesButton.addEventListener("click", backToFiles);

async function loadTrash() {
    clearErrors();
    const response = await apiFetch("/trash");

    if (!response.ok) {
        showError(trashError, "could not load trash");
        return;
    }

    const data = await response.json();
    renderTrash(data.folders, data.files);
}

function renderTrash(folders, files) {
    trashBody.innerHTML = "";
    trashEmptyMessage.classList.toggle("hidden", folders.length + files.length > 0);

    for (const folder of folders) {
        const row = document.createElement("tr");
        row.appendChild(makeCell(folder.name));
        row.appendChild(makeCell("Folder"));
        row.appendChild(makeCell(formatDate(folder.deleted_at)));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Restore", () => restoreTrashBatch(folder.trash_batch_id))
        );
        actionsCell.appendChild(
            makeButton("Delete forever", () =>
                purgeTrashBatch(folder.trash_batch_id, folder.name)
            )
        );
        row.appendChild(actionsCell);

        trashBody.appendChild(row);
    }

    for (const file of files) {
        const row = document.createElement("tr");
        row.appendChild(makeCell(file.name));
        row.appendChild(makeCell("File"));
        row.appendChild(makeCell(formatDate(file.deleted_at)));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Restore", () => restoreTrashBatch(file.trash_batch_id))
        );
        actionsCell.appendChild(
            makeButton("Delete forever", () =>
                purgeTrashBatch(file.trash_batch_id, file.name)
            )
        );
        row.appendChild(actionsCell);

        trashBody.appendChild(row);
    }
}

async function restoreTrashBatch(trashBatchId) {
    clearErrors();
    const response = await apiFetch("/trash/" + trashBatchId + "/restore", {
        method: "POST",
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(trashError, data.detail || "could not restore this item");
        return;
    }

    await loadTrash();
}

async function purgeTrashBatch(trashBatchId, name) {
    if (
        !confirm(
            "Permanently delete \"" + name + "\" and anything trashed with it? This cannot be undone."
        )
    ) {
        return;
    }

    clearErrors();
    const response = await apiFetch("/trash/" + trashBatchId, { method: "DELETE" });

    if (!response.ok) {
        showError(trashError, "could not permanently delete this item");
        return;
    }

    await loadTrash();
}

searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    showSideSection(searchSection);
    await runSearch(searchQueryInput.value);
});

searchBackButton.addEventListener("click", backToFiles);

async function runSearch(query) {
    const response = await apiFetch("/search?query=" + encodeURIComponent(query));

    if (!response.ok) {
        showError(searchError, "search failed, try a different query");
        return;
    }

    const data = await response.json();
    renderSearchResults(data.items);
}

function renderSearchResults(items) {
    searchBody.innerHTML = "";
    searchEmptyMessage.classList.toggle("hidden", items.length > 0);

    for (const item of items) {
        const row = document.createElement("tr");
        row.appendChild(makeCell(item.name));
        row.appendChild(makeCell(item.item_type === "folder" ? "Folder" : "File"));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";

        if (item.item_type === "folder") {
            actionsCell.appendChild(
                makeButton("Open", async () => {
                    breadcrumb = [
                        { id: null, name: "Home" },
                        { id: item.id, name: item.name },
                    ];
                    await backToFiles();
                })
            );
        } else {
            actionsCell.appendChild(
                makeButton("Download", () => downloadFile(item.id, item.name))
            );
            actionsCell.appendChild(
                makeButton("Share", () => openShares(item.id, item.name))
            );
        }

        row.appendChild(actionsCell);
        searchBody.appendChild(row);
    }
}

async function openShares(fileId, fileName) {
    clearErrors();
    currentSharingFileId = fileId;
    sharesFileName.textContent = fileName;
    showSideSection(sharesSection);
    await loadShares();
}

sharesBackButton.addEventListener("click", backToFiles);

async function loadShares() {
    const response = await apiFetch("/shares/files/" + currentSharingFileId);

    if (!response.ok) {
        showError(sharesError, "could not load shares for this file");
        return;
    }

    const shares = await response.json();
    renderShares(shares);
}

function renderShares(shares) {
    sharesBody.innerHTML = "";
    sharesEmptyMessage.classList.toggle("hidden", shares.length > 0);

    for (const share of shares) {
        const row = document.createElement("tr");
        row.appendChild(makeCell(share.recipient.email));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Revoke", () => revokeShare(share.id))
        );
        row.appendChild(actionsCell);

        sharesBody.appendChild(row);
    }
}

addShareForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const response = await apiFetch("/shares/files/" + currentSharingFileId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipient_email: shareRecipientEmailInput.value }),
    });

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showError(sharesError, data.detail || "could not share this file");
        return;
    }

    shareRecipientEmailInput.value = "";
    await loadShares();
});

async function revokeShare(shareId) {
    clearErrors();
    const response = await apiFetch("/shares/" + shareId, { method: "DELETE" });

    if (!response.ok) {
        showError(sharesError, "could not revoke this share");
        return;
    }

    await loadShares();
}

sharedButton.addEventListener("click", async () => {
    showSideSection(receivedSection);
    await loadReceived();
});

receivedBackButton.addEventListener("click", backToFiles);

async function loadReceived() {
    clearErrors();
    const response = await apiFetch("/shares/received/files");

    if (!response.ok) {
        showError(receivedError, "could not load files shared with you");
        return;
    }

    const files = await response.json();
    renderReceived(files);
}

function renderReceived(files) {
    receivedBody.innerHTML = "";
    receivedEmptyMessage.classList.toggle("hidden", files.length > 0);

    for (const file of files) {
        const row = document.createElement("tr");
        row.appendChild(makeCell(file.name));
        row.appendChild(makeCell(formatSize(file.size_bytes)));

        const actionsCell = document.createElement("td");
        actionsCell.className = "actions";
        actionsCell.appendChild(
            makeButton("Download", () => downloadReceivedFile(file.id, file.name))
        );
        row.appendChild(actionsCell);

        receivedBody.appendChild(row);
    }
}

async function downloadReceivedFile(fileId, name) {
    clearErrors();
    const response = await apiFetch("/shares/received/files/" + fileId + "/download");

    if (!response.ok) {
        showError(receivedError, "could not download this file");
        return;
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

if (accessToken) {
    startSession();
} else {
    showAuth();
}
