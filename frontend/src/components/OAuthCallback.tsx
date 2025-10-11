import { useEffect } from 'react';

export function OAuthCallback() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const provider = params.get('provider');
    const code = params.get('code');
    const state = params.get('state');

    if (provider && code && state) {
      void fetch(`/api/auth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error('OAuth callback failed');
          }
          return response.json();
        })
        .then(() => {
          window.location.replace('/');
        })
        .catch((error) => {
          console.error('Failed to process OAuth callback', error);
        });
    }
  }, []);

  return <div>Completing sign-in…</div>;
}
