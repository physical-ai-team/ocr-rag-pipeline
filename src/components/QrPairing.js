import React, { useCallback, useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { apiUrl, wsUrl } from '../lib/api';
import './QrPairing.css';

// 대시보드 ① "QR 카메라 연동" 패널.
// 세션을 만들고 → QR 을 보여 주고 → 폰이 연결되면 "연결됨" + 받은 프레임 수 + 최근 프레임 미리보기를 보여 준다.
// 폰이 열 주소는 현재 접속한 주소(origin)를 쓰고, REACT_APP_PUBLIC_URL 이 있으면 그 값을 우선한다.
export default function QrPairing() {
  const [session, setSession] = useState(null); // { session_id, phone_path, expires_in }
  const [status, setStatus] = useState({ phone_connected: false, frames: 0 });
  const [error, setError] = useState('');
  const [expired, setExpired] = useState(false);

  const createSession = useCallback(async () => {
    setError('');
    setExpired(false);
    setStatus({ phone_connected: false, frames: 0 });
    try {
      const res = await fetch(apiUrl('/api/session'), { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSession(await res.json());
    } catch (e) {
      setSession(null);
      setError(`세션을 만들 수 없습니다 (${e.message}). api 서버가 켜져 있는지 확인하세요.`);
    }
  }, []);

  useEffect(() => {
    createSession();
  }, [createSession]);

  // 대시보드 WebSocket: 폰 연결 상태와 프레임 수를 실시간으로 받는다
  const sid = session?.session_id;
  useEffect(() => {
    if (!sid) return undefined;
    let closedByUs = false;
    let retry;
    let ws;
    const connect = () => {
      ws = new WebSocket(wsUrl(`/api/ws/dash/${encodeURIComponent(sid)}`));
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'status') setStatus(msg);
      };
      ws.onclose = (e) => {
        if (closedByUs) return;
        if (e.code === 4404) setExpired(true);
        else retry = setTimeout(connect, 1500);
      };
    };
    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retry);
      if (ws) ws.close();
    };
  }, [sid]);

  const base = process.env.REACT_APP_PUBLIC_URL || window.location.origin;
  const phoneUrl = session ? `${base}${session.phone_path}` : '';
  const isLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)/.test(base);

  return (
    <section className="qrp">
      <header className="qrp-head">
        <h3>① QR 카메라 연동</h3>
        <span className={status.phone_connected ? 'qrp-badge on' : 'qrp-badge'}>
          {status.phone_connected ? '● 연결됨' : '○ 대기 중'}
        </span>
      </header>

      {error && <p className="qrp-error">{error}</p>}

      {session && !expired && (
        <>
          <div className="qrp-qr">
            <QRCodeSVG value={phoneUrl} size={180} marginSize={2} />
          </div>
          <p className="qrp-url">{phoneUrl}</p>
          {isLocalhost && (
            <p className="qrp-warn">
              지금 주소가 localhost 라서 폰에서 열 수 없습니다. 터널(https) 주소로 이 페이지를 다시 열어 주세요.
            </p>
          )}
          {status.phone_connected && (
            <div className="qrp-live">
              <p>받은 프레임 {status.frames}장</p>
              {status.frames > 0 && (
                <img
                  className="qrp-preview"
                  src={apiUrl(`/api/session/${sid}/latest.jpg?f=${status.frames}`)}
                  alt="폰에서 받은 최근 프레임"
                />
              )}
            </div>
          )}
        </>
      )}

      {expired && <p className="qrp-warn">세션이 만료되었습니다.</p>}

      <button className="qrp-btn" onClick={createSession}>
        새 QR 만들기
      </button>
    </section>
  );
}
