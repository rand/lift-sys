# TUI Affordances

- **TabbedContent**: Keyboard navigable tabs (Config, IR, Planner) with focus indicators.
- **Input Widgets**: Submit on Enter, show inline status text, support copy/paste.
- **Status Panel**: Streaming status messages with color-coded severity via Rich markup.
- **Command Bindings**: `Ctrl+R` refreshes planner, `Ctrl+F` (future) initiates forward mode, `Q` quits.
- **Notification Toast**: Temporary banners at bottom using `call_later` to auto-dismiss.
- **Progress Indicators**: Use `Spinner` widget during async HTTP operations.
- **Error Handling**: Exceptions displayed in modal dialog with stack trace, accessible via keyboard.
