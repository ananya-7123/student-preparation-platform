(function () {
    const { escapeHtml } = window.PrepAPI;

    function barColorClass(pct) {
        if (pct >= 70) return "good";
        if (pct >= 45) return "mid";
        return "low";
    }

    async function openAttemptModal(attemptId) {
        window.PrepApp.openModal(
            `Attempt #${attemptId} Breakdown`,
            '<div class="empty-state">Loading attempt details...</div>'
        );
        try {
            const res = await window.PrepAPI.getMockAttempt(attemptId);
            if (!res.results) {
                window.PrepApp.openModal(
                    `Attempt #${attemptId} (In Progress)`,
                    `<div class="alert alert-info">This attempt has ${res.total_questions} questions and has not been submitted yet.</div>`
                );
                return;
            }
            const html = `
                <div style="margin-bottom:12px;font-size:13.5px;">
                    <strong>Score:</strong> ${res.correct_answers}/${res.total_questions} (${res.score_percentage}%) •
                    <strong>Time:</strong> ${res.time_taken_seconds || 0}s
                </div>
                ${res.results
                    .map(
                        (item, idx) => `
                    <div class="result-item ${item.is_correct ? "ok" : "bad"}">
                        <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:4px;">
                            <strong>Q${idx + 1}. ${escapeHtml(item.category)}${item.topic ? ` (${escapeHtml(item.topic)})` : ""}</strong>
                            <span class="badge ${item.is_correct ? "badge-pyq" : "badge-danger"}">
                                ${item.is_correct ? "Correct" : "Incorrect"}
                            </span>
                        </div>
                        <div style="font-size:13.5px;margin-bottom:4px;">${escapeHtml(item.question_text)}</div>
                        <div style="font-size:12.5px;">
                            <strong>Selected:</strong> ${escapeHtml(item.selected_option || "Skipped")} |
                            <strong>Correct:</strong> ${escapeHtml(item.correct_option)}
                        </div>
                        ${item.explanation ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${escapeHtml(item.explanation)}</div>` : ""}
                    </div>
                `
                    )
                    .join("")}
            `;
            window.PrepApp.openModal(`Attempt #${attemptId} Breakdown`, html);
        } catch (err) {
            window.PrepApp.openModal(
                `Attempt #${attemptId}`,
                `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`
            );
        }
    }

    async function loadStudentDashboard(identifier) {
        const area = document.getElementById("perfDashboardArea");
        const cleaned = (identifier || "").trim();
        const currentStudent =
            window.PrepApp.getCurrentStudent ? window.PrepApp.getCurrentStudent() : null;

        if (!cleaned && !currentStudent) {
            await loadRecentOverview();
            return;
        }

        area.innerHTML = '<div class="card"><div class="empty-state">Loading performance analytics...</div></div>';

        try {
            const useOwnEndpoint =
                currentStudent &&
                (!cleaned || cleaned.toLowerCase() === currentStudent.roll_number.toLowerCase());
            const perf = useOwnEndpoint
                ? await window.PrepAPI.getMyPerformance()
                : await window.PrepAPI.getStudentPerformance(cleaned);

            if (perf.total_attempts === 0) {
                area.innerHTML = `
                    <div class="card">
                        <div class="alert alert-info" style="margin-bottom:0;">
                            No mock attempts recorded yet for <strong>${escapeHtml(cleaned)}</strong>. Take a test in the <strong>Mock Test Arena</strong> to generate analytics!
                        </div>
                    </div>
                `;
                return;
            }

            const catHtml = perf.category_breakdown.length
                ? perf.category_breakdown
                      .map(
                          (cat) => `
                        <div style="margin-bottom:12px;">
                            <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:600;">
                                <span>${escapeHtml(cat.category)}</span>
                                <span>${cat.correct}/${cat.attempted} (${cat.accuracy_percentage}%)</span>
                            </div>
                            <div class="bar-track">
                                <div class="bar-fill ${barColorClass(cat.accuracy_percentage)}" style="width:${cat.accuracy_percentage}%"></div>
                            </div>
                        </div>
                    `
                      )
                      .join("")
                : '<div class="empty-state">No completed category metrics yet.</div>';

            const topicRows = perf.topic_breakdown.length
                ? `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Topic</th>
                                <th>Category</th>
                                <th>Score</th>
                                <th>Accuracy</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${perf.topic_breakdown
                                .map(
                                    (t) => `
                                <tr>
                                    <td><strong>${escapeHtml(t.topic)}</strong></td>
                                    <td>${escapeHtml(t.category)}</td>
                                    <td>${t.correct}/${t.attempted}</td>
                                    <td>
                                        <span class="badge ${t.accuracy_percentage >= 70 ? "badge-pyq" : t.accuracy_percentage >= 45 ? "badge-reported" : "badge-danger"}">
                                            ${t.accuracy_percentage}%
                                        </span>
                                    </td>
                                </tr>
                            `
                                )
                                .join("")}
                        </tbody>
                    </table>
                `
                : '<div class="empty-state">Complete at least one mock test to view topic mastery.</div>';

            const attemptRows = perf.recent_attempts
                .map(
                    (a) => `
                    <tr>
                        <td>#${a.attempt_id}</td>
                        <td>${escapeHtml(a.company_name || "Mixed / Any")}</td>
                        <td>${escapeHtml(a.category)}</td>
                        <td>${a.correct_answers}/${a.total_questions}</td>
                        <td><strong>${a.score_percentage}%</strong></td>
                        <td>${a.completed_at ? '<span class="badge badge-pyq">Completed</span>' : '<span class="badge badge-reported">In Progress</span>'}</td>
                        <td>
                            <button class="btn btn-secondary btn-sm view-attempt-btn" data-aid="${a.attempt_id}" type="button">Review</button>
                        </td>
                    </tr>
                `
                )
                .join("");

            area.innerHTML = `
                <div class="grid-4">
                    <div class="kpi-card">
                        <div class="kpi-label">Completed Tests</div>
                        <div class="kpi-value">${perf.completed_attempts}</div>
                        <div class="kpi-sub">Total started: ${perf.total_attempts}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Average Score</div>
                        <div class="kpi-value">${perf.average_score_percentage}%</div>
                        <div class="kpi-sub">Across completed attempts</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Best Score</div>
                        <div class="kpi-value">${perf.best_score_percentage}%</div>
                        <div class="kpi-sub">Personal best</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Questions Answered</div>
                        <div class="kpi-value">${perf.total_questions_answered}</div>
                        <div class="kpi-sub">${perf.total_correct_answers} correct total</div>
                    </div>
                </div>

                <div class="grid-2" style="margin-top:16px;">
                    <div class="card">
                        <div class="card-title">Category-Wise Accuracy</div>
                        <div class="card-subtitle">Accuracy across Aptitude, Reasoning, Verbal, and Technical</div>
                        ${catHtml}
                    </div>
                    <div class="card">
                        <div class="card-title">Topic Breakdown (Weakest First)</div>
                        <div class="card-subtitle">Lowest-accuracy topics appear at the top for targeted revision</div>
                        ${topicRows}
                    </div>
                </div>

                <div class="card" style="margin-top:16px;">
                    <div class="card-title">Recent Mock Attempts</div>
                    <div style="overflow-x:auto;margin-top:10px;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Attempt</th>
                                    <th>Company</th>
                                    <th>Category</th>
                                    <th>Correct</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>${attemptRows}</tbody>
                        </table>
                    </div>
                </div>
            `;

            area.querySelectorAll(".view-attempt-btn").forEach((btn) => {
                btn.addEventListener("click", () => {
                    openAttemptModal(Number(btn.getAttribute("data-aid")));
                });
            });
        } catch (err) {
            area.innerHTML = `<div class="card"><div class="alert alert-danger">${escapeHtml(err.message)}</div></div>`;
        }
    }

    async function loadRecentOverview() {
        const area = document.getElementById("perfDashboardArea");
        try {
            const data = await window.PrepAPI.listRecentAttempts(15);
            const rows = data.attempts || [];
            if (!rows.length) {
                area.innerHTML = '<div class="card"><div class="empty-state">No mock attempts recorded yet. Start a test in the Mock Test Arena!</div></div>';
                return;
            }
            area.innerHTML = `
                <div class="card">
                    <div class="card-title">Recent Platform Mock Attempts</div>
                    <div class="card-subtitle">Click any student to load their detailed category &amp; topic analytics.</div>
                    <div style="overflow-x:auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Attempt</th>
                                    <th>Student</th>
                                    <th>Roll No</th>
                                    <th>Category</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows
                                    .map(
                                        (a) => `
                                    <tr>
                                        <td>#${a.attempt_id}</td>
                                        <td><strong>${escapeHtml(a.student_name)}</strong></td>
                                        <td>${escapeHtml(a.student_roll_number || "-")}</td>
                                        <td>${escapeHtml(a.category)}</td>
                                        <td><strong>${a.score_percentage}%</strong> (${a.correct_answers}/${a.total_questions})</td>
                                        <td>${a.completed_at ? '<span class="badge badge-pyq">Completed</span>' : '<span class="badge badge-reported">In Progress</span>'}</td>
                                        <td>
                                            <button class="btn btn-primary btn-sm load-student-btn" data-id="${escapeHtml(a.student_roll_number || a.student_name)}" type="button">Analytics</button>
                                        </td>
                                    </tr>
                                `
                                    )
                                    .join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            area.querySelectorAll(".load-student-btn").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    document.getElementById("perfSearchInput").value = id;
                    loadStudentDashboard(id);
                });
            });
        } catch (err) {
            area.innerHTML = `<div class="card"><div class="alert alert-danger">${escapeHtml(err.message)}</div></div>`;
        }
    }

    function init() {
        document.getElementById("perfLoadBtn").addEventListener("click", () => {
            loadStudentDashboard(document.getElementById("perfSearchInput").value);
        });
        document.getElementById("perfSearchInput").addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                loadStudentDashboard(e.target.value);
            }
        });
    }

    window.PrepPerformance = {
        init,
        loadStudentDashboard,
    };
})();

