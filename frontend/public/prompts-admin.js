// Prompts Admin - Standalone JavaScript
const API_BASE = '/api/prompts';
const TOKEN_KEY = 'prompts_admin_token';
const TOKEN_EXPIRY_KEY = 'prompts_admin_token_expiry';

const CATEGORIES = {
    chat: { name: 'Chat', color: 'chat' },
    analysis: { name: 'Analyse', color: 'analysis' },
    report: { name: 'Report', color: 'report' },
    material: { name: 'Material', color: 'material' },
};

let currentToken = null;
let allPrompts = [];
let editingPrompt = null;

// Token management
function saveToken(token, expiresIn) {
    const expiryTime = Date.now() + expiresIn * 1000;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
    currentToken = token;
}

function getToken() {
    const token = localStorage.getItem(TOKEN_KEY);
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

    if (!token || !expiry) return null;
    if (Date.now() > parseInt(expiry)) {
        clearToken();
        return null;
    }

    return token;
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
    currentToken = null;
}

// Toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastContent = document.getElementById('toastContent');

    toastContent.textContent = message;
    toastContent.className = `toast-content toast-${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Authentication
async function authenticate(password) {
    const response = await fetch(`${API_BASE}/authenticate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
    });

    if (!response.ok) {
        throw new Error(response.status === 401 ? 'Falsches Passwort' : 'Authentifizierung fehlgeschlagen');
    }

    return response.json();
}

// Load prompts
async function loadPrompts() {
    const token = getToken();
    if (!token) {
        showLoginModal();
        return;
    }

    document.getElementById('loadingContainer').classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/list`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearToken();
                showLoginModal();
                return;
            }
            throw new Error('Fehler beim Laden der Prompts');
        }

        allPrompts = await response.json();
        renderPrompts();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        document.getElementById('loadingContainer').classList.add('hidden');
    }
}

// Render prompts
function renderPrompts() {
    const container = document.getElementById('promptsContainer');
    container.innerHTML = '';

    // Group by category
    const byCategory = {};
    allPrompts.forEach(prompt => {
        const category = prompt.category || 'other';
        if (!byCategory[category]) byCategory[category] = [];
        byCategory[category].push(prompt);
    });

    // Render each category
    Object.entries(CATEGORIES).forEach(([categoryKey, categoryInfo]) => {
        const prompts = byCategory[categoryKey] || [];
        if (prompts.length === 0) return;

        const section = document.createElement('div');
        section.className = 'category-section';

        section.innerHTML = `
            <h2 class="category-header">
                <span class="category-badge ${categoryKey}">${categoryInfo.name}</span>
                <span class="category-count">(${prompts.length})</span>
            </h2>
            <div class="prompts-grid" id="grid-${categoryKey}"></div>
        `;

        container.appendChild(section);

        const grid = document.getElementById(`grid-${categoryKey}`);
        prompts.forEach(prompt => {
            const card = document.createElement('div');
            card.className = 'prompt-card';
            card.innerHTML = `
                <div class="prompt-card-header">
                    <h3>${prompt.prompt_name}</h3>
                    <button class="btn-edit" data-key="${prompt.prompt_key}">Bearbeiten</button>
                </div>
                ${prompt.description ? `<p class="prompt-description">${prompt.description}</p>` : ''}
                <div class="prompt-preview">${prompt.prompt_content.substring(0, 200)}${prompt.prompt_content.length > 200 ? '...' : ''}</div>
                <div class="prompt-meta">
                    <span>Key: ${prompt.prompt_key}</span>
                    ${prompt.temperature ? `<span>Temp: ${prompt.temperature}</span>` : ''}
                    ${prompt.version ? `<span>v${prompt.version}</span>` : ''}
                </div>
            `;

            card.querySelector('.btn-edit').addEventListener('click', () => openEditor(prompt));
            grid.appendChild(card);
        });
    });
}

// Editor
function openEditor(prompt) {
    editingPrompt = prompt;
    document.getElementById('editorTitle').textContent = prompt.prompt_name;
    document.getElementById('editorDescription').textContent = prompt.description || '';
    document.getElementById('editorMeta').innerHTML = `
        <span>Key: ${prompt.prompt_key}</span>
        ${prompt.temperature ? `<span>Temperature: ${prompt.temperature}</span>` : ''}
        ${prompt.max_tokens ? `<span>Max Tokens: ${prompt.max_tokens}</span>` : ''}
        ${prompt.version ? `<span>Version: ${prompt.version}</span>` : ''}
    `;

    const textarea = document.getElementById('editorTextarea');
    textarea.value = prompt.prompt_content;
    updateCharCount();

    document.getElementById('editorModal').classList.remove('hidden');
}

function closeEditor() {
    editingPrompt = null;
    document.getElementById('editorModal').classList.add('hidden');
}

function updateCharCount() {
    const textarea = document.getElementById('editorTextarea');
    document.getElementById('charCount').textContent = `${textarea.value.length} Zeichen`;
}

async function savePrompt() {
    if (!editingPrompt) return;

    const token = getToken();
    if (!token) {
        showLoginModal();
        return;
    }

    const content = document.getElementById('editorTextarea').value;
    const saveBtn = document.getElementById('editorSaveBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Speichert...';

    try {
        const response = await fetch(`${API_BASE}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({
                prompt_key: editingPrompt.prompt_key,
                prompt_content: content,
            }),
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearToken();
                showLoginModal();
                return;
            }
            throw new Error('Fehler beim Speichern');
        }

        const result = await response.json();
        showToast(`Prompt gespeichert (Version ${result.version})`);

        // Update local data
        const index = allPrompts.findIndex(p => p.prompt_key === editingPrompt.prompt_key);
        if (index !== -1) {
            allPrompts[index].prompt_content = content;
            allPrompts[index].version = result.version;
        }

        setTimeout(() => {
            closeEditor();
            renderPrompts();
        }, 1000);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Speichern';
    }
}

// Reload prompts
async function reloadPrompts() {
    const token = getToken();
    if (!token) {
        showLoginModal();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/reload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
        });

        if (!response.ok) {
            if (response.status === 401) {
                clearToken();
                showLoginModal();
                return;
            }
            throw new Error('Fehler beim Neuladen');
        }

        const result = await response.json();
        showToast(`${result.count} Prompts neu geladen`);
        await loadPrompts();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Login/Logout
function showLoginModal() {
    document.getElementById('passwordModal').classList.remove('hidden');
    document.getElementById('mainContent').classList.add('hidden');
}

function hideLoginModal() {
    document.getElementById('passwordModal').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
}

function logout() {
    clearToken();
    showLoginModal();
    allPrompts = [];
    document.getElementById('promptsContainer').innerHTML = '';
}

// Event Listeners
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const password = document.getElementById('passwordInput').value;
    const errorEl = document.getElementById('passwordError');
    const btn = document.getElementById('loginBtn');

    errorEl.classList.add('hidden');
    btn.disabled = true;
    btn.textContent = 'Authentifiziere...';

    try {
        const response = await authenticate(password);
        saveToken(response.token, response.expires_in);
        hideLoginModal();
        await loadPrompts();
        document.getElementById('passwordInput').value = '';
        showToast('Erfolgreich eingeloggt');
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Einloggen';
    }
});

document.getElementById('logoutBtn').addEventListener('click', logout);
document.getElementById('reloadBtn').addEventListener('click', reloadPrompts);
document.getElementById('editorCloseBtn').addEventListener('click', closeEditor);
document.getElementById('editorCancelBtn').addEventListener('click', closeEditor);
document.getElementById('editorSaveBtn').addEventListener('click', savePrompt);
document.getElementById('editorTextarea').addEventListener('input', updateCharCount);

// Initialize - Always show modal first, then check token
window.addEventListener('DOMContentLoaded', () => {
    console.log('Prompts Admin initialized');

    // Always show password modal initially
    showLoginModal();

    const token = getToken();
    console.log('Token:', token ? 'exists' : 'not found');

    if (token) {
        // Token exists, try to use it
        currentToken = token;
        hideLoginModal();
        loadPrompts();
    } else {
        // No token, user must log in
        console.log('No valid token - login required');
    }
});
