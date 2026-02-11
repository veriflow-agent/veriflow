// static/js/app.js - Main Application Entry Point
// VeriFlow Redesign - Minimalist Theme
// REWRITTEN: Comprehensive mode uses SSE for progress only, HTTP fetch for results

// ============================================
// ANALYZE HANDLER
// ============================================

async function handleAnalyze() {
    var content = htmlInput ? htmlInput.value.trim() : '';
    var url = articleUrl ? articleUrl.value.trim() : '';

    // If URL is provided but content is empty, fetch from URL first
    if (url && isValidUrl(url) && !content) {
        try {
            showUrlStatus('loading', 'Fetching article...');

            // Show progress section so SSE messages are visible during fetch
            hideAllSections();
            showSection(statusSection);
            clearProgressLog();
            addProgress('Fetching article from URL...');

            var result = await fetchArticleFromUrl(url);

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

    var mode = AppState.currentMode;

    if (mode === 'comprehensive') {
        processContent(content, 'comprehensive');

    } else if (mode === 'llm-output') {
        var links = hasHTMLLinks(content);

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
                console.log('[Comprehensive] Rendering final results:', {
                    hasClassification: !!AppState.currentComprehensiveResults.content_classification,
                    hasSourceVerification: !!AppState.currentComprehensiveResults.source_verification,
                    hasModeRouting: !!AppState.currentComprehensiveResults.mode_routing,
                    hasModeReports: !!AppState.currentComprehensiveResults.mode_reports,
                    modeReportKeys: AppState.currentComprehensiveResults.mode_reports ? Object.keys(AppState.currentComprehensiveResults.mode_reports) : [],
                    hasSynthesis: !!AppState.currentComprehensiveResults.synthesis_report,
                    sessionId: AppState.currentComprehensiveResults.session_id,
                    processingTime: AppState.currentComprehensiveResults.processing_time
                });
                renderComprehensiveResults(AppState.currentComprehensiveResults);
            } else {
                console.warn('[Comprehensive] No results to render!');
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
    var mode = AppState.currentMode;
    var data = null;
    var filename = 'veriflow-results';

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
        var timestamp = new Date().toISOString().slice(0, 10);
        downloadAsJson(data, filename + '-' + timestamp + '.json');
    } else {
        console.warn('No results to export');
    }
}

// ============================================
// COMPREHENSIVE ANALYSIS (REWRITTEN)
// ============================================

/**
 * Start comprehensive analysis and wait for completion.
 *
 * Flow:
 * 1. POST to /api/comprehensive-analysis -> get job_id
 * 2. Open SSE stream for progress messages only (no result data)
 * 3. When SSE signals done, fetch full result via HTTP GET
 * 4. Store result in AppState
 */
async function runComprehensiveAnalysis(content) {
    try {
        addProgress('Initiating comprehensive analysis pipeline...');

        var sourceUrl = articleUrl ? articleUrl.value.trim() : '';

        var response = await fetch('/api/comprehensive-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: content,
                source_url: sourceUrl || undefined,
                input_type: 'text'
            })
        });

        if (!response.ok) {
            var errBody = await response.json().catch(function() { return {}; });
            throw new Error(errBody.error || 'Comprehensive analysis failed to start');
        }

        var data = await response.json();
        var jobId = data.job_id;

        // Store job ID
        AppState.currentJobIds.comprehensive = jobId;

        addProgress('Analysis started (job: ' + jobId.slice(0, 8) + '...)');

        // Step 1: Stream progress messages via SSE
        await streamComprehensiveProgress(jobId);

        // Step 2: Fetch the full result via HTTP
        addProgress('Loading results...');
        var result = await fetchComprehensiveResult(jobId);

        // Step 3: Store the result
        AppState.currentComprehensiveResults = result;
        addProgress('Comprehensive analysis complete!');

    } catch (error) {
        console.error('[Comprehensive] Analysis error:', error);
        addProgress('Analysis failed: ' + error.message, 'error');
        throw error;
    }
}

/**
 * Stream progress messages via SSE.
 * This ONLY handles progress text -- no result data.
 * Resolves when the backend signals completion.
 * Rejects on error or if the connection drops and the job hasn't finished.
 */
function streamComprehensiveProgress(jobId) {
    return new Promise(function(resolve, reject) {
        var eventSource = new EventSource('/api/job/' + jobId + '/stream');
        var settled = false;

        // Store for cleanup
        AppState.activeEventSources.push(eventSource);

        function settle(fn, arg) {
            if (settled) return;
            settled = true;
            eventSource.close();
            fn(arg);
        }

        eventSource.onmessage = function(event) {
            try {
                var data = JSON.parse(event.data);

                // Heartbeat -- ignore
                if (data.heartbeat) return;

                // Progress message -- show in log
                if (data.message) {
                    addProgress(data.message);
                }

                // Completion signal
                if (data.status === 'completed') {
                    // We do NOT use data.result here.
                    // The result will be fetched via HTTP in runComprehensiveAnalysis.
                    settle(resolve);
                    return;
                }

                // Failure signal
                if (data.status === 'failed') {
                    settle(reject, new Error(data.error || 'Analysis failed'));
                    return;
                }

                // Cancelled
                if (data.status === 'cancelled') {
                    settle(reject, new Error('Analysis cancelled'));
                    return;
                }

            } catch (e) {
                console.error('[Comprehensive] Error parsing SSE:', e);
            }
        };

        eventSource.onerror = function() {
            if (settled) return;

            console.log('[Comprehensive] SSE connection lost, checking job status...');
            eventSource.close();

            // Connection dropped -- check if job finished despite the drop
            fetch('/api/job/' + jobId)
                .then(function(r) { return r.json(); })
                .then(function(job) {
                    if (job.status === 'completed') {
                        // Job finished, SSE just dropped. We'll fetch result in the caller.
                        settle(resolve);
                    } else if (job.status === 'failed') {
                        settle(reject, new Error(job.error || 'Analysis failed'));
                    } else {
                        // Job still running but SSE died.
                        // Start polling instead of giving up.
                        console.log('[Comprehensive] Job still running, switching to polling...');
                        pollForCompletion(jobId)
                            .then(function() { settle(resolve); })
                            .catch(function(err) { settle(reject, err); });
                    }
                })
                .catch(function() {
                    settle(reject, new Error('Connection lost during analysis'));
                });
        };
    });
}

/**
 * Poll job status when SSE connection drops mid-analysis.
 * Checks every 5 seconds, up to 60 attempts (5 minutes).
 */
function pollForCompletion(jobId) {
    return new Promise(function(resolve, reject) {
        var attempts = 0;
        var maxAttempts = 60;
        var interval = 5000;

        function check() {
            attempts++;
            fetch('/api/job/' + jobId)
                .then(function(r) { return r.json(); })
                .then(function(job) {
                    if (job.status === 'completed') {
                        resolve();
                    } else if (job.status === 'failed') {
                        reject(new Error(job.error || 'Analysis failed'));
                    } else if (job.status === 'cancelled') {
                        reject(new Error('Analysis cancelled'));
                    } else if (attempts >= maxAttempts) {
                        reject(new Error('Analysis timed out'));
                    } else {
                        // Show latest progress if available
                        var log = job.progress_log || [];
                        if (log.length > 0) {
                            var latest = log[log.length - 1];
                            if (latest.message) {
                                addProgress(latest.message);
                            }
                        }
                        setTimeout(check, interval);
                    }
                })
                .catch(function() {
                    if (attempts >= maxAttempts) {
                        reject(new Error('Connection lost'));
                    } else {
                        setTimeout(check, interval);
                    }
                });
        }

        check();
    });
}

/**
 * Fetch the full result from the job endpoint via HTTP.
 * Retries up to 3 times with 2-second delays.
 * This is the ONLY path for getting comprehensive results.
 */
function fetchComprehensiveResult(jobId) {
    var maxAttempts = 4;
    var retryDelay = 2000;

    function attempt(n) {
        return fetch('/api/job/' + jobId)
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Job fetch failed: HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function(job) {
                console.log('[Comprehensive] Fetch attempt ' + n + ':', {
                    status: job.status,
                    hasResult: !!job.result,
                    resultKeys: job.result ? Object.keys(job.result) : [],
                    hasSynthesis: !!(job.result && job.result.synthesis_report)
                });

                if (job.result) {
                    return job.result;
                }

                // Result not ready yet (maybe complete_job hasn't finished storing)
                if (n < maxAttempts) {
                    console.log('[Comprehensive] Result not ready, retry in ' + retryDelay + 'ms');
                    return new Promise(function(resolve) {
                        setTimeout(function() { resolve(attempt(n + 1)); }, retryDelay);
                    });
                }

                throw new Error('Analysis completed but results unavailable after retries');
            })
            .catch(function(err) {
                if (n < maxAttempts) {
                    console.log('[Comprehensive] Fetch error, retry: ' + err.message);
                    return new Promise(function(resolve) {
                        setTimeout(function() { resolve(attempt(n + 1)); }, retryDelay);
                    });
                }
                throw err;
            });
    }

    return attempt(1);
}


// ============================================
// EVENT LISTENERS
// ============================================

function initEventListeners() {
    // Mode card selection
    modeCards.forEach(function(card) {
        card.addEventListener('click', function() {
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
        clearBtn.addEventListener('click', function() {
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
        stopBtn.addEventListener('click', function() {
            AppState.closeAllStreams();
            addProgress('Analysis stopped by user', 'warning');
            setLoadingState(false);
            stopBtn.disabled = true;
        });
    }

    // New check button
    if (newCheckBtn) {
        newCheckBtn.addEventListener('click', function() {
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
        retryBtn.addEventListener('click', function() {
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
    var resultTabs = [
        { tab: factCheckTab, name: 'fact-check' },
        { tab: keyClaimsTab, name: 'key-claims' },
        { tab: biasAnalysisTab, name: 'bias-analysis' },
        { tab: lieDetectionTab, name: 'lie-detection' },
        { tab: manipulationTab, name: 'manipulation' },
        { tab: comprehensiveTab, name: 'comprehensive' }
    ];

    resultTabs.forEach(function(item) {
        if (item.tab) {
            item.tab.addEventListener('click', function() { switchResultTab(item.name); });
        }
    });

    // Content input change detection (for LLM output mode)
    if (htmlInput) {
        htmlInput.addEventListener('input', debounce(function() {
            if (AppState.currentMode === 'llm-output') {
                var content = htmlInput.value;
                if (content.length > 50) {
                    var linkCount = countLinks(content);
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
        toggleUrlBtn.addEventListener('click', function() {
            var isUrlVisible = urlInputContainer && urlInputContainer.style.display !== 'none';

            if (isUrlVisible) {
                showTextInput();
            } else {
                showUrlInput();
            }
        });
    }

    // Fetch URL button
    if (fetchUrlBtn && articleUrl) {
        fetchUrlBtn.addEventListener('click', async function() {
            var url = articleUrl.value.trim();

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

                var result = await fetchArticleFromUrl(url);

                // Hide progress section after fetch completes
                hideAllSections();

                // Check if scraping failed
                if (result && result.scrape_failed) {
                    showScrapeFailure(result);
                    showTextInput();
                    return;
                }

                if (htmlInput) {
                    htmlInput.value = result.content;
                }

                showUrlStatus('success', 'Fetched: ' + (result.title || result.domain), result);

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
        articleUrl.addEventListener('keypress', function(e) {
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