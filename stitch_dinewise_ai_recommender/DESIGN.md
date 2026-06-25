---
name: Lumina Gastronomy
colors:
  surface: '#051424'
  surface-dim: '#051424'
  surface-bright: '#2c3a4c'
  surface-container-lowest: '#010f1f'
  surface-container-low: '#0d1c2d'
  surface-container: '#122131'
  surface-container-high: '#1c2b3c'
  surface-container-highest: '#273647'
  on-surface: '#d4e4fa'
  on-surface-variant: '#e1bfb5'
  inverse-surface: '#d4e4fa'
  inverse-on-surface: '#233143'
  outline: '#a98a80'
  outline-variant: '#594139'
  surface-tint: '#ffb59d'
  primary: '#ffb59d'
  on-primary: '#5d1900'
  primary-container: '#ff6b35'
  on-primary-container: '#5f1900'
  inverse-primary: '#ab3500'
  secondary: '#eec140'
  on-secondary: '#3e2e00'
  secondary-container: '#b68e01'
  on-secondary-container: '#382a00'
  tertiary: '#c3c6d7'
  on-tertiary: '#2c303d'
  tertiary-container: '#9699a9'
  on-tertiary-container: '#2e313f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59d'
  on-primary-fixed: '#390c00'
  on-primary-fixed-variant: '#832600'
  secondary-fixed: '#ffdf92'
  secondary-fixed-dim: '#eec140'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#594400'
  tertiary-fixed: '#dfe2f3'
  tertiary-fixed-dim: '#c3c6d7'
  on-tertiary-fixed: '#171b28'
  on-tertiary-fixed-variant: '#434654'
  background: '#051424'
  on-background: '#d4e4fa'
  surface-variant: '#273647'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style
The design system targets an upscale, tech-savvy audience seeking high-end culinary experiences through the lens of artificial intelligence. The brand personality is sophisticated yet energetic, blending the precision of data with the warmth of hospitality. 

The aesthetic is a refined **Glassmorphism** execution set against a cinematic dark backdrop. It utilizes high-transparency layers to create a sense of infinite depth, mimicking the multi-layered complexity of flavor profiles. The emotional response is one of discovery and "premium intelligence"—where every recommendation feels like a curated invitation rather than a search result.

## Colors
The palette is rooted in a "Midnight Orchard" concept. The base is a deep navy-to-charcoal gradient that provides a stable, high-contrast foundation for AI-driven insights. 

The accent is a "Solar Flare" gradient ranging from vibrant orange to rich gold. This is used sparingly but impactfully for primary actions and "Match Scores." Grayscale tones are pulled from cool slate blue to maintain harmony with the navy background, ensuring that text never feels jarringly white, but rather luminously integrated.

## Typography
This design system uses a dual-font strategy to balance character with utility. **Outfit** provides a geometric, modern geometric flair for headings, echoing the innovative nature of the AI. **Inter** handles all functional and body text, ensuring maximum legibility during data-dense restaurant comparisons.

Hierarchy is established through significant weight contrast. Display headings use tight letter-spacing and bold weights, while labels use slightly increased tracking and medium weights to remain legible against semi-transparent backgrounds.

## Layout & Spacing
The layout follows a 12-column fluid grid for desktop and a 4-column grid for mobile. We use a "Generous Breath" philosophy—white space is not just a gap, but a tool to reduce cognitive load in the AI decision-making process.

Margins and paddings scale dynamically. Vertical rhythm is strictly enforced in multiples of 8px. Cards and containers should use `lg` (40px) padding on desktop to maintain the premium feel, while mobile scales down to `md` (24px) to maximize screen real estate.

## Elevation & Depth
Depth is created through light and transparency rather than traditional dark shadows.
1.  **Level 0 (Base):** The deep navy gradient background.
2.  **Level 1 (Cards):** Semi-transparent white (`rgba(255, 255, 255, 0.05)`) with a `backdrop-filter: blur(12px)`. Borders are 1px solid `rgba(255, 255, 255, 0.1)`.
3.  **Level 2 (Popovers/Modals):** Increased opacity (`rgba(255, 255, 255, 0.1)`) and a subtle outer glow using a 20% opacity version of the primary orange color to simulate light emission.

Shadows are "Ambient Glows"—highly diffused (30px+ blur) with very low opacity (10-15%) using the primary accent color.

## Shapes
The shape language is organic and approachable. We use a **Rounded** (Level 2) baseline for most containers to soften the technical nature of the AI. 

- Standard components (Inputs, Buttons): 0.5rem radius.
- Feature Cards: 1.5rem (`rounded-xl`).
- Tags/Pills: Full radius (pill-shaped) to distinguish them from interactive buttons.
- Search Bars: Full radius to imply a "capsule" or "lens" into the data.

## Components

### Buttons
Primary buttons utilize the **Solar Flare** gradient with white text and a subtle drop shadow that matches the gradient color. Hover states should trigger a slight scale-up (1.02x) and an increase in the background's saturation. Secondary buttons use a "Ghost" style: a subtle white border and no fill until hover.

### Glass Cards
The core of the UI. Each card must have a 1px top-down inner highlight (white, 20% opacity) to simulate a glass edge catching the light. Content inside cards should be grouped with generous internal padding.

### Inputs
Search inputs and filters are dark, semi-transparent fields (`rgba(0, 0, 0, 0.2)`) with a 1px border. On focus, the border transitions to the primary gold color with a soft outer glow.

### Score Badges
The "AI Match Score" is the most prominent value display. It should be rendered in a large, bold **Outfit** font, using the accent gradient for the text itself or a high-contrast circular "meter" around the number.

### Chips & Tags
Used for cuisine types (e.g., "Japanese," "Vegan"). These use a low-opacity version of the secondary color (`rgba(247, 201, 72, 0.1)`) with text in the solid secondary color to ensure legibility without competing with primary buttons.