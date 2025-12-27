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
qr_img = qr.make_image(fill_color="#001f3f", back_color="white")
qr_img = qr_img.resize((200, 200))

# Create main certificate image - A4 proportions at high DPI
width, height = 1920, 2400
background = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(background)

# Load fonts with fallback
try:
    main_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 80)
    header_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 52)
    section_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 40)
    score_display_font = ImageFont.truetype('C:/Windows/Fonts/arialbdu.ttf', 72)
    label_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 26)
    body_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 24)
    small_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 20)
    footer_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 18)
except:
    main_title_font = ImageFont.load_default()
    header_font = ImageFont.load_default()
    section_title_font = ImageFont.load_default()
    score_display_font = ImageFont.load_default()
    label_font = ImageFont.load_default()
    body_font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    footer_font = ImageFont.load_default()

# Professional Color Palette
deep_navy = '#001f3f'
navy_blue = '#0f3a66'
metallic_gold = '#fbbf24'
bright_white = '#ffffff'
text_dark = '#1f2937'
text_light = '#6b7280'
light_gray = '#f3f4f6'

# Top decorative navy border
draw.rectangle([(0, 0), (width, 60)], fill=deep_navy)

# Golden star in top-left (bold metallic)
star_x, star_y = 120, 120
draw.text((star_x, star_y), '★', font=ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 140), 
         fill=metallic_gold, anchor='mm')

# QR Code in top-right with label
qr_x = width - 280
qr_y = 60
background.paste(qr_img, (qr_x, qr_y))
draw.text((qr_x + 100, qr_y + 220), 'SCAN FOR FULL', font=small_font, fill=deep_navy, anchor='mm')
draw.text((qr_x + 100, qr_y + 250), 'AUDIT TRAIL', font=small_font, fill=deep_navy, anchor='mm')

# Header Block - Centered at top
y_pos = 150
title_text = 'VERIFIED TECHNICAL CREDENTIAL'
draw.text((width//2, y_pos), title_text, font=main_title_font, fill=deep_navy, anchor='mm')

y_pos += 100
org_text = 'Ubuntu Code Integrity Crucible (UCIC)'
draw.text((width//2, y_pos), org_text, font=header_font, fill=metallic_gold, anchor='mm')

# Decorative line separator
y_pos += 90
draw.line([(150, y_pos), (width-150, y_pos)], fill=metallic_gold, width=6)

# Score Block - Prominent center-aligned gold-accented box
y_pos += 80
score_box_top = y_pos
score_box_height = 200

# Gold accent border (thick top bar)
draw.rectangle([(200, score_box_top), (width-200, score_box_top+15)], fill=metallic_gold)

# Main score box with border
draw.rectangle([(200, score_box_top), (width-200, score_box_top+score_box_height)], 
               fill=light_gray, outline=metallic_gold, width=6)

# Score label
draw.text((width//2, score_box_top + 40), 'OVERALL SCORE', font=label_font, fill=deep_navy, anchor='mm')

# Score display - large, bold, navy
draw.text((width//2, score_box_top + 95), '32/50', font=score_display_font, fill=deep_navy, anchor='mm')

# Percentage
draw.text((width//2, score_box_top + 160), '64% Technical Merit', font=body_font, fill=text_dark, anchor='mm')

y_pos = score_box_top + score_box_height + 60

# Project Title Block
draw.text((150, y_pos), 'PROJECT DETAILS', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 65

# Two-column grid layout
col1_x = 150
col2_x = width // 2 + 100

details = [
    ('Project Name', 'Telco USSD Assist MCP', 'Validation Date', 'November 15, 2025'),
    ('Code Repository', 'Publicly Auditable', 'Audit Authority', 'UCIC'),
]

for detail_set in details:
    col1_label, col1_value, col2_label, col2_value = detail_set
    
    # Column 1
    draw.text((col1_x, y_pos), col1_label + ':', font=label_font, fill=deep_navy, anchor='lm')
    draw.text((col1_x, y_pos + 40), col1_value, font=body_font, fill=text_dark, anchor='lm')
    
    # Column 2
    draw.text((col2_x, y_pos), col2_label + ':', font=label_font, fill=deep_navy, anchor='lm')
    draw.text((col2_x, y_pos + 40), col2_value, font=body_font, fill=text_dark, anchor='lm')
    
    y_pos += 120

y_pos += 40

# Validated Competencies Section - Two Column Grid
draw.text((150, y_pos), 'VALIDATED CORE COMPETENCIES', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 80

# Competency badges with scores
competencies = [
    ('Technical Architecture', '7/10', 'Solid code quality with 15 unit tests'),
    ('Mission Alignment', '8.5/10', 'Successfully addressed real problem'),
    ('API Integration', 'VERIFIED', 'Multiple AI Clients: Claude, Cursor, Gemini'),
    ('Deployment Status', 'VERIFIED', 'Live endpoint at FastMCP Cloud'),
]

competency_col1_x = 150
competency_col2_x = width // 2 + 100
competency_y = y_pos

# Left column competencies
for idx in range(0, len(competencies), 2):
    comp_name, score, description = competencies[idx]
    
    # Score badge box
    badge_width = 140
    badge_height = 70
    draw.rectangle([(competency_col1_x, competency_y), 
                   (competency_col1_x + badge_width, competency_y + badge_height)], 
                   fill=metallic_gold, outline=deep_navy, width=3)
    
    # Score text in badge
    draw.text((competency_col1_x + badge_width//2, competency_y + badge_height//2), 
             score, font=score_display_font, fill=deep_navy, anchor='mm')
    
    # Competency label
    draw.text((competency_col1_x + badge_width + 30, competency_y + 10), 
             comp_name, font=label_font, fill=deep_navy, anchor='lm')
    
    # Description
    draw.text((competency_col1_x + badge_width + 30, competency_y + 50), 
             description, font=small_font, fill=text_light, anchor='lm')
    
    competency_y += 130

# Right column competencies
competency_y = y_pos
for idx in range(1, len(competencies), 2):
    comp_name, score, description = competencies[idx]
    
    # Score badge box
    badge_width = 140
    badge_height = 70
    draw.rectangle([(competency_col2_x, competency_y), 
                   (competency_col2_x + badge_width, competency_y + badge_height)], 
                   fill=metallic_gold, outline=deep_navy, width=3)
    
    # Score text in badge
    draw.text((competency_col2_x + badge_width//2, competency_y + badge_height//2), 
             score, font=score_display_font, fill=deep_navy, anchor='mm')
    
    # Competency label
    draw.text((competency_col2_x + badge_width + 30, competency_y + 10), 
             comp_name, font=label_font, fill=deep_navy, anchor='lm')
    
    # Description
    draw.text((competency_col2_x + badge_width + 30, competency_y + 50), 
             description, font=small_font, fill=text_light, anchor='lm')
    
    competency_y += 130

y_pos += 400

# Integrity Assurance Section
draw.text((150, y_pos), 'INTEGRITY ASSURANCE', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 70

integrity_items = [
    ('Verifiable Code', 'Publicly accessible with complete transparency and permanent audit trail'),
    ('Focus on Utility', 'Genuine need identified and validated in Ghanaian market'),
    ('Permanent Record', 'Full technical analysis available on public GitHub repository'),
]

for title, description in integrity_items:
    draw.text((180, y_pos), '✓', font=body_font, fill=metallic_gold, anchor='lm')
    draw.text((240, y_pos), title + ':', font=label_font, fill=deep_navy, anchor='lm')
    draw.text((240, y_pos + 40), description, font=small_font, fill=text_light, anchor='lm')
    y_pos += 100

# Authority Section - Clearly separated at bottom
y_pos += 60
draw.line([(150, y_pos), (width-150, y_pos)], fill=metallic_gold, width=4)
y_pos += 50

draw.text((150, y_pos), 'VALIDATED BY AUTHORITY', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 70

authority_review = 'Detailed Technical Review by GitHub Copilot'
draw.text((180, y_pos), authority_review, font=body_font, fill=text_dark, anchor='lm')
y_pos += 60

founders_title = 'Founders and Technical Authorities'
draw.text((180, y_pos), founders_title, font=label_font, fill=deep_navy, anchor='lm')
y_pos += 60

# Authority names with full titles
authorities = [
    'Dr. Jodogn - Founder, Ubuntu Patient Care',
    'Dr. Tom Zubiri - Technical Authority, UCIC Chief Integrity Officer (AI)',
]

for auth in authorities:
    draw.text((200, y_pos), auth, font=body_font, fill=text_dark, anchor='lm')
    y_pos += 50

# Footer with navy background
footer_y = height - 140
draw.rectangle([(0, height-150), (width, height)], fill=deep_navy)

draw.text((width//2, footer_y - 20), 'Code integrity and technical merit are non-negotiable standards', 
          font=label_font, fill=metallic_gold, anchor='mm')

draw.text((width//2, footer_y + 40), 'Certificate Generated: ' + datetime.now().strftime('%B %d, %Y'), 
          font=footer_font, fill=bright_white, anchor='mm')
draw.text((width//2, footer_y + 80), '© 2025 Ubuntu Code Integrity Crucible - All Rights Reserved', 
          font=footer_font, fill='#bfdbfe', anchor='mm')

# Save as high-quality JPEG
output_path = 'c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Ubuntu Code Integrity Crucible (UCIC)/5-Telco-USSD-Assist/Telco_USSD_Technical_Certificate.jpg'
background.save(output_path, 'JPEG', quality=99)
print('✅ Professional certificate redesigned with high-authority styling')
print(f'✅ Resolution: 1920x2400px (premium print-ready)')
print(f'✅ Color palette: Deep Navy + Metallic Gold')
print(f'✅ Location: {output_path}')
