import { useRef, useState, useCallback, useEffect } from 'react';

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement>;
  isReady: boolean;
  error: string | null;
  streamDropped: boolean;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  startRecording: () => void;
  stopRecording: () => Promise<Blob | null>;
  isRecording: boolean;
}

export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const isRecordingRef = useRef(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [streamDropped, setStreamDropped] = useState(false);

  const startCamera = useCallback(async () => {
    setError(null);
    setStreamDropped(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      // Detect stream drop
      stream.getTracks().forEach((track) => {
        track.addEventListener('ended', () => {
          if (isRecordingRef.current) {
            setStreamDropped(true);
            setIsRecording(false);
            isRecordingRef.current = false;
            if (
              mediaRecorderRef.current &&
              mediaRecorderRef.current.state !== 'inactive'
            ) {
              mediaRecorderRef.current.stop();
            }
          }
        });
      });

      streamRef.current = stream;

      // Attach stream to video element — retry if ref isn't mounted yet
      const attachStream = () => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch((err) => {
            console.warn('[useCamera] play() rejected (autoplay policy?):', err);
          });
          setIsReady(true);
          console.log('[useCamera] Camera stream attached successfully');
          return true;
        }
        return false;
      };

      if (!attachStream()) {
        console.warn('[useCamera] videoRef.current is null — retrying...');
        let retries = 0;
        const retryInterval = setInterval(() => {
          retries++;
          if (attachStream()) {
            clearInterval(retryInterval);
          } else if (retries >= 10) {
            clearInterval(retryInterval);
            console.error('[useCamera] Failed to attach stream after 10 retries');
            setError('Camera started but video element not ready. Please go back and try again.');
          }
        }, 100);
      }
    } catch (err) {
      console.error('[useCamera] getUserMedia failed:', err);
      setError(err instanceof Error ? err.message : 'Camera access denied');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsReady(false);
  }, []);

  const startRecording = useCallback(() => {
    if (!streamRef.current) return;

    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/mp4';

    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    recorder.start(100);
    isRecordingRef.current = true;
    setIsRecording(true);
  }, []);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        isRecordingRef.current = false;
        setIsRecording(false);
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const mimeType = recorder.mimeType;
        const blob = new Blob(chunksRef.current, { type: mimeType });
        isRecordingRef.current = false;
        setIsRecording(false);
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    videoRef,
    isReady,
    error,
    streamDropped,
    startCamera,
    stopCamera,
    startRecording,
    stopRecording,
    isRecording,
  };
}
