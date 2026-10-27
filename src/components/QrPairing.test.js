import { render, screen, waitFor, act } from '@testing-library/react';
import QrPairing from './QrPairing';

// 가짜 WebSocket: 테스트에서 서버가 보낸 것처럼 메시지를 흘려 보낼 수 있다
class FakeWebSocket {
  static instances = [];
  constructor(url) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }
  close() {}
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  global.WebSocket = FakeWebSocket;
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ session_id: 'abc123', phone_path: '/m?sid=abc123', expires_in: 1800 }),
  });
});

test('세션을 만들어 QR 주소를 보여 주고, 폰이 연결되면 "연결됨"으로 바뀐다', async () => {
  render(<QrPairing />);

  // 세션 발급 → 폰이 열 주소(현재 origin + phone_path)가 화면에 보인다
  expect(await screen.findByText(`${window.location.origin}/m?sid=abc123`)).toBeInTheDocument();
  expect(screen.getByText('○ 대기 중')).toBeInTheDocument();

  // 세션 번호로 대시보드 WebSocket 에 접속한다
  await waitFor(() => expect(FakeWebSocket.instances.length).toBe(1));
  expect(FakeWebSocket.instances[0].url).toContain('/api/ws/dash/abc123');

  // 서버가 "폰 연결됨, 프레임 3장"을 알려 주면 화면이 바뀐다
  act(() => {
    FakeWebSocket.instances[0].onmessage({
      data: JSON.stringify({ type: 'status', phone_connected: true, frames: 3 }),
    });
  });
  expect(screen.getByText('● 연결됨')).toBeInTheDocument();
  expect(screen.getByText('받은 프레임 3장')).toBeInTheDocument();
});

test('api 서버에 연결할 수 없으면 안내 문구를 보여 준다', async () => {
  global.fetch = jest.fn().mockRejectedValue(new Error('Failed to fetch'));
  render(<QrPairing />);
  expect(await screen.findByText(/세션을 만들 수 없습니다/)).toBeInTheDocument();
});
