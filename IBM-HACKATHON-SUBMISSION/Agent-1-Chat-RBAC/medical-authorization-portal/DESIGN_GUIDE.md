# Frontend Design Guide - Visual Reference

## Login Page UI

```
┌─────────────────────────────────────────┐
│   [LOGO] Medical Portal                 │
│   Secure Healthcare Authorization       │
│                                         │
│   ┌───────────────┬───────────────┐    │
│   │   [Google]    │  [Microsoft]  │    │
│   └───────────────┴───────────────┘    │
│                                         │
│         ─────────────────────           │
│         Or continue with email          │
│         ─────────────────────           │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │ Username or Email               │  │
│   │ [__________________________]     │  │
│   └─────────────────────────────────┘  │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │ Password                   [👁]   │  │
│   │ [__________________________]     │  │
│   └─────────────────────────────────┘  │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │        [Sign In Button]         │  │
│   └─────────────────────────────────┘  │
│                                         │
│   Don't have an account? Create one     │
│                                         │
│   ┌─────────────────────────────────┐  │
│   │ Security Notice: This system    │  │
│   │ contains PHI. Unauthorized...   │  │
│   └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Color Scheme

### Primary Colors (Blue Gradient)
```
Gradient Start: #1e3c72 (Dark Blue)
Gradient Mid:  #2a5298 (Medium Blue)
Bright Blue:   #2563eb (Primary)
```

### Secondary Colors (Slate)
```
Darkest:  #0f172a (Background)
Dark:     #1e293b (Cards)
Medium:   #475569 (Text)
Light:    #e2e8f0 (Borders)
Lightest: #f8fafc (Input backgrounds)
```

### Status Colors
```
Success: #16a34a (Green)
Warning: #ea580c (Orange)
Error:   #dc2626 (Red)
Info:    #2563eb (Blue)
```

---

## Typography

### Font Family
**Inter** - Professional, modern, readable

```
Light (300)     - Captions, secondary text
Regular (400)   - Body text
Medium (500)    - Labels
Semibold (600)  - Buttons, subheadings
Bold (700)      - Headings
```

### Font Sizes
```
28px - Main heading (H1)
24px - Subheading (H2)
18px - Card titles
16px - Button text
14px - Body text
13px - Small text
12px - Captions
```

---

## Component Examples

### Button States

#### Primary Button
```
Normal:   Blue background, white text, shadow
Hover:   Slightly darker, shadow increases
Active:  Slightly raised effect
```

#### Secondary Button
```
Normal:   Light gray background
Hover:   Medium gray background
Active:  Pressed effect
```

### Input Fields

```
Default:  Light gray background, thin border
Focus:    White background, blue border, focus ring
Error:    Red border, error color text
```

### Cards

```
┌─────────────────────┐
│ Card Title          │
├─────────────────────┤
│ Card content here   │
│                     │
│ More content...     │
└─────────────────────┘

Border: 1px #e2e8f0
Shadow: 0 1px 2px rgba(0,0,0,0.05)
```

### Alerts

```
Success: Green left border, light green background
Warning: Orange left border, light orange background
Error:   Red left border, light red background
Info:    Blue left border, light blue background
```

---

## Layout System

### Spacing Unit: 8px base

```
Gap/Margin/Padding:
- Small:   8px
- Medium:  16px
- Large:   24px
- XLarge:  32px
```

### Border Radius

```
Small:    6px (inputs, small buttons)
Medium:   8px (cards, modals)
Large:    12px (large components)
Full:     9999px (pills)
```

### Shadows

```
sm:  0 1px 2px rgba(0, 0, 0, 0.05)
md:  0 4px 6px rgba(0, 0, 0, 0.1)
lg:  0 10px 15px rgba(0, 0, 0, 0.1)
xl:  0 20px 25px rgba(0, 0, 0, 0.1)
```

---

## Responsive Breakpoints

```
Mobile:    < 480px
Tablet:    480px - 768px
Desktop:   768px - 1200px
Wide:      > 1200px
```

### Mobile Adjustments
```
- Single column layout
- Larger touch targets
- Simplified navigation
- Stacked buttons
```

---

## Animation Specifications

### Slide Up (Page Load)
```
Duration:    600ms
Easing:      ease-out
Direction:   30px down → 0px
Opacity:     0% → 100%
```

### Fade In (Modal/Overlay)
```
Duration:    300ms
Easing:      ease-out
Opacity:     0% → 100%
```

### Hover Effects
```
Button:      translateY(-2px) + shadow increase
Card:        border color change + shadow increase
Link:        underline appear
```

---

## OAuth Button Styling

### Google Button
```
Border:   1.5px #e2e8f0
BG:       White
Color:    #334155
Icon:     Google G logo
Hover:    Light red tint background
```

### Microsoft Button
```
Border:   1.5px #e2e8f0
BG:       White
Color:    #334155
Icon:     Microsoft squares
Hover:    Light blue tint background
```

---

## Accessibility

### Focus States
```
All interactive elements have visible focus ring:
- 3px blue outline
- 0.1 opacity
```

### Color Contrast
```
Text on background: 4.5:1 ratio minimum
Large text: 3:1 ratio minimum
```

### Touch Targets
```
Minimum size: 44px × 44px
On mobile: larger targets for buttons
```

---

## Icons

All icons are SVG inline or from Lucide React:
```
- Eye / Eye-off (password toggle)
- Check (success)
- X (close)
- Alert Triangle (warning)
- Alert Circle (error)
- Info (information)
```

---

## Form Validation

### Error State
```
Border:   Red (#dc2626)
BG:       Light red (#fee2e2)
Message:  Red text below field
Icon:     Error icon
```

### Success State
```
Border:   Green (#16a34a)
BG:       Light green (#f0fdf4)
Message:  Green text below field
Icon:     Check icon
```

---

## Header Navigation

### Desktop Layout
```
┌────────────────────────────────────────┐
│ [Logo] Dashboard Patients ...  [User] │
│        ▲─────────────────────────▲     │
│        └─ Navigation Items ──────┘     │
└────────────────────────────────────────┘
```

### Mobile Layout
```
┌──────────────────────────────────┐
│ [Menu] Logo            [Settings]│
└──────────────────────────────────┘
Hamburger menu slides in from left
```

---

## Mobile Optimizations

### Buttons
```
- 44px minimum height
- Full width on mobile
- Stacked vertically
- Increased padding
```

### Forms
```
- Single column
- Large input fields
- Clear labels
- Number keypad for numeric inputs
```

### Text
```
- Minimum 16px font size
- Increased line height (1.8)
- Shorter paragraphs
```

---

## Dark Mode Consideration

Currently: **Light mode only**

If dark mode added:
```
Background:  #0f172a
Cards:       #1e293b
Text:        #f1f5f9
Borders:     #334155
```

---

## Performance Targets

```
First Contentful Paint:  < 1.5s
Largest Contentful Paint: < 2.5s
Cumulative Layout Shift: < 0.1
Time to Interactive:     < 3.5s
```

---

## Browser Compatibility

```
Chrome:     Latest 2 versions ✓
Firefox:    Latest 2 versions ✓
Safari:     Latest 2 versions ✓
Edge:       Latest 2 versions ✓
iOS Safari: Latest 2 versions ✓
Android Chrome: Latest 2 versions ✓
```

---

## File Size Targets

```
CSS:        < 50KB
JavaScript: < 100KB
Fonts:      < 200KB (system fonts)
Images:     < 500KB total
```

---

## Example Gradient Use

### Button Gradient
```css
background: linear-gradient(
  135deg,
  #2563eb 0%,
  #1d4ed8 100%
);
```

### Header Gradient
```css
background: linear-gradient(
  135deg,
  #1e3c72 0%,
  #2a5298 100%
);
```

---

This guide is a living document and will be updated as the design system evolves.

**Last Updated**: October 26, 2025
