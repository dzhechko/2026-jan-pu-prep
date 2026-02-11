import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import { useUserStore } from '@/entities/user/store';
import ProfilePage from '../ProfilePage';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
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

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: 'Иван',
        onboarding_complete: true,
        subscription_status: 'free',
      },
      token: 'tok',
    });
  });

  it('shows loading spinner initially', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<ProfilePage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders profile header with user name', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<ProfilePage />);
    expect(screen.getByText('Иван')).toBeInTheDocument();
  });

  it('shows subscription info on load', async () => {
    mockGet.mockResolvedValueOnce({
      data: { status: 'none', plan: null, expires_at: null, cancelled_at: null },
    });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    });
  });

  it('shows error state on fetch failure', async () => {
    mockGet.mockRejectedValueOnce({ message: 'Ошибка загрузки' });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Ошибка загрузки')).toBeInTheDocument();
    });
  });

  it('navigates back when back button clicked', async () => {
    mockGet.mockResolvedValueOnce({
      data: { status: 'none', plan: null, expires_at: null, cancelled_at: null },
    });
    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('На главную')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('На главную'));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('shows active subscription details', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        status: 'active',
        plan: 'premium',
        expires_at: '2026-03-01T00:00:00Z',
        cancelled_at: null,
      },
    });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Отменить подписку')).toBeInTheDocument();
    });
  });

  it('shows data export button', async () => {
    mockGet.mockResolvedValueOnce({
      data: { status: 'none', plan: null, expires_at: null, cancelled_at: null },
    });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText(/Экспорт данных/i)).toBeInTheDocument();
    });
  });

  it('shows delete account section', async () => {
    mockGet.mockResolvedValueOnce({
      data: { status: 'none', plan: null, expires_at: null, cancelled_at: null },
    });

    render(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText(/Удалить аккаунт/i)).toBeInTheDocument();
    });
  });
});
