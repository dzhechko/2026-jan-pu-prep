import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import InsightsPage from '../InsightsPage';

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

const insightData = {
  insight: {
    id: 'i1',
    title: 'Ваш прогресс',
    body: 'Вы записали еду 5 дней подряд — отличный результат!',
    action: null,
    type: 'progress' as const,
    created_at: '2026-01-15T10:00:00Z',
  },
  is_locked: false,
};

describe('InsightsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<InsightsPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders insight on successful load', async () => {
    mockGet.mockResolvedValueOnce({ data: insightData });

    render(<InsightsPage />);

    await waitFor(() => {
      expect(screen.getByText('Ваш прогресс')).toBeInTheDocument();
      expect(screen.getByText(/записали еду 5 дней/)).toBeInTheDocument();
    });
  });

  it('shows error state on failure', async () => {
    mockGet.mockRejectedValueOnce({ message: 'Ошибка загрузки' });

    render(<InsightsPage />);

    await waitFor(() => {
      expect(screen.getByText('Ошибка загрузки')).toBeInTheDocument();
    });
  });

  it('shows locked state for paywall', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        ...insightData,
        is_locked: true,
      },
    });

    render(<InsightsPage />);

    await waitFor(() => {
      expect(screen.getByText('Ваш прогресс')).toBeInTheDocument();
    });
  });

  it('navigates back when back button clicked', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<InsightsPage />);
    fireEvent.click(screen.getByText(/Назад/));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('shows retry button on error', async () => {
    mockGet.mockRejectedValueOnce({ message: 'Ошибка' });

    render(<InsightsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Попробовать снова/)).toBeInTheDocument();
    });
  });
});
