import React, { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '../lib/api';
import './PhoneCapture.css';

// OCR 담당과 합의한 뒤 이 숫자만 바꾸면 된다.
export const CAPTURE_CONFIG = {
  fps: 2, // 초당 전송 프레임 수
  width: 1280, // 요청 해상도 (브라우저가 가까운 값으로 맞춘다)
  height: 720,
  jpegQuality: 0.8, // 0~1
  maxBuffered: 500000, // 송신 대기 데이터(bytes)가 이만큼 쌓이면 프레임을 버린다 (지연이 쌓이지 않게)
  reconnectMs: 1500,
};

// api 가 보내는 close 코드 → 사용자에게 보여 줄 안내
const CLOSE_MESSAGES = {
  4404: 'QR이 만료되었거나 잘못되었습니다. PC 화면에서 QR을 새로 만들어 다시 스캔하세요.',
  4409: '다른 폰이 이 세션에 연결되어 연결이 종료되었습니다.',
  4410: '세션이 만료되었습니다. PC 화면에서 QR을 새로 만들어 다시 스캔하세요.',
};

export default function PhoneCapture() {
  const sid = new URLSearchParams(window.location.search).get('sid');

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const streamRef = useRef(null);
  const wakeLockRef = useRef(null);
  const stoppedRef = useRef(true); // true 면 재연결하지 않는다

  const [phase, setPhase] = useState('idle'); // idle | running | closed | error
  const [connected, setConnected] = useState(false);
  const [message, setMessage] = useState('');
  const [sent, setSent] = useState(0);
  const [skipped, setSkipped] = useState(0);

  const stopAll = useCallback(() => {
    stoppedRef.current = true;
    clearInterval(timerRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (wakeLockRef.current) {
      wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
    }
  }, []);

  // 화면을 벗어날 때 카메라와 연결을 정리한다
  useEffect(() => stopAll, [stopAll]);

  const sendFrame = useCallback(() => {
    const ws = wsRef.current;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !video || !video.videoWidth) return;
    if (ws.bufferedAmount > CAPTURE_CONFIG.maxBuffered) {
      setSkipped((n) => n + 1);
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (blob && ws.readyState === WebSocket.OPEN) {
          ws.send(blob);
          setSent((n) => n + 1);
        }
      },
      'image/jpeg',
      CAPTURE_CONFIG.jpegQuality
    );
  }, []);

  const connect = useCallback(() => {
    const ws = new WebSocket(wsUrl(`/api/ws/phone/${encodeURIComponent(sid)}`));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onerror = () => ws.close();
    ws.onclose = (e) => {
      setConnected(false);
      if (stoppedRef.current) return;
      if (CLOSE_MESSAGES[e.code]) {
        stopAll();
        setPhase('closed');
        setMessage(CLOSE_MESSAGES[e.code]);
        return;
      }
      setTimeout(() => !stoppedRef.current && connect(), CAPTURE_CONFIG.reconnectMs);
    };
    ws.onmessage = (e) => {
      try {
        if (JSON.parse(e.data).type === 'stop') {
          stopAll();
          setPhase('closed');
          setMessage('PC에서 연결을 종료했습니다.');
        }
      } catch (_) {
        /* JSON 이 아닌 메시지는 무시 */
      }
    };
  }, [sid, stopAll]);

  const start = async () => {
    setMessage('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: CAPTURE_CONFIG.width },
          height: { ideal: CAPTURE_CONFIG.height },
        },
        audio: false,
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      try {
        wakeLockRef.current = await navigator.wakeLock?.request('screen'); // 화면이 꺼지지 않게
      } catch (_) {
        /* 지원하지 않는 브라우저는 그냥 넘어간다 */
      }
      stoppedRef.current = false;
      setSent(0);
      setSkipped(0);
      setPhase('running');
      connect();
      timerRef.current = setInterval(sendFrame, 1000 / CAPTURE_CONFIG.fps);
    } catch (e) {
      stopAll();
      setPhase('error');
      setMessage(`카메라를 켤 수 없습니다: ${e.message} (주소가 https 인지, 카메라 권한을 허용했는지 확인하세요)`);
    }
  };

  if (!sid) {
    return (
      <div className="phone">
        <p className="phone-error">세션 정보가 없습니다. PC 화면의 QR 코드를 스캔해서 들어와 주세요.</p>
      </div>
    );
  }

  return (
    <div className="phone">
      <video ref={videoRef} className="phone-video" autoPlay playsInline muted />
      <canvas ref={canvasRef} hidden />

      <div className="phone-panel">
        {phase === 'running' ? (
          <>
            <p className={connected ? 'phone-ok' : 'phone-warn'}>
              {connected ? '● PC와 연결됨 — 전송 중' : '● 연결이 끊겼습니다. 다시 연결하는 중…'}
            </p>
            <p className="phone-meta">
              전송 {sent}장 · 건너뜀 {skipped}장
            </p>
            <button className="phone-btn secondary" onClick={() => { stopAll(); setPhase('idle'); }}>
              전송 중지
            </button>
          </>
        ) : (
          <>
            <button className="phone-btn" onClick={start}>
              카메라 켜고 전송 시작
            </button>
            <p className="phone-hint">폰을 거치대에 고정하고, 화면 자동 회전을 켠 상태에서 모니터를 향하게 하세요.</p>
          </>
        )}
        {message && <p className="phone-error">{message}</p>}
      </div>
    </div>
  );
}
