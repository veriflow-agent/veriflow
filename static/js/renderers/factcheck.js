// static/js/renderers/factcheck.js - Fact Check & LLM Verification Rendering
// VeriFlow Redesign - Minimalist Theme

// ============================================
// DISPLAY VERIFICATION RESULTS (Unified)
// ============================================

function displayVerificationResults() {
    let data, facts, sessionId, duration, pipelineType, auditUrl;

    if (AppState.currentLLMVerificationResults) {
        console.log('Displaying LLM Verification Results');

        if (AppState.currentLLMVerificationResults.factCheck) {
            data = AppState.currentLLMVerificationResults.factCheck;
        } else {
            data = AppState.currentLLMVerificationResults;
        }

        facts = data.results || data.claims || [];
        sessionId = data.session_id || '-';
        duration = data.duration || data.processing_time || 0;
        pipelineType = 'LLM Interpretation Verification';
        auditUrl = data.audit_url || AppState.currentLLMVerificationResults.audit_url;

    } else if (AppState.currentFactCheckResults) {
        console.log('Displaying Web Search Fact-Check Results');

        data = AppState.currentFactCheckResults;
        facts = data.facts || data.claims || [];
        sessionId = data.session_id || '-';
        duration = data.processing_time || data.duration || 0;
        pipelineType = 'Web Search Fact-Checking';
        auditUrl = data.audit_url;

    } else {
        console.error('No verification results available');
        return;
    }

    console.log(`Processing ${facts.length} facts from ${pipelineType}`);

    if (data.success === false) {
        console.error('Verification marked as failed');
        showError('Verification failed. Please try again.');
        return;
    }

    // Calculate statistics
    const totalFacts = facts.length;
    const verifiedFacts = facts.filter(f => 
        (f.verification_score || f.match_score || 0) >= 0.9
    ).length;
    const partialFacts = facts.filter(f => {
        const score = f.verification_score || f.match_score || 0;
        return score >= 0.7 && score < 0.9;
    }).length;
    const unverifiedFacts = facts.filter(f => 
        (f.verification_score || f.match_score || 0) < 0.7
    ).length;

    // Update summary stats
    const verifiedCount = document.getElementById('verifiedCount');
    const issuesCount = document.getElementById('issuesCount');
    const unverifiedCount = document.getElementById('unverifiedCount');

    if (verifiedCount) verifiedCount.textContent = verifiedFacts;
    if (issuesCount) issuesCount.textContent = partialFacts;
    if (unverifiedCount) unverifiedCount.textContent = unverifiedFacts;

    // Update session info
    const sessionIdEl = document.getElementById('sessionId');
    const processingTimeEl = document.getElementById('processingTime');

    if (sessionIdEl) sessionIdEl.textContent = sessionId;
    if (processingTimeEl) processingTimeEl.textContent = Math.round(duration) + 's';

    // Handle R2 link
    const r2Link = document.getElementById('r2Link');
    const r2Sep = document.getElementById('r2Sep');

    if (r2Link && r2Sep && auditUrl) {
        r2Link.href = auditUrl;
        r2Link.style.display = 'inline';
        r2Sep.style.display = 'inline';
    } else if (r2Link && r2Sep) {
        r2Link.style.display = 'none';
        r2Sep.style.display = 'none';
    }

    // Render facts
    if (factsContainer) {
        factsContainer.innerHTML = '';
        facts.forEach((fact, index) => {
            factsContainer.appendChild(createFactCard(fact, index + 1));
        });
    }
}

// Alias for compatibility
function displayFactCheckResults() {
    displayVerificationResults();
}

// ============================================
// CREATE FACT CARD
// ============================================

function createFactCard(fact, number) {
    const card = document.createElement('div');
    const score = fact.verification_score || fact.match_score || 0;
    const scoreClass = getScoreClass(score);
    
    card.className = `fact-card ${scoreClass}`;

    const statementText = fact.claim_text || fact.statement || 'No statement available';
    const reportText = fact.report || fact.assessment || 'No report available';

    // Handle interpretation issues (LLM verification specific)
    let issuesHtml = '';
    if (fact.interpretation_issues && fact.interpretation_issues.length > 0) {
        issuesHtml = `
            <div class="fact-issues">
                <strong>Issues found:</strong>
                <ul>
                    ${fact.interpretation_issues.map(issue => `<li>${escapeHtml(issue)}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    // Handle sources
    let sourcesHtml = '';
    if (fact.cited_source_urls && fact.cited_source_urls.length > 0) {
        const sourceLinks = fact.cited_source_urls.map(url => 
            `<a href="${escapeHtml(url)}" target="_blank" class="source-link">${getDomainFromUrl(url)}</a>`
        ).join(' ');
        sourcesHtml = `<div class="fact-sources">Sources: ${sourceLinks}</div>`;
    } else if (fact.sources_used && fact.sources_used.length > 0) {
        const sourceLinks = fact.sources_used.map(url => 
            `<a href="${escapeHtml(url)}" target="_blank" class="source-link">${getDomainFromUrl(url)}</a>`
        ).join(' ');
        sourcesHtml = `<div class="fact-sources">Sources: ${sourceLinks}</div>`;
    }

    // Build card HTML
    card.innerHTML = `
        <div class="fact-header">
            <span class="fact-number">#${number}</span>
            <span class="fact-verdict ${scoreClass}">${getScoreLabel(score)}</span>
        </div>
        <div class="fact-claim">${escapeHtml(statementText)}</div>
        <div class="fact-explanation">${escapeHtml(reportText)}</div>
        ${issuesHtml}
        ${sourcesHtml}
    `;

    return card;
}
