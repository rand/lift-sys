/**
 * Integration tests for SemanticEditor component
 *
 * Tests editor integration with Zustand store, debounced semantic analysis,
 * and decoration rendering.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SemanticEditor } from './SemanticEditor';
import { useICSStore } from '@/lib/ics/store';
import * as api from '@/lib/ics/api';
import type { SemanticAnalysis } from '@/types/ics/semantic';

// Mock the API module
vi.mock('@/lib/ics/api', () => ({
  analyzeText: vi.fn(),
  checkBackendHealth: vi.fn(),
}));

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

  it('should update specificationText in store when typing in editor', async () => {
    const user = userEvent.setup();
    render(<SemanticEditor />);

    // Find the editor element
    const editor = document.querySelector('[data-placeholder]');
    expect(editor).toBeInTheDocument();

    // Type some text
    await user.click(editor!);
    await user.keyboard('Hello world');

    // Wait for store to update
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.specificationText).toContain('Hello world');
    });
  });

  it('should trigger semantic analysis after 500ms debounce', async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    expect(editor).toBeInTheDocument();

    // Type text that will trigger analysis
    await user.click(editor!);
    await user.keyboard('The system must validate user input');

    // Store should be updated immediately
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.specificationText.length).toBeGreaterThan(0);
    });

    // Analysis should NOT have started yet
    let state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);

    // Fast-forward time by 400ms (before debounce completes)
    vi.advanceTimersByTime(400);
    state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);

    // Fast-forward remaining 100ms to trigger debounce
    vi.advanceTimersByTime(100);

    // Wait for analysis to start
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(true);
    });

    // Wait for analysis to complete (mock is synchronous but wrapped in async)
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(false);
      expect(state.semanticAnalysis).not.toBeNull();
    });

    vi.useRealTimers();
  });

  it('should update decorations when semantic analysis completes', async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);

    // Type text with detectable patterns (modal operators)
    await user.keyboard('The system must process data and should validate input');

    // Fast-forward debounce
    vi.advanceTimersByTime(500);

    // Wait for analysis to complete
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    });

    // Check that semantic analysis contains expected elements
    const state = useICSStore.getState();
    expect(state.semanticAnalysis?.modalOperators.length).toBeGreaterThan(0);
    expect(state.semanticAnalysis?.entities.length).toBeGreaterThan(0);

    // Verify decorations are applied (check for semantic classes in DOM)
    // Note: ProseMirror decorations render as spans with semantic classes
    await waitFor(() => {
      const semanticElements = document.querySelectorAll('.entity, .modal');
      expect(semanticElements.length).toBeGreaterThan(0);
    });

    vi.useRealTimers();
  });

  it('should handle empty text without errors', async () => {
    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    expect(editor).toBeInTheDocument();

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
    const user = userEvent.setup({ delay: null });

    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);

    // Generate long text (500+ characters with semantic patterns)
    const longText = Array(10)
      .fill(
        'The system must validate user input and should process data efficiently. ' +
        'Users can submit forms when authenticated. The algorithm should optimize performance.'
      )
      .join(' ');

    // Type long text
    await user.keyboard(longText);

    // Store should update
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.specificationText.length).toBeGreaterThan(500);
    });

    // Measure time for analysis
    const startTime = performance.now();

    // Trigger debounce
    vi.advanceTimersByTime(500);

    // Wait for analysis
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
    });

    const endTime = performance.now();
    const analysisTime = endTime - startTime;

    // Analysis should complete in reasonable time (< 1000ms for mock)
    // This is a sanity check - real performance testing would be more sophisticated
    expect(analysisTime).toBeLessThan(1000);

    // Verify analysis contains multiple elements
    const state = useICSStore.getState();
    expect(state.semanticAnalysis?.entities.length).toBeGreaterThan(5);
    expect(state.semanticAnalysis?.modalOperators.length).toBeGreaterThan(5);

    vi.useRealTimers();
  });

  it('should update character count as user types', async () => {
    const user = userEvent.setup();
    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);

    // Initial count
    expect(screen.getByText(/0 characters/i)).toBeInTheDocument();

    // Type text
    await user.keyboard('Test');

    // Wait for count to update
    await waitFor(() => {
      expect(screen.getByText(/4 characters/i)).toBeInTheDocument();
    });

    // Type more text
    await user.keyboard(' input');

    await waitFor(() => {
      expect(screen.getByText(/10 characters/i)).toBeInTheDocument();
    });
  });

  it('should show editing state when focused', async () => {
    const user = userEvent.setup();
    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');

    // Initially not focused
    expect(screen.getByText(/click to edit/i)).toBeInTheDocument();

    // Focus editor
    await user.click(editor!);

    // Should show editing state
    await waitFor(() => {
      expect(screen.getByText(/editing\.\.\./i)).toBeInTheDocument();
    });

    // Blur editor
    await user.tab();

    // Should return to unfocused state
    await waitFor(() => {
      expect(screen.getByText(/click to edit/i)).toBeInTheDocument();
    });
  });

  it('should debounce analysis when typing continuously', async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);

    // Type first word
    await user.keyboard('Hello');

    // Advance 300ms (not enough to trigger)
    vi.advanceTimersByTime(300);

    // Type more (resets debounce)
    await user.keyboard(' world');

    // Advance 300ms again
    vi.advanceTimersByTime(300);

    // Analysis should NOT have started yet
    let state = useICSStore.getState();
    expect(state.isAnalyzing).toBe(false);

    // Now wait full 500ms without typing
    vi.advanceTimersByTime(500);

    // Analysis should start
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(true);
    });

    vi.useRealTimers();
  });

  it('should handle backend API fallback gracefully', async () => {
    vi.useFakeTimers();

    // Mock backend as available initially
    vi.mocked(api.checkBackendHealth).mockResolvedValue(true);

    // Mock backend API to fail
    vi.mocked(api.analyzeText).mockRejectedValue(new Error('Backend unavailable'));

    const user = userEvent.setup({ delay: null });
    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);
    await user.keyboard('Test input for backend fallback');

    // Trigger analysis
    vi.advanceTimersByTime(500);

    // Should fall back to mock analysis without throwing
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).not.toBeNull();
      expect(state.isAnalyzing).toBe(false);
    });

    // Verify mock analysis was used (should have some entities/modals)
    const state = useICSStore.getState();
    expect(state.semanticAnalysis?.entities).toBeDefined();

    vi.useRealTimers();
  });

  it('should not trigger analysis for text shorter than 3 characters', async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<SemanticEditor />);

    const editor = document.querySelector('[data-placeholder]');
    await user.click(editor!);

    // Type only 2 characters
    await user.keyboard('Hi');

    // Fast-forward debounce
    vi.advanceTimersByTime(500);

    // Analysis should NOT start
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(false);
      expect(state.semanticAnalysis).toBeNull();
    });

    // Type one more character (now 3 total)
    await user.keyboard('!');

    // Fast-forward debounce
    vi.advanceTimersByTime(500);

    // Now analysis should start
    await waitFor(() => {
      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(true);
    });

    vi.useRealTimers();
  });
});
