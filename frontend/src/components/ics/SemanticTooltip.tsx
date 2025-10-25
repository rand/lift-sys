/**
 * SemanticTooltip: Hover tooltip for semantic elements
 */

import { useEffect, useState } from 'react';
import type {
  Entity,
  Constraint,
  TypedHole,
  Ambiguity,
  Contradiction,
  ModalOperator,
} from '@/types/ics/semantic';

interface SemanticTooltipProps {
  visible: boolean;
  position: { x: number; y: number };
  element: TooltipElement | null;
}

export type TooltipElement =
  | { type: 'entity'; data: Entity }
  | { type: 'constraint'; data: Constraint }
  | { type: 'hole'; data: TypedHole }
  | { type: 'ambiguity'; data: Ambiguity }
  | { type: 'contradiction'; data: Contradiction }
  | { type: 'modal'; data: ModalOperator }
  | { type: 'text'; title: string; content: string };

export function SemanticTooltip({ visible, position, element }: SemanticTooltipProps) {
  const [adjustedPosition, setAdjustedPosition] = useState(position);

  // Adjust position to keep tooltip on screen
  useEffect(() => {
    if (!visible) return;

    const offset = 10;
    let x = position.x + offset;
    let y = position.y + offset;

    // Simple bounds checking (can be improved with actual tooltip dimensions)
    if (x + 300 > window.innerWidth) {
      x = position.x - 310; // Show to the left instead
    }
    if (y + 200 > window.innerHeight) {
      y = position.y - 210; // Show above instead
    }

    setAdjustedPosition({ x, y });
  }, [visible, position]);

  if (!visible || !element) {
    return null;
  }

  return (
    <div
      className="semantic-tooltip"
      style={{
        position: 'fixed',
        top: `${adjustedPosition.y}px`,
        left: `${adjustedPosition.x}px`,
        zIndex: 9999,
      }}
    >
      {element.type === 'entity' && <EntityTooltip entity={element.data} />}
      {element.type === 'constraint' && <ConstraintTooltip constraint={element.data} />}
      {element.type === 'hole' && <HoleTooltip hole={element.data} />}
      {element.type === 'ambiguity' && <AmbiguityTooltip ambiguity={element.data} />}
      {element.type === 'contradiction' && <ContradictionTooltip contradiction={element.data} />}
      {element.type === 'modal' && <ModalTooltip modal={element.data} />}
      {element.type === 'text' && <TextTooltip title={element.title} content={element.content} />}
    </div>
  );
}

function EntityTooltip({ entity }: { entity: Entity }) {
  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">{entity.type}</span>
        <span className="tooltip-confidence">{Math.round(entity.confidence * 100)}%</span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-label">Entity:</div>
        <div className="tooltip-value">{entity.text}</div>
        {entity.type === 'TECHNICAL' && (
          <div className="tooltip-hint">Technical term or system component</div>
        )}
        {entity.type === 'PERSON' && (
          <div className="tooltip-hint">User role or actor</div>
        )}
        {entity.type === 'ORG' && (
          <div className="tooltip-hint">Organization or group</div>
        )}
        {entity.type === 'FUNCTION' && (
          <div className="tooltip-hint">Code function or method</div>
        )}
      </div>
    </div>
  );
}

function ConstraintTooltip({ constraint }: { constraint: Constraint }) {
  const severityColor = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#dc2626',
  }[constraint.severity];

  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">{constraint.type}</span>
        <span className="tooltip-severity" style={{ color: severityColor }}>
          {constraint.severity}
        </span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-label">Constraint:</div>
        <div className="tooltip-value">{constraint.description}</div>
        {constraint.expression && (
          <div className="tooltip-expression">{constraint.expression}</div>
        )}
      </div>
    </div>
  );
}

function HoleTooltip({ hole }: { hole: TypedHole }) {
  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">{hole.kind}</span>
        <span className={`tooltip-status status-${hole.status}`}>
          {hole.status}
        </span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-label">Typed Hole:</div>
        <div className="tooltip-value">{hole.identifier}</div>
        {hole.typeHint && hole.typeHint !== 'unknown' && (
          <div className="tooltip-hint">Type: {hole.typeHint}</div>
        )}
        {hole.dependencies.blocks.length > 0 && (
          <div className="tooltip-hint">
            Blocks: {hole.dependencies.blocks.length} holes
          </div>
        )}
        {hole.dependencies.blockedBy.length > 0 && (
          <div className="tooltip-hint">
            Blocked by: {hole.dependencies.blockedBy.length} holes
          </div>
        )}
      </div>
    </div>
  );
}

function AmbiguityTooltip({ ambiguity }: { ambiguity: Ambiguity }) {
  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">Ambiguity</span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-label">Issue:</div>
        <div className="tooltip-value">{ambiguity.reason}</div>
        {ambiguity.suggestions.length > 0 && (
          <>
            <div className="tooltip-label">Suggestions:</div>
            <ul className="tooltip-list">
              {ambiguity.suggestions.map((suggestion, idx) => (
                <li key={idx}>{suggestion}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

function ContradictionTooltip({ contradiction }: { contradiction: Contradiction }) {
  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">Contradiction</span>
        <span className="tooltip-severity" style={{ color: '#ef4444' }}>
          {contradiction.severity}
        </span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-label">Conflicting statements:</div>
        <ul className="tooltip-list">
          {contradiction.conflicts.map((conflict, idx) => (
            <li key={idx}>{conflict}</li>
          ))}
        </ul>
        {contradiction.resolution && (
          <>
            <div className="tooltip-label">Resolution:</div>
            <div className="tooltip-value">{contradiction.resolution}</div>
          </>
        )}
      </div>
    </div>
  );
}

function ModalTooltip({ modal }: { modal: ModalOperator }) {
  const modalityDescriptions = {
    certainty: 'Indicates confidence or likelihood',
    possibility: 'Indicates potential or optional behavior',
    necessity: 'Indicates required or mandatory behavior',
    prohibition: 'Indicates forbidden behavior',
  };

  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">Modal: {modal.modality}</span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-value">{modal.text}</div>
        <div className="tooltip-hint">
          {modalityDescriptions[modal.modality]}
        </div>
        {modal.scope && (
          <div className="tooltip-hint">Scope: {modal.scope}</div>
        )}
      </div>
    </div>
  );
}

function TextTooltip({ title, content }: { title: string; content: string }) {
  return (
    <div className="tooltip-content">
      <div className="tooltip-header">
        <span className="tooltip-badge">{title}</span>
      </div>
      <div className="tooltip-body">
        <div className="tooltip-value">{content}</div>
      </div>
    </div>
  );
}
