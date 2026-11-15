(function () {
    const { escapeHtml } = window.PrepAPI;

    const PAGE_SIZE = 20;
    let currentOffset = 0;
    let totalMatching = 0;
    let filtersLoaded = false;

    function badgeClassForType(qType) {
        const t = (qType || "").toUpperCase();
        if (t === "PYQ") return "badge-pyq";
        if (t === "REPORTED") return "badge-reported";
        return "badge-practice";
    }

    async function loadFilters() {
        try {
            const data = await window.PrepAPI.getQuestionFilters();
            document.getElementById("kpiQuestionsTotal").textContent = data.total_questions;
            document.getElementById("kpiMcqTotal").textContent = data.total_mcqs;

            const compSelect = document.getElementById("qFilterCompany");
            compSelect.innerHTML = '<option value="">All Companies</option>';
            if (data.has_common_questions) {
                compSelect.innerHTML += '<option value="Common">Common / Multiple Companies</option>';
            }
            (data.companies || []).forEach((name) => {
                compSelect.innerHTML += `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`;
            });

            const catSelect = document.getElementById("qFilterCategory");
            catSelect.innerHTML = '<option value="">All Categories</option>';
            (data.categories || []).forEach((cat) => {
                catSelect.innerHTML += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
            });

            const typeSelect = document.getElementById("qFilterType");
            typeSelect.innerHTML = `
                <option value="">All Types</option>
                <option value="PYQ">PYQ</option>
                <option value="PRACTICE">PRACTICE</option>
                <option value="REPORTED">REPORTED</option>
            `;

            filtersLoaded = true;
            return data;
        } catch (err) {
            console.error("Failed to load question filters:", err);
            return null;
        }
    }

    function readCurrentFilterParams() {
        return {
            company_name: document.getElementById("qFilterCompany").value,
            category: document.getElementById("qFilterCategory").value,
            question_type: document.getElementById("qFilterType").value,
            difficulty: document.getElementById("qFilterDifficulty").value,
            mcq_only: document.getElementById("qFilterMcq").value,
            search: document.getElementById("qFilterSearch").value.trim(),
            limit: PAGE_SIZE,
            offset: currentOffset,
        };
    }

    async function loadQuestions() {
        if (!filtersLoaded) {
            await loadFilters();
        }
        const listEl = document.getElementById("questionListContainer");
        listEl.innerHTML = '<div class="empty-state">Loading questions...</div>';

        try {
            const data = await window.PrepAPI.listQuestions(readCurrentFilterParams());
            totalMatching = data.total || 0;
            const rows = data.questions || [];

            const startIdx = totalMatching === 0 ? 0 : currentOffset + 1;
            const endIdx = Math.min(currentOffset + rows.length, totalMatching);
            document.getElementById("qSummaryLine").textContent =
                `Showing ${startIdx}–${endIdx} of ${totalMatching} matching questions`;

            const pageNum = Math.floor(currentOffset / PAGE_SIZE) + 1;
            const totalPages = Math.max(1, Math.ceil(totalMatching / PAGE_SIZE));
            document.getElementById("qPageInfo").textContent = `Page ${pageNum} of ${totalPages}`;
            document.getElementById("qPrevBtn").disabled = currentOffset === 0;
            document.getElementById("qNextBtn").disabled = currentOffset + PAGE_SIZE >= totalMatching;

            if (!rows.length) {
                listEl.innerHTML = '<div class="empty-state">No questions matched the selected filters.</div>';
                return;
            }

            listEl.innerHTML = rows
                .map((q) => {
                    const isMcq = Boolean(q.correct_option && q.option_a && q.option_b && q.option_c && q.option_d);
                    const typeUpper = (q.question_type || "").toUpperCase();
                    const reportedTooltip =
                        typeUpper === "REPORTED"
                            ? 'title="Candidate-reported experience question (not an official verified company paper)"'
                            : "";

                    let optionsHtml = "";
                    if (isMcq) {
                        optionsHtml = `
                            <div class="options-preview">
                                <div class="option-chip"><strong>A.</strong> ${escapeHtml(q.option_a)}</div>
                                <div class="option-chip"><strong>B.</strong> ${escapeHtml(q.option_b)}</div>
                                <div class="option-chip"><strong>C.</strong> ${escapeHtml(q.option_c)}</div>
                                <div class="option-chip"><strong>D.</strong> ${escapeHtml(q.option_d)}</div>
                            </div>
                            <button class="btn btn-secondary btn-sm toggle-ans-btn" type="button" data-qid="${q.id}">
                                Show Answer &amp; Explanation
                            </button>
                            <div id="ansDrawer-${q.id}" class="answer-drawer" style="display:none;">
                                <strong>Correct Answer: Option ${escapeHtml(q.correct_option)}</strong>
                                ${
                                    q.explanation
                                        ? `<div style="margin-top:4px;">${escapeHtml(q.explanation)}</div>`
                                        : ""
                                }
                            </div>
                        `;
                    }

                    return `
                        <div class="question-card">
                            <div class="question-meta">
                                <span class="badge ${badgeClassForType(q.question_type)}" ${reportedTooltip}>
                                    ${escapeHtml(typeUpper)}
                                </span>
                                <span class="badge badge-info">${escapeHtml(q.company_name || "Common")}</span>
                                <span class="badge badge-muted">${escapeHtml(q.category)}</span>
                                ${q.topic ? `<span class="badge badge-muted">${escapeHtml(q.topic)}</span>` : ""}
                                <span class="badge badge-muted">${escapeHtml(q.difficulty)}</span>
                                <span class="badge ${isMcq ? "badge-pyq" : "badge-muted"}">
                                    ${isMcq ? "MCQ" : "Non-MCQ / Coding"}
                                </span>
                            </div>
                            <div class="question-body">${escapeHtml(q.question_text)}</div>
                            ${optionsHtml}
                            ${
                                q.source
                                    ? `<div class="question-source" style="margin-top:8px;">Source: ${escapeHtml(q.source)}</div>`
                                    : ""
                            }
                        </div>
                    `;
                })
                .join("");

            listEl.querySelectorAll(".toggle-ans-btn").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const qid = btn.getAttribute("data-qid");
                    const drawer = document.getElementById(`ansDrawer-${qid}`);
                    const visible = drawer.style.display === "block";
                    drawer.style.display = visible ? "none" : "block";
                    btn.textContent = visible ? "Show Answer & Explanation" : "Hide Answer";
                });
            });
        } catch (err) {
            listEl.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }

    function openAddQuestionModal() {
        const companies = window.PrepCompanies ? window.PrepCompanies.getAllCompanies() : [];
        const optionsHtml = companies
            .map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
            .join("");

        window.PrepApp.openModal(
            "Add Question to Question Bank",
            `
            <form id="addQuestionForm">
                <div class="grid-2" style="margin-bottom:12px;">
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Company (Optional)</label>
                        <select id="addQCompany" class="select" style="width:100%;">
                            <option value="">Common / General</option>
                            ${optionsHtml}
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Category *</label>
                        <select id="addQCategory" class="select" style="width:100%;" required>
                            <option value="Aptitude">Aptitude</option>
                            <option value="Reasoning">Reasoning</option>
                            <option value="Verbal">Verbal</option>
                            <option value="Technical">Technical</option>
                            <option value="Coding">Coding</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Topic</label>
                        <input id="addQTopic" class="input" style="width:100%;" type="text" placeholder="e.g. Arrays, DBMS, Probability" />
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Question Type</label>
                        <select id="addQType" class="select" style="width:100%;">
                            <option value="PRACTICE">PRACTICE</option>
                            <option value="PYQ">PYQ</option>
                            <option value="REPORTED">REPORTED</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Difficulty</label>
                        <select id="addQDifficulty" class="select" style="width:100%;">
                            <option value="Easy">Easy</option>
                            <option value="Medium" selected>Medium</option>
                            <option value="Hard">Hard</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Source</label>
                        <input id="addQSource" class="input" style="width:100%;" type="text" placeholder="e.g. Internal Practice or Notice" />
                    </div>
                </div>

                <div style="margin-bottom:10px;">
                    <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Question Text *</label>
                    <textarea id="addQText" class="textarea" rows="3" style="width:100%;" required placeholder="Enter full question prompt..."></textarea>
                </div>

                <div style="font-size:12px;font-weight:700;margin:10px 0 6px;color:var(--text-muted);">
                    MCQ Options (Optional — fill all 4 + Correct Option to make it mock-eligible)
                </div>
                <div class="grid-2" style="margin-bottom:10px;">
                    <input id="addQOptA" class="input" type="text" placeholder="Option A" />
                    <input id="addQOptB" class="input" type="text" placeholder="Option B" />
                    <input id="addQOptC" class="input" type="text" placeholder="Option C" />
                    <input id="addQOptD" class="input" type="text" placeholder="Option D" />
                </div>
                <div class="grid-2" style="margin-bottom:12px;">
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Correct Option</label>
                        <select id="addQCorrect" class="select" style="width:100%;">
                            <option value="">None (Non-MCQ)</option>
                            <option value="A">A</option>
                            <option value="B">B</option>
                            <option value="C">C</option>
                            <option value="D">D</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;font-size:12px;font-weight:600;margin-bottom:4px;">Explanation</label>
                        <input id="addQExp" class="input" style="width:100%;" type="text" placeholder="Why this answer is correct..." />
                    </div>
                </div>

                <div id="addQError" class="alert alert-danger" style="display:none;"></div>
                <button type="submit" class="btn btn-primary">Save Question</button>
            </form>
        `
        );

        document.getElementById("addQuestionForm").addEventListener("submit", async (e) => {
            e.preventDefault();
            const errBox = document.getElementById("addQError");
            errBox.style.display = "none";

            const companyVal = document.getElementById("addQCompany").value;
            const payload = {
                company_id: companyVal ? Number(companyVal) : null,
                category: document.getElementById("addQCategory").value,
                topic: document.getElementById("addQTopic").value.trim() || null,
                difficulty: document.getElementById("addQDifficulty").value,
                question_type: document.getElementById("addQType").value,
                source: document.getElementById("addQSource").value.trim() || null,
                question_text: document.getElementById("addQText").value.trim(),
                option_a: document.getElementById("addQOptA").value.trim() || null,
                option_b: document.getElementById("addQOptB").value.trim() || null,
                option_c: document.getElementById("addQOptC").value.trim() || null,
                option_d: document.getElementById("addQOptD").value.trim() || null,
                correct_option: document.getElementById("addQCorrect").value || null,
                explanation: document.getElementById("addQExp").value.trim() || null,
            };

            try {
                await window.PrepAPI.createQuestion(payload);
                window.PrepApp.closeModal();
                filtersLoaded = false;
                currentOffset = 0;
                await loadQuestions();
            } catch (err) {
                errBox.textContent = err.message;
                errBox.style.display = "block";
            }
        });
    }

    function filterByCompany(companyName) {
        currentOffset = 0;
        const sel = document.getElementById("qFilterCompany");
        if (sel) sel.value = companyName;
        loadQuestions();
    }

    function init() {
        document.getElementById("qApplyFiltersBtn").addEventListener("click", () => {
            currentOffset = 0;
            loadQuestions();
        });

        document.getElementById("qFilterSearch").addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                currentOffset = 0;
                loadQuestions();
            }
        });

        document.getElementById("qResetFiltersBtn").addEventListener("click", () => {
            document.getElementById("qFilterCompany").value = "";
            document.getElementById("qFilterCategory").value = "";
            document.getElementById("qFilterType").value = "";
            document.getElementById("qFilterDifficulty").value = "";
            document.getElementById("qFilterMcq").value = "";
            document.getElementById("qFilterSearch").value = "";
            currentOffset = 0;
            loadQuestions();
        });

        document.getElementById("qPrevBtn").addEventListener("click", () => {
            if (currentOffset >= PAGE_SIZE) {
                currentOffset -= PAGE_SIZE;
                loadQuestions();
            }
        });

        document.getElementById("qNextBtn").addEventListener("click", () => {
            if (currentOffset + PAGE_SIZE < totalMatching) {
                currentOffset += PAGE_SIZE;
                loadQuestions();
            }
        });

        document
            .getElementById("openAddQuestionBtn")
            .addEventListener("click", openAddQuestionModal);
    }

    window.PrepQuestions = {
        init,
        loadFilters,
        loadQuestions,
        filterByCompany,
    };
})();

