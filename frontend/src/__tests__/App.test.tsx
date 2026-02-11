import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { App } from '@/app/App';

// Mock the Telegram WebApp global
beforeEach(() => {
  // Provide a mock Telegram WebApp object
  window.Telegram = {
    WebApp: {
      initData: 'mock_init_data',
      initDataUnsafe: {
        user: {
          id: 123456789,
          first_name: 'Test',
          last_name: 'User',
          username: 'testuser',
          language_code: 'ru',
        },
      },
      colorScheme: 'light',
      themeParams: {
        bg_color: '#ffffff',
        text_color: '#000000',
        hint_color: '#999999',
        link_color: '#2481cc',
        button_color: '#2481cc',
        button_text_color: '#ffffff',
        secondary_bg_color: '#f0f0f0',
      },
      isExpanded: false,
      viewportHeight: 600,
      viewportStableHeight: 600,
      platform: 'tdesktop',
      version: '7.0',
      ready: vi.fn(),
      expand: vi.fn(),
      close: vi.fn(),
      enableClosingConfirmation: vi.fn(),
      disableClosingConfirmation: vi.fn(),
      setHeaderColor: vi.fn(),
      setBackgroundColor: vi.fn(),
      MainButton: {
        text: '',
        color: '#2481cc',
        textColor: '#ffffff',
        isVisible: false,
        isActive: true,
        show: vi.fn(),
        hide: vi.fn(),
        enable: vi.fn(),
        disable: vi.fn(),
        setText: vi.fn(),
        onClick: vi.fn(),
        offClick: vi.fn(),
        showProgress: vi.fn(),
        hideProgress: vi.fn(),
      },
      BackButton: {
        isVisible: false,
        show: vi.fn(),
        hide: vi.fn(),
        onClick: vi.fn(),
        offClick: vi.fn(),
      },
      HapticFeedback: {
        impactOccurred: vi.fn(),
        notificationOccurred: vi.fn(),
        selectionChanged: vi.fn(),
      },
    },
  };
});

describe('App', () => {
  it('renders without crashing', async () => {
    render(<App />);

    // Wait for the lazy-loaded DashboardPage to appear
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeDefined();
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
