import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';
import { useUserStore } from '@/entities/user/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SubscriptionResponse {
  status: 'active' | 'cancelled' | 'none';
  plan: string | null;
  expires_at: string | null;
  cancelled_at: string | null;
}

interface CancelResponse {
  status: string;
  message: string;
}

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
// Helpers
// ---------------------------------------------------------------------------

function formatRussianDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const user = useUserStore((state) => state.user);

  // Subscription data
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Cancel flow
  const [showConfirm, setShowConfirm] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelResult, setCancelResult] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Fetch subscription
  // -------------------------------------------------------------------------

  const fetchSubscription = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<SubscriptionResponse>('/payments/subscription');
      setSubscription(response.data);
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить данные подписки.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  // -------------------------------------------------------------------------
  // Cancel handler
  // -------------------------------------------------------------------------

  const handleCancelSubscription = useCallback(async () => {
    triggerHapticImpact('medium');
    setCancelling(true);

    try {
      const response = await apiClient.delete<CancelResponse>('/payments/subscription');
      setCancelResult(response.data.message);
      setShowConfirm(false);

      // Update local subscription state to reflect cancellation
      if (subscription) {
        setSubscription({
          ...subscription,
          status: 'cancelled',
        });
      }

      triggerHapticNotification('success');
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось отменить подписку. Попробуйте ещё раз.';
      setError(message);
      setShowConfirm(false);
      triggerHapticNotification('error');
    } finally {
      setCancelling(false);
    }
  }, [subscription]);

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    triggerHapticImpact('light');
    navigate('/');
  }, [navigate]);

  const handleNavigatePaywall = useCallback(() => {
    triggerHapticImpact('light');
    navigate('/paywall');
  }, [navigate]);

  // -------------------------------------------------------------------------
  // Telegram user info
  // -------------------------------------------------------------------------

  const telegramUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
  const displayName = user?.first_name || telegramUser?.first_name || 'Пользователь';
  const username = telegramUser?.username;

  // -------------------------------------------------------------------------
  // Render: Subscription section
  // -------------------------------------------------------------------------

  const renderSubscriptionSection = () => {
    if (loading) {
      return (
        <div className="flex justify-center py-8">
          <Spinner size="md" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
          <p className="mb-4 text-sm text-tg-text">{error}</p>
          <button
            type="button"
            onClick={fetchSubscription}
            className="
              rounded-xl bg-tg-button px-4 py-2
              text-sm font-medium text-tg-button-text
              transition-all duration-150
              hover:opacity-90 active:opacity-80
            "
          >
            Попробовать снова
          </button>
        </div>
      );
    }

    if (!subscription) return null;

    // Cancel result message
    if (cancelResult) {
      return (
        <div className="rounded-2xl bg-tg-secondary-bg p-6">
          <div className="mb-3 flex items-center gap-2">
            <span className="inline-block rounded-lg bg-yellow-400/20 px-2 py-1 text-xs font-semibold text-yellow-700">
              Отменена
            </span>
          </div>
          <p className="text-sm text-tg-text">{cancelResult}</p>
          {subscription.expires_at && (
            <p className="mt-2 text-xs text-tg-hint">
              Доступ до {formatRussianDate(subscription.expires_at)}
            </p>
          )}
        </div>
      );
    }

    // Active subscription
    if (subscription.status === 'active') {
      return (
        <div className="rounded-2xl bg-tg-secondary-bg p-6">
          <div className="mb-3 flex items-center gap-2">
            <span className="inline-block rounded-lg bg-green-500/20 px-2 py-1 text-xs font-semibold text-green-700">
              Premium
            </span>
          </div>
          <p className="text-sm text-tg-text">
            Тариф: <span className="font-medium">{subscription.plan || 'Premium'}</span>
          </p>
          {subscription.expires_at && (
            <p className="mt-1 text-sm text-tg-hint">
              Действует до {formatRussianDate(subscription.expires_at)}
            </p>
          )}
          <button
            type="button"
            onClick={() => {
              triggerHapticImpact('light');
              setShowConfirm(true);
            }}
            className="
              mt-4 rounded-xl border border-red-500/30
              bg-red-500/10 px-4 py-2
              text-sm font-medium text-red-600
              transition-all duration-150
              hover:opacity-90 active:opacity-80
            "
          >
            Отменить подписку
          </button>
        </div>
      );
    }

    // Cancelled subscription
    if (subscription.status === 'cancelled') {
      return (
        <div className="rounded-2xl bg-tg-secondary-bg p-6">
          <div className="mb-3 flex items-center gap-2">
            <span className="inline-block rounded-lg bg-yellow-400/20 px-2 py-1 text-xs font-semibold text-yellow-700">
              Отменена
            </span>
          </div>
          {subscription.expires_at && (
            <p className="text-sm text-tg-text">
              Доступ до {formatRussianDate(subscription.expires_at)}
            </p>
          )}
          <p className="mt-1 text-xs text-tg-hint">
            Подписка не будет продлена автоматически
          </p>
        </div>
      );
    }

    // No subscription (status === 'none')
    return (
      <div className="rounded-2xl bg-tg-secondary-bg p-6">
        <p className="mb-1 text-sm font-medium text-tg-text">Бесплатный план</p>
        <p className="mb-4 text-xs text-tg-hint">
          Ограниченный доступ к инсайтам и функциям
        </p>
        <button
          type="button"
          onClick={handleNavigatePaywall}
          className="
            rounded-xl bg-tg-button px-4 py-2
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          Перейти на Premium
        </button>
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // Render: Confirmation dialog
  // -------------------------------------------------------------------------

  const renderConfirmDialog = () => {
    if (!showConfirm) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-6">
        <div className="w-full max-w-sm rounded-2xl bg-tg-bg p-6">
          <h3 className="mb-2 text-lg font-semibold text-tg-text">
            Вы уверены?
          </h3>
          <p className="mb-6 text-sm text-tg-hint">
            Вы потеряете доступ к Premium функциям после окончания текущего периода.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={cancelling}
              onClick={() => {
                triggerHapticImpact('light');
                setShowConfirm(false);
              }}
              className="
                flex-1 rounded-xl border border-tg-hint/20
                bg-tg-secondary-bg py-2.5
                text-sm font-medium text-tg-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              Оставить
            </button>
            <button
              type="button"
              disabled={cancelling}
              onClick={handleCancelSubscription}
              className="
                flex-1 rounded-xl
                bg-red-500 py-2.5
                text-sm font-medium text-white
                transition-all duration-150
                hover:opacity-90 active:opacity-80
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              {cancelling ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <Spinner size="sm" />
                </span>
              ) : (
                'Отменить'
              )}
            </button>
          </div>
        </div>
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Confirmation dialog overlay */}
      {renderConfirmDialog()}

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tg-text">Профиль</h1>
      </div>

      {/* User info */}
      <div className="mb-6 rounded-2xl bg-tg-secondary-bg p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-tg-button/15">
            <span className="text-xl font-bold text-tg-button">
              {displayName.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-tg-text">{displayName}</p>
            {username && (
              <p className="text-sm text-tg-hint">@{username}</p>
            )}
          </div>
        </div>
      </div>

      {/* Subscription section */}
      <div className="mb-6">
        <h2 className="mb-3 text-lg font-semibold text-tg-text">Подписка</h2>
        {renderSubscriptionSection()}
      </div>

      {/* Back button */}
      <button
        type="button"
        onClick={handleBack}
        className="
          w-full rounded-xl border border-tg-hint/20
          bg-tg-secondary-bg py-3
          text-sm font-medium text-tg-text
          transition-all duration-150
          hover:opacity-90 active:opacity-80
        "
      >
        На главную
      </button>
    </div>
  );
};

export default ProfilePage;
