/**
 * GOTG PACS Lightweight DICOM Viewer
 * Optimized for offline operation and low bandwidth
 */

const ORTHANC_URL = window.location.origin.replace(':3000', ':8042');
let currentStudy = null;
let currentImage = null;
let zoom = 1;
let inverted = false;

// Initialize viewer
document.addEventListener('DOMContentLoaded', () => {
    loadStudies();
    setupToolbar();
    checkOnlineStatus();
    
    // Check online status every 30 seconds
    setInterval(checkOnlineStatus, 30000);
});

// Check if PACS is online
async function checkOnlineStatus() {
    try {
        const response = await fetch(`${ORTHANC_URL}/system`, {
            method: 'GET',
            headers: {
                'Authorization': 'Basic ' + btoa('orthanc:orthanc')
            }
        });
        
        if (response.ok) {
            setOnlineStatus(true);
        } else {
            setOnlineStatus(false);
        }
    } catch (error) {
        setOnlineStatus(false);
    }
}

function setOnlineStatus(online) {
    const indicator = document.getElementById('statusIndicator');
    const text = document.getElementById('statusText');
    
    if (online) {
        indicator.classList.remove('offline');
        text.textContent = 'Online';
    } else {
        indicator.classList.add('offline');
        text.textContent = 'Offline';
    }
}

// Load studies from Orthanc
async function loadStudies() {
    const studyList = document.getElementById('studyList');
    
    try {
        const response = await fetch(`${ORTHANC_URL}/studies`, {
            headers: {
                'Authorization': 'Basic ' + btoa('orthanc:orthanc')
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load studies');
        }
        
        const studyIds = await response.json();
        
        if (studyIds.length === 0) {
            studyList.innerHTML = '<div class="no-studies">No studies available</div>';
            return;
        }
        
        studyList.innerHTML = '';
        
        // Load study details
        for (const studyId of studyIds) {
            const studyResponse = await fetch(`${ORTHANC_URL}/studies/${studyId}`, {
                headers: {
                    'Authorization': 'Basic ' + btoa('orthanc:orthanc')
                }
            });
            
            const study = await studyResponse.json();
            const studyItem = createStudyItem(study);
            studyList.appendChild(studyItem);
        }
        
    } catch (error) {
        console.error('Failed to load studies:', error);
        studyList.innerHTML = '<div class="no-studies">Failed to load studies. Check connection.</div>';
    }
}

// Create study list item
function createStudyItem(study) {
    const div = document.createElement('div');
    div.className = 'study-item';
    div.onclick = () => loadStudy(study);
    
    const tags = study.MainDicomTags || {};
    const patientTags = study.PatientMainDicomTags || {};
    
    div.innerHTML = `
        <div class="study-info">
            <div><strong>Patient:</strong> ${patientTags.PatientName || 'Unknown'}</div>
            <div><strong>Date:</strong> ${formatDate(tags.StudyDate)}</div>
            <div><strong>Description:</strong> ${tags.StudyDescription || 'N/A'}</div>
            <div><strong>Modality:</strong> ${tags.ModalitiesInStudy || 'N/A'}</div>
        </div>
    `;
    
    return div;
}

// Format DICOM date
function formatDate(dicomDate) {
    if (!dicomDate || dicomDate.length !== 8) return 'Unknown';
    const year = dicomDate.substring(0, 4);
    const month = dicomDate.substring(4, 6);
    const day = dicomDate.substring(6, 8);
    return `${year}-${month}-${day}`;
}

// Load and display study
async function loadStudy(study) {
    currentStudy = study;
    
    // Highlight selected study
    document.querySelectorAll('.study-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    try {
        // Get first series
        const seriesId = study.Series[0];
        const seriesResponse = await fetch(`${ORTHANC_URL}/series/${seriesId}`, {
            headers: {
                'Authorization': 'Basic ' + btoa('orthanc:orthanc')
            }
        });
        
        const series = await seriesResponse.json();
        
        // Get first instance
        const instanceId = series.Instances[0];
        await loadInstance(instanceId, study);
        
    } catch (error) {
        console.error('Failed to load study:', error);
        alert('Failed to load study images');
    }
}

// Load and display DICOM instance
async function loadInstance(instanceId, study) {
    try {
        // Get preview image (PNG)
        const imageUrl = `${ORTHANC_URL}/instances/${instanceId}/preview`;
        const response = await fetch(imageUrl, {
            headers: {
                'Authorization': 'Basic ' + btoa('orthanc:orthanc')
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load image');
        }
        
        const blob = await response.blob();
        const img = new Image();
        img.src = URL.createObjectURL(blob);
        
        img.onload = () => {
            displayImage(img, study);
        };
        
        currentImage = img;
        
    } catch (error) {
        console.error('Failed to load instance:', error);
        alert('Failed to load image');
    }
}

// Display image on canvas
function displayImage(img, study) {
    const canvas = document.getElementById('dicomCanvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size
    canvas.width = img.width;
    canvas.height = img.height;
    
    // Draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    
    // Apply current transformations
    if (inverted) {
        invertImage(ctx, canvas.width, canvas.height);
    }
    
    // Update image info
    updateImageInfo(study);
}

// Update image information display
function updateImageInfo(study) {
    const tags = study.MainDicomTags || {};
    const patientTags = study.PatientMainDicomTags || {};
    
    document.getElementById('patientName').textContent = patientTags.PatientName || 'Unknown';
    document.getElementById('studyDate').textContent = formatDate(tags.StudyDate);
    document.getElementById('modality').textContent = tags.ModalitiesInStudy || 'N/A';
    document.getElementById('description').textContent = tags.StudyDescription || 'N/A';
    document.getElementById('imageInfo').style.display = 'block';
}

// Invert image colors
function invertImage(ctx, width, height) {
    const imageData = ctx.getImageData(0, 0, width, height);
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
        data[i] = 255 - data[i];       // Red
        data[i + 1] = 255 - data[i + 1]; // Green
        data[i + 2] = 255 - data[i + 2]; // Blue
    }
    
    ctx.putImageData(imageData, 0, 0);
}

// Setup toolbar buttons
function setupToolbar() {
    document.getElementById('zoomInBtn').onclick = () => {
        zoom *= 1.2;
        applyZoom();
    };
    
    document.getElementById('zoomOutBtn').onclick = () => {
        zoom /= 1.2;
        applyZoom();
    };
    
    document.getElementById('resetBtn').onclick = () => {
        zoom = 1;
        inverted = false;
        if (currentImage && currentStudy) {
            displayImage(currentImage, currentStudy);
        }
    };
    
    document.getElementById('invertBtn').onclick = () => {
        inverted = !inverted;
        if (currentImage && currentStudy) {
            displayImage(currentImage, currentStudy);
        }
    };
    
    document.getElementById('downloadBtn').onclick = () => {
        const canvas = document.getElementById('dicomCanvas');
        const link = document.createElement('a');
        link.download = `study_${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
    };
}

// Apply zoom transformation
function applyZoom() {
    const canvas = document.getElementById('dicomCanvas');
    canvas.style.transform = `scale(${zoom})`;
}
