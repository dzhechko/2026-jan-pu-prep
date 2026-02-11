import { useMemo } from 'react';

/**
 * Telegram WebApp type declarations for the global Telegram object.
 * These mirror the subset of the Telegram Mini Apps API we use.
 */
interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
  header_bg_color?: string;
  accent_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  subtitle_text_color?: string;
  destructive_text_color?: string;
}

interface WebAppInitData {
  user?: TelegramUser;
  auth_date?: number;
  hash?: string;
  query_id?: string;
  start_param?: string;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: WebAppInitData;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  platform: string;
  version: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
  };
  BackButton: {
    isVisible: boolean;
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

/** Mock user for development outside Telegram */
const MOCK_USER: TelegramUser = {
  id: 123456789,
  first_name: 'Dev',
  last_name: 'User',
  username: 'devuser',
  language_code: 'ru',
  is_premium: false,
};

/** Mock theme params for development */
const MOCK_THEME: ThemeParams = {
  bg_color: '#ffffff',
  text_color: '#000000',
  hint_color: '#999999',
  link_color: '#2481cc',
  button_color: '#2481cc',
  button_text_color: '#ffffff',
  secondary_bg_color: '#f0f0f0',
};

export interface UseTelegramReturn {
  webApp: TelegramWebApp | null;
  user: TelegramUser | null;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isReady: boolean;
  initData: string;
}

export function useTelegram(): UseTelegramReturn {
  const webApp = window.Telegram?.WebApp ?? null;
  const isReady = webApp !== null;

  const user = useMemo(() => {
    if (webApp?.initDataUnsafe?.user) {
      return webApp.initDataUnsafe.user;
    }
    // Fallback mock for development outside Telegram
    if (import.meta.env.DEV) {
      return MOCK_USER;
    }
    return null;
  }, [webApp]);

  const colorScheme = webApp?.colorScheme ?? 'light';

  const themeParams = useMemo(() => {
    if (webApp?.themeParams) {
      return webApp.themeParams;
    }
    return MOCK_THEME;
  }, [webApp]);

  const initData = webApp?.initData ?? '';

  return {
    webApp,
    user,
    colorScheme,
    themeParams,
    isReady,
    initData,
  };
}
