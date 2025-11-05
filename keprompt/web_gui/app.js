// ===== Status Management =====
function setStatusLight(status) {
    const statusLight = document.getElementById('status-light');
    const statusText = document.getElementById('api-status');
    
    switch(status) {
        case 'ready':
            statusLight.style.background = '#28a745'; // Green
            statusLight.title = 'Status: Ready';
            statusText.textContent = 'Ready';
            break;
        case 'loading':
            statusLight.style.background = '#ffc107'; // Yellow
            statusLight.title = 'Status: Loading...';
            statusText.textContent = 'Loading...';
            break;
        case 'error':
            statusLight.style.background = '#dc3545'; // Red
            statusLight.title = 'Status: Error';
            statusText.textContent = 'Error';
            break;
        case 'connected':
            statusLight.style.background = '#28a745'; // Green
            statusLight.title = 'Status: Connected';
            statusText.textContent = 'Connected';
            break;
        case 'disconnected':
            statusLight.style.background = '#dc3545'; // Red
            statusLight.title = 'Status: Disconnected';
            statusText.textContent = 'Disconnected';
            break;
    }
}

// ===== API Client =====
const API = {
    baseURL: '/api',
    
    async request(endpoint, options = {}) {
        // Set status to loading (yellow)
        setStatusLight('loading');
        
        try {
            // Debug REST call if window.DEBUG_API is set
            if (window.DEBUG_API) {
                console.log('🔵 API Request:', {
                    endpoint: `${this.baseURL}${endpoint}`,
                    method: options.method || 'GET',
                    body: options.body ? JSON.parse(options.body) : null
                });
            }
            
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });
            
            const data = await response.json();
            
            // Debug REST response if window.DEBUG_API is set
            if (window.DEBUG_API) {
                console.log('🟢 API Response:', {
                    endpoint: `${this.baseURL}${endpoint}`,
                    status: response.status,
                    ok: response.ok,
                    data: data
                });
            }
            
            if (!response.ok) {
                setStatusLight('error');
                throw new Error(data.error || 'Request failed');
            }
            
            // Set status back to ready (green)
            setStatusLight('ready');
            
            return data;
        } catch (error) {
            if (window.DEBUG_API) {
                console.error('🔴 API Error:', {
                    endpoint: `${this.baseURL}${endpoint}`,
                    error: error
                });
            }
            console.error('API Error:', error);
            setStatusLight('error');
            throw error;
        }
    },
    
    // Chat endpoints
    async getChats(limit = 50) {
        return this.request(`/chats?limit=${limit}`);
    },
    
    async getChat(chatId) {
        return this.request(`/chats/${chatId}`);
    },
    
    async createChat(prompt, params = {}) {
        return this.request('/chats', {
            method: 'POST',
            body: JSON.stringify({ prompt, params }),
        });
    },
    
    async sendMessage(chatId, message) {
        return this.request(`/chats/${chatId}/messages`, {
            method: 'PUT',
            body: JSON.stringify({ answer: message }),
        });
    },
    
    async deleteChat(chatId) {
        return this.request(`/chats/${chatId}`, {
            method: 'DELETE',
        });
    },
    
    // Resource endpoints
    async getPrompts(pattern = null) {
        const url = pattern ? `/prompts?pattern=${encodeURIComponent(pattern)}` : '/prompts';
        return this.request(url);
    },
    
    async getModels(filters = {}) {
        const params = new URLSearchParams();
        if (filters.name) params.append('name', filters.name);
        if (filters.provider) params.append('provider', filters.provider);
        if (filters.company) params.append('company', filters.company);
        const queryString = params.toString();
        return this.request(`/models${queryString ? '?' + queryString : ''}`);
    },
    
    async getProviders() {
        return this.request('/providers');
    },
    
    async getFunctions() {
        return this.request('/functions');
    },
    
    async getDatabase() {
        return this.request('/database');
    },
    
    async getHealth() {
        return fetch('/health').then(r => r.json());
    }
};

// ===== State Management =====
const State = {
    currentTab: 'chats',
    currentChat: null,
    chats: [],
    prompts: [],
    models: [],
    providers: [],
    functions: [],
};

// ===== Utility Functions =====
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        if (hours === 0) {
            const minutes = Math.floor(diff / (1000 * 60));
            return minutes === 0 ? 'Just now' : `${minutes}m ago`;
        }
        return `${hours}h ago`;
    }
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString();
}

function formatTime(dateString) {
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showError(message, container = null) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    if (container) {
        container.innerHTML = '';
        container.appendChild(errorDiv);
    } else {
        console.error(message);
    }
}

function showLoading(container) {
    container.innerHTML = '<div class="loading">Loading</div>';
}

// ===== Tab Management =====
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            State.currentTab = tabName;
            
            // Load tab content
            loadTabContent(tabName);
        });
    });
}

function loadTabContent(tabName) {
    switch (tabName) {
        case 'chats':
            loadChats();
            break;
        case 'prompts':
            loadPrompts();
            break;
        case 'models':
            loadModels();
            break;
        case 'providers':
            loadProviders();
            break;
        case 'functions':
            loadFunctions();
            break;
        case 'database':
            loadDatabase();
            break;
        case 'server':
            loadServer();
            break;
    }
}

// ===== Chat Functions =====
async function loadChats() {
    const chatList = document.getElementById('chat-list');
    showLoading(chatList);
    
    try {
        const response = await API.getChats();
        State.chats = response.data || [];
        renderChatList(State.chats);
    } catch (error) {
        showError('Failed to load chats', chatList);
    }
}

function renderChatList(chats) {
    const chatList = document.getElementById('chat-list');
    
    if (!chats || chats.length === 0) {
        chatList.innerHTML = '<div class="empty-state"><p>No chats yet. Create one to get started!</p></div>';
        return;
    }
    
    chatList.innerHTML = chats.map(chat => {
        // Handle different timestamp field names
        const timestamp = chat.created_at || chat.created_timestamp || new Date().toISOString();
        const model = chat.model || chat.llm_model || 'No model';
        
        return `
            <div class="chat-item" data-chat-id="${chat.chat_id}" style="display: flex; flex-direction: column; gap: 0.25rem; padding: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="color: #6c757d; font-size: 0.85rem; min-width: 2rem;">${chat.chat_id}</span>
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;">${chat.prompt_name || 'Untitled'}</span>
                    <span style="color: #6c757d; font-size: 0.75rem; white-space: nowrap;">${formatDate(timestamp)}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem; padding-left: 2.5rem;">
                    <span style="color: #6c757d; font-size: 0.75rem; font-style: italic;">🤖 ${model}</span>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    document.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', () => {
            const chatId = item.dataset.chatId;
            selectChat(chatId);
        });
    });
}

async function selectChat(chatId) {
    // Update active state in list
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.toggle('active', item.dataset.chatId === chatId);
    });
    
    // Show chat interface
    document.getElementById('no-chat-selected').style.display = 'none';
    document.getElementById('chat-interface').style.display = 'flex';
    
    // Load chat messages
    const messagesArea = document.getElementById('messages-area');
    showLoading(messagesArea);
    
    try {
        const response = await API.getChat(chatId);
        // Extract chat data from nested structure
        const chatData = response.data[0]?.chat?.__data__ || response.data;
        
        // Parse messages_json if it's a string
        if (chatData.messages_json && typeof chatData.messages_json === 'string') {
            chatData.messages = JSON.parse(chatData.messages_json);
        } else if (chatData.messages_json) {
            chatData.messages = chatData.messages_json;
        }
        
        // Normalize timestamp field names
        if (chatData.created_timestamp && !chatData.created_at) {
            chatData.created_at = chatData.created_timestamp;
        }
        
        State.currentChat = chatData;
        renderChat(State.currentChat);
    } catch (error) {
        console.error('Error loading chat:', error);
        showError('Failed to load chat', messagesArea);
    }
}

function renderChat(chat) {
    // Update header
    document.getElementById('chat-title').textContent = chat.prompt_name || 'Chat';
    document.getElementById('chat-meta').textContent = 
        `${chat.chat_id} • Created ${formatDate(chat.created_at)}`;
    
    // Render messages
    const messagesArea = document.getElementById('messages-area');
    messagesArea.innerHTML = '';
    
    if (!chat.messages || chat.messages.length === 0) {
        messagesArea.innerHTML = '<div class="empty-state"><p>No messages yet. Start the conversation!</p></div>';
        return;
    }
    
    chat.messages.forEach((message, index) => {
        const messageDiv = document.createElement('div');
        const role = message.role || 'unknown';
        
        
        // Extract content based on message type
        let content = '';
        let contentHtml = '';
        let label = '';
        
        // Check if message content contains tool calls (type: 'tool' or 'tool_use')
        const hasToolCalls = Array.isArray(message.content) && 
            message.content.some(item => item.type === 'tool' || item.type === 'tool_use');
        
        // Add appropriate classes
        messageDiv.className = `message ${role}${hasToolCalls ? ' tool-call' : ''}`;
        
        // Debug logging
        if (hasToolCalls) {
            console.log('Tool call detected in message', index, ':', message);
        }
        
        // Determine avatar and label based on role and content
        let avatar = 'U';
        if (role === 'tool') {
            avatar = '🔧';
            label = '⚡ Tool Response';
        } else if (role === 'system') {
            avatar = 'S';
            label = '⚙️ System';
        } else if (role === 'assistant' && hasToolCalls) {
            avatar = '🔧';
            // Get the first tool call ID for the label
            const firstToolCall = message.content.find(item => item.type === 'tool' || item.type === 'tool_use');
            const callId = firstToolCall?.id || '';
            label = `⚡ Tool Call ${callId}`;
        } else if (role === 'assistant') {
            avatar = 'AI';
            label = '🤖 Assistant';
        } else if (role === 'user') {
            avatar = 'U';
            label = '👤 User';
        }
        
        if (role === 'assistant' && hasToolCalls) {
            // Assistant is making tool calls (content array with type: 'tool' or 'tool_use')
            const toolCalls = message.content.filter(item => item.type === 'tool' || item.type === 'tool_use');
            const textContent = message.content
                .filter(item => item.type === 'text')
                .map(item => item.text)
                .join('\n\n');
            
            contentHtml = `
                ${textContent ? `<div style="margin-bottom: 0.5rem;">${renderMarkdown(textContent)}</div>` : ''}
                <div style="padding: 0.5rem; background: rgba(0,0,0,0.05); border-radius: 4px; font-size: 0.85rem;">
                    ${toolCalls.map(call => {
                        const toolName = call.name || 'unknown';
                        const args = call.input || call.arguments || {};
                        const argEntries = Object.entries(args);
                        return `
                            <div style="margin-bottom: 0.5rem;">
                                <strong>🔧 ${toolName}()</strong>
                                ${argEntries.length > 0 ? `
                                    <div style="margin-left: 1rem; font-family: monospace; font-size: 0.8rem; margin-top: 0.25rem;">
                                        ${argEntries.map(([key, val]) => 
                                            `<div>${key}: ${JSON.stringify(val)}</div>`
                                        ).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else if (role === 'tool') {
            // Tool response - content is an array with tool_result objects
            if (Array.isArray(message.content) && message.content.length > 0) {
                const toolResult = message.content[0];
                const toolUseId = toolResult.tool_use_id || '';
                const resultContent = toolResult.content || toolResult;
                
                try {
                    const result = typeof resultContent === 'string' ? JSON.parse(resultContent) : resultContent;
                    contentHtml = `<pre style="font-size: 0.85rem; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
                } catch {
                    contentHtml = `<div>${escapeHtml(String(resultContent))}</div>`;
                }
                label = `⚡ Tool Response ${toolUseId}`;
            } else {
                // Fallback for old format
                const toolName = message.name || 'tool';
                try {
                    const result = typeof message.content === 'string' ? JSON.parse(message.content) : message.content;
                    contentHtml = `<pre style="font-size: 0.85rem; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
                } catch {
                    contentHtml = `<div>${escapeHtml(message.content)}</div>`;
                }
                label = `⚡ ${toolName} response`;
            }
        } else {
            // Regular user/assistant/system message
            if (typeof message.content === 'string') {
                content = message.content;
            } else if (Array.isArray(message.content)) {
                content = message.content
                    .filter(item => item.type === 'text')
                    .map(item => item.text)
                    .join('\n\n');
            }
            
            // Render content based on role
            if (role === 'user') {
                contentHtml = escapeHtml(content);
            } else if (role === 'assistant' || role === 'system') {
                contentHtml = renderMarkdown(content);
            } else {
                contentHtml = escapeHtml(content);
            }
        }
        
        // Format timestamp
        const timeStr = message.timestamp || message.created_at || new Date().toISOString();
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-bubble collapsed" data-expanded="false">
                    <div class="message-label">
                        ${label}
                        <span class="collapse-indicator">▶</span>
                    </div>
                    <div class="message-body">${contentHtml}</div>
                </div>
            </div>
        `;
        
        // Store original content for collapse/expand
        const messageBody = messageDiv.querySelector('.message-body');
        const originalContent = messageBody.innerHTML;
        // Create plain text version with '\n' for newlines
        const plainText = messageBody.textContent.replace(/\n/g, '\\n');
        
        // Set initial collapsed state
        messageBody.textContent = plainText;
        
        // Add double-click handler for collapse/expand on the entire bubble
        const bubble = messageDiv.querySelector('.message-bubble');
        const labelEl = messageDiv.querySelector('.message-label');
        bubble.addEventListener('dblclick', (e) => {
            const isExpanded = bubble.getAttribute('data-expanded') === 'true';
            bubble.setAttribute('data-expanded', !isExpanded);
            if (isExpanded) {
                bubble.classList.add('collapsed');
                labelEl.querySelector('.collapse-indicator').textContent = '▶';
                // Replace content with plain text version showing '\n'
                messageBody.textContent = plainText;
            } else {
                bubble.classList.remove('collapsed');
                labelEl.querySelector('.collapse-indicator').textContent = '▼';
                // Restore original HTML content
                messageBody.innerHTML = originalContent;
            }
        });
        
        messagesArea.appendChild(messageDiv);
    });
    
    // Scroll to bottom
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return '';
    
    // Convert markdown to HTML
    let html = text;
    
    // Code blocks (```lang\ncode\n```)
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // Tables (must be done before inline code)
    html = html.replace(/\|(.+)\|[\r\n]+\|[-:\s|]+\|[\r\n]+((?:\|.+\|[\r\n]*)+)/g, (match, header, rows) => {
        const headers = header.split('|').map(h => h.trim()).filter(h => h);
        const rowData = rows.trim().split(/[\r\n]+/).map(row => 
            row.split('|').map(cell => cell.trim()).filter(cell => cell)
        );
        
        return `<table class="markdown-table">
            <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
            <tbody>${rowData.map(row => 
                `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`
            ).join('')}</tbody>
        </table>`;
    });
    
    // Inline code (`code`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Bold (**text** or __text__)
    html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    
    // Italic (*text* or _text_)
    html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Headers (# Header)
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // Lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message || !State.currentChat) return;
    
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    input.disabled = true;
    
    try {
        // Add user message to UI immediately
        const messagesArea = document.getElementById('messages-area');
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user';
        userMessageDiv.innerHTML = `
            <div class="message-avatar">U</div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="message-label">👤 User</div>
                    <div class="message-body">${escapeHtml(message)}</div>
                </div>
                <div class="message-time">${formatTime(new Date().toISOString())}</div>
            </div>
        `;
        messagesArea.appendChild(userMessageDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;
        
        // Clear input
        input.value = '';
        
        // Send to API
        const response = await API.sendMessage(State.currentChat.chat_id, message);
        
        // Reload chat to get assistant response
        await selectChat(State.currentChat.chat_id);
        
    } catch (error) {
        showError('Failed to send message');
    } finally {
        sendBtn.disabled = false;
        input.disabled = false;
        input.focus();
    }
}

// ===== New Chat Modal =====
function initNewChatModal() {
    const modal = document.getElementById('new-chat-modal');
    const newChatBtn = document.getElementById('new-chat-btn');
    const closeBtn = modal.querySelector('.close-modal');
    const cancelBtn = document.getElementById('cancel-chat-btn');
    const createBtn = document.getElementById('create-chat-btn');
    
    newChatBtn.addEventListener('click', async () => {
        modal.classList.add('active');
        await loadPromptsForModal();
    });
    
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });
    
    cancelBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });
    
    createBtn.addEventListener('click', async () => {
        await createNewChat();
    });
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });
}

async function loadPromptsForModal() {
    const select = document.getElementById('prompt-select');
    
    try {
        const response = await API.getPrompts();
        // API returns prompts in 'prompts' field, not 'data'
        const prompts = response.prompts || response.data || [];
        
        // Store prompts for parameter extraction
        State.promptsForModal = prompts;
        
        select.innerHTML = '<option value="">-- Select a prompt --</option>' +
            (prompts.length > 0
                ? prompts.map(p => `<option value="${p.name}">${p.name}</option>`).join('')
                : '<option value="" disabled>No prompts available</option>');
        
        // Add event listener for prompt selection
        select.onchange = () => {
            const selectedPrompt = prompts.find(p => p.name === select.value);
            if (selectedPrompt) {
                displayPromptParameters(selectedPrompt);
            } else {
                document.getElementById('prompt-params').style.display = 'none';
            }
        };
            
    } catch (error) {
        console.error('Error loading prompts for modal:', error);
        select.innerHTML = '<option value="">Error loading prompts</option>';
    }
}

function displayPromptParameters(prompt) {
    const paramsSection = document.getElementById('prompt-params');
    const paramsContainer = document.getElementById('params-container');
    
    // Parse parameters from prompt source
    let params = {};
    if (prompt.source) {
        const firstLine = prompt.source.split('\n')[0];
        if (firstLine.startsWith('.prompt')) {
            try {
                const jsonPart = firstLine.substring('.prompt'.length).trim();
                const parsed = JSON.parse('{' + jsonPart + '}');
                params = parsed.params || {};
            } catch (e) {
                if (window.DEBUG_API) {
                    console.log('Failed to parse prompt parameters:', e);
                }
            }
        }
    }
    
    // If no parameters, hide the section
    if (Object.keys(params).length === 0) {
        paramsSection.style.display = 'none';
        return;
    }
    
    // Show parameters section and build input fields
    paramsSection.style.display = 'block';
    paramsContainer.innerHTML = Object.entries(params).map(([key, defaultValue]) => `
        <div class="param-input-group" style="margin-bottom: 0.75rem;">
            <label for="param-${key}" style="display: block; margin-bottom: 0.25rem; font-weight: 500;">
                ${key}:
            </label>
            <input 
                type="text" 
                id="param-${key}" 
                name="${key}"
                class="form-control param-input" 
                value="${escapeHtml(String(defaultValue))}"
                placeholder="Enter ${key}"
                style="width: 100%;"
            />
        </div>
    `).join('');
}

async function createNewChat() {
    const select = document.getElementById('prompt-select');
    const promptName = select.value;
    
    if (!promptName) {
        alert('Please select a prompt');
        return;
    }
    
    // Find the selected prompt to get its path
    const selectedPrompt = State.promptsForModal?.find(p => p.name === promptName);
    if (!selectedPrompt || !selectedPrompt.path) {
        alert('Could not find prompt path');
        return;
    }
    
    const createBtn = document.getElementById('create-chat-btn');
    createBtn.disabled = true;
    
    try {
        // Collect parameter values from input fields
        const paramInputs = document.querySelectorAll('.param-input');
        const params = {};
        paramInputs.forEach(input => {
            const paramName = input.name;
            const paramValue = input.value.trim();
            if (paramName && paramValue) {
                params[paramName] = paramValue;
            }
        });
        
        // Create chat with prompt path (not name)
        const response = await API.createChat(selectedPrompt.path, params);
        
        // Log response for debugging
        if (window.DEBUG_API) {
            console.log('Create chat response:', response);
        }
        
        // Extract chat_id from response
        let chatId;
        if (response.data) {
            // Handle different response structures
            if (typeof response.data === 'number') {
                chatId = response.data;
            } else if (response.data.chat_id) {
                chatId = response.data.chat_id;
            } else if (response.data.id) {
                chatId = response.data.id;
            }
        } else if (response.chat_id) {
            chatId = response.chat_id;
        } else if (response.id) {
            chatId = response.id;
        }
        
        if (!chatId) {
            console.error('Could not extract chat_id from response:', response);
            throw new Error('Invalid response from server: missing chat_id');
        }
        
        // Close modal and reset
        const modal = document.getElementById('new-chat-modal');
        modal.classList.remove('active');
        document.getElementById('prompt-params').style.display = 'none';
        
        // Reload chats and select new one
        await loadChats();
        await selectChat(chatId);
        
    } catch (error) {
        console.error('Error creating chat:', error);
        alert('Failed to create chat: ' + error.message);
    } finally {
        createBtn.disabled = false;
    }
}

// ===== Delete Chat =====
function initDeleteChat() {
    const deleteBtn = document.getElementById('delete-chat-btn');
    
    deleteBtn.addEventListener('click', () => {
        if (!State.currentChat) return;
        
        showConfirmModal(
            'Delete Chat',
            `Are you sure you want to delete chat ${State.currentChat.chat_id}? This cannot be undone.`,
            async () => {
                try {
                    await API.deleteChat(State.currentChat.chat_id);
                    
                    // Clear current chat
                    State.currentChat = null;
                    document.getElementById('chat-interface').style.display = 'none';
                    document.getElementById('no-chat-selected').style.display = 'flex';
                    
                    // Reload chat list
                    await loadChats();
                    
                } catch (error) {
                    alert('Failed to delete chat: ' + error.message);
                }
            }
        );
    });
}

// ===== Confirm Modal =====
function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('confirm-modal');
    const titleEl = document.getElementById('confirm-title');
    const messageEl = document.getElementById('confirm-message');
    const okBtn = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    const closeBtn = modal.querySelector('.close-modal');
    
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    modal.classList.add('active');
    
    const close = () => {
        modal.classList.remove('active');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        closeBtn.onclick = null;
    };
    
    okBtn.onclick = () => {
        close();
        onConfirm();
    };
    
    cancelBtn.onclick = close;
    closeBtn.onclick = close;
    
    modal.onclick = (e) => {
        if (e.target === modal) close();
    };
}

// ===== Prompts Tab =====
async function loadPrompts() {
    const promptList = document.getElementById('prompt-list');
    showLoading(promptList);
    
    try {
        const response = await API.getPrompts();
        // API returns prompts in 'prompts' field, not 'data'
        State.prompts = response.prompts || response.data || [];
        renderPromptList(State.prompts);
    } catch (error) {
        console.error('Error loading prompts:', error);
        showError('Failed to load prompts', promptList);
    }
}

function renderPromptList(prompts) {
    const promptList = document.getElementById('prompt-list');
    
    if (!prompts || prompts.length === 0) {
        promptList.innerHTML = '<div class="empty-state"><p>No prompts found</p></div>';
        return;
    }
    
    promptList.innerHTML = prompts.map(prompt => {
        // Parse version from source
        let version = '';
        if (prompt.source) {
            const firstLine = prompt.source.split('\n')[0];
            if (firstLine.startsWith('.prompt')) {
                try {
                    const jsonPart = firstLine.substring('.prompt'.length).trim();
                    const parsed = JSON.parse('{' + jsonPart + '}');
                    version = parsed.version || '';
                } catch (e) {
                    // Ignore parsing errors
                }
            }
        }
        
        const versionBadge = version ? ` <span style="background: #e3f2fd; color: #1976d2; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 500;">v${version}</span>` : '';
        
        return `
            <div class="chat-item" data-prompt-name="${escapeHtml(prompt.name)}" style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.2rem;">📝</span>
                <span style="flex: 1;">${prompt.name}${versionBadge}</span>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    document.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', () => {
            const promptName = item.dataset.promptName;
            selectPrompt(promptName);
        });
    });
}

// ===== Prompt Syntax Highlighting =====
function highlightPromptSource(source) {
    const lines = source.split('\n');
    let currentMode = null; // Tracks .system, .user, or .assistant
    
    // Mode colors
    const modeColors = {
        '.system': '#28a745',     // Green
        '.user': '#17a2b8',       // Cyan
        '.assistant': '#ffc107'   // Amber/yellow
    };
    
    const result = lines.map((line, i) => {
        const lineNum = (i + 1).toString().padStart(3, ' ');
        let highlightedLine = '';
        
        // Check if line starts with a mode-changing keyword
        if (line.startsWith('.system') || line.startsWith('.user') || line.startsWith('.assistant')) {
            const spaceIndex = line.indexOf(' ');
            currentMode = spaceIndex > 0 ? line.substring(0, spaceIndex) : line;
            
            // Highlight the keyword in bold with its mode color
            const keyword = currentMode;
            const rest = spaceIndex > 0 ? line.substring(spaceIndex) : '';
            const color = modeColors[currentMode] || '#0066cc';
            highlightedLine = `<span style="color: ${color}; font-weight: bold;">${escapeHtml(keyword)}</span>${rest ? highlightVariables(rest, color) : ''}`;
        }
        // Check for other keywords
        else if (line.startsWith('.#')) {
            // Comment
            highlightedLine = `<span style="color: #6c757d; font-style: italic;">${escapeHtml(line)}</span>`;
        }
        else if (line.startsWith('.llm')) {
            const spaceIndex = line.indexOf(' ');
            const keyword = spaceIndex > 0 ? line.substring(0, spaceIndex) : line;
            const rest = spaceIndex > 0 ? line.substring(spaceIndex) : '';
            highlightedLine = `<span style="color: #0066cc; font-weight: bold;">${escapeHtml(keyword)}</span>${rest ? highlightJson(rest) : ''}`;
        }
        else if (line.startsWith('.cmd')) {
            const spaceIndex = line.indexOf(' ');
            const keyword = spaceIndex > 0 ? line.substring(0, spaceIndex) : line;
            const rest = spaceIndex > 0 ? line.substring(spaceIndex) : '';
            highlightedLine = `<span style="color: #0066cc; font-weight: bold;">${escapeHtml(keyword)}</span>${rest ? highlightFunctionCall(rest) : ''}`;
        }
        else if (line.startsWith('.prompt') || line.startsWith('.exec') || line.startsWith('.exit') || 
                 line.startsWith('.print') || line.startsWith('.set') || line.startsWith('.debug') ||
                 line.startsWith('.include') || line.startsWith('.image') || line.startsWith('.clear') ||
                 line.startsWith('.text')) {
            const spaceIndex = line.indexOf(' ');
            const keyword = spaceIndex > 0 ? line.substring(0, spaceIndex) : line;
            const rest = spaceIndex > 0 ? line.substring(spaceIndex) : '';
            highlightedLine = `<span style="color: #0066cc; font-weight: bold;">${escapeHtml(keyword)}</span>${rest ? highlightVariables(rest) : ''}`;
        }
        // Continuation line - use current mode color if in a mode
        else if (currentMode && modeColors[currentMode]) {
            const color = modeColors[currentMode];
            highlightedLine = `<span style="color: ${color};">${highlightVariables(line, color)}</span>`;
        }
        // Default line
        else {
            highlightedLine = highlightVariables(line);
        }
        
        return `<div style="display: flex;">
            <span style="color: #6c757d; user-select: none; padding-right: 1rem; text-align: right; min-width: 3rem;">${lineNum}</span>
            <span style="flex: 1; white-space: pre-wrap; word-break: break-all;">${highlightedLine}</span>
        </div>`;
    }).join('');
    
    return result;
}

function highlightJson(text) {
    // Simple JSON syntax highlighting
    let html = escapeHtml(text);
    // Highlight strings
    html = html.replace(/"([^"\\]*(\\.[^"\\]*)*)"/g, '<span style="color: #d63384;">"$1"</span>');
    // Highlight numbers
    html = html.replace(/\b(\d+\.?\d*)\b/g, '<span style="color: #098658;">$1</span>');
    // Highlight booleans and null
    html = html.replace(/\b(true|false|null)\b/g, '<span style="color: #0066cc;">$1</span>');
    return html;
}

function highlightFunctionCall(text) {
    // Highlight function name and parameters
    const match = text.match(/^\s*(\w+)\s*\(/);
    if (match) {
        const funcName = match[1];
        const rest = text.substring(match[0].length - 1); // Keep the opening paren
        return ` <span style="color: #795548; font-weight: bold;">${funcName}</span>${highlightVariables(rest)}`;
    }
    return highlightVariables(text);
}

function highlightVariables(text, baseColor = null) {
    // Highlight <<variable>> patterns
    let html = escapeHtml(text);
    html = html.replace(/&lt;&lt;([^&]+)&gt;&gt;/g, '<span style="color: #d63384; font-weight: bold;">&lt;&lt;$1&gt;&gt;</span>');
    // If baseColor is provided and text doesn't already have color spans, wrap it
    if (baseColor && !html.includes('<span')) {
        return html;
    }
    return html;
}

function selectPrompt(promptName) {
    // Find the prompt
    const prompt = State.prompts.find(p => p.name === promptName);
    if (!prompt) return;
    
    // Update active state in list
    document.querySelectorAll('#prompt-list .chat-item').forEach(item => {
        item.classList.toggle('active', item.dataset.promptName === promptName);
    });
    
    // Show prompt details interface
    document.getElementById('no-prompt-selected').style.display = 'none';
    document.getElementById('prompt-details').style.display = 'flex';
    
    // Parse metadata
    let version = '';
    let params = {};
    
    if (prompt.source) {
        const firstLine = prompt.source.split('\n')[0];
        if (firstLine.startsWith('.prompt')) {
            try {
                const jsonPart = firstLine.substring('.prompt'.length).trim();
                const parsed = JSON.parse('{' + jsonPart + '}');
                version = parsed.version || '';
                params = parsed.params || {};
            } catch (e) {
                if (window.DEBUG_API) {
                    console.log('Failed to parse prompt metadata:', e);
                }
            }
        }
    }
    
    // Update header
    document.getElementById('prompt-name').textContent = prompt.name;
    
    // Build metadata string
    const metaParts = [];
    if (version) metaParts.push(`Version: ${version}`);
    if (prompt.path) metaParts.push(`Path: ${prompt.path}`);
    document.getElementById('prompt-meta').textContent = metaParts.join(' • ');
    
    // Render prompt details
    const contentArea = document.getElementById('prompt-content-area');
    
    // Build parameters section (condensed)
    const paramsHtml = Object.keys(params).length > 0 
        ? `<div style="background: #f8f9fa; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; border-left: 3px solid #007bff;">
            <strong style="color: #495057; font-size: 0.9rem;">Parameters:</strong>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                ${Object.entries(params).map(([key, value]) => 
                    `<span style="background: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; border: 1px solid #dee2e6;">
                        <strong>${key}:</strong> <code style="color: #d63384;">${escapeHtml(String(value))}</code>
                    </span>`
                ).join('')}
            </div>
           </div>`
        : '';
    
    // Format source code with line numbers and syntax highlighting
    const sourceHtml = highlightPromptSource(prompt.source || '');
    
    contentArea.innerHTML = `
        ${paramsHtml}
        <div style="background: #f8f9fa; border-radius: 6px; padding: 1rem; font-family: 'Courier New', monospace; font-size: 0.85rem; line-height: 1.5; overflow-x: auto; height: calc(100% - ${Object.keys(params).length > 0 ? '100px' : '20px'}); overflow-y: auto;">
            ${sourceHtml}
        </div>
    `;
}

// ===== Models Tab =====
async function loadModels(filters = {}) {
    const content = document.getElementById('models-content');
    showLoading(content);
    
    try {
        const response = await API.getModels(filters);
        console.log('Models response:', response);
        State.models = response.data || [];
        renderModels(State.models);
        
        // Populate filter dropdowns if first load
        if (!filters.provider && !filters.company) {
            populateModelFilters(State.models);
        }
    } catch (error) {
        console.error('Error loading models:', error);
        showError('Failed to load models: ' + error.message, content);
    }
}

function populateModelFilters(models) {
    const providerFilter = document.getElementById('provider-filter');
    const companyFilter = document.getElementById('company-filter');
    
    const providers = [...new Set(models.map(m => m.provider))].sort();
    const companies = [...new Set(models.map(m => m.company))].sort();
    
    providerFilter.innerHTML = '<option value="">All Providers</option>' +
        providers.map(p => `<option value="${p}">${p}</option>`).join('');
    
    companyFilter.innerHTML = '<option value="">All Companies</option>' +
        companies.map(c => `<option value="${c}">${c}</option>`).join('');
}

function renderModels(models) {
    const content = document.getElementById('models-content');
    
    if (!models || models.length === 0) {
        content.innerHTML = '<div class="empty-state"><p>No models found</p></div>';
        return;
    }
    
    content.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Provider</th>
                    <th>Company</th>
                    <th>Model</th>
                    <th>Max Tokens</th>
                    <th>$/MT In</th>
                    <th>$/MT Out</th>
                    <th>Features</th>
                </tr>
            </thead>
            <tbody>
                ${models.map(m => `
                    <tr>
                        <td>${m.provider || ''}</td>
                        <td>${m.company || ''}</td>
                        <td><strong>${m.model || m.name || ''}</strong></td>
                        <td>${m.max_tokens ? m.max_tokens.toLocaleString() : ''}</td>
                        <td>$${m.input_cost ? (m.input_cost * 1000000).toFixed(2) : '0.00'}</td>
                        <td>$${m.output_cost ? (m.output_cost * 1000000).toFixed(2) : '0.00'}</td>
                        <td>
                            ${m.supports ? Object.entries(m.supports)
                                .filter(([key, value]) => value === true)
                                .map(([key]) => {
                                    // Map support keys to display names and colors
                                    const supportMap = {
                                        'vision': { label: 'Vision', color: 'badge-info' },
                                        'function_calling': { label: 'Functions', color: 'badge-success' },
                                        'native_streaming': { label: 'Streaming', color: 'badge-primary' },
                                        'parallel_function_calling': { label: 'Parallel Fns', color: 'badge-success' },
                                        'pdf_input': { label: 'PDF', color: 'badge-info' },
                                        'prompt_caching': { label: 'Caching', color: 'badge-warning' },
                                        'reasoning': { label: 'Reasoning', color: 'badge-primary' },
                                        'response_schema': { label: 'Schema', color: 'badge-secondary' },
                                        'system_messages': { label: 'System', color: 'badge-secondary' },
                                        'tool_choice': { label: 'Tool Choice', color: 'badge-success' }
                                    };
                                    const config = supportMap[key] || { label: key, color: 'badge-secondary' };
                                    return `<span class="badge ${config.color}">${config.label}</span>`;
                                })
                                .join(' ') : ''}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// ===== Providers Tab =====
async function loadProviders() {
    const content = document.getElementById('providers-content');
    showLoading(content);
    
    try {
        const response = await API.getProviders();
        console.log('Providers response:', response);
        State.providers = response.data || [];
        renderProviders(State.providers);
    } catch (error) {
        console.error('Error loading providers:', error);
        showError('Failed to load providers: ' + error.message, content);
    }
}

function renderProviders(providers) {
    const content = document.getElementById('providers-content');
    
    if (!providers || providers.length === 0) {
        content.innerHTML = '<div class="empty-state"><p>No providers found</p></div>';
        return;
    }
    
    content.innerHTML = `
        <div class="card-grid">
            ${providers.map(provider => `
                <div class="stat-card">
                    <div class="stat-value">${provider.models_count || 0}</div>
                    <div class="stat-label">${provider.name || 'Unknown'}</div>
                </div>
            `).join('')}
        </div>
    `;
}

// ===== Functions Tab =====
async function loadFunctions() {
    const content = document.getElementById('functions-content');
    showLoading(content);
    
    try {
        const response = await API.getFunctions();
        State.functions = response.data || [];
        renderFunctions(State.functions);
    } catch (error) {
        showError('Failed to load functions', content);
    }
}

function renderFunctions(functions) {
    const content = document.getElementById('functions-content');
    
    if (!functions || functions.length === 0) {
        content.innerHTML = '<div class="empty-state"><p>No functions found</p></div>';
        return;
    }
    
    content.innerHTML = functions.map(item => {
        // Functions have nested structure: item.function contains the actual function
        const func = item.function || item;
        const params = func.parameters?.properties || {};
        const required = func.parameters?.required || [];
        
        return `
            <div class="card">
                <div class="card-header">${func.name || 'Unnamed Function'}</div>
                <div class="card-body">
                    <p>${func.description || 'No description'}</p>
                    ${Object.keys(params).length > 0 ? `
                        <h4 style="margin-top: 1rem; margin-bottom: 0.5rem;">Parameters:</h4>
                        <ul style="margin-left: 1.5rem;">
                            ${Object.entries(params).map(([paramName, paramInfo]) => `
                                <li>
                                    <strong>${paramName}</strong>
                                    ${required.includes(paramName) ? '<span class="badge badge-danger">Required</span>' : ''}
                                    - ${paramInfo.description || 'No description'}
                                </li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ===== Database Tab =====
async function loadDatabase() {
    const content = document.getElementById('database-content');
    showLoading(content);
    
    try {
        const response = await API.getDatabase();
        renderDatabase(response.data);
    } catch (error) {
        showError('Failed to load database info', content);
    }
}

function renderDatabase(dbInfo) {
    const content = document.getElementById('database-content');
    
    if (!dbInfo || !dbInfo.database_exists) {
        content.innerHTML = `
            <div class="empty-state">
                <h3>Database not initialized</h3>
                <p>The database has not been created yet.</p>
            </div>
        `;
        return;
    }
    
    content.innerHTML = `
        <div class="card-grid">
            <div class="stat-card">
                <div class="stat-value">${dbInfo.size_mb}</div>
                <div class="stat-label">Size (MB)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${dbInfo.chat_count}</div>
                <div class="stat-label">Total Chats</div>
            </div>
        </div>
        <div class="card" style="margin-top: 1rem;">
            <div class="card-header">Database Information</div>
            <div class="card-body">
                <p><strong>Path:</strong> ${dbInfo.path}</p>
                <p><strong>Last Modified:</strong> ${formatDate(new Date(dbInfo.last_modified * 1000))}</p>
            </div>
        </div>
    `;
}

// ===== Server Tab =====
async function loadServer() {
    const content = document.getElementById('server-content');
    showLoading(content);
    
    try {
        const response = await API.getHealth();
        renderServer(response.data);
    } catch (error) {
        showError('Failed to load server info', content);
    }
}

function renderServer(serverInfo) {
    const content = document.getElementById('server-content');
    
    content.innerHTML = `
        <div class="card">
            <div class="card-header">Server Status</div>
            <div class="card-body">
                <p><strong>Service:</strong> ${serverInfo.service}</p>
                <p><strong>Version:</strong> ${serverInfo.version}</p>
                <p><strong>Status:</strong> <span class="badge badge-success">Healthy</span></p>
            </div>
        </div>
    `;
}

// ===== Search and Filter Handlers =====
function initSearchAndFilters() {
    // Model filters
    const modelSearch = document.getElementById('model-search');
    const providerFilter = document.getElementById('provider-filter');
    const companyFilter = document.getElementById('company-filter');
    
    let modelFilterTimeout;
    const filterModels = () => {
        clearTimeout(modelFilterTimeout);
        modelFilterTimeout = setTimeout(() => {
            loadModels({
                name: modelSearch.value,
                provider: providerFilter.value,
                company: companyFilter.value
            });
        }, 300);
    };
    
    modelSearch.addEventListener('input', filterModels);
    providerFilter.addEventListener('change', filterModels);
    companyFilter.addEventListener('change', filterModels);
    
    // Refresh buttons
    document.getElementById('refresh-prompts-btn').addEventListener('click', loadPrompts);
    document.getElementById('refresh-models-btn').addEventListener('click', () => loadModels());
    document.getElementById('refresh-providers-btn').addEventListener('click', loadProviders);
    document.getElementById('refresh-functions-btn').addEventListener('click', loadFunctions);
    document.getElementById('refresh-db-btn').addEventListener('click', loadDatabase);
    document.getElementById('refresh-server-btn').addEventListener('click', loadServer);
}

// ===== Message Input Handler =====
function initMessageInput() {
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    
    // Send on Enter (Shift+Enter for new line)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    sendBtn.addEventListener('click', sendMessage);
    
    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = input.scrollHeight + 'px';
    });
}

// ===== Check API Status =====
async function checkAPIStatus() {
    try {
        const response = await API.getHealth();
        document.getElementById('api-status').textContent = 'Connected';
        document.getElementById('api-status').style.background = 'var(--success-color)';
        document.getElementById('version-info').textContent = `v${response.data.version}`;
    } catch (error) {
        document.getElementById('api-status').textContent = 'Disconnected';
        document.getElementById('api-status').style.background = 'var(--danger-color)';
    }
}

// ===== Debug Toggle =====
function initDebugToggle() {
    const debugToggle = document.getElementById('debug-toggle');
    
    // Load saved debug state from localStorage
    const savedDebugState = localStorage.getItem('debugMode') === 'true';
    debugToggle.checked = savedDebugState;
    window.DEBUG_API = savedDebugState;
    
    // Handle toggle changes
    debugToggle.addEventListener('change', (e) => {
        window.DEBUG_API = e.target.checked;
        localStorage.setItem('debugMode', e.target.checked);
        console.log('Debug mode:', window.DEBUG_API ? 'ON' : 'OFF');
    });
}

// ===== Initialize Application =====
async function init() {
    // Initialize debug toggle first
    initDebugToggle();
    
    // Check API status
    await checkAPIStatus();
    
    // Initialize components
    initTabs();
    initNewChatModal();
    initDeleteChat();
    initMessageInput();
    initSearchAndFilters();
    
    // Load initial content
    loadChats();
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
