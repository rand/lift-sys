export type Provider = 'anthropic' | 'openai' | 'gemini' | 'local';

export interface ProviderConfig {
  type: Provider;
  authenticated: boolean;
  capabilities: {
    streaming: boolean;
    structuredOutput: boolean;
    reasoning: boolean;
  };
  status: 'healthy' | 'degraded' | 'unavailable';
  expiresAt?: string;
}
