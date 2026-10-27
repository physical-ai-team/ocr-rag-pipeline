// api 서비스 주소를 만드는 도우미.
// - 개발(npm start): .env.development 의 REACT_APP_API_ORIGIN(http://localhost:8000)으로 바로 접속한다.
// - 빌드본을 api 가 함께 서빙할 때: 값이 비어 있어서 같은 주소(origin)를 쓴다. (폰 테스트, 터널 1개로 충분)
const ORIGIN = process.env.REACT_APP_API_ORIGIN || '';

export function apiUrl(path) {
  return `${ORIGIN}${path}`;
}

export function wsUrl(path) {
  if (ORIGIN) return `${ORIGIN.replace(/^http/, 'ws')}${path}`;
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${window.location.host}${path}`;
}
