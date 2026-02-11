import React, { useEffect, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { Providers } from './providers';
import { useTelegram } from '@/shared/hooks/useTelegram';
import { Spinner } from '@/shared/ui';

export const App: React.FC = () => {
  const { webApp, isReady, colorScheme } = useTelegram();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (webApp) {
      // Signal to Telegram that the app is ready
      webApp.ready();

      // Expand to full viewport height
      webApp.expand();

      // Apply theme colors
      if (webApp.themeParams.header_bg_color) {
        webApp.setHeaderColor(webApp.themeParams.header_bg_color);
      }
      if (webApp.themeParams.bg_color) {
        webApp.setBackgroundColor(webApp.themeParams.bg_color);
      }

      // Enable closing confirmation to prevent accidental closure
      webApp.enableClosingConfirmation();
    }

    // Mark as initialized even in dev mode (outside Telegram)
    setInitialized(true);
  }, [webApp]);

  // Apply color scheme class for Tailwind dark mode support
  useEffect(() => {
    const root = document.documentElement;
    if (colorScheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [colorScheme]);

  if (!initialized) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-tg-bg">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isReady && !import.meta.env.DEV) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-tg-bg p-4">
        <Spinner size="lg" />
        <p className="text-tg-hint text-sm">
          Please open this app inside Telegram.
        </p>
      </div>
    );
  }

  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
};
