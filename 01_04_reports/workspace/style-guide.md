# Report Style Guide

A dark-themed, minimalist design system for professional PDF reports.

## Design Principles

1. **Clarity over decoration** — Every element serves a purpose
2. **Generous whitespace** — Let content breathe
3. **Consistent rhythm** — Predictable spacing creates visual harmony
4. **Subtle contrast** — Dark backgrounds with carefully balanced text colors

## Page Structure (Critical for PDF)

Every document uses `.page` containers. Each `.page` = one printed page.

```html
<body>
  <div class="page">
    <header class="page-header">...</header>
    <div class="page-content">
      <!-- Main content here -->
    </div>
    <footer class="page-footer">...</footer>
  </div>
  
  <div class="page">
    <!-- Next page -->
  </div>
</body>
```

- `body` has no padding — `.page` handles all padding
- `.page-content` grows to fill space between header and footer
- `.page-footer` sticks to bottom via `margin-top: auto`
- Add `page-break-after: always` handled automatically

## Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Background | Near black | `#0d0d0d` | Page background |
| Surface | Dark gray | `#1a1a1a` | Cards, code blocks, table headers |
| Border | Subtle gray | `#2a2a2a` | Dividers, image borders, table lines |
| Text Primary | Off-white | `#e5e5e5` | Body text, headings |
| Text Secondary | Muted gray | `#888888` | Captions, metadata, secondary info |
| Accent | Soft blue | `#6b9fff` | Links, highlights, emphasis |
| Success | Muted green | `#4ade80` | Positive indicators |
| Warning | Muted amber | `#fbbf24` | Cautions |
| Error | Muted red | `#f87171` | Errors, critical info |

## Typography

### Font Stack

- **Headings & Body**: Lexend (variable weight 100-900)
- **Code & Data**: IBM Plex Mono (monospace)

### Type Scale (1.25 ratio)

| Element | Size | Weight | Line Height | Letter Spacing |
|---------|------|--------|-------------|----------------|
| H1 | 32px | 600 | 1.2 | -0.02em |
| H2 | 26px | 600 | 1.25 | -0.01em |
| H3 | 21px | 500 | 1.3 | 0 |
| H4 | 17px | 500 | 1.4 | 0 |
| Body | 14px | 400 | 1.7 | 0.01em |
| Small | 12px | 400 | 1.6 | 0.02em |
| Code | 13px | 400 | 1.5 | 0 |

### Typography Rules

1. **Line length**: 60-75 characters for optimal readability
2. **Paragraph spacing**: 1.5em between paragraphs
3. **Heading spacing**: 2em above, 0.75em below
4. **Never use pure white** (#ffffff) — use #e5e5e5 for less eye strain
5. **Lexend for reading** — optimized for readability, reduces visual stress

## Spacing System (8px base)

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight inline spacing |
| `--space-2` | 8px | Default inline spacing |
| `--space-3` | 16px | Component padding |
| `--space-4` | 24px | Section gaps |
| `--space-5` | 32px | Major section breaks |
| `--space-6` | 48px | Page margins |
| `--space-7` | 64px | Hero spacing |

## Page Layout

### Page Padding (applied to .page, not body)
- **Top/Bottom**: 48px (`--page-padding-y`)
- **Left/Right**: 56px (`--page-padding-x`)

### Content Width
- Maximum: 720px for text content
- Full width for tables and images when needed

### Page Breaks
- Each `.page` div creates a page break automatically
- Use `.no-break` class to prevent splitting elements
- Headings automatically avoid page break after them

## Components

### Images

```css
/* Subtle border, slight rounding, contained */
img {
  max-width: 100%;
  border: 1px solid #2a2a2a;
  border-radius: 6px;
}
```

- Always include alt text
- Add caption below in secondary text color
- 24px margin above and below

### Tables

- Header: Surface background (#1a1a1a), semibold text
- Rows: Transparent background, subtle bottom border
- Cells: 12px vertical padding, 16px horizontal
- No outer border — let the grid emerge from row dividers
- Align numbers to the right
- Align text to the left

### Code Blocks

- Background: Surface (#1a1a1a)
- Border: 1px solid #2a2a2a
- Padding: 16px
- Font: IBM Plex Mono, 13px
- Border-radius: 6px
- No syntax highlighting colors — keep it monochrome

### Inline Code

- Background: rgba(255,255,255,0.06)
- Padding: 2px 6px
- Border-radius: 4px
- Font: IBM Plex Mono

### Blockquotes

- Left border: 3px solid accent (#6b9fff)
- Padding-left: 20px
- Text color: Secondary (#888888)
- Italic style

### Lists

- Bullet: Small circle, secondary color
- Indent: 24px
- Item spacing: 8px
- Nested lists: Additional 24px indent

### Horizontal Rules

- Height: 1px
- Color: Border (#2a2a2a)
- Margin: 32px vertical

## Do's and Don'ts

### Do
- Use consistent heading hierarchy
- Leave generous margins
- Use secondary color for less important info
- Keep tables simple and scannable
- Use subtle borders to define regions

### Don't
- Use decorative icons or emojis
- Add drop shadows or glows
- Use multiple accent colors
- Center body text
- Use bold for entire paragraphs
- Underline text (except links)

## Print Considerations

- `print-background: true` required for dark theme
- Images should have sufficient contrast on dark background
- Test at 100% zoom before finalizing
- A4 format preferred for international use
