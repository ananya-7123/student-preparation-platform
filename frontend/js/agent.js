(function () {
    const { escapeHtml, renderSimpleMarkdown } = window.PrepAPI;

    const chatHistory = [];

    function appendChatMessage(role, content, meta = null) {
        const container = document.getElementById("agentChatMessages");
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-msg ${role}`;

        if (role === "user") {
            msgDiv.textContent = content;
        } else {
            let metaHtml = "";
            if (meta) {
                const modeLabel =
                    meta.mode === "langgraph_gemini"
                        ? "LangGraph + Gemini"
                        : "Database + Document RAG";
                const toolsBadges = (meta.tools_used || [])
                    .map((t) => `<span class="badge badge-info">${escapeHtml(t)}</span>`)
                    .join(" ");
                const sourcesList =
                    meta.sources && meta.sources.length
                        ? `<div style="width:100%;margin-top:4px;">Sources: ${meta.sources
                              .map((s) => `<code>${escapeHtml(s)}</code>`)
                              .join(", ")}</div>`
                        : "";
                metaHtml = `
                    <div class="chat-meta">
                        <span class="badge badge-muted">${modeLabel}</span>
                        ${toolsBadges}
                        ${sourcesList}
                    </div>
                `;
            }
            msgDiv.innerHTML = renderSimpleMarkdown(content) + metaHtml;
        }

        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    }

    async function sendChatMessage(customText = null) {
        const input = document.getElementById("agentMessageInput");
        const message = (customText !== null ? customText : input.value).trim();
        if (!message) return;

        if (customText === null) {
            input.value = "";
        }

        appendChatMessage("user", message);

        const companyHint = document.getElementById("agentCompanyHint").value || null;
        const profile = window.PrepApp.getStudentProfile();
        const studentIdentifier = profile.roll || profile.name || null;

        const sendBtn = document.getElementById("agentSendBtn");
        sendBtn.disabled = true;
        sendBtn.textContent = "Thinking...";

        try {
            const data = await window.PrepAPI.chatAgent({
                message,
                company_name: companyHint,
                student_identifier: studentIdentifier,
                history: chatHistory.slice(-6),
            });

            chatHistory.push({ role: "user", content: message });
            chatHistory.push({ role: "assistant", content: data.response });

            appendChatMessage("assistant", data.response, {
                mode: data.mode,
                tools_used: data.tools_used,
                sources: data.sources,
            });
        } catch (err) {
            appendChatMessage("assistant", `**Error:** ${err.message}`);
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = "Send";
        }
    }

    async function runRagSearch() {
        const query = document.getElementById("ragQueryInput").value.trim();
        const company = document.getElementById("ragCompanySelect").value;
        const container = document.getElementById("ragResultsContainer");

        if (!query) {
            container.innerHTML = '<div class="alert alert-warning">Enter a search query first.</div>';
            return;
        }

        container.innerHTML = '<div class="empty-state">Searching indexed documents...</div>';

        try {
            const res = await window.PrepAPI.searchRagDocs(query, company, 4);
            if (!res.results || !res.results.length) {
                container.innerHTML = '<div class="empty-state">No matching document excerpts found.</div>';
                return;
            }

            container.innerHTML = res.results
                .map(
                    (c) => `
                <div style="border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;background:var(--surface-muted);">
                    <div style="display:flex;justify-content:space-between;gap:6px;margin-bottom:4px;">
                        <span class="badge badge-info">${escapeHtml(c.company)}</span>
                        <span class="badge badge-muted">Score: ${c.score}</span>
                    </div>
                    <div style="font-weight:600;font-size:11.5px;color:var(--text-muted);margin-bottom:4px;">
                        ${escapeHtml(c.source_file)}${c.page ? ` (p.${c.page})` : ""}
                    </div>
                    <div style="white-space:pre-line;line-height:1.45;">${escapeHtml(c.content)}</div>
                </div>
            `
                )
                .join("");
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }

    function populateCompanyHints(companies) {
        const hintSelect = document.getElementById("agentCompanyHint");
        const cur = hintSelect.value;
        hintSelect.innerHTML = '<option value="">Auto-detect company</option>';
        (companies || []).forEach((c) => {
            hintSelect.innerHTML += `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>`;
        });
        if (cur) hintSelect.value = cur;
    }

    function populateRagCompanies(indexedCompanies) {
        const ragSelect = document.getElementById("ragCompanySelect");
        ragSelect.innerHTML = '<option value="">All Indexed Companies</option>';
        (indexedCompanies || []).forEach((name) => {
            ragSelect.innerHTML += `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`;
        });
    }

    function init() {
        document.getElementById("agentSendBtn").addEventListener("click", () => sendChatMessage());
        document.getElementById("agentMessageInput").addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendChatMessage();
        });

        document.querySelectorAll(".chip-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const prompt = btn.getAttribute("data-prompt");
                sendChatMessage(prompt);
            });
        });

        document.getElementById("ragSearchBtn").addEventListener("click", runRagSearch);
        document.getElementById("ragQueryInput").addEventListener("keydown", (e) => {
            if (e.key === "Enter") runRagSearch();
        });
    }

    window.PrepAgent = {
        init,
        populateCompanyHints,
        populateRagCompanies,
        sendChatMessage,
    };
})();

