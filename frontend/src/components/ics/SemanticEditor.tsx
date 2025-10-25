/**
 * SemanticEditor: ProseMirror-based editor with semantic highlighting
 *
 * This editor provides real-time semantic analysis and highlighting for
 * natural language specifications.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { keymap } from 'prosemirror-keymap';
import { history, undo, redo } from 'prosemirror-history';
import { baseKeymap } from 'prosemirror-commands';
import { specSchema } from '@/lib/ics/schema';
import { useICSStore } from '@/lib/ics/store';
import { createDecorationsPlugin, updateDecorations } from '@/lib/ics/decorations';
import {
  createAutocompletePlugin,
  insertAutocompleteItem,
  searchFiles,
  searchSymbols,
  type AutocompleteState,
  type AutocompleteItem,
} from '@/lib/ics/autocomplete';
import { AutocompletePopup } from './AutocompletePopup';
import { generateMockAnalysis } from '@/lib/ics/mockSemanticAnalysis';
import '@/styles/ics.css';

interface SemanticEditorProps {
  placeholder?: string;
  editable?: boolean;
  className?: string;
}

export function SemanticEditor({
  placeholder = 'Start writing your specification...',
  editable = true,
  className = '',
}: SemanticEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  // Autocomplete state
  const [autocompleteState, setAutocompleteState] = useState<AutocompleteState | null>(null);
  const [autocompleteItems, setAutocompleteItems] = useState<AutocompleteItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });

  const { setSpecification, specificationText, semanticAnalysis, selectHole, updateSemanticAnalysis } = useICSStore();

  // Autocomplete handlers
  const handleAutocompleteTrigger = useCallback(async (state: AutocompleteState) => {
    setAutocompleteState(state);
    setSelectedIndex(0);

    // Fetch autocomplete items based on trigger type
    const items = state.trigger === '#'
      ? await searchFiles(state.query)
      : await searchSymbols(state.query);

    setAutocompleteItems(items);

    // Calculate popup position (simplified - just use a fixed offset for now)
    // In production, calculate based on cursor coordinates
    if (viewRef.current) {
      const coords = viewRef.current.coordsAtPos(state.to);
      setPopupPosition({
        top: coords.bottom + 5,
        left: coords.left,
      });
    }
  }, []);

  const handleAutocompleteDismiss = useCallback(() => {
    setAutocompleteState(null);
    setAutocompleteItems([]);
    setSelectedIndex(0);
  }, []);

  const handleAutocompleteSelect = useCallback((item: AutocompleteItem) => {
    if (viewRef.current && autocompleteState) {
      insertAutocompleteItem(viewRef.current, autocompleteState, item);
      handleAutocompleteDismiss();
      viewRef.current.focus();
    }
  }, [autocompleteState, handleAutocompleteDismiss]);

  const handleAutocompleteKeyDown = useCallback((key: string) => {
    if (key === 'ArrowDown') {
      setSelectedIndex((prev) => Math.min(prev + 1, autocompleteItems.length - 1));
    } else if (key === 'ArrowUp') {
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (key === 'Enter' && autocompleteItems[selectedIndex]) {
      handleAutocompleteSelect(autocompleteItems[selectedIndex]);
    } else if (key === 'Escape') {
      handleAutocompleteDismiss();
    }
  }, [autocompleteItems, selectedIndex, handleAutocompleteSelect, handleAutocompleteDismiss]);

  // Listen for hole selection events
  useEffect(() => {
    const handleSelectHole = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail?.holeId) {
        selectHole(customEvent.detail.holeId);
      }
    };

    document.addEventListener('selectHole', handleSelectHole);
    return () => document.removeEventListener('selectHole', handleSelectHole);
  }, [selectHole]);

  useEffect(() => {
    if (!editorRef.current) return;

    // Create initial state with all plugins
    const state = EditorState.create({
      schema: specSchema,
      plugins: [
        history(),
        keymap({
          'Mod-z': undo,
          'Mod-y': redo,
          'Mod-Shift-z': redo,
        }),
        keymap(baseKeymap),
        createDecorationsPlugin(() => semanticAnalysis),
        createAutocompletePlugin({
          onTrigger: handleAutocompleteTrigger,
          onDismiss: handleAutocompleteDismiss,
        }),
      ],
    });

    // Create editor view
    const view = new EditorView(editorRef.current, {
      state,
      editable: () => editable,
      attributes: {
        class: className,
        'data-placeholder': placeholder,
      },
      handleDOMEvents: {
        focus: () => {
          setIsFocused(true);
          return false;
        },
        blur: () => {
          setIsFocused(false);
          return false;
        },
      },
      dispatchTransaction(transaction) {
        const newState = view.state.apply(transaction);
        view.updateState(newState);

        // Update store with new content
        if (transaction.docChanged) {
          const text = newState.doc.textContent;
          setSpecification(newState.doc, text);
        }
      },
    });

    viewRef.current = view;

    // Cleanup
    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [editable, className, placeholder, setSpecification, handleAutocompleteTrigger, handleAutocompleteDismiss]);

  // Update decorations when semantic analysis changes
  useEffect(() => {
    if (viewRef.current && semanticAnalysis) {
      updateDecorations(viewRef.current);
    }
  }, [semanticAnalysis]);

  // Trigger mock semantic analysis when text changes (debounced)
  useEffect(() => {
    if (!specificationText || specificationText.length < 3) {
      return;
    }

    const timeoutId = setTimeout(() => {
      const analysis = generateMockAnalysis(specificationText);
      updateSemanticAnalysis(analysis);
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [specificationText, updateSemanticAnalysis]);

  return (
    <div className="ics-editor-container">
      <div className="ics-editor-toolbar">
        <div className="text-sm text-muted-foreground">
          {isFocused ? 'Editing...' : 'Click to edit'}
        </div>
        <div className="ml-auto text-xs text-muted-foreground">
          {specificationText.length} characters
        </div>
      </div>
      <div className="ics-editor-content">
        <div ref={editorRef} />
        {autocompleteState && autocompleteItems.length > 0 && (
          <AutocompletePopup
            items={autocompleteItems}
            selected={selectedIndex}
            position={popupPosition}
            onSelect={handleAutocompleteSelect}
            onKeyDown={handleAutocompleteKeyDown}
          />
        )}
      </div>
    </div>
  );
}
