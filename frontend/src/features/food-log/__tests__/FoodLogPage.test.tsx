import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test-utils';
import FoodLogPage from '../FoodLogPage';

const mockPost = vi.fn();
const mockGet = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
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

describe('FoodLogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: { entries: [], total: 0 } });
  });

  it('renders the food input form', () => {
    render(<FoodLogPage />);
    expect(screen.getByText('Запись еды')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Что вы съели?')).toBeInTheDocument();
  });

  it('renders mood options', () => {
    render(<FoodLogPage />);
    expect(screen.getByText('Настроение')).toBeInTheDocument();
    expect(screen.getByText('Отлично')).toBeInTheDocument();
    expect(screen.getByText('Плохо')).toBeInTheDocument();
  });

  it('renders context options', () => {
    render(<FoodLogPage />);
    expect(screen.getByText('Контекст')).toBeInTheDocument();
    expect(screen.getByText('Дом')).toBeInTheDocument();
    expect(screen.getByText('Работа')).toBeInTheDocument();
  });

  it('shows character count', () => {
    render(<FoodLogPage />);
    expect(screen.getByText('0/500')).toBeInTheDocument();
  });

  it('submit button is disabled when text is empty', () => {
    render(<FoodLogPage />);
    const btn = screen.getByRole('button', { name: 'Записать' });
    expect(btn).toBeDisabled();
  });

  it('enables submit when text is entered', () => {
    render(<FoodLogPage />);
    const textarea = screen.getByPlaceholderText('Что вы съели?');
    fireEvent.change(textarea, { target: { value: 'Каша овсяная' } });
    const btn = screen.getByRole('button', { name: 'Записать' });
    expect(btn).not.toBeDisabled();
  });

  it('shows empty history message after loading', async () => {
    render(<FoodLogPage />);

    await waitFor(() => {
      expect(screen.getByText('Записей пока нет')).toBeInTheDocument();
    });
  });

  it('submits food log and calls API with correct payload', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        entry_id: 'e1',
        parsed_items: [
          { name: 'Овсянка', calories: 250, category: 'green' },
        ],
        total_calories: 250,
      },
    });

    render(<FoodLogPage />);

    // Wait for initial history load
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalled();
    });

    const textarea = screen.getByPlaceholderText('Что вы съели?');
    fireEvent.change(textarea, { target: { value: 'Овсянка утром' } });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/food/log', {
        raw_text: 'Овсянка утром',
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Результат')).toBeInTheDocument();
    });
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValueOnce({ message: 'Ошибка сервера' });

    render(<FoodLogPage />);

    const textarea = screen.getByPlaceholderText('Что вы съели?');
    fireEvent.change(textarea, { target: { value: 'Еда' } });
    fireEvent.click(screen.getByRole('button', { name: 'Записать' }));

    await waitFor(() => {
      expect(screen.getByText('Ошибка сервера')).toBeInTheDocument();
    });
  });

  it('fetches and displays history entries', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        entries: [
          {
            id: 'h1',
            raw_text: 'Борщ с хлебом',
            total_calories: 450,
            mood: 'great',
            context: 'home',
            logged_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
    });

    render(<FoodLogPage />);

    await waitFor(() => {
      expect(screen.getByText('Борщ с хлебом')).toBeInTheDocument();
      expect(screen.getByText('450 ккал')).toBeInTheDocument();
    });
  });

  it('navigates back when back button clicked', () => {
    render(<FoodLogPage />);
    const backBtn = screen.getByText(/Назад/);
    fireEvent.click(backBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});
