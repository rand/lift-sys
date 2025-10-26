/**
 * ProseMirror decorations plugin for semantic highlighting
 */

import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type { SemanticAnalysis } from '@/types/ics/semantic';

export const decorationsPluginKey = new PluginKey('semanticDecorations');

/**
 * Create entity decoration
 */
function createEntityDecoration(from: number, to: number, entity: any): Decoration {
  const entityClass = `entity entity-${entity.type.toLowerCase()}`;
  const confidencePercent = Math.round(entity.confidence * 100);

  return Decoration.inline(from, to, {
    class: entityClass,
    title: `${entity.type} (${confidencePercent}% confident)`,
    'data-entity-id': entity.id,
    'data-entity-type': entity.type,
    'data-confidence': entity.confidence.toString(),
  });
}

/**
 * Create constraint decoration
 */
function createConstraintDecoration(from: number, to: number, constraint: any): Decoration {
  const constraintClass = `constraint constraint-${constraint.type} severity-${constraint.severity}`;

  return Decoration.inline(from, to, {
    class: constraintClass,
    title: constraint.description,
    'data-constraint-id': constraint.id,
    'data-constraint-type': constraint.type,
    'data-severity': constraint.severity,
  });
}

/**
 * Create ambiguity decoration
 */
function createAmbiguityDecoration(from: number, to: number, ambiguity: any): Decoration {
  return Decoration.inline(from, to, {
    class: 'ambiguity',
    title: ambiguity.reason,
    'data-ambiguity-id': ambiguity.id,
  });
}

/**
 * Create contradiction decoration
 */
function createContradictionDecoration(from: number, to: number, contradiction: any): Decoration {
  return Decoration.inline(from, to, {
    class: 'contradiction',
    title: `Contradiction: ${contradiction.conflicts.join(', ')}`,
    'data-contradiction-id': contradiction.id,
  });
}

/**
 * Create typed hole widget decoration
 */
function createHoleWidget(pos: number, hole: any): Decoration {
  return Decoration.widget(pos, () => {
    const badge = document.createElement('span');
    badge.className = `hole hole-${hole.kind} hole-${hole.status}`;
    badge.textContent = hole.identifier;
    badge.setAttribute('data-hole-id', hole.id);
    badge.setAttribute('title', `${hole.kind}: ${hole.typeHint}`);

    // Make it clickable
    badge.style.cursor = 'pointer';
    badge.addEventListener('click', (e) => {
      e.stopPropagation();
      // Dispatch custom event for hole selection
      const event = new CustomEvent('selectHole', { detail: { holeId: hole.id } });
      document.dispatchEvent(event);
    });

    return badge;
  }, {
    side: -1,
    key: `hole-${hole.id}`,
  });
}

/**
 * Create modal operator mark decoration
 */
function createModalDecoration(from: number, to: number, modal: any): Decoration {
  return Decoration.inline(from, to, {
    class: `modal modal-${modal.modality}`,
    title: `Modal: ${modal.modality}`,
    'data-modal-id': modal.id,
  });
}

/**
 * Create relationship mark decoration
 */
function createRelationshipDecoration(from: number, to: number, relationship: any): Decoration {
  return Decoration.inline(from, to, {
    class: `relationship relationship-${relationship.type}`,
    title: `Relationship: ${relationship.type}`,
    'data-relationship-id': relationship.id,
  });
}

/**
 * Build decoration set from semantic analysis
 */
export function buildDecorations(
  doc: ProseMirrorNode,
  analysis: SemanticAnalysis | null
): DecorationSet {
  if (!analysis) {
    return DecorationSet.empty;
  }

  const decorations: Decoration[] = [];

  // Add entity decorations
  for (const entity of analysis.entities) {
    if (entity.from >= 0 && entity.to <= doc.content.size) {
      decorations.push(createEntityDecoration(entity.from, entity.to, entity));
    }
  }

  // Add constraint decorations
  for (const constraint of analysis.constraints) {
    // Check if constraint has position data (from/to fields)
    if ('from' in constraint && 'to' in constraint &&
        typeof constraint.from === 'number' && typeof constraint.to === 'number' &&
        constraint.from >= 0 && constraint.to <= doc.content.size) {
      decorations.push(createConstraintDecoration(constraint.from, constraint.to, constraint));
    }
  }

  // Add ambiguity decorations
  for (const ambiguity of analysis.ambiguities) {
    if (ambiguity.from >= 0 && ambiguity.to <= doc.content.size) {
      decorations.push(createAmbiguityDecoration(ambiguity.from, ambiguity.to, ambiguity));
    }
  }

  // Add contradiction decorations
  for (const contradiction of analysis.contradictions) {
    if (contradiction.from >= 0 && contradiction.to <= doc.content.size) {
      decorations.push(createContradictionDecoration(contradiction.from, contradiction.to, contradiction));
    }
  }

  // Add typed hole widgets
  for (const hole of analysis.typedHoles) {
    if (hole.pos !== undefined && hole.pos >= 0 && hole.pos <= doc.content.size) {
      decorations.push(createHoleWidget(hole.pos, hole));
    }
  }

  // Add modal operator decorations
  for (const modal of analysis.modalOperators) {
    if (modal.from >= 0 && modal.to <= doc.content.size) {
      decorations.push(createModalDecoration(modal.from, modal.to, modal));
    }
  }

  // Add relationship decorations
  for (const relationship of analysis.relationships) {
    if (relationship.from >= 0 && relationship.to <= doc.content.size) {
      decorations.push(createRelationshipDecoration(relationship.from, relationship.to, relationship));
    }
  }

  // Sort decorations by position
  decorations.sort((a, b) => {
    const aPos = (a as any).from ?? (a as any).pos ?? 0;
    const bPos = (b as any).from ?? (b as any).pos ?? 0;
    return aPos - bPos;
  });

  return DecorationSet.create(doc, decorations);
}

/**
 * Create ProseMirror plugin for semantic decorations
 */
export function createDecorationsPlugin(getAnalysis: () => SemanticAnalysis | null) {
  return new Plugin({
    key: decorationsPluginKey,

    state: {
      init(_, state) {
        return buildDecorations(state.doc, getAnalysis());
      },

      apply(tr, decorationSet, oldState, newState) {
        // Check if semantic analysis was provided in transaction metadata
        const analysis = tr.getMeta('semanticAnalysis');

        if (analysis !== undefined) {
          // Rebuild decorations with new analysis
          return buildDecorations(newState.doc, analysis);
        }

        // If document changed, map existing decorations to new positions
        if (tr.docChanged) {
          return decorationSet.map(tr.mapping, newState.doc);
        }

        // Otherwise, return existing decorations unchanged
        return decorationSet;
      },
    },

    props: {
      decorations(state) {
        return this.getState(state);
      },
    },
  });
}
