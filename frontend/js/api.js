/**
 * Centralized API client for Student Preparation Platform.
 * Automatically works when served via FastAPI (/ui) OR standalone/file:// on localhost:8000.
 */

const API_BASE = window.location.port === "8000" ? "" : "http://127.0.0.1:8000";
const AUTH_TOKEN_KEY = "kiit_prep_auth_token";

function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function setAuthToken(token) {
    if (token) {
        localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
        localStorage.removeItem(AUTH_TOKEN_KEY);
    }
}

async function apiRequest(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const token = getAuthToken();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };
    if (token && !headers.Authorization) {
        headers.Authorization = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    const response = await fetch(url, config);
    let data = null;
    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        if (response.status === 401 && token && !path.startsWith("/auth/login")) {
            setAuthToken("");
        }
        const message =
            (data && (data.detail || data.error || data.message)) ||
            `Request failed (${response.status})`;
        const err = new Error(typeof message === "string" ? message : JSON.stringify(message));
        err.status = response.status;
        throw err;
    }

    return data;
}

function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderSimpleMarkdown(mdText) {
    if (!mdText) return "";
    const safe = escapeHtml(mdText);
    const lines = safe.split(/\r?\n/);
    let html = "";
    let inList = false;

    const closeList = () => {
        if (inList) {
            html += "</ul>";
            inList = false;
        }
    };

    const formatInline = (line) =>
        line
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");

    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) {
            closeList();
            continue;
        }
        if (line === "---") {
            closeList();
            html += '<hr style="border:none;border-top:1px solid #e2e8f0;margin:8px 0;" />';
            continue;
        }
        if (line.startsWith("### ")) {
            closeList();
            html += `<h3>${formatInline(line.slice(4))}</h3>`;
            continue;
        }
        if (line.startsWith("## ")) {
            closeList();
            html += `<h3>${formatInline(line.slice(3))}</h3>`;
            continue;
        }
        if (line.startsWith("- ") || line.startsWith("* ") || /^\d+\.\s/.test(line)) {
            if (!inList) {
                html += "<ul>";
                inList = true;
            }
            const itemText = line.replace(/^(-|\*|\d+\.)\s+/, "");
            html += `<li>${formatInline(itemText)}</li>`;
            continue;
        }
        closeList();
        html += `<p style="margin:4px 0;">${formatInline(line)}</p>`;
    }
    closeList();
    return html;
}

window.PrepAPI = {
    apiRequest,
    escapeHtml,
    renderSimpleMarkdown,
    getAuthToken,
    setAuthToken,
    getHealth: () => apiRequest("/health"),
    // Auth
    signup: (payload) =>
        apiRequest("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
    login: (payload) =>
        apiRequest("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
    getMe: () => apiRequest("/auth/me"),
    // Companies
    getCompanies: () => apiRequest("/companies/"),
    getCompany: (name) => apiRequest(`/companies/${encodeURIComponent(name)}`),
    getEligibility: (name) => apiRequest(`/companies/${encodeURIComponent(name)}/eligibility`),
    getSelectionProcess: (name) => apiRequest(`/companies/${encodeURIComponent(name)}/selection-process`),
    // Questions
    getQuestionFilters: () => apiRequest("/questions/filters"),
    listQuestions: (params = {}) => {
        const qs = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== "") {
                qs.append(k, String(v));
            }
        });
        return apiRequest(`/questions/?${qs.toString()}`);
    },
    createQuestion: (payload) =>
        apiRequest("/questions/", { method: "POST", body: JSON.stringify(payload) }),
    // Mock Test
    startMockTest: (payload) =>
        apiRequest("/mock/start", { method: "POST", body: JSON.stringify(payload) }),
    submitMockTest: (attemptId, payload) =>
        apiRequest(`/mock/${attemptId}/submit`, { method: "POST", body: JSON.stringify(payload) }),
    getMockAttempt: (attemptId) => apiRequest(`/mock/${attemptId}`),
    // Performance
    getMyPerformance: () => apiRequest("/performance/me"),
    getStudentPerformance: (identifier) =>
        apiRequest(`/performance/${encodeURIComponent(identifier)}`),
    listRecentAttempts: (limit = 15) => apiRequest(`/performance/?limit=${limit}`),
    // AI Agent & RAG
    chatAgent: (payload) =>
        apiRequest("/agent/chat", { method: "POST", body: JSON.stringify(payload) }),
    getRagStatus: () => apiRequest("/agent/rag/status"),
    searchRagDocs: (query, companyName = "", topK = 4) => {
        const qs = new URLSearchParams({ query, top_k: String(topK) });
        if (companyName) qs.append("company_name", companyName);
        return apiRequest(`/agent/rag/search?${qs.toString()}`);
    },
};

