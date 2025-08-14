# SA RIS Hackathon Demo

## What We Built
OpenEMR integration with South African healthcare systems:
- **Healthbridge** clearing house integration
- **Medical Aid** schemes (Discovery, Momentum, etc.)
- **ICD-10** code validation
- **NRPL** billing codes
- **Workflow sync** between OpenEMR and SA RIS

## Quick Demo

### HTML Demo (Works Right Now!)
```bash
cd openemr
start demo_sa_ris.html
```
**Just double-click the HTML file to open in browser!**

### PHP Demo (if PHP installed)
```bash
cd openemr
php demo_sa_ris.php
```

### 2. Key Features Demonstrated
- ✅ Create radiology appointments with SA medical aid integration
- ✅ Process orders with ICD-10 validation
- ✅ Submit claims to Healthbridge clearing house
- ✅ Real-time medical aid verification
- ✅ Bi-directional workflow synchronization

### 3. Core Files
- `healthbridge_integration/HealthbridgeConnector.php` - Clearing house API
- `sa_ris_integration/SAOpenEMRIntegration.php` - Main integration
- `workflow_sync/WorkflowSyncService.php` - Data synchronization
- `icd10_service/SAICD10Service.php` - ICD-10 management
- `demo_sa_ris.php` - Complete demonstration

## Hackathon Value
- **Real SA market focus** - Actual medical aid schemes and billing codes
- **Production-ready code** - Full error handling and logging
- **Complete integration** - Works with teammate's PACS/reporting system
- **Compliance ready** - POPIA and HPCSA compliant

## Demo Script
```php
// The demo shows:
// 1. Creating appointments with Discovery Health
// 2. ICD-10 code validation (R06.02, R50.9)
// 3. NRPL billing (CT scan = R2,850)
// 4. Healthbridge claim submission
// 5. Real-time status tracking
```

**Ready to demo! 🚀**