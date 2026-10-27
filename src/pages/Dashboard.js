import React from 'react';
import QrPairing from '../components/QrPairing';
import StorageStatus from '../components/StorageStatus';
import RagSearch from '../components/RagSearch';

const linkStyle = {
  color: '#4ade8a',
  border: '1px solid #4ade8a',
  borderRadius: 20,
  padding: '6px 14px',
  fontSize: 13,
  fontWeight: 700,
  textDecoration: 'none',
};

// 대시보드 (/dashboard): 기획의 "웹페이지에 반드시 있어야 할 3가지" ① QR ② 저장 현황 ③ RAG 검색.
export default function Dashboard() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0d14', padding: 24, boxSizing: 'border-box' }}>
      <nav style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginBottom: 16 }}>
        <a href="/" style={{ ...linkStyle, color: '#94a3b8', borderColor: '#1e293b' }}>
          메인
        </a>
        <a href="/conveyor" target="_blank" rel="noopener" style={linkStyle}>
          컨베이어 열기 (새 탭)
        </a>
      </nav>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 16,
          alignItems: 'start',
        }}
      >
        <QrPairing />
        <StorageStatus />
        <RagSearch />
      </div>
    </div>
  );
}
