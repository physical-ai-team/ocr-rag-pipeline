import React, { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import PASSAGES from '../data/passages';
import './Conveyor.css';

// 원문 컨베이어 (/conveyor). PC 화면에 영어 지문 카드를 벨트처럼 흘려보내고, 폰 카메라로 찍어 OCR 을 시험한다.
// 원본: ocr-conveyor-test.html (단일 HTML) 을 React 로 옮긴 것.
//
// 성능: 카드 이동은 requestAnimationFrame 에서 ref 로 transform 만 직접 바꾼다 (프레임마다 setState 하지 않음).
// 글자 크기·줄 간격·카드 높이·간격은 CSS 변수로 넘겨서, 슬라이더를 움직여도 카드 200장을 다시 그리지 않는다.

const MIN_SPEED = 5;
const MAX_SPEED = 600;
const clampSpeed = (v) => Math.max(MIN_SPEED, Math.min(MAX_SPEED, v));

const FACES = [
  { value: 'serif', label: 'Serif' },
  { value: 'sans', label: 'Sans' },
  { value: 'mono', label: 'Mono' },
];
const DIRS = [
  { value: 'left', label: '← 왼쪽' },
  { value: 'right', label: '오른쪽 →' },
];

// 카드 한 벌. 같은 세트를 두 벌 이어 붙여 끊김 없이 순환시킨다 (두 번째 벌은 화면 읽기 프로그램에서 숨김)
const CardGroup = memo(function CardGroup({ passages, groupRef, hidden }) {
  return (
    <div className="conveyor-group" ref={groupRef} aria-hidden={hidden || undefined}>
      {passages.map((p, i) => (
        <article className="conveyor-item" key={i}>
          <span className="conveyor-idx">{String(i + 1).padStart(3, '0')}</span>
          <div className="conveyor-item-body">
            <h2>{p.title}</h2>
            {p.body.map((t, j) => (
              <p key={j}>{t}</p>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
});

export default function Conveyor() {
  const laneRef = useRef(null);
  const trackRef = useRef(null);
  const surfaceRef = useRef(null);
  const groupRef = useRef(null); // 첫 번째 카드 묶음 (한 바퀴 길이 계산용)

  // 애니메이션용 값은 ref 에 둔다 (바뀌어도 다시 그리지 않음)
  const offsetRef = useRef(0); // 현재 이동한 거리(px)
  const loopWRef = useRef(0); // 한 바퀴 길이 = 카드 한 벌 너비 + 간격
  const speedRef = useRef(80);
  const dirRef = useRef('left');

  // 조절 패널 값 (사용자가 바꿀 때만 다시 그린다)
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(80); // px/s
  const [fontSize, setFontSize] = useState(14); // px
  const [leading, setLeading] = useState(2.0); // 줄 간격
  const [gap, setGap] = useState(40); // 카드 사이 간격(px)
  const [count, setCount] = useState(PASSAGES.length); // 투입 지문 수
  const [height, setHeight] = useState(66); // 카드 높이(vh)
  const [face, setFace] = useState('serif');
  const [theme, setTheme] = useState(''); // '' | paper | dark | lowc
  const [dir, setDir] = useState('left');
  const [guides, setGuides] = useState(false); // 안전여백 가이드 표시

  speedRef.current = speed;
  dirRef.current = dir;

  const passages = useMemo(() => PASSAGES.slice(0, count), [count]);

  // 현재 offset 을 화면(벨트 + 표면 무늬)에 반영
  const apply = useCallback(() => {
    const x = -offsetRef.current;
    if (trackRef.current) trackRef.current.style.transform = `translate3d(${x}px, 0, 0)`;
    if (surfaceRef.current) surfaceRef.current.style.backgroundPosition = `${x}px 0`;
  }, []);

  // 한 바퀴 길이를 다시 재고 offset 을 그 안으로 맞춘다
  const measure = useCallback(() => {
    if (!trackRef.current || !groupRef.current) return;
    const g = parseFloat(getComputedStyle(trackRef.current).gap) || 0;
    const loopW = groupRef.current.getBoundingClientRect().width + g;
    loopWRef.current = loopW;
    if (loopW > 0) offsetRef.current = ((offsetRef.current % loopW) + loopW) % loopW;
    apply();
  }, [apply]);

  const reset = useCallback(() => {
    offsetRef.current = 0;
    apply();
  }, [apply]);

  // 지문 수가 바뀌면 처음 위치로 (원본의 build 와 같음)
  useLayoutEffect(() => {
    offsetRef.current = 0;
  }, [count]);

  // 카드 수·간격·높이가 바뀌면 한 바퀴 길이를 다시 잰다
  useLayoutEffect(measure, [measure, count, gap, height]);

  // 창 크기 변화, 웹폰트 로딩 후에도 다시 잰다
  useEffect(() => {
    const ro = new ResizeObserver(measure);
    ro.observe(laneRef.current);
    let alive = true;
    if (document.fonts) document.fonts.ready.then(() => alive && measure());
    return () => {
      alive = false;
      ro.disconnect();
    };
  }, [measure]);

  // 재생 중일 때만 프레임 루프를 돌린다
  useEffect(() => {
    if (!running) return undefined;
    let last = 0;
    let rafId = requestAnimationFrame(function frame(ts) {
      if (!last) last = ts;
      const dt = Math.min((ts - last) / 1000, 0.1); // 탭 전환 등으로 멈췄다 돌아와도 크게 튀지 않게
      last = ts;
      const loopW = loopWRef.current;
      let offset = offsetRef.current + (dirRef.current === 'left' ? 1 : -1) * speedRef.current * dt;
      if (loopW > 0) offset = ((offset % loopW) + loopW) % loopW;
      offsetRef.current = offset;
      apply();
      rafId = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(rafId);
  }, [running, apply]);

  // 키보드 단축키: Space 재생/정지, ←/→ 속도 ±5, R 처음, G 가이드
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.matches('input, select')) return;
      if (e.key === ' ') {
        e.preventDefault();
        setRunning((v) => !v);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setSpeed((v) => clampSpeed(v + 5));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setSpeed((v) => clampSpeed(v - 5));
      } else if (e.key === 'r' || e.key === 'R') {
        reset();
      } else if (e.key === 'g' || e.key === 'G') {
        setGuides((v) => !v);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [reset]);

  // 카드 모양 값은 CSS 변수로 넘긴다
  const stageStyle = {
    '--conveyor-fs': `${fontSize}px`,
    '--conveyor-lh': leading.toFixed(2),
    '--conveyor-card-h': `${height}vh`,
    '--conveyor-gap': `${gap}px`,
  };

  return (
    <div className="conveyor">
      <section
        className="conveyor-stage"
        data-face={face}
        data-theme={theme || undefined}
        data-guides={guides || undefined}
        style={stageStyle}
      >
        <div className="conveyor-lane" ref={laneRef}>
          <div className="conveyor-track" ref={trackRef}>
            <CardGroup passages={passages} groupRef={groupRef} />
            <CardGroup passages={passages} hidden />
          </div>
        </div>
        <div className="conveyor-belt" ref={surfaceRef} />
        <div className="conveyor-meta">
          <span>카드 9:16</span>
          <span>
            물품 <b>{count}</b>
          </span>
          <span>
            속도 <b>{speed}</b> px/s
          </span>
          <span>{running ? '이송 중' : '정지'}</span>
        </div>
      </section>

      <aside className="conveyor-panel">
        <h1>OCR Conveyor Bench</h1>
        <p className="conveyor-sub">English source feed</p>

        <div className="conveyor-transport">
          <button className={`conveyor-play${running ? ' running' : ''}`} onClick={() => setRunning((v) => !v)}>
            {running ? '정지' : '재생'}
          </button>
          <button onClick={reset}>처음</button>
          <button onClick={() => setGuides((v) => !v)}>가이드</button>
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-speed">
            이송 속도 <output>{speed} px/s</output>
          </label>
          <input
            type="range"
            id="conveyor-speed"
            min={MIN_SPEED}
            max={MAX_SPEED}
            step="5"
            value={speed}
            onChange={(e) => setSpeed(clampSpeed(+e.target.value))}
          />
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-size">
            글자 크기 <output>{fontSize} px</output>
          </label>
          <input
            type="range"
            id="conveyor-size"
            min="8"
            max="32"
            step="1"
            value={fontSize}
            onChange={(e) => setFontSize(+e.target.value)}
          />
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-leading">
            줄 간격 <output>{leading.toFixed(2)}</output>
          </label>
          <input
            type="range"
            id="conveyor-leading"
            min="1.4"
            max="3.2"
            step="0.05"
            value={leading}
            onChange={(e) => setLeading(+e.target.value)}
          />
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-gap">
            물품 간격 <output>{gap} px</output>
          </label>
          <input
            type="range"
            id="conveyor-gap"
            min="0"
            max="300"
            step="5"
            value={gap}
            onChange={(e) => setGap(+e.target.value)}
          />
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-count">
            투입 지문 수 <output>{count} 장</output>
          </label>
          <select id="conveyor-count" value={count} onChange={(e) => setCount(+e.target.value)}>
            <option value="10">10장 (짧은 순환)</option>
            <option value="25">25장</option>
            <option value="50">50장</option>
            <option value="100">100장 (전체)</option>
          </select>
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-height">
            카드 높이 <output>{height} vh</output>
          </label>
          <input
            type="range"
            id="conveyor-height"
            min="30"
            max="88"
            step="1"
            value={height}
            onChange={(e) => setHeight(+e.target.value)}
          />
        </div>

        <div className="conveyor-rule" />

        <div className="conveyor-field">
          <label>서체</label>
          <div className="conveyor-seg">
            {FACES.map((f) => (
              <button key={f.value} aria-pressed={face === f.value} onClick={() => setFace(f.value)}>
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div className="conveyor-field">
          <label htmlFor="conveyor-theme">지면</label>
          <select id="conveyor-theme" value={theme} onChange={(e) => setTheme(e.target.value)}>
            <option value="">흰 종이 / 검은 글씨</option>
            <option value="paper">미색 종이</option>
            <option value="dark">검은 카드 / 흰 글씨</option>
            <option value="lowc">저대비 (인식률 스트레스)</option>
          </select>
        </div>

        <div className="conveyor-field">
          <label>진행 방향</label>
          <div className="conveyor-seg">
            {DIRS.map((d) => (
              <button key={d.value} aria-pressed={dir === d.value} onClick={() => setDir(d.value)}>
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div className="conveyor-rule" />

        <p className="conveyor-hint">
          <kbd>Space</kbd> 재생 / 정지
          <br />
          <kbd>←</kbd> <kbd>→</kbd> 속도 ±5
          <br />
          <kbd>R</kbd> 처음으로 &nbsp; <kbd>G</kbd> 가이드
          <br />
          카드 {count}장이 끊김 없이 순환합니다.
        </p>
      </aside>
    </div>
  );
}
