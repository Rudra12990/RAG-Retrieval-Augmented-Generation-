const API_URL = "https://rag-retrieval-augmented-generation.onrender.com";

// DOM Matrix Element Interceptors
const docIdInput = document.getElementById("doc-id");
const docContentInput = document.getElementById("doc-content");
const btnSave = document.getElementById("btn-save");
const saveStatus = document.getElementById("save-status");
const docListTarget = document.getElementById("doc-list-target");

const queryTextInput = document.getElementById("query-text");
const btnQuery = document.getElementById("btn-query");
const queryStatus = document.getElementById("query-status");

const aiOutput = document.getElementById("ai-output");
const retrievedContext = document.getElementById("retrieved-context");
const btnClear = document.getElementById("btn-clear");

const conflictModal = document.getElementById("conflict-modal");
const modalDesc = document.getElementById("modal-desc");
const modalCancel = document.getElementById("modal-cancel");
const modalAppend = document.getElementById("modal-append");
const modalOverwrite = document.getElementById("modal-overwrite");

function showStatus(element, text, type) {
    element.className = `status-box status-${type}`;
    element.innerText = text;
    element.style.display = "block";
}

// 🔄 Action: Re-render Sidebar Registry Items dynamically
async function fetchWorkspaceIndexes() {
    try {
        const response = await fetch(`${API_URL}/documents`);
        const data = await response.json();
        
        if(!response.ok) throw new Error();
        
        docListTarget.innerHTML = "";
        
        if (data.documents.length === 0) {
            docListTarget.innerHTML = `<li style="font-size:0.8rem; color:var(--text-secondary); text-align:center; padding-top:1rem;">Workspace index empty</li>`;
            return;
        }
        
        data.documents.forEach(id => {
            const li = document.createElement("li");
            li.className = "doc-item";
            li.innerHTML = `
                <span class="doc-id-text" title="${id}">${id}</span>
                <button class="btn-trash" onclick="deleteIndexTarget('${id}')">✕ Delete</button>
            `;
            docListTarget.appendChild(li);
        });
    } catch (err) {
        docListTarget.innerHTML = `<li style="font-size:0.75rem; color:var(--accent-danger); text-align:center;">Failed to sync sidebar indices</li>`;
    }
}

// 🗑️ Action: Drop explicit Key from collection row
async function deleteIndexTarget(docId) {
    if (!confirm(`Remove index entry '${docId}' from database?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/documents/${encodeURIComponent(docId)}`, {
            method: "DELETE"
        });
        const data = await response.json();
        
        if(!response.ok) throw new Error(data.detail);
        
        fetchWorkspaceIndexes(); // Instantly pull an updated list layout
    } catch (err) {
        alert(`Deletion aborted: ${err.message}`);
    }
}

async function saveDocument(mode = "check") {
    const docId = docIdInput.value.trim();
    const textContent = docContentInput.value.trim();

    if (!docId || !textContent) {
        showStatus(saveStatus, "Please complete all fields.", "error");
        return;
    }

    btnSave.disabled = true;
    showStatus(saveStatus, "Syncing cloud parameters...", "info");

    try {
        const response = await fetch(`${API_URL}/add?doc_id=${encodeURIComponent(docId)}&text_content=${encodeURIComponent(textContent)}&mode=${mode}`, {
            method: "POST"
        });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || "Server pipeline issue.");

        if (data.status === "exists_warning") {
            modalDesc.innerText = `The identifier '${docId}' already matches active content inside the cloud database. Choose a resolution matrix strategy:`;
            conflictModal.classList.add("active");
            saveStatus.style.display = "none";
        } else {
            showStatus(saveStatus, data.message, "success");
            docIdInput.value = "";
            docContentInput.value = "";
            conflictModal.classList.remove("active");
            fetchWorkspaceIndexes(); // Update dynamic list tracking visual view
        }
    } catch (err) {
        showStatus(saveStatus, err.message, "error");
    } finally {
        btnSave.disabled = false;
    }
}

async function runQuery() {
    const question = queryTextInput.value.trim();
    if (!question) {
        showStatus(queryStatus, "Please supply an inquiry statement.", "error");
        return;
    }

    btnQuery.disabled = true;
    aiOutput.innerText = "Synthesizing input matrices... Context generation processing...";
    showStatus(queryStatus, "Processing AI query...", "info");

    try {
        const response = await fetch(`${API_URL}/ask?question=${encodeURIComponent(question)}`, {
            method: "POST"
        });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || "Inference failed.");

        // Parse markdown text string dynamically via Marked compilation parser engine
        aiOutput.innerHTML = marked.parse(data.answer);
        retrievedContext.innerText = data.retrieved_context;
        queryStatus.style.display = "none";
        queryTextInput.value = "";
    } catch (err) {
        aiOutput.innerText = "Processing broken.";
        showStatus(queryStatus, err.message, "error");
    } finally {
        btnQuery.disabled = false;
    }
}

async function clearStorage() {
    if (!confirm("Wipe entire repository database cache?")) return;
    try {
        const response = await fetch(`${API_URL}/clear`, { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        aiOutput.innerText = "Workspace cache flushed clean.";
        retrievedContext.innerText = "No queries compiled yet.";
        fetchWorkspaceIndexes();
    } catch (err) {
        alert(`Flush action failed: ${err.message}`);
    }
}

// Event Listener Subscriptions Matrix
btnSave.addEventListener("click", () => saveDocument("check"));
btnQuery.addEventListener("click", runQuery);
btnClear.addEventListener("click", clearStorage);

modalCancel.addEventListener("click", () => {
    conflictModal.classList.remove("active");
    showStatus(saveStatus, "Operation aborted.", "info");
});
modalAppend.addEventListener("click", () => saveDocument("append"));
modalOverwrite.addEventListener("click", () => saveDocument("overwrite"));

// Initialize Workspace Sync Elements on load phase closure
fetchWorkspaceIndexes();