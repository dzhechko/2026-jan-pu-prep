import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { App } from '@/app/App';
import { useUserStore } from '@/entities/user/store';

// Mock the API client to prevent real network requests
vi.mock('@/shared/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('insights')) {
        return Promise.resolve({ data: { insight: { id: '1', title: 'Test', body: 'Test body', action: null, type: 'general', created_at: new Date().toISOString() }, is_locked: false } });
      }
      if (url.includes('payments')) {
        return Promise.resolve({ data: { status: 'none', plan: null, expires_at: null, cancelled_at: null } });
      }
      return Promise.resolve({ data: { patterns: [], risk_today: null } });
    }),
    delete: vi.fn().mockResolvedValue({ data: { status: 'ok', message: 'Подписка отменена' } }),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

beforeEach(() => {
  useUserStore.getState().clearAuth();
});

describe('App', () => {
  it('renders without crashing', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('НутриМайнд')).toBeDefined();
    });
  });

  it('calls Telegram WebApp.ready() on mount', async () => {
    render(<App />);

    await waitFor(() => {
      expect(window.Telegram?.WebApp?.ready).toHaveBeenCalled();
    });
  });

  it('calls Telegram WebApp.expand() on mount', async () => {
    render(<App />);

    await waitFor(() => {
      expect(window.Telegram?.WebApp?.expand).toHaveBeenCalled();
    });
  });
});
