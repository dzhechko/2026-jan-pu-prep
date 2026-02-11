import React, { useEffect, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { Providers } from './providers';
import { useTelegram } from '@/shared/hooks/useTelegram';
import { useAuth } from '@/shared/hooks/useAuth';
import { Spinner } from '@/shared/ui';

export const App: React.FC = () => {
  const { webApp, isReady, colorScheme, initData } = useTelegram();
  const { login, isAuthenticated, user } = useAuth();
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Initialize Telegram WebApp
  useEffect(() => {
    if (webApp) {
      webApp.ready();
      webApp.expand();
      if (webApp.themeParams.header_bg_color) {
        webApp.setHeaderColor(webApp.themeParams.header_bg_color);
      }
      if (webApp.themeParams.bg_color) {
        webApp.setBackgroundColor(webApp.themeParams.bg_color);
      }
      webApp.enableClosingConfirmation();
    }
  }, [webApp]);

  // Auto-authenticate with Telegram initData
  useEffect(() => {
    const authenticate = async () => {
      if (isAuthenticated) {
        setAuthLoading(false);
        return;
      }

      if (!initData) {
        // No initData available — either not in Telegram or dev mode
        if (import.meta.env.DEV) {
          setAuthLoading(false);
        }
        return;
      }

      try {
        await login(initData);
      } catch {
        setAuthError('Ошибка авторизации. Попробуйте перезапустить приложение.');
      } finally {
        setAuthLoading(false);
      }
    };

    authenticate();
  }, [initData, isAuthenticated, login]);

  // Redirect based on onboarding status
  useEffect(() => {
    if (!isAuthenticated || !user) return;

    const currentPath = window.location.hash.replace('#', '') || '/';
    if (!user.onboarding_complete && currentPath === '/') {
      window.location.hash = '#/onboarding';
    }
  }, [isAuthenticated, user]);

  // Apply color scheme class for Tailwind dark mode
  useEffect(() => {
    const root = document.documentElement;
    if (colorScheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [colorScheme]);

  // Not inside Telegram (production)
  if (!isReady && !import.meta.env.DEV) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-tg-bg p-6 text-center">
        <div className="text-4xl">📱</div>
        <h1 className="text-xl font-bold text-tg-text">НутриМайнд</h1>
        <p className="text-tg-hint">
          Откройте это приложение через Telegram
        </p>
        <a
          href="https://t.me/nutrimind_bot"
          className="mt-2 rounded-lg bg-tg-button px-6 py-3 font-medium text-tg-button-text"
        >
          Открыть в Telegram
        </a>
      </div>
    );
  }

  // Auth loading
  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-tg-bg">
        <Spinner size="lg" />
      </div>
    );
  }

  // Auth error
  if (authError) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-tg-bg p-6 text-center">
        <p className="text-tg-text">{authError}</p>
        <button
          className="rounded-lg bg-tg-button px-6 py-3 font-medium text-tg-button-text"
          onClick={() => window.location.reload()}
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
};
