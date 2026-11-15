(function () {
    const { escapeHtml } = window.PrepAPI;

    let activeAttempt = null;
    let currentIndex = 0;
    let selectedAnswers = {}; // question_id -> "A" | "B" | "C" | "D"
    let timerInterval = null;
    let elapsedSeconds = 0;

    function formatTimer(secs) {
        const mins = String(Math.floor(secs / 60)).padStart(2, "0");
        const rem = String(secs % 60).padStart(2, "0");
        return `${mins}:${rem}`;
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function startTimer() {
        stopTimer();
        elapsedSeconds = 0;
        document.getElementById("mockTimerDisplay").textContent = "00:00";
        timerInterval = setInterval(() => {
            elapsedSeconds += 1;
            document.getElementById("mockTimerDisplay").textContent = formatTimer(elapsedSeconds);
        }, 1000);
    }

    function populateCompanyDropdown(companies) {
        const select = document.getElementById("mockCompany");
        const current = select.value;
        select.innerHTML = '<option value="">Any Company</option>';
        (companies || []).forEach((c) => {
            select.innerHTML += `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>`;
        });
        if (current) select.value = current;
    }

    function renderActiveQuestion() {
        if (!activeAttempt || !activeAttempt.questions.length) return;
        const total = activeAttempt.questions.length;
        const q = activeAttempt.questions[currentIndex];

        // Question Pills
        const pillsEl = document.getElementById("mockQuestionPills");
        pillsEl.innerHTML = activeAttempt.questions
            .map((item, idx) => {
                const isAnswered = Boolean(selectedAnswers[item.id]);
                const cls = idx === currentIndex ? "current" : isAnswered ? "answered" : "";
                return `<button class="q-pill ${cls}" type="button" data-idx="${idx}">${idx + 1}</button>`;
            })
            .join("");

        pillsEl.querySelectorAll(".q-pill").forEach((pill) => {
            pill.addEventListener("click", () => {
                currentIndex = Number(pill.getAttribute("data-idx"));
                renderActiveQuestion();
            });
        });

        const chosen = selectedAnswers[q.id] || null;
        const options = [
            ["A", q.option_a],
            ["B", q.option_b],
            ["C", q.option_c],
            ["D", q.option_d],
        ];

        document.getElementById("mockQuestionStage").innerHTML = `
            <div class="question-meta">
                <span class="badge badge-practice">Question ${currentIndex + 1} of ${total}</span>
                <span class="badge badge-info">${escapeHtml(q.company_name || "Common")}</span>
                <span class="badge badge-muted">${escapeHtml(q.category)}</span>
                ${q.topic ? `<span class="badge badge-muted">${escapeHtml(q.topic)}</span>` : ""}
                <span class="badge badge-muted">${escapeHtml(q.difficulty)}</span>
            </div>
            <div class="question-body" style="font-size:15.5px;margin-bottom:16px;">${escapeHtml(q.question_text)}</div>
            <div>
                ${options
                    .map(
                        ([letter, text]) => `
                    <label class="mock-option-label ${chosen === letter ? "selected" : ""}">
                        <input type="radio" name="mockQ_${q.id}" value="${letter}" ${chosen === letter ? "checked" : ""} />
                        <span><strong>${letter}.</strong> ${escapeHtml(text)}</span>
                    </label>
                `
                    )
                    .join("")}
            </div>
        `;

        document
            .querySelectorAll(`input[name="mockQ_${q.id}"]`)
            .forEach((radio) => {
                radio.addEventListener("change", (e) => {
                    selectedAnswers[q.id] = e.target.value;
                    renderActiveQuestion();
                });
            });

        document.getElementById("mockPrevQBtn").disabled = currentIndex === 0;
        document.getElementById("mockNextQBtn").disabled = currentIndex === total - 1;
    }

    function renderResults(res) {
        stopTimer();
        document.getElementById("mockActiveCard").style.display = "none";
        const resCard = document.getElementById("mockResultCard");
        resCard.style.display = "block";

        const badgeType =
            res.score_percentage >= 70
                ? "badge-pyq"
                : res.score_percentage >= 40
                ? "badge-reported"
                : "badge-danger";

        resCard.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;">
                <div>
                    <h2 style="font-size:20px;font-weight:800;">Mock Test Results (Attempt #${res.attempt_id})</h2>
                    <div style="font-size:13px;color:var(--text-subtle);">
                        ${escapeHtml(res.student_name)} ${res.student_roll_number ? `(${escapeHtml(res.student_roll_number)})` : ""} • Time Taken: ${escapeHtml(res.time_taken_seconds || 0)}s
                    </div>
                </div>
                <div style="display:flex;gap:10px;align-items:center;">
                    <span class="badge ${badgeType}" style="font-size:14px;padding:6px 14px;">
                        ${res.correct_answers} / ${res.total_questions} Correct (${res.score_percentage}%)
                    </span>
                    <button id="mockTakeAnotherBtn" class="btn btn-primary btn-sm" type="button">New Mock Test</button>
                    <button id="mockGoPerfBtn" class="btn btn-secondary btn-sm" type="button">View Analytics</button>
                </div>
            </div>

            <div>
                ${(res.results || [])
                    .map(
                        (item, idx) => `
                    <div class="result-item ${item.is_correct ? "ok" : "bad"}">
                        <div style="display:flex;justify-content:space-between;gap:10px;margin-bottom:6px;flex-wrap:wrap;">
                            <strong>Q${idx + 1}. ${escapeHtml(item.category)} ${item.topic ? `(${escapeHtml(item.topic)})` : ""}</strong>
                            <span class="badge ${item.is_correct ? "badge-pyq" : "badge-danger"}">
                                ${item.is_correct ? "Correct" : "Incorrect"}
                            </span>
                        </div>
                        <div style="font-size:14px;margin-bottom:8px;">${escapeHtml(item.question_text)}</div>
                        <div style="font-size:13px;margin-bottom:6px;">
                            <strong>Your Answer:</strong> ${escapeHtml(item.selected_option || "Skipped")} &nbsp;|&nbsp;
                            <strong>Correct Answer:</strong> ${escapeHtml(item.correct_option)}
                        </div>
                        ${
                            item.explanation
                                ? `<div style="font-size:12.5px;color:var(--text-muted);background:var(--surface-muted);padding:8px 10px;border-radius:6px;">
                                    <strong>Explanation:</strong> ${escapeHtml(item.explanation)}
                                   </div>`
                                : ""
                        }
                    </div>
                `
                    )
                    .join("")}
            </div>
        `;

        document.getElementById("mockTakeAnotherBtn").addEventListener("click", () => {
            resCard.style.display = "none";
            document.getElementById("mockSetupCard").style.display = "block";
        });

        document.getElementById("mockGoPerfBtn").addEventListener("click", () => {
            const identifier = res.student_roll_number || res.student_name;
            window.PrepApp.openPerformanceForStudent(identifier);
        });
    }

    async function handleStartMock() {
        const errEl = document.getElementById("mockSetupError");
        errEl.style.display = "none";

        const currentStudent = window.PrepApp.getCurrentStudent ? window.PrepApp.getCurrentStudent() : null;
        const studentName =
            document.getElementById("mockStudentName").value.trim() ||
            (currentStudent ? currentStudent.full_name : "");
        const studentRoll =
            document.getElementById("mockStudentRoll").value.trim() ||
            (currentStudent ? currentStudent.roll_number : "");

        if (!studentName) {
            errEl.textContent = "Please enter your Student Name before starting.";
            errEl.style.display = "block";
            return;
        }

        // Sync guest profile cleanly when not signed in
        window.PrepApp.setStudentProfile(studentName, studentRoll);

        const payload = {
            student_name: studentName,
            student_roll_number: studentRoll || null,
            company_name: document.getElementById("mockCompany").value || null,
            category: document.getElementById("mockCategory").value || "Mixed",
            difficulty: document.getElementById("mockDifficulty").value || null,
            num_questions: Number(document.getElementById("mockNumQuestions").value),
        };

        const btn = document.getElementById("startMockBtn");
        btn.disabled = true;
        btn.textContent = "Generating Mock Test...";

        try {
            const attempt = await window.PrepAPI.startMockTest(payload);
            activeAttempt = attempt;
            currentIndex = 0;
            selectedAnswers = {};

            document.getElementById("mockSetupCard").style.display = "none";
            document.getElementById("mockResultCard").style.display = "none";
            document.getElementById("mockActiveCard").style.display = "block";

            document.getElementById("mockActiveTitle").textContent =
                `Attempt #${attempt.attempt_id} — ${attempt.category}`;
            document.getElementById("mockActiveMeta").textContent =
                `Student: ${attempt.student_name}${attempt.company_name ? ` | Company: ${attempt.company_name}` : ""} | ${attempt.total_questions} Questions`;

            startTimer();
            renderActiveQuestion();
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.textContent = "Start Mock Test";
        }
    }

    async function handleSubmitMock() {
        if (!activeAttempt) return;
        const btn = document.getElementById("submitMockBtn");
        btn.disabled = true;
        btn.textContent = "Submitting...";

        const answersPayload = activeAttempt.questions.map((q) => ({
            question_id: q.id,
            selected_option: selectedAnswers[q.id] || null,
        }));

        try {
            const res = await window.PrepAPI.submitMockTest(activeAttempt.attempt_id, {
                answers: answersPayload,
                time_taken_seconds: elapsedSeconds,
            });
            activeAttempt = null;
            renderResults(res);
        } catch (err) {
            alert(`Failed to submit mock test: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = "Submit Mock Test";
        }
    }

    function syncProfileInputs(name, roll, force = false) {
        const nameInput = document.getElementById("mockStudentName");
        const rollInput = document.getElementById("mockStudentRoll");
        if (name && (force || !nameInput.value.trim())) nameInput.value = name;
        if (roll && (force || !rollInput.value.trim())) rollInput.value = roll;
    }

    function init() {
        document.getElementById("startMockBtn").addEventListener("click", handleStartMock);
        document.getElementById("submitMockBtn").addEventListener("click", handleSubmitMock);
        document.getElementById("mockPrevQBtn").addEventListener("click", () => {
            if (currentIndex > 0) {
                currentIndex -= 1;
                renderActiveQuestion();
            }
        });
        document.getElementById("mockNextQBtn").addEventListener("click", () => {
            if (activeAttempt && currentIndex < activeAttempt.questions.length - 1) {
                currentIndex += 1;
                renderActiveQuestion();
            }
        });
    }

    window.PrepMock = {
        init,
        populateCompanyDropdown,
        syncProfileInputs,
    };
})();

