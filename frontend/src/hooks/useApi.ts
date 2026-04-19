export const API_BASE =
  (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ??
  'http://localhost:8000';

// Module-level last error for debug panel access
let _lastApiError: string | null = null;
export function getLastApiError(): string | null {
  return _lastApiError;
}

async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  retries = 3,
): Promise<T> {
  let lastErr: unknown;
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (attempt < retries - 1) {
        await new Promise((r) => setTimeout(r, Math.pow(2, attempt) * 500));
      }
    }
  }
  const msg = lastErr instanceof Error ? lastErr.message : String(lastErr);
  _lastApiError = `[${new Date().toISOString()}] ${msg}`;
  throw lastErr;
}

export interface MotionPhase {
  time_range: string;
  action: string;
  tempo: string;
  energy: string;
}

export interface AnalysisResult {
  movement_summary: string;
  body_parts: string[];
  phases: MotionPhase[];
  camera_angle: string;
  overall_style: string;
  best_frame_timestamp: string;
  person_description: string;
  veo_prompt: string;
  frame_uri?: string;
}

export interface UploadResponse {
  video_id: string;
  gcs_uri: string;
  share_url: string;
}

export interface AvatarResponse {
  avatar_image_url: string;
}

export interface GenerateVideoResponse {
  operation_id: string;
}

export interface StatusResponse {
  status: 'processing' | 'complete' | 'failed';
  result_url?: string;
  error?: string;
}

export interface ShareResponse {
  download_url: string;
  qr_data: string;
}

export function useApi() {
  const checkHealth = async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      return res.ok;
    } catch {
      return false;
    }
  };

  const uploadVideo = async (blob: Blob): Promise<UploadResponse> => {
    return retryWithBackoff(async () => {
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return res.json() as Promise<UploadResponse>;
    });
  };

  const analyzeVideo = (
    videoId: string,
    onPhase: (text: string) => void,
  ): Promise<AnalysisResult> => {
    return retryWithBackoff(() =>
      new Promise<AnalysisResult>(async (resolve, reject) => {
        try {
          const res = await fetch(`${API_BASE}/api/analyze/${videoId}`, {
            method: 'POST',
          });
          if (!res.ok) throw new Error(`Analyze failed: ${res.status}`);

          const reader = res.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split('\n\n');
            buffer = events.pop() ?? '';

            for (const event of events) {
              const lines = event.split('\n');
              let eventType = 'message';
              let data = '';

              for (const line of lines) {
                if (line.startsWith('event:')) eventType = line.slice(6).trim();
                if (line.startsWith('data:')) data = line.slice(5).trim();
              }

              if (eventType === 'phase' && data) {
                onPhase(data);
              } else if (eventType === 'result' && data) {
                resolve(JSON.parse(data) as AnalysisResult);
              } else if (eventType === 'error' && data) {
                reject(new Error(data));
              }
            }
          }
        } catch (err) {
          reject(err);
        }
      }),
    );
  };

  const generateAvatar = async (payload: {
    video_id: string;
    avatar_style: string;
  }): Promise<AvatarResponse> => {
    return retryWithBackoff(async () => {
      const res = await fetch(`${API_BASE}/api/generate-avatar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Generate avatar failed: ${res.status}`);
      return res.json() as Promise<AvatarResponse>;
    });
  };

  const generateVideo = async (payload: {
    video_id: string;
    avatar_image_url: string;
    motion_analysis: Record<string, unknown>;
    avatar_style: string;
    location_theme: string;
  }): Promise<GenerateVideoResponse> => {
    return retryWithBackoff(async () => {
      const res = await fetch(`${API_BASE}/api/generate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`Generate video failed: ${res.status} — ${body}`);
      }
      return res.json() as Promise<GenerateVideoResponse>;
    });
  };

  const pollStatus = async (operationId: string): Promise<StatusResponse> => {
    return retryWithBackoff(async () => {
      const res = await fetch(`${API_BASE}/api/status/${operationId}`);
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`Status check failed: ${res.status} — ${body}`);
      }
      return res.json() as Promise<StatusResponse>;
    });
  };

  const getShare = async (videoId: string): Promise<ShareResponse> => {
    return retryWithBackoff(async () => {
      const res = await fetch(`${API_BASE}/api/share/${videoId}`);
      if (!res.ok) throw new Error(`Share lookup failed: ${res.status}`);
      return res.json() as Promise<ShareResponse>;
    });
  };

  return { checkHealth, uploadVideo, analyzeVideo, generateAvatar, generateVideo, pollStatus, getShare };
}
