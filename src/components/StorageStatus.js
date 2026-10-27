import React, { useCallback, useEffect, useState } from 'react';
import { apiUrl, wsUrl } from '../lib/api';
import './Panel.css';

const GOAL = 100; // 목표 저장 개수 (기획 화면의 "11 / 100 저장")
const MAX_ITEMS = 30;

// 대시보드 ② "실시간 저장 현황" 패널.
// 처음엔 GET /api/stored 로 최근 목록을 받고, 이후엔 WS /api/ws/stored 로 새로 저장된 문장을 받아 위에 쌓는다.
export default function StorageStatus() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [live, setLive] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/stored?limit=${MAX_ITEMS}`));
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
      setItems(body.items);
      setTotal(body.total);
      setError('');
    } catch (e) {
      setError(`저장 목록을 불러올 수 없습니다 (${e.message}).`);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let closedByUs = false;
    let retry;
    let ws;
    const connect = () => {
      ws = new WebSocket(wsUrl('/api/ws/stored'));
      ws.onopen = () => {
        setLive(true);
        load(); // 끊겨 있던 동안 저장된 것까지 다시 맞춘다
      };
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type !== 'stored') return;
        setItems((prev) => [...msg.items.slice().reverse(), ...prev].slice(0, MAX_ITEMS));
        setTotal(msg.total);
        setError('');
      };
      ws.onclose = () => {
        setLive(false);
        if (!closedByUs) retry = setTimeout(connect, 1500);
      };
    };
    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retry);
      if (ws) ws.close();
    };
  }, [load]);

  const percent = Math.min(100, (total / GOAL) * 100);

  return (
    <section className="panel">
      <header className="panel-head">
        <h3>② 실시간 저장 현황</h3>
        <span className={live ? 'panel-badge on' : 'panel-badge'}>{live ? '● LIVE' : '○ 연결 중'}</span>
      </header>

      <p className="st-count">
        <strong>{total}</strong> / {GOAL} 저장
      </p>
      <div className="st-bar">
        <div className="st-bar-fill" style={{ width: `${percent}%` }} />
      </div>

      {error && <p className="panel-error">{error}</p>}

      <ul className="st-list">
        {items.map((item, i) => (
          <li key={item.id} className={i === 0 ? 'st-item new' : 'st-item'}>
            <span className="st-no">#{String(total - i).padStart(3, '0')}</span>
            <span className="st-text">{item.text}</span>
            <span className="st-tag">저장됨</span>
          </li>
        ))}
        {items.length === 0 && !error && <li className="st-empty">아직 저장된 문장이 없습니다.</li>}
      </ul>
    </section>
  );
}
