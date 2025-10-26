/**
 * Zustand store for ICS (Integrated Context Studio) state
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { enableMapSet } from 'immer';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type {
  SemanticAnalysis,
  HoleDetails,
  Constraint,
  LayoutConfig,
  PanelVisibility,
  ConstraintPropagationEvent,
} from '@/types/ics/semantic';

// Enable Map and Set support in Immer
enableMapSet();

interface ICSStore {
  // Document state
  specification: ProseMirrorNode | null;
  specificationText: string;

  // Semantic analysis
  semanticAnalysis: SemanticAnalysis | null;
  isAnalyzing: boolean;

  // Holes & constraints
  holes: Map<string, HoleDetails>;
  constraints: Map<string, Constraint>;
  selectedHole: string | null;

  // Constraint propagation tracking
  constraintPropagationHistory: ConstraintPropagationEvent[];

  // Relationship selection
  selectedRelationship: string | null;

  // UI state
  layout: LayoutConfig;
  panelVisibility: PanelVisibility;
  activeTab: 'natural-language' | 'ir' | 'code' | 'split';

  // Actions
  setSpecification: (doc: ProseMirrorNode, text: string) => void;
  updateSemanticAnalysis: (analysis: SemanticAnalysis) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  selectHole: (id: string | null) => void;
  selectRelationship: (id: string | null) => void;
  resolveHole: (id: string, refinement: unknown) => Promise<void>;
  propagateConstraints: (holeId: string) => void;
  setLayout: (layout: Partial<LayoutConfig>) => void;
  setPanelVisibility: (panel: keyof PanelVisibility, visible: boolean) => void;
  setActiveTab: (tab: 'natural-language' | 'ir' | 'code' | 'split') => void;
  clearPropagationHistory: () => void;

  // Computed getters
  unresolvedHoles: () => HoleDetails[];
  criticalPathHoles: () => HoleDetails[];
  blockedHoles: () => HoleDetails[];
}

const defaultLayout: LayoutConfig = {
  leftPanelWidth: 300,
  rightPanelWidth: 400,
  inspectorHeight: 300,
  chatHeight: 300,
  showFileExplorer: true,
  showSymbolsPanel: true,
  showInspector: true,
  showChat: true,
};

const defaultPanelVisibility: PanelVisibility = {
  fileExplorer: true,
  symbolsPanel: true,
  inspector: true,
  chat: true,
  terminal: false,
};

export const useICSStore = create<ICSStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Initial state
        specification: null,
        specificationText: '',
        semanticAnalysis: null,
        isAnalyzing: false,
        holes: new Map(),
        constraints: new Map(),
        selectedHole: null,
        constraintPropagationHistory: [],
        selectedRelationship: null,
        layout: defaultLayout,
        panelVisibility: defaultPanelVisibility,
        activeTab: 'natural-language',

        // Actions
        setSpecification: (doc, text) =>
          set((state) => {
            state.specification = doc;
            state.specificationText = text;
          }),

        updateSemanticAnalysis: (analysis) =>
          set((state) => {
            state.semanticAnalysis = analysis;

            // Update holes map
            for (const hole of analysis.typedHoles) {
              const existing = state.holes.get(hole.id);
              // Merge with existing data if available
              state.holes.set(hole.id, {
                identifier: hole.identifier,
                kind: hole.kind,
                typeHint: hole.typeHint,
                description: hole.description,
                status: hole.status,
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
                provenance: hole.provenance || {
                  source: 'unknown',
                  confidence: hole.confidence,
                  timestamp: new Date().toISOString(),
                  author: null,
                  evidenceRefs: hole.evidence || [],
                  metadata: {},
                },
                acceptanceCriteria: [],
                refinements: [],
                ...existing,
              });
            }

            // Update constraints map
            for (const constraint of analysis.constraints) {
              state.constraints.set(constraint.id, constraint);
            }
          }),

        setIsAnalyzing: (analyzing) =>
          set((state) => {
            state.isAnalyzing = analyzing;
          }),

        selectHole: (id) =>
          set((state) => {
            state.selectedHole = id;
          }),

        selectRelationship: (id) =>
          set((state) => {
            state.selectedRelationship = id;
          }),

        resolveHole: async (id, refinement) => {
          const hole = get().holes.get(id);
          if (!hole) {
            throw new Error(`Hole ${id} not found`);
          }

          // TODO: Validate refinement against constraints
          // TODO: Check for conflicts

          set((state) => {
            const h = state.holes.get(id);
            if (h) {
              h.status = 'resolved';
              // Store refinement in metadata
              h.provenance.metadata.refinement = refinement;
            }
          });

          // Propagate constraints to dependent holes
          get().propagateConstraints(id);
        },

        propagateConstraints: (holeId) => {
          const hole = get().holes.get(holeId);
          if (!hole || !hole.propagatesTo || hole.propagatesTo.length === 0) {
            return;
          }

          // Helper: Estimate solution space size based on constraints
          const estimateSolutionSpace = (constraints: string[]): number => {
            let baseSpace = 1000; // Initial solution space size

            constraints.forEach((constraintId) => {
              const constraint = get().constraints.get(constraintId);
              if (!constraint) return;

              // Reduce solution space based on constraint type
              switch (constraint.type) {
                case 'return_constraint':
                  baseSpace *= 0.6; // 40% reduction
                  break;
                case 'loop_constraint':
                  baseSpace *= 0.7; // 30% reduction
                  break;
                case 'position_constraint':
                  baseSpace *= 0.8; // 20% reduction
                  break;
              }
            });

            return Math.max(1, Math.floor(baseSpace));
          };

          set((state) => {
            for (const propagation of hole.propagatesTo) {
              const targetHole = state.holes.get(propagation.targetId);
              if (targetHole) {
                // Calculate solution space before adding constraint
                const beforeSize = estimateSolutionSpace(targetHole.constraints || []);

                // Create new constraint
                const newConstraint: Constraint = {
                  id: `constraint-${Date.now()}-${Math.random()}`,
                  type: 'return_constraint',
                  description: propagation.constraint,
                  severity: 'error',
                  appliesTo: [propagation.targetId],
                  source: `Propagated from ${holeId}`,
                  impact: propagation.impact,
                  locked: true,
                };

                state.constraints.set(newConstraint.id, newConstraint);

                // Add to hole's constraints
                if (!targetHole.constraints) {
                  targetHole.constraints = [];
                }
                targetHole.constraints.push(newConstraint.id);

                // Calculate solution space after adding constraint
                const afterSize = estimateSolutionSpace(targetHole.constraints);
                const reductionPercentage = Math.floor(
                  ((beforeSize - afterSize) / beforeSize) * 100
                );

                // Update solution space on hole
                targetHole.solutionSpace = {
                  before: `~${beforeSize} options`,
                  after: `~${afterSize} options`,
                  reduction: reductionPercentage,
                  remainingOptions: [], // TODO: Generate actual options
                };

                // Create propagation event
                const event: ConstraintPropagationEvent = {
                  id: `propagation-${Date.now()}-${Math.random()}`,
                  timestamp: Date.now(),
                  sourceHole: holeId,
                  targetHole: propagation.targetId,
                  addedConstraints: [newConstraint],
                  solutionSpaceReduction: {
                    before: beforeSize,
                    after: afterSize,
                    percentage: reductionPercentage,
                  },
                  status: 'completed',
                };

                // Add to history
                state.constraintPropagationHistory.push(event);
              }
            }
          });
        },

        setLayout: (newLayout) =>
          set((state) => {
            state.layout = { ...state.layout, ...newLayout };
          }),

        setPanelVisibility: (panel, visible) =>
          set((state) => {
            state.panelVisibility[panel] = visible;
          }),

        setActiveTab: (tab) =>
          set((state) => {
            state.activeTab = tab;
          }),

        clearPropagationHistory: () =>
          set((state) => {
            state.constraintPropagationHistory = [];
          }),

        // Computed getters
        unresolvedHoles: () => {
          return Array.from(get().holes.values()).filter((h) => h.status === 'unresolved');
        },

        criticalPathHoles: () => {
          return Array.from(get().holes.values()).filter((h) => h.priority === 'critical');
        },

        blockedHoles: () => {
          return Array.from(get().holes.values()).filter((h) =>
            h.blockedBy.some((dep) => get().holes.get(dep.id)?.status !== 'resolved')
          );
        },
      })),
      {
        name: 'ics-store',
        partialize: (state) => ({
          layout: state.layout,
          panelVisibility: state.panelVisibility,
          activeTab: state.activeTab,
        }),
      }
    )
  )
);
