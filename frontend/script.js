document.addEventListener('DOMContentLoaded', () => {
    const API_URL = 'http://127.0.0.1:5000/api';
    const state = {
        token: localStorage.getItem('token'),
        userId: localStorage.getItem('userId'),
        currentPage: ''
    };

    // Page Elements
    const pages = document.querySelectorAll('.page');
    const navLinks = document.querySelectorAll('.nav-link');
    const logoutBtn = document.getElementById('logout-btn');

    // Login/Register Form Elements
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');

    // Home Page Elements
    const recommendationsGrid = document.getElementById('recommendations-grid');

    // Agent Page Elements
    const chatHistory = document.getElementById('chat-history');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const agentRecommendationsGrid = document.getElementById('agent-recommendations-grid');

    // Detail Page Elements
    const mediaDetailContent = document.getElementById('media-detail-content');

    // --- ROUTING ---
    function navigateTo(pageId, resourceId) {
        if (!state.token && pageId !== 'login-page') {
            pageId = 'login-page';
        }

        pages.forEach(page => {
            page.style.display = page.id === pageId ? 'block' : 'none';
        });
        state.currentPage = pageId;
        updateNav();

        // Fetch data for the new page
        if (pageId === 'home-page') {
            fetchHomePageData();
        } else if (pageId === 'agent-page') {
            // Clear previous results when navigating to agent page
            agentRecommendationsGrid.innerHTML = '';
        } else if (pageId === 'detail-page' && resourceId) {
            fetchDetailPageData(resourceId);
        }
    }

    function updateNav() {
        if (state.token) {
            logoutBtn.style.display = 'inline';
            navLinks.forEach(link => {
                if (link.id !== 'logout-btn') link.style.display = 'inline';
            });
        } else {
            logoutBtn.style.display = 'none';
            navLinks.forEach(link => {
                if (link.id !== 'logout-btn') link.style.display = 'none';
            });
        }
    }

    window.addEventListener('hashchange', () => {
        const hash = location.hash.substring(1);
        const [pageName, resourceId] = hash.split('/');
        const pageId = pageName + '-page';
        navigateTo(pageId, resourceId);
    });

    // --- AUTHENTICATION ---
    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.parentElement.style.display = 'none';
        registerForm.parentElement.style.display = 'block';
    });

    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.parentElement.style.display = 'none';
        loginForm.parentElement.style.display = 'block';
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;

        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await response.json();
            if (response.ok) {
                alert('Registration successful! Please log in.');
                showLoginLink.click();
            } else {
                throw new Error(data.error || 'Registration failed');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            if (response.ok) {
                state.token = data.access_token;
                state.userId = data.user_id;
                localStorage.setItem('token', state.token);
                localStorage.setItem('userId', state.userId);
                location.hash = 'home';
                navigateTo('home-page');
            } else {
                throw new Error(data.error || 'Login failed');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });

    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        state.token = null;
        state.userId = null;
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        location.hash = 'login';
        navigateTo('login-page');
    });

    // Initial load
    const initialPage = location.hash ? location.hash.substring(1) : 'home';
    const [initialPageName, initialResourceId] = initialPage.split('/');
    navigateTo(initialPageName + '-page', initialResourceId);

    // --- AGENT CHAT ---

    // --- AGENT CHAT ---
    async function handleChatSubmit() {
        const message = chatInput.value.trim();
        if (!message) return;

        appendMessageToHistory('User', message);
        chatInput.value = '';

        try {
            const response = await fetch(`${API_URL}/agent/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-access-token': state.token
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            if (response.ok) {
                appendMessageToHistory('AI', data.nl_response);
                if (data.structured_results && data.structured_results.length > 0) {
                    renderMediaGrid(agentRecommendationsGrid, data.structured_results);
                }
            } else {
                throw new Error(data.error || 'AI chat failed');
            }
        } catch (error) {
            console.error('Chat error:', error);
            appendMessageToHistory('AI', `Sorry, an error occurred: ${error.message}`);
        }
    }

    function appendMessageToHistory(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
        chatHistory.appendChild(messageElement);
        chatHistory.scrollTop = chatHistory.scrollHeight; // Auto-scroll to bottom
    }

    chatSendBtn.addEventListener('click', handleChatSubmit);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleChatSubmit();
        }
    });

    // --- PAGE DATA FETCHING ---
    async function fetchHomePageData() {
        try {
            const response = await fetch(`${API_URL}/movies?sort_by=popularity.desc&limit=10`, {
                headers: { 'x-access-token': state.token }
            });
            const data = await response.json();
            if (response.ok) {
                renderMediaGrid(recommendationsGrid, data.results);
            } else {
                throw new Error(data.error || 'Failed to fetch recommendations');
            }
        } catch (error) {
            console.error('Error fetching home page data:', error);
            recommendationsGrid.innerHTML = `<p>Error loading recommendations: ${error.message}</p>`;
        }
    }

    async function fetchDetailPageData(mediaId) {
        mediaDetailContent.innerHTML = '<p>Loading details...</p>';
        try {
            // We can try fetching from both movie and series endpoints
            // A more robust solution would be to know the media_type beforehand
            const movieResponse = await fetch(`${API_URL}/movies/${mediaId}`, {
                headers: { 'x-access-token': state.token }
            });
            if (movieResponse.ok) {
                const data = await movieResponse.json();
                renderMediaDetail(data);
                return;
            }

            const seriesResponse = await fetch(`${API_URL}/series/${mediaId}`, {
                headers: { 'x-access-token': state.token }
            });
            if (seriesResponse.ok) {
                const data = await seriesResponse.json();
                renderMediaDetail(data);
                return;
            }

            throw new Error('Media not found in movies or series.');

        } catch (error) {
            console.error('Error fetching detail page data:', error);
            mediaDetailContent.innerHTML = `<p>Error loading details: ${error.message}</p>`;
        }
    }

    // --- RENDERING ---
    function renderMediaGrid(container, items) {
        container.innerHTML = '';
        if (!items || items.length === 0) {
            container.innerHTML = '<p>No items to display.</p>';
            return;
        }

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'media-card';
            card.dataset.id = item.id;
            card.innerHTML = `
                <img src="${item.poster_url || 'https://via.placeholder.com/180x270.png?text=No+Image'}" alt="${item.title}">
                <div class="media-card-content">
                    <h3>${item.title}</h3>
                    <p>Rating: ${item.vote_average || 'N/A'}</p>
                </div>
            `;
            // Add event listener for detail view
            card.addEventListener('click', () => {
                location.hash = `detail/${item.id}`;
            });
            container.appendChild(card);
        });
    }
});
