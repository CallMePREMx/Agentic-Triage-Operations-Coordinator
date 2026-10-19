/**
 * ATOC — Agentic Triage & Operations Coordinator
 * Frontend JavaScript — handles UI interactions, API calls, and result rendering.
 */

// ─── Quick Example Presets ──────────────────────────────────────────────────
const EXAMPLES = {
    emergency:
        "My name is Sarah Khan, I'm 55 years old female. I've been having severe chest pain and shortness of breath for about 30 minutes. I'm also feeling nauseous and sweating heavily.",
    urgent:
        "I'm Raj Patel, 67 years old male. I've had a severe headache for 6 hours with stiff neck and some confusion. My temperature is high.",
    routine:
        "Hi, my name is Emily Davis. I'm 28 years old. I've had a persistent cough and sore throat for 5 days now. Also some mild fatigue.",
    pediatric:
        "My son is 3 years old, his name is Noah Williams. He's had a high fever for 2 days and is crying inconsolably. He's also not feeding properly.",
};

// ─── DOM References ─────────────────────────────────────────────────────────
const DOM = {
    // Input
    chatInput: document.getElementById("chatInput"),
    btnSubmitChat: document.getElementById("btnSubmitChat"),
    btnChatMode: document.getElementById("btnChatMode"),
    btnFormMode: document.getElementById("btnFormMode"),
    chatMode: document.getElementById("chatMode"),
    formMode: document.getElementById("formMode"),
    intakeForm: document.getElementById("intakeForm"),

    // Results
    resultsEmpty: document.getElementById("resultsEmpty"),
    resultsLoading: document.getElementById("resultsLoading"),
    resultsContent: document.getElementById("resultsContent"),
    loadingSteps: document.getElementById("loadingSteps"),

    // Result Details
    triageBadge: document.getElementById("triageBadge"),
    badgeTier: document.getElementById("badgeTier"),
    badgeLabel: document.getElementById("badgeLabel"),
    badgeScore: document.getElementById("badgeScore"),
    badgeSpec: document.getElementById("badgeSpec"),
    patientSummary: document.getElementById("patientSummary"),
    appointmentDetails: document.getElementById("appointmentDetails"),
    appointmentCard: document.getElementById("appointmentCard"),
    pipelineLog: document.getElementById("pipelineLog"),
    warningsCard: document.getElementById("warningsCard"),
    warningsList: document.getElementById("warningsList"),

    // Pipeline steps
    pipelineStep1: document.getElementById("pipelineStep1"),
    pipelineStep2: document.getElementById("pipelineStep2"),
    pipelineStep3: document.getElementById("pipelineStep3"),
    pipelineStep4: document.getElementById("pipelineStep4"),

    // Voice Intake
    btnVoiceInput: document.getElementById("btnVoiceInput"),
    btnStopVoice: document.getElementById("btnStopVoice"),
    voiceStatusBar: document.getElementById("voiceStatusBar"),
    voiceStatusText: document.getElementById("voiceStatusText"),

    // Clarification Interview
    clarificationPanel: document.getElementById("clarificationPanel"),
    clarificationPrompt: document.getElementById("clarificationPrompt"),
    clarificationOptions: document.getElementById("clarificationOptions"),
    clarificationCustomInput: document.getElementById("clarificationCustomInput"),
    btnSubmitClarification: document.getElementById("btnSubmitClarification"),
    btnSkipClarification: document.getElementById("btnSkipClarification"),

    // Stats
    btnViewStats: document.getElementById("btnViewStats"),
    btnResetDB: document.getElementById("btnResetDB"),
    statsModal: document.getElementById("statsModal"),
    btnCloseStats: document.getElementById("btnCloseStats"),
    statsBody: document.getElementById("statsBody"),
};

const PIPELINE_STEPS = [DOM.pipelineStep1, DOM.pipelineStep2, DOM.pipelineStep3, DOM.pipelineStep4];
const CONNECTORS = document.querySelectorAll(".pipeline-connector");

// Active conversational session ID
let currentSessionId = null;

// ─── Mode Toggle ────────────────────────────────────────────────────────────
DOM.btnChatMode.addEventListener("click", () => {
    DOM.btnChatMode.classList.add("active");
    DOM.btnFormMode.classList.remove("active");
    DOM.chatMode.classList.remove("hidden");
    DOM.formMode.classList.add("hidden");
});

DOM.btnFormMode.addEventListener("click", () => {
    DOM.btnFormMode.classList.add("active");
    DOM.btnChatMode.classList.remove("active");
    DOM.formMode.classList.remove("hidden");
    DOM.chatMode.classList.add("hidden");
});

// ─── Quick Examples ─────────────────────────────────────────────────────────
document.querySelectorAll(".chip[data-example]").forEach((chip) => {
    chip.addEventListener("click", () => {
        const key = chip.dataset.example;
        if (EXAMPLES[key]) {
            currentSessionId = null;
            hideClarificationPanel();
            DOM.chatInput.value = EXAMPLES[key];
            DOM.chatInput.focus();
        }
    });
});

// ─── Voice Preset Samples ───────────────────────────────────────────────────
document.querySelectorAll(".chip-voice").forEach((chip) => {
    chip.addEventListener("click", async () => {
        const voiceKey = chip.dataset.voice;
        showSimulatedVoiceEffect("Transcribing clinical audio...");
        try {
            const res = await fetch("/api/voice-transcribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sample_id: voiceKey }),
            });
            const data = await res.json();
            if (data.transcript) {
                currentSessionId = null;
                hideClarificationPanel();
                DOM.chatInput.value = data.transcript;
                DOM.chatInput.focus();
            }
        } catch (e) {
            console.error("Voice preset error:", e);
        } finally {
            setTimeout(hideVoiceStatus, 1200);
        }
    });
});

// ─── Submit: Chat Mode ──────────────────────────────────────────────────────
DOM.btnSubmitChat.addEventListener("click", () => {
    const message = DOM.chatInput.value.trim();
    if (!message) return;
    hideClarificationPanel();
    currentSessionId = null; // New intake starts fresh session
    runTriagePipeline({ message, allow_clarification: true });
});

// Submit on Ctrl+Enter
DOM.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        DOM.btnSubmitChat.click();
    }
});

// ─── Submit: Form Mode ─────────────────────────────────────────────────────
DOM.intakeForm.addEventListener("submit", (e) => {
    e.preventDefault();
    hideClarificationPanel();
    currentSessionId = null;
    const formData = {
        name: document.getElementById("formName").value.trim(),
        age: parseInt(document.getElementById("formAge").value),
        gender: document.getElementById("formGender").value,
        symptoms: document.getElementById("formSymptoms").value.trim(),
        symptom_duration: document.getElementById("formDuration").value.trim(),
        contact: document.getElementById("formContact").value.trim(),
        allow_clarification: false, // Forms are explicitly pre-filled
    };
    runTriagePipeline(formData);
});

// ─── Clarification Action Listeners ─────────────────────────────────────────
DOM.btnSubmitClarification.addEventListener("click", () => {
    const customText = DOM.clarificationCustomInput.value.trim();
    if (!customText) return;
    DOM.clarificationCustomInput.value = "";
    hideClarificationPanel();
    runTriagePipeline({
        session_id: currentSessionId,
        response: customText,
        allow_clarification: true,
    });
});

DOM.clarificationCustomInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        DOM.btnSubmitClarification.click();
    }
});

DOM.btnSkipClarification.addEventListener("click", () => {
    hideClarificationPanel();
    runTriagePipeline({
        session_id: currentSessionId,
        force_triage: true,
    });
});

function hideClarificationPanel() {
    if (DOM.clarificationPanel) {
        DOM.clarificationPanel.style.display = "none";
    }
}

// ─── Core Pipeline Execution ────────────────────────────────────────────────
async function runTriagePipeline(payload) {
    showLoading();
    resetPipeline();

    const agentNames = ["Intake Agent", "Triage Agent", "Operations Agent", "Critic Agent"];
    let stepIndex = 0;

    // Animate pipeline steps sequentially
    const animationInterval = setInterval(() => {
        if (stepIndex < 4) {
            activatePipelineStep(stepIndex);
            addLoadingStep(`Processing: ${agentNames[stepIndex]}...`);
            stepIndex++;
        }
    }, 350);

    try {
        const response = await fetch("/api/triage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        clearInterval(animationInterval);
        const data = await response.json();

        if (data.session_id) {
            currentSessionId = data.session_id;
        }

        // Check if Intake Agent requests conversational clarification
        if (data.needs_clarification) {
            DOM.resultsLoading.classList.add("hidden");
            DOM.resultsEmpty.classList.remove("hidden");
            DOM.resultsEmpty.innerHTML = `
                <div class="empty-icon" style="color: var(--priority-yellow);">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                </div>
                <h3 style="color:#FCD34D;margin-bottom:6px;">Clarification Requested</h3>
                <p style="font-size:0.85rem;color:var(--text-muted);max-width:320px;">
                    The Intake Agent is requesting details to ensure clinical precision. Please select or type your response on the left.
                </p>
            `;
            DOM.btnSubmitChat.disabled = false;

            // Highlight Step 1 as paused awaiting answer
            activatePipelineStep(0);
            renderClarificationPanel(data);
            return;
        }

        // Complete remaining pipeline animations
        for (let i = stepIndex; i < 4; i++) {
            activatePipelineStep(i);
        }

        // Mark pipeline steps based on results
        if (data.steps) {
            data.steps.forEach((step, idx) => {
                if (idx < 4) {
                    PIPELINE_STEPS[idx].classList.remove("active");
                    PIPELINE_STEPS[idx].classList.add(step.success ? "completed" : "failed");
                }
            });
        }

        // Show results
        setTimeout(() => {
            showResults(data);
        }, 300);

    } catch (error) {
        clearInterval(animationInterval);
        showError("Failed to connect to the server. Is the backend running?");
    }
}

// ─── Render Clarification Panel ─────────────────────────────────────────────
function renderClarificationPanel(data) {
    if (!DOM.clarificationPanel) return;

    DOM.clarificationPrompt.textContent = data.clarification_prompt || "Please clarify your symptoms:";
    DOM.clarificationOptions.innerHTML = "";

    const options = data.quick_replies || [];
    options.forEach((opt) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-clarification-chip";
        btn.textContent = opt;
        btn.addEventListener("click", () => {
            hideClarificationPanel();
            runTriagePipeline({
                session_id: currentSessionId,
                response: opt,
                allow_clarification: true,
            });
        });
        DOM.clarificationOptions.appendChild(btn);
    });

    DOM.clarificationPanel.style.display = "block";
    DOM.clarificationPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ─── Voice Intake / Speech-to-Text ──────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognitionInstance = null;
let isVoiceRecording = false;

function initVoiceRecognition() {
    if (!SpeechRecognition) {
        console.warn("Web Speech API not supported natively in this browser.");
        return;
    }

    try {
        recognitionInstance = new SpeechRecognition();
        recognitionInstance.continuous = true;
        recognitionInstance.interimResults = true;
        recognitionInstance.lang = "en-US";

        recognitionInstance.onstart = () => {
            isVoiceRecording = true;
            DOM.btnVoiceInput.classList.add("recording");
            DOM.voiceStatusBar.style.display = "flex";
            DOM.voiceStatusText.textContent = "Listening... Speak your symptoms clearly";
        };

        recognitionInstance.onresult = (event) => {
            let finalTranscript = "";
            let interimTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            const current = DOM.chatInput.value.trim();
            const textToAdd = (finalTranscript || interimTranscript).trim();
            if (textToAdd) {
                DOM.chatInput.value = current ? `${current} ${textToAdd}` : textToAdd;
            }
        };

        recognitionInstance.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            stopVoiceRecognition();
            if (event.error === "not-allowed") {
                showSimulatedVoiceEffect("Microphone permission denied. Using clinical voice simulation...");
                fallbackToSimulatedVoice();
            }
        };

        recognitionInstance.onend = () => {
            stopVoiceRecognition();
        };
    } catch (e) {
        console.error("Could not initialize SpeechRecognition:", e);
    }
}

function startVoiceRecognition() {
    if (recognitionInstance) {
        try {
            recognitionInstance.start();
        } catch (e) {
            console.warn("Recognition already active or restart error:", e);
        }
    } else {
        fallbackToSimulatedVoice();
    }
}

function stopVoiceRecognition() {
    isVoiceRecording = false;
    if (DOM.btnVoiceInput) DOM.btnVoiceInput.classList.remove("recording");
    if (DOM.voiceStatusBar) DOM.voiceStatusBar.style.display = "none";
    if (recognitionInstance) {
        try { recognitionInstance.stop(); } catch (e) {}
    }
}

function showSimulatedVoiceEffect(msg) {
    if (DOM.voiceStatusBar) {
        DOM.voiceStatusBar.style.display = "flex";
        DOM.voiceStatusText.textContent = msg;
    }
}

function hideVoiceStatus() {
    if (DOM.voiceStatusBar && !isVoiceRecording) {
        DOM.voiceStatusBar.style.display = "none";
    }
}

async function fallbackToSimulatedVoice() {
    showSimulatedVoiceEffect("Voice recognition active (Simulated Intake)...");
    try {
        const res = await fetch("/api/voice-transcribe", { method: "POST" });
        const data = await res.json();
        if (data.transcript) {
            DOM.chatInput.value = data.transcript;
            DOM.chatInput.focus();
        }
    } catch (e) {
        console.error(e);
    } finally {
        setTimeout(hideVoiceStatus, 1500);
    }
}

DOM.btnVoiceInput.addEventListener("click", () => {
    if (isVoiceRecording) {
        stopVoiceRecognition();
    } else {
        startVoiceRecognition();
    }
});

DOM.btnStopVoice.addEventListener("click", () => {
    stopVoiceRecognition();
});

// Initialize SpeechRecognition on page load
initVoiceRecognition();

// ─── Pipeline Animation ────────────────────────────────────────────────────
function resetPipeline() {
    PIPELINE_STEPS.forEach((step) => {
        step.classList.remove("active", "completed", "failed");
    });
    CONNECTORS.forEach((c) => c.classList.remove("active"));
}

function activatePipelineStep(index) {
    if (index < PIPELINE_STEPS.length) {
        // Complete previous steps
        for (let i = 0; i < index; i++) {
            PIPELINE_STEPS[i].classList.remove("active");
            PIPELINE_STEPS[i].classList.add("completed");
        }
        // Activate current step
        PIPELINE_STEPS[index].classList.add("active");

        // Activate connectors up to current step
        CONNECTORS.forEach((c, i) => {
            if (i < index) c.classList.add("active");
        });
    }
}

function addLoadingStep(text) {
    const step = document.createElement("div");
    step.className = "loading-step";
    step.innerHTML = `<span class="step-check">✓</span> ${text}`;
    DOM.loadingSteps.appendChild(step);
}

// ─── UI State Management ───────────────────────────────────────────────────
function showLoading() {
    DOM.resultsEmpty.classList.add("hidden");
    DOM.resultsContent.classList.add("hidden");
    DOM.resultsLoading.classList.remove("hidden");
    DOM.loadingSteps.innerHTML = "";
    DOM.btnSubmitChat.disabled = true;
}

function showResults(data) {
    DOM.resultsLoading.classList.add("hidden");
    DOM.resultsContent.classList.remove("hidden");
    DOM.btnSubmitChat.disabled = false;
    renderResults(data);
}

function showError(message, errors = []) {
    DOM.resultsLoading.classList.add("hidden");
    DOM.resultsEmpty.classList.remove("hidden");
    DOM.resultsEmpty.innerHTML = `
        <div class="empty-icon" style="color: var(--priority-red);">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
        </div>
        <p style="color: var(--priority-red);font-weight:700;">${message}</p>
        ${errors && errors.length ? errors.map(e => `<p style="font-size:0.78rem;margin-top:6px;color:var(--text-muted);">${e}</p>`).join("") : ""}
    `;
    DOM.btnSubmitChat.disabled = false;
}

// ─── Render Results ────────────────────────────────────────────────────────
function renderResults(data) {
    const patient = data.patient;
    const appointment = data.appointment;

    // ── Triage Badge ────────────────────────────────────────────
    if (patient) {
        const tier = patient.priority_tier || "GREEN";
        const tierLabels = {
            RED: "Emergency", ORANGE: "Urgent", YELLOW: "Semi-Urgent",
            GREEN: "Routine", BLUE: "Follow-Up"
        };

        DOM.triageBadge.setAttribute("data-tier", tier);
        DOM.badgeTier.textContent = tier;
        DOM.badgeLabel.textContent = tierLabels[tier] || tier;
        DOM.badgeScore.textContent = `Severity Score: ${(patient.severity_score || 0).toFixed(3)}`;
        DOM.badgeSpec.textContent = patient.recommended_specialization || "General";

        // ── Patient Summary ─────────────────────────────────────
        DOM.patientSummary.innerHTML = `
            <div class="detail-row"><span class="label">Patient ID</span><span class="value">${patient.patient_id}</span></div>
            <div class="detail-row"><span class="label">Name</span><span class="value">${patient.name}</span></div>
            <div class="detail-row"><span class="label">Age</span><span class="value">${patient.age}</span></div>
            <div class="detail-row"><span class="label">Gender</span><span class="value">${patient.gender}</span></div>
            <div class="detail-row"><span class="label">Symptoms</span><span class="value">${(patient.symptoms || []).join(", ")}</span></div>
            <div class="detail-row"><span class="label">Duration</span><span class="value">${patient.symptom_duration}</span></div>
            <div class="detail-row"><span class="label">Triage Notes</span><span class="value" style="max-width:60%;text-align:right;">${(patient.triage_notes || []).slice(0, 3).join("; ")}</span></div>
        `;
    }

    // ── Appointment Details ──────────────────────────────────────
    if (appointment) {
        DOM.appointmentCard.style.display = "block";
        const statusColor = appointment.status === "CONFIRMED" ? "var(--priority-green)" :
            appointment.status === "FAILED" ? "var(--priority-red)" : "var(--priority-yellow)";

        DOM.appointmentDetails.innerHTML = `
            <div class="detail-row"><span class="label">Appointment ID</span><span class="value">${appointment.appointment_id}</span></div>
            <div class="detail-row"><span class="label">Doctor</span><span class="value">Dr. ${appointment.doctor_name}</span></div>
            <div class="detail-row"><span class="label">Specialization</span><span class="value">${appointment.specialization}</span></div>
            <div class="detail-row"><span class="label">Date</span><span class="value">${appointment.date}</span></div>
            <div class="detail-row"><span class="label">Time Slot</span><span class="value">${appointment.time_slot}</span></div>
            <div class="detail-row"><span class="label">Status</span><span class="value" style="color:${statusColor};font-weight:700;">${appointment.status}</span></div>
            <div class="detail-row"><span class="label">Validated</span><span class="value">${appointment.validated_by_critic ? "✓ Yes" : "✗ No"}</span></div>
        `;
    } else {
        DOM.appointmentCard.style.display = "none";
    }

    // ── Pipeline Log ────────────────────────────────────────────
    DOM.pipelineLog.innerHTML = "";
    if (data.steps) {
        data.steps.forEach((step) => {
            const entry = document.createElement("div");
            entry.className = "log-entry";
            entry.innerHTML = `
                <div class="log-icon ${step.success ? "success" : "error"}">${step.success ? "✓" : "✗"}</div>
                <div class="log-content">
                    <div class="log-agent">Step ${step.step}: ${step.agent}</div>
                    <div class="log-detail">${step.details || step.action}</div>
                </div>
            `;
            DOM.pipelineLog.appendChild(entry);
        });
    }

    // ── Warnings ────────────────────────────────────────────────
    if (data.warnings && data.warnings.length > 0) {
        DOM.warningsCard.style.display = "block";
        DOM.warningsList.innerHTML = data.warnings
            .map((w) => `<div class="warning-item">${w}</div>`)
            .join("");
    } else {
        DOM.warningsCard.style.display = "none";
    }

    // ── Errors (for failed pipelines) ───────────────────────────
    if (data.errors && data.errors.length > 0 && !data.success) {
        const errorCard = document.createElement("div");
        errorCard.className = "result-card";
        errorCard.innerHTML = `
            <h3 class="card-title" style="color: var(--priority-red);">✗ Pipeline Errors</h3>
            <div class="card-body">
                ${data.errors.map((e) => `<div class="warning-item" style="border-left-color:var(--priority-red);background:rgba(239,68,68,0.06);">${e}</div>`).join("")}
            </div>
        `;
        DOM.pipelineLog.parentElement.after(errorCard);
    }
}

// ─── Stats Modal ────────────────────────────────────────────────────────────
DOM.btnViewStats.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/stats");
        const stats = await res.json();

        const priorityDist = stats.priority_distribution || {};
        const priorityHTML = Object.entries(priorityDist)
            .map(([tier, count]) => `<div class="detail-row"><span class="label">${tier}</span><span class="value">${count}</span></div>`)
            .join("") || '<p style="color:var(--text-muted);font-size:0.8rem;">No appointments yet</p>';

        DOM.statsBody.innerHTML = `
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">${stats.total_doctors}</div>
                    <div class="stat-label">Doctors</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.total_patients}</div>
                    <div class="stat-label">Patients</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.active_appointments}</div>
                    <div class="stat-label">Active Appointments</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.available_slots}</div>
                    <div class="stat-label">Available Slots</div>
                </div>
            </div>
            <div style="margin-top:var(--space-lg);">
                <h3 style="font-size:0.88rem;font-weight:800;color:var(--text-heading);margin-bottom:var(--space-sm);">Priority Distribution</h3>
                ${priorityHTML}
            </div>
        `;

        DOM.statsModal.classList.remove("hidden");
    } catch (e) {
        alert("Failed to fetch stats. Is the server running?");
    }
});

DOM.btnCloseStats.addEventListener("click", () => {
    DOM.statsModal.classList.add("hidden");
});

DOM.statsModal.addEventListener("click", (e) => {
    if (e.target === DOM.statsModal) DOM.statsModal.classList.add("hidden");
});

// ─── Reset Database ─────────────────────────────────────────────────────────
DOM.btnResetDB.addEventListener("click", async () => {
    if (!confirm("Reset the database? All appointments and patient data will be cleared.")) return;
    try {
        await fetch("/api/reset", { method: "POST" });
        // Reset UI
        DOM.resultsContent.classList.add("hidden");
        DOM.resultsLoading.classList.add("hidden");
        DOM.resultsEmpty.classList.remove("hidden");
        DOM.resultsEmpty.innerHTML = `
            <div class="empty-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <p>Database reset. Submit a new patient case.</p>
        `;
        resetPipeline();
    } catch (e) {
        alert("Failed to reset. Is the server running?");
    }
});
