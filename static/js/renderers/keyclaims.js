// static/js/renderers/keyclaims.js - Key Claims Rendering
// VeriFlow Redesign - Minimalist Theme

// ============================================
// DISPLAY KEY CLAIMS RESULTS
// ============================================

function displayKeyClaimsResults() {
    if (!AppState.currentKeyClaimsResults) {
        console.error('No key claims results available');
        return;
    }

    console.log('Displaying Key Claims Results:', AppState.currentKeyClaimsResults);

    const data = AppState.currentKeyClaimsResults;
    const claims = data.key_claims || [];
    const summary = data.summary || {};

    // Update summary stats if elements exist
    const kcTotalClaims = document.getElementById('kcTotalClaims');
    const kcVerifiedCount = document.getElementById('kcVerifiedCount');
    const kcPartialCount = document.getElementById('kcPartialCount');
    const kcUnverifiedCount = document.getElementById('kcUnverifiedCount');
    const kcOverallCredibility = document.getElementById('kcOverallCredibility');

    if (kcTotalClaims) kcTotalClaims.textContent = summary.total_key_claims || claims.length || 0;
    if (kcVerifiedCount) kcVerifiedCount.textContent = summary.verified_count || 0;
    if (kcPartialCount) kcPartialCount.textContent = summary.partial_count || 0;
    if (kcUnverifiedCount) kcUnverifiedCount.textContent = summary.unverified_count || 0;
    if (kcOverallCredibility) kcOverallCredibility.textContent = summary.overall_credibility || '-';

    // Session info
    const kcSessionId = document.getElementById('kcSessionId');
    const kcProcessingTime = document.getElementById('kcProcessingTime');

    if (kcSessionId) kcSessionId.textContent = data.session_id || '-';
    if (kcProcessingTime) kcProcessingTime.textContent = Math.round(data.processing_time || 0) + 's';

    // R2 link
    const r2Link = document.getElementById('kcR2Link');
    const r2Sep = document.getElementById('kcR2Sep');

    if (r2Link && r2Sep) {
        if (data.r2_upload && data.r2_upload.success && data.r2_upload.url) {
            r2Link.href = data.r2_upload.url;
            r2Link.style.display = 'inline';
            r2Sep.style.display = 'inline';
        } else {
            r2Link.style.display = 'none';
            r2Sep.style.display = 'none';
        }
    }

    // Render key claims list
    if (keyClaimsContainer) {
        keyClaimsContainer.innerHTML = '';
        
        if (claims.length === 0) {
            keyClaimsContainer.innerHTML = '<p class="no-results">No key claims were identified in this content.</p>';
            return;
        }

        claims.forEach((claim, index) => {
            keyClaimsContainer.appendChild(createKeyClaimCard(claim, index + 1));
        });
    }
}

// ============================================
// CREATE KEY CLAIM CARD
// ============================================

function createKeyClaimCard(claim, number) {
    const card = document.createElement('div');
    const score = claim.match_score || 0;
    const scoreClass = getScoreClass(score);

    card.className = `fact-card key-claim-card ${scoreClass}`;

    const statementText = claim.statement || 'No statement available';
    const reportText = claim.report || claim.assessment || 'No report available';

    // Check for false/debunked claims
    const isDebunked = score <= 0.1 && score > 0;

    // Build card HTML
    card.innerHTML = `
        <div class="fact-header">
            <div class="fact-title-row">
                <span class="fact-number">#${number}</span>
                <span class="claim-type-badge">Key Claim</span>
                ${isDebunked ? '<span class="debunked-badge">False</span>' : ''}
            </div>
            <span class="fact-verdict ${scoreClass}">${Math.round(score * 100)}%</span>
        </div>
        <div class="fact-claim">${escapeHtml(statementText)}</div>
        <div class="fact-explanation">${escapeHtml(reportText)}</div>
    `;

    // Add sources if available
    if (claim.sources && claim.sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'fact-sources';
        sourcesDiv.innerHTML = 'Sources: ' + claim.sources.map(url => 
            `<a href="${escapeHtml(url)}" target="_blank" class="source-link">${getDomainFromUrl(url)}</a>`
        ).join(' ');
        card.appendChild(sourcesDiv);
    }

    return card;
}
