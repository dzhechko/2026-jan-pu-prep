import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@/test-utils';
import { useUserStore } from '@/entities/user/store';
import OnboardingPage from '../OnboardingPage';

const mockPost = vi.fn();
const mockNavigate = vi.fn();

vi.mock('@/shared/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockPost(...args),
    get: vi.fn(),
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

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: 'Test',
        onboarding_complete: false,
        subscription_status: 'free',
      },
      token: 'tok',
    });
    localStorage.clear();
  });

  it('renders both questions', () => {
    render(<OnboardingPage />);
    expect(screen.getByText('Как бы вы описали свой режим питания?')).toBeInTheDocument();
    expect(screen.getByText('Какая ваша главная трудность?')).toBeInTheDocument();
  });

  it('renders all options for each question', () => {
    render(<OnboardingPage />);
    expect(screen.getByText('Регулярное — 3 раза в день')).toBeInTheDocument();
    expect(screen.getByText('Переедание')).toBeInTheDocument();
  });

  it('shows submit button disabled initially', () => {
    render(<OnboardingPage />);
    const btn = screen.getByRole('button', { name: 'Готово' });
    expect(btn).toBeDisabled();
  });

  it('enables submit after answering all questions', () => {
    render(<OnboardingPage />);

    fireEvent.click(screen.getByText('Регулярное — 3 раза в день'));
    fireEvent.click(screen.getByText('Переедание'));

    const btn = screen.getByRole('button', { name: 'Готово' });
    expect(btn).not.toBeDisabled();
  });

  it('persists answers to localStorage', () => {
    render(<OnboardingPage />);
    fireEvent.click(screen.getByText('Регулярное — 3 раза в день'));

    const saved = localStorage.getItem('nutrimind-onboarding-answers');
    expect(saved).toBeTruthy();
    const parsed = JSON.parse(saved as string);
    expect(parsed.eating_schedule).toBe('regular');
  });

  it('submits answers and navigates on success', async () => {
    mockPost.mockResolvedValueOnce({ data: { status: 'ok' } });

    render(<OnboardingPage />);

    fireEvent.click(screen.getByText('Регулярное — 3 раза в день'));
    fireEvent.click(screen.getByText('Переедание'));
    fireEvent.click(screen.getByRole('button', { name: 'Готово' }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/onboarding/interview', {
        answers: [
          { question_id: 'eating_schedule', answer_id: 'regular' },
          { question_id: 'biggest_challenge', answer_id: 'overeating' },
        ],
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValueOnce({ message: 'Server error' });

    render(<OnboardingPage />);

    fireEvent.click(screen.getByText('Регулярное — 3 раза в день'));
    fireEvent.click(screen.getByText('Переедание'));
    fireEvent.click(screen.getByRole('button', { name: 'Готово' }));

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
  });

  it('clears localStorage on successful submit', async () => {
    mockPost.mockResolvedValueOnce({ data: { status: 'ok' } });

    render(<OnboardingPage />);

    fireEvent.click(screen.getByText('Регулярное — 3 раза в день'));
    fireEvent.click(screen.getByText('Переедание'));
    fireEvent.click(screen.getByRole('button', { name: 'Готово' }));

    await waitFor(() => {
      expect(localStorage.getItem('nutrimind-onboarding-answers')).toBeNull();
    });
  });
});
