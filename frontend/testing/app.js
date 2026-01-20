/**
 * Cosmos HR - CV Processing Frontend
 * Modern UI with right sidebar, processing time tracking
 */

// Configuration
const API_BASE = 'https://iw9oxe3w4b.execute-api.eu-north-1.amazonaws.com/v1';
const MAX_FILES = 10;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const POLL_INTERVAL = 2000;

// State
let fileQueue = [];
let processingJobs = new Map(); // correlationId -> { file, status, startTime, endTime, ... }
let completedResults = []; // Array of completed candidate data
let pollIntervals = new Map();
let timerIntervals = new Map(); // For live time updates
let allCandidates = []; // Array of all candidates from database
let deleteCandidate = null; // Candidate to delete (set when modal opens)

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileQueueEl = document.getElementById('fileQueue');
const queueList = document.getElementById('queueList');
const queueCount = document.getElementById('queueCount');
const clearQueueBtn = document.getElementById('clearQueue');
const startUploadBtn = document.getElementById('startUpload');
const processingStatus = document.getElementById('processingStatus');
const statusList = document.getElementById('statusList');
const completedCountEl = document.getElementById('completedCount');
const processingCountEl = document.getElementById('processingCount');
const resultsBadge = document.getElementById('resultsBadge');
const noResults = document.getElementById('noResults');
const candidateTabs = document.getElementById('candidateTabs');
const tabsHeader = document.getElementById('tabsHeader');
const tabsContent = document.getElementById('tabsContent');
const themeToggle = document.getElementById('themeToggle');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendMessageBtn = document.getElementById('sendMessage');

// Candidates Page Elements
const candidatesBadge = document.getElementById('candidatesBadge');
const candidateSearch = document.getElementById('candidateSearch');
const roleFilter = document.getElementById('roleFilter');
const sortOrder = document.getElementById('sortOrder');
const refreshCandidatesBtn = document.getElementById('refreshCandidates');
const candidatesLoading = document.getElementById('candidatesLoading');
const candidatesEmpty = document.getElementById('candidatesEmpty');
const candidatesByRole = document.getElementById('candidatesByRole');
const deleteModal = document.getElementById('deleteModal');
const closeDeleteModalBtn = document.getElementById('closeDeleteModal');
const deleteCandidateName = document.getElementById('deleteCandidateName');
const cancelDeleteBtn = document.getElementById('cancelDelete');
const confirmDeleteBtn = document.getElementById('confirmDelete');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNavigation();
    initDropzone();
    initChat();
    initCandidates();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    themeToggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    });
}

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const pages = document.querySelectorAll('.page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageId = item.dataset.page + 'Page';
            const pageName = item.dataset.page;

            navItems.forEach(i => i.classList.remove('active'));
            pages.forEach(p => p.classList.remove('active'));

            item.classList.add('active');
            document.getElementById(pageId).classList.add('active');

            // Refresh candidates when navigating to that page
            if (pageName === 'candidates') {
                loadCandidates();
            }
        });
    });
}

// Dropzone
function initDropzone() {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
        fileInput.value = '';
    });

    clearQueueBtn.addEventListener('click', clearQueue);
    startUploadBtn.addEventListener('click', startProcessing);
}

function handleFiles(files) {
    const validFiles = Array.from(files).filter(file => {
        if (file.size > MAX_FILE_SIZE) {
            alert(`File ${file.name} is too large (max 10MB)`);
            return false;
        }
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'].includes(ext)) {
            alert(`File ${file.name} has unsupported format`);
            return false;
        }
        return true;
    });

    const remaining = MAX_FILES - fileQueue.length;
    if (validFiles.length > remaining) {
        alert(`Can only add ${remaining} more files (max ${MAX_FILES})`);
    }

    validFiles.slice(0, remaining).forEach(file => {
        if (!fileQueue.find(f => f.name === file.name)) {
            fileQueue.push(file);
        }
    });

    renderQueue();
}

function renderQueue() {
    if (fileQueue.length === 0) {
        fileQueueEl.style.display = 'none';
        return;
    }

    fileQueueEl.style.display = 'block';
    queueCount.textContent = `${fileQueue.length} file${fileQueue.length > 1 ? 's' : ''}`;

    queueList.innerHTML = fileQueue.map((file, index) => `
        <div class="queue-item" data-index="${index}">
            <div class="queue-item-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <div class="queue-item-info">
                <div class="queue-item-name">${escapeHtml(file.name)}</div>
                <div class="queue-item-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="queue-item-remove" onclick="removeFromQueue(${index})">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

function removeFromQueue(index) {
    fileQueue.splice(index, 1);
    renderQueue();
}

function clearQueue() {
    fileQueue = [];
    renderQueue();
}

// Processing
async function startProcessing() {
    if (fileQueue.length === 0) return;

    startUploadBtn.disabled = true;
    processingStatus.style.display = 'block';
    processingJobs.clear();

    const filesToProcess = [...fileQueue];

    // Initialize jobs with start time
    for (const file of filesToProcess) {
        const tempId = 'pending-' + file.name;
        processingJobs.set(tempId, {
            file,
            status: 'uploading',
            progress: 0,
            step: 'Uploading...',
            startTime: Date.now(),
            endTime: null,
            data: null,
            tempId: true
        });
    }
    renderStatusList();
    startTimerUpdates();

    // Upload all files
    for (const file of filesToProcess) {
        const tempId = 'pending-' + file.name;
        const tempJob = processingJobs.get(tempId);

        try {
            const correlationId = await uploadFile(file);

            // Transfer to real ID
            processingJobs.delete(tempId);
            processingJobs.set(correlationId, {
                file,
                status: 'processing',
                progress: 10,
                step: 'Queued',
                startTime: tempJob.startTime,
                endTime: null,
                data: null
            });
            renderStatusList();

            startPolling(correlationId);
        } catch (error) {
            console.error('Upload failed:', error);
            tempJob.status = 'failed';
            tempJob.step = 'Upload failed';
            tempJob.progress = 0;
            tempJob.endTime = Date.now();
            renderStatusList();
        }
    }

    fileQueue = [];
    renderQueue();
}

async function uploadFile(file) {
    const response = await fetch(`${API_BASE}/test/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filename: file.name,
            content_type: file.type || 'application/octet-stream'
        })
    });

    if (!response.ok) {
        throw new Error('Failed to get upload URL');
    }

    const { upload_url, fields, correlation_id } = await response.json();

    const formData = new FormData();
    Object.entries(fields).forEach(([key, value]) => {
        formData.append(key, value);
    });
    formData.append('file', file);

    const uploadResponse = await fetch(upload_url, {
        method: 'POST',
        body: formData
    });

    if (!uploadResponse.ok) {
        throw new Error('Failed to upload file');
    }

    return correlation_id;
}

function startPolling(correlationId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/test/status/${correlationId}`);
            if (!response.ok) return;

            const data = await response.json();
            const job = processingJobs.get(correlationId);
            if (!job) return;

            const currentStepInfo = data.steps?.find(s => s.state === 'current');
            job.step = currentStepInfo?.label || getStepLabel(data.status) || data.status;
            job.progress = data.progress_percent || 0;

            if (data.status === 'completed' || data.is_completed) {
                job.status = 'completed';
                job.progress = 100;
                job.step = 'Completed';
                job.endTime = Date.now();
                job.data = data;
                clearInterval(interval);
                pollIntervals.delete(correlationId);
                onJobCompleted(correlationId, data);
            } else if (data.status === 'failed' || data.is_failed) {
                job.status = 'failed';
                job.step = data.error || 'Failed';
                job.progress = 0;
                job.endTime = Date.now();
                clearInterval(interval);
                pollIntervals.delete(correlationId);
            }

            renderStatusList();
            updateStats();
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, POLL_INTERVAL);

    pollIntervals.set(correlationId, interval);
}

function startTimerUpdates() {
    // Clear any existing timer
    if (window.globalTimerInterval) {
        clearInterval(window.globalTimerInterval);
    }

    // Update timers every second
    window.globalTimerInterval = setInterval(() => {
        const hasActiveJobs = Array.from(processingJobs.values()).some(
            job => job.status !== 'completed' && job.status !== 'failed'
        );

        if (!hasActiveJobs) {
            clearInterval(window.globalTimerInterval);
            return;
        }

        // Update time displays
        processingJobs.forEach((job, id) => {
            const timeEl = document.querySelector(`[data-job-id="${id}"] .status-time`);
            if (timeEl && job.status !== 'completed' && job.status !== 'failed') {
                timeEl.textContent = formatTime(Date.now() - job.startTime);
            }
        });
    }, 1000);
}

function onJobCompleted(correlationId, data) {
    const job = processingJobs.get(correlationId);
    if (!job) return;

    const processingTime = job.endTime - job.startTime;

    const candidateName = data.parsed_cv?.personal
        ? `${data.parsed_cv.personal.first_name || ''} ${data.parsed_cv.personal.last_name || ''}`.trim()
        : job.file.name;

    completedResults.push({
        correlationId,
        filename: job.file.name,
        candidateName: candidateName || 'Unknown',
        processingTime,
        data: data
    });

    updateResultsBadge();
    renderResultsTabs();

    // Update candidates data (for badge and when user navigates to page)
    allCandidates = getSessionCandidates();
    updateCandidatesBadge();
}

function renderStatusList() {
    // Update existing cards or create new ones (avoids animation restart)
    const existingCards = new Map();
    statusList.querySelectorAll('.status-card').forEach(card => {
        existingCards.set(card.dataset.jobId, card);
    });

    const currentIds = new Set();

    processingJobs.forEach((job, id) => {
        currentIds.add(id);
        const elapsed = job.endTime
            ? job.endTime - job.startTime
            : Date.now() - job.startTime;

        let card = existingCards.get(id);

        if (card) {
            // Update existing card without replacing HTML (keeps spinner animation)
            card.className = `status-card ${job.status}`;
            card.querySelector('.status-step').textContent = job.step;
            card.querySelector('.status-time').textContent = formatTime(elapsed);
            card.querySelector('.status-progress-fill').style.width = `${job.progress}%`;

            // Only update icon if status changed to completed/failed
            const iconContainer = card.querySelector('.status-icon');
            const hasSpinner = iconContainer.querySelector('.spinner');

            if (job.status === 'completed' && hasSpinner) {
                iconContainer.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>`;
            } else if (job.status === 'failed' && hasSpinner) {
                iconContainer.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>`;
            }
        } else {
            // Create new card
            card = document.createElement('div');
            card.className = `status-card ${job.status}`;
            card.dataset.jobId = id;
            card.innerHTML = `
                <div class="status-icon">
                    ${job.status === 'completed' ? `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                    ` : job.status === 'failed' ? `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    ` : `
                        <div class="spinner"></div>
                    `}
                </div>
                <div class="status-info">
                    <div class="status-filename">${escapeHtml(job.file.name)}</div>
                    <div class="status-step">${escapeHtml(job.step)}</div>
                </div>
                <div class="status-meta">
                    <div class="status-time">${formatTime(elapsed)}</div>
                    <div class="status-progress">
                        <div class="status-progress-fill" style="width: ${job.progress}%"></div>
                    </div>
                </div>
            `;
            statusList.appendChild(card);
        }
    });

    // Remove cards for jobs that no longer exist
    existingCards.forEach((card, id) => {
        if (!currentIds.has(id)) {
            card.remove();
        }
    });
}

function updateStats() {
    const jobs = Array.from(processingJobs.values());
    const completed = jobs.filter(j => j.status === 'completed').length;
    const processing = jobs.filter(j => j.status !== 'completed' && j.status !== 'failed').length;

    completedCountEl.textContent = `${completed} completed`;
    processingCountEl.textContent = `${processing} processing`;
}

function updateResultsBadge() {
    if (completedResults.length > 0) {
        resultsBadge.style.display = 'flex';
        resultsBadge.textContent = completedResults.length;
    } else {
        resultsBadge.style.display = 'none';
    }
}

// Format time as MM:SS or HH:MM:SS
function formatTime(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Results Tabs
function renderResultsTabs() {
    if (completedResults.length === 0) {
        noResults.style.display = 'flex';
        candidateTabs.style.display = 'none';
        return;
    }

    noResults.style.display = 'none';
    candidateTabs.style.display = 'flex';

    tabsHeader.innerHTML = completedResults.map((result, index) => `
        <button class="tab-button ${index === 0 ? 'active' : ''}" data-index="${index}">
            ${escapeHtml(result.candidateName)}
            <span class="time-badge">${formatTime(result.processingTime)}</span>
        </button>
    `).join('');

    tabsContent.innerHTML = completedResults.map((result, index) => `
        <div class="tab-panel ${index === 0 ? 'active' : ''}" data-index="${index}">
            ${renderCandidateCard(result.data, result.processingTime)}
        </div>
    `).join('');

    tabsHeader.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = btn.dataset.index;
            tabsHeader.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            tabsContent.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            tabsContent.querySelector(`.tab-panel[data-index="${index}"]`).classList.add('active');
        });
    });
}

function renderCandidateCard(data, processingTime) {
    const cv = data.parsed_cv || {};
    const personal = cv.personal || {};

    return `
        <div class="extraction-result">
            <div class="candidate-header">
                <div class="candidate-info">
                    <h2>${escapeHtml(personal.first_name || '')} ${escapeHtml(personal.last_name || '')}</h2>
                    <div class="candidate-meta">
                        ${personal.email ? `<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>${escapeHtml(personal.email)}</span>` : ''}
                        ${personal.phone ? `<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>${escapeHtml(personal.phone)}</span>` : ''}
                        ${personal.address_city ? `<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>${escapeHtml(personal.address_city)}</span>` : ''}
                    </div>
                </div>
                <div class="candidate-scores">
                    <div class="score-card">
                        <div class="score-value">${formatTime(processingTime)}</div>
                        <div class="score-label">Processing Time</div>
                    </div>
                    ${data.confidence ? `<div class="score-card"><div class="score-value">${Math.round(data.confidence * 100)}%</div><div class="score-label">Confidence</div></div>` : ''}
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card"><div class="stat-value">${cv.skills?.length || 0}</div><div class="stat-label">Skills</div></div>
                <div class="stat-card"><div class="stat-value">${cv.experience?.length || 0}</div><div class="stat-label">Experience</div></div>
                <div class="stat-card"><div class="stat-value">${cv.education?.length || 0}</div><div class="stat-label">Education</div></div>
                <div class="stat-card"><div class="stat-value">${cv.certifications?.length || 0}</div><div class="stat-label">Certs</div></div>
                <div class="stat-card"><div class="stat-value">${cv.training?.length || 0}</div><div class="stat-label">Training</div></div>
                <div class="stat-card"><div class="stat-value">${cv.languages?.length || 0}</div><div class="stat-label">Languages</div></div>
                <div class="stat-card"><div class="stat-value">${cv.software?.length || 0}</div><div class="stat-label">Software</div></div>
                <div class="stat-card"><div class="stat-value">${cv.driving_licenses?.length || 0}</div><div class="stat-label">Licenses</div></div>
            </div>

            ${renderPersonalInfo(personal)}
            ${cv.experience?.length ? renderExperienceSection(cv.experience) : ''}
            ${cv.education?.length ? renderEducationSection(cv.education) : ''}
            ${cv.skills?.length ? renderSkillsSection(cv.skills) : ''}
            ${cv.certifications?.length ? renderCertificationsSection(cv.certifications) : ''}
            ${cv.training?.length ? renderTrainingSection(cv.training) : ''}
            ${cv.languages?.length ? renderLanguagesSection(cv.languages) : ''}
            ${cv.software?.length ? renderSoftwareSection(cv.software) : ''}
            ${cv.driving_licenses?.length ? renderLicensesSection(cv.driving_licenses) : ''}
        </div>
    `;
}

function renderPersonalInfo(personal) {
    if (!personal) return '';

    const fields = [
        { label: 'Full Name', value: `${personal.first_name || ''} ${personal.last_name || ''}`.trim() },
        { label: 'Email', value: personal.email },
        { label: 'Phone', value: personal.phone },
        { label: 'Date of Birth', value: personal.date_of_birth },
        { label: 'Nationality', value: personal.nationality },
        { label: 'City', value: personal.address_city },
        { label: 'Postal Code', value: personal.address_postal_code },
        { label: 'Military Status', value: personal.military_status }
    ].filter(f => f.value);

    return `
        <div class="data-section">
            <h3>Personal Information</h3>
            <div class="personal-grid">
                ${fields.map(f => `
                    <div class="personal-item">
                        <div class="personal-label">${f.label}</div>
                        <div class="personal-value">${escapeHtml(f.value)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function renderExperienceSection(experience) {
    return `
        <div class="data-section">
            <h3>Experience <span class="count">(${experience.length})</span></h3>
            ${experience.map(exp => `
                <div class="item-card">
                    <div class="item-header">
                        <div class="item-title">${escapeHtml(exp.job_title || 'Position')}</div>
                        <div class="item-date">${exp.start_date || ''}${exp.is_current ? ' - Present' : exp.end_date ? ' - ' + exp.end_date : ''}</div>
                    </div>
                    <div class="item-subtitle">${escapeHtml(exp.company_name || '')}</div>
                    ${exp.description ? `<div class="item-description">${escapeHtml(exp.description)}</div>` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function renderEducationSection(education) {
    return `
        <div class="data-section">
            <h3>Education <span class="count">(${education.length})</span></h3>
            ${education.map(edu => `
                <div class="item-card">
                    <div class="item-header">
                        <div class="item-title">${escapeHtml(edu.degree_title || edu.field_of_study || 'Degree')}</div>
                        <div class="item-date">${edu.graduation_year || ''}</div>
                    </div>
                    <div class="item-subtitle">${escapeHtml(edu.institution_name || '')}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderSkillsSection(skills) {
    const technical = skills.filter(s => s.category === 'technical' || !s.category);
    const soft = skills.filter(s => s.category === 'soft');

    return `
        <div class="data-section">
            <h3>Skills <span class="count">(${skills.length})</span></h3>
            ${technical.length ? `
                <div class="skills-grid" style="margin-bottom: 12px;">
                    ${technical.map(skill => `
                        <span class="skill-tag technical">
                            ${escapeHtml(skill.name)}
                            ${skill.level ? `<span class="skill-level">${skill.level}</span>` : ''}
                        </span>
                    `).join('')}
                </div>
            ` : ''}
            ${soft.length ? `
                <div class="skills-grid">
                    ${soft.map(skill => `
                        <span class="skill-tag soft">${escapeHtml(skill.name)}</span>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
}

function renderCertificationsSection(certifications) {
    return `
        <div class="data-section">
            <h3>Certifications <span class="count">(${certifications.length})</span></h3>
            ${certifications.map(cert => `
                <div class="item-card">
                    <div class="item-header">
                        <div class="item-title">${escapeHtml(cert.certification_name || cert.name || 'Certificate')}</div>
                        <div class="item-date">${cert.issue_date || ''}</div>
                    </div>
                    ${cert.issuing_organization ? `<div class="item-subtitle">${escapeHtml(cert.issuing_organization)}</div>` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function renderTrainingSection(training) {
    return `
        <div class="data-section">
            <h3>Training <span class="count">(${training.length})</span></h3>
            ${training.map(t => `
                <div class="item-card">
                    <div class="item-header">
                        <div class="item-title">${escapeHtml(t.training_name || t.name || 'Training')}</div>
                        <div class="item-date">${t.completion_date || ''}</div>
                    </div>
                    ${t.provider_name ? `<div class="item-subtitle">${escapeHtml(t.provider_name)}</div>` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function renderLanguagesSection(languages) {
    return `
        <div class="data-section">
            <h3>Languages <span class="count">(${languages.length})</span></h3>
            <div class="languages-grid">
                ${languages.map(lang => `
                    <div class="language-card">
                        <span class="language-name">${escapeHtml(lang.language_name || 'Language')}</span>
                        <span class="language-level">${lang.proficiency_level || 'N/A'}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function renderSoftwareSection(software) {
    return `
        <div class="data-section">
            <h3>Software <span class="count">(${software.length})</span></h3>
            <div class="software-grid">
                ${software.map(sw => `
                    <span class="software-tag">
                        ${escapeHtml(sw.name)}
                        ${sw.proficiency_level ? `<span class="skill-level">${sw.proficiency_level}</span>` : ''}
                    </span>
                `).join('')}
            </div>
        </div>
    `;
}

function renderLicensesSection(licenses) {
    return `
        <div class="data-section">
            <h3>Driving Licenses <span class="count">(${licenses.length})</span></h3>
            <div class="license-grid">
                ${licenses.map(lic => `
                    <span class="license-tag">${escapeHtml(lic.license_category || 'License')}</span>
                `).join('')}
            </div>
        </div>
    `;
}

// Chat
function initChat() {
    sendMessageBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });

    // Example query buttons
    document.querySelectorAll('.example-query').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.textContent.replace(/"/g, '');
            sendChatMessage();
        });
    });
}

async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    appendChatMessage('user', message);
    chatInput.value = '';

    try {
        const response = await fetch(`${API_BASE}/test/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message, execute: true, limit: 50 })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        appendChatMessage('assistant', formatQueryResponse(data));
    } catch (error) {
        appendChatMessage('error', 'Failed to process query. Please try again.');
    }
}

function appendChatMessage(type, content) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerHTML = `<div class="message-content">${content}</div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatQueryResponse(data) {
    if (data.error) return `<div class="hr-error">Error: ${escapeHtml(data.error)}</div>`;

    // Handle clarification requests
    if (data.clarification?.needed) {
        let response = `<div class="hr-clarification">`;
        response += `<div class="hr-section-title">🤔 ${data.clarification.question || 'Could you provide more details?'}</div>`;
        if (data.clarification.suggestions?.length > 0) {
            response += '<div class="hr-suggestions"><strong>Suggestions:</strong><ul>';
            response += data.clarification.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('');
            response += '</ul></div>';
        }
        response += '</div>';
        return response;
    }

    // Build response with HR Intelligence analysis if available
    let html = '';

    // HR Intelligence Analysis (new feature)
    if (data.hr_analysis) {
        html += formatHRAnalysis(data.hr_analysis);
    } else if (data.results && data.results.length > 0) {
        // Fallback to simple results display if no HR analysis
        const candidates = data.results.map(r => {
            const name = r.first_name && r.last_name
                ? `${r.first_name} ${r.last_name}`
                : r.name || 'Unknown';
            return `<li><strong>${escapeHtml(name)}</strong>${r.email ? ` (${escapeHtml(r.email)})` : ''}</li>`;
        });
        html = `<div class="hr-simple-results">
            <strong>Found ${data.results.length} candidates:</strong>
            <ul>${candidates.join('')}</ul>
        </div>`;
    } else if (data.sql) {
        html = `<div class="hr-info">Query executed. ${data.row_count || 0} results found.</div>`;
    } else {
        html = `<div class="hr-info">${data.message || 'No results found.'}</div>`;
    }

    // Add metadata footer
    if (data.latency_ms) {
        html += `<div class="hr-metadata">⏱ ${data.latency_ms}ms${data.hr_analysis?.latency_ms ? ` (HR: ${data.hr_analysis.latency_ms}ms)` : ''}</div>`;
    }

    return html;
}

function formatHRAnalysis(hr) {
    const lang = hr.analysis_language === 'el' ? 'el' : 'en';
    const labels = getHRLabels(lang);

    let html = '<div class="hr-analysis">';

    // Section 1: Request Analysis
    const ra = hr.request_analysis;
    if (ra) {
        html += `<div class="hr-section">
            <div class="hr-section-header" onclick="toggleHRSection(this)">
                <span class="hr-section-icon">📋</span>
                <span class="hr-section-title">${labels.requestAnalysis}</span>
                <span class="hr-toggle">▼</span>
            </div>
            <div class="hr-section-content">
                <div class="hr-summary">${escapeHtml(ra.summary)}</div>
                ${ra.mandatory_criteria?.length ? `<div class="hr-criteria mandatory"><strong>${labels.mandatory}:</strong> ${ra.mandatory_criteria.map(c => `<span class="hr-tag mandatory">${escapeHtml(c)}</span>`).join('')}</div>` : ''}
                ${ra.preferred_criteria?.length ? `<div class="hr-criteria preferred"><strong>${labels.preferred}:</strong> ${ra.preferred_criteria.map(c => `<span class="hr-tag preferred">${escapeHtml(c)}</span>`).join('')}</div>` : ''}
                ${ra.inferred_criteria?.length ? `<div class="hr-criteria inferred"><strong>${labels.inferred}:</strong> ${ra.inferred_criteria.map(c => `<span class="hr-tag inferred">${escapeHtml(c)}</span>`).join('')}</div>` : ''}
            </div>
        </div>`;
    }

    // Section 2: Query Outcome
    const qo = hr.query_outcome;
    if (qo) {
        html += `<div class="hr-section">
            <div class="hr-section-header" onclick="toggleHRSection(this)">
                <span class="hr-section-icon">📊</span>
                <span class="hr-section-title">${labels.queryOutcome}</span>
                <span class="hr-toggle">▼</span>
            </div>
            <div class="hr-section-content">
                <div class="hr-stats">
                    <div class="hr-stat"><span class="hr-stat-value">${qo.direct_matches}</span><span class="hr-stat-label">${labels.directMatches}</span></div>
                    <div class="hr-stat"><span class="hr-stat-value">${qo.total_matches}</span><span class="hr-stat-label">${labels.totalMatches}</span></div>
                    ${qo.relaxation_applied ? `<div class="hr-stat relaxed"><span class="hr-stat-value">✓</span><span class="hr-stat-label">${labels.relaxationApplied}</span></div>` : ''}
                </div>
                ${qo.zero_results_reason ? `<div class="hr-note">💡 ${escapeHtml(qo.zero_results_reason)}</div>` : ''}
            </div>
        </div>`;
    }

    // Section 3: Criteria Expansion (if applicable)
    const ce = hr.criteria_expansion;
    if (ce && ce.relaxations?.length > 0) {
        html += `<div class="hr-section">
            <div class="hr-section-header" onclick="toggleHRSection(this)">
                <span class="hr-section-icon">🔄</span>
                <span class="hr-section-title">${labels.criteriaExpansion}</span>
                <span class="hr-toggle">▼</span>
            </div>
            <div class="hr-section-content">
                ${ce.relaxations.map(r => `
                    <div class="hr-relaxation">
                        <div class="hr-relaxation-change">${escapeHtml(r.original)} → ${escapeHtml(r.relaxed_to)}</div>
                        <div class="hr-relaxation-reason">💡 ${escapeHtml(r.reasoning)}</div>
                    </div>
                `).join('')}
                ${ce.business_rationale ? `<div class="hr-rationale">📝 ${escapeHtml(ce.business_rationale)}</div>` : ''}
            </div>
        </div>`;
    }

    // Section 4: Ranked Candidates
    const rc = hr.ranked_candidates;
    if (rc && rc.length > 0) {
        html += `<div class="hr-section expanded">
            <div class="hr-section-header" onclick="toggleHRSection(this)">
                <span class="hr-section-icon">🏆</span>
                <span class="hr-section-title">${labels.rankedCandidates} (${rc.length})</span>
                <span class="hr-toggle">▼</span>
            </div>
            <div class="hr-section-content">
                ${rc.map(c => formatRankedCandidate(c, labels)).join('')}
            </div>
        </div>`;
    }

    // Section 5: HR Recommendation
    const rec = hr.hr_recommendation;
    if (rec && rec.recommendation_summary) {
        html += `<div class="hr-section expanded">
            <div class="hr-section-header" onclick="toggleHRSection(this)">
                <span class="hr-section-icon">💼</span>
                <span class="hr-section-title">${labels.hrRecommendation}</span>
                <span class="hr-toggle">▼</span>
            </div>
            <div class="hr-section-content">
                ${rec.top_candidates?.length ? `<div class="hr-top-candidates"><strong>${labels.topCandidates}:</strong> ${rec.top_candidates.map((n, i) => `<span class="hr-top-name">${i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'} ${escapeHtml(n)}</span>`).join('')}</div>` : ''}
                <div class="hr-recommendation-summary">${escapeHtml(rec.recommendation_summary)}</div>
                ${rec.interview_priorities?.length ? `<div class="hr-priorities"><strong>${labels.interviewPriorities}:</strong><ul>${rec.interview_priorities.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul></div>` : ''}
                ${rec.hiring_suggestions?.length ? `<div class="hr-suggestions"><strong>${labels.hiringSuggestions}:</strong><ul>${rec.hiring_suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></div>` : ''}
                ${rec.alternative_search ? `<div class="hr-alternative">🔍 ${escapeHtml(rec.alternative_search)}</div>` : ''}
            </div>
        </div>`;
    }

    html += '</div>';
    return html;
}

function formatRankedCandidate(c, labels) {
    const suitabilityClass = c.overall_suitability?.toLowerCase().replace(/[^a-z]/g, '-') || 'medium';
    const stars = getSuitabilityStars(c.overall_suitability);

    return `<div class="hr-candidate">
        <div class="hr-candidate-header">
            <span class="hr-rank">#${c.rank}</span>
            <span class="hr-candidate-name">${escapeHtml(c.candidate_name)}</span>
            <span class="hr-suitability ${suitabilityClass}">${stars} ${c.overall_suitability} (${Math.round(c.match_percentage)}%)</span>
        </div>
        <div class="hr-candidate-body">
            ${c.strengths?.length ? `<div class="hr-strengths"><strong>✅ ${labels.strengths}:</strong><ul>${c.strengths.map(s => `<li><span class="hr-confidence ${s.confidence?.toLowerCase()}">${getConfidenceIcon(s.confidence)}</span> ${escapeHtml(s.criterion)}: ${escapeHtml(s.candidate_value)}</li>`).join('')}</ul></div>` : ''}
            ${c.gaps?.length ? `<div class="hr-gaps"><strong>⚠️ ${labels.gaps}:</strong><ul>${c.gaps.map(g => `<li><span class="hr-severity ${g.severity?.toLowerCase()}">${getSeverityIcon(g.severity)}</span> ${escapeHtml(g.criterion)}: ${escapeHtml(g.gap_description)}${g.mitigation ? ` <em>(${escapeHtml(g.mitigation)})</em>` : ''}</li>`).join('')}</ul></div>` : ''}
            ${c.risks?.length ? `<div class="hr-risks"><strong>⚡ ${labels.risks}:</strong><ul>${c.risks.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul></div>` : ''}
            ${c.interview_focus?.length ? `<div class="hr-interview-focus"><strong>🎯 ${labels.interviewFocus}:</strong> ${c.interview_focus.map(f => `<span class="hr-focus-tag">${escapeHtml(f)}</span>`).join('')}</div>` : ''}
        </div>
    </div>`;
}

function getHRLabels(lang) {
    return lang === 'el' ? {
        requestAnalysis: 'Ανάλυση Αιτήματος',
        queryOutcome: 'Αποτελέσματα Αναζήτησης',
        criteriaExpansion: 'Χαλάρωση Κριτηρίων',
        rankedCandidates: 'Κατάταξη Υποψηφίων',
        hrRecommendation: 'Σύσταση HR',
        mandatory: 'Υποχρεωτικά',
        preferred: 'Επιθυμητά',
        inferred: 'Υπονοούμενα',
        directMatches: 'Άμεσα',
        totalMatches: 'Σύνολο',
        relaxationApplied: 'Χαλάρωση',
        topCandidates: 'Κορυφαίοι',
        interviewPriorities: 'Προτεραιότητες Συνέντευξης',
        hiringSuggestions: 'Προτάσεις Πρόσληψης',
        strengths: 'Πλεονεκτήματα',
        gaps: 'Κενά',
        risks: 'Κίνδυνοι',
        interviewFocus: 'Εστίαση Συνέντευξης'
    } : {
        requestAnalysis: 'Request Analysis',
        queryOutcome: 'Query Outcome',
        criteriaExpansion: 'Criteria Expansion',
        rankedCandidates: 'Ranked Candidates',
        hrRecommendation: 'HR Recommendation',
        mandatory: 'Mandatory',
        preferred: 'Preferred',
        inferred: 'Inferred',
        directMatches: 'Direct',
        totalMatches: 'Total',
        relaxationApplied: 'Relaxed',
        topCandidates: 'Top Candidates',
        interviewPriorities: 'Interview Priorities',
        hiringSuggestions: 'Hiring Suggestions',
        strengths: 'Strengths',
        gaps: 'Gaps',
        risks: 'Risks',
        interviewFocus: 'Interview Focus'
    };
}

function getSuitabilityStars(suitability) {
    const map = { 'High': '⭐⭐⭐', 'Medium-High': '⭐⭐½', 'Medium': '⭐⭐', 'Medium-Low': '⭐½', 'Low': '⭐' };
    return map[suitability] || '⭐';
}

function getConfidenceIcon(confidence) {
    return confidence === 'Confirmed' ? '✓' : confidence === 'Likely' ? '~' : '?';
}

function getSeverityIcon(severity) {
    return severity === 'Major' ? '🔴' : severity === 'Moderate' ? '🟡' : '🟢';
}

function toggleHRSection(header) {
    const section = header.parentElement;
    section.classList.toggle('expanded');
    section.classList.toggle('collapsed');
}

// Status labels
const STATUS_LABELS = {
    'uploading': 'Uploading',
    'pending': 'Queued',
    'extracting': 'Extracting Text',
    'parsing': 'AI Parsing',
    'mapping': 'Mapping Skills',
    'storing': 'Saving',
    'indexing': 'Indexing',
    'completed': 'Completed',
    'failed': 'Failed'
};

function getStepLabel(status) {
    return STATUS_LABELS[status] || status;
}

// Utilities
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ============================================
// Candidates Page Functions
// ============================================

function initCandidates() {
    // Event listeners
    refreshCandidatesBtn.addEventListener('click', loadCandidates);
    candidateSearch.addEventListener('input', debounce(filterAndRenderCandidates, 300));
    roleFilter.addEventListener('change', filterAndRenderCandidates);
    sortOrder.addEventListener('change', filterAndRenderCandidates);

    // Delete modal handlers
    closeDeleteModalBtn.addEventListener('click', closeDeleteModal);
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    confirmDeleteBtn.addEventListener('click', executeDelete);

    // Close modal on overlay click
    deleteModal.addEventListener('click', (e) => {
        if (e.target === deleteModal) closeDeleteModal();
    });

    // Load candidates on init
    loadCandidates();
}

async function loadCandidates() {
    candidatesLoading.style.display = 'flex';
    candidatesEmpty.style.display = 'none';
    candidatesByRole.innerHTML = '';

    try {
        // Try to load from API
        const response = await fetch(`${API_BASE}/test/candidates`);

        if (response.ok) {
            const data = await response.json();
            // Transform database candidates to display format
            allCandidates = (data.candidates || []).map(transformDbCandidate);
        } else if (response.status === 404) {
            // Endpoint not implemented yet - use session data
            allCandidates = getSessionCandidates();
        } else {
            throw new Error('Failed to load candidates');
        }
    } catch (error) {
        console.warn('API not available, using session data:', error.message);
        // Fallback to session data
        allCandidates = getSessionCandidates();
    }

    candidatesLoading.style.display = 'none';

    // Update badge
    updateCandidatesBadge();

    // Populate role filter
    populateRoleFilter();

    // Render candidates
    filterAndRenderCandidates();
}

function transformDbCandidate(dbCandidate) {
    /**
     * Transform database candidate format to the format used by the UI.
     * Database returns flat structure with arrays; UI expects parsed_cv format.
     */
    const experience = dbCandidate.experience || [];
    const currentRole = experience.length > 0
        ? experience[0].job_title || 'Unknown Role'
        : 'Unknown Role';

    return {
        id: dbCandidate.candidate_id,
        candidate_id: dbCandidate.candidate_id,
        first_name: dbCandidate.first_name || '',
        last_name: dbCandidate.last_name || '',
        email: dbCandidate.email || '',
        phone: dbCandidate.phone || '',
        city: dbCandidate.address_city || '',
        current_role: currentRole,
        skills_count: (dbCandidate.skills || []).length,
        experience_count: experience.length,
        education_count: (dbCandidate.education || []).length,
        upload_date: dbCandidate.created_at,
        filename: dbCandidate.original_filename,
        cv_url: dbCandidate.s3_key ? `https://lcmgo-cagenai-prod-cv-uploads-eun1.s3.eu-north-1.amazonaws.com/${dbCandidate.s3_key}` : null,
        // Store full data for viewing details
        data: {
            candidate_id: dbCandidate.candidate_id,
            parsed_cv: {
                personal: {
                    first_name: dbCandidate.first_name,
                    last_name: dbCandidate.last_name,
                    email: dbCandidate.email,
                    phone: dbCandidate.phone,
                    date_of_birth: dbCandidate.date_of_birth,
                    nationality: dbCandidate.nationality,
                    address_street: dbCandidate.address_street,
                    address_city: dbCandidate.address_city,
                    address_postal_code: dbCandidate.address_postal_code,
                    address_country: dbCandidate.address_country,
                    military_status: dbCandidate.military_status,
                },
                experience: experience,
                education: dbCandidate.education || [],
                skills: dbCandidate.skills || [],
                languages: dbCandidate.languages || [],
                certifications: dbCandidate.certifications || [],
                training: dbCandidate.training || [],
                software: dbCandidate.software || [],
                driving_licenses: dbCandidate.driving_licenses || [],
            },
            quality_score: dbCandidate.quality_score,
            data_completeness: dbCandidate.data_completeness,
        }
    };
}

function getSessionCandidates() {
    // Convert completed results to candidates format
    return completedResults.map((result, index) => {
        const cv = result.data?.parsed_cv || {};
        const personal = cv.personal || {};
        const experience = cv.experience || [];

        // Get most recent role from experience
        const currentRole = experience.length > 0
            ? experience[0].job_title || 'Unknown Role'
            : 'Unknown Role';

        return {
            id: result.correlationId || `session-${index}`,
            candidate_id: result.data?.candidate_id || null,
            first_name: personal.first_name || '',
            last_name: personal.last_name || '',
            email: personal.email || '',
            phone: personal.phone || '',
            city: personal.address_city || '',
            current_role: currentRole,
            skills_count: cv.skills?.length || 0,
            experience_count: cv.experience?.length || 0,
            education_count: cv.education?.length || 0,
            upload_date: new Date().toISOString(),
            filename: result.filename,
            cv_url: null, // Would need to store S3 URL
            data: result.data
        };
    });
}

function updateCandidatesBadge() {
    if (allCandidates.length > 0) {
        candidatesBadge.style.display = 'flex';
        candidatesBadge.textContent = allCandidates.length;
    } else {
        candidatesBadge.style.display = 'none';
    }
}

function populateRoleFilter() {
    // Get unique roles
    const roles = new Set();
    allCandidates.forEach(c => {
        if (c.current_role && c.current_role !== 'Unknown Role') {
            roles.add(c.current_role);
        }
    });

    // Clear and repopulate
    roleFilter.innerHTML = '<option value="">All Roles</option>';
    Array.from(roles).sort().forEach(role => {
        const option = document.createElement('option');
        option.value = role;
        option.textContent = role;
        roleFilter.appendChild(option);
    });
}

function filterAndRenderCandidates() {
    const searchTerm = candidateSearch.value.toLowerCase().trim();
    const selectedRole = roleFilter.value;
    const sort = sortOrder.value;

    // Filter candidates
    let filtered = allCandidates.filter(c => {
        // Search filter
        if (searchTerm) {
            const fullName = `${c.first_name} ${c.last_name}`.toLowerCase();
            const email = (c.email || '').toLowerCase();
            const role = (c.current_role || '').toLowerCase();
            if (!fullName.includes(searchTerm) &&
                !email.includes(searchTerm) &&
                !role.includes(searchTerm)) {
                return false;
            }
        }

        // Role filter
        if (selectedRole && c.current_role !== selectedRole) {
            return false;
        }

        return true;
    });

    // Sort candidates
    filtered.sort((a, b) => {
        switch (sort) {
            case 'newest':
                return new Date(b.upload_date) - new Date(a.upload_date);
            case 'oldest':
                return new Date(a.upload_date) - new Date(b.upload_date);
            case 'name':
                const nameA = `${a.first_name} ${a.last_name}`.toLowerCase();
                const nameB = `${b.first_name} ${b.last_name}`.toLowerCase();
                return nameA.localeCompare(nameB);
            default:
                return 0;
        }
    });

    // Check if empty
    if (filtered.length === 0) {
        candidatesEmpty.style.display = 'flex';
        candidatesByRole.innerHTML = '';
        return;
    }

    candidatesEmpty.style.display = 'none';

    // Group by role
    const grouped = new Map();
    filtered.forEach(c => {
        const role = c.current_role || 'Unknown Role';
        if (!grouped.has(role)) {
            grouped.set(role, []);
        }
        grouped.get(role).push(c);
    });

    // Render grouped candidates
    renderCandidateGroups(grouped);
}

function renderCandidateGroups(grouped) {
    candidatesByRole.innerHTML = '';

    // Sort groups alphabetically
    const sortedGroups = Array.from(grouped.entries()).sort((a, b) => {
        if (a[0] === 'Unknown Role') return 1;
        if (b[0] === 'Unknown Role') return -1;
        return a[0].localeCompare(b[0]);
    });

    sortedGroups.forEach(([role, candidates]) => {
        const groupEl = document.createElement('div');
        groupEl.className = 'role-group';
        groupEl.innerHTML = `
            <div class="role-group-header" onclick="toggleRoleGroup(this)">
                <div class="role-group-title">
                    <svg class="collapse-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    <span>${escapeHtml(role)}</span>
                    <span class="role-count">${candidates.length}</span>
                </div>
            </div>
            <div class="role-group-content">
                ${candidates.map(c => renderCandidateListCard(c)).join('')}
            </div>
        `;
        candidatesByRole.appendChild(groupEl);
    });
}

function renderCandidateListCard(candidate) {
    const fullName = `${candidate.first_name} ${candidate.last_name}`.trim() || 'Unknown';
    const initials = getInitials(candidate.first_name, candidate.last_name);
    const uploadDate = formatUploadDate(candidate.upload_date);

    return `
        <div class="candidate-list-card" data-id="${candidate.id}">
            <div class="candidate-avatar">${initials}</div>
            <div class="candidate-list-info">
                <div class="candidate-list-name">${escapeHtml(fullName)}</div>
                <div class="candidate-list-details">
                    ${candidate.email ? `<span class="detail-item">${escapeHtml(candidate.email)}</span>` : ''}
                    ${candidate.city ? `<span class="detail-item">${escapeHtml(candidate.city)}</span>` : ''}
                </div>
                <div class="candidate-list-meta">
                    <span class="meta-badge">${candidate.skills_count} skills</span>
                    <span class="meta-badge">${candidate.experience_count} exp</span>
                    <span class="meta-badge">${candidate.education_count} edu</span>
                    <span class="upload-date">Uploaded: ${uploadDate}</span>
                </div>
            </div>
            <div class="candidate-list-actions">
                <button class="btn-icon btn-view" onclick="viewCandidateCV('${candidate.id}')" title="View CV">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>
                </button>
                <button class="btn-icon btn-edit" onclick="editCandidate('${candidate.id}')" title="Edit">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="btn-icon btn-delete" onclick="confirmDeleteCandidate('${candidate.id}')" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;
}

function getInitials(firstName, lastName) {
    const f = (firstName || '').charAt(0).toUpperCase();
    const l = (lastName || '').charAt(0).toUpperCase();
    return f + l || '?';
}

function formatUploadDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    // Less than 24 hours
    if (diff < 24 * 60 * 60 * 1000) {
        const hours = Math.floor(diff / (60 * 60 * 1000));
        if (hours < 1) {
            const mins = Math.floor(diff / (60 * 1000));
            return mins < 1 ? 'Just now' : `${mins} min ago`;
        }
        return `${hours}h ago`;
    }

    // Less than 7 days
    if (diff < 7 * 24 * 60 * 60 * 1000) {
        const days = Math.floor(diff / (24 * 60 * 60 * 1000));
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }

    // Format as date
    return date.toLocaleDateString('el-GR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function toggleRoleGroup(header) {
    const group = header.closest('.role-group');
    group.classList.toggle('collapsed');
}

// View original CV file
function viewCandidateCV(candidateId) {
    const candidate = allCandidates.find(c => c.id === candidateId);
    if (!candidate) {
        alert('Candidate not found');
        return;
    }

    // If we have a CV URL, open it
    if (candidate.cv_url) {
        window.open(candidate.cv_url, '_blank');
        return;
    }

    // Otherwise, show candidate details in Results tab
    if (candidate.data) {
        // Navigate to Results page and show this candidate
        completedResults = completedResults.filter(r => r.correlationId !== candidate.id);
        completedResults.unshift({
            correlationId: candidate.id,
            filename: candidate.filename || 'CV',
            candidateName: `${candidate.first_name} ${candidate.last_name}`.trim(),
            processingTime: 0,
            data: candidate.data
        });
        updateResultsBadge();
        renderResultsTabs();

        // Switch to results page
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelector('[data-page="results"]').classList.add('active');
        document.getElementById('resultsPage').classList.add('active');
    } else {
        alert('CV file not available. The original file may need to be retrieved from the server.');
    }
}

// Edit candidate - navigate to results with edit mode
function editCandidate(candidateId) {
    // For now, just view the candidate
    // Full edit functionality would require backend support
    viewCandidateCV(candidateId);
    alert('Edit mode coming soon. For now, you can view the candidate details.');
}

// Delete confirmation
function confirmDeleteCandidate(candidateId) {
    const candidate = allCandidates.find(c => c.id === candidateId);
    if (!candidate) return;

    deleteCandidate = candidate;
    deleteCandidateName.textContent = `${candidate.first_name} ${candidate.last_name}`.trim() || 'Unknown';
    deleteModal.style.display = 'flex';
}

function closeDeleteModal() {
    deleteModal.style.display = 'none';
    deleteCandidate = null;
}

async function executeDelete() {
    if (!deleteCandidate) return;

    const candidateId = deleteCandidate.id;
    const candidateDbId = deleteCandidate.candidate_id;

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = 'Deleting...';

    try {
        // Try to delete from API if we have a database ID
        if (candidateDbId) {
            const response = await fetch(`${API_BASE}/test/candidates/${candidateDbId}`, {
                method: 'DELETE'
            });

            if (!response.ok && response.status !== 404) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to delete from server');
            }
        }

        // Remove from local state
        allCandidates = allCandidates.filter(c => c.id !== candidateId);
        completedResults = completedResults.filter(r => r.correlationId !== candidateId);

        // Update UI
        updateCandidatesBadge();
        updateResultsBadge();
        filterAndRenderCandidates();
        renderResultsTabs();

        closeDeleteModal();

        // Show success feedback
        console.log(`Candidate ${candidateDbId || candidateId} deleted successfully`);
    } catch (error) {
        console.error('Delete failed:', error);
        alert('Failed to delete candidate: ' + error.message);
    } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = 'Delete';
    }
}

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
