import React from 'react';
import QrPairing from '../components/QrPairing';

// QR 연동 단독 확인용 페이지 (/pair). 대시보드가 완성되면 QrPairing 을 대시보드 ① 패널에 넣고 이 페이지는 지워도 된다.
export default function PairPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0d14', padding: 24 }}>
      <QrPairing />
    </div>
  );
}
