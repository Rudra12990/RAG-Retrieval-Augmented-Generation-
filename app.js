// ⚡ Configuration Parameters - ENTER YOUR ACTUAL VALUES HERE
const SUPABASE_PROJECT_URL = "https://vizpndniifwpwmqnjvvi.supabase.co"; 
const SUPABASE_ANON_PUBLIC_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZpenBuZG5paWZ3cHdtcW5qdnZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxNTAyMjYsImV4cCI6MjA5NzcyNjIyNn0.FQ8WGVVVbA-vbH8pc6nkj1tHc_3fbfFvmOWc4Nn8WeY";
const API_URL = "https://rag-retrieval-augmented-generation.onrender.com";


// 🚀 Initialize browser-side Supabase client engine (FIXED variable collision name)
const supabaseClient = supabase.createClient(SUPABASE_PROJECT_URL, SUPABASE_ANON_PUBLIC_KEY);

// State monitoring parameters
let userSessionToken = null;
let currentAuthMode = "login"; 

// DOM Interceptors Matrix
const authGatekeeper = document.getElementById("auth-gatekeeper");
const mainDashboardLayout = document.getElementById("main-dashboard-layout");
const authEmail = document.getElementById("auth-email");
const authPassword = document.getElementById("auth-password");
const btnPrimaryAuth = document.getElementById("btn-primary-auth");
const btnToggleAuthMode = document.getElementById("btn-toggle-auth-mode");
const authStatus = document.getElementById("auth-status");
const userDisplayEmail = document.getElementById("user-display-email");
const btnLogout = document.getElementById("btn-logout");

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
const themeToggleBtn = document.getElementById("theme-toggle");

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

// Helper: Build authenticated headers containing user identity credentials
function getAuthFetchHeaders() {
    return {
        "Authorization": `Bearer ${userSessionToken}`
    };
}

// 🔄 Monitor Authentication State Changes Across Sessions
supabaseClient.auth.onAuthStateChange((event, session) => {
    if (session) {
        userSessionToken = session.access_token;
        userDisplayEmail.innerText = session.user.email;
        authGatekeeper.style.display = "none";
        mainDashboardLayout.style.display = "flex";
        fetchWorkspaceIndexes();
    } else {
        userSessionToken = null;
        authGatekeeper.style.display = "flex";
        mainDashboardLayout.style.display = "none";
    }
});

// Action: Handle Authentication Execution Loop
btnPrimaryAuth.addEventListener("click", async () => {
    const email = authEmail.value.trim();
    const password = authPassword.value.trim();

    if (!email || !password) {
        showStatus(authStatus, "Please enter email and password.", "error");
        return;
    }

    btnPrimaryAuth.disabled = true;
    showStatus(authStatus, "Processing secure handshake...", "info");

    try {
        if (currentAuthMode === "login") {
            const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
            if (error) {
                showStatus(authStatus, `Login Failed: ${error.message}`, "error");
                return;
            }
        } else {
            const { data, error } = await supabaseClient.auth.signUp({ email, password });
            if (error) {
                showStatus(authStatus, `Registration Failed: ${error.message}`, "error");
                return;
            }
            if (data.user && data.session === null) {
                showStatus(authStatus, "Account created! 📧 Check your inbox for a verification link before logging in.", "success");
                authEmail.value = "";
                authPassword.value = "";
                return;
            }
        }
    } catch (err) {
        showStatus(authStatus, `System Error: ${err.message}`, "error");
    } finally {
        btnPrimaryAuth.disabled = false;
    }
});

// Toggle Auth Mode Display Options
btnToggleAuthMode.addEventListener("click", () => {
    if (currentAuthMode === "login") {
        currentAuthMode = "signup";
        document.getElementById("auth-title").innerText = "Create Cloud Account";
        btnPrimaryAuth.innerText = "Register Account";
        btnToggleAuthMode.innerText = "Already have an account? Log In";
    } else {
        currentAuthMode = "login";
        document.getElementById("auth-title").innerText = "Welcome to Workspace Suite";
        btnPrimaryAuth.innerText = "Log In";
        btnToggleAuthMode.innerText = "Need an account? Sign Up";
    }
    authStatus.style.display = "none";
});

// Log Out Action
btnLogout.addEventListener("click", () => supabaseClient.auth.signOut());

// 🔄 Sync Vector Items list view from Backend Engine
async function fetchWorkspaceIndexes() {
    try {
        const response = await fetch(`${API_URL}/documents`, {
            headers: getAuthFetchHeaders()
        });
        const data = await response.json();
        
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
        docListTarget.innerHTML = `<li style="font-size:0.75rem; color:var(--accent-danger); text-align:center;">Failed to sync indices</li>`;
    }
}

// 🗑️ Drop explicit single key index row parameters
async function deleteIndexTarget(docId) {
    if (!confirm(`Remove index entry '${docId}' from database securely?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/documents/${encodeURIComponent(docId)}`, {
            method: "DELETE",
            headers: getAuthFetchHeaders()
        });
        const data = await response.json();
        if(!response.ok) throw new Error(data.detail);
        fetchWorkspaceIndexes();
    } catch (err) {
        alert(`Deletion failure: ${err.message}`);
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
        const url = `${API_URL}/add?doc_id=${encodeURIComponent(docId)}&text_content=${encodeURIComponent(textContent)}&mode=${mode}`;
        const response = await fetch(url, {
            method: "POST",
            headers: getAuthFetchHeaders()
        });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || "Server communication failed.");

        if (data.status === "exists_warning") {
            modalDesc.innerText = `The identifier '${docId}' matches content inside your repository list. Strategy resolution required:`;
            conflictModal.classList.add("active");
            saveStatus.style.display = "none";
        } else {
            showStatus(saveStatus, data.message, "success");
            docIdInput.value = "";
            docContentInput.value = "";
            conflictModal.classList.remove("active");
            fetchWorkspaceIndexes();
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
    aiOutput.innerText = "Synthesizing input matrices across user context vectors...";
    showStatus(queryStatus, "Processing AI query...", "info");

    try {
        const response = await fetch(`${API_URL}/ask?question=${encodeURIComponent(question)}`, {
            method: "POST",
            headers: getAuthFetchHeaders()
        });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || "Inference transaction failed.");

        aiOutput.innerHTML = marked.parse(data.answer);
        retrievedContext.innerText = data.retrieved_context;
        queryStatus.style.display = "none";
        queryTextInput.value = "";
    } catch (err) {
        aiOutput.innerText = "Processing error encountered.";
        showStatus(queryStatus, err.message, "error");
    } finally {
        btnQuery.disabled = false;
    }
}

async function clearIntervals() { 
    if (!confirm("Wipe your isolated storage layer database index completely clean?")) return;
    try {
        const response = await fetch(`${API_URL}/clear`, { 
            method: "POST",
            headers: getAuthFetchHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);
        aiOutput.innerText = "Your secure profile workspace has been flushed clear.";
        retrievedContext.innerText = "No queries compiled yet.";
        fetchWorkspaceIndexes();
    } catch (err) {
        alert(`Flush failed: ${err.message}`);
    }
}

// Theme switch controller hook mechanics
const currentSavedTheme = localStorage.getItem("themeWorkspacePreference");
if (currentSavedTheme === "light") document.body.classList.add("light-theme");

themeToggleBtn.addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
    localStorage.setItem("themeWorkspacePreference", document.body.classList.contains("light-theme") ? "light" : "dark");
});

// Listener Setup
btnSave.addEventListener("click", () => saveDocument("check"));
btnQuery.addEventListener("click", runQuery);
btnClear.addEventListener("click", clearIntervals);
modalCancel.addEventListener("click", () => { conflictModal.classList.remove("active"); });
modalAppend.addEventListener("click", () => saveDocument("append"));
modalOverwrite.addEventListener("click", () => saveDocument("overwrite"));