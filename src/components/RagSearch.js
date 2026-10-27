import React, { useState } from 'react';
import { apiUrl } from '../lib/api';
import './Panel.css';

// 대시보드 ③ "RAG 검색" 패널. 질문 → POST /api/rag → 답변 + 근거 문장(유사도).
export default function RagSearch() {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null); // { answer, sources, model }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ask = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(apiUrl('/api/rag'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`);
      setResult(body);
    } catch (err) {
      setResult(null);
      setError(`검색 실패: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <header className="panel-head">
        <h3>③ RAG 검색</h3>
      </header>

      <form className="rag-form" onSubmit={ask}>
        <input
          className="rag-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="저장된 원문에 대해 질문하세요 (한국어/영어)"
          aria-label="질문"
        />
        <button className="rag-btn" type="submit" disabled={loading || !question.trim()}>
          {loading ? '검색 중…' : '검색'}
        </button>
      </form>

      {error && <p className="panel-error">{error}</p>}

      {result && (
        <div className="rag-result">
          {result.answer ? (
            <p className="rag-answer">{result.answer}</p>
          ) : (
            result.sources.length > 0 && (
              <p className="panel-warn">LLM 키(GEMINI_API_KEY)가 없어 가장 관련 있는 문장만 보여 줍니다.</p>
            )
          )}
          {result.sources.length > 0 && (
            <ol className="rag-sources">
              {result.sources.map((s) => (
                <li key={s.id}>
                  <span className="rag-n">[{s.n}]</span> {s.text}
                  <span className="rag-score">유사도 {s.score.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}
