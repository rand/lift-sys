# Web UI Affordances

## Global
- **Navigation Shell**: Persistent sidebar with sections for Configuration, Repository, IR Review, Planner, and IDE. Hover reveals section descriptions.
- **Command Palette**: `Ctrl+K` opens palette for quick workflow switching. Displays loading spinner on background operations.

## Configuration View
- **Endpoint Input Field**: Validates URLs on blur, shows inline error text, persists value.
- **Temperature Slider**: Drag updates value with tooltip; includes reset button.
- **Save Button**: Primary CTA; disabled until changes detected, shows success toast on completion.

## Repository View
- **Repository Path Picker**: File selector with breadcrumb navigation and mobile-friendly list.
- **Scan Button**: Triggers CodeQL/Daikon run; displays progress bar and cancellable action chip.
- **Analysis Timeline**: Vertical stepper showing CodeQL, Daikon, Fusion status. Supports retry on failed steps.

## IR Review View
- **IR Summary Card**: Collapsible sections for intent, signature, effects, assertions.
- **Typed Hole Assist Chips**: Click opens drawer with resolution suggestions, keyboard navigable.
- **Invariant Badge**: Shows verification state (Pending/Verified/Failed) with color-coded icons.

## Planner View
- **Plan Graph Canvas**: Zoomable Graphviz render; nodes clickable to reveal metadata.
- **Conflict Log Table**: Paginated table with filters and "Export" button.
- **Action Toolbar**: Buttons for "Re-run Reverse", "Re-run Forward", and "Resolve Holes" with loading states.

## IDE View
- **Monaco Editor Pane**: Syntax highlighting, read-only spec lane, editable implementation lane.
- **Constraint Inspector**: Accordion listing constraints to be sent to vLLM; badges indicate source clause.
- **Execution Console**: Streaming logs from backend WebSocket; supports pause/resume.

## Responsive Considerations
- Stack layout on <768px, collapsible navigation, bottom sheet modals replace drawers, accessible focus states across components.
