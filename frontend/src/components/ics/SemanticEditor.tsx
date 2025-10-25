/**
 * SemanticEditor: ProseMirror-based editor with semantic highlighting
 *
 * This editor provides real-time semantic analysis and highlighting for
 * natural language specifications.
 */

import { useEffect, useRef, useState } from 'react';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { keymap } from 'prosemirror-keymap';
import { history, undo, redo } from 'prosemirror-history';
import { baseKeymap } from 'prosemirror-commands';
import { specSchema } from '@/lib/ics/schema';
import { useICSStore } from '@/lib/ics/store';
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

  const { setSpecification, specificationText } = useICSStore();

  useEffect(() => {
    if (!editorRef.current) return;

    // Create initial state
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
  }, [editable, className, placeholder, setSpecification]);

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
      </div>
    </div>
  );
}
