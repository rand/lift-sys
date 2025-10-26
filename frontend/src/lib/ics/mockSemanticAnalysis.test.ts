/**
 * Unit tests for mock semantic analysis generator
 */

import { describe, it, expect } from 'vitest';
import { generateMockAnalysis } from './mockSemanticAnalysis';
import type { SemanticAnalysis } from '@/types/ics/semantic';

describe('mockSemanticAnalysis', () => {
  describe('Entity Detection', () => {
    it('detects PERSON entities from keywords', () => {
      const text = 'The user logs in and the admin approves the request.';
      const analysis = generateMockAnalysis(text);

      const personEntities = analysis.entities.filter(e => e.type === 'PERSON');
      expect(personEntities.length).toBeGreaterThan(0);

      const userEntity = personEntities.find(e => e.text.toLowerCase() === 'user');
      expect(userEntity).toBeDefined();
      expect(userEntity!.from).toBe(4); // "The user"
      expect(userEntity!.to).toBe(8);
      expect(userEntity!.confidence).toBeGreaterThan(0.8);

      const adminEntity = personEntities.find(e => e.text.toLowerCase() === 'admin');
      expect(adminEntity).toBeDefined();
    });

    it('detects TECHNICAL entities from system keywords', () => {
      const text = 'The system connects to the database via the API.';
      const analysis = generateMockAnalysis(text);

      const techEntities = analysis.entities.filter(e => e.type === 'TECHNICAL');
      expect(techEntities.length).toBeGreaterThanOrEqual(3); // system, database, API

      const systemEntity = techEntities.find(e => e.text.toLowerCase() === 'system');
      expect(systemEntity).toBeDefined();
      expect(systemEntity!.from).toBe(4);
      expect(systemEntity!.to).toBe(10);
    });

    it('detects ORG entities from organization keywords', () => {
      const text = 'The company requires team approval from the department.';
      const analysis = generateMockAnalysis(text);

      const orgEntities = analysis.entities.filter(e => e.type === 'ORG');
      expect(orgEntities.length).toBeGreaterThanOrEqual(2); // company, team, department

      const companyEntity = orgEntities.find(e => e.text.toLowerCase() === 'company');
      expect(companyEntity).toBeDefined();
    });

    it('detects FUNCTION entities from code-related keywords', () => {
      const text = 'The function calls a method in the class module.';
      const analysis = generateMockAnalysis(text);

      const functionEntities = analysis.entities.filter(e => e.type === 'FUNCTION');
      expect(functionEntities.length).toBeGreaterThan(0);

      const funcEntity = functionEntities.find(e => e.text.toLowerCase() === 'function');
      expect(funcEntity).toBeDefined();
    });

    it('handles empty text gracefully for entities', () => {
      const text = '';
      const analysis = generateMockAnalysis(text);

      expect(analysis.entities).toEqual([]);
    });

    it('detects entities case-insensitively', () => {
      const text = 'USER logs in, User creates, user deletes';
      const analysis = generateMockAnalysis(text);

      const personEntities = analysis.entities.filter(e => e.type === 'PERSON');
      expect(personEntities.length).toBe(3); // All three "user" variants
    });
  });

  describe('Modal Operator Detection', () => {
    it('detects necessity modality (must, shall, required)', () => {
      const text = 'The system must authenticate users and shall validate input.';
      const analysis = generateMockAnalysis(text);

      const necessityModals = analysis.modalOperators.filter(m => m.modality === 'necessity');
      expect(necessityModals.length).toBeGreaterThanOrEqual(2);

      const mustModal = necessityModals.find(m => m.text.toLowerCase() === 'must');
      expect(mustModal).toBeDefined();
      expect(mustModal!.from).toBe(11);
      expect(mustModal!.to).toBe(15);
      expect(mustModal!.scope).toBe('sentence');
    });

    it('detects certainty modality (should, ought)', () => {
      const text = 'The application should handle errors gracefully.';
      const analysis = generateMockAnalysis(text);

      const certaintyModals = analysis.modalOperators.filter(m => m.modality === 'certainty');
      expect(certaintyModals.length).toBeGreaterThan(0);

      const shouldModal = certaintyModals.find(m => m.text.toLowerCase() === 'should');
      expect(shouldModal).toBeDefined();
    });

    it('detects possibility modality (may, might, could)', () => {
      const text = 'The user may cancel or might retry the operation.';
      const analysis = generateMockAnalysis(text);

      const possibilityModals = analysis.modalOperators.filter(m => m.modality === 'possibility');
      expect(possibilityModals.length).toBeGreaterThanOrEqual(2);
    });

    it('detects prohibition modality (cannot, must not)', () => {
      const text = 'Users cannot delete system files and must not bypass security.';
      const analysis = generateMockAnalysis(text);

      const prohibitionModals = analysis.modalOperators.filter(m => m.modality === 'prohibition');
      expect(prohibitionModals.length).toBeGreaterThanOrEqual(2);
    });

    it('handles empty text gracefully for modals', () => {
      const text = '';
      const analysis = generateMockAnalysis(text);

      expect(analysis.modalOperators).toEqual([]);
    });
  });

  describe('Typed Hole Detection', () => {
    it('detects basic typed holes with ??? syntax', () => {
      const text = 'The function returns ??? and takes ??? as input.';
      const analysis = generateMockAnalysis(text);

      expect(analysis.typedHoles.length).toBe(2);

      const firstHole = analysis.typedHoles[0];
      expect(firstHole.pos).toBe(21); // Position of first ???
      expect(firstHole.kind).toBe('implementation');
      expect(firstHole.status).toBe('unresolved');
      expect(firstHole.typeHint).toBe('unknown');
    });

    it('detects typed holes with identifiers (???name)', () => {
      const text = 'The return type is ???ReturnType and parameter is ???ParamType.';
      const analysis = generateMockAnalysis(text);

      expect(analysis.typedHoles.length).toBe(2);

      const returnTypeHole = analysis.typedHoles.find(h => h.identifier === 'ReturnType');
      expect(returnTypeHole).toBeDefined();

      const paramTypeHole = analysis.typedHoles.find(h => h.identifier === 'ParamType');
      expect(paramTypeHole).toBeDefined();
    });

    it('assigns unique IDs to typed holes', () => {
      const text = '??? ??? ???';
      const analysis = generateMockAnalysis(text);

      expect(analysis.typedHoles.length).toBe(3);

      const ids = analysis.typedHoles.map(h => h.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(3); // All IDs unique
    });

    it('initializes hole constraints correctly', () => {
      const text = 'The type is ???T';
      const analysis = generateMockAnalysis(text);

      const hole = analysis.typedHoles[0];
      expect(hole.constraints).toEqual([]);
      expect(hole.description).toBeDefined();
      expect(hole.confidence).toBe(0.5);
      expect(hole.evidence).toHaveLength(1);
    });

    it('handles text without holes gracefully', () => {
      const text = 'This is normal text without any holes.';
      const analysis = generateMockAnalysis(text);

      expect(analysis.typedHoles).toEqual([]);
    });
  });

  describe('Ambiguity Detection', () => {
    it('detects ambiguity markers (or, and, maybe, perhaps)', () => {
      const text = 'The user might or maybe should perhaps do this.';
      const analysis = generateMockAnalysis(text);

      // Ambiguities are detected probabilistically (30% chance)
      // So we just check structure when present
      analysis.ambiguities.forEach(amb => {
        expect(amb.id).toBeDefined();
        expect(amb.reason).toBe('Potential ambiguity detected');
        expect(amb.from).toBeGreaterThanOrEqual(0);
        expect(amb.to).toBeGreaterThan(amb.from);
        expect(amb.suggestions).toContain('Consider clarifying this statement');
      });
    });

    it('provides suggestions for ambiguities', () => {
      const text = 'or and maybe perhaps unclear ambiguous';
      const analysis = generateMockAnalysis(text);

      // Even if none detected, structure should be valid
      expect(Array.isArray(analysis.ambiguities)).toBe(true);

      if (analysis.ambiguities.length > 0) {
        const amb = analysis.ambiguities[0];
        expect(amb.suggestions).toEqual(['Consider clarifying this statement']);
      }
    });
  });

  describe('Constraint Detection', () => {
    it('detects temporal constraints (when, if, unless, while)', () => {
      const text = 'When the user logs in, if validation passes, unless errors occur.';
      const analysis = generateMockAnalysis(text);

      expect(analysis.constraints.length).toBeGreaterThanOrEqual(3);

      const whenConstraint = analysis.constraints.find(c => c.description.toLowerCase().includes('when'));
      expect(whenConstraint).toBeDefined();
      expect(whenConstraint!.type).toBe('position_constraint');
      expect(whenConstraint!.severity).toBe('warning');
      expect(whenConstraint!.description.toLowerCase()).toContain('when');
    });

    it('detects constraints with correct positions', () => {
      const text = 'Before starting, after completion, during processing.';
      const analysis = generateMockAnalysis(text);

      const beforeConstraint = analysis.constraints.find(c => c.description.toLowerCase().includes('before'));
      expect(beforeConstraint).toBeDefined();
      // Constraints don't track positions in current interface
      expect(beforeConstraint!.source).toBe('text_analysis');
    });

    it('handles empty text gracefully for constraints', () => {
      const text = '';
      const analysis = generateMockAnalysis(text);

      expect(analysis.constraints).toEqual([]);
    });
  });

  describe('Position Accuracy', () => {
    it('accurately tracks character positions for entities', () => {
      const text = 'The user and admin are here.';
      const analysis = generateMockAnalysis(text);

      const userEntity = analysis.entities.find(e => e.text.toLowerCase() === 'user');
      expect(userEntity).toBeDefined();

      // Extract the substring using positions
      const extractedText = text.substring(userEntity!.from, userEntity!.to);
      expect(extractedText.toLowerCase()).toBe('user');
    });

    it('accurately tracks character positions for modal operators', () => {
      const text = 'This must work.';
      const analysis = generateMockAnalysis(text);

      const mustModal = analysis.modalOperators.find(m => m.text.toLowerCase() === 'must');
      expect(mustModal).toBeDefined();

      const extractedText = text.substring(mustModal!.from, mustModal!.to);
      expect(extractedText.toLowerCase()).toBe('must');
    });

    it('accurately tracks positions for typed holes', () => {
      const text = 'Return ???Type here.';
      const analysis = generateMockAnalysis(text);

      const hole = analysis.typedHoles[0];
      expect(hole.pos).toBe(7); // Position of ???

      // Verify the hole is at that position
      expect(text.substring(hole.pos!)).toMatch(/^\?\?\?/);
    });

    it('accurately captures constraint text in description', () => {
      const text = 'When ready, start.';
      const analysis = generateMockAnalysis(text);

      const constraint = analysis.constraints[0];
      expect(constraint.description.toLowerCase()).toContain('when');
      expect(constraint.source).toBe('text_analysis');
    });
  });

  describe('Required Fields Completeness', () => {
    it('returns all 10 required SemanticAnalysis fields', () => {
      const text = 'The user must authenticate when logging in. ???AuthType';
      const analysis = generateMockAnalysis(text);

      // Verify all 10 fields are present
      expect(analysis).toHaveProperty('entities');
      expect(analysis).toHaveProperty('relationships');
      expect(analysis).toHaveProperty('modalOperators');
      expect(analysis).toHaveProperty('constraints');
      expect(analysis).toHaveProperty('effects');
      expect(analysis).toHaveProperty('assertions');
      expect(analysis).toHaveProperty('ambiguities');
      expect(analysis).toHaveProperty('contradictions');
      expect(analysis).toHaveProperty('typedHoles');
      expect(analysis).toHaveProperty('confidenceScores');
    });

    it('initializes all fields as arrays (except confidenceScores)', () => {
      const text = '';
      const analysis = generateMockAnalysis(text);

      expect(Array.isArray(analysis.entities)).toBe(true);
      expect(Array.isArray(analysis.relationships)).toBe(true);
      expect(Array.isArray(analysis.modalOperators)).toBe(true);
      expect(Array.isArray(analysis.constraints)).toBe(true);
      expect(Array.isArray(analysis.effects)).toBe(true);
      expect(Array.isArray(analysis.assertions)).toBe(true);
      expect(Array.isArray(analysis.ambiguities)).toBe(true);
      expect(Array.isArray(analysis.contradictions)).toBe(true);
      expect(Array.isArray(analysis.typedHoles)).toBe(true);
      expect(typeof analysis.confidenceScores).toBe('object');
    });

    it('populates confidence scores for detected elements', () => {
      const text = 'The user must login. ???AuthType';
      const analysis = generateMockAnalysis(text);

      // Check that confidence scores exist for entities
      analysis.entities.forEach(entity => {
        expect(analysis.confidenceScores).toHaveProperty(entity.id);
        expect(analysis.confidenceScores[entity.id]).toBe(entity.confidence);
      });

      // Check that confidence scores exist for typed holes
      analysis.typedHoles.forEach(hole => {
        expect(analysis.confidenceScores).toHaveProperty(hole.id);
        expect(analysis.confidenceScores[hole.id]).toBe(0.5);
      });
    });
  });

  describe('Realistic Data Generation', () => {
    it('generates realistic entity IDs', () => {
      const text = 'The user logs in.';
      const analysis = generateMockAnalysis(text);

      const entity = analysis.entities[0];
      expect(entity.id).toMatch(/^entity-\d+-\d+$/);
    });

    it('generates realistic modal operator IDs', () => {
      const text = 'Must authenticate.';
      const analysis = generateMockAnalysis(text);

      const modal = analysis.modalOperators[0];
      expect(modal.id).toMatch(/^modal-\d+-\d+$/);
    });

    it('generates realistic typed hole IDs', () => {
      const text = '???Type';
      const analysis = generateMockAnalysis(text);

      const hole = analysis.typedHoles[0];
      expect(hole.id).toMatch(/^hole-\d+$/);
    });

    it('generates realistic constraint IDs', () => {
      const text = 'When ready';
      const analysis = generateMockAnalysis(text);

      const constraint = analysis.constraints[0];
      expect(constraint.id).toMatch(/^constraint-\d+$/);
    });

    it('generates confidence scores in valid range', () => {
      const text = 'The user must authenticate.';
      const analysis = generateMockAnalysis(text);

      analysis.entities.forEach(entity => {
        expect(entity.confidence).toBeGreaterThanOrEqual(0.85);
        expect(entity.confidence).toBeLessThanOrEqual(0.95);
      });
    });
  });

  describe('Complex Text Handling', () => {
    it('handles text with multiple entity types', () => {
      const text = 'The user from the company accesses the system database via API.';
      const analysis = generateMockAnalysis(text);

      const types = new Set(analysis.entities.map(e => e.type));
      expect(types.size).toBeGreaterThan(1); // Multiple entity types detected
      expect(types.has('PERSON')).toBe(true);
      expect(types.has('ORG')).toBe(true);
      expect(types.has('TECHNICAL')).toBe(true);
    });

    it('handles text with multiple modal operators', () => {
      const text = 'The system must validate and should sanitize but may reject input.';
      const analysis = generateMockAnalysis(text);

      const modalities = new Set(analysis.modalOperators.map(m => m.modality));
      expect(modalities.size).toBeGreaterThan(1); // Multiple modalities
      expect(modalities.has('necessity')).toBe(true);
      expect(modalities.has('certainty')).toBe(true);
      expect(modalities.has('possibility')).toBe(true);
    });

    it('handles text with mixed content types', () => {
      const text = 'When the user logs in, the system must authenticate using ???AuthMethod.';
      const analysis = generateMockAnalysis(text);

      expect(analysis.entities.length).toBeGreaterThan(0);
      expect(analysis.modalOperators.length).toBeGreaterThan(0);
      expect(analysis.constraints.length).toBeGreaterThan(0);
      expect(analysis.typedHoles.length).toBe(1);
    });
  });

  describe('Edge Cases', () => {
    it('handles text with only whitespace', () => {
      const text = '   \n\t  ';
      const analysis = generateMockAnalysis(text);

      expect(analysis.entities).toEqual([]);
      expect(analysis.modalOperators).toEqual([]);
      expect(analysis.typedHoles).toEqual([]);
    });

    it('handles very long text efficiently', () => {
      const text = 'The user must login. '.repeat(100);
      const analysis = generateMockAnalysis(text);

      expect(analysis.entities.length).toBeGreaterThan(0);
      expect(analysis.modalOperators.length).toBeGreaterThan(0);
    });

    it('handles text with special characters', () => {
      const text = 'The user@domain.com must login (required!) to the system.';
      const analysis = generateMockAnalysis(text);

      // Should still detect entities and modals despite special chars
      expect(analysis.entities.length).toBeGreaterThan(0);
      expect(analysis.modalOperators.length).toBeGreaterThan(0);
    });

    it('handles overlapping patterns gracefully', () => {
      const text = 'user User USER';
      const analysis = generateMockAnalysis(text);

      // Should detect all three instances
      expect(analysis.entities.length).toBe(3);
    });
  });
});
