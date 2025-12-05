// ============================================================================
// QUBIC Web App - Frontend JavaScript
// South African Rugby Healthcare Contribution DAO
// ============================================================================

const API_BASE = `${window.location.protocol}//${window.location.host}/api`;
let currentPage = 1;
const pageSize = 10;
let allContributors = [];
let charts = {};

// ============================================================================
// EMBEDDED MOCK DATA - SOUTH AFRICAN HEALTHCARE TEAM
// ============================================================================

const MOCK_CONTRIBUTORS = [
    // Ranked contributions with real scoring from QUBIC system
    { id: "contrib_ai_teleradiology", name: "AI Teleradiology Dashboard", github: "ubuntu-patient-care/ai-teleradiology", score: 92, tier: "platinum", module: "PACS Module", contributions: 78, avatar: "https://i.pravatar.cc/150?img=42", rank: 1, breakdown: { code_quality: 28, healthcare_impact: 29, documentation: 30, innovation: 27, integration: 28 }, url: "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/specs/ai-teleradiology" },
    { id: "contrib_gotg_version", name: "GOTG Battle-Ready Edition", github: "ubuntu-patient-care/gotg", score: 89, tier: "gold", module: "Humanitarian System", contributions: 72, avatar: "https://i.pravatar.cc/150?img=88", rank: 2, breakdown: { code_quality: 28, healthcare_impact: 29, documentation: 29, innovation: 28, integration: 28 }, url: "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/GOTG_version" },
    { id: "contrib_cloud_orchestration", name: "Cloud Orchestration AI Engine", github: "ubuntu-patient-care/cloud-orchestration", score: 87, tier: "gold", module: "Enterprise Automation", contributions: 68, avatar: "https://i.pravatar.cc/150?img=77", rank: 3, breakdown: { code_quality: 26, healthcare_impact: 28, documentation: 27, innovation: 26, integration: 25 }, url: "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/cloud_orchestration" },
    { id: "contrib_ibm_hackathon", name: "IBM Hackathon Submission", github: "ubuntu-patient-care/ibm-hackathon", score: 88, tier: "gold", module: "Enterprise System", contributions: 65, avatar: "https://i.pravatar.cc/150?img=99", rank: 4, breakdown: { code_quality: 27, healthcare_impact: 26, documentation: 27, innovation: 26, integration: 27 }, url: "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/IBM-HACKATHON-SUBMISSION" },
    { id: "user_0", name: "Dr. Thembi Dlamini", github: "thembi_md", score: 95, tier: "platinum", module: "PACS Module", contributions: 42, avatar: "https://i.pravatar.cc/150?img=0", rank: 5, breakdown: { code_quality: 28, healthcare_impact: 24, documentation: 19, innovation: 15, integration: 9 } },
    { id: "user_1", name: "Prof. Njabulo Mthembu", github: "njabulo_prof", score: 92, tier: "platinum", module: "RIS Module", contributions: 38, avatar: "https://i.pravatar.cc/150?img=1", rank: 6, breakdown: { code_quality: 27, healthcare_impact: 23, documentation: 19, innovation: 14, integration: 9 } },
    { id: "user_2", name: "Dr. Amahle Khumalo", github: "amahle_dr", score: 89, tier: "gold", module: "Dictation/Reporting", contributions: 35, avatar: "https://i.pravatar.cc/150?img=2", rank: 7, breakdown: { code_quality: 26, healthcare_impact: 22, documentation: 18, innovation: 13, integration: 8 } },
    { id: "user_3", name: "Dr. Sipho Ngcobo", github: "sipho_ngcobo", score: 87, tier: "gold", module: "Medical Billing", contributions: 33, avatar: "https://i.pravatar.cc/150?img=3", rank: 8, breakdown: { code_quality: 25, healthcare_impact: 22, documentation: 17, innovation: 13, integration: 8 } },
    { id: "user_4", name: "Dr. Naledi Mkhize", github: "naledi_mk", score: 85, tier: "gold", module: "Security/Compliance", contributions: 31, avatar: "https://i.pravatar.cc/150?img=4", rank: 9, breakdown: { code_quality: 25, healthcare_impact: 21, documentation: 17, innovation: 12, integration: 8 } },
    { id: "user_5", name: "Dr. Karabo Sesoko", github: "karabo_ses", score: 82, tier: "gold", module: "AI/ML Models", contributions: 29, avatar: "https://i.pravatar.cc/150?img=5", rank: 10, breakdown: { code_quality: 24, healthcare_impact: 20, documentation: 16, innovation: 12, integration: 8 } },
    { id: "user_6", name: "Dr. Busiswa Ndaba", github: "busiswa_nd", score: 79, tier: "silver", module: "PACS Module", contributions: 27, avatar: "https://i.pravatar.cc/150?img=6", rank: 11, breakdown: { code_quality: 23, healthcare_impact: 20, documentation: 16, innovation: 11, integration: 7 } },
    { id: "user_7", name: "Dr. Thandi Mtshali", github: "thandi_mts", score: 77, tier: "silver", module: "RIS Module", contributions: 25, avatar: "https://i.pravatar.cc/150?img=7", rank: 12, breakdown: { code_quality: 22, healthcare_impact: 19, documentation: 15, innovation: 11, integration: 7 } },
    { id: "user_8", name: "Dr. Lerato Mokoena", github: "lerato_mok", score: 75, tier: "silver", module: "Dictation/Reporting", contributions: 23, avatar: "https://i.pravatar.cc/150?img=8", rank: 13, breakdown: { code_quality: 22, healthcare_impact: 19, documentation: 15, innovation: 10, integration: 7 } },
    { id: "user_9", name: "Dr. Nolwazi Zwane", github: "nolwazi_zw", score: 72, tier: "silver", module: "Medical Billing", contributions: 21, avatar: "https://i.pravatar.cc/150?img=9", rank: 14, breakdown: { code_quality: 21, healthcare_impact: 18, documentation: 15, innovation: 10, integration: 6 } },
];

const TIERS = {
    'platinum': { votes: 5, icon: '🏆', color: '#FFD700', name: 'Platinum' },
    'gold': { votes: 3, icon: '🥇', color: '#FFA500', name: 'Gold' },
    'silver': { votes: 2, icon: '🥈', color: '#C0C0C0', name: 'Silver' },
    'bronze': { votes: 1, icon: '🥉', color: '#CD7F32', name: 'Bronze' },
    'recognized': { votes: 1, icon: '⭐', color: '#87CEEB', name: 'Recognized' }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 QUBIC App Initializing...');
    await loadStatistics();
    await loadLeaderboard();
    await loadScoringInfo();
    await loadDAOInfo();
    await loadAnalytics();
    setupEventListeners();
    console.log('✅ QUBIC App Ready!');
});

// ============================================================================
// API CALLS WITH FALLBACK
// ============================================================================

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.warn('API Error, using mock data:', error);
        return null;
    }
}

// ============================================================================
// STATISTICS SECTION
// ============================================================================

async function loadStatistics() {
    console.log('📊 Loading statistics...');
    
    const data = await fetchAPI('/statistics');
    
    if (data && data.data) {
        const stats = data.data;
        document.getElementById('total-contributors').textContent = stats.total_contributors;
        document.getElementById('total-contributions').textContent = stats.total_contributions;
        document.getElementById('avg-score').textContent = stats.average_score;
        document.getElementById('monthly-rewards').textContent = `${stats.monthly_rewards} UC`;
    } else {
        // Use mock data
        document.getElementById('total-contributors').textContent = MOCK_CONTRIBUTORS.length;
        document.getElementById('total-contributions').textContent = '285';
        document.getElementById('avg-score').textContent = '83.4';
        document.getElementById('monthly-rewards').textContent = '30 UC';
    }
}

// ============================================================================
// LEADERBOARD SECTION
// ============================================================================

async function loadLeaderboard(page = 1) {
    console.log(`📋 Loading leaderboard page ${page}...`);
    const data = await fetchAPI(`/leaderboard?page=${page}&limit=${pageSize}`);
    
    if (data && data.data) {
        allContributors = data.data;
        renderLeaderboard(data.data);
        updatePagination(page, data.total);
    } else {
        // Use mock data - sort by score descending
        const sorted = [...MOCK_CONTRIBUTORS].sort((a, b) => b.score - a.score);
        renderLeaderboard(sorted);
        updatePagination(page, sorted.length);
    }
}

function renderLeaderboard(contributors) {
    const tbody = document.getElementById('leaderboardBody');
    tbody.innerHTML = '';

    if (contributors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No contributors found</td></tr>';
        return;
    }

    contributors.forEach((contributor, index) => {
        const row = document.createElement('tr');
        const tierClass = `tier-${contributor.tier}`;
        const tier = TIERS[contributor.tier] || TIERS.recognized;
        
        row.innerHTML = `
            <td>#${index + 1}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <img src="${contributor.avatar}" alt="${contributor.name}" 
                         style="width: 32px; height: 32px; border-radius: 50%;">
                    <span class="contributor-name" onclick="showContributorDetail('${contributor.id}')">
                        ${contributor.name}
                    </span>
                </div>
            </td>
            <td><strong style="color: ${tier.color};">${contributor.score}</strong></td>
            <td><span class="tier-badge ${tierClass}" style="background: ${tier.color}; color: white;">${tier.name}</span></td>
            <td>${contributor.module}</td>
            <td>${contributor.contributions}</td>
            <td>
                <button class="btn btn-secondary" style="padding: 0.5rem 1rem; font-size: 0.9rem;"
                        onclick="showContributorDetail('${contributor.id}')">View</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updatePagination(page, total) {
    const totalPages = Math.ceil(total / pageSize);
    currentPage = page;
    
    document.getElementById('pageInfo').textContent = `Page ${page} of ${totalPages}`;
    document.getElementById('prevBtn').disabled = page <= 1;
    document.getElementById('nextBtn').disabled = page >= totalPages;
}

function nextPage() {
    loadLeaderboard(currentPage + 1);
    window.scrollTo(0, 0);
}

function previousPage() {
    if (currentPage > 1) {
        loadLeaderboard(currentPage - 1);
        window.scrollTo(0, 0);
    }
}

// ============================================================================
// SEARCH & FILTER
// ============================================================================

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const tierFilter = document.getElementById('tierFilter');

    searchInput.addEventListener('input', debounce(handleSearch, 300));
    tierFilter.addEventListener('change', handleTierFilter);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function handleSearch(event) {
    const query = event.target.value.trim();
    
    if (query.length < 2) {
        loadLeaderboard();
        return;
    }

    console.log(`🔍 Searching for: ${query}`);
    const data = await fetchAPI(`/search?q=${encodeURIComponent(query)}`);
    
    if (data && data.data) {
        renderLeaderboard(data.data);
        document.getElementById('pageInfo').textContent = `${data.results} results`;
    } else {
        // Search mock data
        const results = MOCK_CONTRIBUTORS.filter(c =>
            c.name.toLowerCase().includes(query.toLowerCase()) ||
            c.github.toLowerCase().includes(query.toLowerCase()) ||
            c.module.toLowerCase().includes(query.toLowerCase())
        );
        renderLeaderboard(results);
        document.getElementById('pageInfo').textContent = `${results.length} results`;
    }
}

function handleTierFilter(event) {
    const tier = event.target.value;
    
    if (!tier) {
        loadLeaderboard();
        return;
    }

    console.log(`🎯 Filtering by tier: ${tier}`);
    loadLeaderboard(1);
}

// ============================================================================
// CONTRIBUTOR DETAILS MODAL
// ============================================================================

async function showContributorDetail(contributorId) {
    console.log(`👤 Loading contributor details: ${contributorId}`);
    const data = await fetchAPI(`/contributor/${contributorId}`);
    
    let contributor;
    if (data && data.data) {
        contributor = data.data;
    } else {
        // Use mock data - find by ID
        const userId = `user_${contributorId}`;
        contributor = MOCK_CONTRIBUTORS.find(c => c.id === userId);
        if (!contributor) {
            alert('Contributor not found');
            return;
        }
    }

    const modal = document.getElementById('contributorModal');
    const modalBody = document.getElementById('modalBody');
    const tier = TIERS[contributor.tier] || TIERS.contributor;

    modalBody.innerHTML = `
        <div class="contributor-detail">
            <div style="display: flex; gap: 2rem; margin-bottom: 2rem;">
                <img src="${contributor.avatar}" alt="${contributor.name}" 
                     style="width: 120px; height: 120px; border-radius: 50%; border: 4px solid ${tier.color};">
                <div>
                    <h2>${contributor.name}</h2>
                    <p style="color: var(--text); margin-bottom: 1rem;">@${contributor.github}</p>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                        <span class="tier-badge tier-${contributor.tier}" style="background: ${tier.color}; color: white;">
                            ${tier.name}
                        </span>
                        <span style="background: ${tier.color}; color: white; padding: 0.5rem 1rem; border-radius: 20px;">
                            Score: ${contributor.score}
                        </span>
                    </div>
                </div>
            </div>

            <div class="detail-row">
                <span class="detail-label">Rank</span>
                <span>#${contributor.rank || 1}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Total Contributions</span>
                <span>${contributor.contributions}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Primary Module</span>
                <span>${contributor.module}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Voting Power</span>
                <span>${tier.voting_power} votes</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Governance Eligible</span>
                <span>${contributor.score >= 80 ? '✅ Yes' : '❌ No'}</span>
            </div>

            <h3 style="margin-top: 2rem; margin-bottom: 1rem;">Score Breakdown</h3>
            ${renderScoreBreakdown(contributor.breakdown)}
        </div>
    `;

    modal.style.display = 'block';
}

function renderScoreBreakdown(breakdown) {
    let html = '<div style="margin-bottom: 2rem;">';
    for (const [key, value] of Object.entries(breakdown)) {
        const label = key.replace(/_/g, ' ').toUpperCase();
        const percentage = Math.round((value / 100) * 100);
        html += `
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span>${label}</span>
                    <span><strong>${value}</strong> / 100</span>
                </div>
                <div style="background: #E5E7EB; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, var(--primary), var(--secondary)); 
                                height: 100%; width: ${percentage}%;"></div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    return html;
}

function renderContributionTimeline(timeline) {
    let html = '<div>';
    timeline.slice(0, 5).forEach(item => {
        const date = new Date(item.date).toLocaleDateString();
        const icon = getContributionIcon(item.type);
        html += `
            <div style="padding: 0.75rem 0; border-bottom: 1px solid var(--border);">
                <span>${icon} ${item.type}</span> - ${date} (Impact: ${item.impact}/100)
            </div>
        `;
    });
    html += '</div>';
    return html;
}

function renderRewardsHistory(history) {
    let html = '<table style="width: 100%; text-align: center;">';
    html += '<tr style="background: #F3F4F6;"><th style="padding: 0.75rem;">Month</th><th>Reward</th><th>Rank</th></tr>';
    history.forEach(item => {
        html += `<tr><td style="padding: 0.75rem;">${item.month}</td><td>${item.reward}</td><td>${item.rank}</td></tr>`;
    });
    html += '</table>';
    return html;
}

function getContributionIcon(type) {
    const icons = {
        'feature': '✨',
        'bugfix': '🐛',
        'docs': '📚',
        'test': '✅'
    };
    return icons[type] || '📝';
}

function closeModal() {
    document.getElementById('contributorModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('contributorModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

// ============================================================================
// SCORING SECTION
// ============================================================================

async function loadScoringInfo() {
    console.log('📐 Loading scoring framework...');
    const data = await fetchAPI('/scoring');
    
    let aiScoringInfo;
    if (data && data.data) {
        aiScoringInfo = data.data.ai_evaluation;
    } else {
        // Use mock scoring data
        aiScoringInfo = {
            model: 'QUBIC-AI-v2.1',
            status: 'Active',
            confidence: 0.92,
            evaluation_time_ms: 247,
            factors: {
                code_quality: 0.28,
                healthcare_impact: 0.25,
                documentation: 0.20,
                innovation: 0.18,
                integration: 0.09
            }
        };
    }

    const aiHTML = `
        <div style="background: rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 8px;">
            <p><strong>Model:</strong> ${aiScoringInfo.model}</p>
            <p><strong>Status:</strong> <span style="color: #10B981;">● ${aiScoringInfo.status}</span></p>
            <p><strong>Confidence:</strong> ${(aiScoringInfo.confidence * 100).toFixed(1)}%</p>
            <p><strong>Evaluation Time:</strong> ${aiScoringInfo.evaluation_time_ms}ms</p>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.2);">
                ${Object.entries(aiScoringInfo.factors).map(([key, value]) => `
                    <p><small>${key.replace(/_/g, ' ').charAt(0).toUpperCase() + key.replace(/_/g, ' ').slice(1)}: ${(value * 100).toFixed(0)}%</small></p>
                `).join('')}
            </div>
        </div>
    `;
    document.getElementById('aiScoringInfo').innerHTML = aiHTML;
}

// ============================================================================
// DAO SECTION
// ============================================================================

async function loadDAOInfo() {
    console.log('🗳️ Loading DAO information...');
    const data = await fetchAPI('/dao');
    
    let daoData;
    if (data && data.data) {
        daoData = data.data;
    } else {
        // Use mock DAO data
        daoData = {
            total_tokens: '1,000,000 UC',
            treasury: {
                monthly_rewards: '50,000 UC',
                development_fund: '300,000 UC',
                emergency_reserve: '200,000 UC'
            },
            voting_system: {
                governance_types: [
                    {
                        type: 'Tactical Decisions',
                        approval_threshold: 50,
                        quorum: 30,
                        examples: ['Feature prioritization', 'Module updates', 'Documentation standards']
                    },
                    {
                        type: 'Strategic Decisions',
                        approval_threshold: 66,
                        quorum: 40,
                        examples: ['New modules', 'Major rewrites', 'DAO policy changes']
                    },
                    {
                        type: 'Critical Decisions',
                        approval_threshold: 75,
                        quorum: 50,
                        examples: ['Treasury management', 'Blockchain upgrades', 'Emergency protocols']
                    }
                ]
            }
        };
    }

    // Voting Power
    const votingPowerList = document.getElementById('votingPowerList');
    votingPowerList.innerHTML = Object.entries(TIERS).map(([tier, info]) => `
        <li>${tier.toUpperCase()}: ${info.voting_power || 0} vote${(info.voting_power || 0) !== 1 ? 's' : ''}</li>
    `).join('');

    // Treasury
    const treasuryInfo = document.getElementById('treasuryInfo');
    treasuryInfo.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">Total Pool</span>
            <span>${daoData.total_tokens}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Monthly Rewards</span>
            <span>${daoData.treasury.monthly_rewards}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Development Fund</span>
            <span>${daoData.treasury.development_fund}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Emergency Reserve</span>
            <span>${daoData.treasury.emergency_reserve}</span>
        </div>
    `;

    // Governance Types
    const governanceTypes = document.getElementById('governanceTypes');
    governanceTypes.innerHTML = daoData.voting_system.governance_types.map(gov => `
        <div style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
            <strong style="color: var(--primary);">${gov.type}</strong>
            <div style="margin-top: 0.5rem; font-size: 0.9rem;">
                <p>Approval: ${gov.approval_threshold}% | Quorum: ${gov.quorum}%</p>
                <p>Examples: ${gov.examples.join(', ')}</p>
            </div>
        </div>
    `).join('');
}



// ============================================================================
// ANALYTICS SECTION
// ============================================================================

async function loadAnalytics() {
    console.log('📈 Loading analytics...');
    const data = await fetchAPI('/analytics');
    
    let analytics;
    if (data && data.data) {
        analytics = data.data;
    } else {
        // Use mock analytics data
        analytics = {
            module_breakdown: {
                'PACS Module': 28,
                'Medical Billing': 25,
                'Dictation Reporting': 22,
                'RIS Module': 15,
                'Other': 10
            },
            contribution_types: {
                'Bug Fix': 35,
                'Feature': 30,
                'Documentation': 20,
                'Testing': 15
            },
            monthly_trends: {
                'Jan': 45, 'Feb': 52, 'Mar': 48, 'Apr': 61,
                'May': 58, 'Jun': 72, 'Jul': 68, 'Aug': 75,
                'Sep': 82, 'Oct': 78, 'Nov': 85, 'Dec': 92
            },
            tier_distribution: {
                'Platinum': 5,
                'Gold': 8,
                'Silver': 15,
                'Bronze': 28,
                'Contributor': 44
            }
        };
    }
    renderCharts(analytics);
}

function renderCharts(analytics) {
    // Module Breakdown Chart (Doughnut)
    const tierCtx = document.getElementById('tierChart')?.getContext('2d');
    if (tierCtx && charts.tier) charts.tier.destroy();
    if (tierCtx) {
        charts.tier = new Chart(tierCtx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(analytics.module_breakdown),
                datasets: [{
                    data: Object.values(analytics.module_breakdown),
                    backgroundColor: [
                        '#165B33',
                        '#27AE60',
                        '#FFD700',
                        '#F59E0B',
                        '#3B82F6'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    // Contribution Types Chart (Pie)
    const scoreCtx = document.getElementById('scoreChart')?.getContext('2d');
    if (scoreCtx && charts.score) charts.score.destroy();
    if (scoreCtx) {
        charts.score = new Chart(scoreCtx, {
            type: 'pie',
            data: {
                labels: Object.keys(analytics.contribution_types),
                datasets: [{
                    data: Object.values(analytics.contribution_types),
                    backgroundColor: [
                        '#165B33',
                        '#27AE60',
                        '#FFD700',
                        '#F59E0B'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'right' }
                }
            }
        });
    }

    // Monthly Trends Chart (Line)
    const moduleCtx = document.getElementById('moduleChart')?.getContext('2d');
    if (moduleCtx && charts.module) charts.module.destroy();
    if (moduleCtx) {
        charts.module = new Chart(moduleCtx, {
            type: 'line',
            data: {
                labels: Object.keys(analytics.monthly_trends),
                datasets: [{
                    label: 'Contributions',
                    data: Object.values(analytics.monthly_trends),
                    borderColor: '#165B33',
                    backgroundColor: 'rgba(22, 91, 51, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#FFD700',
                    pointBorderColor: '#165B33',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true }
                }
            }
        });
    }

    // Tier Distribution Chart (Bar)
    const contributionsCtx = document.getElementById('contributionsChart')?.getContext('2d');
    if (contributionsCtx && charts.contributions) charts.contributions.destroy();
    if (contributionsCtx) {
        charts.contributions = new Chart(contributionsCtx, {
            type: 'bar',
            data: {
                labels: Object.keys(analytics.tier_distribution),
                datasets: [{
                    label: 'Contributors by Tier',
                    data: Object.values(analytics.tier_distribution),
                    backgroundColor: [
                        '#D4AF37',
                        '#FFD700',
                        '#C0C0C0',
                        '#CD7F32',
                        '#165B33'
                    ]
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true }
                }
            }
        });
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function scrollTo(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

console.log('✅ QUBIC App Script Loaded');
