# UI Interface Core Specifications

## Document Purpose

This document provides **in-depth specifications** for all UI interface core logic and accessibility features in the Braille Card and Cylinder STL Generator application. It serves as an authoritative reference for future development by documenting:

1. **Theme System** — Dark mode, light mode, and high contrast mode implementations
2. **Font Size Adjustment** — Accessibility scaling system
3. **STL Preview Panel** — Three.js 3D viewer configuration and theme-aware rendering
4. **Accessibility Features** — Keyboard navigation, screen reader support, focus indicators
5. **User Preference Handling** — Session-based settings (non-persistent by design)
6. **Help Modal System** — Accessible tabbed help with BANA business card guidance

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source for server-side logic
2. `wsgi.py` — Application startup and configuration
3. `static/workers/csg-worker.js` — Client-side CSG (three-bvh-csg)
4. Manifold WASM (`csg-worker-manifold.js`) — Mesh repair and validation

---

## ⚠️ CRITICAL: HTML File Location Warning

**There are TWO `index.html` files in this project. You MUST edit the correct one:**

| File | Purpose | Served by Flask? | Status |
|------|---------|------------------|--------|
| **`public/index.html`** | **PRODUCTION FILE — Edit this one!** | ✅ YES | **ACTIVE** |
| `templates/index.html` | Legacy/backup file — NOT served | ❌ NO | **⛔ DEPRECATED** |

### `templates/index.html` Deprecation Notice (2026-01-28)

The `templates/index.html` file is **officially deprecated** and should not be edited. It is missing critical features present in `public/index.html`:

| Missing Feature | Purpose |
|----------------|---------|
| `viewport-fit=cover` | iOS notch support |
| `--vh` CSS variable | Mobile viewport handling |
| `safe-area-inset-*` CSS | Edge-to-edge display support |
| `nomodule` fallback script | Older browser compatibility |
| `prefers-reduced-motion` CSS/JS | Motion accessibility |
| WebGL context loss recovery | Graphics stability |

**This file may be removed in a future release.**

**Why this matters:**
- The Flask backend (`backend.py`) serves `public/index.html` via `send_from_directory('public', 'index.html')`
- Changes to `templates/index.html` will have **NO EFFECT** on the running application
- Both files may contain similar content, which can cause confusion

**Before making UI changes:**
1. Always edit `public/index.html`
2. Verify the correct file by checking `backend.py` routes if uncertain
3. Hard refresh the browser (Ctrl+Shift+R) after changes to clear cache

**Route Configuration (from `backend.py`):**
```python
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/index.html')
def index_explicit():
    return send_from_directory('public', 'index.html')
```

---

## Table of Contents

1. [Theme System](#1-theme-system)
   - 1.1 [Theme Modes Overview](#11-theme-modes-overview)
   - 1.2 [Theme CSS Variables](#12-theme-css-variables)
   - 1.3 [High Contrast Mode Specifications](#13-high-contrast-mode-specifications)
   - 1.4 [Theme Switching Logic](#14-theme-switching-logic)
   - 1.5 [Theme Persistence Policy](#15-theme-persistence-policy)
2. [Font Size Adjustment System](#2-font-size-adjustment-system)
   - 2.1 [Font Size Scale](#21-font-size-scale)
   - 2.2 [Font Size Controls UI](#22-font-size-controls-ui)
   - 2.3 [Font Size Logic](#23-font-size-logic)
   - 2.4 [Screen Reader Announcements](#24-screen-reader-announcements)
3. [STL Preview Panel](#3-stl-preview-panel)
   - 3.1 [Three.js Scene Configuration](#31-threejs-scene-configuration)
   - 3.2 [Theme-Aware Colors and Lighting](#32-theme-aware-colors-and-lighting)
   - 3.3 [High Contrast Mode Lighting](#33-high-contrast-mode-lighting)
   - 3.4 [Camera and Controls](#34-camera-and-controls)
     - 3.4.1 [CAMERA_SETTINGS Global Configuration](#341-camera_settings-global-configuration)
     - 3.4.2 [Coordinate System Reference](#342-coordinate-system-reference)
     - 3.4.3 [How to Adjust the Initial Camera View](#343-how-to-adjust-the-initial-camera-view)
     - 3.4.4 [Camera Implementation Details](#344-camera-implementation-details)
     - 3.4.5 [OrbitControls Configuration](#345-orbitcontrols-configuration)
   - 3.5 [Mobile Optimizations](#35-mobile-optimizations)
   - 3.6 [Dynamic Theme Updates](#36-dynamic-theme-updates)
   - 3.7 [STL Preview Label](#37-stl-preview-label)
   - 3.8 [Preview Display Settings (Brightness and Contrast)](#38-preview-display-settings-brightness-and-contrast)
   - 3.9 [WebGL Context Recovery](#39-webgl-context-recovery)
4. [Accessibility Features](#4-accessibility-features)
   - 4.1 [Skip Link Navigation](#41-skip-link-navigation)
   - 4.2 [Focus Indicators](#42-focus-indicators)
   - 4.3 [Screen Reader Support](#43-screen-reader-support)
   - 4.4 [Touch and Mobile Accessibility](#44-touch-and-mobile-accessibility)
   - 4.5 [Toggle Button ARIA Requirements](#45-toggle-button-aria-requirements)
   - 4.6 [Reduced Motion Support](#46-reduced-motion-support)
   - 4.7 [Two-Way Translation Controls](#47-two-way-translation-controls)
   - 4.8 [Double-Sided Card Beta: Disclosure Checkbox and Locked Radio Option](#48-double-sided-card-beta-disclosure-checkbox-and-locked-radio-option)
   - 4.9 [Button Contrast Tokens and the 44 px Action Button](#49-button-contrast-tokens-and-the-44-px-action-button)
   - 4.10 [Live Regions Must Already Be in the Accessibility Tree](#410-live-regions-must-already-be-in-the-accessibility-tree)
5. [Scrollbar Customization](#5-scrollbar-customization)
   - 5.1 [Form Scroll Area Scrollbar](#51-form-scroll-area-scrollbar)
   - 5.2 [Global Page Scrollbar](#52-global-page-scrollbar)
   - 5.3 [Theme-Specific Scrollbar Styles](#53-theme-specific-scrollbar-styles)
6. [Button State Management](#6-button-state-management)
   - 6.1 [Action Button States](#61-action-button-states)
   - 6.2 [Resetting on Settings Changes](#62-resetting-on-settings-changes)
   - 6.3 [Action Button Placement](#63-action-button-placement)
   - 6.4 [High Contrast Button Styling](#64-high-contrast-button-styling)
7. [Layout Responsiveness](#7-layout-responsiveness)
   - 7.1 [Desktop Two-Column Layout](#71-desktop-two-column-layout)
   - 7.2 [Mobile Stacked Layout](#72-mobile-stacked-layout)
   - 7.3 [iOS Safe Area Handling](#73-ios-safe-area-handling)
8. [Help Modal System](#8-help-modal-system)
   - 8.1 [Overview](#81-overview)
   - 8.2 [Modal Structure](#82-modal-structure)
   - 8.3 [Tab Panels](#83-tab-panels)
   - 8.4 [Accessibility Features](#84-accessibility-features)
   - 8.5 [JavaScript API](#85-javascript-api)
   - 8.6 [Trigger Buttons](#86-trigger-buttons)
   - 8.7 [CSS Classes](#87-css-classes)
   - 8.8 [High Contrast Mode](#88-high-contrast-mode)
   - 8.9 [Related Documentation](#89-related-documentation)
9. [Design Rationale](#9-design-rationale)

---

## 1. Theme System

### 1.1 Theme Modes Overview

The application supports **three theme modes** designed to accommodate different visual preferences and accessibility needs:

| Theme | Purpose | Primary Users |
|-------|---------|---------------|
| **Dark** | Reduced eye strain in low-light environments | Default for all users |
| **Light** | Traditional high-brightness interface | Users preferring light backgrounds |
| **High Contrast** | Maximum visibility for low vision users | Users with visual impairments |

**Theme Cycle Order:**
```
Dark → High Contrast → Light → Dark (repeats)
```

**CRITICAL:** The application **always starts in Dark mode** regardless of user's system preferences. This is an intentional design decision to provide a consistent starting experience.

### 1.2 Theme CSS Variables

All theme-dependent colors are defined using CSS custom properties (variables) on the `:root` element and `[data-theme]` attribute selectors.

#### Light Mode (Default CSS Variables)

```css
:root {
    /* Background colors */
    --bg-gradient-start: #e0e7ff;
    --bg-gradient-end: #f6f8fa;
    --bg-primary: #fff;
    --bg-secondary: #f8fafc;
    --bg-tertiary: #f1f5f9;
    --bg-input: #f9fafb;

    /* Text colors */
    --text-primary: #2d3748;
    --text-secondary: #4a5568;
    --text-tertiary: #666;

    /* Border colors */
    --border-primary: #e2e8f0;
    --border-secondary: #cbd5e1;
    --border-focus: #3182ce;

    /* Button colors — every gradient stop clears 4.5:1 against the #fff label
       on its own; border tokens equal the fill here because the fill already
       clears 3:1 against the surface behind it (see Section 4.9) */
    --btn-primary-bg: linear-gradient(90deg, #245d94 60%, #2c6ca8 100%);
    --btn-primary-hover-bg: linear-gradient(90deg, #1d4e7c 60%, #245d94 100%);
    --btn-success-bg: #0f7a5a;
    --btn-success-hover-bg: #0c6349;
    --btn-primary-border: #245d94;
    --btn-primary-border-hover: #1d4e7c;
    --btn-success-border: #0f7a5a;
    --btn-success-border-hover: #0c6349;
    --btn-secondary-bg: #9ca3af;
    --btn-tertiary-bg: #6b7280;

    /* Status colors */
    --error-bg: #fee2e2;
    --error-border: #fecaca;
    --error-text: #b91c1c;
    --info-bg: #dbeafe;
    --info-border: #93c5fd;
    --info-text: #1e40af;

    /* Front-of-card warning and note text (added 2026-08-21). Measured on
       --bg-secondary, the surface all three boxes sit on: 6.18:1 and 5.08:1.
       Both reuse a value already in this palette rather than adding a new hex
       - --warning-text is --error-text, --note-text is --btn-success-bg. */
    --warning-text: #b91c1c;
    --note-text: #0f7a5a;

    /* Skip link label. One value serves all three themes - it clears 4.5:1 on
       every --border-focus (5.21 / 9.20 / 6.70), so it is declared once here
       and not repeated per theme. See Section 4.1. */
    --skip-link-text: #000000;

    /* Shadow colors */
    --shadow-light: rgba(49,130,206,0.10);
    --shadow-medium: rgba(49,130,206,0.18);

    /* STL Preview colors - CRITICAL FOR 3D VIEWING */
    --stl-mesh-color: #5580b3;
    --stl-edge-color: #020617;
    --stl-background: #f1f5f9;
    --stl-ambient-light: #888888;
    --stl-directional-light: #ffffff;
    --stl-ambient-intensity: 0.5;
    --stl-directional-intensity: 1.0;

    /* Scrollbar dimensions */
    --scrollbar-width: 18px;
    --global-scrollbar-width: 13.5px;
    --scrollbar-arrow-color: #3182ce;
}
```

#### Dark Mode

```css
[data-theme="dark"] {
    /* Background colors */
    --bg-gradient-start: #1a202c;
    --bg-gradient-end: #2d3748;
    --bg-primary: #2d3748;
    --bg-secondary: #374151;
    --bg-tertiary: #4a5568;
    --bg-input: #374151;

    /* Text colors */
    --text-primary: #f7fafc;
    --text-secondary: #e2e8f0;
    --text-tertiary: #cbd5e1;

    /* Border colors */
    --border-primary: #4a5568;
    --border-secondary: #718096;
    --border-focus: #63b3ed;

    /* Button colors — solid, not gradient: a fill dark enough for a #fff label
       drops under 3:1 against the #374151 surface, so the border carries the
       component boundary instead (see Section 4.9) */
    --btn-primary-bg: #2c6ca8;
    --btn-primary-hover-bg: #245d94;
    --btn-success-bg: #0c6b4f;
    --btn-success-hover-bg: #0a5940;
    --btn-primary-border: #90cdf4;
    --btn-primary-border-hover: #bee3f8;
    --btn-success-border: #6ee7b7;
    --btn-success-border-hover: #a7f3d0;
    --btn-secondary-bg: #718096;
    --btn-tertiary-bg: #4a5568;

    /* Status colors */
    --error-bg: #742a2a;
    --error-border: #9b2c2c;
    --error-text: #fed7d7;
    --info-bg: #2c5282;
    --info-border: #3182ce;
    --info-text: #bee3f8;

    /* 7.81:1 and 6.76:1 on --bg-secondary. Same reuse as the light theme:
       --error-text and --btn-success-border. */
    --warning-text: #fed7d7;
    --note-text: #6ee7b7;

    /* Shadow colors */
    --shadow-light: rgba(0,0,0,0.3);
    --shadow-medium: rgba(0,0,0,0.5);

    /* STL Preview colors */
    --stl-mesh-color: #90cdf4;
    --stl-edge-color: #1a202c;
    --stl-background: #2d3748;
    --stl-ambient-light: #666666;
    --stl-directional-light: #ffffff;
    --stl-ambient-intensity: 0.6;
    --stl-directional-intensity: 0.9;

    /* Scrollbar */
    --scrollbar-arrow-color: #63b3ed;
}
```

### 1.3 High Contrast Mode Specifications

**CRITICAL FOR LOW VISION USERS:** High Contrast mode uses a specific color palette designed for maximum visibility and readability. These values must be maintained precisely.

#### High Contrast Color Palette

```css
[data-theme="high-contrast"] {
    /* Background - Pure black for maximum contrast */
    --bg-gradient-start: #000000;
    --bg-gradient-end: #000000;
    --bg-primary: #000000;
    --bg-secondary: #1a1a1a;
    --bg-tertiary: #2a2a2a;
    --bg-input: #1a1a1a;

    /* Text - Bright green (#02fe05) for primary text */
    --text-primary: #02fe05;
    --text-secondary: #02fe05;
    --text-tertiary: #02fe05;

    /* Borders - High visibility colors */
    --border-primary: #ffff00;      /* Yellow */
    --border-secondary: #00ffff;    /* Cyan */
    --border-focus: #ff00ff;        /* Magenta */

    /* Buttons - Green for primary actions */
    --btn-primary-bg: #02fe05;
    --btn-primary-hover-bg: #02fe05;
    --btn-success-bg: #02fe05;
    --btn-success-hover-bg: #02fe05;
    /* Declared for completeness; every high-contrast button rule below sets its
       own border with !important, so these tokens never paint */
    --btn-primary-border: #000000;
    --btn-primary-border-hover: #ffff00;
    --btn-success-border: #000000;
    --btn-success-border-hover: #ffff00;
    --btn-secondary-bg: #ff6600;    /* Orange */
    --btn-tertiary-bg: #ff6600;

    /* Status colors */
    --error-bg: #ff0000;
    --error-border: #ff0000;
    --error-text: #02fe05;
    --info-bg: #0000ff;
    --info-border: #0000ff;
    --info-text: #02fe05;

    /* Declared for completeness only: the [data-theme="high-contrast"]
       .grade-note rule forces #fdfe00 with !important and the strong rule
       forces #02fe05, so neither token paints. Both already clear the floor
       (16.04:1 body, 12.58:1 label). */
    --warning-text: #fdfe00;
    --note-text: #fdfe00;

    /* No shadows in high contrast mode */
    --shadow-light: none;
    --shadow-medium: none;

    /* STL Preview - CRITICAL SETTINGS FOR LOW VISION */
    --stl-mesh-color: #00ffff;              /* Bright cyan mesh */
    --stl-edge-color: #000000;              /* Near-maximum contrast on cyan */
    --stl-background: #000000;              /* Pure black background */
    --stl-ambient-light: #666666;           /* Reduced ambient to prevent washing out */
    --stl-directional-light: #e6e6e6;       /* Slightly dimmed for better contrast */
    --stl-ambient-intensity: 0.4;           /* Lower ambient intensity */
    --stl-directional-intensity: 0.8;       /* Controlled directional intensity */

    /* Scrollbar */
    --scrollbar-arrow-color: #02fe05;
}
```

#### High Contrast Color Semantics

| Color Code | Color Name | Usage |
|------------|------------|-------|
| `#02fe05` | Bright Green | Primary text, success states |
| `#fdfe00` | Yellow | Italic text, notes, secondary highlights |
| `#ffff00` | Pure Yellow | Borders, font size controls |
| `#00ffff` | Cyan | STL mesh, reset buttons, accent borders |
| `#ff00ff` | Magenta | Focus indicators |
| `#0201fe` | Blue | Generate button background |
| `#fd01fc` | Violet | Application title |
| `#ff6600` | Orange | Counter plate button, tertiary actions |
| `#000000` | Black | All backgrounds |

#### High Contrast Button Specifications

```css
/* Generate STL Button (Blue background, Yellow text) */
[data-theme="high-contrast"] #action-btn.generate-state {
    background: #0201fe !important;
    color: #fdfe00 !important;
    border: 2px solid #fdfe00 !important;
}

[data-theme="high-contrast"] #action-btn.generate-state:hover {
    border: 2px solid #02fe05 !important;  /* Green border on hover */
}

/* Download STL Button (Green background, Black text) */
[data-theme="high-contrast"] #action-btn.download-state {
    background: #02fe05 !important;
    color: #000000 !important;
    border: 2px solid #000000 !important;
}

[data-theme="high-contrast"] #action-btn.download-state:hover {
    border: 2px solid #ffff00 !important;  /* Yellow border on hover */
}

/* Disabled/Loading State */
[data-theme="high-contrast"] #action-btn:disabled {
    background: #666666 !important;
    color: #cccccc !important;
    border: 2px solid #999999 !important;
    cursor: not-allowed !important;
}
```

### 1.4 Theme Switching Logic

#### JavaScript Implementation

```javascript
// Theme configuration
const themes = ['dark', 'high-contrast', 'light'];
const themeIcons = {
    'dark': '🌙',
    'high-contrast': '⚡',
    'light': '🌞'
};
const themeNames = {
    'dark': 'Dark',
    'high-contrast': 'High Contrast',
    'light': 'Light'
};

let currentThemeIndex = 0;

// Always start in dark mode
applyTheme('dark');

function applyTheme(theme) {
    // Set the data-theme attribute on document root
    document.documentElement.setAttribute('data-theme', theme);

    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    const themeText = themeToggle.querySelector('.theme-text');

    // Calculate and display the NEXT theme (what clicking will change to)
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const nextTheme = themes[nextIndex];

    // Button shows what will happen next, not current state
    themeIcon.textContent = themeIcons[nextTheme];
    themeText.textContent = themeNames[nextTheme];

    // Update ARIA label for screen readers
    themeToggle.setAttribute('aria-label',
        `Current theme: ${themeNames[theme]}. Click to switch to ${themeNames[nextTheme]} theme`);

    // Announce change to screen readers
    const announcement = document.createElement('div');
    announcement.className = 'sr-only';
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.textContent = `Theme changed to ${themeNames[theme]}`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);

    // Update 3D scene colors
    update3DSceneColors();
}

// Theme toggle click handler
document.getElementById('theme-toggle').addEventListener('click', () => {
    currentThemeIndex = (currentThemeIndex + 1) % themes.length;
    applyTheme(themes[currentThemeIndex]);
});
```

### 1.5 Theme Persistence Policy

**IMPORTANT DESIGN DECISION:** Theme preferences are **NOT persisted** across sessions.

**Rationale:**
- Ensures consistent starting experience for all users
- Prevents confusion when users access from different devices
- Dark mode provides the best initial experience for most users
- Users with specific accessibility needs can quickly switch to High Contrast mode

**Implementation:**
```javascript
// Always start in dark mode; do not persist theme
applyTheme('dark');

// NO localStorage calls for theme preference
// Theme resets to dark on every page load
```

---

## 2. Font Size Adjustment System

### 2.1 Font Size Scale

The font size system uses a **predefined scale** of percentage values that apply to the root `<html>` element:

```javascript
const fontSizes = [75, 87.5, 100, 112.5, 125, 150, 175, 200];
//                  ↑    ↑     ↑     ↑      ↑    ↑    ↑    ↑
//               index: 0    1     2     3      4    5    6    7
//                    75%  87.5% 100%  112.5% 125% 150% 175% 200%
```

| Index | Percentage | Description |
|-------|------------|-------------|
| 0 | 75% | Minimum size |
| 1 | 87.5% | Small |
| 2 | 100% | **Default** (standard browser size) |
| 3 | 112.5% | Slightly enlarged |
| 4 | 125% | Medium enlargement |
| 5 | 150% | Large |
| 6 | 175% | Extra large |
| 7 | 200% | Maximum size |

### 2.2 Font Size Controls UI

```
┌─────────────────────────────────────────┐
│  [ A- ]  [ 100 ]  [ A+ ]  [ Reset ]     │
│    ↓        ↓        ↓        ↓         │
│ Decrease  Display  Increase  Reset      │
│           (shows %)          to 100%    │
└─────────────────────────────────────────┘
```

#### HTML Structure

```html
<div class="font-size-controls" role="group" aria-label="Font size controls">
    <button id="font-decrease" class="font-size-btn"
            aria-label="Decrease font size">A-</button>
    <span id="current-font-size" class="font-size-display"
          aria-live="polite">100</span>
    <button id="font-increase" class="font-size-btn"
            aria-label="Increase font size">A+</button>
    <button id="font-reset" class="font-size-btn reset-btn"
            aria-label="Reset font size to default">Reset</button>
</div>
```

### 2.3 Font Size Logic

```javascript
let currentFontSizeIndex = 2; // Start at 100%

// Always start at default 100%; do not persist font size
currentFontSizeIndex = 2;

function applyFontSize(sizeIndex) {
    const size = fontSizes[sizeIndex];

    // Apply to root element - all rem/em units scale accordingly
    document.documentElement.style.fontSize = size + '%';

    // Update display
    document.getElementById('current-font-size').textContent = size;
    currentFontSizeIndex = sizeIndex;

    // Screen reader announcement
    const announcement = document.createElement('div');
    announcement.className = 'sr-only';
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.textContent = `Font size changed to ${size}%`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
}

// Initialize
applyFontSize(currentFontSizeIndex);

// Event listeners
document.getElementById('font-decrease').addEventListener('click', () => {
    if (currentFontSizeIndex > 0) {
        applyFontSize(currentFontSizeIndex - 1);
    }
});

document.getElementById('font-increase').addEventListener('click', () => {
    if (currentFontSizeIndex < fontSizes.length - 1) {
        applyFontSize(currentFontSizeIndex + 1);
    }
});

document.getElementById('font-reset').addEventListener('click', () => {
    applyFontSize(2); // Reset to 100%
});
```

### 2.4 Screen Reader Announcements

Both theme changes and font size changes announce to screen readers using a dynamically created `aria-live` region:

```javascript
// Pattern for announcements
const announcement = document.createElement('div');
announcement.className = 'sr-only';           // Visually hidden
announcement.setAttribute('role', 'status');
announcement.setAttribute('aria-live', 'polite');
announcement.textContent = 'Announcement text here';
document.body.appendChild(announcement);
setTimeout(() => announcement.remove(), 1000);  // Clean up after 1 second
```

**CSS for Screen Reader Only Content:**
```css
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
```

---

## 3. STL Preview Panel

### 3.1 Three.js Scene Configuration

The STL preview uses Three.js for 3D rendering with the following configuration:

```javascript
function init3D() {
    const isMobile = window.innerWidth <= 768;

    // Renderer configuration
    renderer = new THREE.WebGLRenderer({
        antialias: !isMobile,  // Disable antialiasing on mobile for performance
        powerPreference: isMobile ? "low-power" : "high-performance"
    });

    const initW = viewer.clientWidth;
    const initH = viewer.clientHeight || 420;
    renderer.setSize(initW, initH, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 2 : 3));

    // Scene setup
    scene = new THREE.Scene();

    // Camera configuration
    camera = new THREE.PerspectiveCamera(45, initW / initH, 0.1, 1000);
    camera.position.set(0, 0, 120);
    camera.up.set(0, 1, 0);  // Y-up orientation
    camera.lookAt(0, 0, 0);

    // Add camera to scene for attached lights
    scene.add(camera);

    // Orbit controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.rotateSpeed = isMobile ? 0.5 : 1.0;
    controls.zoomSpeed = isMobile ? 0.8 : 1.2;
    controls.panSpeed = isMobile ? 0.5 : 0.8;

    // Touch controls
    controls.touches = {
        ONE: THREE.TOUCH.ROTATE,
        TWO: THREE.TOUCH.DOLLY_PAN
    };
}
```

### 3.2 Theme-Aware Colors and Lighting

The 3D scene colors are read from CSS variables and applied dynamically:

```javascript
// Get theme colors from CSS variables
const styles = getComputedStyle(document.documentElement);
const stlBackground = styles.getPropertyValue('--stl-background').trim() || '#f1f5f9';
const stlAmbientLight = styles.getPropertyValue('--stl-ambient-light').trim() || '#888888';
const stlDirectionalLight = styles.getPropertyValue('--stl-directional-light').trim() || '#ffffff';
const stlMeshColor = styles.getPropertyValue('--stl-mesh-color').trim() || '#5580b3';
const stlEdgeColor = styles.getPropertyValue('--stl-edge-color').trim() || '#020617';
const stlAmbientIntensity = parseFloat(styles.getPropertyValue('--stl-ambient-intensity').trim()) || 0.5;
const stlDirectionalIntensity = parseFloat(styles.getPropertyValue('--stl-directional-intensity').trim()) || 1.0;

// Apply to scene
scene.background = new THREE.Color(stlBackground);
```

#### STL Preview Color Values by Theme

| Variable | Light Mode | Dark Mode | High Contrast |
|----------|------------|-----------|---------------|
| `--stl-mesh-color` | `#5580b3` (Steel Blue) | `#90cdf4` (Light Blue) | `#00ffff` (Bright Cyan) |
| `--stl-edge-color` | `#020617` (Slate 950) | `#1a202c` (Near Black) | `#000000` (Pure Black) |
| `--stl-background` | `#f1f5f9` (Light Gray) | `#2d3748` (Dark Gray) | `#000000` (Pure Black) |
| `--stl-ambient-light` | `#888888` | `#666666` | `#666666` |
| `--stl-directional-light` | `#ffffff` | `#ffffff` | `#e6e6e6` |
| `--stl-ambient-intensity` | `0.5` | `0.6` | `0.4` |
| `--stl-directional-intensity` | `1.0` | `0.9` | `0.8` |

#### Contrast Requirements (WCAG 2.2 SC 1.4.11 Non-text Contrast)

The mesh is a non-text graphical object and must reach 3:1 against the viewer
background. Edge overlay lines render 1px wide, so per W3C Low Vision Task Force
guidance for thin strokes they are held to the 4.5:1 text threshold against the
mesh colour they are drawn on.

| Theme | Mesh vs Background | Edge vs Mesh |
|-------|--------------------|--------------|
| Light | 3.7:1 | 4.9:1 |
| Dark | 7.0:1 | 9.5:1 |
| High Contrast | 16.7:1 | 16.7:1 |

The light theme's mesh colour was `#6699cc` until 2026-07, which measured 2.7:1
and failed SC 1.4.11.

### 3.3 High Contrast Mode Lighting

**CRITICAL FOR LOW VISION USERS:** High contrast mode uses a specialized three-point lighting setup to maximize detail visibility:

```javascript
if (currentTheme === 'high-contrast') {
    // KEY LIGHT: 45° horizontal, 30° vertical (right side) - camera-relative
    // Provides primary illumination and shadow definition
    directionalLight.position.set(0.707, 0.5, 0.612).normalize();
    camera.add(directionalLight);

    // FILL LIGHT: 45° horizontal, 15° vertical (left side)
    // Softens shadows without eliminating them
    const fillLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.4  // 40% of key light intensity
    );
    fillLight.position.set(-0.707, 0.259, 0.659).normalize();
    camera.add(fillLight);

    // BACK LIGHT: Subtle edge definition
    const backLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.2  // 20% of key light intensity
    );
    backLight.position.set(0, 0.5, -0.866).normalize();
    camera.add(backLight);
} else {
    // Standard two-point lighting for other themes
    directionalLight.position.set(0.707, 0.5, 0.612).normalize();
    camera.add(directionalLight);

    const fillLight = new THREE.DirectionalLight(
        new THREE.Color(stlDirectionalLight),
        stlDirectionalIntensity * 0.3
    );
    fillLight.position.set(-0.5, 0.259, 0.659).normalize();
    camera.add(fillLight);
}

// Ambient light for all themes
scene.add(new THREE.AmbientLight(
    new THREE.Color(stlAmbientLight),
    stlAmbientIntensity
));
```

#### Material Properties

`STL_MATERIAL_SETTINGS` in `public/index.html` is the single source for the
preview `MeshPhongMaterial` per theme. `loadSTL()`, `update3DSceneColors()`, and
`updatePreviewDisplaySettings()` all read from it, and `createStlMaterial()` is
the only place a preview material is constructed.

```javascript
const STL_MATERIAL_SETTINGS = {
    default: { specular: 0x111111, shininess: 30 },
    'high-contrast': { specular: 0x333333, shininess: 60 }
};

function createStlMaterial(theme, meshColor) {
    const settings = getStlMaterialSettings(theme);
    return new THREE.MeshPhongMaterial({
        color: new THREE.Color(meshColor),
        specular: settings.specular,
        shininess: settings.shininess,
        flatShading: true,          // Faceted, slicer-style STL display
        side: THREE.DoubleSide,
        polygonOffset: true,        // Keeps the edge overlay clear of z-fighting
        polygonOffsetFactor: 1,
        polygonOffsetUnits: 1
    });
}
```

These are matte to semi-matte, matching how slicers and mesh viewers
(PrusaSlicer, Cura, MeshLab, the three.js editor) present an STL. Until 2026-07
the values were shininess 200 (standard) / 300 (high contrast) with a white
specular, which threw broad highlights across the plate that swallowed the dot
geometry the preview exists to show. Form definition comes from the three-point
lighting above instead.

### 3.4 Camera and Controls

#### 3.4.1 CAMERA_SETTINGS Global Configuration

The application uses a centralized `CAMERA_SETTINGS` object to control the initial camera position for each shape type. This allows easy adjustment of the default viewing angle without modifying multiple code locations.

**Location in Code:** Search for `CAMERA_SETTINGS` in `public/index.html` (near line 2890)

```javascript
// ═══════════════════════════════════════════════════════════════════════════════
// CAMERA SETTINGS - Central configuration for STL preview camera positions
// ═══════════════════════════════════════════════════════════════════════════════
const CAMERA_SETTINGS = {
    // Card shape camera settings (standard flat plate)
    CARD: {
        position: { x: 0, y: 0, z: 120 },   // Camera on +Z axis, looking at origin
        up: { x: 0, y: 1, z: 0 },           // Y-axis is up
        target: { x: 0, y: 0, z: 0 },       // Look at origin
        fov: 45,                            // Field of view in degrees
        near: 0.1,                          // Near clipping plane
        far: 1000                           // Far clipping plane
    },
    // Cylinder shape camera settings (cylindrical surface)
    // Camera positioned to view the indicator shapes (triangle/rectangle) side
    CYLINDER: {
        position: { x: -120, y: 0, z: 0 },  // Camera on -X axis (views indicator side)
        up: { x: 0, y: 0, z: 1 },           // Z-axis is up (cylinder axis)
        target: { x: 0, y: 0, z: 0 },       // Look at origin
        fov: 45,                            // Field of view in degrees
        near: 0.1,                          // Near clipping plane
        far: 1000                           // Far clipping plane
    }
};
```

#### 3.4.2 Coordinate System Reference

| Shape Type | Up Axis | Camera Default Position | Notes |
|------------|---------|------------------------|-------|
| **Card** | Y-axis (0,1,0) | (0, 0, 120) on +Z axis | Camera looks straight at the flat plate |
| **Cylinder** | Z-axis (0,0,1) | (-120, 0, 0) on -X axis | Camera views indicator shapes side |

**Cylinder Coordinate System:**
- The cylinder's central axis runs along the **Z-axis**
- The cylinder is centered at the origin (0, 0, 0)
- Camera orbits around the Z-axis in the XY plane

#### 3.4.3 How to Adjust the Initial Camera View

**To rotate the cylinder's initial view around its vertical axis:**

1. Modify `CAMERA_SETTINGS.CYLINDER.position.x` and `.y` values
2. The camera distance from origin (120 by default) controls zoom level
3. Use these position patterns for common rotations:

| Desired View | Position Values | Description |
|--------------|-----------------|-------------|
| View from -X axis | `{ x: -120, y: 0, z: 0 }` | **Current default** - Views indicator shapes |
| View from +X axis | `{ x: 120, y: 0, z: 0 }` | Opposite side (braille dots facing camera) |
| View from +Y axis | `{ x: 0, y: 120, z: 0 }` | 90° clockwise rotation |
| View from -Y axis | `{ x: 0, y: -120, z: 0 }` | 90° counter-clockwise rotation |
| View from corner | `{ x: 85, y: 85, z: 0 }` | 45° angle (diagonal view) |

**To adjust zoom level:**
- Increase position values (e.g., 150) to zoom out
- Decrease position values (e.g., 80) to zoom in

**To rotate the card's initial view:**
- Modify `CAMERA_SETTINGS.CARD.position` values similarly
- Cards use Y-up orientation, so adjust X and Y for rotation

#### 3.4.4 Camera Implementation Details

```javascript
// Camera settings usage in init3D()
const defaultCam = CAMERA_SETTINGS.CARD;
camera = new THREE.PerspectiveCamera(defaultCam.fov, initW / initH, defaultCam.near, defaultCam.far);
camera.position.set(defaultCam.position.x, defaultCam.position.y, defaultCam.position.z);
camera.up.set(defaultCam.up.x, defaultCam.up.y, defaultCam.up.z);
camera.lookAt(defaultCam.target.x, defaultCam.target.y, defaultCam.target.z);

// When loading STL, camera is repositioned based on shape type
if (isCylinder) {
    const cylCam = CAMERA_SETTINGS.CYLINDER;
    camera.up.set(cylCam.up.x, cylCam.up.y, cylCam.up.z);
    camera.position.set(cylCam.position.x, cylCam.position.y, cylCam.position.z);
    // ... rest of cylinder setup
} else {
    const cardCam = CAMERA_SETTINGS.CARD;
    camera.position.set(cardCam.position.x, cardCam.position.y, cardCam.position.z);
    // ... rest of card setup
}
```

#### 3.4.5 OrbitControls Configuration

```javascript
// OrbitControls settings
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// For cylinders: panning orthogonal to world up (Z-up)
controls.screenSpacePanning = false;

// For cards: screen-space panning (Y-up)
controls.screenSpacePanning = true;
```

### 3.5 Mobile Optimizations

```javascript
const isMobile = window.innerWidth <= 768;

// Renderer optimizations
renderer = new THREE.WebGLRenderer({
    antialias: !isMobile,                           // No AA on mobile
    powerPreference: isMobile ? "low-power" : "high-performance"
});
renderer.setPixelRatio(Math.min(devicePixelRatio, isMobile ? 2 : 3));

// Control speed adjustments
controls.rotateSpeed = isMobile ? 0.5 : 1.0;
controls.zoomSpeed = isMobile ? 0.8 : 1.2;
controls.panSpeed = isMobile ? 0.5 : 0.8;
```

### 3.6 Dynamic Theme Updates

When the theme changes, the 3D scene is updated dynamically:

```javascript
function update3DSceneColors() {
    if (scene && renderer) {
        // Get new theme colors
        const styles = getComputedStyle(document.documentElement);
        // ... extract all color variables ...

        // Update scene background
        scene.background = new THREE.Color(stlBackground);

        // Remove existing lights
        const sceneLightsToRemove = scene.children.filter(child =>
            child instanceof THREE.DirectionalLight ||
            child instanceof THREE.AmbientLight
        );
        sceneLightsToRemove.forEach(light => scene.remove(light));

        const cameraLightsToRemove = camera.children.filter(child =>
            child instanceof THREE.DirectionalLight
        );
        cameraLightsToRemove.forEach(light => camera.remove(light));

        // Rebuild lighting based on new theme
        // ... (theme-specific lighting setup) ...

        // Update mesh material
        if (mesh && mesh.material) {
            mesh.material.color = new THREE.Color(stlMeshColor);
            mesh.material.needsUpdate = true;
        }

        // Force re-render
        renderer.render(scene, camera);
    }
}
```

### 3.7 STL Preview Label

A clarifying label is displayed as an **overlay at the top** of the STL preview panel to help users understand its purpose. This was added because some users were confused and attempted to type text into the preview area. The label is positioned as a top-layer overlay to ensure maximum visibility.

#### HTML Structure

```html
<!-- Viewer Container with Overlay Label -->
<div class="viewer-container">
    <!-- STL Preview Label - Positioned as overlay at top of viewer -->
    <div class="stl-preview-label" id="stl-preview-label" role="note" aria-label="STL Preview information">
        <strong>3D STL Preview</strong> — Interactive preview only (drag to rotate, scroll to zoom)
    </div>
    <div id="viewer" role="img" ...>
        <!-- 3D viewer content -->
    </div>
</div>
```

#### CSS Styling

```css
/* Viewer Container - wraps viewer and overlay label */
.viewer-container {
    position: relative;
    width: 100%;
}

/* STL Preview Label - Overlay at top of viewer */
.stl-preview-label {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 10;
    text-align: center;
    padding: 0.5em 0.75em;
    font-size: 0.85em;
    color: var(--text-secondary);
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px 8px 0 0;
    opacity: 0.95;
}

.stl-preview-label strong {
    color: var(--text-primary);
}

/* High contrast mode */
[data-theme="high-contrast"] .stl-preview-label {
    background: #1a1a1a;
    border: 2px solid #ffff00;
    color: #02fe05;
    opacity: 1;
}

[data-theme="high-contrast"] .stl-preview-label strong {
    color: #fdfe00;
}
```

#### Purpose

The label serves to:
- Clearly identify the panel as an STL preview (not a text input)
- Provide brief interaction instructions (drag to rotate, scroll to zoom)
- Reduce user confusion about the panel's purpose
- **Positioned at top as overlay** to maximize visibility without taking extra space below the viewer

### 3.8 Preview Display Settings (Brightness, Contrast, and Edge Outlines)

User-adjustable brightness, contrast, and edge-outline controls allow customization of how the 3D preview appears. These settings affect **only the visual preview** and do not modify the exported STL file.

**UI Pattern:** Non-cycling **stepper controls** (`−` / `+`) with live value displays for brightness and contrast, plus a single **toggle button** for edge outlines. All three reuse the font-size control styling for consistent keyboard and screen reader behavior; the steppers disable at bounds (levels 1 and 5).

#### Control Overview

| Setting | Purpose | Range | Default | Step Behavior |
|---------|---------|-------|---------|---------------|
| **Brightness** | Adjusts overall light intensity | 1-5 | 3 (Normal) | Non-cycling; +/- buttons disable at min/max |
| **Contrast** | Adjusts ambient vs directional light ratio | 1-5 | 3 (Normal) | Non-cycling; +/- buttons disable at min/max |
| **Edges** | Draws feature-edge outlines over the shaded surface | On/Off | On | `aria-pressed` toggle button |

#### Brightness Levels

Recalibrated 2026-02-02: stakeholder feedback said the old "Very Bright" (1.4×) read as visually normal, so 1.4× became level 3 and the range extended around it.

| Level | Name | Multiplier | Description |
|-------|------|------------|-------------|
| 1 | Very Dim | 0.7× | Significantly reduced lighting |
| 2 | Dim | 1.0× | Old Normal baseline |
| 3 | Normal | 1.4× | **Default** - Recalibrated from old Very Bright |
| 4 | Bright | 1.9× | Extended range |
| 5 | Very Bright | 2.5× | Maximum for high visibility needs |

#### Contrast Levels

Shininess offsets are added to the per-theme `STL_MATERIAL_SETTINGS.shininess` base (30 standard, 60 high contrast). They were rescaled in 2026-07 alongside the matte material: the previous `-40 … +220` range was written for a base of 200 and pushed even level 3 into mirror territory. There is deliberately **no floor** on the resulting shininess, which would defeat the low base.

| Level | Name | Ambient Ratio | Directional Ratio | Specular Intensity | Shininess Offset | Effect |
|-------|------|---------------|-------------------|--------------------|------------------|--------|
| 1 | Very Low | 1.0× | 1.0× | 0.6× | −15 | Flat, even lighting |
| 2 | Low | 0.8× | 1.2× | 1.0× | −5 | Soft shadows |
| 3 | Normal | 0.6× | 1.4× | 1.6× | +10 | **Default** - Balanced lighting |
| 4 | High | 0.4× | 1.7× | 2.2× | +30 | More defined shadows |
| 5 | Very High | 0.25× | 2.0× | 2.8× | +60 | Dramatic lighting with strong shadows |

#### HTML Structure (Stepper)

```html
<!-- Preview Display Controls - Brightness and Contrast as +/- steppers -->
<div class="preview-display-controls" role="group" aria-label="Preview display settings">
    <div class="preview-control-group">
        <span class="preview-control-label" id="brightness-label">Brightness:</span>
        <div class="preview-stepper" role="group" aria-labelledby="brightness-label brightness-value">
            <button type="button" id="brightness-decrease" class="font-size-btn preview-stepper-btn"
                    aria-label="Decrease brightness" aria-controls="brightness-value">
                <span aria-hidden="true">−</span>
            </button>
            <span class="font-size-display preview-stepper-value" id="brightness-value" role="status" aria-live="polite">Normal</span>
            <button type="button" id="brightness-increase" class="font-size-btn preview-stepper-btn"
                    aria-label="Increase brightness" aria-controls="brightness-value">
                <span aria-hidden="true">+</span>
            </button>
        </div>
    </div>

    <div class="preview-control-group">
        <span class="preview-control-label" id="contrast-label">Contrast:</span>
        <div class="preview-stepper" role="group" aria-labelledby="contrast-label contrast-value">
            <button type="button" id="contrast-decrease" class="font-size-btn preview-stepper-btn"
                    aria-label="Decrease contrast" aria-controls="contrast-value">
                <span aria-hidden="true">−</span>
            </button>
            <span class="font-size-display preview-stepper-value" id="contrast-value" role="status" aria-live="polite">Normal</span>
            <button type="button" id="contrast-increase" class="font-size-btn preview-stepper-btn"
                    aria-label="Increase contrast" aria-controls="contrast-value">
                <span aria-hidden="true">+</span>
            </button>
        </div>
    </div>

    <div class="preview-control-group">
        <button type="button" id="edges-toggle" class="font-size-btn preview-toggle-btn active"
                aria-pressed="true" aria-controls="viewer"
                title="Outline the model edges for a higher-contrast view">
            Edges
        </button>
    </div>
</div>
```

#### JavaScript Implementation

```javascript
let previewBrightnessLevel = 3;
let previewContrastLevel = 3;

const BRIGHTNESS_MULTIPLIERS = { 1: 0.7, 2: 1.0, 3: 1.4, 4: 1.9, 5: 2.5 };
const CONTRAST_SETTINGS = {
    1: { ambientRatio: 1.0,  directionalRatio: 1.0, specularIntensity: 0.6, shininessOffset: -15 },
    2: { ambientRatio: 0.8,  directionalRatio: 1.2, specularIntensity: 1.0, shininessOffset: -5 },
    3: { ambientRatio: 0.6,  directionalRatio: 1.4, specularIntensity: 1.6, shininessOffset: 10 },
    4: { ambientRatio: 0.4,  directionalRatio: 1.7, specularIntensity: 2.2, shininessOffset: 30 },
    5: { ambientRatio: 0.25, directionalRatio: 2.0, specularIntensity: 2.8, shininessOffset: 60 }
};

const brightnessLevelNames = { 1: 'Very Dim', 2: 'Dim', 3: 'Normal', 4: 'Bright', 5: 'Very Bright' };
const contrastLevelNames   = { 1: 'Very Low', 2: 'Low', 3: 'Normal', 4: 'High', 5: 'Very High' };

const clampPreviewLevel = level => Math.min(5, Math.max(1, parseInt(level, 10) || 3));

function updatePreviewDisplaySettings() {
    // Applies brightness/contrast multipliers to lights and mesh material.
    // See implementation in templates/public index scripts for full logic.
}

function updateBrightnessStepper() {
    const name = brightnessLevelNames[previewBrightnessLevel];
    const percent = Math.round((BRIGHTNESS_MULTIPLIERS[previewBrightnessLevel] || 1) * 100);
    const value = document.getElementById('brightness-value');
    value.textContent = `${name}`;
    value.setAttribute('title', `${percent}% of base lighting`);

    const dec = document.getElementById('brightness-decrease');
    const inc = document.getElementById('brightness-increase');
    dec.disabled = previewBrightnessLevel <= 1;
    inc.disabled = previewBrightnessLevel >= 5;
    dec.setAttribute('aria-label', `Decrease brightness (current ${name})`);
    inc.setAttribute('aria-label', `Increase brightness (current ${name})`);
}

function applyPreviewBrightness(level) {
    previewBrightnessLevel = clampPreviewLevel(level);
    updatePreviewDisplaySettings();
    updateBrightnessStepper();
}

function updateContrastStepper() {
    const name = contrastLevelNames[previewContrastLevel];
    const ratios = CONTRAST_SETTINGS[previewContrastLevel];
    const value = document.getElementById('contrast-value');
    value.textContent = name;
    value.setAttribute('title', `${ratios.ambientRatio}× ambient / ${ratios.directionalRatio}× directional`);

    const dec = document.getElementById('contrast-decrease');
    const inc = document.getElementById('contrast-increase');
    dec.disabled = previewContrastLevel <= 1;
    inc.disabled = previewContrastLevel >= 5;
    dec.setAttribute('aria-label', `Decrease contrast (current ${name})`);
    inc.setAttribute('aria-label', `Increase contrast (current ${name})`);
}

function applyPreviewContrast(level) {
    previewContrastLevel = clampPreviewLevel(level);
    updatePreviewDisplaySettings();
    updateContrastStepper();
}

document.getElementById('brightness-decrease').addEventListener('click', () => {
    if (previewBrightnessLevel > 1) applyPreviewBrightness(previewBrightnessLevel - 1);
});
document.getElementById('brightness-increase').addEventListener('click', () => {
    if (previewBrightnessLevel < 5) applyPreviewBrightness(previewBrightnessLevel + 1);
});
document.getElementById('contrast-decrease').addEventListener('click', () => {
    if (previewContrastLevel > 1) applyPreviewContrast(previewContrastLevel - 1);
});
document.getElementById('contrast-increase').addEventListener('click', () => {
    if (previewContrastLevel < 5) applyPreviewContrast(previewContrastLevel + 1);
});

updateBrightnessStepper();
updateContrastStepper();
```

#### CSS Styling

```css
/* Preview Display Controls Container - Stepper style */
.preview-display-controls {
    width: 100%;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 1em;
    padding: 0.75em;
    margin-top: 0.5em;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    flex-wrap: wrap;
}

.preview-control-group {
    display: flex;
    align-items: center;
    gap: 0.75em;
    flex-wrap: wrap;
}

.preview-control-label {
    font-size: 0.85em;
    font-weight: 500;
    color: var(--text-primary);
}

.preview-controls-title {
    font-weight: 600;
    font-size: 0.9em;
    color: var(--text-primary);
    white-space: nowrap;
}

.preview-stepper {
    display: flex;
    align-items: center;
    gap: 0.4em;
    flex-wrap: wrap;
}

.preview-stepper .font-size-btn {
    min-width: 2.5em;
    padding: 0.4em 0.65em;
}

.preview-stepper-value {
    min-width: 9.5em;
    text-align: center;
}

/* Stepper buttons: 44x44 floor (WCAG 2.5.5), raised 2026-08-21 from 1.6em */
.preview-stepper-btn {
    min-width: 44px !important;
    min-height: 44px !important;
    padding: 0.2em 0.35em !important;
}

/* Edge outline toggle - same stepper metrics, but wide enough for a word */
.preview-toggle-btn {
    min-width: max(4em, 44px) !important;
    min-height: 44px !important;
    padding: 0.2em 0.6em !important;
}

/* Same WCAG-AA active blues the Expert Mode toggles use */
.preview-toggle-btn.active {
    background: #1e4976;
    color: #fff;
    border-color: #1e4976;
}

[data-theme="dark"] .preview-toggle-btn.active {
    background: #1e5a8a;
    border-color: #1e5a8a;
}

/* Cyan rather than the yellow the shared .font-size-btn hover already uses, so
   pressed and hovered are never the same swatch */
[data-theme="high-contrast"] .preview-toggle-btn.active,
[data-theme="high-contrast"] .preview-toggle-btn.active:hover {
    background: #00ffff !important;
    color: #000000 !important;
    border: 2px solid #00ffff !important;
}

[data-theme="high-contrast"] .preview-controls-title,
[data-theme="high-contrast"] .preview-control-label {
    color: #02fe05 !important;
}

@media (max-width: 768px) {
    .preview-display-controls {
        padding: 0.5em;
        flex-direction: column;
        align-items: flex-start;
    }

    .preview-control-group {
        width: 100%;
        flex-wrap: wrap;
    }

    .preview-stepper {
        width: 100%;
    }

    .preview-stepper .font-size-btn {
        flex: 1;
        min-width: unset;
    }

    .preview-stepper-value {
        flex: 1 1 auto;
    }
}
```

#### Edge Outlines (Feature-Edge Overlay)

WCAG technique G174 endorses offering a user control that switches to a
higher-contrast presentation. Edge rendering is how slicers and CAD viewers
expose structure independently of lighting, so the **Edges** toggle draws the
model's feature edges as lines over the shaded surface.

A full triangle wireframe (`wireframe: true`) is deliberately **not** offered: a
braille plate runs to tens of thousands of facets and reads as noise.
`THREE.EdgesGeometry` with a threshold angle of 22° keeps dot silhouettes and
plate corners while dropping the tessellation seams of the curved surface.

The overlay is **on by default**, because the outlines are what make the dot and
marker shapes legible without relying on the shading. The static markup carries
`aria-pressed="true"` and the `active` class so the button is styled pressed
before any script runs.

```javascript
const STL_EDGE_THRESHOLD_ANGLE = 22;

let edgesOverlay = null;
let edgesVisible = true;

// EdgesGeometry walks every triangle, so this is skipped entirely while the
// overlay is switched off rather than built and hidden.
function refreshEdgesOverlay() {
    disposeEdgesOverlay();
    if (!edgesVisible || !mesh || !mesh.geometry) return;

    const edgeColor = getStlThemeColor('--stl-edge-color', '#020617');
    edgesOverlay = new THREE.LineSegments(
        new THREE.EdgesGeometry(mesh.geometry, STL_EDGE_THRESHOLD_ANGLE),
        new THREE.LineBasicMaterial({ color: new THREE.Color(edgeColor) })
    );
    // Parented to the mesh so it inherits every camera-fitting transform
    mesh.add(edgesOverlay);
}

function applyEdgesVisibility(visible) {
    edgesVisible = Boolean(visible);
    refreshEdgesOverlay();
    updateEdgesToggle();   // aria-pressed + .active class
    render();
}
```

Lifecycle wiring in `public/index.html`:

| Event | Handling |
|-------|----------|
| STL loaded (`loadSTL`) | `refreshEdgesOverlay()` after the mesh is added — rebuilds against the new geometry, or disposes and stops if the toggle is off |
| Theme change (`update3DSceneColors`) | Recolours the existing overlay material from `--stl-edge-color` |
| WebGL context restore | The reload path recreates the mesh with `createStlMaterial()` and calls `refreshEdgesOverlay()` |
| Toggle click | `applyEdgesVisibility(!edgesVisible)` |

Z-fighting between the lines and the facets they trace is prevented by
`polygonOffset` on the mesh material (see `createStlMaterial()` above), not by
nudging the overlay's position.

#### Integration with Theme System

The brightness and contrast settings work in conjunction with the theme system:

1. **Base Values from Theme**: Each theme provides base ambient and directional light intensities via CSS variables
2. **User Adjustments Applied**: Brightness/contrast multipliers are applied on top of theme values
3. **Theme Changes Preserve Settings**: When the theme changes, current brightness/contrast settings are reapplied

```javascript
// In update3DSceneColors():
// After rebuilding lights for new theme...
if (typeof storeOriginalLightIntensities === 'function') {
    storeOriginalLightIntensities();
}
if (typeof updatePreviewDisplaySettings === 'function') {
    updatePreviewDisplaySettings();
}
```

#### Accessibility Features

- **ARIA Labels**: Dynamic labels on +/- buttons reflect current level and action (e.g., "Decrease brightness (current Normal)")
- **Live Value Announcements**: Value displays use `role="status"` + `aria-live="polite"` to announce changes without duplicate overlays
- **Toggle State**: The Edges button follows the ARIA toggle-button pattern — a static accessible name ("Edges") with `aria-pressed` carrying the state, so no extra live region is needed
- **Keyboard Navigation**: Native buttons with disabled states at bounds; Enter/Space activates, Shift+Tab/Tab respects grouping
- **Focus Indicators**: Clear 3px focus outlines with offset for visibility
- **High Contrast Mode**: Labels inherit high-contrast colors; buttons reuse font-size control styling that already meets WCAG AA
- **Active State Colors**: The pressed Edges button uses the same WCAG-AA blues as the Expert Mode toggles (`#1e4976` light, `#1e5a8a` dark, both white-on-blue above 7:1). In high contrast it fills with cyan and black text at 16.7:1 — deliberately *not* the yellow that `.font-size-btn:hover` already uses, so pressed and hovered are never the same swatch. Pressed is a solid fill against an outlined unpressed state, so the distinction survives without colour

#### Non-Persistence Policy

Brightness, contrast, and edge-outline settings are **not persisted** across sessions. This is consistent with the theme and font size policies:
- Settings reset to defaults on page load (brightness and contrast to level 3, edge outlines to on)
- Provides consistent starting experience for all users
- Users with specific needs can quickly adjust as needed

### 3.9 WebGL Context Recovery

The application implements resilient WebGL context loss and recovery handling for stability, especially on Safari/iOS where context loss may occur when tabs are backgrounded or when the system is under memory pressure.

#### Feature Detection

Before initializing the 3D viewer, the application checks for WebGL support:

```javascript
function checkWebGLSupport() {
    try {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        return !!context;
    } catch (e) {
        return false;
    }
}
```

If WebGL is not available, a user-friendly error message is displayed:

```html
<div class="webgl-error" role="alert">
    <strong>WebGL Not Available</strong>
    <p>Your browser does not support WebGL, which is required for the 3D preview.
    You can still generate and download STL files.</p>
    <p>Try updating your browser or enabling hardware acceleration in your browser settings.</p>
</div>
```

#### Context Loss Handling

Event listeners are attached to the WebGL canvas to handle context loss and recovery:

```javascript
renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault(); // Allow recovery
    console.warn('WebGL context lost');

    // Show user-friendly message
    const msg = document.createElement('div');
    msg.id = 'webgl-recovery-msg';
    msg.className = 'webgl-recovery';
    msg.setAttribute('role', 'alert');
    msg.innerHTML = `
        <strong>3D Preview Paused</strong>
        <p>The 3D viewer was interrupted. It will automatically recover.</p>
    `;
    viewer.appendChild(msg);
}, false);

renderer.domElement.addEventListener('webglcontextrestored', () => {
    console.log('WebGL context restored');

    // Remove recovery message
    const msg = document.getElementById('webgl-recovery-msg');
    if (msg) msg.remove();

    // Re-initialize scene
    reinitialize3DScene();

    // Reload last STL if available
    if (lastGeneratedSTLUrl) {
        // Reload the STL mesh
    }
}, false);
```

#### Recovery CSS

```css
.webgl-error,
.webgl-recovery {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--bg-secondary);
    border: 2px solid var(--border-primary);
    border-radius: 8px;
    padding: 1.5em;
    text-align: center;
    max-width: 80%;
    z-index: 20;
}

[data-theme="high-contrast"] .webgl-error,
[data-theme="high-contrast"] .webgl-recovery {
    background: #1a1a1a;
    border-color: #ffff00;
    color: #02fe05;
}
```

#### Browser Compatibility

| Browser | Context Loss Behavior | Recovery Support |
|---------|----------------------|------------------|
| Chrome | Rare (GPU reset) | ✅ Automatic |
| Firefox | Rare | ✅ Automatic |
| Safari Desktop | Occasional (tab backgrounding) | ✅ Automatic |
| Safari iOS | Common (M3/M4 chips, memory pressure) | ✅ Automatic |
| Edge | Rare (GPU reset) | ✅ Automatic |

---

## 4. Accessibility Features

### 4.1 Skip Link Navigation

A skip link is provided for keyboard users to bypass the header and jump directly to the main content:

```html
<a href="#main-content" class="skip-link" tabindex="0">Skip to main content</a>
```

```css
.skip-link {
    position: absolute;
    top: 0;
    left: 0;
    transform: translateY(-100%);  /* Hidden by its OWN height */
    background: var(--border-focus);
    color: var(--skip-link-text);
    padding: 8px 16px;
    text-decoration: none;
    border-radius: 0 0 8px 0;
    z-index: 1000;
    transition: transform 0.3s;
}

.skip-link:focus {
    transform: translateY(0);  /* Becomes visible when focused */
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

**Why the label is `var(--skip-link-text)` and not `white` (fixed 2026-08-21).**
White on `--border-focus` failed WCAG 2.1 SC 1.4.3 (AA) in **all three themes** -
4.03:1 light, 2.28:1 dark, 3.14:1 high contrast, against a 4.5:1 floor.

The obvious repair, darkening `--border-focus` itself, was measured and **rejected**.
That token is also the page-wide focus-ring colour, and the two jobs pull apart: a
blue dark enough to carry white text at 4.5:1 (`#2c5282`, 7.97:1) measures **1.51:1
against the dark theme's page** and 2.47:1 against high-contrast black, dropping every
focus ring on the page below the 3:1 non-text floor of WCAG 2.2 SC 1.4.11. Fixing one
AA failure would have created dozens.

The label moves instead. `#000000` clears 4.5:1 on all three focus colours -
**5.21:1 / 9.20:1 / 6.70:1** - so it needs no per-theme value, and the background,
the focus ring, and every other consumer of `--border-focus` are untouched. Chosen by
Brennen 2026-08-21 (FD-19c) over a decoupled `--skip-link-bg` token, which would have
kept white-on-blue but left the box itself at 2.18:1 / 2.47:1 against the page in the
dark and high-contrast themes, relying on the focus outline alone for its boundary.

**Why `translateY(-100%)` and not a pixel offset (fixed 2026-08-21).** The rule was
`top: -40px`, a fixed lift that cannot hide an element whose height scales with the
app font size. Measured on the real UI, driving `applyFontSize()`'s own scale:

| App font size | Link height | Showing on screen, unfocused (was) | (now) |
|---|---|---|---|
| 100% | 37 px | 0 px | 0 px |
| 125% | 43 px | 3 px | 0 px |
| 150% | 48 px | 8 px | 0 px |
| 175% | 53 px | 13 px | 0 px |
| 200% | 59 px | **19 px** | **0 px** |

`translateY(-100%)` is always exactly one link-height, whatever that height turns out
to be, so the leak closes at every step of the scale. Focusing it still brings it
fully on screen at `y = 0`. The transition moved from `top` to `transform` with it;
`prefers-reduced-motion` still neutralises it through the global
`transition-duration: 0.01ms` override.

> **Correction to the original finding.** The 2026-08-18 audit recorded this as a
> **102 px** link leaving **~62 px** on screen at 200%. Those numbers came from a
> measurement that scaled `<html>` *and* `<body>` together, which compounds;
> `applyFontSize()` sets the root only. The defect was real and is fixed, but its
> true size was 59 px and 19 px. Recorded so the smaller number is not mistaken for
> an incomplete fix.

### 4.2 Focus Indicators

All interactive elements have enhanced focus indicators for keyboard navigation:

```css
/* Standard focus indicator */
button:focus,
input:focus,
select:focus,
textarea:focus,
a:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}

/* Keyboard-specific focus (more visible) */
*:focus-visible {
    outline: 3px solid var(--border-focus) !important;
    outline-offset: 2px !important;
}
```

### 4.3 Screen Reader Support

**ARIA Labels and Descriptions:**
```html
<!-- Font size controls with grouping -->
<div class="font-size-controls" role="group" aria-label="Font size controls">
    <button aria-label="Decrease font size">A-</button>
    <span aria-live="polite">100</span>
    <button aria-label="Increase font size">A+</button>
    <button aria-label="Reset font size to default">Reset</button>
</div>

<!-- Theme toggle with dynamic ARIA label -->
<button id="theme-toggle"
        aria-label="Current theme: Dark. Click to switch to High Contrast theme">
    ...
</button>

<!-- Line inputs with descriptions -->
<input type="text" id="line1"
       aria-describedby="line1-help">
<span id="line1-help" class="sr-only">Maximum 50 characters for line 1</span>
```

### 4.4 Touch and Mobile Accessibility

```css
/* Minimum touch target size (48px) */
@media (max-width: 768px) {
    button {
        min-height: 48px;
        min-width: 48px;
    }

    input[type="text"],
    input[type="number"] {
        min-height: 48px;
        font-size: 16px;  /* Prevents iOS zoom on focus */
    }
}

/* Disable double-tap zoom on buttons */
button {
    touch-action: manipulation;
}

/* Prevent text selection on UI elements */
button {
    -webkit-touch-callout: none;
    -webkit-user-select: none;
    user-select: none;
}
```

### 4.5 Toggle Button ARIA Requirements

All toggle buttons (Info dropdown, Expert Mode toggle, and submenu toggles) implement proper ARIA attributes to communicate their state to screen readers.

#### Required ARIA Attributes

```html
<!-- Info Toggle -->
<button type="button" id="info-toggle" class="info-toggle-btn"
        aria-expanded="false" aria-controls="info-content">
    <span id="info-toggle-text">Directions:</span>
    <span id="info-toggle-icon" aria-hidden="true">▼</span>
</button>
<div id="info-content" class="info-content" style="display: none;">
    <!-- Content -->
</div>

<!-- Expert Mode Toggle -->
<button type="button" id="expert-toggle" class="expert-toggle-btn"
        aria-expanded="false" aria-controls="expert-settings">
    <span id="expert-toggle-text">Show Expert Mode</span>
    <span id="expert-toggle-icon" aria-hidden="true">▼</span>
</button>
<div id="expert-settings" class="expert-settings" style="display: none;">
    <!-- Content -->
</div>
```

#### Key ARIA Requirements

| Attribute | Purpose | Values |
|-----------|---------|--------|
| `aria-expanded` | Indicates whether controlled element is expanded | `"true"` or `"false"` |
| `aria-controls` | Links button to the element it controls | ID of controlled element |
| `aria-hidden="true"` | Hides decorative icons from screen readers | Applied to icon spans |

#### JavaScript State Management

Toggle buttons must update `aria-expanded` dynamically when clicked:

```javascript
expertToggleBtn.addEventListener('click', () => {
    const isVisible = expertSettings.style.display !== 'none';
    expertSettings.style.display = isVisible ? 'none' : 'block';
    expertToggleText.textContent = isVisible ? 'Show Expert Mode' : 'Hide Expert Mode';
    expertToggleIcon.textContent = isVisible ? '▼' : '▲';
    expertToggleBtn.classList.toggle('active', !isVisible);

    // REQUIRED: Update ARIA state
    expertToggleBtn.setAttribute('aria-expanded', String(!isVisible));

    // Optional: Focus management when opening
    if (!isVisible) {
        const firstFocusable = expertSettings.querySelector(
            'input, select, button, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
});
```

#### Screen Reader Announcements

When `aria-expanded` changes, screen readers automatically announce the new state:
- "expanded" when `aria-expanded="true"`
- "collapsed" when `aria-expanded="false"`

#### Expert Mode Submenus

All six submenus use the identical `.expert-submenu-toggle` markup and are wired by one
handler (`initExpertSubmenus()`), which sets `aria-expanded`, toggles `.active`, flips the
`▼`/`▲` icon, and moves focus into the panel on open. A new submenu needs only the markup:

| Order | Submenu | `aria-controls` | Notes |
|-------|---------|-----------------|-------|
| 1 | Shape Selection | `expert-panel-shapes` | |
| 2 | Braille Spacing | `expert-panel-spacing` | |
| 3 | Braille Dot Adjustments | `expert-panel-dots` | |
| 4 | Surface Dimensions | `expert-panel-dimensions` | |
| 5 | Tactile Indicator Dimensions | `expert-panel-tactile` | Whole accordion hidden unless Row Indicator Style is *Tactile seam arrow* |
| 6 | Translation Options | `expert-panel-translation` | Capitalized Letters and Number Signs |

The chevron is decorative and **must** be marked
`<span class="expert-submenu-icon" aria-hidden="true">`. Without it the glyph is folded
into the button's own accessible name and read aloud — NVDA said "Shape Selection▼ button
collapsed" (audit finding F-B). `aria-expanded` already conveys open/closed state, so the
icon carries no information a screen reader needs. The handler flips the glyph with
`icon.textContent = …`, which replaces only the text node, so `aria-hidden` survives every
open and close — verified live, ▼ → ▲ → ▼ with the attribute intact throughout. This
matches `#expert-toggle-icon` and `#info-toggle-icon`, which were already marked this way.

Active toggles use `#1e4976` (light, 6.1:1 with white) and `#1e5a8a` (dark, 4.7:1), not
`--border-focus`, which is only 3.7:1 and fails WCAG AA for the button label.

### 4.6 Reduced Motion Support

The application respects the user's operating system preference for reduced motion (`prefers-reduced-motion` media query) in compliance with WCAG 2.1 Success Criterion 2.3.3.

#### CSS Implementation

All animations and transitions are disabled when reduced motion is preferred:

```css
/* Reduced Motion Support - WCAG 2.1 Requirement */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }

    /* Specifically disable theme transition animations */
    body,
    .container,
    button,
    input,
    select,
    .preview-section,
    .form-section {
        transition: none !important;
    }
}
```

#### JavaScript Implementation

The 3D preview animation loop also respects reduced motion preferences:

```javascript
// Check reduced motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let animationEnabled = !prefersReducedMotion.matches;

function animate() {
    if (animationEnabled) {
        requestAnimationFrame(animate);
    }
    controls && controls.update();
    render();
}

function updateRenderingMode() {
    animationEnabled = !prefersReducedMotion.matches;
    if (!animationEnabled && controls) {
        // Stop continuous animation loop, render on demand only
        controls.addEventListener('change', () => {
            render();
        });
    } else if (animationEnabled) {
        // Resume continuous animation
        animate();
    }
}

prefersReducedMotion.addEventListener('change', updateRenderingMode);
updateRenderingMode();
```

#### Affected Elements

| Element Type | Normal Behavior | Reduced Motion Behavior |
|--------------|----------------|-------------------------|
| Theme transitions | 0.3s fade | Instant |
| Button hover effects | Animated | Instant |
| 3D preview rotation | Continuous animation loop | Render on user interaction only |
| Scroll behavior | Smooth scrolling | Instant jump |

#### How to Test

**On Windows:**
1. Open Settings → Accessibility → Visual effects
2. Toggle "Animation effects" off

**On macOS:**
1. System Settings → Accessibility → Display
2. Toggle "Reduce motion" on

**On iOS:**
1. Settings → Accessibility → Motion
2. Toggle "Reduce Motion" on

### 4.7 Two-Way Translation Controls

The text entry area and the Braille (Unicode) box translate in both directions, with one
button under each:

| Button | Direction | Effect |
|--------|-----------|--------|
| `#translate-to-braille-btn` — "Translate to Braille ↓" | text → braille | Runs the same pipeline generation uses (capitalization, liblouis, BANA wrapping in auto mode) and writes one row per line into `#braille-unicode` |
| `#translate-to-text-btn` — "Translate to Text ↑" | braille → text | Back-translates each braille line through the worker's `backTranslate` message and writes the result into the Auto Placement box (auto mode) or `line1`…`lineN` (manual mode) |

Both buttons sit directly under the box they read from, so the arrow in the label matches
the direction the content moves on screen. Neither button changes the contract: whenever
`#braille-unicode` holds content, those exact cells are what get embossed, and
"Translate to Text" deliberately leaves the braille untouched.

Accessibility requirements:

- Both are `<button type="button" class="btn-translate">`, and **neither carries
  `aria-describedby`**. The 72-word `#braille-unicode-help` paragraph was previously wired
  to both buttons as well as the textarea, so a screen reader spoke it in full on every
  button focus — measured at 59 exposures and 30.9% of all speech in a 34-minute NVDA
  session (audit finding F-C). The paragraph itself is unchanged and still sits visibly
  directly under the field, where a browse-mode user reads it on demand; only the forced
  repetition is gone. The textarea keeps
  `aria-describedby="braille-unicode-help braille-unicode-status"` — it is the one control
  the paragraph is really about ("one description, one host").
- Progress and outcome are announced through the existing `#braille-unicode-live`
  (`role="status" aria-live="polite"`) region, and shown visually in
  `#braille-unicode-status`. Errors set the highlighted variant of the status text rather
  than a colour-only cue.
- Each button disables itself and shows "Translating…" while the worker runs, then restores
  its label in a `finally` block so a worker failure can never leave it stuck.

### 4.8 Double-Sided Card Beta: Disclosure Checkbox and Locked Radio Option

The Double-Sided Card beta toggle (`#double_sided_enabled`) introduces two patterns:

**Disclosure checkbox.** The toggle is a real `<input type="checkbox">` (not a button):
checking it changes what generation produces, so its on/off state is the semantic, and it
additionally discloses the Back of Card section. It carries `aria-expanded` (mirrored to
the checkbox state by `updateDoubleSidedUI()`) and `aria-controls="double-sided-section"`;
ARIA 1.2 permits `aria-expanded` on the checkbox role and the W3C Nu validator accepts it.
The wrapping label uses `.ds-toggle-option` for an explicit 44 px minimum hit target. While
on, the front entry legend `#front-entry-legend` is relabeled "Front of Card — …" and
restored verbatim when off, so the toggle-off page is exactly today's page.

**Locked radio option.** While the beta is on, the Row Indicator Style is forced to
"Tactile seam arrow" (the backend hard-rejects double-sided requests with any other style).
The "Visual markers" radio gets the native `disabled` attribute — announced by screen
readers, skipped by arrow-key navigation, and exempt from contrast minimums (WCAG SC 1.4.3)
— while staying visible, dimmed via `opacity` so every theme keeps its own token colors. A
visible explanation (`#indicator-mode-lock-note`, `role="status"` `aria-live="polite"`) appears
next to the group, and `updateDoubleSidedUI()` appends its id to the disabled radio's
`aria-describedby` so the reason travels with the option; both are removed when the beta
turns off. Native `disabled` was chosen over `aria-disabled` because the repository's
existing convention for unavailable controls is the native attribute, and it needs no
keyboard interception to keep the lock honest.

### 4.9 Button Contrast Tokens and the 44 px Action Button

The full [ADA Accessibility Validation SOP](../development/ADA_ACCESSIBILITY_VALIDATION_SOP.md)
was executed against the double-sided beta flow on 2026-08-17. Two failures were
found, both pre-existing and both app-wide rather than beta-specific.

**Why the tooling did not catch the contrast failure.** Lighthouse scored 100/100
and axe-core passed the primary buttons, because `--btn-primary-bg` was a gradient
and a `background-image` defeats both tools' colour sampling — they skip the element
instead of failing it. Measured directly, white text on the old tokens ran 4.03:1 at
the gradient's dark stop down to **2.28:1** at its light stop, and 2.54:1 on
`--btn-success-bg`. **Any future button token must be measured directly, at every
gradient stop, not trusted to an automated score.**

**Why the dark theme needs a border.** The two rules pull in opposite directions
there. A fill dark enough to carry a white label at 4.5:1 (WCAG 1.4.3) falls under
3:1 against the `#374151` surface behind it (WCAG 1.4.11), so the button block stops
being identifiable as a control. The dark theme therefore uses a solid dark fill for
the label ratio and a light border for the boundary ratio. The light theme needs no
such split — its fill clears both — so its border tokens simply equal its fill and
never paint. The high contrast theme was already compliant and is untouched; its
per-button `!important` border rules override the tokens entirely.

Measured after the change, all three themes:

| Control | Theme | Label vs fill (need 4.5:1) | Boundary vs surface (need 3:1) |
|---|---|---|---|
| `#action-btn`, `#generate-both-btn` | light | 5.50:1 | 6.54:1 (fill) |
| `.pair-downloads button` | light | 5.31:1 | 5.08:1 (fill) |
| `#action-btn`, `#generate-both-btn` | dark | 5.50:1 | 6.00:1 (border) |
| `.pair-downloads button` | dark | 6.50:1 | 6.76:1 (border) |
| `#action-btn`, `#generate-both-btn` | high contrast | 7.94:1 | 16.04:1 (border) |
| `.pair-downloads button` | high contrast | 15.18:1 | 12.58:1 (fill) |

Because `box-sizing: border-box` is global, the added 2 px border does not grow any
button; it was verified not to clip any label (`scrollWidth`/`scrollHeight` equal
`clientWidth`/`clientHeight` on every button in every theme).

**Touch target.** `#action-btn` rendered 34 px tall at desktop widths against the
44 × 44 px floor — the `max-width: 768px` block already forced 48 px, so only desktop
was short. It now carries an explicit `min-height: 44px`. Nothing shrank.

**Reflow and the remaining small targets (fixed 2026-08-18).** Three further
failures were found on 2026-08-17 and fixed the next day:

- **Reflow (WCAG 1.4.10).** At a 320 CSS px viewport **combined with** the app's own
  font control at 200%, the page scrolled horizontally by 127 px. The desktop rules
  pin both header toolbar groups with `flex-shrink: 0`, which stops their children
  ever needing to wrap, so `.font-size-controls` measured 357 px and
  `.theme-toggle-section` 575 px against a 320 px viewport. Each condition passed
  alone; only the combination failed. The `max-width: 768px` block now releases the
  pin (`flex-shrink: 1; min-width: 0; max-width: 100%`), lets `.font-size-controls`
  wrap, and drops `white-space: nowrap` from `.theme-label-box` and
  `.theme-toggle-btn`. All six viewport × font-size combinations now report zero
  horizontal overflow.
- **Header font-size buttons.** Were 36 × 31 px and 34 × 30 px; now carry
  `min-width: 44px; min-height: 44px` under `.font-size-controls .font-size-btn`.
  The selector is scoped on purpose — see the gap below.
- **Radio label rows.** `.radio-option` was 28 px tall and is the hit target for its
  radio; it now carries `min-height: 44px`, the same fix and the same value as
  `.ds-toggle-option`. Nothing shrank.

**Gaps found 2026-08-18, deferred then, both CLOSED 2026-08-21 (v1.17, commit
`7634035`).** Recorded here as found rather than deleted, because when a defect was
seen and why it waited is part of what this section is for. Neither is outstanding:

- ~~The preview panel's stepper and toggle buttons render **20 × 22 px**
  (`#brightness-decrease`, `#brightness-increase`, `#contrast-decrease`,
  `#contrast-increase`) and **49 × 20 px** (`#edges-toggle`)~~ — **FIXED.** They reuse
  the `.font-size-btn` class, which is why the 2026-08-18 header fix was scoped to
  `.font-size-controls .font-size-btn` rather than applied to the bare class: the
  preview panel is laid out tightly, so more than doubling these buttons was a layout
  change that needed its own review. It got one — Brennen approved the reflow from
  before/after screenshots at 100% and 200% font (FD-18). `.preview-stepper-btn` is now
  **44 × 44 px** and `.preview-toggle-btn` **49 × 44 px** (`min-width: max(4em, 44px)`);
  the overlay grows 35 → 56 px at 100% font and 128 → 131 px at 200%, wrapping to two
  rows inside the viewer with nothing clipped. See §3.8.
- ~~The skip link is hidden with a hardcoded `top: -40px`, but at 200% app font size it
  grows to 102 px tall, so roughly 62 px of it stays on screen over the page header.~~
  — **FIXED, and the figure above was wrong.** The 102 px / ~62 px measurement came from
  a probe that scaled `<html>` and `<body>` together, which compounds the two; the real
  leak was **19 px at 200%**, and 0/3/8/13/19 px at 100/125/150/175/200%. The diagnosis
  was right — a fixed pixel offset hiding an element whose height scales with the font —
  so `top: -40px` is now `transform: translateY(-100%)`, which hides the link by its own
  height at any font size: **0 px at all five steps**. See §4.1.

**Nothing from the 2026-08-18 sweep remains open.**

**Warning and note text tokens (fixed 2026-08-21).** The three front-of-card boxes
`#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning` hardcoded
their colour in a `style=` attribute — `#d73502` on the two overflow warnings,
`#059669` on the capitalization note — which both failed WCAG 2.1 SC 1.4.3 (AA) and
broke the standing rule that every colour comes from a design token. One fix served
both: the values moved into `--warning-text` and `--note-text` in all three theme
blocks of Section 1.2.

| Box | Theme | Was | Now | Ratio before → after |
|---|---|---|---|---|
| Both overflow warnings | light | `#d73502` | `var(--warning-text)` `#b91c1c` | 4.56:1 → **6.18:1** |
| Both overflow warnings | dark | `#d73502` | `var(--warning-text)` `#fed7d7` | **2.16:1** → **7.81:1** |
| Capitalization note | light | `#059669` | `var(--note-text)` `#0f7a5a` | **3.60:1** → **5.08:1** |
| Capitalization note | dark | `#059669` | `var(--note-text)` `#6ee7b7` | **2.74:1** → **6.76:1** |
| All three | high contrast | (overridden) | (overridden) | 16.04:1 / 12.58:1, unchanged |

All ratios are against `--bg-secondary`, the surface the boxes sit on, which is the
worst case — `--bg-primary` is lighter in the light theme and darker in the dark
theme, so both tokens measure higher there. High contrast never changed because
`[data-theme="high-contrast"] .grade-note` forces `#fdfe00` with `!important`, which
outranks a normal inline declaration; the tokens are declared in that block for
completeness and never paint.

**Why these values.** Both reuse a hex already in the palette rather than introducing
a new one — `--warning-text` takes `--error-text`'s value in each theme, `--note-text`
takes `--btn-success-bg` (light) and `--btn-success-border` (dark). Chosen by Brennen
2026-08-21 (FD-19a, FD-19b). Note that the light-theme `#d73502` this replaces was
*passing*, at 4.56:1 — by 0.06. A token used in two themes should not sit on that
margin, so it was moved with the failing values rather than left alone.

**The tooling trap, again.** Lighthouse scored **100/100 with all eleven of these
failures live**, on desktop and mobile, exactly as it had in v1.11 for the button
gradients. Two causes: an inline colour on a box that is `display: none` at audit
time is never sampled, and the page background is a `background-image` gradient,
which defeats sampling outright. **A Lighthouse accessibility score of 100 is
necessary but never sufficient evidence on this page — contrast must be measured
directly, with the boxes forced visible, in each of the three themes.**

---

### 4.10 Live Regions Must Already Be in the Accessibility Tree

Found by the NVDA walkthrough on 2026-08-18, not by any automated tool.

**The rule.** A live region announces a **change** to a node the assistive
technology is already tracking. A region that is `display: none` is not in the
accessibility tree at all, so writing its text while it is hidden and revealing it
afterwards produces an **insertion** — a new node that arrives with its text
already inside. Insertions are not changes, and nothing is announced.

Both live regions in the generate flow were written in exactly that order:

```js
el.textContent = message;          // written while the node is off-tree
el.style.display = 'flex';         // revealed only afterwards -> silent
```

**Measured, via the Chrome accessibility tree (CDP `Accessibility.getFullAXTree`):**

| Point in the sequence | `role=status` nodes | Verdict |
|---|---|---|
| Page load (region `display:none`) | 4 | region absent from the tree |
| After 1st message | 5 | node **inserted** with its text — silent |
| After 2nd message | 5 | in-place change — announced |
| After 3rd message | 5 | in-place change — announced |

**Why the tooling passed it.** The markup is textbook-correct — correct `role`,
correct `aria-live`, correct `aria-atomic`. Only the *ordering* is wrong, and
neither Lighthouse nor axe-core evaluates the runtime sequence. Both scored 100/100
with this defect live. **A live region is only proven by hearing it, or by
observing the accessibility tree across the write.**

**Fixed here — `#pair-status` (double-sided pair progress).** The node now stays in
the tree permanently and `setPairStatus()` writes text only. Hiding is done with
`#pair-status:empty`, which clips the region and takes it out of flow while it has
nothing to say, so `.action-footer`'s flex `gap` never sees it. Verified: the
`role=status` node count is **5 at load and 5 after every write**, and
`.action-footer` measures **53.16 px both with the empty region present and with the
element deleted outright** — layout with the beta off is unchanged, as required by
the byte-identical rule in `.clinerules/project-facts.md` §6b. No message wording
changed; this is a timing fix only.

**Fixed here — the four remaining beta-flow warning boxes.** An audit of every live
region on the page found **8 of 10 absent from the accessibility tree at page load**;
only `braille-unicode-live` (an `sr-only` region that is never hidden) was built
correctly. `#pair-status` could be repaired in place because its whole content *is*
the message, so `:empty` matches it. The other four cannot: each wraps a
`<strong>Warning:</strong>` or, in the lock note's case, a full sentence of static
text, so they are never empty and `:empty` never matches.

Those four — `ds-back-overflow-warning`, `ds-gap-warning`,
`indicator-mode-lock-note`, `tactile-gap-warning` — are instead announced through a
**single shared `sr-only` mirror region, `#a11y-status`**, which is never hidden and
never moves, so writing to it is always a change. `announceStatus(source, message)`
takes the id of the owning box: a box only clears the channel when its own message is
still the one showing, so hiding one warning cannot silently wipe another's. Writing
an unchanged string is not a mutation and announces nothing, which is what stops the
per-keystroke recomputes from chattering. Each announcement repeats the box's own
`textContent`, so what is heard matches what is shown, "Warning:" included — the
mirror authors no wording of its own.

**`role="status"` and `aria-live="polite"` were removed from those four boxes.** This
is a deliberate ARIA removal, and worth understanding rather than reverting: on a box
that is hidden between messages those attributes can never fire on first appearance,
and leaving them in place would let an assistive technology that *does* announce a
newly-inserted live region speak the same warning twice — once from the box, once
from the mirror. Everything else about the boxes is unchanged; in particular
`#indicator-mode-lock-note` is still referenced by the disabled "Visual markers"
radio's `aria-describedby`, which reads its text whether or not the box is visible,
so that wiring is untouched.

`#indicator-mode-lock-note` is the sharp case, and the reason this class of bug
survives review: a box whose text updates repeatedly loses only its **first** message
and works perfectly afterwards, but the lock note appears once with fixed text and
was therefore silent **every single time**.

Verified by driving the real UI, not by calling internals: the `role=status` node
count holds at 6 across every write, and each of the four puts its own text on the
channel — the lock note's "Locked: Double-Sided Card is on…" on toggling the beta,
back-of-card overflow on over-long text, the same-surface gap warning on a squeezed
lattice, and the tactile seam-gap warning on a reduced diameter — with the channel
released again once the condition clears.

**Two refinements from the NVDA run that followed (2026-08-18).** Hearing the fix work
exposed two things the accessibility tree cannot show:

*Queue order.* Written synchronously inside the change handler, the lock note was
queued **ahead** of the checkbox's own "checked, expanded" — so the user sat through a
30-word sentence before learning whether the box they had just pressed was ticked. The
announcement is now deferred by one task (`setTimeout(…, 0)`), which lets the
control's own state event go first. There is no declarative way to order a live region
against a control's state announcement, so this is deliberate and must not be
"cleaned up" into a synchronous call.

*Typing chatter.* `ds-back-overflow-warning` recomputes on every keystroke and its text
carries a live cell count, so every character typed produced a genuinely different
string — three separate announcements in one sentence of typing, talking over the user
as they wrote. It now announces only on the transition from hidden to shown; while the
warning stays up, the visible box keeps updating silently. Clearing the overflow and
re-triggering it announces again. Measured: **3 announcements before, 1 after**, over
the same typed sentence.

The general rule both point at: the accessibility tree proves a region *can* announce.
Only listening proves it announces *usefully*.

**Fixed 2026-08-18 — `#error-message`.** Mirrored to `#a11y-status` by a single
MutationObserver rather than an announce call threaded through each of its ~20
writers, so it cannot drift out of step with the visible box and picks up any
message added later. Its `role="alert"`/`aria-live` were removed, for the same
double-speak reason as the four boxes above. The observer reads
`#error-text-container`, which excludes the decorative warning glyph and the
permanent browser-capability notice. Details and the two further defects this
uncovered are in STL Export and Download Specifications §8.

**Was, before that fix:** The same defect affects
the single-sided flow, where `#error-message` carries *every* progress notice,
validation error and failure message. A blind user who overruns a line is shown
"Line 1 exceeds 13 cells…" on screen and hears **nothing**, so they cannot discover
why generation refused. This is a **WCAG 2.1 SC 4.1.3 Status Messages (AA)**
failure and it is app-wide, not beta-specific. The agreed fix is a separate,
always-present `sr-only` mirror region that the code writes to alongside the visual
box, leaving that box's styling and timing untouched — `#error-message` is
`position: absolute` with its own background, border and shadow, so keeping it
permanently in flow is not viable. `#a11y-status` and `announceStatus()` already
exist for this, so the scheduled work is wiring, not new machinery.

**Fixed 2026-08-21 — the last three regions: `auto-overflow-warning`,
`cylinder-overflow-warning` and `caps-warning`.** These carried the identical defect
for three days longer than the rest, because the phase that was to fix them lost its
slot to a numbering collision. All three had textbook-correct
`role="status" aria-live="polite"` on a box that is `display:none` between messages,
and none was among `announceStatus()`'s wired sources — so the front-of-card overflow
warning, the one users hit most often, was silent every time it appeared. The
attributes were removed from all three boxes and each now announces its own
`textContent` through `#a11y-status`, exactly as the beta-flow boxes do. No wording
was authored: what is heard is the box's own text, "Warning:" and "Note:" included.

Each of the three writes and clears through a small helper so no call site can drift:
`hideAutoOverflow()`, `hideCylinderOverflow()`, and the inline clear in
`updateCapsWarning()`. All three announce **only on the transition from hidden to
shown**, for the reason `ds-back-overflow-warning` does.

**The capitalization note is the one that had to be measured rather than reasoned
about.** Its text is fixed, so the expectation was that the "an unchanged string is
not a mutation" property above would suppress its repeats by itself. It does not:
`announceStatus()` assigns `textContent` unconditionally, and assigning an identical
string still replaces the text node — a real DOM mutation. `updateCapsWarning()` also
runs on **every keystroke with no debounce**, unlike the two overflow checks which are
debounced by 250 ms. Measured on the real UI: **11 announcements over 11 keystrokes
without the gate, 1 with it.** The same hidden-to-shown gate the overflow boxes use is
therefore applied here too, despite the static text.

Verified by driving the real UI: the `role=status` node count is **6 at page load and
6 while each of the three warnings is shown** — previously each one pushed the tree to
7 whenever it appeared — and each box announces once per episode and releases the
channel when its condition clears. Listening steps for all three are in
[NVDA Live Warnings Walkthrough](../development/NVDA_LIVE_WARNINGS_WALKTHROUGH.md).

**With these three, every live region on the page is accounted for.** The
`#action-btn` silent-rename defect listed here as outstanding was in fact resolved on
2026-08-18 by the Generate/Download split — `#action-btn` keeps its name and role for
its whole life and the file is offered by a separate `#download-stl-btn` (see STL
Export and Download Specifications §8, v1.8). This paragraph had not been updated to
match; corrected 2026-08-21.

---

## 5. Scrollbar Customization

### 5.1 Form Scroll Area Scrollbar

The right column is split in two: `.form-section` is the panel (never scrolls) and
`.form-scroll` is the scrolling body inside it. The scrollbar therefore belongs to
`.form-scroll`, and it remains the only scrollbar on the page — see §7.1.

```css
.form-scroll {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: auto;           /* Firefox */
    scrollbar-color: #3182ce #e2e8f0; /* Firefox: thumb track */
}

/* WebKit browsers */
.form-scroll::-webkit-scrollbar {
    width: var(--scrollbar-width);   /* 18px */
}

.form-scroll::-webkit-scrollbar-track {
    background: #e2e8f0;
    border-radius: 8px;
    border: 2px solid #3182ce;
}

.form-scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #4299e1, #3182ce);
    border-radius: 10px;
    border: 2px solid #ffffff;
    box-shadow: 0 3px 6px rgba(49, 130, 206, 0.4);
}

.form-scroll::-webkit-scrollbar-thumb:hover {
    background: #2563eb;
}
```

### 5.2 Global Page Scrollbar

```css
body::-webkit-scrollbar {
    width: var(--global-scrollbar-width);  /* 13.5px (25% smaller than form) */
}

body::-webkit-scrollbar-track {
    background: var(--bg-tertiary);
    border-radius: 8px;
    border: 1px solid var(--border-secondary);
}

body::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--text-secondary), var(--text-primary));
    border-radius: 10px;
    border: 2px solid var(--bg-primary);
}
```

### 5.3 Theme-Specific Scrollbar Styles

**Dark Theme:**
```css
[data-theme="dark"] .form-scroll {
    scrollbar-color: #63b3ed #2d3748 !important;
}

[data-theme="dark"] .form-scroll::-webkit-scrollbar-track {
    background: #2d3748 !important;
    border: 1px solid #63b3ed !important;
}

[data-theme="dark"] .form-scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #90cdf4, #63b3ed) !important;
    border: 2px solid #1a202c !important;
}
```

**High Contrast:**
```css
[data-theme="high-contrast"] .form-scroll {
    scrollbar-color: var(--text-secondary) var(--bg-tertiary) !important;
}

[data-theme="high-contrast"] .form-scroll::-webkit-scrollbar-track {
    background: var(--bg-tertiary) !important;
    border: 2px solid var(--border-secondary) !important;
}

[data-theme="high-contrast"] .form-scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--text-secondary), var(--text-primary)) !important;
    box-shadow: none !important;
}
```

---

## 6. Button State Management

### 6.1 Action Button States

The main action button has two states: **Generate** and **Download**.

```javascript
// Generate state (blue, prompts user to create STL)
function resetToGenerateState() {
    // Idempotent - see "Why this must be idempotent" below
    if (actionBtn.getAttribute('data-state') === 'generate' &&
        !actionBtn.disabled &&
        actionBtn.style.opacity === '1') {
        return;
    }
    actionBtn.textContent = 'Generate STL';
    actionBtn.className = 'generate-state';
    actionBtn.setAttribute('data-state', 'generate');
    actionBtn.setAttribute('aria-label', 'Generate STL file from entered text');
    actionBtn.style.opacity = '1';
    actionBtn.disabled = false;
}

// Download state (green, allows user to download generated STL)
function setToDownloadState() {
    actionBtn.textContent = 'Download STL';
    actionBtn.className = 'download-state';
    actionBtn.setAttribute('data-state', 'download');
    actionBtn.setAttribute('aria-label', 'Download generated STL file');
    actionBtn.style.opacity = '1';
    actionBtn.disabled = false;
}
```

**State Transitions:**
```
User enters text → Button shows "Generate STL" (generate-state)
                         ↓
User clicks "Generate STL" → Button shows "Generating..." (disabled)
                         ↓
Generation complete → Button shows "Download STL" (download-state)
                         ↓
User modifies any input → Button returns to "Generate STL" (generate-state)
```

### 6.2 Resetting on Settings Changes

The last transition is safety-critical: a stale STL must never be downloadable under
settings it was not built with. It is implemented as **event delegation on the form**, not
as a list of inputs:

```javascript
['input', 'change'].forEach(eventName => {
    form.addEventListener(eventName, resetToGenerateState);
});
```

This covers every current and future control in `#braille-form` automatically. The previous
hand-maintained list of element IDs silently missed controls added later — the tactile
indicator dials among them — so any new control must **not** re-introduce a per-input
listener; adding it to the form is enough.

Two consequences to keep in mind:

- `#action-btn` lives **outside** the form (in `.action-footer`), so pressing it never
  triggers the reset it would otherwise fire on itself.
- Values written by script (presets, `updateGridColumnsForPlateType()`, the Translate to
  Text button) do not fire `input`/`change`, so those paths call `resetToGenerateState()`
  explicitly.

#### Why this must be idempotent

`resetToGenerateState()` returns early when the button is already in the generate state.
That guard is load-bearing, not an optimization.

A `<textarea>` or `<input>` fires its `change` event on blur — which happens on the very
mousedown that presses the action button. Delegation therefore runs the reset *between*
mousedown and mouseup on the button being pressed. If the reset rewrites `textContent` and
`className` at that moment, **WebKit dispatches no `click` event at all**: mousedown and
mouseup both land, and the click is silently dropped. The user types their text, presses
Generate, and nothing happens — on Safari only, and only on the first press after typing.

The same reasoning rules out a transform-based hover effect on this button
(`#action-btn` animates colour and shadow only): anything that moves the element under the
pointer reproduces the dropped click. Pinned by
`tests/e2e/formLayout.spec.ts` ("acts on the first click even when a text field still has
focus").

### 6.3 Action Button Placement

`#action-btn` sits in `.action-footer`, a fixed bar below `.form-scroll`. It is always
visible: on desktop because it is a flex sibling of the scroll area, on mobile because the
footer is `position: sticky; bottom: 0`. See §7.1.

### 6.4 High Contrast Button Styling

See Section 1.3 for complete high contrast button specifications.

---

## 7. Layout Responsiveness

### 7.1 Desktop Two-Column Layout

The viewport is locked (`body` and `.main-layout` are `overflow: hidden`), so the page has
exactly one scrollbar: `.form-scroll`. The form column is a three-part flex column — panel,
scrolling body, pinned footer:

```css
.content-area {
    display: flex;
    gap: 1.5em;
    width: 100%;
    flex: 1;
    min-height: 0;      /* Lets the flex children shrink and scroll */
    overflow: hidden;
}

/* Left Column - Preview */
.preview-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
}

/* Right Column - Form panel: never scrolls itself */
.form-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}

/* Scrolling body of the form column */
.form-scroll {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
}

/* Pinned action bar - always in view */
.action-footer {
    flex: 0 0 auto;
    display: flex;
    justify-content: center;
    padding-top: 0.6em;
    padding-bottom: env(safe-area-inset-bottom);
    border-top: 1px solid var(--border-primary);
    background: var(--bg-secondary);
}
```

**Invariant:** `.form-scroll` must be the only scrollable descendant of `.form-section`.
Giving `.form-section` its own `overflow-y` again would nest a second scrollbar inside the
first, which is what the split exists to prevent. Pinned by
`tests/e2e/formLayout.spec.ts`.

### 7.2 Mobile Stacked Layout

Below 768px the page itself scrolls, so the panel must not clip and the scroll area must not
create a second scroll context. The footer becomes sticky instead of flex-pinned:

```css
@media (max-width: 768px) {
    .main-layout {
        height: auto;
        min-height: 100vh;
        overflow: visible;   /* See the sticky-ancestor note below */
    }

    .content-area {
        flex-direction: column;
        gap: 1.5em;
        overflow: visible;
    }

    .preview-section {
        flex: none;
        width: 100%;
        height: auto;
    }

    .form-section {
        flex: 1;
        width: 100%;
        max-height: none;
        overflow: visible;
    }

    .form-scroll {
        overflow: visible;
    }

    .action-footer {
        position: sticky;
        bottom: 0;
        z-index: 5;
        padding-bottom: calc(0.4em + env(safe-area-inset-bottom));
        box-shadow: 0 -4px 12px var(--shadow-light);
    }

    #viewer {
        height: calc(40vh - 1em);  /* 40% of viewport on tablets */
    }
}

@media (max-width: 480px) {
    #viewer {
        height: calc(35vh - 1em);  /* 35% of viewport on phones */
    }
}
```

**Sticky-ancestor constraint:** every ancestor of `.action-footer` between it and the page
must keep `overflow: visible` on **both** axes below 768px. A sticky element positions
against its nearest scrolling ancestor, and `overflow-x: hidden` alone is enough to make one
(the other axis computes to `auto`). `.main-layout` previously carried
`overflow-y: auto; overflow-x: hidden` on mobile; because that element never actually
scrolls, the footer silently stopped sticking and simply sat at the end of the document —
which looks like working layout until you scroll. `<body>` already clips horizontally, so
nothing is lost by making the inner containers visible. Pinned by
`tests/e2e/formLayout.spec.ts`.

### 7.3 iOS Safe Area Handling

The application implements full iOS safe area support to prevent content from being hidden under device notches, the Dynamic Island, or the iOS address bar.

#### Viewport Meta Tag

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
```

The `viewport-fit=cover` attribute allows the app to extend into safe area insets.

#### CSS Safe Area Insets

```css
:root {
    /* iOS Safe Area Support */
    --vh: 1vh; /* Dynamic viewport height fallback */
}

body {
    /* Prevent content from being hidden under notch/Dynamic Island */
    padding-top: env(safe-area-inset-top);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
}

.form-section {
    /* Ensure bottom buttons are accessible (not hidden behind iOS toolbar) */
    padding-bottom: calc(1em + env(safe-area-inset-bottom));
}
```

#### Dynamic Viewport Height Support

iOS Safari's address bar can collapse/expand, changing the viewport height. The app handles this with both modern (`dvh`) and fallback (JavaScript) approaches:

```css
/* Dynamic viewport height for full-height layouts */
@supports (height: 100dvh) {
    .content-area {
        min-height: 100dvh;
    }
}

@supports not (height: 100dvh) {
    .content-area {
        min-height: calc(var(--vh, 1vh) * 100);
    }
}
```

#### JavaScript Viewport Height Handler

For browsers that don't support `dvh`, JavaScript dynamically updates the `--vh` custom property:

```javascript
// Dynamic viewport height fix for iOS Safari (address bar handling)
function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Set on load and resize
setVH();
window.addEventListener('resize', setVH);
window.addEventListener('orientationchange', setVH);

// Also handle visualViewport if available (more accurate on mobile)
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', setVH);
}
```

#### Safe Area Support Matrix

| Device Feature | CSS Solution | Fallback |
|----------------|-------------|----------|
| iPhone notch | `env(safe-area-inset-top)` | None needed (graceful) |
| Dynamic Island | `env(safe-area-inset-top)` | None needed (graceful) |
| Bottom gesture bar | `env(safe-area-inset-bottom)` | None needed (graceful) |
| Collapsing address bar | `100dvh` + JavaScript `--vh` | JavaScript only |

#### Testing on iOS

**Manual Testing Steps:**
1. Open app on iPhone with notch (iPhone X+) or Dynamic Island (iPhone 14 Pro+)
2. Verify top content is not hidden under notch/island
3. Verify bottom buttons are fully accessible (not cut off)
4. Scroll to bottom of form section and verify button row is visible
5. Rotate to landscape and verify all content remains accessible
6. Scroll up/down to collapse/expand address bar and verify layout adapts

---

## 8. Help Modal System

### 8.1 Overview

The Help Modal provides business card guidance — with rule statements quoted verbatim from the BANA *Business Cards Fact Sheet* (approved March 2024) — and application help through an accessible tabbed interface. See [`docs/guides/_bana_business_cards_verified_source.md`](../guides/_bana_business_cards_verified_source.md) for the verified-source transcription that the quoted blocks are reproduced from.

**Location:** `public/index.html` (added January 2026)

### 8.2 Modal Structure

```html
<div class="modal hidden" id="helpModal" role="dialog" aria-modal="true" aria-labelledby="helpModalTitle">
    <div class="modal-overlay" id="helpModalOverlay"></div>
    <div class="modal-content modal-large">
        <div class="modal-header">
            <h2 id="helpModalTitle">Help & Guide</h2>
            <button class="modal-close" id="helpModalClose" aria-label="Close help guide">...</button>
        </div>
        <div class="modal-body help-modal-body">
            <div class="help-tabs" role="tablist">...</div>
            <div class="help-panels">...</div>
        </div>
    </div>
</div>
```

### 8.3 Tab Panels

| Tab ID | Panel ID | Content |
|--------|----------|---------|
| `tab-quickstart` | `helpPanelQuickStart` | Getting started steps, basic layout |
| `tab-businesscard` | `helpPanelBusinessCard` | BANA priority guide, space-saving strategies |
| `tab-formatting` | `helpPanelFormatting` | Phone, email, web, name formatting tips |
| `tab-examples` | `helpPanelExamples` | Real-world BANA examples |
| `tab-resources` | `helpPanelResources` | Links to standards, credits |

### 8.4 Accessibility Features

| Feature | Implementation |
|---------|----------------|
| Focus Trap | Tab/Shift+Tab cycles within modal |
| Keyboard Navigation | Arrow keys navigate tabs, Escape closes modal |
| ARIA Roles | `role="dialog"`, `aria-modal="true"`, `role="tablist/tab/tabpanel"` |
| Focus Restoration | Returns focus to trigger element on close |
| Screen Reader | `aria-labelledby`, `aria-selected`, `aria-controls` |

### 8.5 JavaScript API

```javascript
// Open modal (default: quickstart tab)
window.openHelpModal('quickstart');

// Open modal to specific tab
window.openHelpModal('businesscard');

// Switch tabs programmatically
window.switchHelpTab('tab-formatting');
```

### 8.6 Trigger Buttons

**Location:** `.accessibility-controls-top` in title section

| Button | ID | Action |
|--------|-----|--------|
| GitHub Link | — | Opens GitHub repo in new tab |
| Help Button | `helpModalBtn` | Opens Help Modal |
| Info Panel Link | — | Calls `window.openHelpModal('quickstart')` |

### 8.7 CSS Classes

| Class | Purpose |
|-------|---------|
| `.modal` | Fixed full-screen overlay container |
| `.modal.hidden` | Hides modal (display: none) |
| `.modal-overlay` | Semi-transparent backdrop |
| `.modal-content` | Modal dialog box |
| `.modal-large` | Width: 90%, max-width: 800px |
| `.help-tabs` | Tab navigation container |
| `.help-tab` | Individual tab button |
| `.help-panel` | Tab panel content |
| `.help-table` | Styled table for help content |
| `.example-box` | Styled example container |

### 8.8 High Contrast Mode

| Element | High Contrast Style |
|---------|---------------------|
| Modal background | `#000` with `#ffff00` border |
| Tab text | `#02fe05` (green) |
| Active tab | `#ffff00` (yellow) with yellow bottom border |
| Links | `#00ffff` (cyan) |
| Table borders | `#ffff00` (yellow) |

### 8.9 Related Documentation

- [BUSINESS_CARD_TRANSLATION_GUIDE.md](../guides/BUSINESS_CARD_TRANSLATION_GUIDE.md) — Full in-depth guide linked from modal
- [ADA_ACCESSIBILITY_VALIDATION_SOP.md](../development/ADA_ACCESSIBILITY_VALIDATION_SOP.md) — Accessibility testing procedures

---

## 9. Design Rationale

### Why Dark Mode as Default

1. **Reduced Eye Strain** — Dark backgrounds are easier on the eyes, especially during extended use
2. **Power Efficiency** — Dark themes consume less power on OLED/AMOLED displays
3. **Focus on Content** — The 3D preview (main content) stands out better against dark backgrounds
4. **Consistency** — Users get the same starting experience regardless of system settings

### Why No Theme Persistence

1. **Accessibility First** — Users with visual impairments can quickly access High Contrast mode
2. **Device Independence** — Same experience across devices without sync complexity
3. **Predictable Behavior** — Users always know what to expect when loading the app

### Why Specific High Contrast Colors

The high contrast color palette follows WCAG AAA contrast requirements:

| Text Color | Background | Contrast Ratio |
|------------|------------|----------------|
| `#02fe05` (Green) | `#000000` (Black) | 15.4:1 (exceeds 7:1 AAA) |
| `#fdfe00` (Yellow) | `#000000` (Black) | 19.6:1 (exceeds 7:1 AAA) |
| `#00ffff` (Cyan) | `#000000` (Black) | 16.7:1 (exceeds 7:1 AAA) |

### Why Three-Point Lighting in High Contrast Mode

Low vision users benefit from enhanced depth perception:
- **Key Light** — Primary illumination from upper-right
- **Fill Light** — Prevents harsh shadows that obscure details
- **Back Light** — Edge definition helps distinguish the model from the background

---

## Appendix A: Complete Theme Toggle Button HTML

```html
<div class="theme-toggle-section" role="group" aria-labelledby="theme-label">
    <div id="theme-label" class="theme-label-box">
        <span class="theme-label-text">Change Theme to →</span>
    </div>
    <button id="theme-toggle" class="theme-toggle-btn"
            aria-label="Toggle theme"
            title="Toggle between light, dark, and high contrast themes">
        <span class="theme-icon" aria-hidden="true">⚡</span>
        <span class="theme-text">High Contrast</span>
    </button>
</div>
```

## Appendix B: Complete Font Size Controls HTML

```html
<div class="font-size-controls" role="group" aria-label="Font size adjustment">
    <button id="font-decrease" class="font-size-btn"
            aria-label="Decrease font size" title="Decrease font size">
        <span aria-hidden="true">A-</span>
        <span class="sr-only">Decrease font size</span>
    </button>
    <span class="font-size-display" aria-label="Current font size">
        <span id="current-font-size">100</span>%
    </span>
    <button id="font-increase" class="font-size-btn"
            aria-label="Increase font size" title="Increase font size">
        <span aria-hidden="true">A+</span>
        <span class="sr-only">Increase font size</span>
    </button>
    <button id="font-reset" class="font-size-btn reset-btn"
            aria-label="Reset font size to default" title="Reset font size to default">
        <span aria-hidden="true">⟲</span>
        <span class="sr-only">Reset font size</span>
    </button>
</div>
```

## Appendix C: CSS Transition for Theme Changes

```css
/* Smooth transitions between themes */
* {
    transition: background-color 0.3s ease,
                color 0.3s ease,
                border-color 0.3s ease;
    box-sizing: border-box;
}
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial specification document |
| 1.1 | 2024-12-06 | Cross-check verification completed; corrected skip link href from `#main-form` to `#main-content`; updated appendices to match actual implementation |
| 1.2 | 2024-12-06 | Added CAMERA_SETTINGS global configuration documentation in Section 3.4; expanded camera controls section with detailed instructions for adjusting initial view positions for cards and cylinders |
| 1.3 | 2025-12-08 | Added Section 3.7 (STL Preview Label) to clarify the preview panel's purpose; Added Section 3.8 (Preview Display Settings) documenting new brightness and contrast radio button controls for 3D preview customization |
| 1.4 | 2025-12-08 | Fixed Expert Toggle button active state contrast ratio: Changed background from `var(--border-focus)` to darker blues (`#1e4976` for light mode, `#1e5a8a` for dark mode) to meet WCAG AA 4.5:1 contrast requirement with white text |
| 1.5 | 2025-12-08 | **UI Enhancement:** (1) Moved STL Preview Label to top of preview panel as overlay with z-index for visibility; (2) Changed Brightness and Contrast controls from radio buttons to click-through toggle buttons (like Theme toggle) that cycle through levels 1→2→3→4→5→1 on each click |
| 1.6 | 2026-01-05 | Replaced brightness/contrast click-through toggles with +/- stepper controls, added live value display, and refreshed accessibility guidance |
| 1.7 | 2026-01-05 | Added critical warning section about HTML file locations — must edit `public/index.html` (served by Flask), not `templates/index.html` (legacy/not served) |
| 1.8 | 2026-01-05 | **Cross-Browser UI Hardening:** Added Section 3.9 (WebGL Context Recovery), Section 4.5 (Toggle Button ARIA Requirements), Section 4.6 (Reduced Motion Support), and Section 7.3 (iOS Safe Area Handling) to document new accessibility and cross-browser compatibility features |
| 1.9 | 2026-07-30 | **Form column restructure:** Split `.form-section` into a non-scrolling panel plus `.form-scroll` and a pinned `.action-footer`, so `#action-btn` is always in view (Sections 5.1, 6.3, 7.1, 7.2). Documented the form-level event delegation that resets the button on any settings change (Section 6.2), the six Expert Mode submenus and their contrast-safe active colours (Section 4.5), and the two-way translation buttons (new Section 4.7) |
| 1.10 | 2026-08-16 | **Double-Sided Card beta UI:** Added Section 4.8 documenting the disclosure-checkbox toggle (`#double_sided_enabled` with `aria-expanded`/`aria-controls`, 44 px hit target), the Back of Card section reveal with front-legend relabeling, and the locked "Visual markers" radio pattern (native `disabled` + live-region lock note wired into `aria-describedby`). Validated: W3C Nu 0 errors, Lighthouse accessibility 100/100 desktop and mobile |
| 1.11 | 2026-08-17 | **Full ADA SOP executed against the beta flow.** Added Section 4.9 (button contrast tokens, the dark-theme fill-versus-boundary tension, the 44 px `#action-btn`, and the known remaining gaps). Rewrote the `--btn-primary-*` and `--btn-success-*` values in all three theme blocks of Section 1.2 and added four border tokens per theme: white labels were 2.28:1 on the old primary gradient and 2.54:1 on the old success fill, and neither Lighthouse nor axe-core could see it because a `background-image` defeats their sampling. `#action-btn` gained `min-height: 44px` (was 34 px on desktop). Validated after the change: W3C Nu 0 errors 0 warnings on the rendered beta-state DOM, Lighthouse accessibility 100/100 desktop and mobile, 48 of 48 contrast measurements passing across light/dark/high-contrast, keyboard walkthrough clean beta-on and beta-off, reflow clean at 320 px and at 75%/200% app font size on desktop |
| 1.12 | 2026-08-18 | **Reflow and touch-target follow-up to the v1.11 audit, plus a user-facing rename.** Section 4.9 extended: the 320 px + 200% horizontal-scroll failure is fixed by releasing `flex-shrink: 0` on the two header toolbar groups and dropping `white-space: nowrap` from the theme label and button in the `max-width: 768px` block; `.font-size-controls .font-size-btn` gained a 44 × 44 px floor (scoped, not on the bare class); `.radio-option` gained `min-height: 44px`. Two newly found gaps recorded instead of fixed: the preview stepper buttons at 20 × 22 px, and the skip link's hardcoded `top: -40px` failing to hide a 102 px-tall link at 200% font. Separately, the Card Thickness control was renamed to **Print Layer Height** in user-facing text only — see CARD_THICKNESS_PRESET_SPECIFICATIONS.md v1.5. Validated after the change: W3C Nu 0 errors / 0 warnings, Lighthouse 100/100 desktop and mobile, 48 of 48 contrast measurements passing, keyboard walkthrough clean, all six viewport × font-size reflow combinations clean, ruff clean, 30 smoke passed, 90 e2e passed |
| 1.13 | 2026-08-19 | **Reverts the v1.12 rename.** The Card Thickness control keeps its original name: the 0.3 / 0.4 numbers are paper card stock thickness, not print layer height — see CARD_THICKNESS_PRESET_SPECIFICATIONS.md v1.6 for the evidence. User-facing text only; no layout, contrast or structural change, so the v1.12 reflow and touch-target findings stand unaltered. |
| 1.13 | 2026-08-18 | **Live-region defect found by the NVDA walkthrough.** Added Section 4.10: a live region that is `display:none` when its text is written is inserted into the accessibility tree already holding that text, and an insertion is not a change, so nothing is announced. Measured with CDP `Accessibility.getFullAXTree` (`role=status` node count 4 at load, 5 after the first message). Fixed `#pair-status`, which silently swallowed the first of the three double-sided pair messages: the node now stays in the tree and `#pair-status:empty` clips it out of flow instead, with `.action-footer` measured identical (53.16 px) either way. Recorded `#error-message` (all single-sided progress, validation and failure messages, WCAG 4.1.3) and the unannounced `#action-btn` name change as outstanding, scheduled separately. Validated: W3C Nu 0 errors/0 warnings, Lighthouse accessibility 100/100 desktop and mobile |
| 1.14 | 2026-08-18 | **Live-region fix extended to the whole double-sided beta flow.** Section 4.10 extended. An audit of every live region found 8 of 10 absent from the accessibility tree at page load. `#pair-status` took the `:empty` fix; the other four beta boxes (`ds-back-overflow-warning`, `ds-gap-warning`, `indicator-mode-lock-note`, `tactile-gap-warning`) are never empty - each wraps a `<strong>Warning:</strong>` or static text - so they are announced through a new shared always-present `sr-only` region `#a11y-status` via `announceStatus(source, message)`, which is source-scoped so one box clearing cannot wipe another's message. `role="status"`/`aria-live` removed from those four boxes to prevent double-speak; `aria-describedby` wiring on the lock note unaffected. Each announcement repeats the box's own textContent, so no new user-facing wording was authored. `#indicator-mode-lock-note` was silent every time, not just on first appearance. Verified by driving the real UI (role=status node count constant at 6). Remaining: `#error-message`, `auto-overflow-warning`, `cylinder-overflow-warning`, `caps-warning` and the `#action-btn` name change. Validated: W3C Nu 0 errors/0 warnings, Lighthouse accessibility 100/100 desktop and mobile, ruff clean, 119 tests passed |
| 1.15 | 2026-08-18 | **Refinements from hearing the fix run under NVDA.** Section 4.10 extended. The lock note was being queued ahead of the checkbox's own "checked, expanded" because it was written synchronously in the change handler, so the user waited out a 30-word sentence to learn the box was ticked - now deferred one task so the control's state is spoken first. `ds-back-overflow-warning` announced on every keystroke (its text carries a live cell count, so each character is a real change): now announces only on the hidden-to-shown transition, measured 3 announcements before and 1 after over the same typed sentence. Neither was visible in the accessibility tree - the tree proves a region CAN announce, only listening proves it announces usefully |
| 1.16 | 2026-08-18 | **Single-plate flow made audible; Generate/Download split.** Section 4.10: `#error-message` is now mirrored to `#a11y-status` by one MutationObserver, closing the WCAG 4.1.3 failure that left every validation error, progress notice and failure message silent. Its `role="alert"`/`aria-live` removed to prevent double-speak. `#action-btn` no longer renames itself into a download control under the user's focus - a separate `#download-stl-btn` appears instead (styled under its own selectors, 310x44px, contrast 7.25/8.35/15.18:1 across the three themes). Full rationale in STL Export and Download Specifications §8 |
| 1.17 | 2026-08-21 | **The last three unwired live regions, the two remaining touch-target gaps, and the skip link.** Section 4.10: `auto-overflow-warning`, `cylinder-overflow-warning` and `caps-warning` had carried textbook-correct `role="status" aria-live="polite"` on boxes hidden between messages and were in no announcement path at all - a shipped **WCAG 2.1 SC 4.1.3 (AA)** failure covering the front-of-card overflow warning users hit most. Attributes removed from all three; each now announces its own `textContent` through `#a11y-status`, gated hidden-to-shown, via `hideAutoOverflow()` / `hideCylinderOverflow()` / the inline clear in `updateCapsWarning()`. **No user-facing wording was authored.** The capitalization note needed measuring rather than reasoning about: its text is fixed, but `announceStatus()` assigns `textContent` unconditionally and an identical assignment still replaces the text node, and `updateCapsWarning()` runs on every keystroke with no debounce - **11 announcements over 11 keystrokes without a gate, 1 with it** (INTERPOINT §7.6's contradictory "an unchanged string is not a mutation" bullet corrected in the same pass). Section 4.1: the skip link's `top: -40px` replaced by `transform: translateY(-100%)`, which hides it by its own height at any font size - measured leak **0/3/8/13/19 px at 100/125/150/175/200% before, 0 px at all five after**; the original finding's "102 px tall, ~62 px showing" came from a probe that scaled `<html>` and `<body>` together and is corrected in place. Section 3.8: `.preview-stepper-btn` **20x22 -> 44x44 px** and `.preview-toggle-btn` **49x20 -> 49x44 px** (`min-width: max(4em, 44px)`), closing the last WCAG 2.5.5 gaps from v1.12; the overlay grows 35 -> 56 px at 100% font and 128 -> 131 px at 200%, wrapping to two rows inside the viewer with nothing clipped. Separately, all **21 empty `catch` blocks** in `public/index.html` now log (12 `log.error`, 9 `log.debug`), per core rule 13; every `try` kept, no path made able to throw. Validated: W3C Nu **0 errors 0 warnings**, Lighthouse accessibility **100/100 desktop and mobile, 0 failing audits** (`target-size` passing), reflow **0 failures of 6** viewport x font-size combinations, 8 accordion toggles with 0 `aria-expanded`/`aria-controls` defects, ruff clean, **135 pytest / 2 vitest / 106 e2e** (chromium+firefox) unchanged from baseline. **Contrast: 11 pre-existing failures found and NOT introduced here** - identical counts measured against the parent commit; reported separately, see below. |
| 1.19 | 2026-08-21 | **Section 4.9's "Known remaining gaps" list corrected — documentation only.** Both of its bullets were fixed by v1.17 on 2026-08-21 and recorded as fixed in that entry, but the list still presented them as open, so anyone reading §4.9 was told two closed defects were outstanding. The bullets are struck through and marked FIXED in place rather than deleted, each carrying its version, commit `7634035`, and its measured after-figure (steppers 20 × 22 → **44 × 44 px**, toggle 49 × 20 → **49 × 44 px**; skip link **0 px leak at all five font steps**). The skip link's original "102 px tall, ~62 px showing" is corrected where it stands: that probe scaled `<html>` and `<body>` together, and the real leak was **19 px at 200%**. The heading now states that nothing from the 2026-08-18 sweep remains open. No CSS, markup, behaviour, or measurement changed — v1.17's and v1.18's rows are untouched. |
| 1.18 | 2026-08-21 | **The 11 contrast failures v1.17 reported are closed; three colours become tokens.** All eleven were pre-existing and none were introduced by v1.17 — proved by re-running the identical probe against parent commit `9aff093` and getting the same 11 at the same values. Section 1.2: three new tokens per theme block. `--warning-text` and `--note-text` replace the hardcoded inline `color: #d73502` and `color: #059669` on `#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning`, which broke the design-token rule as well as WCAG 2.1 SC 1.4.3 (AA): the overflow warnings went **2.16:1 → 7.81:1** dark and 4.56:1 → **6.18:1** light, the capitalization note **2.74:1 → 6.76:1** dark and **3.60:1 → 5.08:1** light. Both tokens reuse a hex already in the palette (`--error-text`; `--btn-success-bg` / `--btn-success-border`) rather than adding a new one. The light `#d73502` was *passing* at 4.56:1 — by 0.06 — and was moved anyway rather than leave a two-theme token on that margin. High contrast never failed and never changed: `.grade-note` forces `#fdfe00` with `!important`, which outranks a normal inline declaration. Section 4.1: `.skip-link` was `color: white` on `--border-focus` and failed **all three themes** at 4.03 / 2.28 / 3.14:1; the label is now `var(--skip-link-text)` `#000000`, measuring **5.21 / 9.20 / 6.70:1**. Darkening `--border-focus` itself was measured and rejected — it is also the page-wide focus-ring colour, and a blue dark enough for white text (`#2c5282`, 7.97:1) falls to **1.51:1 against the dark theme page**, breaking WCAG 2.2 SC 1.4.11 for every focus ring on the page. All three values chosen by Brennen 2026-08-21 (FD-19a/b/c). Section 4.9 extended with the before/after table and the tooling trap: **Lighthouse scored 100/100 with all eleven failures live**, because an inline colour on a `display:none` box is never sampled and a `background-image` page gradient defeats sampling outright. Validated after the change: contrast **11 failures → 0** across light/dark/high-contrast, plus a new page-wide sweep over *every* visible text element in all three themes at **0 failures** (proved to detect: it reports the 3 skip-link failures when run against the pre-fix file). W3C Nu **0 errors 0 warnings**, Lighthouse accessibility **100/100 desktop and mobile, 0 failing audits**, reflow **0 of 6** viewport × font-size combinations, ruff clean, **135 pytest / 2 vitest / 122 e2e** (chromium+firefox) all unchanged from baseline. No user-facing string, geometry, worker, settings or live-region behaviour changed. |
| 1.21 | 2026-08-22 | **Four small accessibility repairs, four commits, no user-visible sentence and no pixel changed — the batch after the two free wins.** (1) **The 3D preview left the tab ring** (`847ea09`, audit F-G / FD-21 D4): `#viewer` was a `tabindex="0"` div with `role="img"` and no `keydown` listener anywhere in the file, so tabbing into it produced ~65 words ending in "requires mouse or touch" and nothing to do. `tabindex` removed; `role="img"`, the `aria-label` and `aria-describedby="viewer-instructions"` all kept, so browse mode is unchanged. Checked first that nothing depended on it: no test references `#viewer` focus, no script focuses it, and `#viewer:focus-within, #viewer:active` still applies on pointer use. Measured: **real tab ring on load 33 → 32**, with a diff of the two rings showing exactly one removal. That also moves §4.x's reading of audit F-F — **14 of 32** stops now precede Placement Mode, not 15 of 33. Keyboard controls for the preview stay a deferred feature. (2) **The `<h1>` is no longer read "Custom BrailleSTL Generator"** (`8b8f532`, F-H / D5): `.title-section h1` was `display: flex`, which blockifies its children, so both title spans computed to `display: block` and NVDA's browse-mode buffer broke a line between them. Chrome's computed name was always right, and so was the `<form aria-labelledby="main-heading">` that borrows it — only the buffer was wrong, which is why no `aria-label` was added. The h1 is now a block box with `display: inline` spans; `innerText` `"Custom Braille
STL Generator"` → **`"Custom Braille STL Generator"`**. The font size moved onto the h1 so the line box matches the text (box height identical before and after: 29 px at 1440, 20 px at 320) and the two per-breakpoint rules that set both spans collapsed into the h1 rule. `id="main-heading"` untouched. **D5 as written called for a single text node; that was not followed, with Brennen's agreement** — the title renders on one line at every tested width and font size, so there was no "two-line look" to move into CSS, and a single text node would have flattened the two-tone (CSS cannot colour half a text node). Both renderings were shown to him and he chose to keep the spans. All three themes re-checked; SOP reflow 0 failures of 6. (3) **Card Thickness announces one group, not two** (`63d5778`, F-N) — see CARD_THICKNESS_PRESET_SPECIFICATIONS v1.10; named grouping nodes on the page **16 → 15**. (4) **Four per-line language selects lost a description that only repeated their label** (`23575ab`, F-K) — see BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS v1.5; 4 → 0, measured in manual placement mode, where those rows are the only place they exist. Validated: ruff clean, **140 pytest / 2 vitest / 122 e2e** (chromium+firefox), every count identical before and after; W3C Nu 0 errors, 0 warnings. **All four are measured on the accessibility tree, not yet confirmed by ear** — the re-listen is the last step of the audit's item G. |
| 1.20 | 2026-08-22 | **Eight attribute edits that remove roughly a fifth of everything a screen reader says — no wording and no visual change.** The first of the follow-on items from the POST15_7 audit (FD-21, decisions D1-icons and D2 step 1); both were Brennen's approved options. Section 4.5: the six `.expert-submenu-icon` chevrons gained `aria-hidden="true"`, so the decorative `▼` stops being folded into the toggle's accessible name — NVDA had been saying "Shape Selection▼ button collapsed", 17 times for that one button in a measured 34-minute session, while `#expert-toggle-icon` one line away was already marked correctly (audit F-B). Measured on the live AX tree: **5 of 5 exposed accordion names leaked a triangle before, 0 after** (the sixth, Tactile Indicator Dimensions, is hidden unless Row Indicator Style is *Tactile seam arrow*, so it has no AX node in the default state; all six spans carry the attribute). The glyph swap uses `icon.textContent = …`, which replaces only the text node — `aria-hidden` was verified to survive open and close, ▼ → ▲ → ▼, so no JS change was needed. Section 4.7: `aria-describedby="braille-unicode-help"` **removed from `#translate-to-braille-btn` and `#translate-to-text-btn`**. That 72-word paragraph was wired to three controls at once and accounted for 59 exposures, 4,913 words and **30.9% of all speech** (audit F-C); it is unchanged, still visible directly under the field, and still described by `#braille-unicode`, which is the control it is actually about. Measured on the live AX tree: hosts **3 → 1**, nodes carrying a description **20 → 18**, and total description words reachable in one full read of the default page **574 → 430** — a drop of exactly 144, the predicted 72 × 2. **No text was reworded** — shortening the three long paragraphs is D2 step 2 and returns to Brennen as a draft first. Validated: ruff clean, **140 pytest / 2 vitest / 122 e2e** (chromium+firefox), every count unchanged before and after. The speech reduction is measured by accessibility-tree probe, **not yet confirmed by ear**. |

---

## Appendix D: Cross-Check Verification Report

### Verification Summary

A full cross-check was performed between this specification document and the actual implementation in `public/index.html`. The following items were verified:

### ✅ Theme System (Section 1)

| Item | Status | Notes |
|------|--------|-------|
| Light mode CSS variables | ✅ PASS | All 30+ variables match exactly |
| Dark mode CSS variables | ✅ PASS | All variables match exactly |
| High contrast mode CSS variables | ✅ PASS | All critical colors verified |
| Theme cycle order (dark → high-contrast → light) | ✅ PASS | Implementation matches spec |
| Theme persistence policy (none) | ✅ PASS | Always starts in dark mode |
| High contrast button colors | ✅ PASS | Generate: #0201fe bg, #fdfe00 text; Download: #02fe05 bg |

### ✅ Font Size System (Section 2)

| Item | Status | Notes |
|------|--------|-------|
| Font size scale [75, 87.5, 100, 112.5, 125, 150, 175, 200] | ✅ PASS | Exact match |
| Default index = 2 (100%) | ✅ PASS | Verified in implementation |
| Font size persistence policy (none) | ✅ PASS | Always starts at 100% |
| Screen reader announcements | ✅ PASS | Uses aria-live regions |

### ✅ STL Preview Panel (Section 3)

| Item | Status | Notes |
|------|--------|-------|
| Three.js WebGLRenderer settings | ✅ PASS | Antialiasing disabled on mobile |
| Camera settings (45° FOV, position 0,0,120) | ✅ PASS | Exact match |
| OrbitControls damping (0.05) | ✅ PASS | Verified |
| Mobile control speeds (rotate: 0.5, zoom: 0.8, pan: 0.5) | ✅ PASS | Verified |
| High contrast three-point lighting | ✅ PASS | Key, fill, back lights configured |
| Light positions | ✅ PASS | Key: (0.707, 0.5, 0.612), Fill: (-0.707, 0.259, 0.659) |
| High contrast specular (shininess: 300) | ✅ PASS | Verified |
| Standard specular (shininess: 200) | ✅ PASS | Verified |

### ✅ Accessibility Features (Section 4)

| Item | Status | Notes |
|------|--------|-------|
| Skip link (`#main-content`) | ✅ PASS | *Fixed from #main-form* |
| Skip link CSS (top: -40px, focus: top: 0) | ✅ PASS | Verified |
| Focus indicators (3px outline, 2px offset) | ✅ PASS | Verified for all interactive elements |
| .sr-only CSS | ✅ PASS | Exact match |
| Touch targets (48px min on mobile) | ✅ PASS | Verified in media queries |

### ✅ Scrollbar Customization (Section 5)

| Item | Status | Notes |
|------|--------|-------|
| Form section scrollbar width (18px) | ✅ PASS | Uses CSS variable |
| Global scrollbar width (13.5px) | ✅ PASS | Uses CSS variable |
| Dark theme scrollbar colors | ✅ PASS | Gradient thumb, dark track |
| High contrast scrollbar | ✅ PASS | Uses theme variables |

### ✅ Button State Management (Section 6)

| Item | Status | Notes |
|------|--------|-------|
| Generate state (class: generate-state) | ✅ PASS | Verified |
| Download state (class: download-state) | ✅ PASS | Verified |
| State attribute (data-state) | ✅ PASS | Used for click handling |
| ARIA labels for each state | ✅ PASS | Dynamic updates verified |

### ✅ Layout Responsiveness (Section 7)

| Item | Status | Notes |
|------|--------|-------|
| Desktop: 45% preview / 55% form | ✅ PASS | flex: 0 0 45% and calc(55% - 2em) |
| Mobile breakpoint (768px) | ✅ PASS | Stack columns verified |
| Viewer height on tablet (40vh) | ✅ PASS | Verified |
| Viewer height on phone (35vh) | ✅ PASS | Verified in 480px breakpoint |

### Corrections Made During Verification

1. **Skip Link href** — Changed from `#main-form` to `#main-content` to match implementation
2. **Appendix A** — Updated theme toggle HTML to include full structure with label box
3. **Appendix B** — Updated font size controls HTML to include `aria-hidden`, `title`, and `.sr-only` spans

### Verification Method

- Line-by-line comparison of CSS variables
- JavaScript function signature and logic comparison
- HTML structure validation
- Cross-reference of all color hex codes
- Mobile media query verification

---

## Related Specifications

- [SURFACE_DIMENSIONS_SPECIFICATIONS.md](./SURFACE_DIMENSIONS_SPECIFICATIONS.md) — Plate and cylinder dimension controls
- [BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md](./BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md) — Braille dot shape parameters
- [BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md](./BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md) — Text input and translation
- [BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md](./BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md) — Translation preview panel
- [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md) — Counter plate indicator markers
