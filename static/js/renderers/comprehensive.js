// static/js/renderers/comprehensive.js
// VeriFlow - Comprehensive Analysis Mode Renderer
// UPDATED with redesigned metadata rendering

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

    // Render redesigned metadata section (replaces old renderContentClassification + renderSourceCredibility)
    renderRedesignedMetadata(data);

    // Render mode reports and synthesis (unchanged)
    renderModeReports(data.mode_reports);
    renderSynthesisReport(data.synthesis_report);

    // Update session info
    updateComprehensiveSessionInfo(data);
}

// ============================================
// REDESIGNED METADATA RENDERING
// ============================================

/**
 * Main function to render redesigned metadata panel
 * Replaces old renderContentClassification() and renderSourceCredibility()
 */
function renderRedesignedMetadata(data) {
    if (!data) return;

    console.log('[Metadata] Rendering redesigned metadata');

    // Render each section
    renderSummaryCard(data);
    renderContentClassificationSection(data.content_classification);
    renderSourceDetailsSection(data.source_verification);
    renderChecksPerformed(data.mode_routing);
}

/**
 * Render the primary summary card (most important info)
 */
function renderSummaryCard(data) {
    var verification = data.source_verification || {};
    var synthesis = data.synthesis_report || {};

    // Trust Score
    var trustScore = synthesis.trust_score || verification.credibility_tier || '--';
    var trustScoreBadge = document.getElementById('trustScoreBadge');
    if (trustScoreBadge) {
        trustScoreBadge.textContent = trustScore;
    }

    // Source Domain
    var domain = verification.domain || 'Unknown Source';
    var sourceDomain = document.getElementById('sourceDomain');
    if (sourceDomain) {
        sourceDomain.textContent = domain;
    }

    // Source URL Link
    var sourceUrl = data.source_url || verification.url;
    var sourceUrlLink = document.getElementById('sourceUrlLink');
    if (sourceUrlLink && sourceUrl) {
        sourceUrlLink.href = sourceUrl;
        sourceUrlLink.style.display = 'inline-flex';

        var sourceUrlText = document.getElementById('sourceUrlText');
        if (sourceUrlText) {
            sourceUrlText.textContent = sourceUrl.length > 50 ? 
                sourceUrl.substring(0, 50) + '...' : sourceUrl;
        }
    }

    // Credibility Tier
    var tier = verification.credibility_tier || '--';
    var credTierValue = document.getElementById('credTierValue');
    if (credTierValue) {
        credTierValue.textContent = tier !== '--' ? 'Tier ' + tier : '--';
    }

    // Bias Rating
    var biasRating = verification.bias_rating || '--';
    var biasRatingValue = document.getElementById('biasRatingValue');
    if (biasRatingValue) {
        biasRatingValue.textContent = formatBiasRating(biasRating);
    }

    // Factual Reporting
    var factualReporting = verification.factual_reporting || '--';
    var factualReportingValue = document.getElementById('factualReportingValue');
    if (factualReportingValue) {
        factualReportingValue.textContent = formatFactualReporting(factualReporting);
    }
}

/**
 * Render content classification section
 */
function renderContentClassificationSection(classification) {
    if (!classification) {
        console.log('[Metadata] No content classification data');
        return;
    }

    // Content Type
    var contentType = classification.content_type || 'Unknown';
    var contentTypeValue = document.getElementById('contentTypeValue');
    if (contentTypeValue) {
        contentTypeValue.textContent = formatContentType(contentType);
        contentTypeValue.className = 'info-field-value badge ' + getContentTypeClass(contentType);
    }

    // Topic / Realm
    var realm = classification.realm || 'Unknown';
    var subRealm = classification.sub_realm;
    var contentRealmValue = document.getElementById('contentRealmValue');
    if (contentRealmValue) {
        contentRealmValue.textContent = subRealm ? 
            capitalizeFirst(realm) + ' / ' + capitalizeFirst(subRealm) : 
            capitalizeFirst(realm);
    }

    // Apparent Purpose
    var purpose = classification.apparent_purpose || classification.purpose || 'Unknown';
    var contentPurposeValue = document.getElementById('contentPurposeValue');
    if (contentPurposeValue) {
        contentPurposeValue.textContent = capitalizeFirst(purpose);
    }

    // Contains Citations
    var hasCitations = classification.contains_references || (classification.reference_count > 0);
    var hasCitationsValue = document.getElementById('hasCitationsValue');
    if (hasCitationsValue) {
        hasCitationsValue.textContent = hasCitations ? 'Yes' : 'No';
        hasCitationsValue.className = 'info-field-value ' + (hasCitations ? 'yes' : 'no');
    }
}

/**
 * Render source details section
 */
function renderSourceDetailsSection(verification) {
    if (!verification) {
        console.log('[Metadata] No source verification data');
        return;
    }

    // Publication Name
    var publicationName = verification.domain || verification.publication_name || 'Unknown';
    var publicationNameValue = document.getElementById('publicationNameValue');
    if (publicationNameValue) {
        publicationNameValue.textContent = publicationName;
    }

    // Verification Source
    var verificationSource = verification.verification_source || 'Unknown';
    var verificationSourceValue = document.getElementById('verificationSourceValue');
    if (verificationSourceValue) {
        verificationSourceValue.textContent = verificationSource;
    }

    // Is Propaganda
    var isPropaganda = verification.is_propaganda;
    var isPropagandaValue = document.getElementById('isPropagandaValue');
    if (isPropagandaValue) {
        var propagandaText = isPropaganda === true ? 'Yes' : 
                              isPropaganda === false ? 'No' : 
                              'Unknown';
        isPropagandaValue.textContent = propagandaText;
        isPropagandaValue.className = 'info-field-value ' + 
            (isPropaganda === true ? 'warning' : isPropaganda === false ? 'yes' : '');
    }

    // Is Satire
    var isSatire = verification.is_satire;
    var isSatireValue = document.getElementById('isSatireValue');
    if (isSatireValue) {
        var satireText = isSatire === true ? 'Yes' : 
                          isSatire === false ? 'No' : 
                          'Unknown';
        isSatireValue.textContent = satireText;
        isSatireValue.className = 'info-field-value ' + 
            (isSatire === true ? 'warning' : isSatire === false ? 'yes' : '');
    }

    // Tier Description (if available)
    var tierDesc = verification.tier_description;
    var tierDescriptionBlock = document.getElementById('tierDescriptionBlock');
    var tierDescriptionText = document.getElementById('tierDescriptionText');
    if (tierDesc && tierDescriptionBlock && tierDescriptionText) {
        tierDescriptionText.textContent = tierDesc;
        tierDescriptionBlock.style.display = 'block';
    }
}

/**
 * Render checks performed badges
 */
function renderChecksPerformed(modeRouting) {
    var checksContainer = document.getElementById('checksPerformed');
    if (!checksContainer) return;

    if (!modeRouting) {
        checksContainer.innerHTML = '<span class="check-badge">No analysis performed yet</span>';
        return;
    }

    var checks = [];

    if (modeRouting.fact_check) {
        checks.push({ name: 'Fact Checking', active: true });
    }
    if (modeRouting.bias_check) {
        checks.push({ name: 'Bias Detection', active: true });
    }
    if (modeRouting.manipulation_check) {
        checks.push({ name: 'Manipulation Analysis', active: true });
    }
    if (modeRouting.lie_detection) {
        checks.push({ name: 'Lie Detection', active: true });
    }
    if (modeRouting.llm_verification) {
        checks.push({ name: 'LLM Output Verification', active: true });
    }

    if (checks.length === 0) {
        checksContainer.innerHTML = '<span class="check-badge">Content Classification Only</span>';
        return;
    }

    var html = '';
    checks.forEach(function(check) {
        html += '<span class="check-badge' + (check.active ? ' active' : '') + '">';
        html += '<span class="check-icon"></span>';
        html += check.name;
        html += '</span>';
    });

    checksContainer.innerHTML = html;
}

// ============================================
// METADATA HELPER FUNCTIONS
// ============================================

function formatContentType(type) {
    if (!type) return 'Unknown';
    return type
        .split('_')
        .map(function(word) { 
            return word.charAt(0).toUpperCase() + word.slice(1); 
        })
        .join(' ');
}

function getContentTypeClass(type) {
    if (!type) return '';

    var lowerType = type.toLowerCase();
    if (lowerType.includes('news')) return 'content-type-news';
    if (lowerType.includes('opinion')) return 'content-type-opinion';
    if (lowerType.includes('analysis')) return 'content-type-analysis';

    return '';
}

function formatBiasRating(rating) {
    if (!rating) return 'Unknown';

    var lowerRating = rating.toLowerCase();

    if (lowerRating.includes('least')) return 'Least Biased';
    if (lowerRating.includes('left')) return 'Leans Left';
    if (lowerRating.includes('right')) return 'Leans Right';
    if (lowerRating.includes('center')) return 'Center';

    return rating;
}

function formatFactualReporting(reporting) {
    if (!reporting) return 'Unknown';

    var lowerReporting = reporting.toLowerCase();

    if (lowerReporting.includes('high')) return 'High';
    if (lowerReporting.includes('mostly')) return 'Mostly Factual';
    if (lowerReporting.includes('mixed')) return 'Mixed';
    if (lowerReporting.includes('low')) return 'Low';

    return reporting;
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