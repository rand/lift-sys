/**
 * Mock semantic analysis generator for testing
 */

import type { SemanticAnalysis } from '@/types/ics/semantic';

/**
 * Generate mock semantic analysis based on text content
 */
export function generateMockAnalysis(text: string): SemanticAnalysis {
  const entities = [];
  const relationships = [];
  const modalOperators = [];
  const constraints = [];
  const effects = [];
  const assertions = [];
  const ambiguities = [];
  const contradictions = [];
  const typedHoles = [];

  // Simple pattern matching for demo purposes
  // In production, this would be replaced by NLP pipeline (spaCy + HuggingFace)

  // Find entities (simple keyword matching)
  const entityPatterns = [
    { pattern: /\b(user|customer|admin|developer)\b/gi, type: 'PERSON' as const },
    { pattern: /\b(system|application|service|API|database)\b/gi, type: 'TECHNICAL' as const },
    { pattern: /\b(company|organization|team|department)\b/gi, type: 'ORG' as const },
    { pattern: /\b(function|method|class|module)\b/gi, type: 'FUNCTION' as const },
  ];

  entityPatterns.forEach((ep, idx) => {
    let match;
    while ((match = ep.pattern.exec(text)) !== null) {
      entities.push({
        id: `entity-${idx}-${match.index}`,
        type: ep.type,
        text: match[0],
        from: match.index,
        to: match.index + match[0].length,
        confidence: 0.85 + Math.random() * 0.1,
      });
    }
  });

  // Find modal operators (certainty, possibility, necessity)
  const modalPatterns = [
    { pattern: /\b(must|shall|required|mandatory)\b/gi, modality: 'necessity' as const },
    { pattern: /\b(should|ought|recommended)\b/gi, modality: 'certainty' as const },
    { pattern: /\b(may|might|could|possibly)\b/gi, modality: 'possibility' as const },
    { pattern: /\b(cannot|must not|shall not|prohibited)\b/gi, modality: 'prohibition' as const },
  ];

  modalPatterns.forEach((mp, idx) => {
    let match;
    while ((match = mp.pattern.exec(text)) !== null) {
      modalOperators.push({
        id: `modal-${idx}-${match.index}`,
        modality: mp.modality,
        text: match[0],
        from: match.index,
        to: match.index + match[0].length,
        scope: 'sentence',
      });
    }
  });

  // Find typed holes (using ??? syntax)
  const holePattern = /\?\?\?(\w+)?/g;
  let holeMatch;
  while ((holeMatch = holePattern.exec(text)) !== null) {
    const identifier = holeMatch[1] || `hole-${typedHoles.length + 1}`;
    const holeId = `hole-${typedHoles.length}`;
    typedHoles.push({
      id: holeId,
      identifier,
      kind: 'implementation',
      status: 'unresolved',
      typeHint: 'unknown',
      description: `Typed hole at position ${holeMatch.index}`,
      confidence: 0.5,
      evidence: [`Pattern match: ${holeMatch[0]}`],
      pos: holeMatch.index,
      constraints: [],
    });
    // Add confidence score for typed hole
    confidenceScores[holeId] = 0.5;
  }

  // Find ambiguities (or/and patterns, uncertain phrasing)
  const ambiguityPattern = /\b(or|and|maybe|perhaps|unclear|ambiguous)\b/gi;
  let ambMatch;
  while ((ambMatch = ambiguityPattern.exec(text)) !== null) {
    if (Math.random() > 0.7) { // Only mark some as ambiguous
      ambiguities.push({
        id: `ambiguity-${ambiguities.length}`,
        text: ambMatch[0],
        reason: 'Potential ambiguity detected',
        from: ambMatch.index,
        to: ambMatch.index + ambMatch[0].length,
        suggestions: ['Consider clarifying this statement'],
      });
    }
  }

  // Find constraints (when, if, unless patterns)
  const constraintPattern = /\b(when|if|unless|while|during|after|before)\b/gi;
  let constMatch;
  while ((constMatch = constraintPattern.exec(text)) !== null) {
    constraints.push({
      id: `constraint-${constraints.length}`,
      type: 'position_constraint',
      severity: 'warning',
      description: `Temporal constraint: ${constMatch[0]}`,
      appliesTo: [],
      source: 'text_analysis',
      impact: 'Execution order dependency',
      locked: false,
    });
  }

  // Find contradictions (not/never following positive statements - simplified)
  const contradictionPattern = /\b(but|however|although|despite|not|never)\b/gi;
  let contraMatch;
  while ((contraMatch = contradictionPattern.exec(text)) !== null) {
    if (Math.random() > 0.8) { // Rarely mark as contradictions
      contradictions.push({
        id: `contradiction-${contradictions.length}`,
        text: contraMatch[0],
        conflicts: ['Statement A', 'Statement B'],
        from: contraMatch.index,
        to: contraMatch.index + contraMatch[0].length,
        severity: 'warning',
      });
    }
  }

  // Generate confidence scores
  const confidenceScores: Record<string, number> = {};
  entities.forEach(e => confidenceScores[e.id] = e.confidence);
  typedHoles.forEach(h => confidenceScores[h.id] = 0.5);

  return {
    entities,
    relationships,
    modalOperators,
    constraints,
    effects,
    assertions,
    ambiguities,
    contradictions,
    typedHoles,
    confidenceScores,
  };
}
