
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

     /**
     * Exports test results as a JSON file.
     * Attached to the global namespace to be called from onclick.
     */
    Interviewly.exportResults = () => {
        const pageDataEl = document.getElementById('page-data-export');
        if (!pageDataEl) {
            Interviewly.showNotification('Dışa aktarılacak veri bulunamadı.', 'error');
            return;
        }
        
        try {
            const results = JSON.parse(pageDataEl.dataset.exportData);
            results.timestamp = new Date().toISOString();
            const dataStr = JSON.stringify(results, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = `test-results-${results.username}-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(link.href);
            Interviewly.showNotification('Sonuçlar indiriliyor...', 'info');
        } catch (e) {
            Interviewly.showNotification('Sonuçları dışa aktarırken bir hata oluştu.', 'error');
            console.error("Export error:", e);
        }
    };

    /**
     * Shares test results using the Web Share API or copies to clipboard.
     * Attached to the global namespace to be called from onclick.
     */
    Interviewly.shareResults = async () => {
        const pageDataEl = document.getElementById('page-data-export');
        if (!pageDataEl) {
            Interviewly.showNotification('Paylaşılacak veri bulunamadı.', 'error');
            return;
        }

        try {
            const results = JSON.parse(pageDataEl.dataset.exportData);
            const shareData = {
                title: 'Interviewly Test Sonuçlarım',
                text: `${results.username} olarak ${results.category} testini tamamladım! Sonuçlarımı incele.`,
                url: window.location.href
            };

            if (navigator.share) {
                await navigator.share(shareData);
                Interviewly.showNotification('Sonuçlar paylaşıldı!', 'success');
            } else {
                await navigator.clipboard.writeText(`${shareData.text}\n${shareData.url}`);
                Interviewly.showNotification('Sonuç linki panoya kopyalandı!', 'info');
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                 Interviewly.showNotification('Paylaşım sırasında bir hata oluştu.', 'error');
                 console.error('Share error:', err);
            }
        }
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

        // --- New Router ---
        // Detects the current page by a unique class on a main container
        // and calls the corresponding init function.
        if (document.querySelector('.auth-page')) initAuthPage();
        if (document.querySelector('.create-interview-page')) initCreateInterviewPage();
        if (document.querySelector('.edit-profile-page')) initEditProfilePage();
        if (document.querySelector('.interview-page')) initInterviewPage();
        if (document.querySelector('.my-interviews-page')) initMyInterviewsPage();
        if (document.querySelector('.profile-page')) initProfilePage();
        if (document.querySelector('.test-results-page')) initTestResultsPage();
        if (document.querySelector('.question-page')) initInterviewQuestionPage();

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

            const typeMap = { assistant: 'AI Asistan ile Mülakat', written_test: 'Yazılı Mülakat' };
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
        let startTime = Date.now();
        let messageCount = document.querySelectorAll('#chat-messages .message-wrapper').length;
        let timerInterval;
    
        const timerDisplay = document.getElementById('timer-display');
        const userInput = document.getElementById('user-input');
        const chatContainer = document.querySelector('.chat-container');
        const sendBtn = document.getElementById('send-btn');
        const chatForm = document.getElementById('chat-form');
        const typingIndicator = document.getElementById('typing-indicator');
        const endModal = document.getElementById('endModal');
    
        // Timer functions
        function startTimer() {
            timerInterval = setInterval(updateTimer, 1000);
        }
    
        function updateTimer() {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            if (timerDisplay) timerDisplay.textContent = `${minutes}:${seconds}`;
        }
    
        // UI utility functions
        const autoResize = (textarea) => {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
        };
    
        const updateCharCounter = () => {
            const counter = document.getElementById('char-counter');
            if (!counter) return;
            const count = userInput.value.length;
            counter.textContent = `${count}/1000`;
            if (count > 900) counter.style.color = '#ef4444';
            else if (count > 800) counter.style.color = '#f59e0b';
            else counter.style.color = 'var(--text-muted)';
        };
    
        const scrollToBottom = () => {
            if(chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
        };
    
        const showTypingIndicator = () => {
            if(typingIndicator) typingIndicator.style.display = 'flex';
            scrollToBottom();
        };
    
        const hideTypingIndicator = () => {
            if(typingIndicator) typingIndicator.style.display = 'none';
        };
    
        const addMessageToUI = (content, role) => {
            const chatMessages = document.getElementById('chat-messages');
            if (!chatMessages) return;
    
            const messageWrapper = document.createElement('div');
            messageWrapper.className = `message-wrapper ${role}`;
    
            const avatarIcon = role === 'assistant' ? 'fa-robot' : 'fa-user';
            const senderName = role === 'assistant' ? 'AI Mülakatçı' : 'Siz';
    
            messageWrapper.innerHTML = `
                <div class="message ${role}">
                    <div class="message-avatar"><i class="fas ${avatarIcon}"></i></div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-sender">${senderName}</span>
                            <span class="message-time">${++messageCount}</span>
                        </div>
                        <div class="message-text">${content}</div>
                    </div>
                </div>`;
            chatMessages.appendChild(messageWrapper);
            scrollToBottom();
        };
    
        // Form submission handler
        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const message = userInput.value.trim();
            if (!message) return;
    
            addMessageToUI(message, 'user');
            userInput.value = '';
            autoResize(userInput);
            updateCharCounter();
            showTypingIndicator();
            sendBtn.disabled = true;
    
            // Using Fetch API to send data to the server
            fetch(chatForm.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_input: message })
            })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                hideTypingIndicator();
                if (data.ai_reply) {
                    addMessageToUI(data.ai_reply, 'assistant');
                }
                sendBtn.disabled = false;
                userInput.focus();
            })
            .catch(error => {
                console.error('Fetch Hata:', error);
                hideTypingIndicator();
                addMessageToUI("Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.", 'assistant');
                sendBtn.disabled = false;
            });
        });
    
        // Modal functions
        const showEndModal = () => endModal.classList.add('show');
        const hideEndModal = () => endModal.classList.remove('show');
    
        const confirmEndInterview = () => {
            const resultsUrl = endModal.dataset.resultsUrl;
            if(resultsUrl) window.location.href = resultsUrl;
        };
    
        const resetInterview = () => {
            if (confirm('Mülakatı yeniden başlatmak istediğinizden emin misiniz?')) {
                const resetUrl = endModal.dataset.resetUrl;
                if(resetUrl) window.location.href = resetUrl;
            }
        };
    
        // Event Listeners
        if (userInput) {
            userInput.addEventListener('input', () => {
                autoResize(userInput);
                updateCharCounter();
            });
        }
        
        document.querySelector('.btn-danger[onclick*="endInterview"]').addEventListener('click', showEndModal);
        document.querySelector('.btn-secondary[onclick*="resetInterview"]').addEventListener('click', resetInterview);
        if(endModal) {
            endModal.querySelector('.btn-secondary').addEventListener('click', hideEndModal);
            endModal.querySelector('.btn-danger').addEventListener('click', confirmEndInterview);
            endModal.addEventListener('click', (e) => { if (e.target === endModal) hideEndModal(); });
        }
    
        // Initialization
        startTimer();
        scrollToBottom();
        if(userInput) userInput.focus();
        updateCharCounter();
    }

    /**
     * Initializes logic for the 'Interview Question' page.
     */
    function initInterviewQuestionPage() {
        const questionPage = document.querySelector('.question-page');
        if (!questionPage) {
            return; 
        }

        const questionNum = questionPage.dataset.questionNum;
        if (!questionNum) {
            console.error('Question number not found on page.');
            return;
        }

        let startTime = Date.now();
        let timerInterval;

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

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
        }

        function copyQuestion() {
            const questionText = document.querySelector('.question-text').textContent;
            navigator.clipboard.writeText(questionText.trim()).then(() => {
                Interviewly.showNotification('Soru kopyalandı!', 'info');
            }).catch(err => {
                Interviewly.showNotification('Kopyalama başarısız oldu.', 'error');
                console.error('Kopyalama hatası:', err);
            });
        }

        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    Interviewly.showNotification(`Hata: ${err.message}`, 'error');
                });
            } else {
                document.exitFullscreen();
            }
        }
        
        startTimer();

        const textarea = document.getElementById('user_input');
        if (textarea) {
            textarea.addEventListener('input', function () {
                updateCounters();
                autoResize(this);
            });
            textarea.focus();
            updateCounters();
            autoResize(textarea);
        }

        document.getElementById('fullscreenBtn')?.addEventListener('click', toggleFullscreen);
        document.getElementById('copyBtn')?.addEventListener('click', copyQuestion);
        
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const submitBtn = document.getElementById('submitBtn');
                if (document.activeElement === textarea && submitBtn) {
                    e.preventDefault();
                    submitBtn.click();
                }
            }
        });

        const answerForm = document.getElementById('answerForm');
        if(answerForm) {
            answerForm.addEventListener('submit', function (e) {
                const textarea = document.getElementById('user_input');
                const submitBtn = document.getElementById('submitBtn');
                if (textarea && !textarea.value.trim()) {
                    e.preventDefault();
                    Interviewly.showNotification('Lütfen bir cevap yazın.', 'error');
                    return;
                }
                if(submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gönderiliyor...';
                }
            });
        }
    }

    /**
     * Initializes logic for the 'My Interviews' page.
     */
function initMyInterviewsPage() {
    const searchInput = document.getElementById('searchInput');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const noResultsEl = document.querySelector('.empty-state-container');
    const interviewsGrid = document.querySelector('.interviews-grid');

    let currentFilter = 'all';
    let currentSearch = '';

    const applyFilters = () => {
        const cards = document.querySelectorAll('.interview-card');
        let visibleCount = 0;
        cards.forEach(card => {
            const category = card.dataset.category || 'general';
            const title = card.querySelector('.interview-title').textContent.toLowerCase();
            const searchMatch = !currentSearch || title.includes(currentSearch);
            const filterMatch = currentFilter === 'all' || category === currentFilter;

            if (searchMatch && filterMatch) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        if (noResultsEl) {
            noResultsEl.style.display = visibleCount === 0 ? 'block' : 'none';
        }
        if (interviewsGrid) {
            interviewsGrid.style.display = visibleCount > 0 ? 'grid' : 'none';
        }
    };

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            applyFilters();
        });
    }

    filterBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            currentFilter = this.dataset.filter;
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            applyFilters();
        });
    });

    document.querySelectorAll('.btn-delete-interview').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (confirm('Bu mülakatı kalıcı olarak silmek istediğinizden emin misiniz?')) {
                const card = this.closest('.interview-card');
                const interviewId = this.dataset.interviewId;

                fetch(`/interview/delete/${interviewId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                        // CSRF token gerekiyorsa buraya ekleyin:
                        // 'X-CSRFToken': getCookie('csrf_token')
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            if (card) {
                                card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                                card.style.opacity = '0';
                                card.style.transform = 'scale(0.95)';
                                setTimeout(() => {
                                    card.remove();
                                    if (document.querySelectorAll('.interview-card').length === 0) {
                                        if (interviewsGrid) interviewsGrid.style.display = 'none';
                                        if (noResultsEl) noResultsEl.style.display = 'block';
                                    }
                                    applyFilters();
                                }, 400);

                                Interviewly.showNotification('Mülakat başarıyla silindi.', 'success');
                            }
                        } else {
                            Interviewly.showNotification(data.message || 'Silme işlemi başarısız.', 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Silme hatası:', error);
                        Interviewly.showNotification('Sunucu hatası: Silme işlemi başarısız oldu.', 'error');
                    });
            }
        });
    });

    applyFilters();
}



    /**
     * Initializes logic for the 'Profile' page.
     */
    function initProfilePage() {
        const pageDataEl = document.getElementById('page-data');
        if (!pageDataEl || typeof Chart === 'undefined') return;

        try {
            const weeklyData = JSON.parse(pageDataEl.dataset.weeklyData);
            const ctx = document.getElementById('performanceChart')?.getContext('2d');
            if(!ctx) return;

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
        } catch(e) {
            console.error("Could not parse profile chart data:", e);
        }

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
        const chartDataEl = document.getElementById('page-data-chart');
        if (!chartDataEl || typeof Chart === 'undefined') return;
        
        try {
            const chartData = JSON.parse(chartDataEl.dataset.chartData);
            const ctx = document.getElementById('performanceChart')?.getContext('2d');

            if (ctx && chartData.labels && chartData.data) {
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            data: chartData.data,
                            backgroundColor: ['rgba(34, 197, 94, 0.7)', 'rgba(239, 68, 68, 0.7)', 'rgba(107, 114, 128, 0.7)'],
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
        } catch(e) {
             console.error("Could not parse or render test results chart:", e);
        }

        document.querySelectorAll('.action-btn[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                if (action === 'export') {
                   Interviewly.exportResults();
                } else if (action === 'share') {
                   Interviewly.shareResults();
                }
            });
        });
    }

})();
