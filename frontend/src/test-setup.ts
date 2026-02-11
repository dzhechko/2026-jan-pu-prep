import { vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';

// Telegram WebApp mock - reusable across all tests
function createTelegramWebAppMock() {
  return {
    WebApp: {
      initData: '',
      initDataUnsafe: {
        user: {
          id: 123456789,
          first_name: 'Test',
          last_name: 'User',
          username: 'testuser',
          language_code: 'ru',
        },
      },
      colorScheme: 'light' as const,
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
}

beforeEach(() => {
  window.Telegram = createTelegramWebAppMock();
  localStorage.clear();
});
