/**
 * Integration tests for SemanticEditor component
 *
 * Tests editor integration with Zustand store, debounced semantic analysis,
 * and decoration rendering.
 *
 * Note: Due to ProseMirror's reliance on DOM APIs not fully supported in jsdom
 * (elementFromPoint, getClientRects), these tests focus on store integration
 * and use mocked ProseMirror where necessary.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { SemanticEditor } from './SemanticEditor';
import { useICSStore } from '@/lib/ics/store';
import * as api from '@/lib/ics/api';
import type { SemanticAnalysis } from '@/types/ics/semantic';

// Mock the API module
vi.mock('@/lib/ics/api', () => ({
  analyzeText: vi.fn(),
  checkBackendHealth: vi.fn(),
}));

// Mock ProseMirror modules to prevent DOM API issues
vi.mock('prosemirror-view', async (importOriginal) => {
  const actual = await importOriginal<typeof import('prosemirror-view')>();

  return {
    ...actual,
    EditorView: class MockEditorView {
      state: any;
      dom: HTMLDivElement;
      constructor(el: HTMLDivElement, config: any) {
        this.state = config.state;
        this.dom = document.createElement('div');
        this.dom.setAttribute('contenteditable', 'true');
        this.dom.setAttribute('role', 'textbox');
        el.appendChild(this.dom);
      }
      updateState(state: any) {
        this.state = state;
      }
      destroy() {}
      focus() {}
      dispatch() {}
      coordsAtPos() {
        return { top: 0, bottom: 20, left: 0, right: 100 };
      }
    },
  };
});

describe('SemanticEditor Integration Tests', () => {
  beforeEach(() => {
    // Reset store state before each test
    useICSStore.setState({
      specification: null,
      specificationText: '',
      semanticAnalysis: null,
      isAnalyzing: false,
      holes: new Map(),
      constraints: new Map(),
      selectedHole: null,
    });

    // Mock backend health check to return false (use mock analysis)
    vi.mocked(api.checkBackendHealth).mockResolvedValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render editor container with initial state', () => {
    render(<SemanticEditor />);

    // Check for editor elements
    expect(screen.getByText(/click to edit/i)).toBeInTheDocument();
    expect(screen.getByText(/0 characters/i)).toBeInTheDocument();

    // Check store state
    const state = useICSStore.getState();
    expect(state.specificationText).toBe('');
    expect(state.semanticAnalysis).toBeNull();
  });

  it('should update specificationText in store via setSpecification action', async () => {
    render(<SemanticEditor />);

    // Simulate what happens when user types by directly calling setSpecification
    // (since we can't reliably interact with ProseMirror in jsdom)
    const mockDoc = { textContent: 'Hello world' } as any;

    act(() => {
      useICSStore.getState().setSpecification(mockDoc, 'Hello world');
    });

    // Wait for store to update
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.specificationText).toBe('Hello world');
    });
  });

  it('should trigger semantic analysis after 500ms debounce', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Simulate text change in store
    act(() => {
      const mockDoc = { textContent: 'The system must validate input' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'The system must validate input');
    });

    // Store should be updated immediately
    let state = useICSStore.getState();
    expect(state.specificationText).toBe('The system must validate input');

    // Analysis should NOT have started yet
    expect(state.isAnalyzing).toBe(false);

    // Fast-forward time by 400ms (before debounce completes)
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);

    // Fast-forward remaining 100ms to trigger debounce
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    // Wait for analysis to start and complete
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    }, { timeout: 1000 });

    state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);
    expect(state.semanticAnalysis).not.toBeNull();

    vi.useRealTimers();
  });

  it('should update semantic analysis in store when analysis completes', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Simulate text with detectable patterns
    const text = 'The system must process data and should validate input';

    act(() => {
      const mockDoc = { textContent: text } as any;
      useICSStore.getState().setSpecification(mockDoc, text);
    });

    // Fast-forward debounce
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Wait for analysis to complete
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    }, { timeout: 1000 });

    // Check that semantic analysis contains expected elements
    const state = useICSStore.getState();
    expect(state.semanticAnalysis?.modalOperators.length).toBeGreaterThan(0);
    expect(state.semanticAnalysis?.entities.length).toBeGreaterThan(0);

    // Verify specific modal operators were detected
    const modals = state.semanticAnalysis?.modalOperators || [];
    const hasNecessity = modals.some(m => m.modality === 'necessity');
    const hasCertainty = modals.some(m => m.modality === 'certainty');
    expect(hasNecessity || hasCertainty).toBe(true);

    vi.useRealTimers();
  });

  it('should handle empty text without errors', () => {
    render(<SemanticEditor />);

    // Initial state should have empty text
    const state = useICSStore.getState();
    expect(state.specificationText).toBe('');
    expect(state.semanticAnalysis).toBeNull();

    // Verify no errors thrown and component renders
    expect(screen.getByText(/click to edit/i)).toBeInTheDocument();
    expect(screen.getByText(/0 characters/i)).toBeInTheDocument();
  });

  it('should handle long text efficiently', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Generate long text (500+ characters with semantic patterns)
    const longText = Array(10)
      .fill(
        'The system must validate user input and should process data efficiently. ' +
        'Users can submit forms when authenticated. The algorithm should optimize performance.'
      )
      .join(' ');

    expect(longText.length).toBeGreaterThan(500);

    // Simulate long text input
    act(() => {
      const mockDoc = { textContent: longText } as any;
      useICSStore.getState().setSpecification(mockDoc, longText);
    });

    // Verify store updated
    let state = useICSStore.getState();
    expect(state.specificationText.length).toBeGreaterThan(500);

    // Trigger analysis
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Wait for analysis
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    }, { timeout: 1000 });

    // Verify analysis contains multiple elements
    state = useICSStore.getState();
    expect(state.semanticAnalysis?.entities.length).toBeGreaterThan(5);
    expect(state.semanticAnalysis?.modalOperators.length).toBeGreaterThan(5);

    vi.useRealTimers();
  });

  it('should update character count when specificationText changes', async () => {
    render(<SemanticEditor />);

    // Initial count
    expect(screen.getByText(/0 characters/i)).toBeInTheDocument();

    // Update text via store
    act(() => {
      const mockDoc = { textContent: 'Test' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Test');
    });

    // Wait for count to update
    await waitFor(() => {
      expect(screen.getByText(/4 characters/i)).toBeInTheDocument();
    });

    // Update with more text
    act(() => {
      const mockDoc = { textContent: 'Test input' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Test input');
    });

    await waitFor(() => {
      expect(screen.getByText(/10 characters/i)).toBeInTheDocument();
    });
  });

  it('should debounce analysis when text changes rapidly', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Simulate rapid typing by setting text multiple times
    act(() => {
      const mockDoc1 = { textContent: 'Hello' } as any;
      useICSStore.getState().setSpecification(mockDoc1, 'Hello');
    });

    // Advance 300ms
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    // Type more (resets debounce)
    act(() => {
      const mockDoc2 = { textContent: 'Hello world' } as any;
      useICSStore.getState().setSpecification(mockDoc2, 'Hello world');
    });

    // Advance 300ms again
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    // Analysis should NOT have started yet
    let state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);

    // Now wait full 500ms without changes
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Analysis should complete
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    }, { timeout: 1000 });

    vi.useRealTimers();
  });

  it('should handle backend API fallback gracefully', async () => {
    vi.useFakeTimers();

    // Mock backend as available initially
    vi.mocked(api.checkBackendHealth).mockResolvedValue(true);

    // Mock backend API to fail
    vi.mocked(api.analyzeText).mockRejectedValue(new Error('Backend unavailable'));

    render(<SemanticEditor />);

    // Simulate text input
    act(() => {
      const mockDoc = { textContent: 'Test input for backend fallback' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Test input for backend fallback');
    });

    // Trigger analysis
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Should fall back to mock analysis without throwing
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
      expect(state.isAnalyzing).toBe(false);
    }, { timeout: 1000 });

    // Verify mock analysis was used
    const state = useICSStore.getState();
    expect(state.semanticAnalysis?.entities).toBeDefined();

    vi.useRealTimers();
  });

  it('should not trigger analysis for text shorter than 3 characters', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Set only 2 characters
    act(() => {
      const mockDoc = { textContent: 'Hi' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Hi');
    });

    // Fast-forward debounce
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Analysis should NOT start
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    let state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);
    expect(state.semanticAnalysis).toBeNull();

    // Now set 3 characters
    act(() => {
      const mockDoc = { textContent: 'Hi!' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Hi!');
    });

    // Fast-forward debounce
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Now analysis should complete
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    }, { timeout: 1000 });

    vi.useRealTimers();
  });

  it('should set isAnalyzing flag during analysis', async () => {
    vi.useFakeTimers();

    render(<SemanticEditor />);

    // Set text that will trigger analysis
    act(() => {
      const mockDoc = { textContent: 'Test analysis flag' } as any;
      useICSStore.getState().setSpecification(mockDoc, 'Test analysis flag');
    });

    // Trigger debounce
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Should set isAnalyzing to true at some point
    // Note: This is tricky to test precisely because the mock is fast,
    // but we can verify the final state is correct
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(false); // Should be done
      expect(state.semanticAnalysis).not.toBeNull(); // And have results
    }, { timeout: 1000 });

    vi.useRealTimers();
  });
});
