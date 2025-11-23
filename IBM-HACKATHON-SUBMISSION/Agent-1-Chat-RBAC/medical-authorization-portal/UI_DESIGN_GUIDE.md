# 🎨 Visual Guide - Medical Authorization Portal UI

## Color Palette Reference

### Primary Colors
```
Green (South African):      #006533
Gold (South African):       #FFB81C
Blue (Medical):             #005580
Light Green:                #00d084
```

### Secondary Colors
```
Light Background:           #f8fafc
Success:                    #16a34a
Warning:                    #ffc107
Error:                      #dc2626
Info:                       #0c4a6e
```

### Neutral Colors
```
White:                      #ffffff
Text Primary:               #1e293b
Text Secondary:             #64748b
Text Tertiary:              #94a3b8
Border:                     #e0e0e0
```

---

## Login Page Layout

```
┌─────────────────────────────────────────┐
│                                         │
│     Background: Gradient Green→Gold     │
│                                         │
│    ┌─────────────────────────────────┐  │
│    │   White Container (Rounded)     │  │
│    │                                 │  │
│    │    🏥 Medical Portal Logo       │  │
│    │                                 │  │
│    │    Sign In to Your Account      │  │
│    │                                 │  │
│    │  [Google Icon]  [Microsoft Icon]│  │
│    │   Sign in with  Sign in with    │  │
│    │    Google        Microsoft      │  │
│    │                                 │  │
│    │    ─────── OR ───────           │  │
│    │                                 │  │
│    │   [ Username/Email Input ]      │  │
│    │   [ Password Input ••••• ]      │  │
│    │                                 │  │
│    │   [ Secure Login Button ]       │  │
│    │                                 │  │
│    │  Don't have account? Sign up    │  │
│    │                                 │  │
│    │  🔒 Security Notice             │  │
│    └─────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

---

## Admin Dashboard Layout

```
┌──────────────────────────────────────────────────────┐
│  🔧 Admin Dashboard          [Logout Button]         │
│  System Management & Analytics                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Users: 12   │ │ Pending: 5  │ │ Health: 100%│   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                      │
├──────────────────────────────────────────────────────┤
│  User Management        │    System Settings         │
│  ──────────────────────────────────────────         │
│  Name  │ Email │ Role   │ ✓ OAuth Enabled          │
│  Admin │ a@... │ ADMIN  │ ✓ 2FA Required           │
│  John  │ d@... │ DOCTOR │ □ Maintenance Mode       │
│  Mary  │ p@... │ PATIENT│ [Save Settings Button]   │
│        │       │        │                          │
├──────────────────────────────────────────────────────┤
│  Recent Pre-Authorizations                           │
│  ─────────────────────────────────────────          │
│  Auth ID │ Patient │ Status │ AI Conf │ Date       │
│  PA-001  │ Smith   │ ✓      │ 92%     │ 26 Oct     │
│  PA-002  │ Garcia  │ ⏳      │ 78%     │ 26 Oct     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Patient Dashboard Layout

```
┌──────────────────────────────────────────────────────┐
│  🏥 My Medical Portal          [Logout Button]       │
│  Welcome, [Patient Name]! Manage your authorizations │
├──────────────────────────────────────────────────────┤
│                                                      │
│  👤 My Information                                   │
│  ──────────────────────────────────────────         │
│  Name: [Full Name] │ Email: [Email]                 │
│  Status: Active    │ Scheme: Discovery              │
│                                                      │
├──────────────────────────────────────────────────────┤
│  💰 My Benefits                                      │
│  ──────────────────────────────────────────         │
│  Annual Limit: R500,000                              │
│  Used: R185,000  │  Available: R315,000 ✓            │
│  Co-payment: 20%                                     │
│                                                      │
│  ✓ Diagnostic Imaging (X-Ray, CT, MRI)              │
│  ✓ Laboratory Tests (Blood work)                     │
│  ✓ Medical Consultations                            │
│  ✓ Hospitalization                                  │
│                                                      │
├──────────────────────────────────────────────────────┤
│  📋 My Pre-Authorizations                            │
│  ──────────────────────────────────────────         │
│                                                      │
│  ┌─────────────────────────────────┐                │
│  │ ✓ PA-20251026-ABC123 (APPROVED) │                │
│  │ CT Head with Contrast            │                │
│  │ Valid Until: 25 Nov 2025         │                │
│  │ Estimated Cost: R2,450           │                │
│  │ [View Details] [Print]           │                │
│  └─────────────────────────────────┘                │
│                                                      │
│  ┌─────────────────────────────────┐                │
│  │ ⏳ PA-20251025-DEF456 (PENDING) │                │
│  │ MRI Brain - Awaiting Review      │                │
│  │ Requested: 25 Oct 2025           │                │
│  │ Estimated Cost: R3,500           │                │
│  │ [View Details] [Cancel Request]  │                │
│  └─────────────────────────────────┘                │
│                                                      │
│  ┌─────────────────────────────────┐                │
│  │ ✗ PA-20251020-GHI789 (DENIED)   │                │
│  │ Advanced 3D Imaging              │                │
│  │ Reason: Not medically necessary  │                │
│  │ [Request Appeal] [View Details]  │                │
│  └─────────────────────────────────┘                │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [➕ Request New Authorization]                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Doctor Dashboard Layout

```
┌──────────────────────────────────────────────────────┐
│  👨‍⚕️ Doctor Dashboard              [Logout Button]   │
│  Manage pre-authorizations                           │
│  Dr. [Name] | License: ML-2025-XXXX                  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Pending: 8  │ │ Approved:12 │ │ Patients:45 │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                      │
├──────────────────────────────────────────────────────┤
│  📋 Pre-Authorization Requests                       │
│  ──────────────────────────────────────────         │
│  [Pending] [Approved] [Denied]                       │
│                                                      │
│  ┌─────────────────────────────────────┐             │
│  │ John Smith          ⏳ Under Review │             │
│  │                                     │             │
│  │ 🩺 CT Head with Contrast            │             │
│  │ 💰 R2,450  │ 📅 26 Oct 2025         │             │
│  │ 📝 Suspected cerebral infarction    │             │
│  │                                     │             │
│  │ [✓ Approve] [✗ Deny] [View] [Notes]│             │
│  └─────────────────────────────────────┘             │
│                                                      │
│  ┌─────────────────────────────────────┐             │
│  │ Maria Garcia        ⏳ Under Review │             │
│  │                                     │             │
│  │ 🩺 MRI Brain with Contrast          │             │
│  │ 💰 R3,500  │ 📅 26 Oct 2025         │             │
│  │ 📝 Recurrent headaches              │             │
│  │                                     │             │
│  │ [✓ Approve] [✗ Deny] [View] [Notes]│             │
│  └─────────────────────────────────────┘             │
│                                                      │
├──────────────────────────────────────────────────────┤
│  👥 My Patients                                      │
│  ──────────────────────────────────────────         │
│  Name   │ Patient ID │ Last Visit  │ Actions        │
│  Smith  │ PAT-001    │ 26 Oct      │ [Chart][Msg]   │
│  Garcia │ PAT-002    │ 25 Oct      │ [Chart][Msg]   │
│  Johnson│ PAT-003    │ 24 Oct      │ [Chart][Msg]   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Component Specifications

### Buttons

**Primary Button (Green)**
```
Background: #006533
Text Color: White
Padding: 10px 20px
Border-Radius: 6px
Font-Weight: 600
Hover: #005580 with transform
```

**Success Button (Green)**
```
Background: #16a34a
Text Color: White
Usage: Approve, Accept, Yes
Hover: #15803d
```

**Danger Button (Red)**
```
Background: #dc2626
Text Color: White
Usage: Deny, Delete, No
Hover: #b91c1c
```

**Secondary Button (Gray)**
```
Background: #e0e0e0
Text Color: #1e293b
Usage: Cancel, Skip, More info
Hover: #d0d0d0
```

### Status Badges

**Approved (Green)**
```
Background: #d1fae5
Text: #065f46
Border: none
Padding: 6px 12px
Border-Radius: 20px
Icon: ✓
```

**Pending (Yellow)**
```
Background: #fef3c7
Text: #92400e
Border: none
Padding: 6px 12px
Border-Radius: 20px
Icon: ⏳
```

**Denied (Red)**
```
Background: #fee2e2
Text: #991b1b
Border: none
Padding: 6px 12px
Border-Radius: 20px
Icon: ✗
```

### Form Inputs

**Text Input**
```
Background: #f8fafc
Border: 2px solid #e0e0e0
Border-Radius: 8px
Padding: 12px 14px
Font-Size: 14px
Focus: Border #006533, Box-shadow with green
```

**Select Dropdown**
```
Same as Text Input
```

### Cards

**Stat Card**
```
Background: White
Padding: 25px
Border-Radius: 12px
Border-Left: 5px solid #006533
Box-Shadow: 0 2px 10px rgba(0,0,0,0.08)
Hover: Lift up with enhanced shadow
```

**Data Card**
```
Background: #f8fafc
Border: 2px solid #e0e0e0
Border-Radius: 10px
Padding: 20px
Hover: Border #006533, subtle shadow
```

---

## Typography

### Headings
```
H1: 28-32px, bold, color #006533
H2: 20-24px, bold, color #006533
H3: 15-18px, semi-bold, color #1e293b
```

### Body Text
```
Default: 14px, color #1e293b
Secondary: 13px, color #64748b
Small: 12px, color #94a3b8
```

### Labels
```
Font-Size: 12px
Font-Weight: 600
Color: #1e293b
Text-Transform: uppercase
Letter-Spacing: 0.5px
```

---

## Responsive Breakpoints

```
Mobile:     0px - 480px
Tablet:     481px - 768px
Desktop:    769px - 1024px
Large:      1025px+
```

### Grid Adjustments
```
Mobile:     1 column
Tablet:     2 columns
Desktop:    3-4 columns
Large:      4+ columns
```

---

## Animation Specifications

### Button Hover
```
Transform: translateY(-2px)
Transition: all 0.3s ease
Box-Shadow: Enhanced on hover
```

### Card Hover
```
Transform: translateY(-5px)
Transition: all 0.3s ease
Box-Shadow: 0 10px 25px rgba(0,0,0,0.12)
```

### Fade In
```
Opacity: 0 → 1
Transition: all 0.3s ease
```

### Slide Down
```
Transform: translateY(-10px) → translateY(0)
Opacity: 0 → 1
Transition: all 0.3s ease
```

---

## Icon References

Used throughout the application:
```
🏥 Medical/Hospital
🔧 Admin/Settings
👤 User/Profile
🔒 Security/Lock
✓ Approve/Success
✗ Deny/Error
⏳ Pending/Wait
🚪 Logout
💼 Business/Admin
👥 People/Users
💰 Benefits/Money
📋 Documents/Forms
📧 Email
🔐 Security
🩺 Medical/Doctor
📊 Analytics/Charts
⚡ Quick/Fast
```

---

## Accessibility Features

- ✅ Semantic HTML (header, nav, main, section)
- ✅ ARIA labels for icons
- ✅ Keyboard navigation support
- ✅ Color contrast ratios (WCAG AA minimum)
- ✅ Form labels associated with inputs
- ✅ Title attributes for buttons
- ✅ Focus states on interactive elements

---

**Design System v1.0**  
**Last Updated:** October 26, 2025
