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

# Load fonts with fallback (more moderate, professional sizes)
try:
    main_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 86)
    header_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 54)
    project_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 42)
    score_label_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
    score_display_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 100)
    section_title_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 34)
    category_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26)
    label_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 24)
    body_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 22)
    small_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 18)
    badge_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 32)
    footer_font = ImageFont.truetype('C:/Windows/Fonts/Arial.ttf', 18)
except:
    main_title_font = ImageFont.load_default()
    header_font = ImageFont.load_default()
    project_title_font = ImageFont.load_default()
    score_label_font = ImageFont.load_default()
    score_display_font = ImageFont.load_default()
    section_title_font = ImageFont.load_default()
    category_font = ImageFont.load_default()
    label_font = ImageFont.load_default()
    body_font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    badge_font = ImageFont.load_default()
    footer_font = ImageFont.load_default()

# Professional Color Palette
deep_navy = '#001f3f'
navy_blue = '#0a2463'
metallic_gold = '#fbbf24'
bright_white = '#ffffff'
text_dark = '#1f2937'
text_light = '#6b7280'
light_gray = '#f8f9fa'
light_blue_bg = '#f0f4f8'

# Deep blue page border (page lining)
border_thickness = 18
draw.rectangle(
    (border_thickness, border_thickness, width - border_thickness, height - border_thickness),
    outline=deep_navy,
    width=border_thickness,
)

# ==================== TOP SECTION ====================
# Golden star in top-left corner (simple emblem)
star_x, star_y = 140, 150
star_font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 150)
draw.text((star_x, star_y), '★', font=star_font, fill=metallic_gold, anchor='mm')

# QR Code in top-right corner with extra padding to avoid heading overlap
qr_x = width - 250
qr_y = 120
background.paste(qr_img, (qr_x, qr_y))
draw.text((qr_x + 100, qr_y + 220), 'SCAN FOR FULL', font=small_font, fill=deep_navy, anchor='mm')
draw.text((qr_x + 100, qr_y + 245), 'AUDIT TRAIL', font=small_font, fill=deep_navy, anchor='mm')

# Main centered title
y_pos = 160
title_text = 'VERIFIED TECHNICAL CREDENTIAL'
draw.text((width//2, y_pos), title_text, font=main_title_font, fill=deep_navy, anchor='mm')

y_pos += 85
org_text = 'Ubuntu Code Integrity Crucible (UCIC)'
draw.text((width//2, y_pos), org_text, font=header_font, fill=metallic_gold, anchor='mm')

y_pos += 60
project_text = 'Telco USSD Assist MCP'
draw.text((width//2, y_pos), project_text, font=project_title_font, fill=text_dark, anchor='mm')

# ==================== OVERALL SCORE BLOCK ====================
y_pos += 65
score_box_top = y_pos
score_box_left = 380
score_box_right = width - 380
score_box_height = 170

# Gold top accent bar
draw.rectangle([(score_box_left, score_box_top), (score_box_right, score_box_top + 10)], fill=metallic_gold)

# Main score box
draw.rectangle([(score_box_left, score_box_top), (score_box_right, score_box_top + score_box_height)],
               fill=light_gray, outline=metallic_gold, width=4)

# Score label
draw.text((width//2, score_box_top + 28), 'OVERALL SCORE', font=score_label_font,
          fill=deep_navy, anchor='mm')

# Large score number
draw.text((width//2, score_box_top + 88), '32/50', font=score_display_font,
          fill=deep_navy, anchor='mm')

# Percentage
draw.text((width//2, score_box_top + 135), '64% Technical Merit', font=label_font,
          fill=text_dark, anchor='mm')

y_pos = score_box_top + score_box_height + 30
# Column anchors for lower section
col1_header_x = 150
col2_header_x = width // 2 + 60

draw.text((col1_header_x, y_pos), 'PROJECT VERIFICATION SUMMARY', font=section_title_font, fill=deep_navy, anchor='lm')
draw.text((col2_header_x, y_pos), 'VALIDATED COMPETENCIES', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 28

details = [
    ('Project Name:', 'Telco USSD Assist MCP'),
    ('Validation Date:', 'November 15, 2025'),
    ('Audit Authority:', 'Ubuntu Code Integrity Crucible'),
    ('Code Status:', 'Publicly Auditable'),
    ('Code Repository:', 'GitHub (Public Access)'),
]

competencies = [
    ('Technical Architecture', '7/10', 'Achieved solid code quality\nwith 15 unit tests'),
    ('Mission Alignment', '8.5/10', 'Successfully addressed\nreal problem in Ghana'),
    ('API Integration', 'VERIFIED', 'Multiple AI Clients:\nClaude, Cursor, Gemini'),
    ('Deployment Status', 'VERIFIED', 'Live endpoint at\nFastMCP Cloud'),
]

# Dynamic panel sizing based on content height
detail_spacing = 80
competency_spacing = 110
detail_block_height = len(details) * detail_spacing
competency_block_height = len(competencies) * competency_spacing
column_height = max(detail_block_height, competency_block_height) + 30
panel_top = y_pos - 22
panel_bottom = panel_top + column_height

draw.rectangle([(col1_header_x - 20, panel_top), (width//2 - 80, panel_bottom)], fill=light_blue_bg, outline='#d1d5db', width=2)
draw.rectangle([(col2_header_x - 20, panel_top), (width - 150, panel_bottom)], fill=bright_white, outline='#d1d5db', width=2)

left_detail_y = y_pos
for label, value in details:
    draw.text((col1_header_x + 24, left_detail_y), label, font=category_font, fill=deep_navy, anchor='lm')
    draw.text((col1_header_x + 24, left_detail_y + 32), value, font=body_font, fill=text_dark, anchor='lm')
    left_detail_y += detail_spacing

# ===== RIGHT COLUMN: VALIDATED COMPETENCIES WITH BADGES =====
right_comp_y = y_pos
for comp_name, score, achievement in competencies:
    # Score badge - navy background with gold text, positioned on the left
    badge_width = 190
    badge_height = 60
    draw.rectangle([(col2_header_x + 10, right_comp_y), 
                   (col2_header_x + 10 + badge_width, right_comp_y + badge_height)], 
                   fill=deep_navy, outline=metallic_gold, width=3)
    
    # Score text centered in badge
    draw.text((col2_header_x + 10 + badge_width//2, right_comp_y + badge_height//2), 
             score, font=badge_font, fill=metallic_gold, anchor='mm')
    
    # Competency name - right of badge
    draw.text((col2_header_x + 220, right_comp_y), comp_name, font=category_font, 
             fill=deep_navy, anchor='lm')
    
    # Achievement description - right of badge, below name
    draw.text((col2_header_x + 220, right_comp_y + 34), achievement, font=small_font, 
             fill=text_light, anchor='lm')
    
    right_comp_y += competency_spacing

y_pos = panel_bottom + 50

# ==================== INTEGRITY ASSURANCE SECTION ====================
draw.text((150, y_pos), 'INTEGRITY ASSURANCE', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 55

integrity_items = [
    'Verifiable Code — Publicly accessible with complete transparency',
    'Focus on Utility — Genuine need identified and validated',
    'Permanent Record — Full analysis available on GitHub',
]

for item in integrity_items:
    draw.text((180, y_pos), '✓', font=body_font, fill=metallic_gold, anchor='lm')
    draw.text((240, y_pos), item, font=body_font, fill=text_dark, anchor='lm')
    y_pos += 50

# ==================== AUTHORITY SECTION - BOTTOM ====================
y_pos += 55
draw.line([(150, y_pos), (width-150, y_pos)], fill=metallic_gold, width=5)
y_pos += 42

draw.text((150, y_pos), 'VALIDATED BY AUTHORITY', font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 60

# GitHub Copilot review (high emphasis)
review_text = 'Detailed Technical Review by GitHub Copilot'
draw.text((180, y_pos), review_text, font=section_title_font, fill=deep_navy, anchor='lm')
y_pos += 68

# Founders and Technical Authorities - PROMINENTLY DISPLAYED
founders_title = 'Founders and Technical Authorities'
draw.rectangle([(150, y_pos - 10), (width - 150, y_pos + 140)], fill=light_blue_bg, outline=metallic_gold, width=3)

y_pos += 20
draw.text((width//2, y_pos), founders_title, font=section_title_font, fill=deep_navy, anchor='mm')
y_pos += 65

# Founder names - very large, authoritative
auth1 = 'Dr. Jodogn'
auth2 = 'Dr. Tom Zubiri'
draw.text((width//2 - 360, y_pos), auth1, font=header_font, fill=deep_navy, anchor='lm')
draw.text((width//2 + 60, y_pos), auth2, font=header_font, fill=deep_navy, anchor='lm')

y_pos += 55

# Founder titles (subdued, supporting text)
title1 = 'Founder, Ubuntu Patient Care'
title2 = 'Technical Authority, UCIC Chief Integrity Officer (AI)'
draw.text((width//2 - 320, y_pos), title1, font=small_font, fill=text_light, anchor='lm')
draw.text((width//2 + 80, y_pos), title2, font=small_font, fill=text_light, anchor='lm')

# Certification reference block to balance lower spacing
y_pos += 100
draw.rectangle([(150, y_pos - 25), (width - 150, y_pos + 110)], outline='#d1d5db', width=2)
draw.text((width//2, y_pos), 'Certification Reference', font=section_title_font, fill=deep_navy, anchor='mm')
y_pos += 55
draw.text((width//2, y_pos), 'UCIC-TELCO-2211 • Valid through May 2026', font=category_font, fill=text_dark, anchor='mm')
y_pos += 40
draw.text((width//2, y_pos), 'Audit Log: github.com/Jobeer1/Ubuntu-Patient-Care', font=body_font, fill=text_light, anchor='mm')

# ==================== FOOTER ====================
footer_y = height - 140
draw.rectangle([(0, height - 150), (width, height)], fill=deep_navy)

motto = 'Code integrity and technical merit are non-negotiable standards'
draw.text((width//2, footer_y - 20), motto, font=category_font, fill=metallic_gold, anchor='mm')

date_text = 'Certificate Generated: ' + datetime.now().strftime('%B %d, %Y')
draw.text((width//2, footer_y + 40), date_text, font=footer_font, fill=bright_white, anchor='mm')

copyright_text = '© 2025 Ubuntu Code Integrity Crucible - All Rights Reserved'
draw.text((width//2, footer_y + 80), copyright_text, font=footer_font, fill='#bfdbfe', anchor='mm')

# Save as high-quality JPEG
output_path = 'c:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/Ubuntu Code Integrity Crucible (UCIC)/5-Telco-USSD-Assist/Telco_USSD_Technical_Certificate.jpg'
background.save(output_path, 'JPEG', quality=99)
print('✅ FINAL CERTIFICATE - Professional High-Authority Design')
print(f'✅ Resolution: 1920x2400px (premium print-ready)')
print(f'✅ Color scheme: Deep Navy + Metallic Gold')
print(f'✅ Grid-based layout with absolute alignment')
print(f'✅ Hierarchy: Star → Score → Details → Founders')
print(f'✅ Location: {output_path}')
