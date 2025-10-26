/**
 * Integration tests for ICS API client
 * Tests backend health checks and text analysis with MSW mocking
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { analyzeText, checkBackendHealth } from './api';
import type { SemanticAnalysis } from '@/types/ics/semantic';

// Mock semantic analysis response
const mockAnalysisResponse: SemanticAnalysis = {
  entities: [
    {
      id: 'entity-1',
      type: 'FUNCTION',
      text: 'calculateSum',
      from: 0,
      to: 12,
      confidence: 0.95,
    },
  ],
  relationships: [
    {
      id: 'rel-1',
      type: 'dependency',
      source: 'entity-1',
      target: 'entity-2',
      text: 'depends on',
      from: 13,
      to: 23,
      confidence: 0.85,
    },
  ],
  modalOperators: [
    {
      id: 'modal-1',
      modality: 'certainty',
      text: 'must',
      from: 24,
      to: 28,
      scope: 'return value',
    },
  ],
  constraints: [
    {
      id: 'constraint-1',
      type: 'return_constraint',
      description: 'Return value must be non-negative',
      severity: 'error',
      appliesTo: ['hole-1'],
      source: 'NLP analysis',
      impact: 'Prevents negative return values',
      locked: true,
    },
  ],
  effects: [
    {
      id: 'effect-1',
      description: 'Modifies global state',
      from: 29,
      to: 50,
      type: 'state_change',
    },
  ],
  assertions: [
    {
      id: 'assert-1',
      predicate: 'x > 0',
      from: 51,
      to: 56,
      type: 'precondition',
      rationale: 'Input must be positive',
    },
  ],
  ambiguities: [
    {
      id: 'ambig-1',
      text: 'the result',
      from: 57,
      to: 67,
      reason: 'Unclear return type',
      suggestions: ['int', 'float', 'string'],
    },
  ],
  contradictions: [
    {
      id: 'contra-1',
      text: 'must return string or number',
      from: 68,
      to: 96,
      conflicts: ['constraint-1', 'assert-1'],
      severity: 'warning',
    },
  ],
  typedHoles: [
    {
      id: 'hole-1',
      identifier: 'returnType',
      kind: 'signature',
      typeHint: 'int | float',
      description: 'Return type of calculateSum',
      status: 'unresolved',
      confidence: 0.8,
      evidence: ['Modal operator: must', 'Constraint: non-negative'],
    },
  ],
  confidenceScores: {
    overall: 0.87,
    entities: 0.92,
    relationships: 0.81,
    holes: 0.84,
  },
};

// MSW server setup
const server = setupServer(
  // Health check endpoint - healthy
  http.get('http://localhost:8000/ics/health', () => {
    return HttpResponse.json({ status: 'healthy' });
  }),

  // Analyze endpoint - success
  http.post('http://localhost:8000/ics/analyze', async ({ request }) => {
    const body = await request.json() as { text: string };

    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 50));

    return HttpResponse.json(mockAnalysisResponse);
  })
);

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

describe('ICS API Client Integration Tests', () => {
  describe('checkBackendHealth()', () => {
    it('should return true when backend is available', async () => {
      const isHealthy = await checkBackendHealth();

      expect(isHealthy).toBe(true);
    });

    it('should return false when backend is unavailable (network error)', async () => {
      // Override health endpoint to simulate network error
      server.use(
        http.get('http://localhost:8000/ics/health', () => {
          return HttpResponse.error();
        })
      );

      const isHealthy = await checkBackendHealth();

      expect(isHealthy).toBe(false);
    });

    it('should return false when backend returns unhealthy status', async () => {
      // Override health endpoint to return unhealthy
      server.use(
        http.get('http://localhost:8000/ics/health', () => {
          return HttpResponse.json({ status: 'unhealthy' });
        })
      );

      const isHealthy = await checkBackendHealth();

      expect(isHealthy).toBe(false);
    });

    it('should return false when backend returns non-JSON response', async () => {
      // Override health endpoint to return plain text
      server.use(
        http.get('http://localhost:8000/ics/health', () => {
          return new HttpResponse('Internal Server Error', { status: 500 });
        })
      );

      const isHealthy = await checkBackendHealth();

      expect(isHealthy).toBe(false);
    });
  });

  describe('analyzeText()', () => {
    it('should successfully analyze text and return semantic analysis', async () => {
      const text = 'Create a function that calculates the sum of two numbers';
      const result = await analyzeText(text);

      expect(result).toBeDefined();
      expect(result.entities).toHaveLength(1);
      expect(result.entities[0].type).toBe('FUNCTION');
      expect(result.typedHoles).toHaveLength(1);
      expect(result.typedHoles[0].kind).toBe('signature');
      expect(result.confidenceScores.overall).toBe(0.87);
    });

    it('should pass options to the backend', async () => {
      let capturedRequest: { text: string; options?: any } | null = null;

      // Override analyze endpoint to capture request
      server.use(
        http.post('http://localhost:8000/ics/analyze', async ({ request }) => {
          capturedRequest = await request.json() as any;
          return HttpResponse.json(mockAnalysisResponse);
        })
      );

      const text = 'Test text';
      const options = { includeConfidence: true, detectHoles: true };
      await analyzeText(text, options);

      expect(capturedRequest).toBeDefined();
      expect(capturedRequest?.text).toBe(text);
      expect(capturedRequest?.options).toEqual(options);
    });

    it('should handle backend timeout/error and throw', async () => {
      // Override analyze endpoint to simulate timeout
      server.use(
        http.post('http://localhost:8000/ics/analyze', () => {
          return HttpResponse.error();
        })
      );

      const text = 'Test text';

      await expect(analyzeText(text)).rejects.toThrow();
    });

    it('should handle 400 Bad Request with error details', async () => {
      // Override analyze endpoint to return 400 error
      server.use(
        http.post('http://localhost:8000/ics/analyze', () => {
          return HttpResponse.json(
            { detail: 'Invalid text: empty string not allowed' },
            { status: 400 }
          );
        })
      );

      const text = '';

      await expect(analyzeText(text)).rejects.toThrow('Analysis failed: Invalid text: empty string not allowed');
    });

    it('should handle 500 Internal Server Error', async () => {
      // Override analyze endpoint to return 500 error
      server.use(
        http.post('http://localhost:8000/ics/analyze', () => {
          return HttpResponse.json(
            { detail: 'Internal processing error' },
            { status: 500 }
          );
        })
      );

      const text = 'Test text';

      await expect(analyzeText(text)).rejects.toThrow('Analysis failed: Internal processing error');
    });

    it('should handle invalid JSON response from backend', async () => {
      // Override analyze endpoint to return malformed JSON
      server.use(
        http.post('http://localhost:8000/ics/analyze', () => {
          return new HttpResponse('Not JSON', {
            status: 500,
            headers: { 'Content-Type': 'text/plain' }
          });
        })
      );

      const text = 'Test text';

      // When JSON parsing fails, it falls back to 'Unknown error'
      await expect(analyzeText(text)).rejects.toThrow('Analysis failed: Unknown error');
    });

    it('should handle empty text gracefully', async () => {
      // Backend should reject empty text - test the error path
      server.use(
        http.post('http://localhost:8000/ics/analyze', () => {
          return HttpResponse.json(
            { detail: 'Text cannot be empty' },
            { status: 400 }
          );
        })
      );

      await expect(analyzeText('')).rejects.toThrow('Analysis failed: Text cannot be empty');
    });

    it('should return correct structure with all semantic components', async () => {
      const text = 'Function must return positive integer';
      const result = await analyzeText(text);

      // Verify structure matches SemanticAnalysis type
      expect(result).toHaveProperty('entities');
      expect(result).toHaveProperty('relationships');
      expect(result).toHaveProperty('modalOperators');
      expect(result).toHaveProperty('constraints');
      expect(result).toHaveProperty('effects');
      expect(result).toHaveProperty('assertions');
      expect(result).toHaveProperty('ambiguities');
      expect(result).toHaveProperty('contradictions');
      expect(result).toHaveProperty('typedHoles');
      expect(result).toHaveProperty('confidenceScores');

      // Verify arrays
      expect(Array.isArray(result.entities)).toBe(true);
      expect(Array.isArray(result.relationships)).toBe(true);
      expect(Array.isArray(result.modalOperators)).toBe(true);
      expect(Array.isArray(result.constraints)).toBe(true);
      expect(Array.isArray(result.effects)).toBe(true);
      expect(Array.isArray(result.assertions)).toBe(true);
      expect(Array.isArray(result.ambiguities)).toBe(true);
      expect(Array.isArray(result.contradictions)).toBe(true);
      expect(Array.isArray(result.typedHoles)).toBe(true);

      // Verify confidence scores object
      expect(typeof result.confidenceScores).toBe('object');
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long text input', async () => {
      const longText = 'A'.repeat(10000);
      const result = await analyzeText(longText);

      expect(result).toBeDefined();
      expect(result.entities).toBeDefined();
    });

    it('should handle special characters in text', async () => {
      const specialText = 'Function with symbols: @#$%^&*()[]{}';
      const result = await analyzeText(specialText);

      expect(result).toBeDefined();
    });

    it('should handle unicode characters', async () => {
      const unicodeText = '函数必须返回正整数 🚀';
      const result = await analyzeText(unicodeText);

      expect(result).toBeDefined();
    });

    it('should handle concurrent requests', async () => {
      const texts = [
        'First function',
        'Second function',
        'Third function',
      ];

      const promises = texts.map(text => analyzeText(text));
      const results = await Promise.all(promises);

      expect(results).toHaveLength(3);
      results.forEach(result => {
        expect(result).toBeDefined();
        expect(result.entities).toBeDefined();
      });
    });
  });
});
