// LLM Trainer Control Panel JavaScript

// Use relative URLs since page is served from middleware
const API_BASE = '';

// State
let statusUpdateInterval = null;
let currentTab = 'overview';
let consecutiveErrors = 0;
let serviceErrorCounts = {}; // Track consecutive errors per service

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Control Panel] Initializing...');

    // Set all status badges to "Loading..." initially
    setLoadingState();

    // Load data with delays to avoid overwhelming the server
    setTimeout(() => loadConfiguration(), 100);
    setTimeout(() => updateAllStatus(), 300);

    setupEventListeners();

    // Start status polling after initial load
    setTimeout(() => {
        console.log('[Control Panel] Starting status polling...');
        statusUpdateInterval = setInterval(updateAllStatus, 3000);
    }, 1000);
});

function setLoadingState() {
    const statusBadges = ['llm-status', 'middleware-status', 'telegram-status', 'sms-status', 'cerebrum-status'];
    statusBadges.forEach(id => {
        const badge = document.getElementById(id);
        if (badge) {
            badge.textContent = 'Loading...';
            badge.className = 'status-badge loading';
        }
    });
}

function setupEventListeners() {
    // LLM source toggle
    const llmSourceSelect = document.getElementById('llm-source');
    llmSourceSelect.addEventListener('change', () => {
        const ollamaConfig = document.getElementById('ollama-config');
        const openrouterConfig = document.getElementById('openrouter-config');

        if (llmSourceSelect.value === 'openrouter') {
            ollamaConfig.classList.add('hidden');
            openrouterConfig.classList.remove('hidden');
        } else {
            ollamaConfig.classList.remove('hidden');
            openrouterConfig.classList.add('hidden');
        }
    });

    // Button event listeners
    document.getElementById('save-llm-config-btn').addEventListener('click', saveLLMConfiguration);
    document.getElementById('save-telegram-config-btn').addEventListener('click', saveTelegramConfiguration);
    document.getElementById('save-sms-config-btn').addEventListener('click', saveSMSConfiguration);
    document.getElementById('save-ai-backend-btn').addEventListener('click', saveAIBackendConfiguration);
    document.getElementById('start-training-btn').addEventListener('click', startTraining);
    document.getElementById('stop-training-btn').addEventListener('click', stopTraining);
    document.getElementById('refresh-users-btn').addEventListener('click', loadUsers);
}

// Tab switching
function switchTab(tabName) {
    // Update active tab button
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');

    // Update active content
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');

    currentTab = tabName;

    // Load data for specific tabs
    if (tabName === 'users') {
        loadUsers();
    }
}

// Configuration Management
async function loadConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);

        if (response.ok) {
            const config = await response.json();

            // LLM Configuration
            document.getElementById('llm-source').value = config.llm_source || 'ollama';
            document.getElementById('ollama-model').value = config.ollama_model || '';
            document.getElementById('openrouter-model').value = config.openrouter_model || '';
            document.getElementById('openrouter-api-key').value = config.openrouter_api_key || '';

            // Training Configuration
            document.getElementById('max-exchanges').value = config.max_exchanges || 100;
            document.getElementById('delay').value = config.conversation_delay || 2.0;
            document.getElementById('topic-interval').value = config.topic_switch_interval || 10;

            // Messaging Configuration
            document.getElementById('telegram-bot-token').value = config.telegram_bot_token || '';
            document.getElementById('twilio-account-sid').value = config.twilio_account_sid || '';
            document.getElementById('twilio-auth-token').value = config.twilio_auth_token || '';
            document.getElementById('twilio-phone-number').value = config.twilio_phone_number || '';

            // AI Backend Configuration
            document.getElementById('default-ai-backend').value = config.default_ai_backend || 'openrouter';

            // Show/hide appropriate config
            if (document.getElementById('llm-source').value === 'openrouter') {
                document.getElementById('ollama-config').classList.add('hidden');
                document.getElementById('openrouter-config').classList.remove('hidden');
            }

            // Update status badges
            updateConfigurationStatus(config);
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

async function saveLLMConfiguration() {
    const btn = document.getElementById('save-llm-config-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        const config = {
            llm_source: document.getElementById('llm-source').value,
            ollama_model: document.getElementById('ollama-model').value,
            openrouter_model: document.getElementById('openrouter-model').value,
            openrouter_api_key: document.getElementById('openrouter-api-key').value,
            conversation_delay: parseFloat(document.getElementById('delay').value),
            topic_switch_interval: parseInt(document.getElementById('topic-interval').value)
        };

        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('LLM configuration saved successfully!', 'success');
            await loadConfiguration();
        } else {
            const error = await response.json();
            showNotification(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save LLM configuration', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function saveTelegramConfiguration() {
    const btn = document.getElementById('save-telegram-config-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        const config = {
            telegram_bot_token: document.getElementById('telegram-bot-token').value
        };

        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('Telegram configuration saved! Restart telegram_server.py to apply.', 'success');
            await loadConfiguration();
        } else {
            const error = await response.json();
            showNotification(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save Telegram configuration', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function saveSMSConfiguration() {
    const btn = document.getElementById('save-sms-config-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        const config = {
            twilio_account_sid: document.getElementById('twilio-account-sid').value,
            twilio_auth_token: document.getElementById('twilio-auth-token').value,
            twilio_phone_number: document.getElementById('twilio-phone-number').value
        };

        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('SMS configuration saved! Restart sms_server.py to apply.', 'success');
            await loadConfiguration();
        } else {
            const error = await response.json();
            showNotification(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save SMS configuration', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function saveAIBackendConfiguration() {
    const btn = document.getElementById('save-ai-backend-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Saving...';

    try {
        const config = {
            default_ai_backend: document.getElementById('default-ai-backend').value
        };

        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showNotification('AI backend configuration saved!', 'success');
            await loadConfiguration();
        } else {
            const error = await response.json();
            showNotification(`Failed to save: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save AI backend configuration', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function updateConfigurationStatus(config) {
    // Telegram status
    const telegramBadge = document.getElementById('telegram-config-status');
    if (config.telegram_bot_token && config.telegram_bot_token.length > 10) {
        telegramBadge.textContent = 'Configured';
        telegramBadge.className = 'status-badge running';
    } else {
        telegramBadge.textContent = 'Not Configured';
        telegramBadge.className = 'status-badge stopped';
    }

    // SMS status
    const smsBadge = document.getElementById('sms-config-status');
    if (config.twilio_account_sid && config.twilio_auth_token && config.twilio_phone_number) {
        smsBadge.textContent = 'Configured';
        smsBadge.className = 'status-badge running';
    } else {
        smsBadge.textContent = 'Not Configured';
        smsBadge.className = 'status-badge stopped';
    }
}

// Training Control
async function startTraining() {
    const btn = document.getElementById('start-training-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Starting...';

    try {
        const response = await fetch(`${API_BASE}/api/training/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_exchanges: parseInt(document.getElementById('max-exchanges').value),
                delay: parseFloat(document.getElementById('delay').value),
                topic_switch_interval: parseInt(document.getElementById('topic-interval').value)
            })
        });

        if (response.ok) {
            showNotification('Training started!', 'success');
            btn.disabled = true;
            document.getElementById('stop-training-btn').disabled = false;
            await updateAllStatus();
        } else {
            const error = await response.json();
            showNotification(`Failed to start: ${error.detail}`, 'error');
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error starting training:', error);
        showNotification('Failed to start training', 'error');
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function stopTraining() {
    const btn = document.getElementById('stop-training-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Stopping...';

    try {
        const response = await fetch(`${API_BASE}/api/training/stop`, {
            method: 'POST'
        });

        if (response.ok) {
            showNotification('Training stopped', 'success');
            btn.disabled = true;
            document.getElementById('start-training-btn').disabled = false;
            await updateAllStatus();
        } else {
            const error = await response.json();
            showNotification(`Failed to stop: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error stopping training:', error);
        showNotification('Failed to stop training', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Status Updates
async function updateAllStatus() {
    await Promise.all([
        updateServiceStatus(),
        updateTrainingStatus(),
        updateUserStats()
    ]);
}

async function updateServiceStatus() {
    console.log('[updateServiceStatus] Starting status update...');

    // Use middleware proxy endpoints to avoid CORS issues
    // All requests go through the middleware which has proper CORS configured

    const services = [
        { id: 'llm', name: 'LLM Server', proxyEndpoint: '/api/llm/status', defaultPort: 8030 },
        { id: 'middleware', name: 'Middleware', proxyEndpoint: '/api/status', defaultPort: 8032 },
        { id: 'telegram', name: 'Telegram Bot', proxyEndpoint: '/telegram/status', defaultPort: 8041, optional: true },
        { id: 'sms', name: 'SMS Server', proxyEndpoint: '/sms/status', defaultPort: 8040, optional: true },
        { id: 'cerebrum', name: 'CEREBRUM', proxyEndpoint: '/api/cerebrum/status', defaultPort: 8000, optional: true }
    ];

    // Get actual port configuration
    let config = null;
    try {
        console.log('[updateServiceStatus] Fetching config from:', `${API_BASE}/api/config`);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.warn('[updateServiceStatus] Config fetch timeout (2s)');
            controller.abort();
        }, 2000);

        const configResponse = await fetch(`${API_BASE}/api/config`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        console.log('[updateServiceStatus] Config response status:', configResponse.status);
        if (configResponse.ok) {
            config = await configResponse.json();
            console.log('[Status] Config loaded:', config);
        } else {
            console.warn('[updateServiceStatus] Config response not OK:', configResponse.status, configResponse.statusText);
        }
    } catch (error) {
        console.error('[Status] Config fetch failed:', error.name, error.message);
    }

    for (const service of services) {
        const badge = document.getElementById(`${service.id}-status`);
        const portDisplay = document.getElementById(`${service.id}-port`);

        // Determine actual port from config
        let port = service.defaultPort;
        if (config) {
            if (service.id === 'llm') port = config.llm_server_port || port;
            else if (service.id === 'middleware') port = config.middleware_port || port;
            else if (service.id === 'telegram') port = config.telegram_server_port || port;
            else if (service.id === 'sms') port = config.sms_server_port || port;
            else if (service.id === 'cerebrum') port = 8000; // CEREBRUM is always on 8000
        }

        console.log(`[updateServiceStatus] Checking ${service.name} at ${API_BASE}${service.proxyEndpoint}`);

        try {
            // Use middleware proxy endpoints to avoid CORS
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.warn(`[updateServiceStatus] ${service.name} timeout (3s)`);
                controller.abort();
            }, 3000);

            const response = await fetch(`${API_BASE}${service.proxyEndpoint}`, {
                method: 'GET',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            console.log(`[updateServiceStatus] ${service.name} response:`, response.status, response.statusText);

            if (response.ok) {
                badge.textContent = 'Running';
                badge.className = 'status-badge running';
                console.log(`[Status] ${service.name}: Running ✓`);
                serviceErrorCounts[service.id] = 0; // Reset error count on success
            } else if (response.status === 502 || response.status === 503 || response.status === 504) {
                // Service unreachable through proxy - but could be transient
                // Only mark as stopped after 2 consecutive failures
                serviceErrorCounts[service.id] = (serviceErrorCounts[service.id] || 0) + 1;

                if (serviceErrorCounts[service.id] >= 2) {
                    badge.textContent = 'Stopped';
                    badge.className = 'status-badge stopped';
                    console.log(`[Status] ${service.name}: Stopped after ${serviceErrorCounts[service.id]} failures (${response.status})`);
                } else {
                    // First failure - keep previous status but log warning
                    console.warn(`[Status] ${service.name}: Transient failure (${response.status}), attempt ${serviceErrorCounts[service.id]}/2`);
                }
            } else {
                badge.textContent = 'Error';
                badge.className = 'status-badge warning';
                console.warn(`[Status] ${service.name}: Error ${response.status}`);
                serviceErrorCounts[service.id] = (serviceErrorCounts[service.id] || 0) + 1;
            }

            if (portDisplay) {
                portDisplay.textContent = port;
            }

            consecutiveErrors = 0; // Reset error counter on success
        } catch (error) {
            // Network error or timeout - could be transient
            // Only mark as stopped after 2 consecutive failures
            serviceErrorCounts[service.id] = (serviceErrorCounts[service.id] || 0) + 1;

            console.error(`[updateServiceStatus] ${service.name} fetch error (attempt ${serviceErrorCounts[service.id]}/2):`, {
                name: error.name,
                message: error.message
            });

            if (serviceErrorCounts[service.id] >= 2) {
                badge.textContent = service.optional ? 'Not Configured' : 'Stopped';
                badge.className = 'status-badge stopped';
            } else {
                // First failure - keep previous status
                console.warn(`[Status] ${service.name}: Transient error, keeping previous status`);
            }

            if (portDisplay) {
                portDisplay.textContent = port;
            }
        }
    }
}

async function updateTrainingStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/training/status`);

        if (response.ok) {
            const status = await response.json();

            // Update all training status badges
            const badges = [
                'training-status-badge',
                'training-status-badge-2'
            ];

            badges.forEach(badgeId => {
                const badge = document.getElementById(badgeId);
                if (status.running) {
                    badge.textContent = 'Running';
                    badge.className = 'status-badge running';
                } else {
                    badge.textContent = 'Stopped';
                    badge.className = 'status-badge stopped';
                }
            });

            // Update button states
            document.getElementById('start-training-btn').disabled = status.running;
            document.getElementById('stop-training-btn').disabled = !status.running;

            if (!status.running) {
                document.getElementById('start-training-btn').textContent = '▶ Start Training';
                document.getElementById('stop-training-btn').textContent = '⏹ Stop Training';
            }

            // Update metrics
            const exchangesElements = [
                'exchanges-completed',
                'exchanges-completed-2'
            ];
            exchangesElements.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = status.exchanges_completed || 0;
            });

            const topicElements = [
                'current-topic',
                'current-topic-2'
            ];
            topicElements.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = status.current_topic || '-';
            });

            // Update source and model
            const config = await fetch(`${API_BASE}/api/config`).then(r => r.json());
            const sourceEl = document.getElementById('current-source');
            const modelEl = document.getElementById('current-model');

            if (sourceEl) {
                sourceEl.textContent = config.llm_source === 'openrouter' ? 'OpenRouter' : 'Ollama';
            }
            if (modelEl) {
                modelEl.textContent = config.llm_source === 'openrouter'
                    ? config.openrouter_model
                    : config.ollama_model;
            }
        }
    } catch (error) {
        console.error('Error updating training status:', error);
    }
}

async function updateUserStats() {
    try {
        // Try to get user counts from messaging servers
        let telegramCount = 0;
        let smsCount = 0;

        // Try Telegram
        try {
            const telegramResponse = await fetch('http://localhost:8041/telegram/status', {
                signal: AbortSignal.timeout(1000)
            });
            if (telegramResponse.ok) {
                const data = await telegramResponse.json();
                telegramCount = data.users?.length || 0;
            }
        } catch (e) {
            // Telegram not running
        }

        // Try SMS
        try {
            const smsResponse = await fetch('http://localhost:8040/sms/status', {
                signal: AbortSignal.timeout(1000)
            });
            if (smsResponse.ok) {
                const data = await smsResponse.json();
                smsCount = data.users?.length || 0;
            }
        } catch (e) {
            // SMS not running
        }

        // Update UI
        document.getElementById('telegram-user-count').textContent = telegramCount;
        document.getElementById('sms-user-count').textContent = smsCount;
        document.getElementById('total-user-count').textContent = telegramCount + smsCount;
    } catch (error) {
        console.error('Error updating user stats:', error);
    }
}

// User Management
async function loadUsers() {
    const tbody = document.getElementById('users-table-body');
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Loading users...</td></tr>';

    try {
        let allUsers = [];

        // Fetch Telegram users
        try {
            const telegramResponse = await fetch('http://localhost:8041/telegram/status', {
                signal: AbortSignal.timeout(2000)
            });
            if (telegramResponse.ok) {
                const data = await telegramResponse.json();
                if (data.users) {
                    allUsers = allUsers.concat(data.users.map(u => ({
                        ...u,
                        platform: 'telegram'
                    })));
                }
            }
        } catch (e) {
            console.log('Telegram server not accessible');
        }

        // Fetch SMS users
        try {
            const smsResponse = await fetch('http://localhost:8040/sms/status', {
                signal: AbortSignal.timeout(2000)
            });
            if (smsResponse.ok) {
                const data = await smsResponse.json();
                if (data.users) {
                    allUsers = allUsers.concat(data.users.map(u => ({
                        ...u,
                        platform: 'sms'
                    })));
                }
            }
        } catch (e) {
            console.log('SMS server not accessible');
        }

        // Display users
        if (allUsers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No users registered yet</td></tr>';
        } else {
            tbody.innerHTML = allUsers.map(user => `
                <tr>
                    <td>${user.platform.toUpperCase()}</td>
                    <td>${user.chat_id || user.user_id || user.phone_number || '-'}</td>
                    <td>${user.name || 'Not set'}</td>
                    <td><span class="status-badge ${user.ai_backend === 'cerebrum' ? 'warning' : 'running'}">${user.ai_backend || 'openrouter'}</span></td>
                    <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Error loading users</td></tr>';
    }
}

// Notifications
function showNotification(message, type = 'info') {
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
        max-width: 400px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// CSS animations
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
