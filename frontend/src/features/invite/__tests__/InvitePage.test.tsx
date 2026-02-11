import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test-utils';
import InvitePage from '../InvitePage';

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

describe('InvitePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<InvitePage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders invite page with empty invites', async () => {
    mockGet.mockResolvedValueOnce({
      data: { invites: [], total_redeemed: 0 },
    });

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/Пригласить друга/i)).toBeInTheDocument();
    });
  });

  it('shows error on fetch failure', async () => {
    mockGet.mockRejectedValueOnce({ message: 'Ошибка сети' });

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText('Ошибка сети')).toBeInTheDocument();
    });
  });

  it('generates invite code', async () => {
    mockGet.mockResolvedValueOnce({
      data: { invites: [], total_redeemed: 0 },
    });
    mockPost.mockResolvedValueOnce({
      data: { invite_code: 'ABC12345', share_url: 'https://t.me/bot?start=ABC12345' },
    });

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/Создать приглашение/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Создать приглашение/i));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/invite/generate');
    });
  });

  it('navigates back when back button clicked', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<InvitePage />);
    fireEvent.click(screen.getByText(/Назад/));
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  it('shows invites list when data loaded', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        invites: [
          { code: 'INV123', status: 'redeemed', created_at: '2026-01-01', redeemed_at: '2026-01-02' },
        ],
        total_redeemed: 1,
      },
    });

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/INV123/)).toBeInTheDocument();
    });
  });
});
