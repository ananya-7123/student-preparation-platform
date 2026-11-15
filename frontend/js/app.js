(function () {
    const VIEW_META = {
        companies: {
            title: "Company Explorer",
            subtitle: "Verified KIIT placement eligibility, selection rounds, and registered companies",
        },
        questions: {
            title: "Question Bank",
            subtitle: "Filter MCQ and non-MCQ practice, PYQ, and candidate-reported questions",
        },
        mock: {
            title: "Mock Test Arena",
            subtitle: "Take timed MCQ mock tests with post-submission scoring and explanations",
        },
        performance: {
            title: "Performance Tracker",
            subtitle: "Track attempt history, category accuracy, and weak topics needing revision",
        },
        agent: {
            title: "AI Placement Assistant & Docs",
            subtitle: "Ask LangGraph + PostgreSQL + Recruitment PDF RAG questions",
        },
    };

    const STORAGE_KEY = "kiit_prep_student_profile";
    const GUEST_MODE_KEY = "kiit_prep_guest_mode";

    let currentStudent = null;
    let initialDataLoaded = false;

    function getCurrentStudent() {
        return currentStudent;
    }

    function getStudentProfile() {
        if (currentStudent) {
            return {
                name: currentStudent.full_name || "",
                roll: currentStudent.roll_number || "",
                branch: currentStudent.branch || "",
                cgpa: currentStudent.cgpa,
            };
        }
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
        } catch {
            return {};
        }
    }

    function setStudentProfile(name, roll) {
        if (currentStudent) {
            if (window.PrepMock) {
                window.PrepMock.syncProfileInputs(currentStudent.full_name, currentStudent.roll_number);
            }
            return;
        }
        const profile = {
            name: (name || "").trim(),
            roll: (roll || "").trim(),
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
        if (window.PrepMock) window.PrepMock.syncProfileInputs(profile.name, profile.roll);
    }

    function renderSessionHeader() {
        const pill = document.getElementById("sessionUserPill");
        const guestLabel = document.getElementById("guestSessionLabel");
        const openAuthBtn = document.getElementById("openAuthBtn");
        const logoutBtn = document.getElementById("logoutBtn");

        if (currentStudent) {
            const extraParts = [currentStudent.roll_number];
            if (currentStudent.branch) extraParts.push(currentStudent.branch);
            if (currentStudent.cgpa !== null && currentStudent.cgpa !== undefined) {
                extraParts.push(`CGPA ${currentStudent.cgpa}`);
            }
            pill.textContent = `${currentStudent.full_name} • ${extraParts.join(" • ")}`;
            pill.style.display = "inline-flex";
            logoutBtn.style.display = "inline-flex";
            guestLabel.style.display = "none";
            openAuthBtn.style.display = "none";
        } else {
            pill.style.display = "none";
            logoutBtn.style.display = "none";
            guestLabel.style.display = "inline-flex";
            openAuthBtn.style.display = "inline-flex";
        }
    }

    function setAuthTab(tabName) {
        const isLogin = tabName === "login";
        document.getElementById("tabLoginBtn").classList.toggle("active", isLogin);
        document.getElementById("tabSignupBtn").classList.toggle("active", !isLogin);
        document.getElementById("loginForm").style.display = isLogin ? "block" : "none";
        document.getElementById("signupForm").style.display = isLogin ? "none" : "block";
        document.getElementById("loginError").style.display = "none";
        document.getElementById("signupError").style.display = "none";
    }

    function showAuthScreen(tabName = "login") {
        setAuthTab(tabName);
        document.getElementById("authScreen").style.display = "flex";
        document.getElementById("appShell").style.display = "none";
    }

    async function loadInitialAppData() {
        loadSystemStatus();
        if (initialDataLoaded) return;
        initialDataLoaded = true;
        window.PrepQuestions.loadFilters();
        const companies = await window.PrepCompanies.loadCompanies();
        window.PrepMock.populateCompanyDropdown(companies);
        window.PrepAgent.populateCompanyHints(companies);
    }

    async function enterWorkspace({ isGuest = false } = {}) {
        document.getElementById("authScreen").style.display = "none";
        document.getElementById("appShell").style.display = "flex";

        if (isGuest) {
            localStorage.setItem(GUEST_MODE_KEY, "1");
        } else {
            localStorage.removeItem(GUEST_MODE_KEY);
        }

        renderSessionHeader();

        const profile = getStudentProfile();
        if (window.PrepMock) {
            window.PrepMock.syncProfileInputs(profile.name || "", profile.roll || "", Boolean(currentStudent));
        }
        const perfInput = document.getElementById("perfSearchInput");
        if (perfInput && currentStudent) {
            perfInput.value = currentStudent.roll_number;
        }

        await loadInitialAppData();
        switchView("companies", true);
    }

    async function handleLoginSubmit(e) {
        e.preventDefault();
        const errEl = document.getElementById("loginError");
        errEl.style.display = "none";

        const identifier = document.getElementById("loginIdentifier").value.trim();
        const password = document.getElementById("loginPassword").value;
        const btn = document.getElementById("loginSubmitBtn");
        btn.disabled = true;
        btn.textContent = "Signing in...";

        try {
            const res = await window.PrepAPI.login({ identifier, password });
            window.PrepAPI.setAuthToken(res.access_token);
            currentStudent = res.student;
            document.getElementById("loginPassword").value = "";
            await enterWorkspace({ isGuest: false });
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.textContent = "Sign In";
        }
    }

    async function handleSignupSubmit(e) {
        e.preventDefault();
        const errEl = document.getElementById("signupError");
        errEl.style.display = "none";

        const cgpaRaw = document.getElementById("signupCgpa").value.trim();
        const payload = {
            full_name: document.getElementById("signupName").value.trim(),
            roll_number: document.getElementById("signupRoll").value.trim(),
            email: document.getElementById("signupEmail").value.trim() || null,
            branch: document.getElementById("signupBranch").value || null,
            cgpa: cgpaRaw !== "" ? Number(cgpaRaw) : null,
            password: document.getElementById("signupPassword").value,
        };

        const btn = document.getElementById("signupSubmitBtn");
        btn.disabled = true;
        btn.textContent = "Creating account...";

        try {
            const res = await window.PrepAPI.signup(payload);
            window.PrepAPI.setAuthToken(res.access_token);
            currentStudent = res.student;
            document.getElementById("signupPassword").value = "";
            await enterWorkspace({ isGuest: false });
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = "block";
        } finally {
            btn.disabled = false;
            btn.textContent = "Create Student Account";
        }
    }

    function handleLogout() {
        window.PrepAPI.setAuthToken("");
        localStorage.removeItem(GUEST_MODE_KEY);
        currentStudent = null;
        document.getElementById("mockStudentName").value = "";
        document.getElementById("mockStudentRoll").value = "";
        document.getElementById("perfSearchInput").value = "";
        showAuthScreen("login");
    }

    function switchView(viewName, skipAutoLoad = false) {
        document.querySelectorAll(".nav-btn").forEach((btn) => {
            btn.classList.toggle("active", btn.getAttribute("data-view") === viewName);
        });
        document.querySelectorAll(".view-panel").forEach((panel) => {
            panel.classList.toggle("active", panel.id === `view-${viewName}`);
        });

        const meta = VIEW_META[viewName] || VIEW_META.companies;
        document.getElementById("viewTitle").textContent = meta.title;
        document.getElementById("viewSubtitle").textContent = meta.subtitle;

        if (skipAutoLoad) return;

        if (viewName === "questions") {
            window.PrepQuestions.loadQuestions();
        } else if (viewName === "performance") {
            const perfInput = document.getElementById("perfSearchInput");
            const profile = getStudentProfile();
            if (!perfInput.value.trim() && (profile.roll || profile.name)) {
                perfInput.value = profile.roll || profile.name;
            }
            window.PrepPerformance.loadStudentDashboard(perfInput.value);
        }
    }

    function openModal(title, bodyHtml) {
        document.getElementById("appModalTitle").textContent = title;
        document.getElementById("appModalBody").innerHTML = bodyHtml;
        document.getElementById("appModalBackdrop").classList.add("open");
    }

    function closeModal() {
        document.getElementById("appModalBackdrop").classList.remove("open");
    }

    function openQuestionsForCompany(companyName) {
        switchView("questions", true);
        window.PrepQuestions.loadFilters().then(() => {
            window.PrepQuestions.filterByCompany(companyName);
        });
    }

    function openAgentForCompany(companyName) {
        switchView("agent");
        const hintSelect = document.getElementById("agentCompanyHint");
        if (hintSelect) hintSelect.value = companyName;
        const input = document.getElementById("agentMessageInput");
        if (input) {
            input.value = `Give me placement details, eligibility, rounds, and tips for ${companyName}`;
            input.focus();
        }
    }

    function openPerformanceForStudent(identifier) {
        document.getElementById("perfSearchInput").value = identifier;
        switchView("performance");
    }

    async function loadSystemStatus() {
        const dot = document.getElementById("dbStatusDot");
        const text = document.getElementById("dbStatusText");
        try {
            const health = await window.PrepAPI.getHealth();
            const isHealthy = health && health.database === "connected";
            dot.className = `dot ${isHealthy ? "ok" : "err"}`;
            text.textContent = isHealthy ? "API & PostgreSQL Online" : "DB Disconnected";
        } catch {
            dot.className = "dot err";
            text.textContent = "Backend Unreachable";
        }

        try {
            const rag = await window.PrepAPI.getRagStatus();
            document.getElementById("ragStatusBadge").textContent =
                `RAG: ${rag.indexed_files_count} files / ${rag.total_chunks} chunks`;
            document.getElementById("kpiRagChunks").textContent = rag.total_chunks;
            document.getElementById("kpiRagFilesSub").textContent =
                `${rag.pdf_files_extracted} PDFs + notes indexed`;
            window.PrepAgent.populateRagCompanies(rag.indexed_companies);
        } catch {
            document.getElementById("ragStatusBadge").textContent = "RAG: unavailable";
        }
    }

    async function bootstrap() {
        // Initialize UI module listeners
        window.PrepCompanies.init();
        window.PrepQuestions.init();
        window.PrepMock.init();
        window.PrepPerformance.init();
        window.PrepAgent.init();

        // Sidebar tab switching
        document.querySelectorAll(".nav-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                switchView(btn.getAttribute("data-view"));
            });
        });

        // Modal bindings
        document.getElementById("appModalCloseBtn").addEventListener("click", closeModal);
        document.getElementById("appModalBackdrop").addEventListener("click", (e) => {
            if (e.target.id === "appModalBackdrop") closeModal();
        });

        // Auth UI bindings
        document.getElementById("tabLoginBtn").addEventListener("click", () => setAuthTab("login"));
        document.getElementById("tabSignupBtn").addEventListener("click", () => setAuthTab("signup"));
        document.getElementById("loginForm").addEventListener("submit", handleLoginSubmit);
        document.getElementById("signupForm").addEventListener("submit", handleSignupSubmit);
        document.getElementById("continueGuestBtn").addEventListener("click", () => {
            enterWorkspace({ isGuest: true });
        });
        document.getElementById("openAuthBtn").addEventListener("click", () => showAuthScreen("login"));
        document.getElementById("logoutBtn").addEventListener("click", handleLogout);

        // Restore authenticated session if valid bearer token exists
        const token = window.PrepAPI.getAuthToken();
        if (token) {
            try {
                currentStudent = await window.PrepAPI.getMe();
                await enterWorkspace({ isGuest: false });
                return;
            } catch {
                window.PrepAPI.setAuthToken("");
                currentStudent = null;
            }
        }

        // Restore guest mode if previously selected
        if (localStorage.getItem(GUEST_MODE_KEY) === "1") {
            await enterWorkspace({ isGuest: true });
            return;
        }

        showAuthScreen("login");
    }

    window.PrepApp = {
        getCurrentStudent,
        getStudentProfile,
        setStudentProfile,
        showAuthScreen,
        switchView,
        openModal,
        closeModal,
        openQuestionsForCompany,
        openAgentForCompany,
        openPerformanceForStudent,
    };

    document.addEventListener("DOMContentLoaded", bootstrap);
})();
