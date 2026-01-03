// static/js/app.js - Main Application Entry Point
// This file ties together all modules and sets up event listeners

// ============================================
// URL INPUT ELEMENTS (add to config.js if you prefer)
// ============================================

const articleUrl = document.getElementById('articleUrl');
const fetchUrlBtn = document.getElementById('fetchUrlBtn');
const urlFetchStatus = document.getElementById('urlFetchStatus');

// ============================================
// URL INPUT HANDLING
// ============================================

// Validate URL format
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

// Show URL fetch status with different states
function showUrlStatus(type, message) {
    if (!urlFetchStatus) return;
    urlFetchStatus.style.display = 'flex';
    urlFetchStatus.className = `url-fetch-status ${type}`;

    const icons = {
        loading: '⏳',
        success: '✅',
        error: '❌'
    };

    urlFetchStatus.innerHTML = `
        <span class="status-icon">${icons[type] || '📄'}</span>
        <span class="status-text">${message}</span>
    `;
}

function hideUrlStatus() {
    if (urlFetchStatus) {
        urlFetchStatus.style.display = 'none';
    }
}

// Fetch article content from URL via backend
async function fetchArticleFromUrl(url) {
    showUrlStatus('loading', 'Fetching article content...');

    try {
        const response = await fetch('/api/scrape-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.message || 'Failed to fetch article');
        }

        const data = await response.json();

        if (!data.content || data.content.trim().length < 100) {
            throw new Error('Could not extract sufficient content from the URL');
        }

        // Show success with content length
        const charCount = data.content.length.toLocaleString();
        const titleInfo = data.title ? ` from "${data.title}"` : '';
        showUrlStatus('success', `Fetched ${charCount} characters${titleInfo}`);

        return {
            content: data.content,
            title: data.title,
            url: data.url
        };

    } catch (error) {
        showUrlStatus('error', error.message);
        throw error;
    }
}

// Initialize URL input event listeners
function initUrlInputListeners() {
    if (!articleUrl || !fetchUrlBtn) {
        console.log('URL input elements not found, skipping URL input initialization');
        return;
    }

    // Enable/disable fetch button based on URL validity
    articleUrl.addEventListener('input', () => {
        const url = articleUrl.value.trim();
        fetchUrlBtn.disabled = !isValidUrl(url);

        // Add visual indicator when URL is entered
        if (url && isValidUrl(url)) {
            htmlInput.classList.add('url-filled');
        } else {
            htmlInput.classList.remove('url-filled');
        }
    });

    // Clear URL styling when textarea is used directly
    htmlInput.addEventListener('input', () => {
        if (htmlInput.value.trim()) {
            htmlInput.classList.remove('url-filled');
        }
    });

    // Fetch button click handler
    fetchUrlBtn.addEventListener('click', async () => {
        const url = articleUrl.value.trim();

        if (!isValidUrl(url)) {
            showUrlStatus('error', 'Please enter a valid URL');
            return;
        }

        try {
            // Disable button and show loading state
            fetchUrlBtn.disabled = true;
            fetchUrlBtn.innerHTML = '<span class="fetch-icon">⏳</span><span class="fetch-text">Fetching...</span>';

            const result = await fetchArticleFromUrl(url);

            // Put the fetched content into the textarea
            htmlInput.value = result.content;
            htmlInput.classList.add('url-filled');

            // Trigger input event to update any format detection
            htmlInput.dispatchEvent(new Event('input'));

        } catch (error) {
            console.error('URL fetch error:', error);
            // Error already shown via showUrlStatus
        } finally {
            // Re-enable button with original text
            fetchUrlBtn.disabled = !isValidUrl(articleUrl.value.trim());
            fetchUrlBtn.innerHTML = '<span class="fetch-icon">📥</span><span class="fetch-text">Fetch</span>';
        }
    });

    // Allow Enter key to trigger fetch
    articleUrl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !fetchUrlBtn.disabled) {
            e.preventDefault();
            fetchUrlBtn.click();
        }
    });

    console.log('✅ URL input listeners initialized');
}

// Clear URL input field
function clearUrlInput() {
    if (articleUrl) {
        articleUrl.value = '';
    }
    if (fetchUrlBtn) {
        fetchUrlBtn.disabled = true;
    }
    hideUrlStatus();
    htmlInput.classList.remove('url-filled');
}

// ============================================
// ANALYZE BUTTON HANDLER
// ============================================

async function handleAnalyze() {
    let content = htmlInput.value.trim();
    const url = articleUrl ? articleUrl.value.trim() : '';

    // If URL is provided but content is empty, fetch from URL first
    if (url && isValidUrl(url) && !content) {
        try {
            addProgress('🔗 Fetching article from URL...');
            const result = await fetchArticleFromUrl(url);
            content = result.content;
            htmlInput.value = content;
        } catch (error) {
            showError('Failed to fetch article: ' + error.message);
            return;
        }
    }

    if (!content) {
        showError('Please paste some content or enter a URL to analyze.');
        return;
    }

    // Hide URL status when starting analysis
    hideUrlStatus();

    // Mode-specific validation
    if (AppState.currentMode === 'llm-output') {
        const links = hasHTMLLinks(content);

        if (!links) {
            AppState.pendingContent = content;
            showPlainTextModal();
            return;
        }

        processContent(content, 'html');

    } else if (AppState.currentMode === 'text-factcheck') {
        processContent(content, 'text');

    } else if (AppState.currentMode === 'key-claims') {
        processContent(content, 'key-claims');

    } else if (AppState.currentMode === 'bias-analysis') {
        processContent(content, 'bias');

    } else if (AppState.currentMode === 'lie-detection') {
        processContent(content, 'lie-detection');
    }
}

// ============================================
// PROCESS CONTENT
// ============================================

async function processContent(content, type) {
    AppState.closeAllStreams();

    setLoadingState(true);
    stopBtn.disabled = false;
    hideAllSections();
    showSection(statusSection);
    clearProgressLog();

    // Clear all results
    AppState.clearResults();

    try {
        if (type === 'html') {
            // LLM Output Verification Pipeline
            addProgress('🔍 Starting LLM interpretation verification...');
            await runLLMVerification(content);
        } else if (type === 'text') {
            // Web Search Fact-Checking Pipeline
            addProgress('🔍 Starting web search fact-checking...');
            await runFactCheck(content);
        } else if (type === 'key-claims') {
            // Key Claims Pipeline
            addProgress('🎯 Starting key claims analysis...');
            await runKeyClaimsCheck(content);
        } else if (type === 'bias') {
            addProgress('📊 Starting bias analysis...');
            await runBiasCheck(content);
        } else if (type === 'lie-detection') {
            addProgress('🕵️ Starting lie detection analysis...');
            await runLieDetection(content);
        }

        displayCombinedResults(type);

    } catch (error) {
        console.error('Error during analysis:', error);

        if (!error.message.includes('cancelled') && !error.message.includes('stopped')) {
            showError(error.message || 'An unexpected error occurred. Please try again.');
        }
    } finally {
        setLoadingState(false);
        stopBtn.disabled = true;
    }
}

// ============================================
// DISPLAY RESULTS ROUTER
// ============================================

function displayCombinedResults(type) {
    hideAllSections();
    showSection(resultsSection);

    // Hide ALL tabs first
    factCheckTab.style.display = 'none';
    if (keyClaimsTab) keyClaimsTab.style.display = 'none';
    biasAnalysisTab.style.display = 'none';
    lieDetectionTab.style.display = 'none';

    // Show ONLY the tab for what was just run
    switch (type) {
        case 'html':
            // LLM Output verification
            factCheckTab.style.display = 'block';
            displayVerificationResults();
            switchResultTab('fact-check');
            break;

        case 'text':
            // Web Search fact-check
            factCheckTab.style.display = 'block';
            displayVerificationResults();
            switchResultTab('fact-check');
            break;

        case 'key-claims':
            // Key Claims
            if (keyClaimsTab) keyClaimsTab.style.display = 'block';
            displayKeyClaimsResults();
            switchResultTab('key-claims');
            break;

        case 'bias':
            // Bias Analysis
            biasAnalysisTab.style.display = 'block';
            displayBiasResults();
            switchResultTab('bias-analysis');
            break;

        case 'lie-detection':
            // Lie Detection
            lieDetectionTab.style.display = 'block';
            displayLieDetectionResults();
            switchResultTab('lie-detection');
            break;

        default:
            console.error('Unknown result type:', type);
    }
}

// ============================================
// EVENT LISTENERS SETUP
// ============================================

function initEventListeners() {
    // Analyze button
    checkBtn.addEventListener('click', handleAnalyze);

    // Mode tabs
    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchMode(tab.dataset.mode);
        });
    });

    // Input validation
    htmlInput.addEventListener('input', () => {
        const content = htmlInput.value.trim();

        if (!content) {
            hideContentFormatIndicator();
            return;
        }

        // Only show format indicator for LLM output mode
        if (AppState.currentMode === 'llm-output') {
            const hasLinks = hasHTMLLinks(content);
            const linkCount = countLinks(content);
            showContentFormatIndicator(hasLinks, linkCount);
        } else {
            hideContentFormatIndicator();
        }
    });

    // Clear button
    clearBtn.addEventListener('click', () => {
        htmlInput.value = '';
        publicationUrl.value = '';
        clearUrlInput();  // NEW: Clear URL input
        hideContentFormatIndicator();
        hideAllSections();
        AppState.clearResults();
    });

    // Stop button
    stopBtn.addEventListener('click', () => {
        AppState.closeAllStreams();
        addProgress('⏹️ Analysis stopped by user', 'warning');
        setLoadingState(false);
        stopBtn.disabled = true;
    });

    // New check button
    newCheckBtn.addEventListener('click', () => {
        hideAllSections();
        htmlInput.value = '';
        publicationUrl.value = '';
        clearUrlInput();  // NEW: Clear URL input
        hideContentFormatIndicator();
        AppState.clearResults();
    });

    // Retry button
    retryBtn.addEventListener('click', () => {
        hideAllSections();
        if (htmlInput.value.trim()) {
            handleAnalyze();
        }
    });

    // Export button
    exportBtn.addEventListener('click', exportResults);
}

// ============================================
// INITIALIZATION
// ============================================

function init() {
    initEventListeners();
    initUrlInputListeners();  // NEW: Initialize URL input
    initModalListeners();
    initBiasModelTabs();

    console.log('✅ VeriFlow app initialized successfully');
    console.log('📦 Modules loaded: config, utils, ui, modal, api, renderers');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}