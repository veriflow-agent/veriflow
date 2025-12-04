// static/js/renderers/bias.js - Bias Analysis Rendering

// ============================================
// DISPLAY PUBLICATION PROFILE (MBFC DATA)
// ============================================

function displayPublicationProfile(analysis) {
    const profile = analysis.publication_profile;
    const card = document.getElementById('publicationProfileCard');

    if (!profile) {
        // No publication profile - hide the card
        if (card) card.style.display = 'none';
        return;
    }

    // Show the card
    card.style.display = 'block';

    // Publication name
    document.getElementById('profilePublicationName').textContent = profile.name || 'Unknown';

    // Source badge (MBFC vs Local)
    const sourceBadge = document.getElementById('profileSourceBadge');
    if (profile.source === 'mbfc') {
        sourceBadge.textContent = 'MBFC';
        sourceBadge.className = 'profile-source-badge mbfc';
    } else {
        sourceBadge.textContent = 'Local DB';
        sourceBadge.className = 'profile-source-badge local';
    }

    // Political leaning with color
    const leaningEl = document.getElementById('profilePoliticalLeaning');
    const leaning = profile.political_leaning || 'Unknown';
    leaningEl.textContent = capitalizeWords(leaning.replace(/-/g, ' '));
    leaningEl.className = 'profile-value ' + getLeaningClass(leaning);

    // Bias rating
    const biasRating = profile.bias_rating;
    document.getElementById('profileBiasRating').textContent = 
        biasRating !== null && biasRating !== undefined ? `${biasRating.toFixed(1)}/10` : '-';

    // Factual reporting
    document.getElementById('profileFactualReporting').textContent = 
        profile.factual_reporting || '-';

    // Credibility
    document.getElementById('profileCredibility').textContent = 
        profile.credibility_rating || '-';

    // Optional details
    const detailsSection = document.getElementById('profileDetails');
    let hasDetails = false;

    // Ownership
    if (profile.ownership) {
        document.getElementById('profileOwnership').textContent = profile.ownership;
        document.getElementById('profileOwnershipRow').style.display = 'flex';
        hasDetails = true;
    } else {
        document.getElementById('profileOwnershipRow').style.display = 'none';
    }

    // Known biases
    if (profile.known_biases && profile.known_biases.length > 0) {
        document.getElementById('profileKnownBiases').textContent = profile.known_biases.join(', ');
        document.getElementById('profileKnownBiasesRow').style.display = 'flex';
        hasDetails = true;
    } else {
        document.getElementById('profileKnownBiasesRow').style.display = 'none';
    }

    // Failed fact checks
    if (profile.failed_fact_checks && profile.failed_fact_checks.length > 0) {
        document.getElementById('profileFailedFactChecks').textContent = 
            `${profile.failed_fact_checks.length} on record`;
        document.getElementById('profileFailedFactChecksRow').style.display = 'flex';
        hasDetails = true;
    } else {
        document.getElementById('profileFailedFactChecksRow').style.display = 'none';
    }

    detailsSection.style.display = hasDetails ? 'block' : 'none';

    // MBFC link
    const footer = document.getElementById('profileFooter');
    const mbfcLink = document.getElementById('profileMbfcLink');
    if (profile.mbfc_url) {
        mbfcLink.href = profile.mbfc_url;
        footer.style.display = 'block';
    } else {
        footer.style.display = 'none';
    }
}

function getLeaningClass(leaning) {
    if (!leaning) return '';
    leaning = leaning.toLowerCase();
    if (leaning.includes('left')) return 'bias-left';
    if (leaning.includes('right')) return 'bias-right';
    if (leaning.includes('center')) return 'bias-center';
    return '';
}

function capitalizeWords(str) {
    return str.replace(/\b\w/g, char => char.toUpperCase());
}

// ============================================
// DISPLAY BIAS RESULTS
// ============================================

function displayBiasResults() {
    if (!AppState.currentBiasResults || !AppState.currentBiasResults.success) {
        return;
    }

    const analysis = AppState.currentBiasResults.analysis;

    // ✅ NEW: Display publication profile from MBFC
    displayPublicationProfile(analysis);

    const score = analysis.consensus_bias_score || 0;
    const direction = analysis.consensus_direction || 'Unknown';
    const confidence = analysis.confidence || 0;

    document.getElementById('consensusBiasScore').textContent = score.toFixed(1) + '/10';
    document.getElementById('consensusBiasDirection').textContent = direction;
    document.getElementById('biasConfidence').textContent = Math.round(confidence * 100) + '%';

    document.getElementById('biasSessionId').textContent = AppState.currentBiasResults.session_id || '-';
    document.getElementById('biasProcessingTime').textContent = Math.round(AppState.currentBiasResults.processing_time || 0) + 's';

    displayModelAnalysis('gpt', analysis.gpt_analysis);
    displayModelAnalysis('claude', analysis.claude_analysis);
    displayConsensusAnalysis(analysis);
}

// ============================================
// DISPLAY MODEL ANALYSIS
// ============================================

function displayModelAnalysis(model, data) {
    if (!data) return;

    const prefix = model === 'gpt' ? 'gpt' : 'claude';

    document.getElementById(`${prefix}OverallAssessment`).textContent = data.reasoning || '-';

    const indicatorsList = document.getElementById(`${prefix}BiasIndicators`);
    indicatorsList.innerHTML = '';

    if (data.biases_detected && data.biases_detected.length > 0) {
        data.biases_detected.forEach(bias => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${bias.type}</strong> (${bias.severity}/10): ${bias.evidence}`;
            indicatorsList.appendChild(li);
        });
    } else {
        indicatorsList.innerHTML = '<li>No significant bias indicators detected</li>';
    }

    const languageText = data.balanced_aspects ? data.balanced_aspects.join(' • ') : 'Analysis complete';
    document.getElementById(`${prefix}LanguageAnalysis`).textContent = languageText;
}

// ============================================
// DISPLAY CONSENSUS ANALYSIS
// ============================================

function displayConsensusAnalysis(analysis) {
    const agreementList = document.getElementById('areasOfAgreement');
    agreementList.innerHTML = '';
    (analysis.areas_of_agreement || []).forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        agreementList.appendChild(li);
    });

    const disagreementList = document.getElementById('areasOfDisagreement');
    disagreementList.innerHTML = '';
    (analysis.areas_of_disagreement || []).forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        disagreementList.appendChild(li);
    });

    document.getElementById('finalAssessment').textContent = analysis.final_assessment || '-';

    const recommendationsList = document.getElementById('recommendations');
    recommendationsList.innerHTML = '';
    (analysis.recommendations || []).forEach(rec => {
        const li = document.createElement('li');
        li.textContent = rec;
        recommendationsList.appendChild(li);
    });
}

// ============================================
// MODEL TAB SWITCHING FOR BIAS ANALYSIS
// ============================================

function initBiasModelTabs() {
    modelTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Update active tab styling
            modelTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Get selected model
            const model = tab.dataset.model;

            // Show/hide the correct analysis panel
            const gptAnalysis = document.getElementById('gptAnalysis');
            const claudeAnalysis = document.getElementById('claudeAnalysis');
            const consensusAnalysis = document.getElementById('consensusAnalysis');

            if (gptAnalysis) {
                gptAnalysis.style.display = model === 'gpt' ? 'block' : 'none';
            }
            if (claudeAnalysis) {
                claudeAnalysis.style.display = model === 'claude' ? 'block' : 'none';
            }
            if (consensusAnalysis) {
                consensusAnalysis.style.display = model === 'consensus' ? 'block' : 'none';
            }
        });
    });
}
