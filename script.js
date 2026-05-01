// HackRx Enhanced LLM Frontend JavaScript

class HackRxLLM {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:8000';
        this.init();
    }

    init() {
        this.initializeElements();
        this.attachEventListeners();
        this.checkServerHealth();
        this.loadSavedSettings();
    }

    initializeElements() {
        // Main elements
        this.ocrMethodSelect = document.getElementById('ocrMethod');
        this.documentUrlInput = document.getElementById('documentUrl');
        this.fileInput = document.getElementById('fileInput');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileList = document.getElementById('fileList');
        this.questionsContainer = document.getElementById('questionsContainer');
        this.processBtn = document.getElementById('processBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.resultsSection = document.getElementById('resultsSection');
        this.processingInfo = document.getElementById('processingInfo');
        this.answersContainer = document.getElementById('answersContainer');
        this.toastContainer = document.getElementById('toastContainer');

        // Status elements
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');

        // Tab elements
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');

        this.selectedFiles = [];
        this.currentTab = 'url';
    }

    attachEventListeners() {
        // Tab switching
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // File upload
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Questions management
        document.getElementById('addQuestion').addEventListener('click', () => this.addQuestion());
        this.questionsContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-question') || e.target.parentElement.classList.contains('remove-question')) {
                this.removeQuestion(e.target.closest('.question-item'));
            }
        });

        // Action buttons
        this.processBtn.addEventListener('click', () => this.processDocument());
        this.clearBtn.addEventListener('click', () => this.clearAll());

        // Example cards
        document.querySelectorAll('.example-card').forEach(card => {
            card.addEventListener('click', () => {
                const questions = JSON.parse(card.dataset.questions);
                this.loadExampleQuestions(questions);
            });
        });

        // Save settings on change
        this.ocrMethodSelect.addEventListener('change', () => this.saveSettings());
    }

    // Tab Management
    switchTab(tabName) {
        this.currentTab = tabName;

        // Update tab buttons
        this.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}Tab`);
        });

        // Clear previous inputs when switching tabs
        if (tabName === 'url') {
            this.selectedFiles = [];
            this.updateFileList();
        } else {
            this.documentUrlInput.value = '';
        }
    }

    // File Management
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files);
        this.addFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFiles(files);
        e.target.value = ''; // Reset input
    }

    addFiles(files) {
        const allowedTypes = [
            'application/pdf',
            'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
            'image/bmp', 'image/tiff', 'image/webp'
        ];

        files.forEach(file => {
            if (allowedTypes.includes(file.type)) {
                if (!this.selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                    this.selectedFiles.push(file);
                }
            } else {
                this.showToast(`Unsupported file type: ${file.name}`, 'error');
            }
        });

        this.updateFileList();
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
    }

    updateFileList() {
        if (this.selectedFiles.length === 0) {
            this.fileList.innerHTML = '';
            return;
        }

        const html = this.selectedFiles.map((file, index) => {
            const icon = this.getFileIcon(file.type);
            const size = this.formatFileSize(file.size);

            return `
                <div class="file-item">
                    <div class="file-info">
                        <i class="${icon} file-icon"></i>
                        <div class="file-details">
                            <h4>${file.name}</h4>
                            <p>${size} • ${file.type}</p>
                        </div>
                    </div>
                    <button class="remove-file" onclick="app.removeFile(${index})" title="Remove file">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');

        this.fileList.innerHTML = html;
    }

    getFileIcon(mimeType) {
        if (mimeType === 'application/pdf') return 'fas fa-file-pdf';
        if (mimeType.startsWith('image/')) return 'fas fa-file-image';
        return 'fas fa-file';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Questions Management
    addQuestion() {
        const questionItem = document.createElement('div');
        questionItem.className = 'question-item';
        questionItem.innerHTML = `
            <input type="text" class="question-input" placeholder="Enter your question...">
            <button type="button" class="remove-question" title="Remove Question">
                <i class="fas fa-times"></i>
            </button>
        `;

        this.questionsContainer.appendChild(questionItem);
        questionItem.querySelector('.question-input').focus();
    }

    removeQuestion(questionItem) {
        if (this.questionsContainer.children.length > 1) {
            questionItem.remove();
        } else {
            this.showToast('At least one question is required', 'warning');
        }
    }

    getQuestions() {
        const inputs = this.questionsContainer.querySelectorAll('.question-input');
        return Array.from(inputs)
            .map(input => input.value.trim())
            .filter(question => question.length > 0);
    }

    loadExampleQuestions(questions) {
        // Clear existing questions
        this.questionsContainer.innerHTML = '';

        // Add example questions
        questions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.innerHTML = `
                <input type="text" class="question-input" placeholder="Enter your question..." value="${question}">
                <button type="button" class="remove-question" title="Remove Question">
                    <i class="fas fa-times"></i>
                </button>
            `;
            this.questionsContainer.appendChild(questionItem);
        });

        this.showToast('Example questions loaded!', 'success');
    }

    // Server Communication
    async checkServerHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();

            if (data.status === 'ok') {
                this.statusDot.classList.add('connected');
                this.statusText.textContent = `Connected • OCR: ${data.supported_ocr_methods.join(', ')}`;
            } else {
                this.updateConnectionStatus(false, 'Server error');
            }
        } catch (error) {
            this.updateConnectionStatus(false, 'Server offline');
        }
    }

    updateConnectionStatus(connected, message) {
        if (connected) {
            this.statusDot.classList.add('connected');
        } else {
            this.statusDot.classList.remove('connected');
        }
        this.statusText.textContent = message;
    }

    async processDocument() {
        const questions = this.getQuestions();
        const ocrMethod = this.ocrMethodSelect.value;

        // Validation
        if (questions.length === 0) {
            this.showToast('Please enter at least one question', 'error');
            return;
        }

        if (this.currentTab === 'url') {
            const url = this.documentUrlInput.value.trim();
            if (!url) {
                this.showToast('Please enter a document URL', 'error');
                return;
            }
            await this.processUrl(url, questions, ocrMethod);
        } else {
            if (this.selectedFiles.length === 0) {
                this.showToast('Please select at least one file', 'error');
                return;
            }
            await this.processFiles(this.selectedFiles, questions, ocrMethod);
        }
    }

    async processUrl(url, questions, ocrMethod) {
        this.showLoading(true);

        try {
            const response = await fetch(`${this.apiBaseUrl}/hackrx/run`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    documents: url,
                    questions: questions,
                    ocr_method: ocrMethod
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.displayResults(data, questions);
            this.showToast('Document processed successfully!', 'success');

        } catch (error) {
            console.error('Error:', error);
            this.showToast(`Processing failed: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async processFiles(files, questions, ocrMethod) {
        this.showLoading(true);

        try {
            const formData = new FormData();

            files.forEach(file => {
                formData.append('files', file);
            });

            questions.forEach(question => {
                formData.append('questions', question);
            });

            formData.append('ocr_method', ocrMethod);

            const response = await fetch(`${this.apiBaseUrl}/hackrx/upload-images`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.displayResults(data, questions);
            this.showToast('Files processed successfully!', 'success');

        } catch (error) {
            console.error('Error:', error);
            this.showToast(`Processing failed: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // UI Management
    showLoading(show) {
        this.loadingIndicator.style.display = show ? 'block' : 'none';
        this.processBtn.disabled = show;
        this.resultsSection.style.display = show ? 'none' : 'block';
    }

    displayResults(data, questions) {
        // Display processing info
        if (data.processing_info) {
            const info = data.processing_info;
            this.processingInfo.innerHTML = `
                <div class="info-grid">
                    <div class="info-item">
                        <h4>${info.processing_time_seconds || 0}s</h4>
                        <p>Processing Time</p>
                    </div>
                    <div class="info-item">
                        <h4>${info.total_chunks || 0}</h4>
                        <p>Text Chunks</p>
                    </div>
                    <div class="info-item">
                        <h4>${info.ocr_method_used || 'N/A'}</h4>
                        <p>OCR Method</p>
                    </div>
                    <div class="info-item">
                        <h4>${info.files_processed || 1}</h4>
                        <p>Files Processed</p>
                    </div>
                </div>
            `;
        }

        // Display answers
        const answersHtml = data.answers.map((answer, index) => {
            const question = questions[index] || `Question ${index + 1}`;
            return `
                <div class="answer-card">
                    <div class="answer-header">
                        <i class="fas fa-question-circle"></i>
                        <strong>${question}</strong>
                    </div>
                    <div class="answer-content">${answer}</div>
                </div>
            `;
        }).join('');

        this.answersContainer.innerHTML = answersHtml;
        this.resultsSection.style.display = 'block';
    }

    clearAll() {
        // Clear inputs
        this.documentUrlInput.value = '';
        this.selectedFiles = [];
        this.updateFileList();

        // Clear questions (keep one empty question)
        this.questionsContainer.innerHTML = `
            <div class="question-item">
                <input type="text" class="question-input" placeholder="Enter your question...">
                <button type="button" class="remove-question" title="Remove Question">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        // Hide results
        this.resultsSection.style.display = 'none';

        this.showToast('All fields cleared', 'success');
    }

    // Settings Management
    saveSettings() {
        const settings = {
            ocrMethod: this.ocrMethodSelect.value
        };
        localStorage.setItem('hackrx-settings', JSON.stringify(settings));
    }

    loadSavedSettings() {
        try {
            const settings = JSON.parse(localStorage.getItem('hackrx-settings') || '{}');
            if (settings.ocrMethod) this.ocrMethodSelect.value = settings.ocrMethod;
        } catch (error) {
            console.log('No saved settings found');
        }
    }

    // Toast Notifications
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'exclamation-circle' : 
                    'exclamation-triangle';

        toast.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;

        this.toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.parentElement.removeChild(toast);
            }
        }, 5000);
    }
}

// Initialize the application
const app = new HackRxLLM();

// Export for debugging
window.app = app;