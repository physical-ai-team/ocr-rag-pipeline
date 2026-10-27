import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl, wsUrl } from '../lib/api';
import './Panel.css';

const GOAL = 100; // 컨베이어 지문 수 (기획 화면의 "11 / 100 저장")
const MAX_ITEMS = 30;

// 대시보드 ② "실시간 저장 현황" 패널.
// - 지문 탭: 카드 제목으로 묶은 지문 목록 (GET /api/passages). 숫자는 저장된 지문 수 / 100.
// - 문장 탭: 실제로 DB 에 저장된 문장 (GET /api/stored).
// 새로 저장될 때마다 WS /api/ws/stored 로 알림을 받아 문장은 바로 쌓고, 지문 목록은 다시 불러온다.
export default function StorageStatus() {
  const [tab, setTab] = useState('passages');
  const [passages, setPassages] = useState({ passages: [], untitled_sentences: 0, total_sentences: 0 });
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [live, setLive] = useState(false);
  const [error, setError] = useState('');
  const refetchTimer = useRef(null);

  const fetchJson = async (path) => {
    const res = await fetch(apiUrl(path));
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    return body;
  };

  const loadPassages = useCallback(async () => {
    try {
      setPassages(await fetchJson('/api/passages'));
    } catch (e) {
      setError(`지문 목록을 불러올 수 없습니다 (${e.message}).`);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const body = await fetchJson(`/api/stored?limit=${MAX_ITEMS}`);
      setItems(body.items);
      setTotal(body.total);
      setError('');
    } catch (e) {
      setError(`저장 목록을 불러올 수 없습니다 (${e.message}).`);
    }
    loadPassages();
  }, [loadPassages]);

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
        // 프레임마다 알림이 오므로 잠깐 모았다가 지문 목록을 한 번만 다시 불러온다
        clearTimeout(refetchTimer.current);
        refetchTimer.current = setTimeout(loadPassages, 500);
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
      clearTimeout(refetchTimer.current);
      if (ws) ws.close();
    };
  }, [load, loadPassages]);

  const count = passages.passages.length;
  const percent = Math.min(100, (count / GOAL) * 100);
  const recentFirst = passages.passages.slice().sort((a, b) => b.last_ts - a.last_ts);

  return (
    <section className="panel">
      <header className="panel-head">
        <h3>② 실시간 저장 현황</h3>
        <span className={live ? 'panel-badge on' : 'panel-badge'}>{live ? '● LIVE' : '○ 연결 중'}</span>
      </header>

      <p className="st-count">
        <strong>{count}</strong> / {GOAL} 지문 저장
      </p>
      <div className="st-bar">
        <div className="st-bar-fill" style={{ width: `${percent}%` }} />
      </div>
      <p className="st-sub">
        문장 {total}개{passages.untitled_sentences > 0 && ` · 제목 미확인 문장 ${passages.untitled_sentences}개`}
      </p>

      <div className="st-tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'passages'} onClick={() => setTab('passages')}>
          지문
        </button>
        <button role="tab" aria-selected={tab === 'sentences'} onClick={() => setTab('sentences')}>
          문장
        </button>
      </div>

      {error && <p className="panel-error">{error}</p>}

      {tab === 'passages' ? (
        <ul className="st-list">
          {recentFirst.map((p, i) => (
            <li key={p.no} className={i === 0 ? 'st-item new' : 'st-item'}>
              <span className="st-no">#{String(p.no).padStart(3, '0')}</span>
              <span className="st-text">{p.title}</span>
              <span className="st-tag">문장 {p.sentences}</span>
            </li>
          ))}
          {count === 0 && !error && <li className="st-empty">아직 저장된 지문이 없습니다.</li>}
        </ul>
      ) : (
        <ul className="st-list">
          {items.map((item, i) => (
            <li key={item.id} className={i === 0 ? 'st-item new' : 'st-item'}>
              <span className="st-no">#{String(total - i).padStart(3, '0')}</span>
              <span className="st-text">
                {item.text}
                {item.meta?.title && <span className="st-title">{item.meta.title}</span>}
              </span>
              <span className="st-tag">저장됨</span>
            </li>
          ))}
          {items.length === 0 && !error && <li className="st-empty">아직 저장된 문장이 없습니다.</li>}
        </ul>
      )}
    </section>
  );
}
