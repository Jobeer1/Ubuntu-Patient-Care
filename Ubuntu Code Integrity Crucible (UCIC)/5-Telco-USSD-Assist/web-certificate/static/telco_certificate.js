const certificateData = {
    projectName: 'Telco USSD Assist MCP',
    overallScore: '32 / 50',
    scoreMeta: '64% Technical Merit',
    summary: {
        project: 'Telco USSD Assist MCP',
        date: 'November 15, 2025',
        authority: 'Ubuntu Code Integrity Crucible',
        status: 'Publicly Auditable',
        repository: 'github.com/Jobeer1/Ubuntu-Patient-Care'
    },
    competencies: [
        {
            name: 'Technical Architecture',
            score: '7 / 10',
            description: 'Achieved solid code quality with 15 regression-protecting unit tests.'
        },
        {
            name: 'Mission Alignment',
            score: '8.5 / 10',
            description: 'Directly supports Ghanaian telco support flows with verified knowledge base.'
        },
        {
            name: 'API Integration',
            score: 'VERIFIED',
            description: 'Multiple MCP-compatible clients operational: Claude, Cursor, Gemini.'
        },
        {
            name: 'Deployment Status',
            score: 'VERIFIED',
            description: 'Live endpoint deployed on FastMCP Cloud with observability hooks.'
        }
    ],
    integrity: [
        'Verifiable codebase with public GitHub history and audit trail.',
        'Real-world telco need validated through support-team interviews.',
        'Full UCIC analysis committed to immutable repository logs.'
    ],
    reviewLead: 'Detailed Technical Review by GitHub Copilot',
    founders: [
        {
            name: 'Dr. Jodogn',
            title: 'Founder, Ubuntu Patient Care'
        },
        {
            name: 'Dr. Tom Zubiri',
            title: 'Technical Authority, UCIC Chief Integrity Officer (AI)'
        }
    ],
    referenceCode: 'UCIC-TELCO-2211 • Valid through May 2026',
    referenceLink: 'Audit Log: github.com/Jobeer1/Ubuntu-Patient-Care',
    generatedDate: new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    })
};

const $ = (selector) => document.querySelector(selector);

function populateCertificate(data) {
    $('#project-name').textContent = data.projectName;
    $('#overall-score').textContent = data.overallScore;
    $('#score-meta').textContent = data.scoreMeta;

    $('#summary-project').textContent = data.summary.project;
    $('#summary-date').textContent = data.summary.date;
    $('#summary-authority').textContent = data.summary.authority;
    $('#summary-status').textContent = data.summary.status;
    $('#summary-repo').textContent = data.summary.repository;

    const competencyList = document.getElementById('competency-list');
    competencyList.innerHTML = '';
    data.competencies.forEach((comp) => {
        const li = document.createElement('li');
        li.className = 'competency';
        li.innerHTML = `
            <div class="competency__badge">${comp.score}</div>
            <div class="competency__details">
                <h3>${comp.name}</h3>
                <p>${comp.description}</p>
            </div>
        `;
        competencyList.appendChild(li);
    });

    const integrityList = document.getElementById('integrity-list');
    integrityList.innerHTML = '';
    data.integrity.forEach((item) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>✓</span><p>${item}</p>`;
        integrityList.appendChild(li);
    });

    document.getElementById('review-lead').textContent = data.reviewLead;
    document.getElementById('founder-one-name').textContent = data.founders[0].name;
    document.getElementById('founder-one-title').textContent = data.founders[0].title;
    document.getElementById('founder-two-name').textContent = data.founders[1].name;
    document.getElementById('founder-two-title').textContent = data.founders[1].title;

    document.getElementById('reference-code').textContent = data.referenceCode;
    document.getElementById('reference-link').textContent = data.referenceLink;
    document.getElementById('generated-date').textContent = `Certificate Generated: ${data.generatedDate}`;
}

populateCertificate(certificateData);
