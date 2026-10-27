import React, { useState } from 'react';
import { createStitches } from '@stitches/react';

const { styled } = createStitches({
  theme: {
    colors: {
      bg: '#090d16',
      cardBg: '#111827',
      cardBorder: '#1f2937',
      textPrimary: '#f9fafb',
      textSecondary: '#9ca3af',
      accent: '#38bdf8',
      accentHover: '#0ea5e9',
      resultBg: '#030712',
    },
  },
});

const Container = styled('div', {
  backgroundColor: '$bg',
  color: '$textPrimary',
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '20px',
  fontFamily: "'Inter', sans-serif",
});

const Card = styled('div', {
  backgroundColor: '$cardBg',
  border: '1px solid $cardBorder',
  borderRadius: '16px',
  padding: '32px',
  width: '100%',
  maxWidth: '640px',
  boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.5), 0 8px 10px -6px rgb(0 0 0 / 0.5)',
});

const Badge = styled('span', {
  backgroundColor: 'rgba(56, 189, 248, 0.1)',
  color: '$accent',
  fontSize: '12px',
  fontWeight: '600',
  padding: '4px 10px',
  borderRadius: '20px',
  display: 'inline-block',
  marginBottom: '12px',
});

const Title = styled('h1', {
  color: '$textPrimary',
  fontSize: '22px',
  fontWeight: '700',
  marginBottom: '8px',
});

const Description = styled('p', {
  color: '$textSecondary',
  fontSize: '14px',
  marginBottom: '24px',
});

const UploadBox = styled('label', {
  border: '2px dashed $cardBorder',
  borderRadius: '12px',
  padding: '32px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  backgroundColor: 'rgba(17, 24, 39, 0.5)',
  '&:hover': {
    borderColor: '$accent',
    backgroundColor: 'rgba(56, 189, 248, 0.03)',
  },
  input: {
    display: 'none',
  },
});

const PreviewImage = styled('img', {
  width: '100%',
  maxHeight: '300px',
  objectFit: 'contain',
  borderRadius: '8px',
  marginTop: '20px',
  border: '1px solid $cardBorder',
});

const Button = styled('button', {
  backgroundColor: '$accent',
  color: '#090d16',
  border: 'none',
  width: '100%',
  padding: '12px 20px',
  borderRadius: '8px',
  fontWeight: '600',
  fontSize: '15px',
  cursor: 'pointer',
  marginTop: '20px',
  transition: 'background-color 0.2s',
  '&:hover': {
    backgroundColor: '$accentHover',
  },
});

const ResultBox = styled('div', {
  backgroundColor: '$resultBg',
  border: '1px solid $cardBorder',
  borderRadius: '8px',
  padding: '16px',
  marginTop: '20px',
  fontSize: '14px',
  color: '$textPrimary',
  whiteSpace: 'pre-wrap',
  maxHeight: '150px',
  overflowY: 'auto',
});

function App() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [resultText, setResultText] = useState('');

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(URL.createObjectURL(file));
      setResultText(''); // 새 이미지 올리면 결과 초기화
    }
  };

  const handleExtract = () => {
    setLoading(true);
    // 나중에 백엔드 OCR 연동할 때 이 부분을 API 호출로 교체하면 됩니다!
    setTimeout(() => {
      setLoading(false);
      setResultText("Successfully extracted text: [Mock OCR Result] The quick brown fox jumps over the lazy dog. Ready for Vector DB embedding & RAG pipeline.");
    }, 1200);
  };

  return (
    <Container>
      <Card>
        <Badge>AI PIPELINE DEMO</Badge>
        <Title>📷 OCR & RAG Document Intelligence</Title>
        <Description>영문 원문 이미지를 업로드하여 텍스트를 추출하고 벡터 데이터베이스와 연동하세요.</Description>
        
        <UploadBox>
          <span style={{ fontSize: '14px', color: '#9ca3af', marginBottom: '8px' }}>📁 이미지를 여기에 마우스로 드래그하거나 클릭하여 업로드</span>
          <span style={{ fontSize: '12px', color: '#4b5563' }}>PNG, JPG, JPEG 지원</span>
          <input type="file" accept="image/*" onChange={handleImageUpload} />
        </UploadBox>
        
        {image && (
          <>
            <PreviewImage src={image} alt="Preview" />
            <Button onClick={handleExtract} disabled={loading}>
              {loading ? '텍스트 추출 및 임베딩 중...' : '✨ 텍스트 추출 시작'}
            </Button>
          </>
        )}

        {resultText && (
          <div style={{ marginTop: '20px' }}>
            <span style={{ fontSize: '13px', fontWeight: '600', color: '#38bdf8' }}>📄 추출된 텍스트 결과</span>
            <ResultBox>{resultText}</ResultBox>
          </div>
        )}
      </Card>
    </Container>
  );
}

export default App;