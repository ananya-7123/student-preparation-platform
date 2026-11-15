(function () {
    const { escapeHtml } = window.PrepAPI;

    let allCompanies = [];
    let selectedCompanyName = null;

    function getListContainer() {
        return document.getElementById("companyListContainer");
    }

    function getDetailContainer() {
        return document.getElementById("companyDetailCard");
    }

    function renderCompanyList(filterText = "") {
        const container = getListContainer();
        const term = filterText.trim().toLowerCase();
        const filtered = term
            ? allCompanies.filter(
                  (c) =>
                      c.name.toLowerCase().includes(term) ||
                      (c.industry && c.industry.toLowerCase().includes(term))
              )
            : allCompanies;

        if (!filtered.length) {
            container.innerHTML = '<div class="empty-state">No companies match your search.</div>';
            return;
        }

        container.innerHTML = filtered
            .map((c) => {
                const isActive =
                    selectedCompanyName &&
                    c.name.toLowerCase() === selectedCompanyName.toLowerCase();
                const hasDriveInfo = Boolean(c.industry || c.description);
                return `
                    <div class="company-item ${isActive ? "active" : ""}" data-company="${escapeHtml(c.name)}">
                        <div>
                            <div class="company-item-name">${escapeHtml(c.name)}</div>
                            <div class="company-item-ind">${escapeHtml(c.industry || "Question Bank Company")}</div>
                        </div>
                        <span class="badge ${hasDriveInfo ? "badge-pyq" : "badge-muted"}">
                            ${hasDriveInfo ? "Drive Info" : "Q-Bank"}
                        </span>
                    </div>
                `;
            })
            .join("");

        container.querySelectorAll(".company-item").forEach((el) => {
            el.addEventListener("click", () => {
                const name = el.getAttribute("data-company");
                selectCompany(name);
            });
        });
    }

    async function selectCompany(companyName) {
        selectedCompanyName = companyName;
        renderCompanyList(document.getElementById("companySearchInput").value || "");

        const detailEl = getDetailContainer();
        detailEl.innerHTML = '<div class="empty-state">Loading company details...</div>';

        const [compRes, eligRes, procRes] = await Promise.allSettled([
            window.PrepAPI.getCompany(companyName),
            window.PrepAPI.getEligibility(companyName),
            window.PrepAPI.getSelectionProcess(companyName),
        ]);

        if (compRes.status !== "fulfilled") {
            detailEl.innerHTML = `<div class="alert alert-danger">Failed to load ${escapeHtml(companyName)}: ${escapeHtml(compRes.reason?.message || "Unknown error")}</div>`;
            return;
        }

        const comp = compRes.value;
        const elig = eligRes.status === "fulfilled" ? eligRes.value : null;
        const proc = procRes.status === "fulfilled" ? procRes.value : null;

        let eligHtml = "";
        if (elig) {
            eligHtml = `
                <div class="grid-3" style="margin: 12px 0;">
                    <div class="kpi-card" style="background:var(--surface-muted);">
                        <div class="kpi-label">CGPA Cutoff</div>
                        <div class="kpi-value" style="font-size:20px;">${escapeHtml(elig.cgpa_cutoff)}</div>
                    </div>
                    <div class="kpi-card" style="background:var(--surface-muted);">
                        <div class="kpi-label">Backlogs Allowed</div>
                        <div class="kpi-value" style="font-size:20px;">${escapeHtml(elig.backlogs_allowed)}</div>
                    </div>
                    <div class="kpi-card" style="background:var(--surface-muted);">
                        <div class="kpi-label">Eligible Streams</div>
                        <div style="font-size:13px;font-weight:600;margin-top:4px;">${escapeHtml(elig.branches)}</div>
                    </div>
                </div>
                ${
                    elig.additional_notes
                        ? `<div class="alert alert-info">${escapeHtml(elig.additional_notes)}</div>`
                        : ""
                }
            `;
        } else {
            eligHtml = `
                <div class="alert alert-warning" style="margin-top:10px;">
                    Official KIIT eligibility criteria are not stored for <strong>${escapeHtml(comp.name)}</strong> yet (registered from Question Bank without inventing cutoffs).
                </div>
            `;
        }

        let roundsHtml = "";
        if (proc && Array.isArray(proc.round_details) && proc.round_details.length) {
            roundsHtml = `
                <div class="rounds-list">
                    ${proc.round_details
                        .map(
                            (r) => `
                        <div class="round-item">
                            <div class="round-num">${escapeHtml(r.round_number)}</div>
                            <div>
                                <div style="font-weight:700;font-size:14px;">${escapeHtml(r.round_name)}</div>
                                <div style="font-size:13px;color:var(--text-muted);">${escapeHtml(r.description || "")}</div>
                            </div>
                        </div>
                    `
                        )
                        .join("")}
                </div>
            `;
        } else {
            roundsHtml = `
                <div class="alert alert-info" style="margin-top:10px;">
                    Selection round sequence is not stored in the database for <strong>${escapeHtml(comp.name)}</strong>.
                </div>
            `;
        }

        detailEl.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
                <div>
                    <h2 style="font-size:21px;font-weight:800;">${escapeHtml(comp.name)}</h2>
                    <div style="font-size:13px;color:var(--text-subtle);margin-top:2px;">
                        ${escapeHtml(comp.industry || "Registered in Question Bank")}
                    </div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="btn btn-primary btn-sm" id="btnCompanyQuestions">Browse Questions</button>
                    <button class="btn btn-secondary btn-sm" id="btnCompanyAskAi">Ask AI About ${escapeHtml(comp.name)}</button>
                </div>
            </div>

            ${
                comp.description
                    ? `<p style="margin-top:12px;font-size:14px;color:var(--text-muted);">${escapeHtml(comp.description)}</p>`
                    : ""
            }

            <h3 style="margin-top:20px;font-size:15px;font-weight:700;">Eligibility Criteria</h3>
            ${eligHtml}

            <h3 style="margin-top:18px;font-size:15px;font-weight:700;">Selection Process</h3>
            ${roundsHtml}
        `;

        document.getElementById("btnCompanyQuestions").addEventListener("click", () => {
            window.PrepApp.openQuestionsForCompany(comp.name);
        });
        document.getElementById("btnCompanyAskAi").addEventListener("click", () => {
            window.PrepApp.openAgentForCompany(comp.name);
        });
    }

    async function loadCompanies() {
        try {
            allCompanies = await window.PrepAPI.getCompanies();
            document.getElementById("kpiCompaniesTotal").textContent = allCompanies.length;
            renderCompanyList(document.getElementById("companySearchInput").value || "");

            if (!selectedCompanyName && allCompanies.length) {
                const preferred =
                    allCompanies.find((c) => c.name === "TCS") || allCompanies[0];
                selectCompany(preferred.name);
            }
            return allCompanies;
        } catch (err) {
            getListContainer().innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
            return [];
        }
    }

    function init() {
        const searchInput = document.getElementById("companySearchInput");
        searchInput.addEventListener("input", () => {
            renderCompanyList(searchInput.value);
        });
    }

    window.PrepCompanies = {
        init,
        loadCompanies,
        selectCompany,
        getAllCompanies: () => allCompanies,
    };
})();

