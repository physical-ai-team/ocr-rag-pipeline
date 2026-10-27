import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import PhoneCapture from './pages/PhoneCapture';
import PairPage from './pages/PairPage';
import Dashboard from './pages/Dashboard';
import Conveyor from './pages/Conveyor';
import reportWebVitals from './reportWebVitals';

// 라우터 없이 주소(path)만 보고 화면을 고른다.
//   /m          폰 촬영 페이지 (QR 로 열리는 주소)
//   /pair       QR 연동 확인 페이지
//   /dashboard  ① QR ② 저장 현황 ③ RAG 검색
//   그 외       기존 App
const pages = { '/m': PhoneCapture, '/pair': PairPage, '/dashboard': Dashboard, '/conveyor': Conveyor };
const Page = pages[window.location.pathname] || App;

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

