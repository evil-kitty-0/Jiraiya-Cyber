const API_BASE = "http://127.0.0.1:8090";
const API_URL = `${API_BASE}/api/chat`;
const SESSIONS_URL = `${API_BASE}/api/sessions`;

const chatArea = document.getElementById("chatArea");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("newChatBtn");
const chatHistory = document.getElementById("chatHistory");
const menuBtn = document.getElementById("menuBtn");
const sidebar = document.querySelector(".sidebar");
const cyberPanel = document.getElementById("cyberPanel");
const cyberAuthModal = document.getElementById("cyberAuthModal");
const cyberModalTitle = document.getElementById("cyberModalTitle");
const cyberModalTarget = document.getElementById("cyberModalTarget");
const cyberModalAction = document.getElementById("cyberModalAction");
let pendingCyberFinding = null;

let messages = [];
let currentSessionId = null;
let sessions = [];


/* ============================================================
   MESSAGE UI
   ============================================================ */

function addMessage(role, text) {

    const message = document.createElement("div");
    message.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent =
        role === "user" ? "U" : "🐸";

    const content = document.createElement("div");
    content.className = "message-content";

    const roleName = document.createElement("div");
    roleName.className = "message-role";
    roleName.textContent =
        role === "user" ? "You" : "Jiraiya";

    const textElement = document.createElement("div");
    textElement.textContent = text;

    content.appendChild(roleName);
    content.appendChild(textElement);

    message.appendChild(avatar);
    message.appendChild(content);

    chatArea.appendChild(message);

    chatArea.scrollTop =
        chatArea.scrollHeight;

    return textElement;
}


/* ============================================================
   CYBER UI
   ============================================================ */

async function cyberRequest(path, options) {
    options = options || {};
    options.headers = Object.assign({"Content-Type":"application/json"}, options.headers || {});
    const response = await fetch(API_BASE + path, options);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Cyber API request failed");
    return data;
}

function toggleCyberPanel(open) {
    if (!cyberPanel) return;
    cyberPanel.classList.toggle("open", open !== false);
    if (open !== false) loadCyberFindings();
}

async function saveCyberScope() {
    const program = document.getElementById("cyberProgram").value.trim();
    const hosts = document.getElementById("cyberHosts").value.split(",").map(function(x){return x.trim();}).filter(Boolean);
    const paths = document.getElementById("cyberPaths").value.split(",").map(function(x){return x.trim();}).filter(Boolean);
    const status = document.getElementById("cyberScopeStatus");
    try {
        const data = await cyberRequest("/api/cyber/scope", {method:"POST", body:JSON.stringify({program:program, allowed_hosts:hosts, allowed_paths:paths.length ? paths : ["/"]})});
        status.textContent = "Scope saved: " + data.scope.allowed_hosts.join(", ");
        await loadCyberFindings();
    } catch (error) { status.textContent = "❌ " + error.message; }
}

async function runCyberRecon() {
    const raw = document.getElementById("cyberReconUrls").value;
    const urls = raw.split(",").map(function(x){return x.trim();}).filter(Boolean);
    if (!urls.length) { alert("Enter at least one authorized URL."); return; }
    try {
        const data = await cyberRequest("/api/cyber/recon", {method:"POST", body:JSON.stringify({urls:urls, max_requests:5})});
        await loadCyberFindings();
        alert("Recon complete. " + data.findings.length + " candidate finding(s) created.");
    } catch (error) { alert("Recon failed: " + error.message); }
}

async function loadCyberFindings() {
    const box = document.getElementById("cyberFindings");
    if (!box) return;
    try {
        const data = await cyberRequest("/api/cyber/findings");
        box.innerHTML = "";
        if (!data.findings.length) {
            box.innerHTML = '<div class="cyber-status-text">No findings yet. Ask Jiraiya-Cyber to analyze an authorized target.</div>';
            return;
        }
        data.findings.forEach(renderCyberFinding);
    } catch (error) { box.textContent = "❌ " + error.message; }
}

function renderCyberFinding(finding) {
    const box = document.getElementById("cyberFindings");
    const card = document.createElement("div");
    card.className = "cyber-finding";
    const title = document.createElement("div");
    title.className = "cyber-finding-title";
    title.textContent = finding.title;
    const meta = document.createElement("div");
    meta.className = "cyber-finding-meta";
    meta.textContent = finding.vulnerability_type + " · " + (Number(finding.confidence)*100).toFixed(0) + "% confidence\\n" + finding.target + "\\nStatus: " + finding.status;
    const actions = document.createElement("div");
    actions.className = "cyber-finding-actions";
    if (finding.status === "NEEDS_VERIFICATION" || finding.status === "VERIFIED") {
        const btn = document.createElement("button");
        btn.className = "cyber-approve";
        btn.textContent = "Request PoC authorization";
        btn.onclick = function(){ openCyberAuthorization(finding); };
        actions.appendChild(btn);
        const reportBtn = document.createElement("button");
        reportBtn.className = "cyber-secondary";
        reportBtn.textContent = "Generate report";
        reportBtn.onclick = async function(){
            try {
                const data = await cyberRequest("/api/cyber/report/" + encodeURIComponent(finding.id), {method:"POST", body:JSON.stringify({})});
                const blob = new Blob([JSON.stringify(data.report, null, 2)], {type:"application/json"});
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url; a.download = finding.id + "-report.json"; a.click();
                URL.revokeObjectURL(url);
            } catch (error) { alert("Report generation failed: " + error.message); }
        };
        actions.appendChild(reportBtn);
    }
    card.appendChild(title); card.appendChild(meta); card.appendChild(actions); box.appendChild(card);
}

async function openCyberAuthorization(finding) {
    pendingCyberFinding = finding;
    try {
        const data = await cyberRequest("/api/cyber/finding/" + encodeURIComponent(finding.id) + "/authorization", {method:"POST", body:JSON.stringify({action:"controlled_non_destructive_poc", max_attempts:1, expires_in_seconds:300})});
        pendingCyberFinding.authorization = data.authorization;
        cyberModalTitle.textContent = finding.title;
        cyberModalTarget.textContent = finding.target;
        cyberModalAction.textContent = data.authorization.action;
        cyberAuthModal.classList.add("open");
    } catch (error) { alert("Authorization request failed: " + error.message); }
}

async function approveCyberAuthorization() {
    if (!pendingCyberFinding || !pendingCyberFinding.authorization) return;
    try {
        await cyberRequest("/api/cyber/authorization/" + encodeURIComponent(pendingCyberFinding.authorization.id) + "/approve", {method:"POST", body:"{}"});
        cyberModalApprove.style.display = "none";
        cyberModalExecute.style.display = "inline-block";
        alert("Authorization approved. The next button runs one bounded GET verification against the exact authorized target.");
    } catch (error) { alert("Approval failed: " + error.message); }
}

async function executeCyberAuthorization() {
    if (!pendingCyberFinding || !pendingCyberFinding.authorization) return;
    try {
        const auth = pendingCyberFinding.authorization;
        const result = await cyberRequest("/api/cyber/authorization/" + encodeURIComponent(auth.id) + "/consume", {
            method:"POST",
            body:JSON.stringify({finding_id: pendingCyberFinding.id, action:"controlled_non_destructive_poc"})
        });
        cyberAuthModal.classList.remove("open");
        await loadCyberFindings();
        alert("Authorized check completed. Signals: " + ((((result.result && result.result.confirmed_signals) || []).join(", ")) || "none"));
    } catch (error) { alert("Authorized check failed: " + error.message); }
}

function closeCyberAuthorization() {
    pendingCyberFinding = null;
    cyberModalApprove.style.display = "inline-block";
    cyberModalExecute.style.display = "none";
    cyberAuthModal.classList.remove("open");
}

/* ============================================================
   SESSION API
   ============================================================ */

async function createSession(title = "New Chat") {

    const response = await fetch(
        SESSIONS_URL,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title
            })
        }
    );

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(
            data.error ||
            "Unable to create session"
        );
    }

    return data.session;
}


async function loadSessions() {

    try {

        const response = await fetch(
            SESSIONS_URL
        );

        const data = await response.json();

        if (!response.ok || !data.ok) {
            throw new Error(
                data.error ||
                "Unable to load sessions"
            );
        }

        sessions = Array.isArray(
            data.sessions
        )
            ? data.sessions
            : [];

        renderSessionList();

    } catch (error) {

        console.error(
            "Session loading error:",
            error
        );
    }
}


async function loadSession(sessionId) {

    const response = await fetch(
        `${SESSIONS_URL}/${sessionId}`
    );

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(
            data.error ||
            "Unable to load chat"
        );
    }

    return data.session;
}


async function deleteSession(sessionId) {

    const response = await fetch(
        `${SESSIONS_URL}/${sessionId}`,
        {
            method: "DELETE"
        }
    );

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(
            data.error ||
            "Unable to delete chat"
        );
    }

    return true;
}


async function renameSession(
    sessionId,
    title
) {

    const response = await fetch(
        `${SESSIONS_URL}/${sessionId}`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title
            })
        }
    );

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(
            data.error ||
            "Unable to rename chat"
        );
    }

    return data.session;
}


/* ============================================================
   SESSION LIST UI
   ============================================================ */

function renderSessionList() {

    chatHistory.innerHTML = "";

    if (!sessions.length) {
        return;
    }

    sessions.forEach(session => {

        const item =
            document.createElement("div");

        item.className = "chat-item";

        if (
            session.id ===
            currentSessionId
        ) {
            item.classList.add("active");
        }

        item.textContent =
            session.title ||
            "New Chat";

        item.dataset.sessionId =
            session.id;

        item.addEventListener(
            "click",
            () => {
                openSession(session.id);
            }
        );

        chatHistory.appendChild(item);
    });
}


/* ============================================================
   OPEN SESSION
   ============================================================ */

async function openSession(sessionId) {

    try {

        const session =
            await loadSession(sessionId);

        currentSessionId =
            session.id;

        messages = [];

        chatArea.innerHTML = "";

        const storedMessages =
            Array.isArray(session.messages)
                ? session.messages
                : [];

        storedMessages.forEach(item => {

            if (
                item.role !== "user" &&
                item.role !== "assistant"
            ) {
                return;
            }

            const content =
                String(
                    item.content || ""
                );

            messages.push({
                role: item.role,
                content: content
            });

            if (content) {
                addMessage(
                    item.role,
                    content
                );
            }
        });

        if (!storedMessages.length) {
            showWelcome();
        }

        renderSessionList();

        closeSidebarOnMobile();

        messageInput.focus();

    } catch (error) {

        console.error(
            "Open session error:",
            error
        );
    }
}


/* ============================================================
   SEND MESSAGE
   ============================================================ */

async function sendMessage() {

    const message =
        messageInput.value.trim();

    if (
        !message ||
        sendBtn.disabled
    ) {
        return;
    }


    /*
     * Create a session automatically
     * if one does not exist.
     */

    if (!currentSessionId) {

        try {

            const session =
                await createSession(
                    message.slice(0, 40)
                );

            currentSessionId =
                session.id;

            sessions.unshift(session);

            renderSessionList();

        } catch (error) {

            alert(
                "Unable to create chat: " +
                error.message
            );

            return;
        }
    }


    const welcome =
        document.getElementById(
            "welcome"
        );

    if (welcome) {
        welcome.remove();
    }


    addMessage(
        "user",
        message
    );

    messages.push({
        role: "user",
        content: message
    });


    messageInput.value = "";

    messageInput.style.height =
        "auto";

    sendBtn.disabled = true;


    const replyElement =
        addMessage(
            "assistant",
            "Jiraiya is thinking..."
        );


    try {

        /*
         * Send previous conversation
         * WITHOUT duplicating the current
         * message in history.
         */

        const history =
            messages.slice(0, -1);


        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        message: message,
                        history: history,
                        session_id:
                            currentSessionId
                    })
                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.ok
        ) {
            throw new Error(
                data.error ||
                "API request failed"
            );
        }


        const reply =
            data.reply || "";


        replyElement.textContent =
            reply ||
            "No response received.";


        messages.push({
            role: "assistant",
            content: reply
        });


        /*
         * Update session title
         * after first message.
         */

        if (
            messages.length === 2
        ) {

            try {

                const title =
                    message.length > 40
                        ? message.slice(0, 40) + "..."
                        : message;

                await renameSession(
                    currentSessionId,
                    title
                );

            } catch (error) {

                console.warn(
                    "Title update failed:",
                    error
                );
            }
        }


        await loadSessions();

    } catch (error) {

        replyElement.textContent =
            "❌ Connection error: " +
            error.message;

        /*
         * Remove failed assistant
         * message from local history.
         */

        messages.pop();
    }


    sendBtn.disabled = false;

    messageInput.focus();
}


/* ============================================================
   NEW CHAT
   ============================================================ */

async function newChat() {

    try {

        const session =
            await createSession(
                "New Chat"
            );

        currentSessionId =
            session.id;

        messages = [];

        sessions.unshift(session);

        renderSessionList();

        showWelcome();

        closeSidebarOnMobile();

        messageInput.focus();

    } catch (error) {

        alert(
            "Unable to create new chat: " +
            error.message
        );
    }
}


function showWelcome() {

    chatArea.innerHTML = `
        <div class="welcome" id="welcome">
            <div class="welcome-logo">🐸</div>

            <h2>Namaste, I'm Jiraiya.</h2>

            <p>How can I help you today?</p>

            <div class="suggestions">

                <button
                    data-prompt="Explain something to me">
                    💡 Explain something
                </button>

                <button
                    data-prompt="Help me write some code">
                    💻 Help me code
                </button>

                <button
                    data-prompt="Search the web for something">
                    🌐 Search the web
                </button>

                <button
                    data-prompt="Calculate something for me">
                    🧮 Calculate
                </button>

            </div>
        </div>
    `;

    setupSuggestions();
}


/* ============================================================
   MOBILE SIDEBAR
   ============================================================ */

function closeSidebarOnMobile() {

    if (
        window.innerWidth <= 768 &&
        sidebar
    ) {
        sidebar.classList.remove(
            "open"
        );
    }
}


/* ============================================================
   SUGGESTIONS
   ============================================================ */

function setupSuggestions() {

    document
        .querySelectorAll(
            "[data-prompt]"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    messageInput.value =
                        button.dataset.prompt;

                    messageInput.focus();

                    autoResize();
                }
            );
        });
}


/* ============================================================
   INPUT RESIZE
   ============================================================ */

function autoResize() {

    messageInput.style.height =
        "auto";

    messageInput.style.height =
        Math.min(
            messageInput.scrollHeight,
            160
        ) + "px";
}


/* ============================================================
   INITIAL SESSION RESTORE
   ============================================================ */

async function initializeApp() {

    await loadSessions();

    /*
     * Restore most recently updated
     * session automatically.
     */

    if (sessions.length) {

        const lastSession =
            sessions[0];

        try {

            await openSession(
                lastSession.id
            );

        } catch (error) {

            console.error(
                "Session restore error:",
                error
            );

            showWelcome();
        }

    } else {

        showWelcome();
    }
}


/* ============================================================
   EVENT LISTENERS
   ============================================================ */

sendBtn.addEventListener(
    "click",
    sendMessage
);


messageInput.addEventListener(
    "input",
    autoResize
);


messageInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


newChatBtn.addEventListener(
    "click",
    newChat
);


menuBtn.addEventListener(
    "click",
    () => {

        if (sidebar) {

            sidebar.classList.toggle(
                "open"
            );
        }
    }
);


document.getElementById("cyberScopeBtn")?.addEventListener("click", saveCyberScope);\ndocument.getElementById("cyberRefreshBtn")?.addEventListener("click", loadCyberFindings);\ndocument.getElementById("cyberCloseBtn")?.addEventListener("click", function(){toggleCyberPanel(false);});\ndocument.getElementById("cyberModalCancel")?.addEventListener("click", closeCyberAuthorization);\ndocument.getElementById("cyberModalApprove")?.addEventListener("click", approveCyberAuthorization);\ndocument.getElementById("cyberToggleBtn")?.addEventListener("click", function(){toggleCyberPanel(true);});\n\n/* ============================================================
   START
   ============================================================ */

initializeApp();
