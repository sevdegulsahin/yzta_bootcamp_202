
(function () {
    'use strict';

    /**
     * @namespace Interviewly
     * @description Global namespace for the application's client-side logic.
     */
    const Interviewly = window.Interviewly || {};

    /**
     * Shows a notification message.
     * @param {string} message - The message to display.
     * @param {string} [type='info'] - The type of notification ('info', 'success', 'error').
     */
    Interviewly.showNotification = (message, type = 'info') => {
        const container = document.getElementById('notification-container');
        if (!container) return;

        const iconMap = {
            info: 'fa-info-circle',
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle'
        };

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas ${iconMap[type]}"></i>
            <span>${message}</span>
        `;
        container.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    };

    window.Interviewly = Interviewly;

    /**
     * Initializes page-specific logic after the DOM is fully loaded.
     */
    document.addEventListener('DOMContentLoaded', () => {

        // Initialize AOS library for animations if it exists
        if (typeof AOS !== 'undefined') {
            AOS.init({
                duration: 800,
                once: true,
                disable: 'mobile'
            });
        }

        // Router for page-specific scripts
        const pageId = document.body.dataset.pageId;
        switch (pageId) {
            case 'auth':
                initAuthPage();
                break;
            case 'create-interview':
                initCreateInterviewPage();
                break;
            case 'edit-profile':
                initEditProfilePage();
                break;
            case 'interview':
                initInterviewPage();
                break;
            case 'my-interviews':
                initMyInterviewsPage();
                break;
            case 'profile':
                initProfilePage();
                break;
            case 'test-results':
                initTestResultsPage();
                break;
        }
        // This runs outside the router to catch pages without a pageId
        initInterviewQuestionPage();
    });

    /**
     * Initializes logic for authentication pages (Login & Register).
     */
    function initAuthPage() {
        const authForm = document.querySelector('.auth-form');
        if (!authForm) return;

        const submitBtn = authForm.querySelector('.btn-submit');

        authForm.addEventListener('submit', (e) => {
            let isValid = true;
            authForm.querySelectorAll('input[required]').forEach(input => {
                if (!input.value.trim()) isValid = false;
            });

            if (!isValid) {
                e.preventDefault();
                return Interviewly.showNotification("Lütfen tüm zorunlu alanları doldurun.", "error");
            }

            if (authForm.querySelector('#confirm_password')) {
                const password = authForm.querySelector('#password').value;
                const confirmPassword = authForm.querySelector('#confirm_password').value;
                if (password !== confirmPassword) {
                    e.preventDefault();
                    return Interviewly.showNotification("Şifreler eşleşmiyor.", "error");
                }
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${submitBtn.innerText}...`;
            }
        });

        const toggleBtn = authForm.querySelector('.password-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const passwordInput = document.getElementById('password');
                const icon = toggleBtn.querySelector('i');
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    icon.classList.replace('fa-eye', 'fa-eye-slash');
                } else {
                    passwordInput.type = 'password';
                    icon.classList.replace('fa-eye-slash', 'fa-eye');
                }
            });
        }
    }

    /**
     * Initializes logic for the 'Create Interview' page.
     */
    function initCreateInterviewPage() {
        const pageDataEl = document.getElementById('page-data');
        if (!pageDataEl) return;

        let selectedType = pageDataEl.dataset.selectedType || '';
        let selectedMode = pageDataEl.dataset.selectedMode || '';

        const form = document.getElementById('interviewForm');
        const typeCards = document.querySelectorAll('.type-card');
        const modeSection = document.getElementById('mode-section');
        const summarySection = document.getElementById('summary-section');
        const techAreaItem = document.getElementById('technical-area-item');
        const techAreaSelect = document.getElementById('technical_area');
        const modeChoiceSelect = document.getElementById('mode_choice');
        const startButton = document.getElementById('startButton');

        function updateSummary() {
            if (!summarySection) return;
            const summaryData = {
                type: document.getElementById('summary-type'),
                mode: document.getElementById('summary-mode'),
                area: document.getElementById('summary-area'),
                areaItem: document.getElementById('summary-area-item'),
                difficulty: document.getElementById('summary-difficulty'),
                duration: document.getElementById('summary-duration'),
            };

            const typeMap = { assistant: 'AI Asistan ile Mülakat', written_test: 'Yazılı Test' };
            const modeMap = { general: 'Genel Yetenek', technical: 'Teknik' };
            const difficultyMap = { beginner: 'Başlangıç', intermediate: 'Orta', advanced: 'İleri' };

            summaryData.type.textContent = typeMap[selectedType] || '-';
            summaryData.mode.textContent = modeMap[selectedMode] || '-';

            const techAreaValue = techAreaSelect.value;
            if (selectedMode === 'technical' && techAreaValue) {
                summaryData.area.textContent = techAreaValue.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                summaryData.areaItem.style.display = 'flex';
            } else {
                summaryData.areaItem.style.display = 'none';
            }

            summaryData.difficulty.textContent = difficultyMap[document.getElementById('difficulty').value] || '-';
            summaryData.duration.textContent = `${document.getElementById('duration').value} dakika`;

            if (selectedType && selectedMode) {
                summarySection.style.display = 'block';
            }
        }

        function checkFormCompletion() {
            let isValid = selectedType && selectedMode;
            if (selectedMode === 'technical') {
                isValid = isValid && techAreaSelect.value;
            }
            startButton.disabled = !isValid;
        }

        function handleModeChoiceChange(mode) {
            selectedMode = mode;
            if (mode === 'technical') {
                techAreaItem.style.display = 'block';
                techAreaSelect.required = true;
            } else {
                techAreaItem.style.display = 'none';
                techAreaSelect.required = false;
                techAreaSelect.value = '';
            }
            updateSummary();
            checkFormCompletion();
        }

        function selectInterviewType(type) {
            typeCards.forEach(card => card.classList.remove('selected'));
            const selectedCard = document.querySelector(`.type-card[data-type="${type}"]`);
            if (selectedCard) selectedCard.classList.add('selected');

            document.getElementById('interview_type').value = type;
            selectedType = type;
            modeSection.style.display = 'block';
            updateSummary();
            checkFormCompletion();
        }

        function resetForm() {
            selectedType = '';
            selectedMode = '';
            form.reset();
            typeCards.forEach(card => card.classList.remove('selected'));
            document.getElementById('interview_type').value = '';
            modeSection.style.display = 'none';
            summarySection.style.display = 'none';
            techAreaItem.style.display = 'none';
            startButton.disabled = true;
            Interviewly.showNotification('Form sıfırlandı.', 'info');
        }

        function quickStart(type, mode, area = null) {
            selectInterviewType(type);
            modeChoiceSelect.value = mode;
            handleModeChoiceChange(mode);
            if (area) {
                techAreaSelect.value = area;
            }
            updateSummary();
            checkFormCompletion();
            summarySection.scrollIntoView({ behavior: 'smooth' });
        }

        // Event Listeners
        typeCards.forEach(card => card.addEventListener('click', () => selectInterviewType(card.dataset.type)));
        modeChoiceSelect.addEventListener('change', (e) => handleModeChoiceChange(e.target.value));
        form.addEventListener('change', () => { updateSummary(); checkFormCompletion(); });
        document.querySelector('.btn-secondary').addEventListener('click', resetForm);
        document.querySelectorAll('.quick-start-btn').forEach(btn => btn.addEventListener('click', (e) => {
            const data = e.currentTarget.dataset;
            quickStart(data.type, data.mode, data.area);
        }));

        form.addEventListener('submit', () => {
            startButton.disabled = true;
            startButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Hazırlanıyor...';
        });

        // Initial state setup
        if (selectedType) selectInterviewType(selectedType);
        if (selectedMode) handleModeChoiceChange(selectedMode);
    }

    /**
     * Initializes logic for the 'Edit Profile' page.
     */

    function previewAvatar(event) {
        const input = event.target;
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                document.getElementById('avatarPreview').src = e.target.result;
            }
            reader.readAsDataURL(input.files[0]);
        }
    }


    /**
     * Initializes logic for the real-time 'Interview' page.
     */
    function initInterviewPage() {
        const pageDataEl = document.getElementById('page-data');
        if (!pageDataEl) return;

        let startTime = Date.now();
        let messageCount = parseInt(pageDataEl.dataset.chatHistoryLength, 10) || 0;
        const userInput = document.getElementById('user-input');
        const chatContainer = document.querySelector('.chat-container');

        const timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            const display = `${minutes}:${seconds}`;
            document.getElementById('timer-display').textContent = display;
            document.getElementById('elapsed-time').textContent = display;
        }, 1000);

        const autoResize = (textarea) => {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
        };

        const updateCharCounter = () => {
            const counter = document.getElementById('char-counter');
            const count = userInput.value.length;
            counter.textContent = `${count}/1000`;
            if (count > 900) counter.style.color = '#ef4444';
            else if (count > 800) counter.style.color = '#f59e0b';
            else counter.style.color = 'var(--text-muted)';
        };

        const scrollToBottom = () => chatContainer.scrollTop = chatContainer.scrollHeight;

        userInput.addEventListener('input', () => {
            autoResize(userInput);
            updateCharCounter();
        });

        document.getElementById('chat-form').addEventListener('submit', function (e) {
            e.preventDefault();
            if (!userInput.value.trim()) return;
            document.getElementById('send-btn').disabled = true;
            document.getElementById('typing-indicator').style.display = 'flex';
            scrollToBottom();
            setTimeout(() => this.submit(), 300);
        });

        const endModal = document.getElementById('endModal');
        document.querySelector('.btn-danger').addEventListener('click', () => endModal.classList.add('show'));
        endModal.querySelector('.btn-secondary').addEventListener('click', () => endModal.classList.remove('show'));
        endModal.addEventListener('click', (e) => { if (e.target === endModal) endModal.classList.remove('show'); });
        endModal.querySelector('.btn-danger').addEventListener('click', () => window.location.href = pageDataEl.dataset.resetUrl);

        document.querySelector('.btn-secondary[onclick]').addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Mülakatı yeniden başlatmak istediğinizden emin misiniz?')) {
                window.location.href = pageDataEl.dataset.resetUrl;
            }
        });

        scrollToBottom();
        userInput.focus();
        updateCharCounter();
        document.getElementById('message-count').textContent = messageCount;
    }

    /**
     * Initializes logic for the 'Interview Question' page.
     */
    function initInterviewQuestionPage() {
        const questionPage = document.querySelector('.question-page');
        if (!questionPage) {
            return; // Not on the interview question page
        }

        const questionNum = questionPage.dataset.questionNum;
        if (!questionNum) {
            console.error('Question number not found on page.');
            return;
        }

        let startTime = Date.now();
        let timerInterval;

        // Initialize timer
        function startTimer() {
            timerInterval = setInterval(updateTimer, 1000);
        }
        function updateTimer() {
            const timerEl = document.getElementById('timer');
            if (!timerEl) return;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            const display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            timerEl.textContent = display;
        }

        // Character and word counter
        function updateCounters() {
            const textarea = document.getElementById('user_input');
            if (!textarea) return;
            const text = textarea.value;
            const charCount = text.length;
            const wordCount = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
            document.getElementById('charCounter').textContent = `${charCount}/2000`;
            document.getElementById('wordCounter').textContent = `${wordCount} kelime`;
            const charCounterEl = document.getElementById('charCounter');
            if (charCount > 1800) {
                charCounterEl.style.color = '#ef4444';
            } else if (charCount > 1600) {
                charCounterEl.style.color = '#f59e0b';
            } else {
                charCounterEl.style.color = 'var(--text-muted)';
            }
        }

        // Auto-resize textarea
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
        }

        // Copy question text
        function copyQuestion() {
            const questionText = document.querySelector('.question-text').textContent;
            navigator.clipboard.writeText(questionText.trim()).then(() => {
                Interviewly.showNotification('Soru kopyalandı!', 'info');
            }).catch(err => {
                Interviewly.showNotification('Kopyalama başarısız oldu.', 'error');
                console.error('Kopyalama hatası:', err);
            });
        }

        // Toggle fullscreen
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    Interviewly.showNotification(`Hata: ${err.message}`, 'error');
                });
            } else {
                document.exitFullscreen();
            }
        }

        // Save draft functionality
        const saveModal = document.getElementById('saveModal');

        function showSaveModal() {
            const textarea = document.getElementById('user_input');
            if (textarea.value.trim()) {
                if (saveModal) saveModal.classList.add('show');
            } else {
                Interviewly.showNotification('Kaydedilecek cevap bulunamadı.', 'error');
            }
        }

        function closeModal() {
            if (saveModal) saveModal.classList.remove('show');
        }

        function confirmSaveDraft() {
            const textarea = document.getElementById('user_input');
            const draft = {
                question: String(questionNum),
                answer: textarea.value,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem('interview_draft', JSON.stringify(draft));
            Interviewly.showNotification('Taslak kaydedildi!', 'success');
            closeModal();
        }

        // Load draft on page load
        function loadDraft() {
            const draftJSON = localStorage.getItem('interview_draft');
            if (draftJSON) {
                try {
                    const draftData = JSON.parse(draftJSON);
                    if (String(draftData.question) === String(questionNum)) {
                        const textarea = document.getElementById('user_input');
                        textarea.value = draftData.answer;
                        updateCounters();
                        autoResize(textarea);
                        Interviewly.showNotification('Kaydedilmiş taslak yüklendi.', 'info');
                    }
                } catch (e) {
                    console.error("Failed to parse draft from localStorage", e);
                    localStorage.removeItem('interview_draft');
                }
            }
        }

        // --- Start of logic from original DOMContentLoaded ---
        startTimer();

        const textarea = document.getElementById('user_input');
        if (textarea) {
            textarea.addEventListener('input', function () {
                updateCounters();
                autoResize(this);
            });
            textarea.focus();
        }

        loadDraft();

        document.getElementById('fullscreenBtn')?.addEventListener('click', toggleFullscreen);
        document.getElementById('copyBtn')?.addEventListener('click', copyQuestion);
        document.getElementById('saveDraftBtn')?.addEventListener('click', showSaveModal);
        document.getElementById('cancelSaveBtn')?.addEventListener('click', closeModal);
        document.getElementById('confirmSaveBtn')?.addEventListener('click', confirmSaveDraft);
        
        if (saveModal) {
            saveModal.addEventListener('click', function (e) {
                if (e.target === this) {
                    closeModal();
                }
            });
        }

        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const submitBtn = document.getElementById('submitBtn');
                if (document.activeElement === textarea && submitBtn) {
                    e.preventDefault();
                    submitBtn.click();
                }
            }
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                showSaveModal();
            }
            if (e.key === 'Escape' && saveModal && saveModal.classList.contains('show')) {
                closeModal();
            }
        });

        const answerForm = document.getElementById('answerForm');
        if(answerForm) {
            answerForm.addEventListener('submit', function (e) {
                const textarea = document.getElementById('user_input');
                const submitBtn = document.getElementById('submitBtn');
                if (!textarea.value.trim()) {
                    e.preventDefault();
                    Interviewly.showNotification('Lütfen bir cevap yazın.', 'error');
                    return;
                }
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gönderiliyor...';
                localStorage.removeItem('interview_draft');
            });
        }
    }

    /**
     * Initializes logic for the 'My Interviews' page.
     */
    function initMyInterviewsPage() {
        const searchInput = document.getElementById('searchInput');
        const filterBtns = document.querySelectorAll('.filter-btn');
        const noResultsEl = document.getElementById('noResults');
        const cards = document.querySelectorAll('.interview-card');

        let currentFilter = 'all';
        let currentSearch = '';

        const applyFilters = () => {
            let visibleCount = 0;
            cards.forEach(card => {
                const category = card.dataset.category || 'general';
                const title = card.querySelector('.interview-title').textContent.toLowerCase();
                const question = card.querySelector('.question-text').textContent.toLowerCase();
                const searchMatch = !currentSearch || title.includes(currentSearch) || question.includes(currentSearch);
                const filterMatch = currentFilter === 'all' || category === currentFilter;

                if (searchMatch && filterMatch) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            noResultsEl.style.display = visibleCount === 0 ? 'block' : 'none';
        };

        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            applyFilters();
        });

        filterBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                currentFilter = this.dataset.filter;
                filterBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                applyFilters();
            });
        });
    }

    /**
     * Initializes logic for the 'Profile' page.
     */
    function initProfilePage() {
        const pageDataEl = document.getElementById('page-data');
        if (!pageDataEl || typeof Chart === 'undefined') return;

        const weeklyData = JSON.parse(pageDataEl.dataset.weeklyData);

        const ctx = document.getElementById('performanceChart').getContext('2d');
        const performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: weeklyData.labels,
                datasets: [{
                    label: 'Günlük Skor',
                    data: weeklyData.data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#64748b' } },
                    x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#64748b' } }
                }
            }
        });

        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            if (!btn.href) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    Interviewly.showNotification('Bu özellik yakında eklenecek!', 'info');
                });
            }
        });
    }

    /**
     * Initializes logic for the 'Test Results' page.
     */
    function initTestResultsPage() {
        const pageDataEl = document.getElementById('page-data');
        if (!pageDataEl || typeof Chart === 'undefined') return;

        const chartData = JSON.parse(pageDataEl.dataset.chartData);

        if (chartData.labels && chartData.data) {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        data: chartData.data,
                        backgroundColor: ['#22c55e', '#ef4444', '#6b7280'],
                        borderColor: ['#16a34a', '#dc2626', '#4b5563'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: 'var(--text-primary)', font: { size: 14 } }
                        }
                    }
                }
            });
        }

        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                if (action === 'export') {
                    Interviewly.showNotification('Sonuçlar indiriliyor...', 'info');
                } else if (action === 'share') {
                    Interviewly.showNotification('Paylaşım özelliği yakında gelecek.', 'info');
                }
            });
        });
    }

})();