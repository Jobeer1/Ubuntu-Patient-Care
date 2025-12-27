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
qr_img = qr.make_image(fill_color="#1e3a8a", back_color="white")
qr_img = qr_img.resize((180, 180))

# Create main certificate image - A4 proportions at high DPI
width, height = 1920, 2400
background = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(background)

# Load fonts with fallback
try:
    main_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 72)
    header_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 48)
    section_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 36)
    score_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 56)
    body_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 24)
    small_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 20)
    footer_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 18)
    motto_font = ImageFont.truetype('C:/Windows/Fonts/georgia.ttf', 22)
except:
    main_title_font = ImageFont.load_default()
    header_font = ImageFont.load_default()
    section_title_font = ImageFont.load_default()
    score_font = ImageFont.load_default()
    body_font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    footer_font = ImageFont.load_default()
    motto_font = ImageFont.load_default()

# Colors - Professional palette
dark_navy = '#0f1929'
deep_blue = '#1e3a8a'
accent_gold = '#fbbf24'
light_bg = '#f8fafc'
text_dark = '#1f2937'
text_light = '#6b7280'
border_color = '#3b82f6'

# Top decorative border
draw.rectangle([(0, 0), (width, 40)], fill=deep_blue)

# Golden star in top-left
star_x, star_y = 80, 100
draw.text((star_x, star_y), '★', font=ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 120), 
         fill=accent_gold, anchor='mm')

# QR Code in top-right
qr_x = width - 250
qr_y = 80
background.paste(qr_img, (qr_x, qr_y))
draw.text((qr_x + 90, qr_y + 210), 'Scan for full audit', font=small_font, fill=deep_blue, anchor='mm')

# Main title
y_pos = 140
title_text = 'VERIFIED TECHNICAL CREDENTIAL'
draw.text((width//2, y_pos), title_text, font=main_title_font, fill=deep_blue, anchor='mm')

y_pos += 90
org_text = 'Ubuntu Code Integrity Crucible (UCIC)'
draw.text((width//2, y_pos), org_text, font=header_font, fill=accent_gold, anchor='mm')

# Separator line
y_pos += 80
draw.line([(100, y_pos), (width-100, y_pos)], fill=accent_gold, width=4)

# Project Title - Most prominent after main title
y_pos += 50
project_label = 'Project:'
draw.text((120, y_pos), project_label, font=small_font, fill=deep_blue, anchor='lm')
y_pos += 40
project_name = 'Telco USSD Assist MCP'
draw.text((140, y_pos), project_name, font=section_title_font, fill=text_dark, anchor='lm')

y_pos += 60
# Overall Score Block - High contrast gold-bordered box
score_box_y = y_pos
draw.rectangle([(100, y_pos), (width-100, y_pos+160)], fill=light_bg, outline=accent_gold, width=5)

y_pos += 30
draw.text((width//2, y_pos), 'OVERALL SCORE', font=body_font, fill=deep_blue, anchor='mm')
y_pos += 50
draw.text((width//2, y_pos), '32/50', font=score_font, fill=accent_gold, anchor='mm')
y_pos += 60
draw.text((width//2, y_pos), '(64% Technical Merit)', font=body_font, fill=text_dark, anchor='mm')
y_pos = score_box_y + 170

# Validation details
y_pos += 30
details = [
    ('Validation Date', 'November 15, 2025'),
    ('Code Visibility', 'Publicly Auditable Repository'),
]
for idx, (label, value) in enumerate(details):
    x_pos = 150 if idx == 0 else width//2 + 100
    draw.text((x_pos, y_pos), label + ':', font=small_font, fill=deep_blue, anchor='lm')
    draw.text((x_pos, y_pos + 35), value, font=body_font, fill=text_dark, anchor='lm')

y_pos += 100

# Validated Core Competencies - Two Column Layout
draw.text((120, y_pos), 'VALIDATED CORE COMPETENCIES', font=section_title_font, fill=deep_blue, anchor='lm')
y_pos += 60

# Column positions
left_col_x = 150
right_col_x = width // 2 + 100
competency_y_start = y_pos

# Left column - Scores
competencies_left = [
    ('Technical Architecture', '7/10'),
    ('Mission Alignment', '8.5/10'),
    ('API Integration', 'Verified'),
    ('Deployment Status', 'Verified'),
]

current_y = competency_y_start
for label, score in competencies_left:
    # Score box
    if score == 'Verified':
        color = '#10b981'
    elif '8' in score:
        color = '#f59e0b'
    else:
        color = '#f59e0b'
    
    draw.rectangle([(left_col_x, current_y), (left_col_x + 120, current_y + 50)], 
                   fill=color, outline=text_dark, width=2)
    draw.text((left_col_x + 60, current_y + 25), score, font=score_font, fill='white', anchor='mm')
    current_y += 90

# Right column - Achievements
current_y = competency_y_start
achievements = [
    'Solid code quality with\n15 unit tests',
    'Successfully addressed\nreal problem',
    'Multiple AI Clients:\nClaude, Cursor, Gemini',
    'Live endpoint at\nFastMCP Cloud',
]

for achievement in achievements:
    draw.text((right_col_x, current_y + 10), achievement, font=small_font, fill=text_dark, anchor='lm')
    current_y += 90

y_pos = competency_y_start + 400

# Integrity Assurance Section
draw.text((120, y_pos), 'INTEGRITY ASSURANCE', font=section_title_font, fill=deep_blue, anchor='lm')
y_pos += 60

integrity_items = [
    ('Verifiable Code', 'Publicly accessible with complete transparency and permanent audit trail'),
    ('Focus on Utility', 'Genuine need identified and validated in Ghanaian market'),
    ('Permanent Record', 'Full technical analysis available on public GitHub repository'),
]

for title, description in integrity_items:
    draw.text((140, y_pos), '✓ ' + title + ':', font=body_font, fill=deep_blue, anchor='lm')
    draw.text((200, y_pos + 35), description, font=small_font, fill=text_light, anchor='lm')
    y_pos += 90

y_pos += 40
# Authority Section - Bottom Right Area
draw.text((width//2 + 100, y_pos), 'VALIDATED BY AUTHORITY', font=section_title_font, fill=deep_blue, anchor='lm')
y_pos += 60

authority_text = 'Detailed review by GitHub Copilot'
draw.text((width//2 + 120, y_pos), authority_text, font=body_font, fill=text_dark, anchor='lm')
y_pos += 50

authority_under = 'Founders and Technical Authorities'
draw.text((width//2 + 120, y_pos), authority_under, font=small_font, fill=deep_blue, anchor='lm')
y_pos += 50

authorities = [
    'Dr. Jodogn - Founder, Ubuntu Patient Care',
    'Dr. Tom Zubiri - Technical Authority, UCIC Chief Integrity Officer',
]

for auth in authorities:
    draw.text((width//2 + 140, y_pos), auth, font=small_font, fill=text_dark, anchor='lm')
    y_pos += 45

# Footer with motto
footer_y = height - 120
draw.rectangle([(0, height-150), (width, height)], fill=deep_blue)

motto = 'Code integrity and technical merit are non-negotiable standards'
draw.text((width//2, footer_y - 30), motto, font=motto_font, fill=accent_gold, anchor='mm')

draw.text((width//2, footer_y + 30), 'Certificate Generated: ' + datetime.now().strftime('%B %d, %Y'), 
          font=footer_font, fill='white', anchor='mm')
draw.text((width//2, footer_y + 70), '© 2025 Ubuntu Code Integrity Crucible - All Rights Reserved', 
          font=footer_font, fill='#bfdbfe', anchor='mm')

# Save as high-quality JPEG
output_path = 'c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Ubuntu Code Integrity Crucible (UCIC)/5-Telco-USSD-Assist/Telco_USSD_Technical_Certificate.jpg'
background.save(output_path, 'JPEG', quality=99)
print('✅ Professional certificate redesigned: Telco_USSD_Technical_Certificate.jpg')
print(f'✅ High-resolution: 1920x2400px (print-ready)')
print(f'✅ Location: {output_path}')
