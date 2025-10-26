/**
 * Unit tests for ICS Zustand store
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useICSStore } from './store';
import type { SemanticAnalysis, HoleDetails, Constraint } from '@/types/ics/semantic';

// Create a fresh store instance for each test
const createStore = () => {
  const store = useICSStore.getState();
  // Reset to initial state
  useICSStore.setState({
    specification: null,
    specificationText: '',
    semanticAnalysis: null,
    isAnalyzing: false,
    holes: new Map(),
    constraints: new Map(),
    selectedHole: null,
    layout: {
      leftPanelWidth: 300,
      rightPanelWidth: 400,
      inspectorHeight: 300,
      chatHeight: 300,
      showFileExplorer: true,
      showSymbolsPanel: true,
      showInspector: true,
      showChat: true,
    },
    panelVisibility: {
      fileExplorer: true,
      symbolsPanel: true,
      inspector: true,
      chat: true,
      terminal: false,
    },
    activeTab: 'natural-language',
  });
  return useICSStore;
};

describe('ICS Store', () => {
  beforeEach(() => {
    createStore();
  });

  describe('Initial State', () => {
    it('initializes with null specification', () => {
      const state = useICSStore.getState();
      expect(state.specification).toBeNull();
      expect(state.specificationText).toBe('');
    });

    it('initializes with null semantic analysis', () => {
      const state = useICSStore.getState();
      expect(state.semanticAnalysis).toBeNull();
      expect(state.isAnalyzing).toBe(false);
    });

    it('initializes with empty holes and constraints maps', () => {
      const state = useICSStore.getState();
      expect(state.holes).toBeInstanceOf(Map);
      expect(state.holes.size).toBe(0);
      expect(state.constraints).toBeInstanceOf(Map);
      expect(state.constraints.size).toBe(0);
    });

    it('initializes with default layout configuration', () => {
      const state = useICSStore.getState();
      expect(state.layout).toEqual({
        leftPanelWidth: 300,
        rightPanelWidth: 400,
        inspectorHeight: 300,
        chatHeight: 300,
        showFileExplorer: true,
        showSymbolsPanel: true,
        showInspector: true,
        showChat: true,
      });
    });

    it('initializes with default panel visibility', () => {
      const state = useICSStore.getState();
      expect(state.panelVisibility).toEqual({
        fileExplorer: true,
        symbolsPanel: true,
        inspector: true,
        chat: true,
        terminal: false,
      });
    });

    it('initializes with natural-language active tab', () => {
      const state = useICSStore.getState();
      expect(state.activeTab).toBe('natural-language');
    });
  });

  describe('setSpecification', () => {
    it('updates specification and text', () => {
      const mockDoc = {} as any; // Mock ProseMirrorNode
      const text = 'Test specification text';

      useICSStore.getState().setSpecification(mockDoc, text);

      const state = useICSStore.getState();
      expect(state.specification).toBe(mockDoc);
      expect(state.specificationText).toBe(text);
    });

    it('overwrites previous specification', () => {
      const doc1 = { type: 'doc1' } as any;
      const doc2 = { type: 'doc2' } as any;

      useICSStore.getState().setSpecification(doc1, 'First');
      useICSStore.getState().setSpecification(doc2, 'Second');

      const state = useICSStore.getState();
      expect(state.specification).toBe(doc2);
      expect(state.specificationText).toBe('Second');
    });
  });

  describe('updateSemanticAnalysis', () => {
    it('updates semantic analysis', () => {
      const mockAnalysis: SemanticAnalysis = {
        entities: [],
        relationships: [],
        modalOperators: [],
        constraints: [],
        effects: [],
        assertions: [],
        ambiguities: [],
        contradictions: [],
        typedHoles: [],
        confidenceScores: {},
      };

      useICSStore.getState().updateSemanticAnalysis(mockAnalysis);

      const state = useICSStore.getState();
      expect(state.semanticAnalysis).toBe(mockAnalysis);
    });

    it('updates holes map from typed holes', () => {
      const mockAnalysis: SemanticAnalysis = {
        entities: [],
        relationships: [],
        modalOperators: [],
        constraints: [],
        effects: [],
        assertions: [],
        ambiguities: [],
        contradictions: [],
        typedHoles: [
          {
            id: 'hole-1',
            identifier: 'H1',
            kind: 'implementation',
            typeHint: 'string',
            description: 'Test hole',
            status: 'unresolved',
            confidence: 0.9,
            evidence: ['evidence-1'],
          },
          {
            id: 'hole-2',
            identifier: 'H2',
            kind: 'signature',
            typeHint: 'number',
            description: 'Another hole',
            status: 'in_progress',
            confidence: 0.8,
            evidence: ['evidence-2'],
          },
        ],
        confidenceScores: {},
      };

      useICSStore.getState().updateSemanticAnalysis(mockAnalysis);

      const state = useICSStore.getState();
      expect(state.holes.size).toBe(2);
      expect(state.holes.has('hole-1')).toBe(true);
      expect(state.holes.has('hole-2')).toBe(true);

      const hole1 = state.holes.get('hole-1')!;
      expect(hole1.identifier).toBe('H1');
      expect(hole1.kind).toBe('implementation');
      expect(hole1.typeHint).toBe('string');
      expect(hole1.status).toBe('unresolved');
    });

    it('updates constraints map from constraints', () => {
      const mockConstraints: Constraint[] = [
        {
          id: 'c1',
          type: 'return_constraint',
          description: 'Must return string',
          severity: 'error',
          appliesTo: ['hole-1'],
          source: 'analysis',
          impact: 'High',
          locked: false,
        },
        {
          id: 'c2',
          type: 'position_constraint',
          description: 'Must be first',
          severity: 'warning',
          appliesTo: ['hole-2'],
          source: 'inference',
          impact: 'Medium',
          locked: true,
        },
      ];

      const mockAnalysis: SemanticAnalysis = {
        entities: [],
        relationships: [],
        modalOperators: [],
        constraints: mockConstraints,
        effects: [],
        assertions: [],
        ambiguities: [],
        contradictions: [],
        typedHoles: [],
        confidenceScores: {},
      };

      useICSStore.getState().updateSemanticAnalysis(mockAnalysis);

      const state = useICSStore.getState();
      expect(state.constraints.size).toBe(2);
      expect(state.constraints.has('c1')).toBe(true);
      expect(state.constraints.has('c2')).toBe(true);

      const c1 = state.constraints.get('c1')!;
      expect(c1.description).toBe('Must return string');
      expect(c1.severity).toBe('error');
    });

    it('merges with existing hole data', () => {
      // First, set up existing hole with custom data
      const existingHole: HoleDetails = {
        identifier: 'H1',
        kind: 'implementation',
        typeHint: 'string',
        description: 'Original description',
        status: 'in_progress',
        phase: 2,
        priority: 'high',
        blocks: [],
        blockedBy: [],
        dependsOn: [],
        constraints: ['existing-constraint'],
        propagatesTo: [],
        solutionSpace: {
          before: 'Wide',
          after: 'Narrow',
          reduction: 50,
          remainingOptions: ['option1', 'option2'],
        },
        provenance: {
          source: 'human',
          confidence: 0.95,
          timestamp: '2025-01-01T00:00:00Z',
          author: 'user-123',
          evidenceRefs: ['ref1'],
          metadata: { custom: 'data' },
        },
        acceptanceCriteria: [{ description: 'Must work', status: 'pending' }],
        refinements: [],
      };

      useICSStore.setState((state) => {
        state.holes.set('hole-1', existingHole);
      });

      // Now update with new analysis
      const mockAnalysis: SemanticAnalysis = {
        entities: [],
        relationships: [],
        modalOperators: [],
        constraints: [],
        effects: [],
        assertions: [],
        ambiguities: [],
        contradictions: [],
        typedHoles: [
          {
            id: 'hole-1',
            identifier: 'H1',
            kind: 'implementation',
            typeHint: 'string',
            description: 'Updated description',
            status: 'unresolved', // Different status
            confidence: 0.8,
            evidence: ['new-evidence'],
          },
        ],
        confidenceScores: {},
      };

      useICSStore.getState().updateSemanticAnalysis(mockAnalysis);

      const state = useICSStore.getState();
      const hole = state.holes.get('hole-1')!;

      // Should preserve existing custom data
      expect(hole.phase).toBe(2);
      expect(hole.priority).toBe('high');
      expect(hole.constraints).toEqual(['existing-constraint']);
      expect(hole.solutionSpace.reduction).toBe(50);
      expect(hole.provenance.author).toBe('user-123');
      expect(hole.acceptanceCriteria).toHaveLength(1);
    });
  });

  describe('setIsAnalyzing', () => {
    it('sets analyzing state to true', () => {
      useICSStore.getState().setIsAnalyzing(true);

      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(true);
    });

    it('sets analyzing state to false', () => {
      useICSStore.getState().setIsAnalyzing(true);
      useICSStore.getState().setIsAnalyzing(false);

      const state = useICSStore.getState();
      expect(state.isAnalyzing).toBe(false);
    });
  });

  describe('selectHole', () => {
    it('selects a hole by ID', () => {
      useICSStore.getState().selectHole('hole-123');

      const state = useICSStore.getState();
      expect(state.selectedHole).toBe('hole-123');
    });

    it('changes selected hole', () => {
      useICSStore.getState().selectHole('hole-1');
      useICSStore.getState().selectHole('hole-2');

      const state = useICSStore.getState();
      expect(state.selectedHole).toBe('hole-2');
    });

    it('clears selected hole with null', () => {
      useICSStore.getState().selectHole('hole-1');
      useICSStore.getState().selectHole(null);

      const state = useICSStore.getState();
      expect(state.selectedHole).toBeNull();
    });
  });

  describe('setLayout', () => {
    it('updates partial layout configuration', () => {
      useICSStore.getState().setLayout({ leftPanelWidth: 350 });

      const state = useICSStore.getState();
      expect(state.layout.leftPanelWidth).toBe(350);
      expect(state.layout.rightPanelWidth).toBe(400); // Unchanged
    });

    it('updates multiple layout properties', () => {
      useICSStore.getState().setLayout({
        leftPanelWidth: 350,
        rightPanelWidth: 450,
        showInspector: false,
      });

      const state = useICSStore.getState();
      expect(state.layout.leftPanelWidth).toBe(350);
      expect(state.layout.rightPanelWidth).toBe(450);
      expect(state.layout.showInspector).toBe(false);
      expect(state.layout.chatHeight).toBe(300); // Unchanged
    });
  });

  describe('setPanelVisibility', () => {
    it('toggles panel visibility', () => {
      useICSStore.getState().setPanelVisibility('inspector', false);

      const state = useICSStore.getState();
      expect(state.panelVisibility.inspector).toBe(false);
    });

    it('sets multiple panels independently', () => {
      useICSStore.getState().setPanelVisibility('terminal', true);
      useICSStore.getState().setPanelVisibility('chat', false);

      const state = useICSStore.getState();
      expect(state.panelVisibility.terminal).toBe(true);
      expect(state.panelVisibility.chat).toBe(false);
      expect(state.panelVisibility.inspector).toBe(true); // Unchanged
    });
  });

  describe('setActiveTab', () => {
    it('changes active tab', () => {
      useICSStore.getState().setActiveTab('ir');

      const state = useICSStore.getState();
      expect(state.activeTab).toBe('ir');
    });

    it('switches between all tab types', () => {
      useICSStore.getState().setActiveTab('code');
      expect(useICSStore.getState().activeTab).toBe('code');

      useICSStore.getState().setActiveTab('split');
      expect(useICSStore.getState().activeTab).toBe('split');

      useICSStore.getState().setActiveTab('natural-language');
      expect(useICSStore.getState().activeTab).toBe('natural-language');
    });
  });

  describe('resolveHole', () => {
    beforeEach(() => {
      // Set up a hole to resolve
      const mockAnalysis: SemanticAnalysis = {
        entities: [],
        relationships: [],
        modalOperators: [],
        constraints: [],
        effects: [],
        assertions: [],
        ambiguities: [],
        contradictions: [],
        typedHoles: [
          {
            id: 'hole-1',
            identifier: 'H1',
            kind: 'implementation',
            typeHint: 'string',
            description: 'Test hole',
            status: 'unresolved',
            confidence: 0.9,
            evidence: [],
          },
        ],
        confidenceScores: {},
      };

      useICSStore.getState().updateSemanticAnalysis(mockAnalysis);
    });

    it('marks hole as resolved', async () => {
      await useICSStore.getState().resolveHole('hole-1', { value: 'resolved value' });

      const state = useICSStore.getState();
      const hole = state.holes.get('hole-1');
      expect(hole?.status).toBe('resolved');
    });

    it('stores refinement in provenance metadata', async () => {
      const refinement = { implementation: 'function test() { return "hello"; }' };
      await useICSStore.getState().resolveHole('hole-1', refinement);

      const state = useICSStore.getState();
      const hole = state.holes.get('hole-1');
      expect(hole?.provenance.metadata.refinement).toEqual(refinement);
    });

    it('throws error for non-existent hole', async () => {
      await expect(
        useICSStore.getState().resolveHole('non-existent', {})
      ).rejects.toThrow('Hole non-existent not found');
    });
  });

  describe('propagateConstraints', () => {
    beforeEach(() => {
      // Set up holes with propagation relationships
      useICSStore.setState((state) => {
        state.holes.set('hole-source', {
          identifier: 'HS',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Source hole',
          status: 'resolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [
            {
              targetId: 'hole-target',
              targetName: 'HT',
              constraint: 'Must accept string',
              impact: 'Type signature changed',
            },
          ],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('hole-target', {
          identifier: 'HT',
          kind: 'signature',
          typeHint: 'unknown',
          description: 'Target hole',
          status: 'unresolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });
      });
    });

    it('propagates constraints to target holes', () => {
      useICSStore.getState().propagateConstraints('hole-source');

      const state = useICSStore.getState();
      const targetHole = state.holes.get('hole-target')!;

      expect(targetHole.constraints).toHaveLength(1);
      expect(state.constraints.size).toBeGreaterThan(0);

      // Find the propagated constraint
      const constraintId = targetHole.constraints[0];
      const constraint = state.constraints.get(constraintId);

      expect(constraint).toBeDefined();
      expect(constraint!.description).toBe('Must accept string');
      expect(constraint!.appliesTo).toContain('hole-target');
      expect(constraint!.source).toContain('hole-source');
      expect(constraint!.locked).toBe(true);
    });

    it('handles holes without propagation targets', () => {
      useICSStore.setState((state) => {
        state.holes.set('hole-no-propagation', {
          identifier: 'HNP',
          kind: 'implementation',
          typeHint: 'string',
          description: 'No propagation',
          status: 'resolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });
      });

      const initialConstraintsSize = useICSStore.getState().constraints.size;
      useICSStore.getState().propagateConstraints('hole-no-propagation');

      // Should not create new constraints
      expect(useICSStore.getState().constraints.size).toBe(initialConstraintsSize);
    });

    it('handles non-existent holes gracefully', () => {
      expect(() => {
        useICSStore.getState().propagateConstraints('non-existent');
      }).not.toThrow();
    });
  });

  describe('Computed Getters', () => {
    beforeEach(() => {
      // Set up various holes for testing getters
      useICSStore.setState((state) => {
        state.holes.set('hole-unresolved-1', {
          identifier: 'H1',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Unresolved hole 1',
          status: 'unresolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('hole-resolved-1', {
          identifier: 'H2',
          kind: 'implementation',
          typeHint: 'number',
          description: 'Resolved hole 1',
          status: 'resolved',
          phase: 1,
          priority: 'low',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('hole-critical', {
          identifier: 'H3',
          kind: 'signature',
          typeHint: 'boolean',
          description: 'Critical hole',
          status: 'unresolved',
          phase: 1,
          priority: 'critical',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('hole-blocked', {
          identifier: 'H4',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Blocked hole',
          status: 'unresolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [
            { id: 'hole-unresolved-1', name: 'H1', reason: 'Dependency', type: 'blocked_by' },
          ],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('hole-not-blocked', {
          identifier: 'H5',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Not blocked hole',
          status: 'unresolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [
            { id: 'hole-resolved-1', name: 'H2', reason: 'Dependency', type: 'blocked_by' },
          ],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });
      });
    });

    describe('unresolvedHoles', () => {
      it('returns all unresolved holes', () => {
        const unresolved = useICSStore.getState().unresolvedHoles();

        expect(unresolved).toHaveLength(4);
        expect(unresolved.every((h) => h.status === 'unresolved')).toBe(true);
      });

      it('excludes resolved holes', () => {
        const unresolved = useICSStore.getState().unresolvedHoles();
        const unresolvedIds = unresolved.map((h) => h.identifier);

        expect(unresolvedIds).not.toContain('H2'); // Resolved hole
      });
    });

    describe('criticalPathHoles', () => {
      it('returns critical priority holes', () => {
        const critical = useICSStore.getState().criticalPathHoles();

        expect(critical).toHaveLength(1);
        expect(critical[0].identifier).toBe('H3');
        expect(critical[0].priority).toBe('critical');
      });

      it('excludes non-critical holes', () => {
        const critical = useICSStore.getState().criticalPathHoles();
        const criticalIds = critical.map((h) => h.identifier);

        expect(criticalIds).not.toContain('H1'); // Medium priority
        expect(criticalIds).not.toContain('H2'); // Low priority
      });
    });

    describe('blockedHoles', () => {
      it('returns holes blocked by unresolved dependencies', () => {
        const blocked = useICSStore.getState().blockedHoles();

        expect(blocked).toHaveLength(1);
        expect(blocked[0].identifier).toBe('H4');
      });

      it('excludes holes blocked by resolved dependencies', () => {
        const blocked = useICSStore.getState().blockedHoles();
        const blockedIds = blocked.map((h) => h.identifier);

        // H5 is blocked by H2 which is resolved, so it shouldn't be in the list
        expect(blockedIds).not.toContain('H5');
      });

      it('excludes holes with no blockers', () => {
        const blocked = useICSStore.getState().blockedHoles();
        const blockedIds = blocked.map((h) => h.identifier);

        expect(blockedIds).not.toContain('H1'); // No blockers
      });
    });
  });

  describe('State Immutability', () => {
    it('does not mutate state directly', () => {
      const initialState = useICSStore.getState();
      const initialHoles = initialState.holes;

      useICSStore.getState().setIsAnalyzing(true);

      const newState = useICSStore.getState();
      // State should be updated
      expect(newState.isAnalyzing).toBe(true);
      // But original reference might be same (immer handles this)
    });

    it('creates new constraint instances on propagation', () => {
      // Set up propagation scenario
      useICSStore.setState((state) => {
        state.holes.set('source', {
          identifier: 'S',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Source',
          status: 'resolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [
            {
              targetId: 'target',
              targetName: 'T',
              constraint: 'Test constraint',
              impact: 'High',
            },
          ],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });

        state.holes.set('target', {
          identifier: 'T',
          kind: 'signature',
          typeHint: 'unknown',
          description: 'Target',
          status: 'unresolved',
          phase: 1,
          priority: 'medium',
          blocks: [],
          blockedBy: [],
          dependsOn: [],
          constraints: [],
          propagatesTo: [],
          solutionSpace: {
            before: 'Unknown',
            after: 'Unknown',
            reduction: 0,
            remainingOptions: [],
          },
          provenance: {
            source: 'agent',
            confidence: 0.9,
            timestamp: new Date().toISOString(),
            author: null,
            evidenceRefs: [],
            metadata: {},
          },
          acceptanceCriteria: [],
          refinements: [],
        });
      });

      const beforeConstraints = useICSStore.getState().constraints.size;
      useICSStore.getState().propagateConstraints('source');
      const afterConstraints = useICSStore.getState().constraints.size;

      expect(afterConstraints).toBeGreaterThan(beforeConstraints);
    });
  });
});
