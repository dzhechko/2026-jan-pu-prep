import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import LessonDetailPage from '../LessonDetailPage';

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
    useParams: () => ({ id: 'l1' }),
  };
});

const lessonResponse = {
  lesson: {
    id: 'l1',
    title: 'Основы CBT',
    content_md: '# Введение\n\nЭто первый урок по когнитивно-поведенческой терапии.',
    duration_min: 10,
  },
  progress: { current: 0, total: 5 },
};

describe('LessonDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<LessonDetailPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders lesson content on successful load', async () => {
    mockGet.mockResolvedValueOnce({ data: lessonResponse });

    render(<LessonDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
    });
  });

  it('shows error state on failure', async () => {
    mockGet.mockRejectedValueOnce({ message: 'Не найден' });

    render(<LessonDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Не найден')).toBeInTheDocument();
    });
  });

  it('navigates back when back button clicked', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<LessonDetailPage />);
    fireEvent.click(screen.getByText(/К урокам/));
    expect(mockNavigate).toHaveBeenCalledWith('/lessons');
  });

  it('shows complete button', async () => {
    mockGet.mockResolvedValueOnce({ data: lessonResponse });

    render(<LessonDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
    });

    expect(screen.getByText('Пройден')).toBeInTheDocument();
  });

  it('marks lesson complete on button click', async () => {
    mockGet.mockResolvedValueOnce({ data: lessonResponse });
    mockPost.mockResolvedValueOnce({
      data: { status: 'ok', newly_completed: true },
    });

    render(<LessonDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Основы CBT')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Пройден'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/lessons/l1/complete');
    });
  });
});
