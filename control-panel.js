// LLM Trainer Control Panel JavaScript

const MIDDLEWARE_PORT = 8032;
const API_BASE = `http://127.0.0.1:${MIDDLEWARE_PORT}`;

// DOM Elements
const llmSourceSelect = document.getElementById('llm-source');
const ollamaConfig = document.getElementById('ollama-config');
const openrouterConfig = document.getElementById('openrouter-config');
const ollamaModelInput = document.getElementById('ollama-model');
const openrouterModelInput = document.getElementById('openrouter-model');
const openrouterApiKeyInput = document.getElementById('openrouter-api-key');
const saveConfigBtn = document.getElementById('save-config-btn');

const maxExchangesInput = document.getElementById('max-exchanges');
const delayInput = document.getElementById('delay');
const topicIntervalInput = document.getElementById('topic-interval');
const startTrainingBtn = document.getElementById('start-training-btn');
const stopTrainingBtn = document.getElementById('stop-training-btn');

const trainingStatusBadge = document.getElementById('training-status-badge');
const currentSourceSpan = document.getElementById('current-source');
const currentModelSpan = document.getElementById('current-model');
const exchangesCompletedSpan = document.getElementById('exchanges-completed');
const currentTopicSpan = document.getElementById('current-topic');

// State
let statusUpdateInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConfiguration();
    updateStatus();
    setupEventListeners();

    // Start status polling
    statusUpdateInterval = setInterval(updateStatus, 3000);
});

function setupEventListeners() {
    llmSourceSelect.addEventListener('change', () => {
        if (llmSourceSelect.value === 'openrouter') {
            ollamaConfig.classList.add('hidden');
            openrouterConfig.classList.remove('hidden');
        } else {
            ollamaConfig.classList.remove('hidden');
            openrouterConfig.classList.add('hidden');
        }
    });

    saveConfigBtn.addEventListener('click', saveConfiguration);
    startTrainingBtn.addEventListener('click', startTraining);
    stopTrainingBtn.addEventListener('click', stopTraining);
}

async function loadConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);

        if (response.ok) {
            const config = await response.json();

            // Populate fields
            llmSourceSelect.value = config.llm_source || 'ollama';
            ollamaModelInput.value = config.ollama_model || '';
            openrouterModelInput.value = config.openrouter_model || '';
            openrouterApiKeyInput.value = config.openrouter_api_key || '';

            maxExchangesInput.value = config.max_exchanges || 100;
            delayInput.value = config.conversation_delay || 2.0;
            topicIntervalInput.value = config.topic_switch_interval || 10;

            // Show/hide appropriate config
            if (llmSourceSelect.value === 'openrouter') {
                ollamaConfig.classList.add('hidden');
                openrouterConfig.classList.remove('hidden');
            }

            // Update status display
            currentSourceSpan.textContent = config.llm_source === 'openrouter' ? 'OpenRouter' : 'Ollama';
            currentModelSpan.textContent = config.llm_source === 'openrouter'
                ? config.openrouter_model
                : config.ollama_model;
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

async function saveConfiguration() {
    const originalText = saveConfigBtn.textContent;
    saveConfigBtn.disabled = true;
    saveConfigBtn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        const config = {
            llm_source: llmSourceSelect.value,
            ollama_model: ollamaModelInput.value,
            openrouter_model: openrouterModelInput.value,
            openrouter_api_key: openrouterApiKeyInput.value,
            conversation_delay: parseFloat(delayInput.value),
            topic_switch_interval: parseInt(topicIntervalInput.value)
        };

        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('Configuration saved successfully!', 'success');
            await loadConfiguration();
        } else {
            const error = await response.json();
            showNotification(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save configuration', 'error');
    } finally {
        saveConfigBtn.disabled = false;
        saveConfigBtn.textContent = originalText;
    }
}

async function startTraining() {
    const originalText = startTrainingBtn.textContent;
    startTrainingBtn.disabled = true;
    startTrainingBtn.innerHTML = '<span class="spinner"></span> Starting...';

    try {
        const response = await fetch(`${API_BASE}/api/training/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_exchanges: parseInt(maxExchangesInput.value),
                delay: parseFloat(delayInput.value),
                topic_switch_interval: parseInt(topicIntervalInput.value)
            })
        });

        if (response.ok) {
            showNotification('Training started!', 'success');
            startTrainingBtn.disabled = true;
            stopTrainingBtn.disabled = false;
            await updateStatus();
        } else {
            const error = await response.json();
            showNotification(`Failed to start: ${error.detail}`, 'error');
            startTrainingBtn.disabled = false;
            startTrainingBtn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error starting training:', error);
        showNotification('Failed to start training', 'error');
        startTrainingBtn.disabled = false;
        startTrainingBtn.textContent = originalText;
    }
}

async function stopTraining() {
    const originalText = stopTrainingBtn.textContent;
    stopTrainingBtn.disabled = true;
    stopTrainingBtn.innerHTML = '<span class="spinner"></span> Stopping...';

    try {
        const response = await fetch(`${API_BASE}/api/training/stop`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('Training stopped', 'success');
            stopTrainingBtn.disabled = true;
            startTrainingBtn.disabled = false;
            await updateStatus();
        } else {
            const error = await response.json();
            showNotification(`Failed to stop: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error stopping training:', error);
        showNotification('Failed to stop training', 'error');
    } finally {
        stopTrainingBtn.disabled = false;
        stopTrainingBtn.textContent = originalText;
    }
}

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/training/status`);

        if (response.ok) {
            const status = await response.json();

            // Update status badge
            if (status.running) {
                trainingStatusBadge.textContent = 'Running';
                trainingStatusBadge.className = 'status-badge running';
                startTrainingBtn.disabled = true;
                stopTrainingBtn.disabled = false;
                startTrainingBtn.textContent = '▶ Start Training';
            } else {
                trainingStatusBadge.textContent = 'Stopped';
                trainingStatusBadge.className = 'status-badge stopped';
                startTrainingBtn.disabled = false;
                stopTrainingBtn.disabled = true;
                stopTrainingBtn.textContent = '⏹ Stop Training';
            }

            // Update metrics
            exchangesCompletedSpan.textContent = status.exchanges_completed || 0;
            currentTopicSpan.textContent = status.current_topic || '-';
        }
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

function showNotification(message, type = 'info') {
    // Simple notification - you could make this fancier
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--primary)'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
