// static/js/renderers/manipulation.js - Manipulation Detection Rendering
// VeriFlow Redesign - Minimalist Theme

// ============================================
// DISPLAY MANIPULATION RESULTS
// ============================================

function displayManipulationResults() {
    if (!AppState.currentManipulationResults || !AppState.currentManipulationResults.success) {
        console.error('No manipulation results available');
        return;
    }

    console.log('Displaying Manipulation Results:', AppState.currentManipulationResults);

    const data = AppState.currentManipulationResults;

    // Score display
    const scoreElement = document.getElementById('manipScore');
    if (scoreElement) {
        const score = data.manipulation_score || 0;
        scoreElement.textContent = score.toFixed(1);
        scoreElement.className = `manipulation-score-value ${getManipulationScoreClass(score)}`;
    }

    // Score label
    const scoreLabelElement = document.getElementById('manipScoreLabel');
    if (scoreLabelElement) {
        scoreLabelElement.textContent = getManipulationLabel(data.manipulation_score || 0);
    }

    // Score justification
    const justificationElement = document.getElementById('manipScoreJustification');
    if (justificationElement) {
        justificationElement.textContent = data.score_justification || '';
    }

    // Summary content
    const summaryElement = document.getElementById('manipSummaryContent');
    if (summaryElement) {
        summaryElement.innerHTML = '';
        
        if (data.narrative_summary) {
            summaryElement.innerHTML = `<p>${escapeHtml(data.narrative_summary)}</p>`;
        } else if (data.summary) {
            summaryElement.innerHTML = `<p>${escapeHtml(data.summary)}</p>`;
        }

        // Add key findings
        if (data.key_findings && data.key_findings.length > 0) {
            const findingsDiv = document.createElement('div');
            findingsDiv.className = 'manipulation-findings';
            findingsDiv.innerHTML = `
                <h4>Key Findings</h4>
                <ul>
                    ${data.key_findings.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                </ul>
            `;
            summaryElement.appendChild(findingsDiv);
        }

        // Add techniques detected
        if (data.techniques_detected && data.techniques_detected.length > 0) {
            const techniquesDiv = document.createElement('div');
            techniquesDiv.className = 'manipulation-techniques';
            techniquesDiv.innerHTML = `
                <h4>Manipulation Techniques</h4>
                <ul>
                    ${data.techniques_detected.map(t => `<li>${escapeHtml(typeof t === 'string' ? t : t.name || t.technique)}</li>`).join('')}
                </ul>
            `;
            summaryElement.appendChild(techniquesDiv);
        }
    }

    // Recommendation
    const recommendationElement = document.getElementById('manipRecommendation');
    if (recommendationElement && data.recommendation) {
        recommendationElement.innerHTML = `
            <div class="recommendation-box">
                <strong>Recommendation:</strong>
                <p>${escapeHtml(data.recommendation)}</p>
            </div>
        `;
    }

    // Facts container (for detailed tab)
    const factsContainer = document.getElementById('manipFactsContainer');
    if (factsContainer && data.analyzed_facts) {
        factsContainer.innerHTML = '';
        
        data.analyzed_facts.forEach((fact, index) => {
            factsContainer.appendChild(createManipulationFactCard(fact, index + 1));
        });
    }

    // Detailed content
    const detailedContent = document.getElementById('manipDetailedContent');
    if (detailedContent) {
        detailedContent.innerHTML = '';

        // Add agenda analysis
        if (data.agenda_analysis) {
            const agendaDiv = document.createElement('div');
            agendaDiv.className = 'detailed-section';
            agendaDiv.innerHTML = `
                <h4>Agenda Analysis</h4>
                <p>${escapeHtml(data.agenda_analysis.summary || data.agenda_analysis)}</p>
            `;
            detailedContent.appendChild(agendaDiv);
        }

        // Add fact distortion analysis
        if (data.fact_distortion) {
            const distortionDiv = document.createElement('div');
            distortionDiv.className = 'detailed-section';
            distortionDiv.innerHTML = `
                <h4>Fact Distortion Analysis</h4>
                <p>${escapeHtml(data.fact_distortion.summary || data.fact_distortion)}</p>
            `;
            detailedContent.appendChild(distortionDiv);
        }

        // Add emotional manipulation analysis
        if (data.emotional_manipulation) {
            const emotionalDiv = document.createElement('div');
            emotionalDiv.className = 'detailed-section';
            emotionalDiv.innerHTML = `
                <h4>Emotional Manipulation</h4>
                <p>${escapeHtml(data.emotional_manipulation.summary || data.emotional_manipulation)}</p>
            `;
            detailedContent.appendChild(emotionalDiv);
        }
    }

    // Session info
    const sessionId = document.getElementById('manipSessionId');
    const processingTime = document.getElementById('manipProcessingTime');

    if (sessionId) sessionId.textContent = data.session_id || '-';
    if (processingTime) processingTime.textContent = Math.round(data.processing_time || 0) + 's';

    // R2 link
    const r2Link = document.getElementById('manipR2Link');
    const r2Sep = document.getElementById('manipR2Sep');

    if (r2Link && r2Sep) {
        if (data.r2_url || data.audit_url) {
            r2Link.href = data.r2_url || data.audit_url;
            r2Link.style.display = 'inline';
            r2Sep.style.display = 'inline';
        } else {
            r2Link.style.display = 'none';
            r2Sep.style.display = 'none';
        }
    }
}

// ============================================
// CREATE MANIPULATION FACT CARD
// ============================================

function createManipulationFactCard(fact, number) {
    const card = document.createElement('div');
    card.className = 'manipulation-fact-card';

    const distortionLevel = fact.distortion_level || fact.manipulation_level || 'unknown';
    const distortionClass = getDistortionClass(distortionLevel);

    card.innerHTML = `
        <div class="fact-header">
            <span class="fact-number">#${number}</span>
            <span class="distortion-badge ${distortionClass}">${capitalizeFirst(distortionLevel)}</span>
        </div>
        <div class="fact-claim">${escapeHtml(fact.claim || fact.statement || '')}</div>
        ${fact.analysis ? `<div class="fact-analysis">${escapeHtml(fact.analysis)}</div>` : ''}
        ${fact.issues && fact.issues.length > 0 ? `
            <div class="fact-issues">
                <strong>Issues:</strong>
                <ul>${fact.issues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
            </div>
        ` : ''}
    `;

    return card;
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function getManipulationScoreClass(score) {
    if (score <= 3) return 'score-low';
    if (score <= 6) return 'score-medium';
    return 'score-high';
}

function getManipulationLabel(score) {
    if (score <= 2) return 'Minimal Manipulation';
    if (score <= 4) return 'Low Manipulation';
    if (score <= 6) return 'Moderate Manipulation';
    if (score <= 8) return 'High Manipulation';
    return 'Severe Manipulation';
}

function getDistortionClass(level) {
    switch (level.toLowerCase()) {
        case 'high':
        case 'severe':
            return 'distortion-high';
        case 'medium':
        case 'moderate':
            return 'distortion-medium';
        case 'low':
        case 'minimal':
            return 'distortion-low';
        default:
            return 'distortion-unknown';
    }
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}
