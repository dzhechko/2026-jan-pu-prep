import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import { useUserStore } from '@/entities/user/store';
import DashboardPage from '../DashboardPage';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
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

describe('DashboardPage', () => {
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
    render(<DashboardPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows greeting with user name', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText('Привет, Иван!')).toBeInTheDocument();
  });

  it('shows generic greeting when no user', () => {
    useUserStore.getState().clearAuth();
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText('Привет!')).toBeInTheDocument();
  });

  it('renders patterns on successful load', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/patterns') {
        return Promise.resolve({
          data: {
            patterns: [
              {
                id: 'p1',
                type: 'time',
                description_ru: 'Поздний ужин после 21:00',
                confidence: 0.8,
                discovered_at: '2026-01-01',
              },
            ],
            risk_today: null,
          },
        });
      }
      // insights/today
      return Promise.resolve({
        data: {
          insight: { id: 'i1', title: 'Инсайт', body: 'Тело', action: null, type: 'general', created_at: '2026-01-01' },
          is_locked: false,
        },
      });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Поздний ужин после 21:00')).toBeInTheDocument();
    });
  });

  it('shows empty state when no patterns', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/patterns') {
        return Promise.resolve({
          data: { patterns: [], risk_today: null },
        });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Недостаточно данных для анализа/)).toBeInTheDocument();
    });
  });

  it('shows error state and retry button', async () => {
    mockGet.mockRejectedValue({ message: 'Ошибка сервера' });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Ошибка сервера')).toBeInTheDocument();
    });
    expect(screen.getByText('Попробовать снова')).toBeInTheDocument();
  });

  it('navigates to food-log on button click', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    fireEvent.click(screen.getByText('Записать еду'));
    expect(mockNavigate).toHaveBeenCalledWith('/food-log');
  });

  it('navigates to lessons on button click', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    fireEvent.click(screen.getByText('Уроки CBT'));
    expect(mockNavigate).toHaveBeenCalledWith('/lessons');
  });

  it('navigates to profile on button click', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    fireEvent.click(screen.getByText('Профиль'));
    expect(mockNavigate).toHaveBeenCalledWith('/profile');
  });

  it('shows risk card when risk_today is present', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/patterns') {
        return Promise.resolve({
          data: {
            patterns: [],
            risk_today: {
              level: 'high',
              time_window: '18:00-22:00',
              recommendation: 'Будьте внимательны к вечернему перекусу',
            },
          },
        });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Риск сегодня')).toBeInTheDocument();
      expect(screen.getByText('Будьте внимательны к вечернему перекусу')).toBeInTheDocument();
    });
  });
});
