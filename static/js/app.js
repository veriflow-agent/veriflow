// static/js/app.js - Main Application Entry Point
// VeriFlow Redesign - Minimalist Theme

// ============================================
// ANALYZE HANDLER
// ============================================

async function handleAnalyze() {
    let content = htmlInput ? htmlInput.value.trim() : '';
    const url = articleUrl ? articleUrl.value.trim() : '';

    // If URL is provided but content is empty, fetch from URL first
    if (url && isValidUrl(url) && !content) {
        try {
            showUrlStatus('loading', 'Fetching article...');

            // Show progress section so SSE messages are visible during fetch
            hideAllSections();
            showSection(statusSection);
            clearProgressLog();
            addProgress('Fetching article from URL...');

            const result = await fetchArticleFromUrl(url);

            // Check if scraping failed (but we may still have credibility data)
            if (result && result.scrape_failed) {
                hideAllSections();

                // Show the scrape failure UI with reason and paste prompt
                showScrapeFailure(result);

                // Switch to text input so user can paste
                showTextInput();

                return;
            }

            content = result.content;
            if (htmlInput) htmlInput.value = content;
            showUrlStatus('success', 'Article fetched successfully', result);
        } catch (error) {
            hideAllSections();
            showUrlStatus('error', 'Failed to fetch: ' + error.message);
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

    // Mode-specific validation and processing
    const mode = AppState.currentMode;

    if (mode === 'comprehensive') {
        // Comprehensive mode handles everything
        processContent(content, 'comprehensive');

    } else if (mode === 'llm-output') {
        const links = hasHTMLLinks(content);

        if (!links) {
            AppState.pendingContent = content;
            showPlainTextModal();
            return;
        }

        processContent(content, 'html');

    } else if (mode === 'text-factcheck') {
        processContent(content, 'text');

    } else if (mode === 'key-claims') {
        processContent(content, 'key-claims');

    } else if (mode === 'bias-analysis') {
        processContent(content, 'bias');

    } else if (mode === 'lie-detection') {
        processContent(content, 'lie-detection');

    } else if (mode === 'manipulation') {
        processContent(content, 'manipulation');
    }
}

// ============================================
// PROCESS CONTENT
// ============================================

async function processContent(content, type) {
    AppState.closeAllStreams();

    setLoadingState(true);
    if (stopBtn) stopBtn.disabled = false;
    hideAllSections();
    showSection(statusSection);
    clearProgressLog();

    // Clear all results
    AppState.clearResults();

    try {
        switch (type) {
            case 'comprehensive':
                addProgress('Starting comprehensive analysis...');
                await runComprehensiveAnalysis(content);
                break;

            case 'html':
                addProgress('Starting LLM interpretation verification...');
                await runLLMVerification(content);
                break;

            case 'text':
                addProgress('Starting web search fact-checking...');
                await runFactCheck(content);
                break;

            case 'key-claims':
                addProgress('Starting key claims analysis...');
                await runKeyClaimsCheck(content);
                break;

            case 'bias':
                addProgress('Starting bias analysis...');
                await runBiasCheck(content);
                break;

            case 'lie-detection':
                addProgress('Starting deception detection...');
                await runLieDetection(content);
                break;

            case 'manipulation':
                addProgress('Starting manipulation analysis...');
                await runManipulationCheck(content);
                break;
        }

        displayCombinedResults(type);

    } catch (error) {
        console.error('Error during analysis:', error);

        if (!error.message.includes('cancelled') && !error.message.includes('stopped')) {
            showError(error.message || 'An unexpected error occurred. Please try again.');
        }
    } finally {
        setLoadingState(false);
        if (stopBtn) stopBtn.disabled = true;
    }
}

// ============================================
// DISPLAY COMBINED RESULTS
// ============================================

function displayCombinedResults(type) {
    hideAllSections();
    showSection(resultsSection);

    // Hide all result tabs first
    if (factCheckTab) factCheckTab.style.display = 'none';
    if (keyClaimsTab) keyClaimsTab.style.display = 'none';
    if (biasAnalysisTab) biasAnalysisTab.style.display = 'none';
    if (lieDetectionTab) lieDetectionTab.style.display = 'none';
    if (manipulationTab) manipulationTab.style.display = 'none';
    if (comprehensiveTab) comprehensiveTab.style.display = 'none';

    switch (type) {
        case 'comprehensive':
            if (comprehensiveTab) comprehensiveTab.style.display = 'block';
            if (AppState.currentComprehensiveResults) {
                renderComprehensiveResults(AppState.currentComprehensiveResults);
            }
            switchResultTab('comprehensive');
            break;

        case 'html':
        case 'text':
            if (factCheckTab) factCheckTab.style.display = 'block';
            displayVerificationResults();
            switchResultTab('fact-check');
            break;

        case 'key-claims':
            if (keyClaimsTab) keyClaimsTab.style.display = 'block';
            displayKeyClaimsResults();
            switchResultTab('key-claims');
            break;

        case 'bias':
            if (biasAnalysisTab) biasAnalysisTab.style.display = 'block';
            displayBiasResults();
            switchResultTab('bias-analysis');
            break;

        case 'lie-detection':
            if (lieDetectionTab) lieDetectionTab.style.display = 'block';
            displayLieDetectionResults();
            switchResultTab('lie-detection');
            break;

        case 'manipulation':
            if (manipulationTab) manipulationTab.style.display = 'block';
            displayManipulationResults();
            switchResultTab('manipulation');
            break;
    }
}

// ============================================
// EXPORT RESULTS
// ============================================

function exportResults() {
    const mode = AppState.currentMode;
    let data = null;
    let filename = 'veriflow-results';

    switch (mode) {
        case 'comprehensive':
            data = AppState.currentComprehensiveResults;
            filename = 'veriflow-comprehensive';
            break;
        case 'llm-output':
        case 'text-factcheck':
            data = AppState.currentLLMVerificationResults || AppState.currentFactCheckResults;
            filename = 'veriflow-factcheck';
            break;
        case 'key-claims':
            data = AppState.currentKeyClaimsResults;
            filename = 'veriflow-keyclaims';
            break;
        case 'bias-analysis':
            data = AppState.currentBiasResults;
            filename = 'veriflow-bias';
            break;
        case 'lie-detection':
            data = AppState.currentLieDetectionResults;
            filename = 'veriflow-deception';
            break;
        case 'manipulation':
            data = AppState.currentManipulationResults;
            filename = 'veriflow-manipulation';
            break;
    }

    if (data) {
        const timestamp = new Date().toISOString().slice(0, 10);
        downloadAsJson(data, `${filename}-${timestamp}.json`);
    } else {
        console.warn('No results to export');
    }
}

// ============================================
// COMPREHENSIVE ANALYSIS
// ============================================

async function runComprehensiveAnalysis(content) {
    try {
        addProgress('Initiating comprehensive analysis pipeline...');

        const response = await fetch('/api/comprehensive-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: content,
                input_type: 'text'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Comprehensive analysis failed to start');
        }

        const data = await response.json();

        // Store job ID
        AppState.currentJobIds.comprehensive = data.job_id;

        addProgress('Stage 1: Pre-analysis starting...');

        // Stream progress
        await streamComprehensiveProgress(data.job_id);

    } catch (error) {
        console.error('Comprehensive analysis error:', error);
        addProgress(`Analysis failed: ${error.message}`, 'error');
        throw error;
    }
}

async function streamComprehensiveProgress(jobId) {
    return new Promise((resolve, reject) => {
        const eventSource = new EventSource(`/api/job/${jobId}/stream`);
        let settled = false;  // Prevent double resolve/reject

        // Store for cleanup
        AppState.activeEventSources.push(eventSource);

        function settleWith(result) {
            if (settled) return;
            settled = true;
            eventSource.close();
            resolve(result);
        }

        function settleError(err) {
            if (settled) return;
            settled = true;
            eventSource.close();
            reject(err);
        }

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Handle heartbeat
                if (data.heartbeat) return;

                // Extract details (stage and partial_result are nested inside details)
                const details = data.details || {};

                // Handle progress updates with stage info
                if (details.stage) {
                    const stageMessages = {
                        'content_classification': 'Classifying content type...',
                        'source_verification': 'Verifying source credibility...',
                        'author_research': 'Researching author...',
                        'mode_routing': 'Selecting analysis modes...',
                        'mode_execution': 'Running selected modes...',
                        'synthesis': 'Synthesizing final report...'
                    };
                    addProgress(stageMessages[details.stage] || data.message || `Stage: ${details.stage}`);
                }

                if (data.message && !details.stage) {
                    addProgress(data.message);
                }

                // Handle partial results (for progressive UI updates)
                if (details.partial_result) {
                    updateComprehensivePartialResults(details.partial_result);
                }

                // Handle completion
                if (data.status === 'completed') {
                    if (data.result) {
                        // Result included in SSE event -- use it directly
                        AppState.currentComprehensiveResults = data.result;
                        addProgress('Comprehensive analysis complete!');
                        settleWith(data.result);
                    } else {
                        // Result missing (e.g. SSE reconnect sent status without result)
                        // Fetch full result from the job endpoint
                        addProgress('Fetching results...');
                        fetch(`/api/job/${jobId}`)
                            .then(r => r.json())
                            .then(job => {
                                if (job.result) {
                                    AppState.currentComprehensiveResults = job.result;
                                    addProgress('Comprehensive analysis complete!');
                                    settleWith(job.result);
                                } else {
                                    settleError(new Error('Analysis completed but results unavailable'));
                                }
                            })
                            .catch(err => settleError(new Error('Failed to fetch results: ' + err.message)));
                    }
                }

                // Handle failure
                if (data.status === 'failed') {
                    settleError(new Error(data.error || 'Analysis failed'));
                }

            } catch (e) {
                console.error('Error parsing SSE data:', e);
            }
        };

        eventSource.onerror = (error) => {
            if (settled) return;  // Already handled completion
            console.error('SSE error:', error);
            eventSource.close();

            // Check if job completed despite stream error
            fetch(`/api/job/${jobId}`)
                .then(r => r.json())
                .then(job => {
                    if (job.status === 'completed' && job.result) {
                        AppState.currentComprehensiveResults = job.result;
                        settleWith(job.result);
                    } else if (job.status === 'completed') {
                        settleError(new Error('Analysis completed but results unavailable'));
                    } else if (job.status === 'failed') {
                        settleError(new Error(job.error || 'Analysis failed'));
                    } else {
                        settleError(new Error('Connection lost during analysis'));
                    }
                })
                .catch(() => settleError(new Error('Connection lost')));
        };
    });
}

function updateComprehensivePartialResults(partial) {
    // Show comprehensive results panel progressively during analysis
    const panel = document.getElementById('comprehensiveResults');
    if (panel) panel.style.display = 'block';

    // Also make sure the results section is visible
    if (resultsSection) showSection(resultsSection);

    // Update UI progressively as stages complete
    if (partial.content_classification) {
        renderContentClassification(partial.content_classification);
    }
    if (partial.source_verification) {
        renderSourceCredibility(partial.source_verification);
    }
    if (partial.mode_routing) {
        renderModeRouting(partial.mode_routing);
    }
}

// ============================================
// EVENT LISTENERS
// ============================================

function initEventListeners() {
    // Mode card selection
    modeCards.forEach(card => {
        card.addEventListener('click', () => {
            if (card.classList.contains('disabled')) return;
            switchMode(card.dataset.mode);
        });
    });

    // Analyze button
    if (checkBtn) {
        checkBtn.addEventListener('click', handleAnalyze);
    }

    // Clear button
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (htmlInput) htmlInput.value = '';
            if (publicationUrl) publicationUrl.value = '';
            clearUrlInput();
            hideContentFormatIndicator();
            hideAllSections();
            AppState.clearResults();
        });
    }

    // Stop button
    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            AppState.closeAllStreams();
            addProgress('Analysis stopped by user', 'warning');
            setLoadingState(false);
            stopBtn.disabled = true;
        });
    }

    // New check button
    if (newCheckBtn) {
        newCheckBtn.addEventListener('click', () => {
            hideAllSections();
            if (htmlInput) htmlInput.value = '';
            if (publicationUrl) publicationUrl.value = '';
            clearUrlInput();
            hideContentFormatIndicator();
            AppState.clearResults();
        });
    }

    // Retry button
    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            hideAllSections();
            if (htmlInput && htmlInput.value.trim()) {
                handleAnalyze();
            }
        });
    }

    // Export button
    if (exportBtn) {
        exportBtn.addEventListener('click', exportResults);
    }

    // Result tab switching
    const resultTabs = [
        { tab: factCheckTab, name: 'fact-check' },
        { tab: keyClaimsTab, name: 'key-claims' },
        { tab: biasAnalysisTab, name: 'bias-analysis' },
        { tab: lieDetectionTab, name: 'lie-detection' },
        { tab: manipulationTab, name: 'manipulation' },
        { tab: comprehensiveTab, name: 'comprehensive' }
    ];

    resultTabs.forEach(({ tab, name }) => {
        if (tab) {
            tab.addEventListener('click', () => switchResultTab(name));
        }
    });

    // Content input change detection (for LLM output mode)
    if (htmlInput) {
        htmlInput.addEventListener('input', debounce(() => {
            if (AppState.currentMode === 'llm-output') {
                const content = htmlInput.value;
                if (content.length > 50) {
                    const linkCount = countLinks(content);
                    showContentFormatIndicator(linkCount > 0, linkCount);
                } else {
                    hideContentFormatIndicator();
                }
            }
        }, 500));
    }
}

// ============================================
// URL INPUT LISTENERS
// ============================================

function initUrlInputListeners() {
    // Toggle URL/Text input
    if (toggleUrlBtn) {
        toggleUrlBtn.addEventListener('click', () => {
            const isUrlVisible = urlInputContainer && urlInputContainer.style.display !== 'none';

            if (isUrlVisible) {
                showTextInput();
            } else {
                showUrlInput();
            }
        });
    }

    // Fetch URL button
    if (fetchUrlBtn && articleUrl) {
        fetchUrlBtn.addEventListener('click', async () => {
            const url = articleUrl.value.trim();

            if (!url) {
                showUrlStatus('error', 'Please enter a URL');
                return;
            }

            if (!isValidUrl(url)) {
                showUrlStatus('error', 'Please enter a valid URL');
                return;
            }

            try {
                showUrlStatus('loading', 'Fetching article...');

                // Show progress section so SSE messages are visible during fetch
                hideAllSections();
                showSection(statusSection);
                clearProgressLog();
                addProgress('Fetching article from URL...');

                const result = await fetchArticleFromUrl(url);

                // Hide progress section after fetch completes
                hideAllSections();

                // Check if scraping failed
                if (result && result.scrape_failed) {
                    // Show the scrape failure UI with reason and paste prompt
                    showScrapeFailure(result);

                    // Switch to text view so user can paste
                    showTextInput();

                    return;
                }

                if (htmlInput) {
                    htmlInput.value = result.content;
                }

                showUrlStatus('success', `Fetched: ${result.title || result.domain}`, result);

                // Show the metadata panel
                showArticleMetadata(result);

                // Switch to text view to show content
                showTextInput();

            } catch (error) {
                hideAllSections();
                showUrlStatus('error', 'Failed to fetch: ' + error.message);
            }
        });

        // Enter key in URL input
        articleUrl.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                fetchUrlBtn.click();
            }
        });
    }
}

// ============================================
// INITIALIZATION
// ============================================

function init() {
    initEventListeners();
    initUrlInputListeners();
    initModalListeners();
    initBiasModelTabs();
    initManipulationTabs();

    // Set initial mode AND activate the mode card
    updatePlaceholder(AppState.currentMode);
    switchMode(AppState.currentMode);

    console.log('VeriFlow initialized');
    console.log('Modules: config, utils, ui, modal, api, renderers');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}