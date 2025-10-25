/**
 * ProseMirror schema for semantic specification editing
 *
 * This schema defines the structure of documents in the ICS editor,
 * including semantic nodes for entities, constraints, holes, and references.
 */

import { Schema, NodeSpec, MarkSpec } from 'prosemirror-model';

// Node specifications
const nodes: Record<string, NodeSpec> = {
  doc: {
    content: 'block+',
  },

  paragraph: {
    content: 'inline*',
    group: 'block',
    parseDOM: [{ tag: 'p' }],
    toDOM() {
      return ['p', 0];
    },
  },

  heading: {
    attrs: { level: { default: 1 } },
    content: 'inline*',
    group: 'block',
    defining: true,
    parseDOM: [
      { tag: 'h1', attrs: { level: 1 } },
      { tag: 'h2', attrs: { level: 2 } },
      { tag: 'h3', attrs: { level: 3 } },
    ],
    toDOM(node) {
      return [`h${node.attrs.level}`, 0];
    },
  },

  blockquote: {
    content: 'block+',
    group: 'block',
    parseDOM: [{ tag: 'blockquote' }],
    toDOM() {
      return ['blockquote', 0];
    },
  },

  code_block: {
    content: 'text*',
    marks: '',
    group: 'block',
    code: true,
    defining: true,
    parseDOM: [{ tag: 'pre', preserveWhitespace: 'full' }],
    toDOM() {
      return ['pre', ['code', 0]];
    },
  },

  text: {
    group: 'inline',
  },

  // Semantic node: Entity (person, org, technical term, etc.)
  entity: {
    attrs: {
      entityType: { default: 'TECHNICAL' },
      entityId: { default: '' },
      confidence: { default: 1.0 },
    },
    inline: true,
    group: 'inline',
    content: 'text*',
    atom: false,
    parseDOM: [
      {
        tag: 'span.entity',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return {
            entityType: dom.getAttribute('data-entity-type'),
            entityId: dom.getAttribute('data-entity-id'),
            confidence: parseFloat(dom.getAttribute('data-confidence') || '1.0'),
          };
        },
      },
    ],
    toDOM(node) {
      return [
        'span',
        {
          class: `entity entity-${node.attrs.entityType.toLowerCase()}`,
          'data-entity-type': node.attrs.entityType,
          'data-entity-id': node.attrs.entityId,
          'data-confidence': node.attrs.confidence,
        },
        0,
      ];
    },
  },

  // Semantic node: Constraint (return, loop, position)
  constraint: {
    attrs: {
      constraintType: { default: 'return_constraint' },
      constraintId: { default: '' },
      severity: { default: 'error' },
    },
    inline: true,
    group: 'inline',
    content: 'text*',
    atom: false,
    parseDOM: [
      {
        tag: 'span.constraint',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return {
            constraintType: dom.getAttribute('data-constraint-type'),
            constraintId: dom.getAttribute('data-constraint-id'),
            severity: dom.getAttribute('data-severity'),
          };
        },
      },
    ],
    toDOM(node) {
      return [
        'span',
        {
          class: `constraint constraint-${node.attrs.constraintType} severity-${node.attrs.severity}`,
          'data-constraint-type': node.attrs.constraintType,
          'data-constraint-id': node.attrs.constraintId,
          'data-severity': node.attrs.severity,
        },
        0,
      ];
    },
  },

  // Semantic node: Typed hole
  hole: {
    attrs: {
      holeId: { default: '' },
      kind: { default: 'intent' },
      status: { default: 'unresolved' },
    },
    inline: true,
    group: 'inline',
    content: 'text*',
    atom: false,
    parseDOM: [
      {
        tag: 'span.hole',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return {
            holeId: dom.getAttribute('data-hole-id'),
            kind: dom.getAttribute('data-kind'),
            status: dom.getAttribute('data-status'),
          };
        },
      },
    ],
    toDOM(node) {
      return [
        'span',
        {
          class: `hole hole-${node.attrs.kind} hole-${node.attrs.status}`,
          'data-hole-id': node.attrs.holeId,
          'data-kind': node.attrs.kind,
          'data-status': node.attrs.status,
        },
        0,
      ];
    },
  },

  // Semantic node: Reference (#file or @symbol)
  reference: {
    attrs: {
      refType: { default: 'file' },  // 'file' or 'symbol'
      refId: { default: '' },
      refTarget: { default: '' },
    },
    inline: true,
    group: 'inline',
    content: 'text*',
    atom: false,
    parseDOM: [
      {
        tag: 'span.reference',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return {
            refType: dom.getAttribute('data-ref-type'),
            refId: dom.getAttribute('data-ref-id'),
            refTarget: dom.getAttribute('data-ref-target'),
          };
        },
      },
    ],
    toDOM(node) {
      return [
        'span',
        {
          class: `reference reference-${node.attrs.refType}`,
          'data-ref-type': node.attrs.refType,
          'data-ref-id': node.attrs.refId,
          'data-ref-target': node.attrs.refTarget,
        },
        0,
      ];
    },
  },

  hard_break: {
    inline: true,
    group: 'inline',
    selectable: false,
    parseDOM: [{ tag: 'br' }],
    toDOM() {
      return ['br'];
    },
  },
};

// Mark specifications
const marks: Record<string, MarkSpec> = {
  strong: {
    parseDOM: [
      { tag: 'strong' },
      { tag: 'b', getAttrs: (node) => (node as HTMLElement).style.fontWeight !== 'normal' && null },
      { style: 'font-weight', getAttrs: (value) => /^(bold(er)?|[5-9]\d{2,})$/.test(value as string) && null },
    ],
    toDOM() {
      return ['strong', 0];
    },
  },

  em: {
    parseDOM: [{ tag: 'i' }, { tag: 'em' }, { style: 'font-style=italic' }],
    toDOM() {
      return ['em', 0];
    },
  },

  code: {
    parseDOM: [{ tag: 'code' }],
    toDOM() {
      return ['code', 0];
    },
  },

  // Mark: Ambiguity (yellow wavy underline)
  ambiguity: {
    attrs: { reason: { default: '' } },
    parseDOM: [
      {
        tag: 'span.ambiguity',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return { reason: dom.getAttribute('data-reason') || '' };
        },
      },
    ],
    toDOM(mark) {
      return [
        'span',
        {
          class: 'ambiguity',
          'data-reason': mark.attrs.reason,
          style: 'text-decoration: wavy underline yellow;',
        },
        0,
      ];
    },
  },

  // Mark: Contradiction (red wavy underline)
  contradiction: {
    attrs: { conflicts: { default: '' } },
    parseDOM: [
      {
        tag: 'span.contradiction',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return { conflicts: dom.getAttribute('data-conflicts') || '' };
        },
      },
    ],
    toDOM(mark) {
      return [
        'span',
        {
          class: 'contradiction',
          'data-conflicts': mark.attrs.conflicts,
          style: 'text-decoration: wavy underline red;',
        },
        0,
      ];
    },
  },

  // Mark: Modal operator (must, may, should)
  modalOperator: {
    attrs: { modality: { default: 'necessity' } },
    parseDOM: [
      {
        tag: 'span.modal-operator',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return { modality: dom.getAttribute('data-modality') || 'necessity' };
        },
      },
    ],
    toDOM(mark) {
      return [
        'span',
        {
          class: `modal-operator modal-${mark.attrs.modality}`,
          'data-modality': mark.attrs.modality,
        },
        0,
      ];
    },
  },

  // Mark: Relationship (causal, temporal, etc.)
  relationship: {
    attrs: { relType: { default: 'dependency' } },
    parseDOM: [
      {
        tag: 'span.relationship',
        getAttrs(dom) {
          if (typeof dom === 'string') return false;
          return { relType: dom.getAttribute('data-rel-type') || 'dependency' };
        },
      },
    ],
    toDOM(mark) {
      return [
        'span',
        {
          class: `relationship relationship-${mark.attrs.relType}`,
          'data-rel-type': mark.attrs.relType,
        },
        0,
      ];
    },
  },
};

/**
 * Semantic specification schema
 */
export const specSchema = new Schema({ nodes, marks });
