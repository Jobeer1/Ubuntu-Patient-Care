// Demo Frontend JavaScript
// Simulates the Ubuntu Patient Care AI Training Pipeline

let recordsToday = 0;
let jobCounter = 0;
let auditCounter = 0;

// Console logging
function logToConsole(message, type = 'info') {
    const console = document.getElementById('console');
    const line = document.createElement('div');
    line.className = 'console-line';
    
    const prompt = document.createElement('span');
    prompt.className = 'console-prompt';
    prompt.textContent = '$';
    
    const text = document.createElement('span');
    text.className = `console-text console-${type}`;
    text.textContent = message;
    
    line.appendChild(prompt);
    line.appendChild(text);
    console.appendChild(line);
    
    // Auto-scroll to bottom
    console.scrollTop = console.scrollHeight;
}

function clearConsole() {
    const console = document.getElementById('console');
    console.innerHTML = `
        <div class="console-line">
            <span class="console-prompt">$</span>
            <span class="console-text">Console cleared</span>
        </div>
    `;
}

// Update stage status
function updateStage(stageNum, status) {
    const stage = document.getElementById(`stage-${stageNum}`);
    const statusEl = stage.querySelector('.stage-status');
    
    stage.classList.remove('stage-active');
    
    if (status === 'active') {
        stage.classList.add('stage-active');
        statusEl.textContent = 'Active';
    } else if (status === 'complete') {
        statusEl.textContent = 'Complete';
        statusEl.style.color = 'var(--success)';
    } else if (status === 'processing') {
        statusEl.textContent = 'Processing';
        statusEl.style.color = 'var(--warning)';
    }
}

// Simulate file upload from clinic
function simulateUpload() {
    const timestamp = new Date().toLocaleTimeString();
    const fileNum = Math.floor(Math.random() * 1000);
    const recordCount = Math.floor(Math.random() * 50) + 20;
    
    recordsToday += recordCount;
    document.getElementById('records-today').textContent = recordsToday;
    
    logToConsole(`[${timestamp}] New data detected from clinic`, 'success');
    logToConsole(`Downloading batch_manifest_${fileNum}.json...`);
    
    // Update file list
    const fileList = document.getElementById('file-list');
    if (fileList.querySelector('.empty-state')) {
        fileList.innerHTML = '';
    }
    
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <div>
            <div class="file-name">batch_manifest_${fileNum}.json</div>
            <div style="font-size: 12px; color: var(--gray); margin-top: 4px;">
                ${recordCount} records • ${timestamp}
            </div>
        </div>
        <span class="file-status status-processing">Processing</span>
    `;
    fileList.insertBefore(fileItem, fileList.firstChild);
    
    // Simulate processing
    setTimeout(() => {
        logToConsole('✓ POPIA compliance validation passed', 'success');
        logToConsole(`Uploading to GCS: gs://ubuntu-training-data-private/training_data/...`);
        
        setTimeout(() => {
            const statusEl = fileItem.querySelector('.file-status');
            statusEl.textContent = 'Synced';
            statusEl.className = 'file-status status-success';
            
            logToConsole('✓ Upload complete. File marked as processed.', 'success');
            logToConsole(`Ready for training with ${recordCount} new records`, 'success');
            
            // Update stage
            updateStage(1, 'complete');
            updateStage(2, 'active');
        }, 2000);
    }, 1500);
}

// Start training job
function startTraining() {
    if (recordsToday === 0) {
        logToConsole('⚠ No training data available. Upload data first.', 'warning');
        return;
    }
    
    jobCounter++;
    const jobId = `vertex-ai-job-${Date.now().toString().slice(-8)}`;
    const timestamp = new Date().toLocaleTimeString();
    
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    logToConsole('VERTEX AI CUSTOM TRAINING JOB CONFIGURATION', 'info');
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    logToConsole(`Job ID: ${jobId}`);
    logToConsole('Machine Type: n1-highmem-8');
    logToConsole('Accelerator: NVIDIA_TESLA_T4 x1', 'success');
    logToConsole('Estimated Training Time: 2-4 hours (vs 12+ hours on CPU)', 'success');
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    
    // Update job list
    const jobList = document.getElementById('job-list');
    if (jobList.querySelector('.empty-state')) {
        jobList.innerHTML = '';
    }
    
    const jobItem = document.createElement('div');
    jobItem.className = 'job-item';
    jobItem.innerHTML = `
        <div>
            <div class="job-name">Whisper Fine-tune #${jobCounter}</div>
            <div style="font-size: 12px; color: var(--gray); margin-top: 4px;">
                ${jobId} • ${timestamp}
            </div>
        </div>
        <span class="job-status status-processing">Training</span>
    `;
    jobList.insertBefore(jobItem, jobList.firstChild);
    
    // Update stage
    updateStage(2, 'processing');
    
    // Simulate training progress
    let epoch = 1;
    const trainingInterval = setInterval(() => {
        if (epoch <= 5) {
            const loss = (0.45 - (epoch * 0.05)).toFixed(3);
            const accuracy = (0.88 + (epoch * 0.015)).toFixed(3);
            logToConsole(`Epoch ${epoch}/5: loss=${loss}, accuracy=${accuracy}`);
            epoch++;
        } else {
            clearInterval(trainingInterval);
            
            // Training complete
            logToConsole('═══════════════════════════════════════════════════════════', 'success');
            logToConsole('✓ TRAINING COMPLETE', 'success');
            logToConsole('Final Validation Accuracy: 0.963 (+8.5% improvement)', 'success');
            logToConsole('Model saved to GCS', 'success');
            logToConsole('═══════════════════════════════════════════════════════════', 'success');
            
            const statusEl = jobItem.querySelector('.job-status');
            statusEl.textContent = 'Complete';
            statusEl.className = 'job-status status-success';
            
            // Update metrics
            document.getElementById('accuracy').textContent = '96.3%';
            document.getElementById('speed').textContent = '2.3 hrs';
            
            // Update stages
            updateStage(2, 'complete');
            updateStage(3, 'active');
            
            // Generate audit artifact
            setTimeout(() => generateAudit(jobId), 1000);
        }
    }, 1500);
}

// Generate audit artifact
function generateAudit(jobId) {
    auditCounter++;
    const artifactId = `audit-${Date.now().toString().slice(-8)}`;
    const timestamp = new Date().toLocaleTimeString();
    
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    logToConsole('OPUS WORKFLOW EXECUTION', 'info');
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    logToConsole(`Workflow ID: STT-OPTIMIZER-PIPELINE-V1`);
    logToConsole(`Job ID: ${jobId}`);
    logToConsole(`Artifact ID: ${artifactId}`);
    logToConsole('');
    logToConsole('Stage 1: Data Import & Processing ✓', 'success');
    logToConsole('Stage 2: AI Decisioning & Routing ✓', 'success');
    logToConsole('Stage 3: Agentic Review (Policy Check) ✓', 'success');
    logToConsole('');
    logToConsole('Validation Score: 0.963 (96.3%)');
    logToConsole('Review Decision: AUTO_APPROVED', 'success');
    logToConsole('Reason: Score exceeds 95% threshold', 'success');
    logToConsole('POPIA Compliance: ✓ PASSED', 'success');
    logToConsole('Human Review: NOT_REQUIRED', 'success');
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    
    // Update audit list
    const auditList = document.getElementById('audit-list');
    if (auditList.querySelector('.empty-state')) {
        auditList.innerHTML = '';
    }
    
    const auditItem = document.createElement('div');
    auditItem.className = 'audit-item';
    auditItem.innerHTML = `
        <div>
            <div class="audit-name">Audit Artifact #${auditCounter}</div>
            <div style="font-size: 12px; color: var(--gray); margin-top: 4px;">
                ${artifactId} • ${timestamp}
            </div>
            <div style="font-size: 12px; margin-top: 4px;">
                <span style="color: var(--success); font-weight: 600;">✓ Auto-Approved</span>
                <span style="color: var(--gray);"> • Score: 96.3%</span>
            </div>
        </div>
        <span class="audit-status status-success">Compliant</span>
    `;
    auditList.insertBefore(auditItem, auditList.firstChild);
    
    // Update metrics
    document.getElementById('approved').textContent = '100%';
    
    // Update stages
    updateStage(3, 'complete');
    updateStage(4, 'active');
    
    // Deploy model
    setTimeout(() => deployModel(), 1500);
}

// Deploy model
function deployModel() {
    logToConsole('═══════════════════════════════════════════════════════════', 'success');
    logToConsole('🚀 MODEL DEPLOYMENT', 'success');
    logToConsole('═══════════════════════════════════════════════════════════', 'success');
    logToConsole('Copying model to public bucket...');
    
    setTimeout(() => {
        logToConsole('✓ Model deployed: gs://ubuntu-ai-models-public/whisper-finetuned-v1.2-sa.tar.gz', 'success');
        logToConsole('✓ Model available for clinic download', 'success');
        logToConsole('═══════════════════════════════════════════════════════════', 'success');
        logToConsole('');
        logToConsole('*** PIPELINE COMPLETE ***', 'success');
        logToConsole('Accuracy: +8.5% improvement', 'success');
        logToConsole('Training Time: 2.3 hours (GPU accelerated)', 'success');
        logToConsole('Compliance: 100% POPIA compliant', 'success');
        logToConsole('Status: Auto-approved and deployed', 'success');
        
        updateStage(4, 'complete');
        
        // Show celebration
        showCelebration();
    }, 2000);
}

// Show celebration animation
function showCelebration() {
    const celebration = document.createElement('div');
    celebration.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 40px 60px;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        text-align: center;
        z-index: 1000;
        animation: popIn 0.3s ease;
    `;
    
    celebration.innerHTML = `
        <div style="font-size: 64px; margin-bottom: 16px;">🎉</div>
        <h2 style="font-size: 24px; margin-bottom: 8px; color: var(--dark);">Pipeline Complete!</h2>
        <p style="color: var(--gray); font-size: 16px;">Model deployed successfully</p>
        <button onclick="this.parentElement.remove()" style="margin-top: 20px; padding: 10px 24px; background: var(--primary); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
            Close
        </button>
    `;
    
    document.body.appendChild(celebration);
    
    // Add animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes popIn {
            from {
                opacity: 0;
                transform: translate(-50%, -50%) scale(0.8);
            }
            to {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
        }
    `;
    document.head.appendChild(style);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (celebration.parentElement) {
            celebration.remove();
        }
    }, 5000);
}

// Auto-demo mode
function runFullDemo() {
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    logToConsole('🎬 STARTING FULL PIPELINE DEMO', 'info');
    logToConsole('═══════════════════════════════════════════════════════════', 'info');
    
    // Step 1: Upload data
    setTimeout(() => {
        logToConsole('Step 1: Simulating clinic data upload...');
        simulateUpload();
    }, 1000);
    
    // Step 2: Start training
    setTimeout(() => {
        logToConsole('Step 2: Starting Vertex AI training job...');
        startTraining();
    }, 6000);
}

// Add keyboard shortcut for demo
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        runFullDemo();
    }
});

// Initial welcome message
setTimeout(() => {
    logToConsole('✓ System ready. Press buttons or Ctrl+D for full demo.', 'success');
}, 500);
