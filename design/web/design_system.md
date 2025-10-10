# Web Design System

## Foundations
- **Colors**: Base neutral palette (#0F172A, #1E293B, #334155, #F8FAFC). Accent primary #6366F1 (indigo), success #10B981, warning #F59E0B, error #EF4444. Contrast verified with WCAG AA for text/icons.
- **Typography**: Inter for body (16px base), JetBrains Mono for code elements. Line height 1.5.
- **Spacing**: 8px grid scaled (4, 8, 12, 16, 24, 32).
- **Elevation**: Shadows applied via tokens `shadow-sm`, `shadow-md`, `shadow-lg` matching shadcn/ui defaults.

## Components
- **Button**: Variants `default`, `secondary`, `destructive`, `ghost`, `outline`. Props: `size`, `loading`, `icon`. Uses accessible focus ring.
- **Card**: Header, content, footer slots. Supports `status` prop for accent border.
- **Input**: Text, textarea, select unified; includes error message slot and optional icon.
- **Tabs**: Horizontal and vertical orientation with keyboard navigation; used in IDE.
- **Drawer**: Slide-over for typed hole resolution. Supports `onResolve` callback.
- **Badge**: Semantic color variants (info, success, warning, error) used for invariants.
- **Timeline**: Vertical progress indicator with animated connectors.

## Patterns
- **Feedback**: Toast notifications via shadcn `useToast`, inline validation, skeleton loaders for async fetches.
- **Layouts**: Responsive shell with collapsible sidebar, main content using CSS grid (sidebar 280px, content flexible). Mobile uses bottom navigation.
- **Theming**: Light/dark using CSS variables `--background`, `--foreground`; toggled via system preference.

## Accessibility
- Minimum tap target 44px. Keyboard focus loops by section. All modals use ARIA roles. Color palette ensures 4.5:1 contrast for text, 3:1 for icons.

## Documentation
Component stories documented in `frontend/docs/components.mdx` (see frontend project) with usage examples and prop tables generated via TypeDoc.
