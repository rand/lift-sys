# TUI Design System

- **Color Theme**: Uses Textual default dark palette with semantic tokens (`success`, `warning`, `error`) mapped to Rich styles `green`, `yellow`, `red`.
- **Typography**: Textual default font with monospace for IR payload sections.
- **Spacing**: 1 unit padding for compact views, 2 units for primary panels.
- **Components**:
  - `StatusPanel`: Reactive widget for streaming messages.
  - `PlanPanel`: Derived from `Static`, renders planner steps with bullet formatting.
  - `IRPanel`: Scrollable static view showing JSON formatted IR.
  - `CommandBar`: Footer binding summary with dynamic hints.
- **Interactions**: All focusable widgets respond to `Tab`/`Shift+Tab`. Async calls display spinner overlay.
- **Accessibility**: High contrast text, avoids color-only signalling by pairing icons/labels, ensures content accessible via screen reader friendly text (Textual's semantics).
