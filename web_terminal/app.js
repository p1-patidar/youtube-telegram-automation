// Global app state and functions
const app = {
    ws: null,
    selectedAccount: null,
    accounts: [],

    init() {
        this.connectWebSocket();
        this.initNavigation();
        this.loadAccounts();
        this.initAutomationForm();
        this.setTodayDate();
        this.setupPromotionToggles();
    },

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };

        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    },

    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        if (connected) {
            statusText.textContent = 'Connected';
        } else {
            statusText.textContent = 'Disconnected';
            statusDot.style.background = '#ef4444';
        }
    },

    handleWebSocketMessage(data) {
        if (data.type === 'progress') {
            this.updateProgress(data.current, data.total, data.message);
        } else if (data.type === 'log') {
            this.addProgressLog(data.message, data.className);
        }
    },

    initNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const view = item.getAttribute('data-view');
                this.showView(view);

                // Update active state
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                item.classList.add('active');
            });
        });
    },

    showView(viewName) {
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');

        // Load data for specific views
        if (viewName === 'accounts') {
            this.loadAccounts();
        } else if (viewName === 'promotion') {
            this.loadPromotionConfig();
        } else if (viewName === 'stats') {
            this.loadStats();
        }
    },

    async loadAccounts() {
        try {
            const response = await fetch('/api/accounts');
            const data = await response.json();
            console.log('Accounts loaded:', data);

            if (data.success) {
                this.accounts = data.accounts || [];
                this.renderAccounts();
                this.updateStats();
                this.loadGlobalAccountSelector();
                this.loadAccountsForAutomation();
                this.loadAccountsForStats();

                // Auto-select saved account from previous session
                const savedAccount = this.accounts.find(acc => acc.selected);
                if (savedAccount && !this.selectedAccount) {
                    this.selectedAccount = savedAccount.name;
                    console.log('Auto-selected saved account:', savedAccount.name);
                    // Also authenticate it on the backend
                    this.selectAccount(savedAccount.name);
                }
            } else {
                console.error('Failed to load accounts:', data.error);
                this.showToast('Failed to load accounts: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Failed to load accounts:', error);
            this.showToast('Failed to load accounts', 'error');

        }
    },

    renderAccounts() {
        const grid = document.getElementById('accountsGrid');

        if (this.accounts.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px;">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 16px; opacity: 0.3;">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                    <h3 style="margin-bottom: 8px;">No accounts found</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">Add your first YouTube account to get started</p>
                    <button class="btn btn-primary" onclick="app.openAddAccountModal()">Add Account</button>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.accounts.map(account => `
            <div class="account-card ${account.selected ? 'selected' : ''}" onclick="app.selectAccount('${account.name}')">
                <div class="account-header">
                    <div class="account-avatar">${account.name.charAt(0).toUpperCase()}</div>
                    <div class="account-info">
                        <h4>${account.channel_title || account.name}</h4>
                        <p>${account.channel_id || 'No channel info'}</p>
                    </div>
                </div>
                ${account.selected ? '<div style="color: var(--success); font-size: 13px; font-weight: 600;">✓ Selected</div>' : ''}
            </div>
        `).join('');
    },

    async selectAccount(accountName) {
        try {
            const response = await fetch('/api/select-account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account: accountName })
            });

            const data = await response.json();
            if (data.success) {
                this.selectedAccount = accountName;
                this.showToast(`Selected account: ${accountName}`, 'success');
                this.loadAccounts();
            } else {
                this.showToast(data.error || 'Failed to select account', 'error');
            }
        } catch (error) {
            this.showToast('Failed to select account', 'error');
        }
    },

    loadGlobalAccountSelector() {
        const select = document.getElementById('globalAccountSelect');
        if (!select) return;

        const currentValue = select.value || this.selectedAccount || '';
        select.innerHTML = '<option value="">Select account...</option>';

        this.accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.channel_id || account.name;
            option.textContent = account.channel_title || account.name;
            if (account.selected || account.name === this.selectedAccount) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        // Restore selection if it existed
        if (currentValue) {
            select.value = currentValue;
        }
    },

    async selectGlobalAccount(channelId) {
        if (!channelId) return;

        // Find the account by channel_id
        const account = this.accounts.find(a => a.channel_id === channelId || a.name === channelId);
        if (!account) return;

        try {
            const response = await fetch('/api/select-account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account: account.name })
            });

            const data = await response.json();
            if (data.success) {
                this.selectedAccount = account.name;
                this.selectedChannelId = channelId;

                // Sync all other dropdowns
                this.syncAllAccountDropdowns(channelId);

                this.showToast(`Active account: ${account.channel_title || account.name}`, 'success');
                this.loadAccounts();
            } else {
                this.showToast(data.error || 'Failed to select account', 'error');
            }
        } catch (error) {
            this.showToast('Failed to select account', 'error');
        }
    },

    syncAllAccountDropdowns(channelId) {
        // Sync automation dropdown
        const automationSelect = document.getElementById('automationAccountSelect');
        if (automationSelect) automationSelect.value = channelId;

        // Sync promotion dropdown
        const promotionSelect = document.getElementById('promotionAccountSelect');
        if (promotionSelect) promotionSelect.value = channelId;

        // Sync stats dropdown
        const statsSelect = document.getElementById('statsAccountSelect');
        if (statsSelect) statsSelect.value = channelId;
    },


    openAddAccountModal() {
        document.getElementById('addAccountModal').classList.add('active');
        document.getElementById('newAccountName').value = '';
        document.getElementById('newAccountName').focus();
    },

    closeAddAccountModal() {
        document.getElementById('addAccountModal').classList.remove('active');
    },

    async addAccount() {
        const accountName = document.getElementById('newAccountName').value.trim();

        if (!accountName) {
            this.showToast('Please enter an account name', 'warning');
            return;
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(accountName)) {
            this.showToast('Invalid account name. Use only letters, numbers, hyphens, and underscores', 'error');
            return;
        }

        this.closeAddAccountModal();
        this.showToast('Opening browser for OAuth authentication...', 'info');

        try {
            const response = await fetch('/api/add-account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account_name: accountName })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast(`Account ${accountName} added successfully!`, 'success');
                this.loadAccounts();
            } else {
                this.showToast(data.error || 'Failed to add account', 'error');
            }
        } catch (error) {
            this.showToast('Failed to add account', 'error');
        }
    },

    async setTodayDate() {
        const globalSelect = document.getElementById('globalAccountSelect');
        const channelId = globalSelect ? globalSelect.value : '';

        try {
            // Fetch last video date from backend
            let url = '/api/last-video-date';
            if (channelId) {
                url += `?channel_id=${channelId}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.success && data.next_date) {
                document.getElementById('startDate').value = data.next_date;
                if (data.last_video) {
                    console.log(`Last video was on ${data.last_video}, scheduling from ${data.next_date}`);
                }
                return;
            }
        } catch (error) {
            console.error('Error fetching last video date:', error);
        }

        // Fallback to tomorrow
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const dateStr = tomorrow.toISOString().split('T')[0];
        document.getElementById('startDate').value = dateStr;
    },

    initAutomationForm() {
        const vpd = document.getElementById('videosPerDay');
        vpd.addEventListener('change', () => {
            this.updateTimeSlots(parseInt(vpd.value));
        });

        // Set initial time slot to 7 PM IST
        this.updateTimeSlots(1);
    },

    updateTimeSlots(count) {
        const container = document.getElementById('timeSlotsContainer');
        const slots = [];

        // Default to 7 PM (19:00) IST for first slot, then add 1 hour for each subsequent
        for (let i = 0; i < count; i++) {
            const hour = 19 + i; // Start at 7 PM (19:00)
            const displayHour = hour > 23 ? hour - 24 : hour; // Wrap to next day if needed
            slots.push(`<input type="time" class="input-field" value="${displayHour.toString().padStart(2, '0')}:00" style="margin-bottom: 8px;">`);
        }

        container.innerHTML = slots.join('');
    },

    async loadAccountsForAutomation() {
        const select = document.getElementById('automationAccountSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select an account...</option>';

        if (this.accounts.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No accounts available - add one first';
            option.disabled = true;
            select.appendChild(option);
            return;
        }

        this.accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.channel_id || account.name;
            option.textContent = account.channel_title || account.name;
            if (account.selected || (this.selectedChannelId && (account.channel_id === this.selectedChannelId))) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    },

    async loadAccountsForStats() {
        const select = document.getElementById('statsAccountSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select an account...</option>';

        if (this.accounts.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No accounts available';
            option.disabled = true;
            select.appendChild(option);
            return;
        }

        this.accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.channel_id;
            option.textContent = account.channel_title || account.name;
            select.appendChild(option);
        });
    },

    async runAutomation() {
        const globalSelect = document.getElementById('globalAccountSelect');
        const channelId = globalSelect ? globalSelect.value : '';
        const startDate = document.getElementById('startDate').value;
        const videosPerDay = parseInt(document.getElementById('videosPerDay').value);
        const timeInputs = document.querySelectorAll('#timeSlotsContainer input[type="time"]');
        const timeSlots = Array.from(timeInputs).map(input => input.value);

        if (!channelId) {
            this.showToast('Please select an account from the sidebar', 'warning');
            return;
        }

        if (!startDate) {
            this.showToast('Please select a start date', 'warning');
            return;
        }

        // Show progress container
        const progressContainer = document.getElementById('automationProgress');
        progressContainer.style.display = 'block';
        document.getElementById('progressLog').innerHTML = '';
        document.getElementById('progressBar').style.width = '0%';

        try {
            const response = await fetch('/api/run-automation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account: this.selectedAccount,
                    channel_id: channelId,
                    start_date: startDate,
                    videos_per_day: videosPerDay,
                    time_slots: timeSlots
                })
            });

            const data = await response.json();
            if (!data.success) {
                this.showToast(data.error || 'Automation failed', 'error');
            }
        } catch (error) {
            this.showToast('Failed to start automation', 'error');
        }
    },

    updateProgress(current, total, message) {
        const percentage = Math.round((current / total) * 100);
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = `${percentage}%`;
        progressBar.textContent = `${percentage}%`;

        if (message) {
            this.addProgressLog(message, 'info');
        }
    },

    addProgressLog(message, className = '') {
        const log = document.getElementById('progressLog');
        const div = document.createElement('div');
        div.textContent = message;
        if (className) div.className = className;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
    },

    async loadStats() {
        const globalSelect = document.getElementById('globalAccountSelect');
        const channelId = globalSelect ? globalSelect.value : '';
        if (!channelId) {
            document.getElementById('statsContainer').innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">Select an account from the sidebar to view statistics</p>';
            return;
        }

        try {
            const response = await fetch(`/api/stats?channel_id=${channelId}`);
            const data = await response.json();

            const container = document.getElementById('statsContainer');
            if (data.stats) {
                container.innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-info">
                                <p class="stat-label">Total Videos Processed</p>
                                <h3 class="stat-value">${data.stats.total_videos || 0}</h3>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-info">
                                <p class="stat-label">Successfully Scheduled</p>
                                <h3 class="stat-value">${data.stats.scheduled || 0}</h3>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-info">
                                <p class="stat-label">Duplicates Detected</p>
                                <h3 class="stat-value">${data.stats.duplicates || 0}</h3>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            this.showToast('Failed to load stats', 'error');
        }
    },

    updateStats() {
        document.getElementById('accountCount').textContent = this.accounts.length;
        document.getElementById('videosScheduled').textContent = '0'; // Will be updated from API
        document.getElementById('lastRun').textContent = 'Never'; // Will be updated from API
    },

    async loadAccountsForPromotion() {
        const select = document.getElementById('promotionAccountSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Select an account...</option>';

        if (this.accounts.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No accounts available - add one first';
            option.disabled = true;
            select.appendChild(option);
            return;
        }

        this.accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.channel_id;
            option.textContent = account.channel_title || account.name;
            select.appendChild(option);
        });

        // Load promotion config from .env
        this.loadPromotionConfig();
    },

    async loadPromotionConfig() {
        try {
            const response = await fetch('/api/promotion-config');
            const data = await response.json();

            if (data.success && data.config) {
                const config = data.config;

                // Populate Telegram fields
                if (config.telegram.bot_token) {
                    document.getElementById('telegramBotToken').value = config.telegram.bot_token;
                    document.getElementById('telegramChannelId').value = config.telegram.channel_id;
                    document.getElementById('enableTelegram').checked = true;
                    document.getElementById('telegramConfig').style.display = 'block';
                }

                // Update Twitter connection status (from .env credentials)
                if (config.twitter.connected) {
                    this.updateTwitterStatus(true, '@X Account');
                    document.getElementById('enableTwitter').checked = true;
                    document.getElementById('twitterConfig').style.display = 'block';
                }

                // Update Instagram connection status (from .env credentials)
                if (config.instagram.connected) {
                    this.updateInstagramStatus(true, '@' + config.instagram.username);
                    document.getElementById('enableInstagram').checked = true;
                    document.getElementById('instagramConfig').style.display = 'block';
                }
            }
        } catch (error) {
            console.error('Failed to load promotion config:', error);
        }

        // Load recent videos for the selected account
        this.loadRecentVideos();
    },

    async loadRecentVideos() {
        const globalSelect = document.getElementById('globalAccountSelect');
        const channelId = globalSelect ? globalSelect.value : '';
        const container = document.getElementById('videoSelectionList');

        if (!channelId) {
            container.innerHTML = '<p class="loading-text">Select an account to load videos...</p>';
            return;
        }

        container.innerHTML = '<p class="loading-text">Loading videos...</p>';

        try {
            const response = await fetch(`/api/recent-videos?channel_id=${channelId}&limit=20`);
            const data = await response.json();

            if (data.success && data.videos && data.videos.length > 0) {
                container.innerHTML = data.videos.map(video => `
                    <label class="video-item" data-video-id="${video.id}">
                        <input type="checkbox" class="video-checkbox" data-id="${video.id}" onchange="app.onVideoCheckChange('${video.id}', this.checked)">
                        <img src="${video.thumbnail}" alt="" class="video-thumb">
                        <div class="video-info">
                            <div class="video-title" title="${video.title}">${video.title}</div>
                            <div class="video-date">${video.published}</div>
                        </div>
                    </label>
                `).join('');
            } else {
                container.innerHTML = '<p class="loading-text">No videos found</p>';
            }
        } catch (error) {
            console.error('Error loading videos:', error);
            container.innerHTML = '<p class="loading-text">Failed to load videos</p>';
        }
    },

    onVideoCheckChange(videoId, isChecked) {
        const item = document.querySelector(`.video-item[data-video-id="${videoId}"]`);
        if (item) {
            item.classList.toggle('selected', isChecked);
        }
        // Update select all checkbox
        this.updateSelectAllState();
    },

    toggleSelectAllVideos() {
        const selectAll = document.getElementById('selectAllVideos');
        const checkboxes = document.querySelectorAll('.video-checkbox');
        const items = document.querySelectorAll('.video-item');

        checkboxes.forEach(cb => cb.checked = selectAll.checked);
        items.forEach(item => item.classList.toggle('selected', selectAll.checked));
    },

    updateSelectAllState() {
        const checkboxes = document.querySelectorAll('.video-checkbox');
        const checkedCount = document.querySelectorAll('.video-checkbox:checked').length;
        const selectAll = document.getElementById('selectAllVideos');

        if (selectAll) {
            selectAll.checked = checkboxes.length > 0 && checkedCount === checkboxes.length;
            selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
        }
    },

    getSelectedVideoIds() {
        return Array.from(document.querySelectorAll('.video-checkbox:checked')).map(cb => cb.dataset.id);
    },

    setupPromotionToggles() {
        const platforms = ['Telegram', 'Twitter', 'Instagram'];
        platforms.forEach(platform => {
            const checkbox = document.getElementById(`enable${platform}`);
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    const config = document.getElementById(`${platform.toLowerCase()}Config`);
                    if (config) {
                        config.style.display = e.target.checked ? 'block' : 'none';
                    }
                });
            }
        });

        // Listen for OAuth callback messages
        window.addEventListener('message', (event) => {
            if (event.data.type === 'twitter_connected') {
                this.updateTwitterStatus(true, event.data.username);
                this.showToast(`Twitter connected as ${event.data.username}`, 'success');
            }
        });
    },

    async connectTwitter() {
        try {
            const response = await fetch('/api/twitter/auth');
            const data = await response.json();

            if (data.success && data.auth_url) {
                // Open OAuth window
                const width = 600;
                const height = 700;
                const left = (screen.width - width) / 2;
                const top = (screen.height - height) / 2;

                window.open(
                    data.auth_url,
                    'Twitter Authorization',
                    `width=${width},height=${height},left=${left},top=${top}`
                );
            } else {
                this.showToast(data.error || 'Failed to start Twitter auth', 'error');
            }
        } catch (error) {
            this.showToast('Failed to connect Twitter', 'error');
        }
    },

    async disconnectTwitter() {
        try {
            const response = await fetch('/api/twitter/disconnect', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.updateTwitterStatus(false);
                this.showToast('Twitter disconnected', 'info');
            }
        } catch (error) {
            this.showToast('Failed to disconnect Twitter', 'error');
        }
    },

    updateTwitterStatus(connected, username = '') {
        const disconnected = document.querySelector('#twitterAuthStatus .auth-status-disconnected');
        const connectedEl = document.querySelector('#twitterAuthStatus .auth-status-connected');
        const usernameEl = document.getElementById('twitterUsername');

        if (connected) {
            disconnected.style.display = 'none';
            connectedEl.style.display = 'flex';
            if (usernameEl && username) usernameEl.textContent = username;
        } else {
            disconnected.style.display = 'block';
            connectedEl.style.display = 'none';
        }
    },

    async connectInstagram() {
        // Instagram uses username/password, so show a prompt
        const username = prompt('Enter your Instagram username:');
        if (!username) return;

        const password = prompt('Enter your Instagram password:');
        if (!password) return;

        try {
            this.showToast('Connecting to Instagram...', 'info');

            const response = await fetch('/api/instagram/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (data.success) {
                this.updateInstagramStatus(true, data.username);
                this.showToast(`Instagram connected as ${data.username}`, 'success');
            } else {
                this.showToast(data.error || 'Failed to connect Instagram', 'error');
            }
        } catch (error) {
            this.showToast('Failed to connect Instagram', 'error');
        }
    },

    async disconnectInstagram() {
        try {
            const response = await fetch('/api/instagram/disconnect', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.updateInstagramStatus(false);
                this.showToast('Instagram disconnected', 'info');
            }
        } catch (error) {
            this.showToast('Failed to disconnect Instagram', 'error');
        }
    },

    updateInstagramStatus(connected, username = '') {
        const disconnected = document.querySelector('#instagramAuthStatus .auth-status-disconnected');
        const connectedEl = document.querySelector('#instagramAuthStatus .auth-status-connected');
        const usernameEl = document.getElementById('instagramUsername');

        if (connected) {
            disconnected.style.display = 'none';
            connectedEl.style.display = 'flex';
            if (usernameEl && username) usernameEl.textContent = username;
        } else {
            disconnected.style.display = 'block';
            connectedEl.style.display = 'none';
        }
    },

    async runPromotion() {
        const globalSelect = document.getElementById('globalAccountSelect');
        const channelId = globalSelect ? globalSelect.value : '';
        const selectedVideos = this.getSelectedVideoIds();

        if (!channelId) {
            this.showToast('Please select an account from the sidebar', 'warning');
            return;
        }

        if (selectedVideos.length === 0) {
            this.showToast('Please select at least one video to promote', 'warning');
            return;
        }

        // Collect platform settings
        const platforms = {};

        if (document.getElementById('enableTelegram').checked) {
            platforms.telegram = {
                bot_token: document.getElementById('telegramBotToken').value,
                channel_id: document.getElementById('telegramChannelId').value
            };

            if (!platforms.telegram.bot_token || !platforms.telegram.channel_id) {
                this.showToast('Please fill Telegram configuration', 'warning');
                return;
            }
        }

        if (document.getElementById('enableTwitter').checked) {
            // Check if Twitter is connected via OAuth
            const twitterConnected = document.querySelector('#twitterAuthStatus .auth-status-connected');
            if (!twitterConnected || twitterConnected.style.display === 'none') {
                this.showToast('Please connect your Twitter account first', 'warning');
                return;
            }
            platforms.twitter = { use_oauth: true };
        }

        if (document.getElementById('enableInstagram').checked) {
            // Check if Instagram is connected
            const instaConnected = document.querySelector('#instagramAuthStatus .auth-status-connected');
            if (!instaConnected || instaConnected.style.display === 'none') {
                this.showToast('Please connect your Instagram account first', 'warning');
                return;
            }
            platforms.instagram = { use_oauth: true };
        }

        if (Object.keys(platforms).length === 0) {
            this.showToast('Please enable at least one platform', 'warning');
            return;
        }

        // Show progress
        const progressContainer = document.getElementById('promotionProgress');
        progressContainer.style.display = 'block';
        document.getElementById('promotionLog').innerHTML = '';
        document.getElementById('promotionProgressBar').style.width = '0%';

        try {
            const response = await fetch('/api/run-promotion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    channel_id: channelId,
                    video_ids: selectedVideos,
                    platforms: platforms
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast(data.message || 'Promotion started!', 'success');
                // Start polling for status updates
                this.pollPromotionStatus();
            } else {
                this.showToast(data.error || 'Promotion failed', 'error');
                progressContainer.style.display = 'none';
            }
        } catch (error) {
            this.showToast('Failed to start promotion', 'error');
            document.getElementById('promotionProgress').style.display = 'none';
        }
    },

    async pollPromotionStatus() {
        const logContainer = document.getElementById('promotionLog');
        const progressBar = document.getElementById('promotionProgressBar');

        const poll = async () => {
            try {
                const response = await fetch('/api/promotion-status');
                const data = await response.json();

                // Update log display
                logContainer.innerHTML = data.logs.map(log => `<div class="log-line">${log}</div>`).join('');
                logContainer.scrollTop = logContainer.scrollHeight;

                // Update progress bar (estimate based on log count)
                if (data.running) {
                    progressBar.style.width = '50%';
                } else if (data.complete) {
                    progressBar.style.width = '100%';
                }

                // Continue polling if still running
                if (data.running) {
                    setTimeout(poll, 500);
                } else {
                    progressBar.style.width = '100%';
                    if (data.logs.some(l => l.includes('❌'))) {
                        this.showToast('Promotion completed with some errors', 'warning');
                    } else {
                        this.showToast('Promotion completed successfully!', 'success');
                    }
                }
            } catch (error) {
                console.error('Error polling status:', error);
            }
        };

        poll();
    },

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }
};

// Initialize app when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    app.init();
});

// Handle modal close on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// Handle Enter key in add account modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && document.getElementById('addAccountModal').classList.contains('active')) {
        app.addAccount();
    }
});
