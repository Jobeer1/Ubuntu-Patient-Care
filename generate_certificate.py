from PIL import Image, ImageDraw, ImageFont
import qrcode
from datetime import datetime

# Create QR code for GitHub audit log
qr_url = "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/Ubuntu%20Code%20Integrity%20Crucible%20%28UCIC%29/5-Telco-USSD-Assist"
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=2,
)
qr.add_data(qr_url)
qr.make(fit=True)
qr_img = qr.make_image(fill_color="#1e3a8a", back_color="#f5f5f5")
qr_img = qr_img.resize((200, 200))

# Create main certificate image
width, height = 1600, 2000
background = Image.new('RGB', (width, height), color='#ffffff')
draw = ImageDraw.Draw(background)

# Load fonts
try:
    title_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 52)
    header_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 40)
    section_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 30)
    body_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 22)
    small_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 18)
    footer_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 14)
except:
    title_font = ImageFont.load_default()
    header_font = ImageFont.load_default()
    section_font = ImageFont.load_default()
    body_font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    footer_font = ImageFont.load_default()

# Colors
dark_blue = '#1e40af'
light_blue = '#3b82f6'
accent_gold = '#fbbf24'
text_dark = '#111827'
text_light = '#6b7280'
background_accent = '#eff6ff'

# Draw gradient-like background with subtle blue
draw.rectangle([(0, 0), (width, 300)], fill='#1e40af')
draw.rectangle([(0, height-150), (width, height)], fill='#1e40af')

# Draw golden star in top left corner
seal_x, seal_y = 100, 80
draw.text((seal_x, seal_y), '★', font=ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 100) if True else ImageFont.load_default(), 
         fill='#fbbf24', anchor='mm')

# Draw decorative top border
draw.line([(60, 350), (width-60, 350)], fill=accent_gold, width=5)

# Title with gradient effect (white on blue background)
y_pos = 100
title_text = '🎓 VERIFIED TECHNICAL CREDENTIAL'
draw.text((width//2, y_pos), title_text, font=title_font, fill='#ffffff', anchor='mm')

y_pos += 100
org_text = 'Ubuntu Code Integrity Crucible (UCIC)'
draw.text((width//2, y_pos), org_text, font=header_font, fill='#fbbf24', anchor='mm')

# Main content area with light blue background
draw.rectangle([(60, 350), (width-60, height-150)], fill=background_accent, outline=light_blue, width=3)

y_pos = 400
cert_desc = 'This credential certifies that the project has undergone a transparent,'
draw.text((width//2, y_pos), cert_desc, font=body_font, fill=text_dark, anchor='mm')
y_pos += 35
cert_desc2 = 'AI-driven, and bias-free technical audit by industry experts.'
draw.text((width//2, y_pos), cert_desc2, font=body_font, fill=text_dark, anchor='mm')

y_pos += 80
# Project details in two columns
draw.text((100, y_pos), 'PROJECT DETAILS', font=section_font, fill=dark_blue, anchor='lm')
y_pos += 50

details_left = [
    ('Project Title', 'Telco USSD Assist MCP'),
    ('Validation Date', 'November 15, 2025'),
    ('Audit Authority', 'Ubuntu Code Integrity Crucible'),
]

details_right = [
    ('Overall Score', '32/50 (64%)'),
    ('Code Status', 'Publicly Auditable'),
    ('Repository', 'Open Source'),
]

for label, value in details_left:
    draw.text((120, y_pos), label + ':', font=body_font, fill=dark_blue, anchor='lm')
    draw.text((450, y_pos), value, font=body_font, fill=text_dark, anchor='lm')
    y_pos += 45

y_pos = 680
for label, value in details_right:
    draw.text((900, y_pos), label + ':', font=body_font, fill=dark_blue, anchor='lm')
    draw.text((1230, y_pos), value, font=body_font, fill=text_dark, anchor='lm')
    y_pos += 45

y_pos = 780
# Competencies section
draw.text((100, y_pos), 'VALIDATED COMPETENCIES', font=section_font, fill=dark_blue, anchor='lm')
y_pos += 50

competencies = [
    ('Technical Architecture', '7/10', 'Solid code quality with 15 unit tests and proper error handling'),
    ('Mission Alignment', '8.5/10', 'Successfully addressed verified real problem in Ghanaian market'),
    ('API Integration', 'Verified', 'Multiple AI Clients: Claude, Cursor, Gemini'),
    ('Deployment Status', 'Verified', 'Live endpoint accessible at FastMCP Cloud'),
]

for comp_label, score, detail in competencies:
    # Draw score box
    if score != 'Verified':
        score_color = '#10b981' if '8' in score or '7' in score else '#f59e0b'
    else:
        score_color = '#10b981'
    
    draw.rectangle([(120, y_pos-5), (250, y_pos+35)], fill=score_color, outline=dark_blue, width=2)
    draw.text((185, y_pos+15), score, font=body_font, fill='#ffffff', anchor='mm')
    
    draw.text((280, y_pos), comp_label, font=body_font, fill=dark_blue, anchor='lm')
    draw.text((280, y_pos+35), detail, font=small_font, fill=text_light, anchor='lm')
    y_pos += 85

y_pos += 20
# Integrity advantage
draw.text((100, y_pos), 'INTEGRITY ASSURANCE', font=section_font, fill=dark_blue, anchor='lm')
y_pos += 50

integrity_points = [
    '✓ Verifiable Code: Publicly accessible with complete transparency and audit trail',
    '✓ Focus on Utility: Genuine problem identified and validated in target market',
    '✓ Permanent Record: Full technical analysis available on public GitHub repository',
]

for point in integrity_points:
    draw.text((120, y_pos), point, font=body_font, fill=text_dark, anchor='lm')
    y_pos += 45

y_pos += 30
# Signature section with decorative line
draw.line([(100, y_pos), (width-100, y_pos)], fill=accent_gold, width=3)
y_pos += 40

draw.text((100, y_pos), 'VALIDATED BY AUTHORITY', font=section_font, fill=dark_blue, anchor='lm')
y_pos += 50

# Authority statement
authority_text = 'Detailed review by GitHub Copilot'
draw.text((120, y_pos), authority_text, font=body_font, fill=text_dark, anchor='lm')
y_pos += 45

authority_under = 'Under the Authority of:'
draw.text((120, y_pos), authority_under, font=small_font, fill=dark_blue, anchor='lm')
y_pos += 40

# Authorities without signature lines
authorities = [
    ('Dr. Jodogn', 'Founder, Ubuntu Patient Care'),
    ('Dr. Tom Zubiri', 'Technical Authority, UCIC Chief Integrity Officer (AI)'),
]

for name, role in authorities:
    draw.text((140, y_pos), name, font=body_font, fill=dark_blue, anchor='lm')
    draw.text((140, y_pos + 35), role, font=small_font, fill=text_light, anchor='lm')
    y_pos += 75

# QR Code section
qr_x = width - 280
qr_y = 420
background.paste(qr_img, (qr_x, qr_y))
draw.text((qr_x + 100, qr_y + 220), 'Scan for full audit', font=footer_font, fill=dark_blue, anchor='mm')

# Footer
footer_y = height - 100
draw.rectangle([(0, height-150), (width, height)], fill='#1e40af')
draw.text((width//2, footer_y-35), 'Certificate Generated: ' + datetime.now().strftime('%B %d, %Y'), 
          font=small_font, fill='#ffffff', anchor='mm')
draw.text((width//2, footer_y+10), '© 2025 Ubuntu Code Integrity Crucible - All Rights Reserved', 
          font=footer_font, fill='#bfdbfe', anchor='mm')

# Save as high-quality JPEG
output_path = 'c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Ubuntu Code Integrity Crucible (UCIC)/5-Telco-USSD-Assist/Telco_USSD_Technical_Certificate.jpg'
background.save(output_path, 'JPEG', quality=98)
print('✅ Enhanced certificate created with QR code: Telco_USSD_Technical_Certificate.jpg')
print(f'✅ Location: {output_path}')
