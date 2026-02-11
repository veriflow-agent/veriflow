// static/js/renderers/comprehensive.js
// VeriFlow - Comprehensive Analysis Mode Renderer
// CLEAN REWRITE - All results arrive at once from HTTP fetch

// ============================================
// COMPREHENSIVE RESULTS RENDERER
// ============================================

/**
 * Render comprehensive analysis results.
 * Called ONCE after the full result is fetched via HTTP.
 * @param {Object} data - Full comprehensive analysis result
 */
function renderComprehensiveResults(data) {
    if (!data) {
        console.error('[Comprehensive] renderComprehensiveResults called with null/undefined data');
        return;
    }

    console.log('[Comprehensive] Rendering results with keys:', Object.keys(data));
    console.log('[Comprehensive] Data check:', {
        hasClassification: !!data.content_classification,
        hasSourceVerification: !!data.source_verification,
        hasModeRouting: !!data.mode_routing,
        hasModeReports: !!data.mode_reports,
        modeReportKeys: data.mode_reports ? Object.keys(data.mode_reports) : [],
        hasSynthesis: !!data.synthesis_report,
        sessionId: data.session_id,
        processingTime: data.processing_time
    });

    // Show the comprehensive results panel
    var panel = document.getElementById('comprehensiveResults');
    if (!panel) {
        console.error('[Comprehensive] comprehensiveResults panel not found in DOM');
        return;
    }
    panel.style.display = 'block';

    // Render each section
    renderContentClassification(data.content_classification);
    renderSourceCredibility(data.source_verification);
    renderModeRouting(data.mode_routing);
    renderModeReports(data.mode_reports);
    renderSynthesisReport(data.synthesis_report);

    // Update session info
    updateComprehensiveSessionInfo(data);
}

// ============================================
// STAGE 1: CONTENT CLASSIFICATION
// ============================================

function renderContentClassification(classification) {
    if (!classification) {
        console.log('[Comprehensive] No content classification data');
        return;
    }

    // Content Type
    var typeEl = document.getElementById('compContentType');
    if (typeEl) {
        typeEl.textContent = formatContentType(classification.content_type);
    }

    // Topic/Realm
    var topicEl = document.getElementById('compContentRealm');
    if (topicEl) {
        var realm = classification.realm || 'Unknown';
        var subRealm = classification.sub_realm;
        topicEl.textContent = subRealm ? capitalizeFirst(realm) + ' / ' + capitalizeFirst(subRealm) : capitalizeFirst(realm);
    }

    // Purpose
    var purposeEl = document.getElementById('compContentPurpose');
    if (purposeEl) {
        purposeEl.textContent = capitalizeFirst(classification.apparent_purpose || classification.purpose || 'Unknown');
    }

    // Has Sources
    var sourcesEl = document.getElementById('compHasCitations');
    if (sourcesEl) {
        var hasRefs = classification.contains_references || (classification.reference_count > 0);
        sourcesEl.textContent = hasRefs ? 'Yes' : 'No';
    }
}

function formatContentType(type) {
    if (!type) return 'Unknown';
    return type
        .split('_')
        .map(function(word) { return word.charAt(0).toUpperCase() + word.slice(1); })
        .join(' ');
}

// ============================================
// STAGE 1: SOURCE CREDIBILITY
// ============================================

function renderSourceCredibility(verification) {
    if (!verification) {
        console.log('[Comprehensive] No source verification data');
        return;
    }

    // Handle error/no-URL cases
    if (verification.error || verification.status === 'no_url_to_verify') {
        var tierEl = document.getElementById('compCredTier');
        if (tierEl) tierEl.textContent = 'N/A';
        var tierDescEl = document.getElementById('compCredTierDesc');
        if (tierDescEl) tierDescEl.textContent = 'No source URL provided';
        return;
    }

    // Trust Level / Tier
    var tierEl2 = document.getElementById('compCredTier');
    if (tierEl2) {
        var tier = verification.credibility_tier || 'Unknown';
        tierEl2.textContent = tier;
        tierEl2.className = 'tier-value tier-' + tier;
    }

    var tierDescEl2 = document.getElementById('compCredTierDesc');
    if (tierDescEl2) {
        tierDescEl2.textContent = verification.tier_description || '';
    }

    // Publication name
    var pubEl = document.getElementById('compPublicationName');
    if (pubEl) {
        pubEl.textContent = verification.domain || verification.publication_name || '--';
    }

    // Bias Rating
    var biasEl = document.getElementById('compBiasRating');
    if (biasEl) {
        biasEl.textContent = verification.bias_rating || '--';
    }

    // Accuracy Record
    var accuracyEl = document.getElementById('compFactualRating');
    if (accuracyEl) {
        accuracyEl.textContent = verification.factual_reporting || '--';
    }
}

// ============================================
// MODE ROUTING (WHAT WE CHECKED)
// ============================================

function renderModeRouting(routing) {
    var checksEl = document.getElementById('selectedModesGrid');
    if (!checksEl) return;

    if (!routing || !routing.selected_modes) {
        checksEl.innerHTML = '<span class="mode-pending">Mode selection pending...</span>';
        return;
    }

    var modeNames = {
        'key_claims_analysis': 'Fact Checking',
        'bias_analysis': 'Bias Detection',
        'manipulation_detection': 'Manipulation Analysis',
        'lie_detection': 'Deception Indicators',
        'llm_output_verification': 'AI Citation Verification'
    };

    if (routing.selected_modes.length === 0) {
        checksEl.innerHTML = '<span class="mode-pending">No modes selected</span>';
        return;
    }

    checksEl.innerHTML = routing.selected_modes
        .map(function(m) { return '<span class="mode-badge">' + (modeNames[m] || m) + '</span>'; })
        .join('');
}

// ============================================
// STAGE 2: MODE REPORTS (Collapsible Details)
// ============================================

function renderModeReports(modeReports) {
    var container = document.getElementById('modeReportsContainer');
    if (!container) return;

    if (!modeReports || Object.keys(modeReports).length === 0) {
        container.innerHTML = '<p class="no-reports">No detailed reports available yet.</p>';
        return;
    }

    var modeConfig = {
        'key_claims_analysis': { title: 'Fact Check Results', renderer: renderFactCheckSummary },
        'bias_analysis': { title: 'Bias Analysis', renderer: renderBiasSummary },
        'manipulation_detection': { title: 'Manipulation Detection', renderer: renderManipulationSummary },
        'lie_detection': { title: 'Deception Indicators', renderer: renderLieDetectionSummary },
        'llm_output_verification': { title: 'AI Citation Check', renderer: renderLLMVerificationSummary }
    };

    var html = '';

    for (var modeKey in modeReports) {
        if (!modeReports.hasOwnProperty(modeKey)) continue;
        var report = modeReports[modeKey];
        var config = modeConfig[modeKey] || { title: modeKey, renderer: renderGenericSummary };

        html += '<div class="mode-report-card" data-mode="' + modeKey + '">'
            + '<div class="mode-report-header" onclick="toggleModeReport(\'' + modeKey + '\')">'
            + '<span class="mode-title">' + config.title + '</span>'
            + '<span class="mode-toggle">Show</span>'
            + '</div>'
            + '<div class="mode-report-content" id="modeContent_' + modeKey + '" style="display: none;">'
            + config.renderer(report)
            + '</div>'
            + '</div>';
    }

    container.innerHTML = html;
}

function toggleModeReport(modeKey) {
    var content = document.getElementById('modeContent_' + modeKey);
    var card = content ? content.closest('.mode-report-card') : null;
    var toggle = card ? card.querySelector('.mode-toggle') : null;

    if (content) {
        var isVisible = content.style.display !== 'none';
        content.style.display = isVisible ? 'none' : 'block';
        if (toggle) toggle.textContent = isVisible ? 'Show' : 'Hide';
    }
}

// Mode-specific renderers
function renderFactCheckSummary(report) {
    if (!report) return '<p>No fact check data</p>';

    var summary = report.summary || {};
    var total = summary.total_key_claims || 0;
    var verified = summary.verified_count || 0;
    var partial = summary.partial_count || 0;
    var unverified = summary.unverified_count || 0;
    var confidence = summary.average_confidence || 0;

    return '<div class="report-summary">'
        + '<div class="summary-stats">'
        + '<div class="stat-item"><span class="stat-value">' + total + '</span><span class="stat-label">Claims Checked</span></div>'
        + '<div class="stat-item verified"><span class="stat-value">' + verified + '</span><span class="stat-label">Verified</span></div>'
        + '<div class="stat-item partial"><span class="stat-value">' + partial + '</span><span class="stat-label">Partial</span></div>'
        + '<div class="stat-item unverified"><span class="stat-value">' + unverified + '</span><span class="stat-label">Unverified</span></div>'
        + '</div>'
        + '<div class="confidence-bar-container">'
        + '<span class="confidence-label">Confidence: ' + Math.round(confidence * 100) + '%</span>'
        + '<div class="confidence-bar"><div class="confidence-fill" style="width: ' + (confidence * 100) + '%"></div></div>'
        + '</div>'
        + '<p class="overall-assessment">' + (summary.overall_credibility || 'Assessment pending') + '</p>'
        + '</div>';
}

function renderBiasSummary(report) {
    if (!report) return '<p>No bias analysis data</p>';

    var analysis = report.analysis || {};
    var score = analysis.consensus_bias_score != null ? analysis.consensus_bias_score : 0;
    var direction = analysis.consensus_direction || 'Unknown';
    var assessment = analysis.final_assessment || 'No assessment available';

    var absScore = Math.abs(score);
    var biasClass = 'low';
    if (absScore > 6) biasClass = 'high';
    else if (absScore > 3) biasClass = 'medium';

    return '<div class="report-summary">'
        + '<div class="bias-indicator ' + biasClass + '">'
        + '<span class="bias-score">' + score.toFixed(1) + '/10</span>'
        + '<span class="bias-direction">' + direction + '</span>'
        + '</div>'
        + '<p class="bias-assessment">' + escapeHtml(assessment) + '</p>'
        + '</div>';
}

function renderManipulationSummary(report) {
    if (!report) return '<p>No manipulation data</p>';

    var score = report.manipulation_score != null ? report.manipulation_score : 0;
    var assessment = report.overall_assessment || 'Unknown';
    var agenda = report.detected_agenda;

    var scoreClass = 'low';
    if (score > 6) scoreClass = 'high';
    else if (score > 3) scoreClass = 'medium';

    return '<div class="report-summary">'
        + '<div class="manipulation-indicator ' + scoreClass + '">'
        + '<span class="manip-score">' + score.toFixed(1) + '/10</span>'
        + '<span class="manip-label">Manipulation Score</span>'
        + '</div>'
        + '<p class="manip-assessment">' + escapeHtml(assessment) + '</p>'
        + (agenda ? '<p class="detected-agenda"><strong>Detected Agenda:</strong> ' + escapeHtml(agenda) + '</p>' : '')
        + '</div>';
}

function renderLieDetectionSummary(report) {
    if (!report) return '<p>No lie detection data</p>';

    var score = report.deception_likelihood_score != null ? report.deception_likelihood_score : (report.overall_score || 0);
    var assessment = report.overall_assessment || 'Unknown';

    var scoreClass = 'low';
    if (score > 6) scoreClass = 'high';
    else if (score > 3) scoreClass = 'medium';

    return '<div class="report-summary">'
        + '<div class="deception-indicator ' + scoreClass + '">'
        + '<span class="deception-score">' + score + '/10</span>'
        + '<span class="deception-label">Deception Likelihood</span>'
        + '</div>'
        + '<p class="deception-assessment">' + escapeHtml(assessment) + '</p>'
        + '</div>';
}

function renderLLMVerificationSummary(report) {
    if (!report) return '<p>No LLM verification data</p>';

    var total = report.total_claims || 0;
    var verified = report.verified_count || 0;
    var misrep = report.misrepresented_count || 0;
    var notFound = report.not_found_count || 0;

    return '<div class="report-summary">'
        + '<div class="summary-stats">'
        + '<div class="stat-item"><span class="stat-value">' + total + '</span><span class="stat-label">Citations Checked</span></div>'
        + '<div class="stat-item verified"><span class="stat-value">' + verified + '</span><span class="stat-label">Verified</span></div>'
        + '<div class="stat-item unverified"><span class="stat-value">' + misrep + '</span><span class="stat-label">Misrepresented</span></div>'
        + '<div class="stat-item"><span class="stat-value">' + notFound + '</span><span class="stat-label">Not Found</span></div>'
        + '</div>'
        + '</div>';
}

function renderGenericSummary(report) {
    return '<pre class="report-json">' + escapeHtml(JSON.stringify(report, null, 2)) + '</pre>';
}

// ============================================
// STAGE 3: SYNTHESIS REPORT (Main Output)
// ============================================

function renderSynthesisReport(synthesis) {
    console.log('[Comprehensive] Rendering synthesis report:', synthesis ? Object.keys(synthesis) : 'null');

    if (!synthesis) {
        console.warn('[Comprehensive] No synthesis report in data');
        var scoreCircleLoading = document.getElementById('compOverallScore');
        if (scoreCircleLoading) {
            var sv = scoreCircleLoading.querySelector('.score-value');
            if (sv) sv.textContent = '--';
        }
        return;
    }

    // Overall Score
    var scoreCircle = document.getElementById('compOverallScore');
    if (scoreCircle) {
        var score = synthesis.overall_score != null ? synthesis.overall_score : (synthesis.overall_credibility_score != null ? synthesis.overall_credibility_score : '--');
        var scoreValueEl = scoreCircle.querySelector('.score-value');
        if (scoreValueEl) {
            scoreValueEl.textContent = score;
        }
        scoreCircle.className = 'score-circle ' + getScoreClass(score);
    }

    // Overall Rating
    var ratingEl = document.getElementById('compOverallRating');
    if (ratingEl) {
        var rating = synthesis.overall_rating || synthesis.overall_credibility_rating || '--';
        ratingEl.textContent = rating;
        ratingEl.className = 'rating-badge ' + getRatingClass(rating);
    }

    // Confidence
    var confBar = document.getElementById('compConfidenceBar');
    var confValue = document.getElementById('compConfidenceValue');
    if (confBar && confValue) {
        var conf = synthesis.confidence || synthesis.confidence_in_assessment || 0;
        confBar.style.width = conf + '%';
        confValue.textContent = Math.round(conf) + '%';
    }

    // THE MAIN OUTPUT: Human-readable summary
    renderSynthesisSummary(synthesis.summary || synthesis.narrative_summary);

    // Key Concerns
    renderKeyConcerns(synthesis.key_concerns);

    // Positive Indicators
    renderPositiveIndicators(synthesis.positive_indicators);

    // Recommendations
    renderRecommendations(synthesis.recommendations);

    // Analysis Notes
    if (synthesis.analysis_notes) {
        renderAnalysisNotes(synthesis.analysis_notes);
    }
}

/**
 * Render the main human-readable summary
 */
function renderSynthesisSummary(summary) {
    var container = document.getElementById('synthesisSummaryContainer');
    if (!container) {
        console.error('[Comprehensive] synthesisSummaryContainer not found');
        return;
    }

    if (!summary) {
        container.innerHTML = '<p class="no-summary">Analysis complete -- no summary generated.</p>';
        return;
    }

    // Convert markdown-style formatting to HTML
    var formattedSummary = escapeHtml(summary);

    // Convert **bold** to <strong>
    formattedSummary = formattedSummary.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Convert line breaks to paragraphs
    var paragraphs = formattedSummary.split('\n\n').filter(function(p) { return p.trim(); });

    if (paragraphs.length > 0) {
        container.innerHTML = paragraphs.map(function(p) {
            return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
        }).join('');
    } else {
        container.innerHTML = '<p>' + formattedSummary.replace(/\n/g, '<br>') + '</p>';
    }
}

function renderKeyConcerns(concerns) {
    var container = document.getElementById('keyConcernsContainer');
    var section = document.getElementById('keyConcernsSection');
    if (!container || !section) return;

    if (!concerns || concerns.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = concerns.map(function(concern) {
        return '<li class="concern-item">'
            + '<span class="concern-icon">[!]</span>'
            + '<span class="concern-text">' + escapeHtml(concern) + '</span>'
            + '</li>';
    }).join('');
}

function renderPositiveIndicators(positives) {
    var container = document.getElementById('positiveIndicatorsContainer');
    var section = document.getElementById('positiveIndicatorsSection');
    if (!container || !section) return;

    if (!positives || positives.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = positives.map(function(positive) {
        return '<li class="positive-item">'
            + '<span class="positive-icon">[+]</span>'
            + '<span class="positive-text">' + escapeHtml(positive) + '</span>'
            + '</li>';
    }).join('');
}

function renderRecommendations(recommendations) {
    var container = document.getElementById('recommendationsContainer');
    var section = document.getElementById('recommendationsSection');
    if (!container || !section) return;

    if (!recommendations || recommendations.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = recommendations.map(function(rec) {
        return '<li class="recommendation-item">'
            + '<span class="rec-icon">></span>'
            + '<span class="rec-text">' + escapeHtml(rec) + '</span>'
            + '</li>';
    }).join('');
}

function renderAnalysisNotes(notes) {
    var container = document.getElementById('analysisNotesContainer');
    if (!container) return;

    if (!notes) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    container.innerHTML = '<div class="analysis-notes">'
        + '<span class="notes-icon">[i]</span>'
        + '<span class="notes-text">' + escapeHtml(notes) + '</span>'
        + '</div>';
}

// ============================================
// SESSION INFO
// ============================================

function updateComprehensiveSessionInfo(data) {
    var sessionIdEl = document.getElementById('compSessionId');
    var analysisTimeEl = document.getElementById('compProcessingTime');
    var r2Link = document.getElementById('compR2Link');
    var r2Sep = document.getElementById('compR2Sep');

    if (sessionIdEl) {
        sessionIdEl.textContent = data.session_id || '--';
    }

    if (analysisTimeEl) {
        var time = data.processing_time || data.total_processing_time;
        analysisTimeEl.textContent = time ? Math.round(time) + 's' : '--';
    }

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
// HELPER FUNCTIONS
// ============================================

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase().replace(/_/g, ' ');
}

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getScoreClass(score) {
    if (score >= 80) return 'score-high';
    if (score >= 65) return 'score-good';
    if (score >= 45) return 'score-mixed';
    if (score >= 25) return 'score-low';
    return 'score-unreliable';
}

function getRatingClass(rating) {
    if (!rating) return '';
    var r = rating.toLowerCase();
    if (r.includes('highly')) return 'rating-highly-credible';
    if (r.includes('credible') && !r.includes('low')) return 'rating-credible';
    if (r.includes('mixed')) return 'rating-mixed';
    if (r.includes('low')) return 'rating-low';
    return 'rating-unreliable';
}

// ============================================
// EXPORTS
// ============================================

if (typeof window !== 'undefined') {
    window.renderComprehensiveResults = renderComprehensiveResults;
    window.toggleModeReport = toggleModeReport;
}
