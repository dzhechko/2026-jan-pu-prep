import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import LessonsPage from '../LessonsPage';

const mockGet = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
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

const lessonsList = {
  lessons: [
    { id: 'l1', title: 'Основы CBT', lesson_order: 1, duration_min: 10, completed: false },
    { id: 'l2', title: 'Когнитивные искажения', lesson_order: 2, duration_min: 15, completed: true },
  ],
  progress: { current: 1, total: 2 },
};

describe('LessonsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<LessonsPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows error state and retry button on failure', async () => {
    mockGet.mockRejectedValue({ message: 'Network error' });
    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
    expect(screen.getByText('Попробовать снова')).toBeInTheDocument();
  });

  it('renders lessons list on success', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/lessons') {
        return Promise.resolve({ data: lessonsList });
      }
      // /lessons/recommended
      return Promise.resolve({ data: { lesson: { id: 'l1' }, progress: { current: 1, total: 2 } } });
    });

    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
      expect(screen.getByText('Когнитивные искажения')).toBeInTheDocument();
    });
  });

  it('shows progress bar', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/lessons') {
        return Promise.resolve({ data: lessonsList });
      }
      return Promise.resolve({ data: { lesson: { id: 'l1' }, progress: { current: 1, total: 2 } } });
    });

    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText(/1 \/ 2 уроков/)).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  it('handles null recommended lesson response', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/lessons') {
        return Promise.resolve({ data: lessonsList });
      }
      return Promise.resolve({ data: null });
    });

    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
    });
  });

  it('shows empty state when no lessons', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/lessons') {
        return Promise.resolve({ data: { lessons: [], progress: { current: 0, total: 0 } } });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Уроки пока не доступны/)).toBeInTheDocument();
    });
  });

  it('navigates to lesson on tap', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/lessons') {
        return Promise.resolve({ data: lessonsList });
      }
      return Promise.resolve({ data: { lesson: { id: 'l1' }, progress: { current: 1, total: 2 } } });
    });

    render(<LessonsPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Основы CBT'));
    expect(mockNavigate).toHaveBeenCalledWith('/lessons/l1');
  });

  it('navigates back when back button clicked', async () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<LessonsPage />);
    fireEvent.click(screen.getByText(/Назад/));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});
