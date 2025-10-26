/**
 * Autocomplete plugin for #file and @symbol references
 */

import { Plugin, PluginKey, TextSelection } from 'prosemirror-state';

export const autocompletePluginKey = new PluginKey('autocomplete');

export interface AutocompleteState {
  active: boolean;
  trigger: '#' | '@' | null;
  query: string;
  from: number;
  to: number;
}

export interface AutocompleteItem {
  id: string;
  label: string;
  detail?: string;
  type: 'file' | 'symbol';
  icon?: string;
}

/**
 * Detect autocomplete trigger and query
 */
function detectTrigger(state: any): AutocompleteState | null {
  const { $from } = state.selection;

  // Only trigger at cursor position (not in selection)
  if (state.selection.from !== state.selection.to) {
    return null;
  }

  // Get text before cursor in current node
  const textBefore = $from.parent.textBetween(
    Math.max(0, $from.parentOffset - 50),
    $from.parentOffset,
    null,
    '\ufffc'
  );

  // Check for # trigger (file reference)
  const fileMatch = textBefore.match(/#([\w\-./]*)$/);
  if (fileMatch) {
    const query = fileMatch[1];
    const from = $from.pos - query.length - 1; // Include #
    const to = $from.pos;

    return {
      active: true,
      trigger: '#',
      query,
      from,
      to,
    };
  }

  // Check for @ trigger (symbol reference)
  const symbolMatch = textBefore.match(/@([\w\-_]*)$/);
  if (symbolMatch) {
    const query = symbolMatch[1];
    const from = $from.pos - query.length - 1; // Include @
    const to = $from.pos;

    return {
      active: true,
      trigger: '@',
      query,
      from,
      to,
    };
  }

  return null;
}

/**
 * Create autocomplete plugin
 */
export function createAutocompletePlugin(options: {
  onTrigger: (state: AutocompleteState) => void;
  onDismiss: () => void;
}) {
  return new Plugin({
    key: autocompletePluginKey,

    state: {
      init() {
        return {
          active: false,
          trigger: null,
          query: '',
          from: 0,
          to: 0,
        };
      },

      apply(tr, prevState) {
        // Check if selection changed
        if (!tr.selectionSet && !tr.docChanged) {
          return prevState;
        }

        const newState = detectTrigger(tr);

        // If autocomplete should be active
        if (newState && newState.active) {
          // Notify parent component
          if (!prevState.active || prevState.query !== newState.query) {
            setTimeout(() => options.onTrigger(newState), 0);
          }
          return newState;
        }

        // If autocomplete should be dismissed
        if (prevState.active) {
          setTimeout(() => options.onDismiss(), 0);
        }

        return {
          active: false,
          trigger: null,
          query: '',
          from: 0,
          to: 0,
        };
      },
    },

    props: {
      // Handle special keys when autocomplete is active
      handleKeyDown(view, event) {
        const state = this.getState(view.state);

        if (!state.active) {
          return false;
        }

        // Let parent component handle these keys
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown' || event.key === 'Enter' || event.key === 'Escape') {
          // Dispatch custom event for parent to handle
          const customEvent = new CustomEvent('autocompleteKey', {
            detail: { key: event.key },
          });
          document.dispatchEvent(customEvent);

          if (event.key === 'Enter' || event.key === 'Escape') {
            event.preventDefault();
            return true;
          }
        }

        return false;
      },
    },
  });
}

/**
 * Insert autocomplete item
 */
export function insertAutocompleteItem(
  view: any,
  state: AutocompleteState,
  item: AutocompleteItem
): void {
  const { from, to, trigger } = state;

  // Create the reference text
  const referenceText = `${trigger}${item.label}`;

  // Create transaction to replace text
  const tr = view.state.tr;
  tr.replaceWith(from, to, view.state.schema.text(referenceText));

  // Move cursor after the reference
  tr.setSelection(TextSelection.create(tr.doc, from + referenceText.length));

  view.dispatch(tr);
  view.focus();
}

/**
 * Mock file search
 */
export async function searchFiles(query: string): Promise<AutocompleteItem[]> {
  // Mock files from FileExplorer
  const files = [
    { path: 'docs/planning/HOLE_INVENTORY.md', type: 'markdown' },
    { path: 'docs/planning/SESSION_STATE.md', type: 'markdown' },
    { path: 'docs/supabase/SUPABASE_SCHEMA.md', type: 'markdown' },
    { path: 'lift_sys/ir/models.py', type: 'python' },
    { path: 'lift_sys/ir/constraints.py', type: 'python' },
    { path: 'lift_sys/dspy_signatures/node_interface.py', type: 'python' },
    { path: 'specifications/example_spec.md', type: 'markdown' },
    { path: 'tests/test_ir.py', type: 'python' },
    { path: 'tests/test_validation.py', type: 'python' },
    { path: 'frontend/src/lib/ics/decorations.test.ts', type: 'typescript' },
  ];

  // Filter by query
  const filtered = files.filter((file) =>
    file.path.toLowerCase().includes(query.toLowerCase())
  );

  // Convert to AutocompleteItem
  return filtered.slice(0, 10).map((file) => ({
    id: file.path,
    label: file.path,
    detail: file.type,
    type: 'file' as const,
    icon: file.type === 'python' ? '🐍' : '📄',
  }));
}

/**
 * Mock symbol search
 */
export async function searchSymbols(query: string): Promise<AutocompleteItem[]> {
  // Mock symbols from semantic analysis
  const symbols = [
    { name: 'TypedHole', type: 'class', detail: 'IR model' },
    { name: 'Constraint', type: 'class', detail: 'IR model' },
    { name: 'SemanticAnalysis', type: 'interface', detail: 'Type definition' },
    { name: 'buildDecorations', type: 'function', detail: 'Decoration builder' },
    { name: 'useICSStore', type: 'hook', detail: 'Zustand hook' },
    { name: 'EntityType', type: 'type', detail: 'Type alias' },
    { name: 'HoleKind', type: 'enum', detail: 'Enum' },
    { name: 'ProvenanceSource', type: 'enum', detail: 'Enum' },
  ];

  // Filter by query
  const filtered = symbols.filter((symbol) =>
    symbol.name.toLowerCase().includes(query.toLowerCase())
  );

  // Convert to AutocompleteItem
  return filtered.slice(0, 10).map((symbol) => ({
    id: symbol.name,
    label: symbol.name,
    detail: `${symbol.type} - ${symbol.detail}`,
    type: 'symbol' as const,
    icon: getSymbolIcon(symbol.type),
  }));
}

function getSymbolIcon(type: string): string {
  switch (type) {
    case 'class': return '🔷';
    case 'interface': return '🔶';
    case 'function': return '⚡';
    case 'hook': return '🪝';
    case 'type': return '📐';
    case 'enum': return '📋';
    default: return '•';
  }
}
