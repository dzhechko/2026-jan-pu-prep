import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubscribeResponse {
  status: string;
  plan: string;
  expires_at: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PREMIUM_FEATURES = [
  {
    icon: '\u{1F4A1}',
    title: 'Безлимитные AI инсайты',
    description: 'Ежедневный персональный анализ без ограничений',
  },
  {
    icon: '\u{1F3AF}',
    title: 'Персонализированные рекомендации',
    description: 'Индивидуальные советы на основе ваших данных',
  },
  {
    icon: '\u{1F9E0}',
    title: 'Полный доступ к CBT урокам',
    description: 'Все техники когнитивно-поведенческой терапии',
  },
  {
    icon: '\u{1F4CA}',
    title: 'Продвинутый анализ паттернов',
    description: 'Глубокий анализ пищевых привычек и триггеров',
  },
];

// ---------------------------------------------------------------------------
// Haptic helpers
// ---------------------------------------------------------------------------

function triggerHapticImpact(style: 'light' | 'medium' | 'heavy'): void {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style);
  } catch {
    // Best-effort
  }
}

function triggerHapticNotification(type: 'success' | 'error' | 'warning'): void {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred(type);
  } catch {
    // Best-effort
  }
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const PaywallPage: React.FC = () => {
  const navigate = useNavigate();

  const [subscribing, setSubscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // -------------------------------------------------------------------------
  // Subscribe handler
  // -------------------------------------------------------------------------

  const handleSubscribe = useCallback(async () => {
    triggerHapticImpact('light');
    setSubscribing(true);
    setError(null);

    try {
      await apiClient.post<SubscribeResponse>('/payments/subscribe', {});
      setSuccess(true);
      triggerHapticNotification('success');
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось оформить подписку. Попробуйте ещё раз.';
      setError(message);
      triggerHapticNotification('error');
    } finally {
      setSubscribing(false);
    }
  }, []);

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleDismiss = useCallback(() => {
    triggerHapticImpact('light');
    navigate(-1);
  }, [navigate]);

  // -------------------------------------------------------------------------
  // Render: Success state
  // -------------------------------------------------------------------------

  if (success) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-tg-bg px-4 pb-8 pt-6">
        <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-green-500/15">
          <span className="text-4xl">{'\u2705'}</span>
        </div>
        <h2 className="mb-2 text-xl font-bold text-tg-text">
          Спасибо! Premium активирован
        </h2>
        <p className="mb-8 text-center text-sm text-tg-hint">
          Теперь вам доступны все функции НутриМайнд
        </p>
        <button
          type="button"
          onClick={() => {
            triggerHapticImpact('light');
            navigate('/');
          }}
          className="
            rounded-xl bg-tg-button px-6 py-3
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          На главную
        </button>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render: Main paywall
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6 text-center">
        <span className="mb-2 inline-block text-4xl">{'\u2728'}</span>
        <h1 className="text-2xl font-bold text-tg-text">
          НутриМайнд Premium
        </h1>
        <p className="mt-2 text-sm text-tg-hint">
          Раскройте полный потенциал заботы о себе
        </p>
      </div>

      {/* Features list */}
      <div className="mb-6 flex flex-col gap-3">
        {PREMIUM_FEATURES.map((feature) => (
          <div
            key={feature.title}
            className="flex items-start gap-3 rounded-2xl bg-tg-secondary-bg p-4"
          >
            <span className="text-2xl leading-none">{feature.icon}</span>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-tg-text">
                {feature.title}
              </h3>
              <p className="mt-0.5 text-xs text-tg-hint">
                {feature.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Pricing card */}
      <div className="mb-6 rounded-2xl bg-tg-secondary-bg p-6 text-center">
        <p className="mb-1 text-sm text-tg-hint">Стоимость подписки</p>
        <p className="text-3xl font-bold text-tg-text">
          499 <span className="text-lg font-normal text-tg-hint">{'\u20BD'}/мес</span>
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-4 rounded-2xl bg-red-500/10 p-4 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Subscribe button */}
      <button
        type="button"
        disabled={subscribing}
        onClick={handleSubscribe}
        className="
          mb-4 w-full rounded-xl bg-tg-button py-3
          text-base font-semibold text-tg-button-text
          transition-all duration-150
          hover:opacity-90 active:opacity-80
          disabled:cursor-not-allowed disabled:opacity-50
        "
      >
        {subscribing ? (
          <span className="inline-flex items-center gap-2">
            <Spinner size="sm" />
            Оформление...
          </span>
        ) : (
          'Подписаться'
        )}
      </button>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={handleDismiss}
        className="
          w-full py-3
          text-sm font-medium text-tg-hint
          transition-all duration-150
          hover:opacity-70 active:opacity-60
        "
      >
        Не сейчас
      </button>
    </div>
  );
};

export default PaywallPage;
