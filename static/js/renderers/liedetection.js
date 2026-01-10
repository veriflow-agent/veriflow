// static/js/renderers/liedetection.js - Lie Detection Rendering
// VeriFlow Redesign - Minimalist Theme

// ============================================
// DISPLAY LIE DETECTION RESULTS
// ============================================

function displayLieDetectionResults() {
    if (!AppState.currentLieDetectionResults || !AppState.currentLieDetectionResults.success) {
        console.error('No lie detection results available');
        return;
    }

    console.log('Displaying Lie Detection Results:', AppState.currentLieDetectionResults);

    const data = AppState.currentLieDetectionResults;
    const analysis = data.analysis || data;

    // Score display
    const scoreElement = document.getElementById('lieScore');
    if (scoreElement) {
        const score = analysis.credibility_score || 0;
        scoreElement.textContent = score;
        scoreElement.className = `lie-score-value ${getLieScoreClass(score)}`;
    }

    // Verdict/Risk level
    const verdictElement = document.getElementById('lieVerdict');
    if (verdictElement) {
        const riskLevel = analysis.risk_level || 'Unknown';
        verdictElement.textContent = `${riskLevel} Risk`;
        verdictElement.className = `lie-verdict risk-${riskLevel.toLowerCase()}`;
    }

    // Justification/Assessment
    const justificationElement = document.getElementById('lieJustification');
    if (justificationElement) {
        justificationElement.textContent = analysis.overall_assessment || '';
    }

    // Markers detected
    const markersContainer = document.getElementById('lieIndicators');
    if (markersContainer) {
        markersContainer.innerHTML = '';

        if (analysis.markers_detected && analysis.markers_detected.length > 0) {
            analysis.markers_detected.forEach(marker => {
                markersContainer.appendChild(createMarkerCard(marker));
            });
        } else {
            markersContainer.innerHTML = '<p class="no-markers">No significant deception markers detected.</p>';
        }

        // Add positive indicators section
        if (analysis.positive_indicators && analysis.positive_indicators.length > 0) {
            const positiveSection = createPositiveIndicatorsSection(analysis.positive_indicators);
            markersContainer.appendChild(positiveSection);
        }
    }

    // Session info
    const sessionId = document.getElementById('lieSessionId');
    const processingTime = document.getElementById('lieProcessingTime');

    if (sessionId) sessionId.textContent = data.session_id || '-';
    if (processingTime) processingTime.textContent = Math.round(data.processing_time || 0) + 's';

    // R2 link
    const r2Link = document.getElementById('lieR2Link');
    const r2Sep = document.getElementById('lieR2Sep');

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
// CREATE MARKER CARD
// ============================================

function createMarkerCard(marker) {
    const card = document.createElement('div');
    card.className = 'marker-card';

    const severity = marker.severity || marker.weight || 'medium';
    const severityClass = getSeverityClass(severity);

    card.innerHTML = `
        <div class="marker-header">
            <span class="marker-type">${escapeHtml(marker.type || marker.category || 'Marker')}</span>
            <span class="marker-severity ${severityClass}">${capitalizeFirst(severity)}</span>
        </div>
        <div class="marker-description">${escapeHtml(marker.description || marker.text || '')}</div>
        ${marker.example ? `<div class="marker-example">"${escapeHtml(marker.example)}"</div>` : ''}
    `;

    return card;
}

// ============================================
// CREATE POSITIVE INDICATORS SECTION
// ============================================

function createPositiveIndicatorsSection(indicators) {
    const section = document.createElement('div');
    section.className = 'positive-indicators-section';

    section.innerHTML = `
        <h4 class="section-title positive">Credibility Indicators</h4>
        <ul class="positive-list">
            ${indicators.map(indicator => `<li>${escapeHtml(typeof indicator === 'string' ? indicator : indicator.description || indicator.text)}</li>`).join('')}
        </ul>
    `;

    return section;
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function getLieScoreClass(score) {
    if (score >= 80) return 'score-high';
    if (score >= 60) return 'score-medium';
    return 'score-low';
}

function getSeverityClass(severity) {
    switch (severity.toLowerCase()) {
        case 'high':
        case 'critical':
            return 'severity-high';
        case 'medium':
        case 'moderate':
            return 'severity-medium';
        default:
            return 'severity-low';
    }
}

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}
