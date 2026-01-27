// static/js/renderers/comprehensive.js
// VeriFlow - Comprehensive Analysis Mode Renderer
// Handles Stage 1 (Pre-Analysis), Stage 2 (Mode Reports), Stage 3 (Synthesis)

// ============================================
// COMPREHENSIVE RESULTS RENDERER
// ============================================

/**
 * Render comprehensive analysis results
 * @param {Object} data - Full comprehensive analysis result
 */
function renderComprehensiveResults(data) {
    console.log('Rendering comprehensive results:', data);
    
    // Show the comprehensive results panel
    const panel = document.getElementById('comprehensiveResults');
    if (!panel) {
        console.error('Comprehensive results panel not found');
        return;
    }
    
    // Render each stage
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
        console.log('No content classification data');
        return;
    }
    
    // Content Type
    const typeEl = document.getElementById('compContentType');
    if (typeEl) {
        typeEl.textContent = formatContentType(classification.content_type);
    }
    
    // Realm
    const realmEl = document.getElementById('compContentRealm');
    if (realmEl) {
        const realm = classification.realm || 'Unknown';
        const subRealm = classification.sub_realm;
        realmEl.textContent = subRealm ? `${capitalizeFirst(realm)} → ${subRealm}` : capitalizeFirst(realm);
    }
    
    // Purpose
    const purposeEl = document.getElementById('compContentPurpose');
    if (purposeEl) {
        purposeEl.textContent = capitalizeFirst(classification.apparent_purpose || 'Unknown');
    }
    
    // Has Citations
    const citationsEl = document.getElementById('compHasCitations');
    if (citationsEl) {
        const hasCitations = classification.has_html_references || classification.has_markdown_references;
        const count = classification.reference_count || 0;
        if (hasCitations && count > 0) {
            citationsEl.innerHTML = `<span class="citation-yes">Yes (${count} found)</span>`;
        } else {
            citationsEl.innerHTML = `<span class="citation-no">No</span>`;
        }
    }
    
    // Classification Notes
    const notesEl = document.getElementById('compClassificationNotes');
    if (notesEl && classification.classification_notes) {
        notesEl.textContent = classification.classification_notes;
        notesEl.style.display = 'block';
    }
}

function formatContentType(type) {
    const typeMap = {
        'news_article': '📰 News Article',
        'opinion_column': '💬 Opinion/Editorial',
        'analysis_piece': '📊 Analysis',
        'social_media_post': '📱 Social Media',
        'press_release': '📋 Press Release',
        'blog_post': '✍️ Blog Post',
        'academic_paper': '🎓 Academic',
        'interview_transcript': '🎤 Interview',
        'speech_transcript': '🎙️ Speech',
        'llm_output': '🤖 AI-Generated',
        'official_statement': '🏛️ Official Statement',
        'advertisement': '📢 Advertisement',
        'satire': '😄 Satire',
        'other': '📄 Other'
    };
    return typeMap[type] || capitalizeFirst(type || 'Unknown');
}

// ============================================
// STAGE 1: SOURCE CREDIBILITY
// ============================================

function renderSourceCredibility(verification) {
    if (!verification) {
        console.log('No source verification data');
        return;
    }
    
    // Tier
    const tierEl = document.getElementById('compCredTier');
    const tierDescEl = document.getElementById('compCredTierDesc');
    
    if (tierEl) {
        const tier = verification.credibility_tier || 3;
        tierEl.textContent = tier;
        tierEl.className = `tier-value tier-${tier}`;
    }
    
    if (tierDescEl) {
        tierDescEl.textContent = verification.tier_description || getTierDescription(verification.credibility_tier);
    }
    
    // Publication Name
    const pubEl = document.getElementById('compPublicationName');
    if (pubEl) {
        pubEl.textContent = verification.publication_name || verification.domain || '—';
    }
    
    // Bias Rating
    const biasEl = document.getElementById('compBiasRating');
    if (biasEl) {
        biasEl.innerHTML = formatBiasRating(verification.bias_rating);
    }
    
    // Factual Reporting
    const factualEl = document.getElementById('compFactualRating');
    if (factualEl) {
        factualEl.innerHTML = formatFactualRating(verification.factual_reporting);
    }
    
    // Flags
    const flagsContainer = document.getElementById('compCredibilityFlags');
    if (flagsContainer) {
        const flags = [];
        
        if (verification.is_propaganda) {
            flags.push({ text: '⚠️ Propaganda', level: 'critical' });
        }
        
        if (verification.special_tags && verification.special_tags.length > 0) {
            verification.special_tags.forEach(tag => {
                flags.push({ text: tag, level: 'high' });
            });
        }
        
        if (flags.length > 0) {
            flagsContainer.innerHTML = flags.map(f => 
                `<span class="flag-badge flag-${f.level}">${escapeHtml(f.text)}</span>`
            ).join('');
            flagsContainer.style.display = 'flex';
        } else {
            flagsContainer.style.display = 'none';
        }
    }
}

function getTierDescription(tier) {
    const descriptions = {
        1: 'Highly Credible',
        2: 'Credible',
        3: 'Mixed Credibility',
        4: 'Low Credibility',
        5: 'Unreliable'
    };
    return descriptions[tier] || 'Unknown';
}

function formatBiasRating(rating) {
    if (!rating) return '—';
    
    const biasColors = {
        'FAR LEFT': '#3b82f6',
        'LEFT': '#60a5fa',
        'LEFT-CENTER': '#93c5fd',
        'CENTER': '#6b7280',
        'RIGHT-CENTER': '#fca5a5',
        'RIGHT': '#f87171',
        'FAR RIGHT': '#ef4444'
    };
    
    const color = biasColors[rating.toUpperCase()] || '#6b7280';
    return `<span style="color: ${color}; font-weight: 500;">${rating}</span>`;
}

function formatFactualRating(rating) {
    if (!rating) return '—';
    
    const factualColors = {
        'VERY HIGH': '#10b981',
        'HIGH': '#22c55e',
        'MOSTLY FACTUAL': '#84cc16',
        'MIXED': '#f59e0b',
        'LOW': '#f97316',
        'VERY LOW': '#ef4444'
    };
    
    const color = factualColors[rating.toUpperCase()] || '#6b7280';
    return `<span style="color: ${color}; font-weight: 500;">${rating}</span>`;
}

// ============================================
// STAGE 1: MODE ROUTING
// ============================================

function renderModeRouting(routing) {
    const container = document.getElementById('selectedModesGrid');
    if (!container) return;
    
    if (!routing) {
        container.innerHTML = '<span class="text-muted">Mode selection pending...</span>';
        return;
    }
    
    const modeIcons = {
        'llm_output_verification': '✅',
        'key_claims_analysis': '🎯',
        'bias_analysis': '📊',
        'manipulation_detection': '🎭',
        'lie_detection': '🕵️',
        'web_search_factcheck': '🔍'
    };
    
    const modeLabels = {
        'llm_output_verification': 'LLM Verification',
        'key_claims_analysis': 'Key Claims',
        'bias_analysis': 'Bias Analysis',
        'manipulation_detection': 'Manipulation',
        'lie_detection': 'Lie Detection',
        'web_search_factcheck': 'Fact-Check'
    };
    
    let html = '';
    
    // Selected modes
    if (routing.selected_modes && routing.selected_modes.length > 0) {
        routing.selected_modes.forEach(mode => {
            const icon = modeIcons[mode] || '📋';
            const label = modeLabels[mode] || formatModeId(mode);
            html += `
                <div class="mode-chip mode-active">
                    <span class="mode-chip-icon">${icon}</span>
                    <span>${label}</span>
                </div>
            `;
        });
    }
    
    // Excluded modes (optional, shown lighter)
    if (routing.excluded_modes && routing.excluded_modes.length > 0) {
        routing.excluded_modes.forEach(mode => {
            const icon = modeIcons[mode] || '📋';
            const label = modeLabels[mode] || formatModeId(mode);
            html += `
                <div class="mode-chip mode-excluded" title="${routing.exclusion_rationale?.[mode] || 'Not applicable'}">
                    <span class="mode-chip-icon">${icon}</span>
                    <span>${label}</span>
                </div>
            `;
        });
    }
    
    container.innerHTML = html || '<span class="text-muted">No modes selected</span>';
}

function formatModeId(modeId) {
    return modeId
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

// ============================================
// STAGE 2: MODE REPORTS (COLLAPSIBLE)
// ============================================

function renderModeReports(reports) {
    const container = document.getElementById('modeReportsContainer');
    if (!container) return;
    
    if (!reports || Object.keys(reports).length === 0) {
        container.innerHTML = '<div class="text-muted">No mode reports available yet.</div>';
        return;
    }
    
    const modeConfig = {
        'key_claims_analysis': { icon: '🎯', label: 'Key Claims Analysis', renderer: renderKeyClaimsSummary },
        'bias_analysis': { icon: '📊', label: 'Bias Analysis', renderer: renderBiasSummary },
        'manipulation_detection': { icon: '🎭', label: 'Manipulation Detection', renderer: renderManipulationSummary },
        'lie_detection': { icon: '🕵️', label: 'Lie Detection', renderer: renderLieDetectionSummary },
        'llm_output_verification': { icon: '✅', label: 'LLM Output Verification', renderer: renderLLMVerificationSummary }
    };
    
    let html = '';
    
    Object.entries(reports).forEach(([modeId, report]) => {
        const config = modeConfig[modeId] || { icon: '📋', label: formatModeId(modeId), renderer: renderGenericSummary };
        const status = report ? 'complete' : 'skipped';
        
        html += `
            <div class="mode-report-card" data-mode="${modeId}">
                <div class="mode-report-header" onclick="toggleModeReport('${modeId}')">
                    <div class="mode-report-title">
                        <span>${config.icon}</span>
                        <span>${config.label}</span>
                    </div>
                    <div class="mode-report-meta">
                        <span class="mode-report-status status-${status}">${capitalizeFirst(status)}</span>
                        <span class="mode-report-toggle">▼</span>
                    </div>
                </div>
                <div class="mode-report-content" id="modeReport_${modeId}">
                    ${report ? config.renderer(report) : '<p class="text-muted">Report not available</p>'}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function toggleModeReport(modeId) {
    const card = document.querySelector(`.mode-report-card[data-mode="${modeId}"]`);
    if (card) {
        card.classList.toggle('expanded');
    }
}

// Toggle all mode reports
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('toggleModeReports');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const cards = document.querySelectorAll('.mode-report-card');
            const allExpanded = Array.from(cards).every(c => c.classList.contains('expanded'));
            
            cards.forEach(card => {
                if (allExpanded) {
                    card.classList.remove('expanded');
                } else {
                    card.classList.add('expanded');
                }
            });
            
            toggleBtn.textContent = allExpanded ? 'Expand All' : 'Collapse All';
        });
    }
});

// Summary renderers for each mode
function renderKeyClaimsSummary(report) {
    if (!report || !report.claims) return '<p>No claims data</p>';
    
    const claims = report.claims || [];
    let html = `<div class="report-summary">`;
    html += `<p><strong>${claims.length}</strong> key claims analyzed</p>`;
    
    claims.forEach((claim, i) => {
        const verdict = claim.verification?.verdict || 'Unknown';
        const verdictClass = getVerdictClass(verdict);
        html += `
            <div class="claim-summary-item">
                <span class="claim-number">#${i + 1}</span>
                <span class="claim-text">${escapeHtml(truncateText(claim.claim || claim.statement, 100))}</span>
                <span class="claim-verdict ${verdictClass}">${verdict}</span>
            </div>
        `;
    });
    
    html += `</div>`;
    return html;
}

function renderBiasSummary(report) {
    if (!report) return '<p>No bias data</p>';
    
    const score = report.consensus_bias_score ?? report.bias_score ?? '—';
    const lean = report.political_lean || report.bias_direction || 'Unknown';
    
    return `
        <div class="report-summary">
            <div class="summary-stat">
                <span class="stat-label">Bias Score</span>
                <span class="stat-value">${score}/10</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Political Lean</span>
                <span class="stat-value">${lean}</span>
            </div>
            ${report.key_concerns ? `<p class="summary-concerns">${escapeHtml(report.key_concerns)}</p>` : ''}
        </div>
    `;
}

function renderManipulationSummary(report) {
    if (!report) return '<p>No manipulation data</p>';
    
    const score = report.overall_manipulation_score ?? '—';
    const level = report.manipulation_level || 'Unknown';
    
    return `
        <div class="report-summary">
            <div class="summary-stat">
                <span class="stat-label">Manipulation Score</span>
                <span class="stat-value">${score}/10</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Level</span>
                <span class="stat-value">${level}</span>
            </div>
            ${report.detected_agenda ? `<p class="summary-agenda"><strong>Agenda:</strong> ${escapeHtml(report.detected_agenda)}</p>` : ''}
        </div>
    `;
}

function renderLieDetectionSummary(report) {
    if (!report) return '<p>No lie detection data</p>';
    
    const score = report.deception_likelihood_score ?? report.overall_score ?? '—';
    const assessment = report.overall_assessment || 'Unknown';
    
    return `
        <div class="report-summary">
            <div class="summary-stat">
                <span class="stat-label">Deception Score</span>
                <span class="stat-value">${score}/10</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Assessment</span>
                <span class="stat-value">${assessment}</span>
            </div>
        </div>
    `;
}

function renderLLMVerificationSummary(report) {
    if (!report) return '<p>No LLM verification data</p>';
    
    const total = report.total_claims || 0;
    const verified = report.verified_count || 0;
    
    return `
        <div class="report-summary">
            <div class="summary-stat">
                <span class="stat-label">Claims Checked</span>
                <span class="stat-value">${total}</span>
            </div>
            <div class="summary-stat">
                <span class="stat-label">Verified</span>
                <span class="stat-value">${verified}/${total}</span>
            </div>
        </div>
    `;
}

function renderGenericSummary(report) {
    return `<pre class="report-json">${escapeHtml(JSON.stringify(report, null, 2))}</pre>`;
}

function getVerdictClass(verdict) {
    const v = (verdict || '').toLowerCase();
    if (v.includes('true') || v.includes('verified') || v.includes('accurate')) return 'verdict-true';
    if (v.includes('false') || v.includes('inaccurate')) return 'verdict-false';
    if (v.includes('partial') || v.includes('mixed')) return 'verdict-partial';
    return 'verdict-unknown';
}

// ============================================
// STAGE 3: SYNTHESIS REPORT
// ============================================

function renderSynthesisReport(synthesis) {
    if (!synthesis) {
        console.log('No synthesis report yet');
        return;
    }
    
    // Overall Score
    const scoreEl = document.getElementById('compOverallScore');
    if (scoreEl) {
        const score = synthesis.overall_credibility_score ?? 0;
        const scoreValue = scoreEl.querySelector('.score-value');
        if (scoreValue) scoreValue.textContent = Math.round(score);
        
        // Add color class based on score
        scoreEl.classList.remove('score-high', 'score-medium', 'score-low');
        if (score >= 70) scoreEl.classList.add('score-high');
        else if (score >= 40) scoreEl.classList.add('score-medium');
        else scoreEl.classList.add('score-low');
    }
    
    // Overall Rating
    const ratingEl = document.getElementById('compOverallRating');
    if (ratingEl) {
        ratingEl.textContent = synthesis.overall_credibility_rating || 'Analysis Complete';
    }
    
    // Confidence
    const confBar = document.getElementById('compConfidenceBar');
    const confValue = document.getElementById('compConfidenceValue');
    if (confBar && confValue) {
        const conf = synthesis.confidence_in_assessment ?? 0;
        confBar.style.width = `${conf}%`;
        confValue.textContent = `${Math.round(conf)}%`;
    }
    
    // Flags
    renderSynthesisFlags(synthesis);
    
    // Key Findings
    renderKeyFindings(synthesis.key_findings);
    
    // Contradictions
    renderContradictions(synthesis.contradictions);
    
    // Recommendations
    renderRecommendations(synthesis.recommendations);
}

function renderSynthesisFlags(synthesis) {
    const container = document.getElementById('flagsContainer');
    const section = document.getElementById('flagsSection');
    if (!container || !section) return;
    
    const allFlags = [
        ...(synthesis.credibility_flags || []),
        ...(synthesis.bias_flags || []),
        ...(synthesis.manipulation_flags || []),
        ...(synthesis.factual_accuracy_flags || [])
    ];
    
    if (allFlags.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    container.innerHTML = allFlags.map(flag => `
        <div class="flag-item severity-${flag.severity || 'medium'}">
            <span class="flag-severity severity-${flag.severity || 'medium'}">${flag.severity || 'Note'}</span>
            <div class="flag-content">
                <div class="flag-description">${escapeHtml(flag.description)}</div>
                <div class="flag-source">Source: ${escapeHtml(flag.source_mode || flag.category || 'Analysis')}</div>
            </div>
        </div>
    `).join('');
    
    section.style.display = 'block';
}

function renderKeyFindings(findings) {
    const container = document.getElementById('keyFindingsContainer');
    const section = document.getElementById('keyFindingsSection');
    if (!container || !section) return;
    
    if (!findings || findings.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    container.innerHTML = findings.map(finding => `
        <div class="finding-item">
            <div class="finding-text">${escapeHtml(finding.finding)}</div>
            ${finding.supporting_evidence && finding.supporting_evidence.length > 0 ? `
                <div class="finding-evidence">
                    ${finding.supporting_evidence.map(e => escapeHtml(e)).join('<br>')}
                </div>
            ` : ''}
        </div>
    `).join('');
    
    section.style.display = 'block';
}

function renderContradictions(contradictions) {
    const container = document.getElementById('contradictionsContainer');
    const section = document.getElementById('contradictionsSection');
    if (!container || !section) return;
    
    if (!contradictions || contradictions.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    container.innerHTML = contradictions.map(c => `
        <div class="contradiction-item">
            <div class="contradiction-findings">
                <div class="contradiction-finding">
                    <strong>${escapeHtml(c.source_1 || 'Mode 1')}:</strong> ${escapeHtml(c.finding_1)}
                </div>
                <div class="contradiction-vs">VS</div>
                <div class="contradiction-finding">
                    <strong>${escapeHtml(c.source_2 || 'Mode 2')}:</strong> ${escapeHtml(c.finding_2)}
                </div>
            </div>
            <div class="contradiction-explanation">${escapeHtml(c.explanation)}</div>
        </div>
    `).join('');
    
    section.style.display = 'block';
}

function renderRecommendations(recommendations) {
    const container = document.getElementById('recommendationsContainer');
    const section = document.getElementById('recommendationsSection');
    if (!container || !section) return;
    
    if (!recommendations || recommendations.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    container.innerHTML = recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('');
    section.style.display = 'block';
}

// ============================================
// SESSION INFO
// ============================================

function updateComprehensiveSessionInfo(data) {
    const sessionEl = document.getElementById('compSessionId');
    const timeEl = document.getElementById('compProcessingTime');
    const r2Link = document.getElementById('compR2Link');
    const r2Sep = document.getElementById('compR2Sep');
    
    if (sessionEl) sessionEl.textContent = data.session_id || '—';
    if (timeEl) timeEl.textContent = data.total_processing_time ? `${Math.round(data.total_processing_time)}s` : '—';
    
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
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.renderComprehensiveResults = renderComprehensiveResults;
    window.toggleModeReport = toggleModeReport;
}
