// static/js/renderers/bias.js - Bias Analysis Rendering
// VeriFlow Redesign - Minimalist Theme

// ============================================
// DISPLAY BIAS RESULTS
// ============================================

function displayBiasResults() {
    if (!AppState.currentBiasResults || !AppState.currentBiasResults.success) {
        console.error('No bias results available');
        return;
    }

    console.log('Displaying Bias Results:', AppState.currentBiasResults);

    const data = AppState.currentBiasResults;

    // Display GPT analysis
    if (data.gpt_analysis) {
        displayModelAnalysis('gpt', data.gpt_analysis);
    }

    // Display Claude analysis
    if (data.claude_analysis) {
        displayModelAnalysis('claude', data.claude_analysis);
    }

    // Display Consensus analysis
    if (data.consensus) {
        displayConsensusAnalysis(data.consensus);
    }

    // Session info
    const sessionId = document.getElementById('biasSessionId');
    const processingTime = document.getElementById('biasProcessingTime');

    if (sessionId) sessionId.textContent = data.session_id || '-';
    if (processingTime) processingTime.textContent = Math.round(data.processing_time || 0) + 's';

    // R2 link
    const r2Link = document.getElementById('biasR2Link');
    const r2Sep = document.getElementById('biasR2Sep');

    if (r2Link && r2Sep) {
        if (data.r2_upload && data.r2_upload.combined_url) {
            r2Link.href = data.r2_upload.combined_url;
            r2Link.style.display = 'inline';
            r2Sep.style.display = 'inline';
        } else {
            r2Link.style.display = 'none';
            r2Sep.style.display = 'none';
        }
    }
}

// ============================================
// DISPLAY MODEL ANALYSIS
// ============================================

function displayModelAnalysis(model, analysis) {
    const prefix = model === 'gpt' ? 'gpt' : 'claude';

    // Score
    const scoreEl = document.getElementById(`${prefix}BiasScore`);
    if (scoreEl) {
        const score = analysis.bias_score || 0;
        scoreEl.textContent = score.toFixed(1);
        scoreEl.className = `bias-score-value ${getBiasScoreClass(score)}`;
    }

    // Direction
    const directionEl = document.getElementById(`${prefix}BiasDirection`);
    if (directionEl) {
        directionEl.textContent = analysis.bias_direction || 'Unknown';
    }

    // Justification
    const justificationEl = document.getElementById(`${prefix}BiasJustification`);
    if (justificationEl) {
        justificationEl.textContent = analysis.summary || analysis.justification || '';
    }

    // Details container
    const detailsEl = document.getElementById(`${prefix}BiasDetails`);
    if (detailsEl) {
        detailsEl.innerHTML = '';

        // Add bias indicators
        if (analysis.bias_indicators && analysis.bias_indicators.length > 0) {
            const indicatorsSection = createBiasSection('Bias Indicators', analysis.bias_indicators);
            detailsEl.appendChild(indicatorsSection);
        }

        // Add language analysis
        if (analysis.language_analysis) {
            const langSection = createLanguageSection(analysis.language_analysis);
            detailsEl.appendChild(langSection);
        }

        // Add framing analysis
        if (analysis.framing_analysis) {
            const framingSection = createFramingSection(analysis.framing_analysis);
            detailsEl.appendChild(framingSection);
        }
    }
}

// ============================================
// DISPLAY CONSENSUS ANALYSIS
// ============================================

function displayConsensusAnalysis(consensus) {
    // Score
    const scoreEl = document.getElementById('consensusBiasScore');
    if (scoreEl) {
        const score = consensus.average_score || 0;
        scoreEl.textContent = score.toFixed(1);
        scoreEl.className = `bias-score-value ${getBiasScoreClass(score)}`;
    }

    // Direction
    const directionEl = document.getElementById('consensusBiasDirection');
    if (directionEl) {
        directionEl.textContent = consensus.consensus_direction || 'Unknown';
    }

    // Justification
    const justificationEl = document.getElementById('consensusBiasJustification');
    if (justificationEl) {
        justificationEl.textContent = consensus.summary || '';
    }

    // Agreement status
    const detailsEl = document.getElementById('consensusBiasDetails');
    if (detailsEl) {
        detailsEl.innerHTML = '';

        // Agreement indicator
        const agreementDiv = document.createElement('div');
        agreementDiv.className = 'consensus-agreement';
        
        const agreementLevel = consensus.agreement_level || 'Unknown';
        const agreementClass = getAgreementClass(agreementLevel);
        
        agreementDiv.innerHTML = `
            <span class="agreement-label">Model Agreement:</span>
            <span class="agreement-value ${agreementClass}">${agreementLevel}</span>
        `;
        detailsEl.appendChild(agreementDiv);

        // Key findings
        if (consensus.key_findings && consensus.key_findings.length > 0) {
            const findingsSection = createBiasSection('Key Findings', consensus.key_findings);
            detailsEl.appendChild(findingsSection);
        }
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function getBiasScoreClass(score) {
    const absScore = Math.abs(score);
    if (absScore <= 2) return 'score-low';
    if (absScore <= 5) return 'score-medium';
    return 'score-high';
}

function getAgreementClass(level) {
    switch (level.toLowerCase()) {
        case 'high':
        case 'strong':
            return 'agreement-high';
        case 'medium':
        case 'moderate':
            return 'agreement-medium';
        default:
            return 'agreement-low';
    }
}

function createBiasSection(title, items) {
    const section = document.createElement('div');
    section.className = 'bias-section';
    
    section.innerHTML = `
        <h4 class="bias-section-title">${title}</h4>
        <ul class="bias-list">
            ${items.map(item => `<li>${escapeHtml(typeof item === 'string' ? item : item.description || item.text || JSON.stringify(item))}</li>`).join('')}
        </ul>
    `;
    
    return section;
}

function createLanguageSection(langAnalysis) {
    const section = document.createElement('div');
    section.className = 'bias-section';
    
    let content = '<h4 class="bias-section-title">Language Analysis</h4>';
    
    if (langAnalysis.loaded_terms && langAnalysis.loaded_terms.length > 0) {
        content += `
            <div class="lang-subsection">
                <span class="lang-label">Loaded Terms:</span>
                <span class="lang-value">${langAnalysis.loaded_terms.join(', ')}</span>
            </div>
        `;
    }
    
    if (langAnalysis.tone) {
        content += `
            <div class="lang-subsection">
                <span class="lang-label">Tone:</span>
                <span class="lang-value">${langAnalysis.tone}</span>
            </div>
        `;
    }
    
    section.innerHTML = content;
    return section;
}

function createFramingSection(framingAnalysis) {
    const section = document.createElement('div');
    section.className = 'bias-section';
    
    let content = '<h4 class="bias-section-title">Framing Analysis</h4>';
    
    if (framingAnalysis.narrative_frame) {
        content += `
            <div class="framing-subsection">
                <span class="framing-label">Narrative Frame:</span>
                <span class="framing-value">${escapeHtml(framingAnalysis.narrative_frame)}</span>
            </div>
        `;
    }
    
    if (framingAnalysis.perspective) {
        content += `
            <div class="framing-subsection">
                <span class="framing-label">Perspective:</span>
                <span class="framing-value">${escapeHtml(framingAnalysis.perspective)}</span>
            </div>
        `;
    }
    
    section.innerHTML = content;
    return section;
}
