import { useEffect, useState } from 'react';
import { Provider, ProviderConfig } from '../types/providers';

interface ProviderSelectorProps {
  onSelect?: (provider: Provider) => void;
}

export function ProviderSelector({ onSelect }: ProviderSelectorProps) {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<Provider | undefined>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void fetchProviders();
  }, []);

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/providers');
      if (!response.ok) {
        throw new Error('Failed to fetch providers');
      }
      const data = await response.json();
      setProviders(
        data.map((item: any) => ({
          type: item.type as Provider,
          authenticated: item.authenticated ?? false,
          capabilities: item.capabilities,
          status: item.status ?? 'healthy',
          expiresAt: item.expiresAt,
        }))
      );
    } catch (error) {
      console.error('Failed to load providers', error);
    } finally {
      setLoading(false);
    }
  };

  const initiateOAuth = async (provider: Provider) => {
    const response = await fetch(`/api/auth/${provider}/initiate`, { method: 'POST' });
    if (!response.ok) {
      console.error('Failed to initiate OAuth');
      return;
    }
    const data = await response.json();
    if (data.authUrl) {
      window.location.href = data.authUrl;
    }
  };

  const handleSelect = (provider: Provider) => {
    setSelectedProvider(provider);
    onSelect?.(provider);
  };

  return (
    <div className="provider-selector">
      <div className="provider-list">
        {providers.map((provider) => (
          <div
            key={provider.type}
            className={`provider-card ${selectedProvider === provider.type ? 'selected' : ''}`}
          >
            <div className="provider-header">
              <span className="provider-name">{provider.type.toUpperCase()}</span>
              <span className={`provider-status ${provider.status}`}>{provider.status}</span>
            </div>
            <div className="provider-capabilities">
              {provider.capabilities.streaming && <span className="badge">Streaming</span>}
              {provider.capabilities.structuredOutput && <span className="badge">Structured</span>}
              {provider.capabilities.reasoning && <span className="badge">Reasoning</span>}
            </div>
            {provider.expiresAt && (
              <div className="provider-expiry">Token expires {provider.expiresAt}</div>
            )}
            <div className="provider-actions">
              <button onClick={() => handleSelect(provider.type)}>Use provider</button>
              {!provider.authenticated && (
                <button onClick={() => initiateOAuth(provider.type)}>Connect</button>
              )}
            </div>
          </div>
        ))}
      </div>
      {loading && <div className="loading">Loading providers…</div>}
    </div>
  );
}
