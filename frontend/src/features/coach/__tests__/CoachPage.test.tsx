import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import { useUserStore } from '@/entities/user/store';
import CoachPage from '../CoachPage';

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

describe('CoachPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: '\u0418\u0432\u0430\u043D',
        onboarding_complete: true,
        subscription_status: 'premium',
      },
      token: 'tok',
    });
  });

  it('renders chat history on load', async () => {
    mockGet.mockResolvedValue({
      data: {
        messages: [
          {
            id: 'm1',
            role: 'user',
            content: '\u041F\u0440\u0438\u0432\u0435\u0442!',
            created_at: '2026-01-01T10:00:00Z',
          },
          {
            id: 'm2',
            role: 'assistant',
            content: '\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!',
            created_at: '2026-01-01T10:00:01Z',
          },
        ],
        has_more: false,
      },
    });

    render(<CoachPage />);

    await waitFor(() => {
      expect(screen.getByText('\u041F\u0440\u0438\u0432\u0435\u0442!')).toBeInTheDocument();
      expect(screen.getByText('\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!')).toBeInTheDocument();
    });
  });

  it('sends message and displays response', async () => {
    // Start with empty history
    mockGet.mockResolvedValue({
      data: { messages: [], has_more: false },
    });

    mockPost.mockResolvedValue({
      data: {
        message: {
          id: 'resp-1',
          role: 'assistant',
          content: '\u0421\u043E\u0432\u0435\u0442 \u043A\u043E\u0443\u0447\u0430',
          created_at: '2026-01-01T10:00:01Z',
        },
      },
    });

    render(<CoachPage />);

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('\u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435...');
    fireEvent.change(textarea, { target: { value: '\u041F\u043E\u043C\u043E\u0433\u0438\u0442\u0435' } });

    const sendButton = screen.getByText('\u27A4');
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText('\u0421\u043E\u0432\u0435\u0442 \u043A\u043E\u0443\u0447\u0430')).toBeInTheDocument();
    });

    expect(mockPost).toHaveBeenCalledWith('/coach/message', {
      content: '\u041F\u043E\u043C\u043E\u0433\u0438\u0442\u0435',
    });
  });

  it('shows loading spinner while fetching history', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<CoachPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows empty state when no messages', async () => {
    mockGet.mockResolvedValue({
      data: { messages: [], has_more: false },
    });

    render(<CoachPage />);

    await waitFor(() => {
      expect(screen.getByText('\u0414\u043E\u0431\u0440\u043E \u043F\u043E\u0436\u0430\u043B\u043E\u0432\u0430\u0442\u044C!')).toBeInTheDocument();
    });
  });

  it('redirects free users to paywall', () => {
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: '\u0418\u0432\u0430\u043D',
        onboarding_complete: true,
        subscription_status: 'free',
      },
      token: 'tok',
    });

    mockGet.mockReturnValue(new Promise(() => {}));
    render(<CoachPage />);
    expect(mockNavigate).toHaveBeenCalledWith('/paywall');
  });
});
