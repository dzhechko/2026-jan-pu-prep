import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test-utils';
import PaywallPage from '../PaywallPage';

const mockPost = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('PaywallPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders premium features', () => {
    render(<PaywallPage />);
    expect(screen.getByText('НутриМайнд Premium')).toBeInTheDocument();
    expect(screen.getByText('Безлимитные AI инсайты')).toBeInTheDocument();
    expect(screen.getByText('Персонализированные рекомендации')).toBeInTheDocument();
    expect(screen.getByText('Полный доступ к CBT урокам')).toBeInTheDocument();
    expect(screen.getByText('Продвинутый анализ паттернов')).toBeInTheDocument();
  });

  it('renders pricing', () => {
    render(<PaywallPage />);
    expect(screen.getByText('499')).toBeInTheDocument();
  });

  it('renders subscribe and dismiss buttons', () => {
    render(<PaywallPage />);
    expect(screen.getByText('Подписаться')).toBeInTheDocument();
    expect(screen.getByText('Не сейчас')).toBeInTheDocument();
  });

  it('subscribes and shows success state', async () => {
    mockPost.mockResolvedValueOnce({
      data: { status: 'active', plan: 'premium', expires_at: '2026-03-01' },
    });

    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Подписаться'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/payments/subscribe', {});
    });

    await waitFor(() => {
      expect(screen.getByText(/Premium активирован/)).toBeInTheDocument();
    });
  });

  it('shows error on subscribe failure', async () => {
    mockPost.mockRejectedValueOnce({ message: 'Платёж не прошёл' });

    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Подписаться'));

    await waitFor(() => {
      expect(screen.getByText('Платёж не прошёл')).toBeInTheDocument();
    });
  });

  it('shows fallback error message', async () => {
    mockPost.mockRejectedValueOnce({});

    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Подписаться'));

    await waitFor(() => {
      expect(screen.getByText('Не удалось оформить подписку. Попробуйте ещё раз.')).toBeInTheDocument();
    });
  });

  it('navigates to home after success', async () => {
    mockPost.mockResolvedValueOnce({
      data: { status: 'active', plan: 'premium', expires_at: '2026-03-01' },
    });

    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Подписаться'));

    await waitFor(() => {
      expect(screen.getByText(/На главную/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('На главную'));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('dismiss navigates back', () => {
    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Не сейчас'));
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('disables button while subscribing', async () => {
    mockPost.mockReturnValue(new Promise(() => {})); // never resolves

    render(<PaywallPage />);
    fireEvent.click(screen.getByText('Подписаться'));

    await waitFor(() => {
      const btn = screen.getByText('Оформление...').closest('button');
      expect(btn).toBeDisabled();
    });
  });
});
