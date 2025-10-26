/**
 * Unit tests for ProseMirror decorations
 */

import { describe, it, expect, vi } from 'vitest';
import { Decoration, DecorationSet } from 'prosemirror-view';
import { Schema, DOMParser as ProseMirrorDOMParser } from 'prosemirror-model';
import { schema } from 'prosemirror-schema-basic';
import { buildDecorations } from './decorations';
import type {
  SemanticAnalysis,
  Entity,
  ModalOperator,
  Constraint,
  Ambiguity,
  Contradiction,
  TypedHole,
} from '@/types/ics/semantic';

/**
 * Helper to create a minimal ProseMirror document
 */
function createDoc(text: string) {
  const div = document.createElement('div');
  div.innerHTML = `<p>${text}</p>`;
  return ProseMirrorDOMParser.fromSchema(schema).parse(div);
}

/**
 * Helper to create test semantic analysis
 */
function createTestAnalysis(overrides: Partial<SemanticAnalysis> = {}): SemanticAnalysis {
  return {
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
    ...overrides,
  };
}

describe('decorations', () => {
  describe('buildDecorations - null/empty cases', () => {
    it('returns empty DecorationSet when analysis is null', () => {
      const doc = createDoc('Test text');
      const decorations = buildDecorations(doc, null);

      expect(decorations).toBe(DecorationSet.empty);
    });

    it('returns empty DecorationSet when analysis has no elements', () => {
      const doc = createDoc('Test text');
      const analysis = createTestAnalysis();
      const decorations = buildDecorations(doc, analysis);

      // Empty analysis should produce empty decoration set
      const decos = decorations.find();
      expect(decos).toHaveLength(0);
    });
  });

  describe('Entity Decorations', () => {
    it('creates entity decoration with correct class and data attributes', () => {
      const doc = createDoc('The user logs in');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 5,
        to: 9,
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(5);
      expect(deco.to).toBe(9);
      expect(deco.type.attrs.class).toContain('entity');
      expect(deco.type.attrs.class).toContain('entity-person');
      expect(deco.type.attrs['data-entity-id']).toBe('entity-1');
      expect(deco.type.attrs['data-entity-type']).toBe('PERSON');
      expect(deco.type.attrs['data-confidence']).toBe('0.95');
      expect(deco.type.attrs.title).toContain('PERSON');
      expect(deco.type.attrs.title).toContain('95%');
    });

    it('creates different entity classes for different types', () => {
      const doc = createDoc('The system user from company');
      const entities: Entity[] = [
        {
          id: 'entity-1',
          type: 'TECHNICAL',
          text: 'system',
          from: 5,
          to: 11,
          confidence: 0.9,
        },
        {
          id: 'entity-2',
          type: 'PERSON',
          text: 'user',
          from: 12,
          to: 16,
          confidence: 0.95,
        },
        {
          id: 'entity-3',
          type: 'ORG',
          text: 'company',
          from: 22,
          to: 29,
          confidence: 0.85,
        },
      ];

      const analysis = createTestAnalysis({ entities });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(3);

      expect((decos[0] as any).type.attrs.class).toContain('entity-technical');
      expect((decos[1] as any).type.attrs.class).toContain('entity-person');
      expect((decos[2] as any).type.attrs.class).toContain('entity-org');
    });

    it('skips entities with invalid positions', () => {
      const doc = createDoc('Short');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 100, // Beyond doc size
        to: 104,
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(0);
    });

    it('handles entity at document boundaries', () => {
      const doc = createDoc('user');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 1,
        to: 5,
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);
    });
  });

  describe('Modal Operator Decorations', () => {
    it('creates modal decoration with correct class and data attributes', () => {
      const doc = createDoc('The system must authenticate');
      const modal: ModalOperator = {
        id: 'modal-1',
        modality: 'necessity',
        text: 'must',
        from: 12,
        to: 16,
        scope: 'sentence',
      };

      const analysis = createTestAnalysis({ modalOperators: [modal] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(12);
      expect(deco.to).toBe(16);
      expect(deco.type.attrs.class).toContain('modal');
      expect(deco.type.attrs.class).toContain('modal-necessity');
      expect(deco.type.attrs['data-modal-id']).toBe('modal-1');
      expect(deco.type.attrs.title).toContain('Modal: necessity');
    });

    it('creates different modal classes for different modalities', () => {
      const doc = createDoc('Must should may cannot');
      const modals: ModalOperator[] = [
        { id: 'm1', modality: 'necessity', text: 'Must', from: 1, to: 5, scope: 'sentence' },
        { id: 'm2', modality: 'certainty', text: 'should', from: 6, to: 12, scope: 'sentence' },
        { id: 'm3', modality: 'possibility', text: 'may', from: 13, to: 16, scope: 'sentence' },
        { id: 'm4', modality: 'prohibition', text: 'cannot', from: 17, to: 23, scope: 'sentence' },
      ];

      const analysis = createTestAnalysis({ modalOperators: modals });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(4);

      expect((decos[0] as any).type.attrs.class).toContain('modal-necessity');
      expect((decos[1] as any).type.attrs.class).toContain('modal-certainty');
      expect((decos[2] as any).type.attrs.class).toContain('modal-possibility');
      expect((decos[3] as any).type.attrs.class).toContain('modal-prohibition');
    });
  });

  describe('Constraint Decorations', () => {
    it('creates constraint decoration with correct class and data attributes', () => {
      const doc = createDoc('When the user logs in');
      const constraint: Constraint = {
        id: 'constraint-1',
        type: 'position_constraint',
        description: 'Temporal constraint: when',
        severity: 'warning',
        appliesTo: [],
        source: 'text_analysis',
        impact: 'Medium',
        locked: false,
        from: 1,
        to: 5,
      } as any;

      const analysis = createTestAnalysis({ constraints: [constraint] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(1);
      expect(deco.to).toBe(5);
      expect(deco.type.attrs.class).toContain('constraint');
      expect(deco.type.attrs.class).toContain('constraint-position_constraint');
      expect(deco.type.attrs.class).toContain('severity-warning');
      expect(deco.type.attrs['data-constraint-id']).toBe('constraint-1');
      expect(deco.type.attrs['data-constraint-type']).toBe('position_constraint');
      expect(deco.type.attrs['data-severity']).toBe('warning');
      expect(deco.type.attrs.title).toBe('Temporal constraint: when');
    });

    it('creates different constraint classes for different severities', () => {
      const doc = createDoc('Test constraint severity');
      const constraints: Constraint[] = [
        {
          id: 'c1',
          type: 'position_constraint',
          description: 'Warning constraint',
          severity: 'warning',
          appliesTo: [],
          source: 'text',
          impact: 'Low',
          locked: false,
          from: 1,
          to: 5,
        } as any,
        {
          id: 'c2',
          type: 'return_constraint',
          description: 'Error constraint',
          severity: 'error',
          appliesTo: [],
          source: 'text',
          impact: 'High',
          locked: false,
          from: 6,
          to: 16,
        } as any,
      ];

      const analysis = createTestAnalysis({ constraints });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(2);

      expect((decos[0] as any).type.attrs.class).toContain('severity-warning');
      expect((decos[1] as any).type.attrs.class).toContain('severity-error');
    });

    it('skips constraints without position data', () => {
      const doc = createDoc('Test constraint');
      const constraint: Constraint = {
        id: 'constraint-1',
        type: 'position_constraint',
        description: 'No position',
        severity: 'warning',
        appliesTo: [],
        source: 'text_analysis',
        impact: 'Medium',
        locked: false,
        // No from/to fields
      };

      const analysis = createTestAnalysis({ constraints: [constraint] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(0);
    });
  });

  describe('Ambiguity Decorations', () => {
    it('creates ambiguity decoration with correct class and data attributes', () => {
      const doc = createDoc('Maybe or perhaps');
      const ambiguity: Ambiguity = {
        id: 'amb-1',
        text: 'or',
        from: 7,
        to: 9,
        reason: 'Potential ambiguity detected',
        suggestions: ['Consider clarifying'],
      };

      const analysis = createTestAnalysis({ ambiguities: [ambiguity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(7);
      expect(deco.to).toBe(9);
      expect(deco.type.attrs.class).toContain('ambiguity');
      expect(deco.type.attrs['data-ambiguity-id']).toBe('amb-1');
      expect(deco.type.attrs.title).toBe('Potential ambiguity detected');
    });

    it('skips ambiguities with invalid positions', () => {
      const doc = createDoc('Short');
      const ambiguity: Ambiguity = {
        id: 'amb-1',
        text: 'or',
        from: -1, // Invalid position
        to: 5,
        reason: 'Test',
      };

      const analysis = createTestAnalysis({ ambiguities: [ambiguity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(0);
    });
  });

  describe('Contradiction Decorations', () => {
    it('creates contradiction decoration with correct class and data attributes', () => {
      const doc = createDoc('Contradictory statement');
      const contradiction: Contradiction = {
        id: 'contra-1',
        text: 'Contradictory',
        from: 1,
        to: 14,
        conflicts: ['stmt-1', 'stmt-2'],
        severity: 'critical',
      };

      const analysis = createTestAnalysis({ contradictions: [contradiction] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(1);
      expect(deco.to).toBe(14);
      expect(deco.type.attrs.class).toContain('contradiction');
      expect(deco.type.attrs['data-contradiction-id']).toBe('contra-1');
      expect(deco.type.attrs.title).toContain('Contradiction:');
      expect(deco.type.attrs.title).toContain('stmt-1');
      expect(deco.type.attrs.title).toContain('stmt-2');
    });
  });

  describe('Typed Hole Widget Decorations', () => {
    it('creates hole widget with correct class and data attributes', () => {
      const doc = createDoc('Return ???Type');
      const hole: TypedHole = {
        id: 'hole-1',
        identifier: 'Type',
        kind: 'signature',
        typeHint: 'string',
        description: 'Return type hole',
        status: 'unresolved',
        confidence: 0.5,
        evidence: ['text analysis'],
        pos: 8,
      };

      const analysis = createTestAnalysis({ typedHoles: [hole] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      // Widget decorations have a 'pos' property instead of 'from'/'to'
      expect(deco.type.spec.key).toBe('hole-hole-1');
    });

    it('creates hole widgets with different kinds and statuses', () => {
      const doc = createDoc('Test ???H1 ???H2 ???H3');
      const holes: TypedHole[] = [
        {
          id: 'h1',
          identifier: 'H1',
          kind: 'intent',
          typeHint: 'unknown',
          description: 'Intent hole',
          status: 'unresolved',
          confidence: 0.5,
          evidence: [],
          pos: 6,
        },
        {
          id: 'h2',
          identifier: 'H2',
          kind: 'implementation',
          typeHint: 'string',
          description: 'Implementation hole',
          status: 'in_progress',
          confidence: 0.7,
          evidence: [],
          pos: 10,
        },
        {
          id: 'h3',
          identifier: 'H3',
          kind: 'assertion',
          typeHint: 'boolean',
          description: 'Assertion hole',
          status: 'resolved',
          confidence: 0.9,
          evidence: [],
          pos: 14,
        },
      ];

      const analysis = createTestAnalysis({ typedHoles: holes });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(3);

      // All should be widget decorations with correct keys
      expect((decos[0] as any).type.spec.key).toBe('hole-h1');
      expect((decos[1] as any).type.spec.key).toBe('hole-h2');
      expect((decos[2] as any).type.spec.key).toBe('hole-h3');
    });

    it('creates clickable hole widget DOM element', () => {
      const doc = createDoc('Test ???Hole');
      const hole: TypedHole = {
        id: 'hole-1',
        identifier: 'Hole',
        kind: 'signature',
        typeHint: 'string',
        description: 'Test hole',
        status: 'unresolved',
        confidence: 0.5,
        evidence: [],
        pos: 6,
      };

      const analysis = createTestAnalysis({ typedHoles: [hole] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      const deco = decos[0] as any;

      // Widget decorations have a toDOM function that's a factory
      // Call it to create the element
      const element = deco.type.toDOM();

      expect(element.tagName).toBe('SPAN');
      expect(element.className).toContain('hole');
      expect(element.className).toContain('hole-signature');
      expect(element.className).toContain('hole-unresolved');
      expect(element.textContent).toBe('Hole');
      expect(element.getAttribute('data-hole-id')).toBe('hole-1');
      expect(element.getAttribute('title')).toContain('signature:');
      expect(element.getAttribute('title')).toContain('string');
      expect(element.style.cursor).toBe('pointer');
    });

    it('skips holes with undefined or invalid positions', () => {
      const doc = createDoc('Test');
      const holes: TypedHole[] = [
        {
          id: 'h1',
          identifier: 'H1',
          kind: 'intent',
          typeHint: 'unknown',
          description: 'No position',
          status: 'unresolved',
          confidence: 0.5,
          evidence: [],
          // No pos field
        },
        {
          id: 'h2',
          identifier: 'H2',
          kind: 'intent',
          typeHint: 'unknown',
          description: 'Invalid position',
          status: 'unresolved',
          confidence: 0.5,
          evidence: [],
          pos: -1,
        },
        {
          id: 'h3',
          identifier: 'H3',
          kind: 'intent',
          typeHint: 'unknown',
          description: 'Beyond doc',
          status: 'unresolved',
          confidence: 0.5,
          evidence: [],
          pos: 1000,
        },
      ];

      const analysis = createTestAnalysis({ typedHoles: holes });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(0);
    });
  });

  describe('Decoration Positioning', () => {
    it('correctly positions decorations at start of document', () => {
      const doc = createDoc('user logs in');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 1, // After opening tag
        to: 5,
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);
      expect((decos[0] as any).from).toBe(1);
      expect((decos[0] as any).to).toBe(5);
    });

    it('correctly positions decorations at end of document', () => {
      const doc = createDoc('Login user');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 7,
        to: 11,
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);
      expect((decos[0] as any).from).toBe(7);
      expect((decos[0] as any).to).toBe(11);
    });

    it('validates positions against document size', () => {
      const doc = createDoc('Small');
      const entity: Entity = {
        id: 'entity-1',
        type: 'PERSON',
        text: 'user',
        from: 1,
        to: 100, // Beyond doc size
        confidence: 0.95,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(0); // Should be filtered out
    });

    it('handles zero-width positions for widgets', () => {
      const doc = createDoc('Test ???');
      const hole: TypedHole = {
        id: 'hole-1',
        identifier: 'Hole',
        kind: 'signature',
        typeHint: 'string',
        description: 'Test',
        status: 'unresolved',
        confidence: 0.5,
        evidence: [],
        pos: 6, // Single position for widget
      };

      const analysis = createTestAnalysis({ typedHoles: [hole] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);
      // Widget has pos instead of from/to
    });
  });

  describe('Multiple Decoration Types', () => {
    it('creates multiple decoration types in same document', () => {
      const doc = createDoc('The user must login');
      const analysis = createTestAnalysis({
        entities: [
          {
            id: 'e1',
            type: 'PERSON',
            text: 'user',
            from: 5,
            to: 9,
            confidence: 0.95,
          },
        ],
        modalOperators: [
          {
            id: 'm1',
            modality: 'necessity',
            text: 'must',
            from: 10,
            to: 14,
            scope: 'sentence',
          },
        ],
      });

      const decorations = buildDecorations(doc, analysis);
      const decos = decorations.find();

      expect(decos).toHaveLength(2);

      // Check both decorations are present
      const entityDeco = decos.find((d: any) => d.from === 5) as any;
      const modalDeco = decos.find((d: any) => d.from === 10) as any;

      expect(entityDeco).toBeDefined();
      expect(modalDeco).toBeDefined();
      expect(entityDeco.type.attrs.class).toContain('entity');
      expect(modalDeco.type.attrs.class).toContain('modal');
    });

    it('sorts decorations by position', () => {
      const doc = createDoc('user system admin');
      const entities: Entity[] = [
        { id: 'e3', type: 'PERSON', text: 'admin', from: 13, to: 18, confidence: 0.9 },
        { id: 'e1', type: 'PERSON', text: 'user', from: 1, to: 5, confidence: 0.9 },
        { id: 'e2', type: 'TECHNICAL', text: 'system', from: 6, to: 12, confidence: 0.9 },
      ];

      const analysis = createTestAnalysis({ entities });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(3);

      // Should be sorted by position
      expect((decos[0] as any).from).toBe(1);
      expect((decos[1] as any).from).toBe(6);
      expect((decos[2] as any).from).toBe(13);
    });

    it('handles overlapping decorations', () => {
      const doc = createDoc('The user must authenticate');
      const analysis = createTestAnalysis({
        entities: [
          { id: 'e1', type: 'PERSON', text: 'user', from: 5, to: 9, confidence: 0.9 },
        ],
        modalOperators: [
          { id: 'm1', modality: 'necessity', text: 'must', from: 10, to: 14, scope: 'sentence' },
        ],
        ambiguities: [
          { id: 'a1', text: 'must authenticate', from: 10, to: 27, reason: 'Ambiguous requirement' },
        ],
      });

      const decorations = buildDecorations(doc, analysis);
      const decos = decorations.find();

      // All decorations should be created even if overlapping
      expect(decos).toHaveLength(3);
    });
  });

  describe('Relationship Decorations', () => {
    it('creates relationship decoration with correct class and data attributes', () => {
      const doc = createDoc('User depends on system');
      const relationship = {
        id: 'rel-1',
        type: 'dependency' as const,
        source: 'entity-1',
        target: 'entity-2',
        text: 'depends on',
        from: 6,
        to: 16,
        confidence: 0.85,
      };

      const analysis = createTestAnalysis({ relationships: [relationship] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);

      const deco = decos[0] as any;
      expect(deco.from).toBe(6);
      expect(deco.to).toBe(16);
      expect(deco.type.attrs.class).toContain('relationship');
      expect(deco.type.attrs.class).toContain('relationship-dependency');
      expect(deco.type.attrs['data-relationship-id']).toBe('rel-1');
      expect(deco.type.attrs.title).toContain('Relationship: dependency');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty document gracefully', () => {
      const doc = createDoc('');
      const analysis = createTestAnalysis({
        entities: [
          { id: 'e1', type: 'PERSON', text: 'user', from: 0, to: 4, confidence: 0.9 },
        ],
      });

      const decorations = buildDecorations(doc, analysis);
      const decos = decorations.find();

      // Should filter out decorations beyond doc size
      expect(decos).toHaveLength(0);
    });

    it('handles mixed valid and invalid positions', () => {
      const doc = createDoc('user system');
      const entities: Entity[] = [
        { id: 'e1', type: 'PERSON', text: 'user', from: 1, to: 5, confidence: 0.9 }, // Valid
        { id: 'e2', type: 'TECHNICAL', text: 'invalid', from: -1, to: 5, confidence: 0.9 }, // Invalid
        { id: 'e3', type: 'TECHNICAL', text: 'system', from: 6, to: 12, confidence: 0.9 }, // Valid
        { id: 'e4', type: 'PERSON', text: 'beyond', from: 100, to: 106, confidence: 0.9 }, // Invalid
      ];

      const analysis = createTestAnalysis({ entities });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(2); // Only valid decorations
      expect((decos[0] as any).from).toBe(1);
      expect((decos[1] as any).from).toBe(6);
    });

    it('handles decorations with same positions', () => {
      const doc = createDoc('The user must login');
      const analysis = createTestAnalysis({
        entities: [
          { id: 'e1', type: 'PERSON', text: 'user', from: 5, to: 9, confidence: 0.9 },
          { id: 'e2', type: 'PERSON', text: 'user', from: 5, to: 9, confidence: 0.8 }, // Duplicate position
        ],
      });

      const decorations = buildDecorations(doc, analysis);
      const decos = decorations.find();

      // Both should be created
      expect(decos).toHaveLength(2);
      expect((decos[0] as any).from).toBe(5);
      expect((decos[1] as any).from).toBe(5);
    });

    it('handles maximum document size correctly', () => {
      const longText = 'user '.repeat(100);
      const doc = createDoc(longText);

      const entity: Entity = {
        id: 'e1',
        type: 'PERSON',
        text: 'user',
        from: 1,
        to: 5,
        confidence: 0.9,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const decos = decorations.find();
      expect(decos).toHaveLength(1);
    });
  });

  describe('Data Attribute Accuracy', () => {
    it('includes all required data attributes for entities', () => {
      const doc = createDoc('The user');
      const entity: Entity = {
        id: 'entity-123',
        type: 'PERSON',
        text: 'user',
        from: 5,
        to: 9,
        confidence: 0.87,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const deco = decorations.find()[0] as any;
      const attrs = deco.type.attrs;

      expect(attrs['data-entity-id']).toBe('entity-123');
      expect(attrs['data-entity-type']).toBe('PERSON');
      expect(attrs['data-confidence']).toBe('0.87');
    });

    it('includes all required data attributes for constraints', () => {
      const doc = createDoc('When ready');
      const constraint: Constraint = {
        id: 'constraint-456',
        type: 'position_constraint',
        description: 'Test',
        severity: 'error',
        appliesTo: [],
        source: 'text',
        impact: 'High',
        locked: false,
        from: 1,
        to: 5,
      } as any;

      const analysis = createTestAnalysis({ constraints: [constraint] });
      const decorations = buildDecorations(doc, analysis);

      const deco = decorations.find()[0] as any;
      const attrs = deco.type.attrs;

      expect(attrs['data-constraint-id']).toBe('constraint-456');
      expect(attrs['data-constraint-type']).toBe('position_constraint');
      expect(attrs['data-severity']).toBe('error');
    });

    it('converts confidence to string for data attributes', () => {
      const doc = createDoc('user');
      const entity: Entity = {
        id: 'e1',
        type: 'PERSON',
        text: 'user',
        from: 1,
        to: 5,
        confidence: 0.123456789,
      };

      const analysis = createTestAnalysis({ entities: [entity] });
      const decorations = buildDecorations(doc, analysis);

      const deco = decorations.find()[0] as any;
      expect(typeof deco.type.attrs['data-confidence']).toBe('string');
      expect(deco.type.attrs['data-confidence']).toBe('0.123456789');
    });
  });
});
