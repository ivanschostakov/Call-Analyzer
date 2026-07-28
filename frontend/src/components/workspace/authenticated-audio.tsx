import { useEffect, useState } from 'react';
import { Play } from 'lucide-react';

import { apiFetchResponse } from '../../api/http';
import { getErrorMessage } from '../../lib/utils';
import { Button } from '../ui/button';

export function AuthenticatedAudio({
  mediaUrl,
  compact = false,
}: {
  mediaUrl: string;
  compact?: boolean;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  async function loadAudio() {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiFetchResponse(mediaUrl, { method: 'GET' });
      const blob = await response.blob();
      const nextUrl = URL.createObjectURL(blob);
      setBlobUrl((currentUrl) => {
        if (currentUrl) {
          URL.revokeObjectURL(currentUrl);
        }
        return nextUrl;
      });
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }

  if (!blobUrl) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Button variant="secondary" size={compact ? 'sm' : 'md'} onClick={loadAudio} disabled={isLoading}>
          <Play size={15} />
          {isLoading ? 'Загружаем аудио...' : 'Открыть аудио'}
        </Button>
        {error ? (
          <p style={{ margin: 0, fontSize: 12, color: '#c68181' }}>
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <audio controls preload="none" src={blobUrl} style={{ width: '100%', maxWidth: compact ? 220 : '100%' }} />
      <Button variant="ghost" size="sm" onClick={loadAudio} style={{ justifyContent: 'flex-start', paddingLeft: 0 }}>
        Обновить аудио
      </Button>
    </div>
  );
}
