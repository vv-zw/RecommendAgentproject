document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('query-input');
    const submitBtn = document.getElementById('submit-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultsContainer = document.getElementById('results-container');
    const recommendationList = document.getElementById('recommendation-list');
    const explanationPanel = document.getElementById('explanation-panel');
    const debugToggle = document.getElementById('debug-toggle');
    const debugPanel = document.getElementById('debug-panel');

    const API_URL = '/api/ai/recommend/full';

    const handleSubmit = async () => {
        const query = queryInput.value.trim();
        if (!query) {
            alert('请输入您想看的内容！');
            return;
        }

        // Show loading state
        loadingIndicator.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        submitBtn.disabled = true;

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: 1, query: query }),
            });

            if (!response.ok) {
                throw new Error(`服务器错误: ${response.statusText}`);
            }

            const result = await response.json();
            if (result.code !== 0) {
                throw new Error(result.error || '获取推荐失败');
            }

            renderResults(result.data);

        } catch (error) {
            alert(`请求失败: ${error.message}`);
        } finally {
            // Hide loading state
            loadingIndicator.classList.add('hidden');
            submitBtn.disabled = false;
        }
    };

    const renderResults = (data) => {
        // Render recommendations
        recommendationList.innerHTML = '';
        if (data.recommendations && data.recommendations.length > 0) {
            data.recommendations.forEach(movie => {
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.innerHTML = `
                    <div class="title">${movie.title}</div>
                    <div class="score">评分: ${movie.score.toFixed(2)}</div>
                `;
                recommendationList.appendChild(card);
            });
        } else {
            recommendationList.innerHTML = '<p>抱歉，没有找到匹配的电影。</p>';
        }

        // Render explanation
        explanationPanel.innerHTML = '';
        if (data.explanation && data.explanation.length > 0) {
            data.explanation.forEach(line => {
                const p = document.createElement('p');
                p.innerHTML = line; // Use innerHTML to render bold tags
                explanationPanel.appendChild(p);
            });
        }

        // Render debug trace
        debugPanel.textContent = JSON.stringify(data.debug_trace, null, 2);

        resultsContainer.classList.remove('hidden');
    };

    // Event Listeners
    submitBtn.addEventListener('click', handleSubmit);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    });

    debugToggle.addEventListener('click', () => {
        debugPanel.classList.toggle('hidden');
    });
});
