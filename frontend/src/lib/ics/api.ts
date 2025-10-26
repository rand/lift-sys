/**
 * API client for ICS backend semantic analysis
 */

import type { SemanticAnalysis } from '@/types/ics/semantic';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface AnalyzeOptions {
  includeConfidence?: boolean;
  detectHoles?: boolean;
}

export interface AnalyzeRequest {
  text: string;
  options?: AnalyzeOptions;
}

/**
 * Analyze text using backend NLP pipeline
 */
export async function analyzeText(
  text: string,
  options: AnalyzeOptions = {}
): Promise<SemanticAnalysis> {
  const response = await fetch(`${API_BASE_URL}/ics/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      options,
    } as AnalyzeRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(`Analysis failed: ${error.detail || response.statusText}`);
  }

  const data = await response.json();
  return data as SemanticAnalysis;
}

/**
 * Check if backend API is available
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/ics/health`, {
      method: 'GET',
    });
    const data = await response.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}
