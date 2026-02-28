# Phase 1: Dashboard UX Overhaul

## Context Links
- Current dashboard: `dashboard/src/` (732 LOC, 10 files)
- Current Tailwind config: `dashboard/tailwind.config.js` (bare minimum)
- Package.json: `dashboard/package.json` (React 19, Vite 7, Tailwind 3)

## Overview
- **Priority**: P1 (highest impact for GitHub stars)
- **Status**: pending
- **Effort**: 12h
- **Description**: Transform the functional-but-basic dashboard into a professional, polished UI using shadcn/ui design patterns (Radix UI primitives + Tailwind + CVA). Dark theme throughout, consistent spacing, subtle animations, proper typography.

## Key Insights
- Current UI uses raw Tailwind classes with inconsistent patterns (e.g., `bg-gray-950`, `bg-gray-900`, `bg-gray-800` mixed without system)
- No component library; each component hand-styles everything
- shadcn/ui approach: copy-paste components (not npm package), Radix primitives, CVA for variants
- React 19 + Tailwind 3 already in place; just need utilities + primitives
- Current codebase is small enough to refactor entirely without risk

## Requirements

### Functional
- All existing functionality preserved (trace list, topology graph, span detail, cost chart)
- New shared component primitives: Button, Badge, Card, Table, Input, Select, Dialog, Sheet, Tooltip
- Consistent dark theme with CSS variables (not hardcoded gray-XXX everywhere)
- Smooth page transitions and micro-interactions
- Responsive layout (works on 1280px+)

### Non-Functional
- No new runtime JS frameworks (keep React + Tailwind)
- Components under 200 LOC each
- Accessible (keyboard nav, ARIA labels on interactive elements)

## Architecture

### Design System Setup
```
dashboard/src/
  lib/
    utils.ts              # cn() helper (clsx + tailwind-merge)
    api-client.ts         # (existing, untouched)
    use-sse-traces.ts     # (existing, untouched)
  components/
    ui/                   # Shared primitives (shadcn-style)
      button.tsx
      badge.tsx
      card.tsx
      input.tsx
      select.tsx
      table.tsx
      dialog.tsx
      sheet.tsx
      tooltip.tsx
      separator.tsx
      scroll-area.tsx
      skeleton.tsx
    trace-list-table.tsx  # Refactored with ui/ primitives
    trace-topology-graph.tsx  # Refined styling
    span-detail-panel.tsx     # Refactored into Sheet component
    cost-summary-chart.tsx    # Refined styling
  pages/
    traces-list-page.tsx  # Refactored layout
    trace-detail-page.tsx # Refactored layout
```

### CSS Variables Theme
Add to `dashboard/src/index.css`:
```css
:root {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;
  --popover: 222.2 84% 4.9%;
  --popover-foreground: 210 40% 98%;
  --primary: 217.2 91.2% 59.8%;
  --primary-foreground: 222.2 47.4% 11.2%;
  --secondary: 217.2 32.6% 17.5%;
  --secondary-foreground: 210 40% 98%;
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;
  --accent: 217.2 32.6% 17.5%;
  --accent-foreground: 210 40% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 210 40% 98%;
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 224.3 76.3% 48%;
  --radius: 0.5rem;
}
```

## Related Code Files

### Files to Modify
- `dashboard/src/index.css` — add CSS variables, refine base styles
- `dashboard/tailwind.config.js` — extend theme with CSS variable references
- `dashboard/src/App.tsx` — refine header, add sidebar potential
- `dashboard/src/pages/traces-list-page.tsx` — use new Table, Badge, Skeleton
- `dashboard/src/pages/trace-detail-page.tsx` — use Sheet for span panel, refine layout
- `dashboard/src/components/trace-list-table.tsx` — rewrite with ui/table + ui/badge
- `dashboard/src/components/span-detail-panel.tsx` — rewrite as Sheet
- `dashboard/src/components/trace-topology-graph.tsx` — refine node styles, add legend
- `dashboard/src/components/cost-summary-chart.tsx` — refine tooltip, add gradient fills

### Files to Create
- `dashboard/src/lib/utils.ts` — `cn()` utility (clsx + twMerge)
- `dashboard/src/components/ui/button.tsx`
- `dashboard/src/components/ui/badge.tsx`
- `dashboard/src/components/ui/card.tsx`
- `dashboard/src/components/ui/input.tsx`
- `dashboard/src/components/ui/table.tsx`
- `dashboard/src/components/ui/sheet.tsx`
- `dashboard/src/components/ui/skeleton.tsx`
- `dashboard/src/components/ui/separator.tsx`
- `dashboard/src/components/ui/tooltip.tsx`
- `dashboard/src/components/ui/scroll-area.tsx`

## Implementation Steps

### Step 1: Install dependencies
```bash
cd dashboard
npm install clsx tailwind-merge class-variance-authority
npm install @radix-ui/react-dialog @radix-ui/react-tooltip @radix-ui/react-scroll-area @radix-ui/react-separator
npm install lucide-react
```

### Step 2: Setup design system foundation
1. Create `src/lib/utils.ts` with `cn()` helper
2. Update `tailwind.config.js` to use CSS variable references for colors
3. Update `src/index.css` with CSS custom properties for dark theme
4. Add `@layer base` styles for consistent typography

### Step 3: Create shared UI primitives
Build each component in `src/components/ui/` following shadcn patterns:
1. `button.tsx` — variants: default, secondary, ghost, destructive; sizes: sm, default, lg
2. `badge.tsx` — variants: default, secondary, destructive, outline + custom status colors
3. `card.tsx` — Card, CardHeader, CardTitle, CardContent, CardFooter
4. `table.tsx` — Table, TableHeader, TableBody, TableRow, TableHead, TableCell
5. `input.tsx` — styled input with focus ring
6. `skeleton.tsx` — loading placeholder with pulse animation
7. `sheet.tsx` — slide-over panel (wraps Radix Dialog)
8. `separator.tsx` — horizontal/vertical divider
9. `tooltip.tsx` — wraps Radix Tooltip
10. `scroll-area.tsx` — wraps Radix ScrollArea

### Step 4: Refactor trace list table
1. Replace raw `<table>` with `ui/table` components
2. Replace status badge with `ui/badge` with status variants
3. Add `Skeleton` for loading state instead of text
4. Add hover state with subtle row highlight
5. Add Lucide icons for status indicators

### Step 5: Refactor span detail panel
1. Convert from inline `<aside>` to Sheet component (slide from right)
2. Use Card components for input/output code blocks
3. Add Lucide icons for metadata labels
4. Improve code block styling (syntax highlighting placeholder)

### Step 6: Refine topology graph
1. Add a type legend (colored dots + labels) below the graph
2. Improve node styling with rounded corners, subtle shadows
3. Add selected node glow effect
4. Refine edge styling (animated dashes for running spans)
5. Add zoom-to-fit button with proper styling

### Step 7: Refine cost chart
1. Add gradient fills to bars
2. Improve tooltip with card-style container
3. Add total cost summary above chart
4. Better empty state with illustration

### Step 8: Refactor App shell and header
1. Add proper logo/icon in header
2. Add breadcrumb navigation (Traces > TraceID)
3. Consistent header height and padding
4. Add subtle border/shadow styling

## Todo List
- [ ] Install new dependencies (clsx, twMerge, CVA, Radix, Lucide)
- [ ] Create `lib/utils.ts` with `cn()` helper
- [ ] Update `tailwind.config.js` with CSS variable theme
- [ ] Update `index.css` with dark theme CSS variables
- [ ] Create `ui/button.tsx`
- [ ] Create `ui/badge.tsx`
- [ ] Create `ui/card.tsx`
- [ ] Create `ui/table.tsx`
- [ ] Create `ui/input.tsx`
- [ ] Create `ui/skeleton.tsx`
- [ ] Create `ui/sheet.tsx`
- [ ] Create `ui/separator.tsx`
- [ ] Create `ui/tooltip.tsx`
- [ ] Create `ui/scroll-area.tsx`
- [ ] Refactor `trace-list-table.tsx` with new primitives
- [ ] Refactor `span-detail-panel.tsx` as Sheet
- [ ] Refine `trace-topology-graph.tsx` styling + legend
- [ ] Refine `cost-summary-chart.tsx` styling
- [ ] Refactor `App.tsx` header + navigation
- [ ] Refactor `traces-list-page.tsx` layout
- [ ] Refactor `trace-detail-page.tsx` layout
- [ ] Verify all existing functionality preserved
- [ ] Run `npm run build` — zero errors

## Success Criteria
- Dashboard looks on par with Linear/Vercel-quality dark theme
- All existing features work identically
- Zero TypeScript errors on `tsc -b`
- Consistent spacing, typography, and color usage throughout
- Keyboard navigation works on all interactive elements

## Risk Assessment
- **Risk**: Radix primitives conflict with React 19 — **Mitigation**: Radix supports React 19 as of v2
- **Risk**: Tailwind CSS variable approach breaks existing styles — **Mitigation**: Incremental migration, keep fallbacks
- **Risk**: Over-engineering component library — **Mitigation**: Only build what we actually use (YAGNI)

## Security Considerations
- No user input is rendered as HTML (already safe with React)
- Lucide icons are SVG (no XSS vector)
