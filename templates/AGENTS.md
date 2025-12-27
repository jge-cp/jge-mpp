# Templates

HTML templates using Tailwind CSS, Flowbite, HTMX, and Alpine.js.

## Philosophy

**REUSE existing partials vs. creating new templates:**
- `partials/submissions/_results.html` - Any sortable/filterable list
- `partials/submissions/_list_filters.html` - Filter forms
- `partials/sidebar.html` - Navigation (never duplicate)

**USE Flowbite MCP** for component snippets when building new UI.

**FOLLOW the established design system** - don't introduce new colors, fonts, or spacing.

## Build Commands

```bash
npm run build:css   # Compile Tailwind CSS
npm run watch:css   # Watch mode for development
```

After changing `tailwind.config.js` or `src/css/input.css`, run build.

## Design System

### Color Distribution (60/30/10 Rule)

| Percentage | Color | Usage |
|------------|-------|-------|
| 60% | `bg-background` (#E8E4DE) | Page backgrounds, sidebar |
| 30% | `text-gray-700`, `bg-cream` (#F5F3EF) | Body text, cards |
| 10% | `bg-accent-500` (#E84D1C) | CTAs, highlights, badges |

### Typography

| Element | Font | Size | Class |
|---------|------|------|-------|
| H1 | Roboto Condensed | 47px | `text-xl font-heading` |
| H2 | Roboto Condensed | 29px | `text-lg font-heading` |
| H3 | Roboto Condensed | 23px | `text-md font-heading` |
| Body | Roboto | 18px | `text-base font-body` |
| Small | Roboto | 14px | `text-sm` |

Scale: Golden Ratio (1.618) with 18px base.

### Custom Colors

| Color | Hex | Usage |
|-------|-----|-------|
| `bg-background` | #E8E4DE | Page background |
| `bg-cream` | #F5F3EF | Card backgrounds |
| `border` / `stripe` | #efece8 | Borders, table stripes |
| `accent-500` | #E84D1C | Primary buttons, links |
| `brand-700` | #756148 | Brand earth tone |

### Dark Mode Colors

| Element | Light | Dark |
|---------|-------|------|
| Page background | #E8E4DE | #000000 |
| Card background | #F5F3EF | #1f2121 |
| Borders | #efece8 | #2a2d2d |
| Table stripe | #efece8 | #161818 |

### Border Radius

- Form inputs: `rounded-full` (pill shape)
- Cards: `rounded-2xl` (32px)
- Buttons: `rounded-xl` (24px)
- Badges: `rounded-full` (pill shape)

## Badge Styling

```html
<span class="badge badge-pending">Awaiting Primary</span>   <!-- #fffbeb bg, dark text -->
<span class="badge badge-pending-final">Awaiting Final</span> <!-- #dd8a4e bg, white text -->
<span class="badge badge-approved">Approved</span>           <!-- green-600, white text -->
<span class="badge badge-rejected">Rejected</span>           <!-- red-600, white text -->
```

All badges: `max-w-[140px]`, `min-h-[48px]`, centered text, pill shape.

## HTMX Patterns

```html
<!-- Polling -->
<div hx-get="/url" hx-trigger="load, every 10s" hx-swap="outerHTML">

<!-- Form submit -->
<form hx-post="/url" hx-target="#results" hx-swap="innerHTML">

<!-- Trigger events from server -->
response['HX-Trigger'] = 'notifications-changed'
```

## Alpine.js Patterns

```html
<!-- Component state -->
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open">Content</div>
</div>

<!-- Dark mode -->
<div x-data :class="$store.darkMode.on && 'dark'">
```

## Key Directories

| Directory | Content |
|-----------|---------|
| `base.html`, `base_dashboard.html` | Base layouts |
| `partials/sidebar.html` | Sidebar with navigation |
| `partials/submissions/` | Shared list/filter components |
| `inspections/` | FA/Lot submission templates |
| `dashboard/` | Dashboard templates |
| `notifications/` | Notification dropdown/list |
