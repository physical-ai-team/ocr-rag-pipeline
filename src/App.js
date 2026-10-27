import React, { useState } from 'react';
import { createStitches } from '@stitches/react';

const { styled } = createStitches({
  theme: {
    colors: {
      bg: '#0a0d14',
      cardBg: '#121824',
      cardBorder: '#1e293b',
      textPrimary: '#f8fafc',
      textSecondary: '#94a3b8',
      accent: '#38bdf8',
      accentHover: '#0ea5e9',
      accentGlow: 'rgba(56, 189, 248, 0.15)',
      navBg: 'rgba(10, 13, 20, 0.8)',
    },
  },
});

// 전체 레이아웃
const PageWrapper = styled('div', {
  backgroundColor: '$bg',
  color: '$textPrimary',
  minHeight: '100vh',
  fontFamily: "'Inter', sans-serif",
  paddingBottom: '80px',
});

// GNB 상단 네비게이션바
const Navbar = styled('header', {
  position: 'sticky',
  top: 0,
  zIndex: 100,
  backdropFilter: 'blur(12px)',
  backgroundColor: '$navBg',
  borderBottom: '1px solid $cardBorder',
  padding: '16px 40px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
});

const Logo = styled('div', {
  fontSize: '20px',
  fontWeight: '800',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  color: '$textPrimary',
  span: {
    color: '$accent',
  },
});

const NavLinks = styled('nav', {
  display: 'flex',
  gap: '24px',
  alignItems: 'center',
  a: {
    color: '$textSecondary',
    textDecoration: 'none',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'color 0.2s',
    '&:hover': {
      color: '$textPrimary',
    },
  },
});

const DemoButton = styled('button', {
  backgroundColor: '$accent',
  color: '#0a0d14',
  border: 'none',
  padding: '8px 16px',
  borderRadius: '20px',
  fontWeight: '700',
  fontSize: '13px',
  cursor: 'pointer',
  transition: 'all 0.2s',
  '&:hover': {
    backgroundColor: '$accentHover',
  },
});

// 시연용 화면(/conveyor, /dashboard)으로 바로 가는 버튼. 두 화면을 나란히 띄우도록 새 탭으로 연다
const NavActions = styled('div', {
  display: 'flex',
  gap: '8px',
});

const PageLink = styled('a', {
  border: '1px solid $accent',
  color: '$accent',
  padding: '7px 14px',
  borderRadius: '20px',
  fontWeight: '700',
  fontSize: '13px',
  textDecoration: 'none',
  transition: 'all 0.2s',
  '&:hover': {
    backgroundColor: '$accent',
    color: '#0a0d14',
  },
});

// 히어로 섹션
const HeroSection = styled('section', {
  maxWidth: '1100px',
  margin: '0 auto',
  padding: '60px 20px 40px',
  textAlign: 'center',
});

const Badge = styled('span', {
  backgroundColor: '$accentGlow',
  color: '$accent',
  border: '1px solid rgba(56, 189, 248, 0.3)',
  fontSize: '13px',
  fontWeight: '600',
  padding: '6px 14px',
  borderRadius: '20px',
  display: 'inline-block',
  marginBottom: '20px',
});

const HeroTitle = styled('h1', {
  fontSize: '44px',
  fontWeight: '800',
  lineHeight: '1.25',
  marginBottom: '16px',
  letterSpacing: '-0.02em',
});

const HeroDesc = styled('p', {
  fontSize: '18px',
  color: '$textSecondary',
  maxWidth: '700px',
  margin: '0 auto 40px',
  lineHeight: '1.6',
});

// 핵심 KPI 정보 카드 섹션
const MetricsGrid = styled('div', {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '20px',
  maxWidth: '850px',
  margin: '0 auto 50px',
});

const MetricCard = styled('div', {
  backgroundColor: '$cardBg',
  border: '1px solid $cardBorder',
  borderRadius: '12px',
  padding: '20px',
  textAlign: 'center',
  h4: {
    fontSize: '12px',
    color: '$textSecondary',
    marginBottom: '8px',
    textTransform: 'uppercase',
  },
  p: {
    fontSize: '22px',
    fontWeight: '700',
    color: '$accent',
  },
});

// 데모 대시보드 카드
const MainCard = styled('div', {
  backgroundColor: '$cardBg',
  border: '1px solid $cardBorder',
  borderRadius: '20px',
  padding: '36px',
  maxWidth: '850px',
  margin: '0 auto',
  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
});

const UploadBox = styled('label', {
  border: '2px dashed $cardBorder',
  borderRadius: '16px',
  padding: '40px 20px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  backgroundColor: 'rgba(18, 24, 36, 0.6)',
  '&:hover': {
    borderColor: '$accent',
    backgroundColor: '$accentGlow',
  },
  input: {
    display: 'none',
  },
});

const PreviewImage = styled('img', {
  width: '100%',
  maxHeight: '360px',
  objectFit: 'contain',
  borderRadius: '12px',
  marginTop: '24px',
  border: '1px solid $cardBorder',
});

const ActionButton = styled('button', {
  backgroundColor: '$accent',
  color: '#0a0d14',
  border: 'none',
  width: '100%',
  padding: '14px 20px',
  borderRadius: '10px',
  fontWeight: '700',
  fontSize: '16px',
  cursor: 'pointer',
  marginTop: '24px',
  transition: 'all 0.2s',
  '&:hover': {
    backgroundColor: '$accentHover',
  },
});

const ResultBox = styled('div', {
  backgroundColor: '#070a10',
  border: '1px solid $cardBorder',
  borderRadius: '10px',
  padding: '20px',
  marginTop: '20px',
  fontSize: '14px',
  lineHeight: '1.6',
  color: '$textPrimary',
  whiteSpace: 'pre-wrap',
});

// 하단 파이프라인 특징 카드 섹션
const FeatureSection = styled('section', {
  maxWidth: '1050px',
  margin: '80px auto 0',
  padding: '0 20px',
});

const SectionTitle = styled('h2', {
  fontSize: '26px',
  fontWeight: '700',
  textAlign: 'center',
  marginBottom: '40px',
});

const FeatureGrid = styled('div', {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '24px',
});

const FeatureCard = styled('div', {
  backgroundColor: '$cardBg',
  border: '1px solid $cardBorder',
  borderRadius: '16px',
  padding: '24px',
  h3: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '10px',
  },
  p: {
    fontSize: '14px',
    color: '$textSecondary',
    lineHeight: '1.5',
  },
});

function App() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [resultText, setResultText] = useState('');

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setResultText('');
    }
  };

  const handleExtract = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setResultText(
        "Successfully extracted text:\n[Mock OCR Result] Deep Learning OCR and RAG Engine Initialization Complete. Embedded in Vector DB with Cosine Similarity Indexing."
      );
    }, 1200);
  };

  return (
    <PageWrapper>
      {/* 상단 네비게이션바 */}
      <Navbar>
        <Logo>
          🔍 OCR·<span>RAG Pipeline</span>
        </Logo>
        <NavLinks>
          <a href="#overview">파이프라인 개요</a>
          <a href="#demo">실시간 데모</a>
          <a href="#architecture">아키텍처</a>
          <a href="#docs">문서</a>
        </NavLinks>
        <NavActions>
          <PageLink href="/conveyor" target="_blank" rel="noopener">
            컨베이어 열기
          </PageLink>
          <PageLink href="/dashboard" target="_blank" rel="noopener">
            대시보드 열기
          </PageLink>
          <DemoButton onClick={() => window.scrollTo({ top: 300, behavior: 'smooth' })}>
            데모 실행하기
          </DemoButton>
        </NavActions>
      </Navbar>

      {/* 히어로 타이틀 섹션 */}
      <HeroSection id="overview">
        <Badge>PHYSICAL AI POC · VISION & RAG</Badge>
        <HeroTitle>
          영문 문서 이미지에서<br />
          지능형 텍스트를 즉시 추출합니다
        </HeroTitle>
        <HeroDesc>
          고성능 OCR 엔진으로 원문 이미지를 스캔하고 벡터 데이터베이스와 연동하여<br />
          실시간 RAG 질의응답 및 데이터 검색 파이프라인을 구축하세요.
        </HeroDesc>

        {/* 핵심 KPI 정보 */}
        <MetricsGrid>
          <MetricCard>
            <h4>처리 시간 목표</h4>
            <p>≤ 200ms</p>
          </MetricCard>
          <MetricCard>
            <h4>인식 정확도</h4>
            <p>≥ 98.5%</p>
          </MetricCard>
          <MetricCard>
            <h4>파이프라인 연동</h4>
            <p>Vector DB Ready</p>
          </MetricCard>
        </MetricsGrid>

        {/* OCR 데모 인터랙션 메인 카드 */}
        <MainCard id="demo">
          <UploadBox>
            <span style={{ fontSize: '28px', marginBottom: '12px' }}>📁</span>
            <span style={{ fontSize: '16px', fontWeight: '600', color: '#f8fafc', marginBottom: '6px' }}>
              문서 이미지를 드래그하거나 클릭하여 업로드하세요
            </span>
            <span style={{ fontSize: '13px', color: '#94a3b8' }}>PNG, JPG, JPEG, WEBP 지원</span>
            <input type="file" accept="image/*" onChange={handleImageUpload} />
          </UploadBox>

          {image && (
            <>
              <PreviewImage src={image} alt="Preview" />
              <ActionButton onClick={handleExtract} disabled={loading}>
                {loading ? '⚡ 텍스트 추출 및 임베딩 처리 중...' : '✨ 텍스트 추출 및 벡터화 시작'}
              </ActionButton>
            </>
          )}

          {resultText && (
            <div style={{ marginTop: '28px', textAlign: 'left' }}>
              <span style={{ fontSize: '14px', fontWeight: '700', color: '#38bdf8' }}>
                📄 추출된 원문 텍스트 & 벡터 데이터
              </span>
              <ResultBox>{resultText}</ResultBox>
            </div>
          )}
        </MainCard>
      </HeroSection>

      {/* 하단 기능 소개 섹션 */}
      <FeatureSection id="architecture">
        <SectionTitle>주요 기능 및 핵심 특징</SectionTitle>
        <FeatureGrid>
          <FeatureCard>
            <h3>📷 다국어 OCR 인식</h3>
            <p>고해상도 이미지 처리 알고리즘을 통해 영문 및 특수 기호를 정밀하게 텍스트로 전환합니다.</p>
          </FeatureCard>
          <FeatureCard>
            <h3>🧠 Vector DB 임베딩</h3>
            <p>추출된 텍스트를 청크 단위로 나누어 지능형 벡터 지식 기반에 실시간 저장 및 인덱싱합니다.</p>
          </FeatureCard>
          <FeatureCard>
            <h3>⚡ RAG 검색 연동</h3>
            <p>사용자 질의 시 연관된 문서 맥락을 초고속으로 추론 및 검색하여 대답 정확도를 높입니다.</p>
          </FeatureCard>
        </FeatureGrid>
      </FeatureSection>
    </PageWrapper>
  );
}

export default App;