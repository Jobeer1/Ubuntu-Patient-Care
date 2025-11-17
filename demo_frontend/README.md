# Ubuntu Patient Care - Demo Frontend

## 🎬 Quick Start for Demo Video

### Option 1: Open Directly in Browser
1. Open `index.html` in any modern browser (Chrome, Firefox, Edge)
2. No server needed - it's a static HTML page!

### Option 2: Use a Local Server (Recommended for recording)
```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000

# Node.js (if you have http-server installed)
npx http-server

# Then open: http://localhost:8000
```

## 🎥 Demo Script for Judges

### Scene 1: Introduction (10 seconds)
- Show the dashboard with all three partner badges visible
- Point out: "Ubuntu Patient Care - AI-Powered Rural Healthcare"
- Highlight the three partner technologies at the top

### Scene 2: Data Collection (15 seconds)
1. Click **"Simulate Upload"** button
2. Watch the console show:
   - Data detection from clinic
   - POPIA compliance validation ✓
   - Upload to GCS
3. Point out: "Simple sync from rural clinics via Google Drive"

### Scene 3: Vertex AI Training (20 seconds)
1. Click **"Start Training"** button
2. Console shows:
   - Machine Type: n1-highmem-8
   - **Accelerator: NVIDIA Tesla T4** (KEY POINT)
   - Training progress through 5 epochs
3. Point out: "2-4 hours with GPU vs 12+ hours on CPU"
4. Watch metrics update:
   - Accuracy: 96.3%
   - Speed: 2.3 hrs

### Scene 4: Opus Audit Trail (15 seconds)
1. Console automatically shows audit generation
2. Point out the audit artifact with:
   - **"NO_HUMAN_REVIEW_NEEDED"** (auto-approval)
   - POPIA Compliant ✓
   - Score: 96.3% (exceeds 95% threshold)
3. Highlight: "Full auditability for healthcare compliance"

### Scene 5: Deployment (10 seconds)
1. Watch automatic deployment
2. Console shows: "Model deployed to public bucket"
3. Point out: "Ready for clinic download immediately"
4. Celebration popup appears 🎉

### Scene 6: Final Overview (10 seconds)
- Pan across the completed pipeline stages (all green)
- Show the metrics dashboard:
  - 96.3% accuracy (+8.5% improvement)
  - 2.3 hours training time
  - 100% auto-approved
  - 3 clinics served
- End with: "Complete pipeline from clinic to deployment"

## ⌨️ Keyboard Shortcuts

- **Ctrl+D**: Run full automated demo (all steps automatically)
- **Clear button**: Reset console

## 🎨 Visual Highlights for Video

### Partner Technology Badges
- **Google Vertex AI** (Blue) - Top right
- **Anthropic Opus** (Orange) - Top right
- **Qdrant Vector DB** (Purple) - Top right

### Pipeline Stages (Visual Flow)
1. 📥 Data Sync → Active during upload
2. 🧠 Vertex AI Training → Active during training
3. 📋 Opus Audit → Active during audit generation
4. 🚀 Deployment → Active during deployment

### Key Metrics to Zoom In On
- **Model Accuracy**: 96.3% (shows improvement)
- **Training Speed**: 2.3 hrs (shows GPU advantage)
- **Auto-Approved**: 100% (shows Opus workflow)
- **Clinics Served**: 3 (shows real-world impact)

### Console Messages to Highlight
```
✓ POPIA compliance validation passed
Accelerator: NVIDIA_TESLA_T4 x1
Final Validation Accuracy: 0.963 (+8.5% improvement)
Review Action: NO_HUMAN_REVIEW_NEEDED
✓ Model deployed: gs://ubuntu-ai-models-public/...
```

## 🎯 Talking Points for Narration

### Google AI Depth
- "We leverage Vertex AI's GPU acceleration for 5x faster training"
- "Google Drive API enables seamless data collection from rural clinics"
- "Cloud Storage provides scalable model distribution"

### Auditable Opus Workflow
- "Every training run generates a comprehensive audit artifact"
- "Automated review logic: models above 95% accuracy are auto-approved"
- "Full POPIA compliance validation for South African healthcare data"
- "Complete traceability from clinic upload to deployment"

### Smart Integration
- "Clinics see a simple Google Drive folder - no technical complexity"
- "Behind the scenes, powerful AI infrastructure optimizes models"
- "Automated pipeline reduces deployment time from weeks to hours"

## 🎬 Pro Tips for Recording

1. **Use Full Screen**: Press F11 for immersive view
2. **Zoom Level**: 100% or 110% for readability
3. **Screen Resolution**: 1920x1080 recommended
4. **Recording Software**: OBS Studio, Loom, or QuickTime
5. **Cursor Highlighting**: Enable in recording software
6. **Audio**: Clear narration explaining each step
7. **Pacing**: Let animations complete before moving on
8. **Multiple Takes**: Record 2-3 times, pick the best

## 🚀 Advanced Demo Features

### Automated Full Demo
Press **Ctrl+D** to run the entire pipeline automatically:
- Uploads data after 1 second
- Starts training after 6 seconds
- Completes full pipeline in ~20 seconds
- Perfect for quick demonstrations

### Manual Control
Use individual buttons for step-by-step demonstration:
- More control over pacing
- Better for detailed explanations
- Can pause between steps

## 📱 Responsive Design

The dashboard works on all screen sizes:
- Desktop: Full grid layout
- Tablet: Stacked cards
- Mobile: Single column

## 🎨 Customization

### Change Colors
Edit `styles.css` variables:
```css
:root {
    --primary: #4285f4;
    --secondary: #34a853;
    /* etc. */
}
```

### Adjust Timing
Edit `script.js` setTimeout values:
```javascript
setTimeout(() => {
    // Adjust these numbers (in milliseconds)
}, 1500);
```

## 🏆 Hackathon Judging Criteria Coverage

✅ **Google AI Depth**: Vertex AI GPU training prominently displayed  
✅ **Auditable Opus Workflow**: Complete audit trail with auto-approval  
✅ **Qdrant Integration**: Ready for vector search (mention in narration)  
✅ **Real-World Impact**: Rural healthcare use case  
✅ **Technical Excellence**: Production-ready architecture  
✅ **User Experience**: Simple clinic interface, powerful backend  

## 📧 Questions?

This is a demo frontend that simulates the backend pipeline you've already built. All the real code is in:
- `mcp_server/data_sync/drive_upload.py`
- `mcp_server/cli/download_ml_models.py`
- `cloud_orchestration/drive_monitor.py`
- `cloud_orchestration/vertex_pipeline_definition.py`
- `cloud_orchestration/opus_audit_artifact.py`

Good luck with your demo! 🚀
