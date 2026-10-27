import React from 'react';
import QrPairing from '../components/QrPairing';
import StorageStatus from '../components/StorageStatus';
import RagSearch from '../components/RagSearch';

// 대시보드 (/dashboard): 기획의 "웹페이지에 반드시 있어야 할 3가지" ① QR ② 저장 현황 ③ RAG 검색.
export default function Dashboard() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0d14', padding: 24, boxSizing: 'border-box' }}>
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
