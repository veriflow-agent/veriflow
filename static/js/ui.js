// static/js/ui.js - UI State Management
// VeriFlow Redesign - Minimalist Theme

// ============================================
// LOADING STATE
// ============================================

function setLoadingState(isLoading) {
    if (checkBtn) checkBtn.disabled = isLoading;
    if (clearBtn) clearBtn.disabled = isLoading;
    if (htmlInput) htmlInput.disabled = isLoading;
    if (stopBtn) stopBtn.style.display = isLoading ? 'inline-flex' : 'none';
}

// ============================================
// SECTION VISIBILITY
// ============================================

function hideAllSections() {
    if (statusSection) statusSection.style.display = 'none';
    if (resultsSection) resultsSection.style.display = 'none';
    if (errorSection) errorSection.style.display = 'none';
}

function showSection(section) {
    if (section) section.style.display = 'block';
}

function showError(message) {
    hideAllSections();
    showSection(errorSection);
    const errorMsg = document.getElementById('errorMessage');
    if (errorMsg) errorMsg.textContent = message;
}

// ============================================
// PROGRESS LOG
// ============================================

function clearProgressLog() {
    if (progressLog) progressLog.innerHTML = '';
}

function addProgress(message, type = 'info') {
    if (!progressLog) return;
    
    const entry = document.createElement('div');
    entry.className = `progress-item ${type}`;
    
    // Remove emoji prefixes for cleaner look (optional - keep for now for clarity)
    entry.textContent = message;
    
    progressLog.appendChild(entry);
    progressLog.scrollTop = progressLog.scrollHeight;
}

// ============================================
// CONTENT FORMAT INDICATOR
// ============================================

function showContentFormatIndicator(hasLinks, linkCount) {
    if (!contentFormatIndicator) return;
    
    const formatIcon = contentFormatIndicator.querySelector('.format-icon');
    const formatText = contentFormatIndicator.querySelector('.format-text');

    if (hasLinks) {
        if (formatIcon) formatIcon.textContent = '✓';
        if (formatText) formatText.textContent = `Detected ${linkCount} source link${linkCount !== 1 ? 's' : ''}`;
        contentFormatIndicator.className = 'content-format-indicator valid';
    } else {
        if (formatIcon) formatIcon.textContent = '!';
        if (formatText) formatText.textContent = 'No source links detected';
        contentFormatIndicator.className = 'content-format-indicator warning';
    }

    contentFormatIndicator.style.display = 'flex';
}

function hideContentFormatIndicator() {
    if (contentFormatIndicator) {
        contentFormatIndicator.style.display = 'none';
    }
}

// ============================================
// MODE SWITCHING
// ============================================

function switchMode(mode) {
    AppState.currentMode = mode;

    // Update card styling
    modeCards.forEach(card => {
        card.classList.toggle('active', card.dataset.mode === mode);
    });

    // Update placeholder text
    updatePlaceholder(mode);

    // Hide content format indicator when switching modes
    hideContentFormatIndicator();

    // Hide URL toggle button for LLM output mode (copy-paste only)
    if (toggleUrlBtn) {
        toggleUrlBtn.style.display = mode === 'llm-output' ? 'none' : '';
    }

    // Ensure text input is shown when switching modes (reset to default)
    showTextInput();

    console.log('Mode switched to:', mode);
}

function updatePlaceholder(mode) {
    if (!htmlInput) return;
    
    const placeholders = {
        'key-claims': 'Paste the article or text you want to analyze...',
        'bias-analysis': 'Paste the article or text to analyze for bias...',
        'lie-detection': 'Paste the text to analyze for deception markers...',
        'manipulation': 'Paste the article to check for manipulation...',
        'text-factcheck': 'Paste the article or text you want to fact-check...',
        'llm-output': 'Paste AI-generated content with source links (from ChatGPT, Perplexity, etc.)...'
    };
    
    htmlInput.placeholder = placeholders[mode] || 'Paste the article or text you want to analyze...';
}

// ============================================
// RESULTS TAB SWITCHING
// ============================================

function switchResultTab(tabName) {
    // Define tab mappings
    const tabMappings = {
        'fact-check': { tab: factCheckTab, panel: factCheckResults },
        'key-claims': { tab: keyClaimsTab, panel: keyClaimsResults },
        'bias-analysis': { tab: biasAnalysisTab, panel: biasAnalysisResults },
        'lie-detection': { tab: lieDetectionTab, panel: lieDetectionResults },
        'manipulation': { tab: manipulationTab, panel: manipulationResults }
    };

    // Hide all panels and deactivate all tabs
    Object.values(tabMappings).forEach(({ tab, panel }) => {
        if (tab) tab.classList.remove('active');
        if (panel) {
            panel.style.display = 'none';
            panel.classList.remove('active');
        }
    });

    // Show selected tab and panel
    const selected = tabMappings[tabName];
    if (selected) {
        if (selected.tab) selected.tab.classList.add('active');
        if (selected.panel) {
            selected.panel.style.display = 'block';
            selected.panel.classList.add('active');
        }
    }
}

// ============================================
// URL INPUT HANDLING
// ============================================

function showUrlInput() {
    if (urlInputContainer) urlInputContainer.style.display = 'block';
    if (textInputContainer) textInputContainer.style.display = 'none';
    updateToggleButton(true);
}

function showTextInput() {
    if (urlInputContainer) urlInputContainer.style.display = 'none';
    if (textInputContainer) textInputContainer.style.display = 'block';
    updateToggleButton(false);
}

function updateToggleButton(isUrlMode) {
    if (!toggleUrlBtn) return;
    
    if (isUrlMode) {
        toggleUrlBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Paste text instead
        `;
    } else {
        toggleUrlBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
            Paste URL instead
        `;
    }
}

function showUrlStatus(type, message, details = null) {
    if (!urlFetchStatus) return;
    
    urlFetchStatus.style.display = 'flex';
    urlFetchStatus.className = `url-fetch-status ${type}`;

    let html = `
        <span class="status-icon">${getStatusIcon(type)}</span>
        <span class="status-text">${message}</span>
    `;

    // Add credibility badge if available
    if (details && details.credibility) {
        const tierColor = getTierColor(details.credibility.tier);
        html += `
            <span class="credibility-badge" style="background: ${tierColor}">
                Tier ${details.credibility.tier}
            </span>
        `;
    }

    urlFetchStatus.innerHTML = html;
}

function hideUrlStatus() {
    if (urlFetchStatus) {
        urlFetchStatus.style.display = 'none';
    }
}

function getStatusIcon(type) {
    const icons = {
        loading: '⏳',
        success: '✓',
        error: '✕',
        info: 'i'
    };
    return icons[type] || '•';
}

function getTierColor(tier) {
    const colors = {
        1: '#6B9B6B',  // Green
        2: '#8AAF6B',  // Light green
        3: '#E8B84A',  // Yellow
        4: '#E89B4A',  // Orange
        5: '#F06449'   // Red
    };
    return colors[tier] || '#9A9A9A';
}

function clearUrlInput() {
    if (articleUrl) articleUrl.value = '';
    hideUrlStatus();
    setLastFetchedArticle(null);
}

// ============================================
// BIAS MODEL TABS
// ============================================

function initBiasModelTabs() {
    if (!modelTabs) return;
    
    modelTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const model = tab.dataset.model;
            
            // Update tab styling
            modelTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show/hide analysis panels
            const gptAnalysis = document.getElementById('gptAnalysis');
            const claudeAnalysis = document.getElementById('claudeAnalysis');
            const consensusAnalysis = document.getElementById('consensusAnalysis');
            
            if (gptAnalysis) gptAnalysis.style.display = model === 'gpt' ? 'block' : 'none';
            if (claudeAnalysis) claudeAnalysis.style.display = model === 'claude' ? 'block' : 'none';
            if (consensusAnalysis) consensusAnalysis.style.display = model === 'consensus' ? 'block' : 'none';
        });
    });
}

// ============================================
// MANIPULATION INNER TABS
// ============================================

function initManipulationTabs() {
    const manipInnerTabs = document.querySelectorAll('.manip-inner-tab');
    
    manipInnerTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.manipTab;
            
            // Update tab styling
            manipInnerTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Show/hide content
            const summaryTab = document.getElementById('manipSummaryTab');
            const factsTab = document.getElementById('manipFactsTab');
            
            if (summaryTab) summaryTab.style.display = tabName === 'summary' ? 'block' : 'none';
            if (factsTab) factsTab.style.display = tabName === 'facts' ? 'block' : 'none';
        });
    });
}
