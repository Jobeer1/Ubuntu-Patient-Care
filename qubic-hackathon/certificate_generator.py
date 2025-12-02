#!/usr/bin/env python3
"""
QUBIC Certificate Generator
Creates professional certificates for evaluated contributions
"""

from datetime import datetime
from typing import Dict
import qrcode
from io import BytesIO
import base64


class QUBICCertificate:
    """Generate QUBIC evaluation certificates"""
    
    TIER_COLORS = {
        "Platinum": "#E5E4E2",
        "Gold": "#FFD700",
        "Silver": "#C0C0C0",
        "Bronze": "#CD7F32",
        "Recognized": "#4A90E2",
        "Needs Improvement": "#95A5A6"
    }
    
    TIER_BADGES = {
        "Platinum": "🏆",
        "Gold": "🥇",
        "Silver": "🥈",
        "Bronze": "🥉",
        "Recognized": "⭐",
        "Needs Improvement": "📝"
    }
    
    def __init__(self, evaluation_data: Dict):
        self.data = evaluation_data
        
    def generate_qr_code(self, audit_url: str) -> str:
        """Generate QR code for audit trail"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(audit_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_html_certificate(self, output_path: str = "certificate.html"):
        """Generate HTML certificate"""
        
        tier = self.data.get("tier", "Recognized")
        score = self.data.get("score", 0)
        contributor = self.data.get("contributor", {})
        contribution = self.data.get("contribution", {})
        breakdown = self.data.get("breakdown", {})
        
        # Generate QR code
        audit_url = contribution.get("audit_url", "https://github.com/ubuntu-patient-care")
        qr_code_data = self.generate_qr_code(audit_url)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUBIC Certificate - {contributor.get('name', 'Contributor')}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 0;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Georgia', serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        
        .certificate {{
            width: 297mm;
            height: 210mm;
            background: white;
            margin: 20px auto;
            padding: 40px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.3);
            position: relative;
            border: 15px solid {self.TIER_COLORS.get(tier, '#4A90E2')};
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 4em;
            margin-bottom: 10px;
        }}
        
        .title {{
            font-size: 2.5em;
            color: #667eea;
            margin: 10px 0;
            font-weight: bold;
        }}
        
        .subtitle {{
            font-size: 1.2em;
            color: #666;
            font-style: italic;
        }}
        
        .tier-badge {{
            text-align: center;
            margin: 30px 0;
        }}
        
        .tier-badge .emoji {{
            font-size: 5em;
        }}
        
        .tier-badge .tier-name {{
            font-size: 2em;
            color: {self.TIER_COLORS.get(tier, '#4A90E2')};
            font-weight: bold;
            margin-top: 10px;
        }}
        
        .tier-badge .score {{
            font-size: 3em;
            color: #333;
            font-weight: bold;
            margin-top: 10px;
        }}
        
        .certificate-text {{
            text-align: center;
            margin: 30px 0;
            font-size: 1.2em;
            line-height: 1.8;
        }}
        
        .contributor-name {{
            font-size: 2em;
            color: #667eea;
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .contribution-title {{
            font-size: 1.5em;
            color: #333;
            font-style: italic;
            margin: 15px 0;
        }}
        
        .breakdown {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .breakdown-item {{
            text-align: center;
        }}
        
        .breakdown-item .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .breakdown-item .value {{
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
        }}
        
        .footer {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
        }}
        
        .signatures {{
            text-align: left;
        }}
        
        .signature {{
            margin: 10px 0;
        }}
        
        .signature-line {{
            border-top: 2px solid #333;
            width: 200px;
            margin-top: 5px;
        }}
        
        .signature-name {{
            font-weight: bold;
            color: #333;
        }}
        
        .signature-title {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .qr-section {{
            text-align: center;
        }}
        
        .qr-code {{
            width: 120px;
            height: 120px;
        }}
        
        .audit-text {{
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }}
        
        .date {{
            text-align: right;
        }}
        
        .date-label {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .date-value {{
            font-weight: bold;
            color: #333;
        }}
        
        .watermark {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 8em;
            color: rgba(102, 126, 234, 0.05);
            font-weight: bold;
            z-index: 0;
        }}
        
        .content {{
            position: relative;
            z-index: 1;
        }}
    </style>
</head>
<body>
    <div class="certificate">
        <div class="watermark">QUBIC</div>
        
        <div class="content">
            <div class="header">
                <div class="logo">🏥</div>
                <div class="title">QUBIC</div>
                <div class="subtitle">Quantified Ubuntu Contribution Integrity Crucible</div>
            </div>
            
            <div class="tier-badge">
                <div class="emoji">{self.TIER_BADGES.get(tier, '⭐')}</div>
                <div class="tier-name">{tier} Tier</div>
                <div class="score">{score}/100</div>
            </div>
            
            <div class="certificate-text">
                This certifies that
            </div>
            
            <div class="contributor-name">
                {contributor.get('name', 'Contributor')}
            </div>
            
            <div class="certificate-text">
                has made a valuable contribution to Ubuntu Patient Care
            </div>
            
            <div class="contribution-title">
                "{contribution.get('title', 'Contribution')}"
            </div>
            
            <div class="breakdown">
                <div class="breakdown-item">
                    <div class="label">Code Quality</div>
                    <div class="value">{breakdown.get('code_quality', 0)}/30</div>
                </div>
                <div class="breakdown-item">
                    <div class="label">Healthcare Impact</div>
                    <div class="value">{breakdown.get('healthcare_impact', 0)}/25</div>
                </div>
                <div class="breakdown-item">
                    <div class="label">Documentation</div>
                    <div class="value">{breakdown.get('documentation', 0)}/20</div>
                </div>
                <div class="breakdown-item">
                    <div class="label">Innovation</div>
                    <div class="value">{breakdown.get('innovation', 0)}/15</div>
                </div>
                <div class="breakdown-item">
                    <div class="label">Integration</div>
                    <div class="value">{breakdown.get('integration', 0)}/10</div>
                </div>
            </div>
            
            <div class="footer">
                <div class="signatures">
                    <div class="signature">
                        <div class="signature-line"></div>
                        <div class="signature-name">Dr. Jodogn</div>
                        <div class="signature-title">Founder, Ubuntu Patient Care</div>
                    </div>
                    <div class="signature">
                        <div class="signature-line"></div>
                        <div class="signature-name">Master Tom</div>
                        <div class="signature-title">Technical Authority</div>
                    </div>
                </div>
                
                <div class="qr-section">
                    <img src="{qr_code_data}" alt="Audit Trail QR Code" class="qr-code">
                    <div class="audit-text">Scan for Audit Trail</div>
                    <div class="audit-text">{contribution.get('commit_hash', 'N/A')[:8]}</div>
                </div>
                
                <div class="date">
                    <div class="date-label">Validated on</div>
                    <div class="date-value">{datetime.now().strftime('%B %d, %Y')}</div>
                    <div class="date-label" style="margin-top: 10px;">QUBIC v1.0</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-print functionality
        window.onload = function() {{
            // Uncomment to auto-print
            // window.print();
        }};
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Certificate generated: {output_path}")
        return output_path


def generate_certificate(evaluation_data: Dict, output_path: str = "certificate.html"):
    """Convenience function to generate certificate"""
    cert = QUBICCertificate(evaluation_data)
    return cert.generate_html_certificate(output_path)


if __name__ == "__main__":
    # Example usage
    sample_data = {
        "tier": "Gold",
        "score": 85,
        "contributor": {
            "name": "John Doe",
            "email": "john@example.com",
            "github": "johndoe"
        },
        "contribution": {
            "title": "AI-Powered Triage System for Emergency Radiology",
            "audit_url": "https://github.com/ubuntu-patient-care/commits/abc123",
            "commit_hash": "abc123def456"
        },
        "breakdown": {
            "code_quality": 25,
            "healthcare_impact": 22,
            "documentation": 18,
            "innovation": 13,
            "integration": 7
        }
    }
    
    generate_certificate(sample_data, "sample_certificate.html")
