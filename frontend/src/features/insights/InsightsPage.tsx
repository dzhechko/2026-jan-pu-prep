import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type InsightType = 'pattern' | 'progress' | 'cbt' | 'risk' | 'general';
type FeedbackRating = 'positive' | 'negative';

interface InsightData {
  id: string;
  title: string;
  body: string;
  action: string | null;
  type: InsightType;
  created_at: string;
}

interface TodayInsightResponse {
  insight: InsightData;
  is_locked: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INSIGHT_TYPE_ICONS: Record<InsightType, string> = {
  pattern: '\u{1F50D}',
  progress: '\u{1F4C8}',
  cbt: '\u{1F9E0}',
  risk: '\u{26A0}\uFE0F',
  general: '\u{1F4A1}',
};

const INSIGHT_TYPE_LABELS: Record<InsightType, string> = {
  pattern: 'Анализ паттернов',
  progress: 'Прогресс',
  cbt: 'Техника CBT',
  risk: 'Оценка рисков',
  general: 'Общий инсайт',
};

const ACTION_BOX_CLASSES: Record<InsightType, string> = {
  pattern: 'bg-blue-500/10 border-blue-500/20',
  progress: 'bg-green-500/10 border-green-500/20',
  cbt: 'bg-purple-500/10 border-purple-500/20',
  risk: 'bg-orange-500/10 border-orange-500/20',
  general: 'bg-yellow-500/10 border-yellow-500/20',
};

const SEEN_DELAY_MS = 3000;

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

const InsightsPage: React.FC = () => {
  const navigate = useNavigate();

  // Data state
  const [insight, setInsight] = useState<InsightData | null>(null);
  const [isLocked, setIsLocked] = useState(false);

  // Loading & error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Feedback state
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  // Seen tracking
  const seenSent = useRef(false);

  // -------------------------------------------------------------------------
  // Fetch today's insight
  // -------------------------------------------------------------------------

  const fetchInsight = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<TodayInsightResponse>('/insights/today');
      setInsight(response.data.insight);
      setIsLocked(response.data.is_locked);
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить инсайт. Попробуйте ещё раз.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInsight();
  }, [fetchInsight]);

  // -------------------------------------------------------------------------
  // Mark as seen after 3 seconds
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!insight || isLocked || seenSent.current) return;

    const timer = setTimeout(() => {
      if (!seenSent.current) {
        seenSent.current = true;
        apiClient.post(`/insights/${insight.id}/seen`).catch(() => {
          // Best-effort: don't block UI on failure
        });
      }
    }, SEEN_DELAY_MS);

    return () => clearTimeout(timer);
  }, [insight, isLocked]);

  // -------------------------------------------------------------------------
  // Feedback handler
  // -------------------------------------------------------------------------

  const handleFeedback = useCallback(
    async (rating: FeedbackRating) => {
      if (!insight || feedbackGiven || feedbackLoading) return;

      triggerHapticNotification('success');
      setFeedbackLoading(true);

      try {
        await apiClient.post(`/insights/${insight.id}/feedback`, { rating });
        setFeedbackGiven(true);
      } catch {
        // Silently fail for feedback
      } finally {
        setFeedbackLoading(false);
      }
    },
    [insight, feedbackGiven, feedbackLoading],
  );

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleNavigate = useCallback(
    (path: string) => {
      triggerHapticImpact('light');
      navigate(path);
    },
    [navigate],
  );

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  const renderLockedOverlay = () => (
    <div className="relative">
      <div className="select-none text-sm leading-relaxed text-tg-text blur-sm">
        {insight!.body}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl bg-tg-secondary-bg/80 p-4">
        <span className="mb-2 text-3xl">{'\u{1F512}'}</span>
        <p className="mb-3 text-center text-sm font-medium text-tg-text">
          Разблокируйте Premium для полного доступа
        </p>
        <button
          type="button"
          onClick={() => handleNavigate('/paywall')}
          className="
            rounded-xl bg-tg-button px-4 py-2
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          Подробнее о Premium
        </button>
      </div>
    </div>
  );

  const renderInsightBody = () => (
    <>
      <p className="whitespace-pre-line text-sm leading-relaxed text-tg-text">
        {insight!.body}
      </p>

      {insight!.action && (
        <div
          className={`mt-4 rounded-xl border p-3 ${ACTION_BOX_CLASSES[insight!.type]}`}
        >
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-tg-hint">
            Рекомендация
          </p>
          <p className="text-sm text-tg-text">{insight!.action}</p>
        </div>
      )}
    </>
  );

  const renderFeedbackSection = () => {
    if (isLocked) return null;

    return (
      <div className="mt-4 rounded-2xl bg-tg-secondary-bg p-4">
        <p className="mb-3 text-sm font-medium text-tg-text">
          Этот инсайт был полезен?
        </p>

        {feedbackGiven ? (
          <p className="text-sm text-tg-hint">Спасибо за отзыв</p>
        ) : (
          <div className="flex gap-3">
            <button
              type="button"
              disabled={feedbackLoading}
              onClick={() => handleFeedback('positive')}
              className="
                flex items-center gap-2 rounded-xl
                border border-tg-hint/20 bg-tg-bg
                px-4 py-2 text-sm font-medium text-tg-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              {feedbackLoading ? (
                <Spinner size="sm" />
              ) : (
                <>{'\u{1F44D}'} Полезно</>
              )}
            </button>
            <button
              type="button"
              disabled={feedbackLoading}
              onClick={() => handleFeedback('negative')}
              className="
                flex items-center gap-2 rounded-xl
                border border-tg-hint/20 bg-tg-bg
                px-4 py-2 text-sm font-medium text-tg-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              {feedbackLoading ? (
                <Spinner size="sm" />
              ) : (
                <>{'\u{1F44E}'} Не очень</>
              )}
            </button>
          </div>
        )}
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="mb-2 text-sm font-medium text-tg-link"
        >
          &larr; Назад
        </button>
        <h1 className="text-2xl font-bold text-tg-text">Инсайты</h1>
        <p className="mt-1 text-sm text-tg-hint">
          Ежедневный анализ ваших пищевых привычек
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
          <p className="mb-4 text-sm text-tg-text">{error}</p>
          <button
            type="button"
            onClick={fetchInsight}
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
      )}

      {/* Insight content */}
      {!loading && !error && insight && (
        <>
          {/* Today's insight card */}
          <div className="mb-4 rounded-2xl bg-tg-secondary-bg p-4">
            {/* Type badge and title */}
            <div className="mb-3 flex items-start gap-3">
              <span className="text-2xl leading-none">
                {INSIGHT_TYPE_ICONS[insight.type] || '\u{1F4A1}'}
              </span>
              <div className="min-w-0 flex-1">
                <span className="mb-1 inline-block rounded-md bg-tg-button/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-tg-hint">
                  {INSIGHT_TYPE_LABELS[insight.type] || 'Инсайт'}
                </span>
                <h2 className="mt-1 text-lg font-semibold text-tg-text">
                  {insight.title}
                </h2>
              </div>
            </div>

            {/* Body or locked overlay */}
            {isLocked ? renderLockedOverlay() : renderInsightBody()}
          </div>

          {/* Feedback section */}
          {renderFeedbackSection()}

          {/* Info section */}
          <div className="mt-6 rounded-2xl bg-tg-secondary-bg p-4">
            <p className="text-sm text-tg-text">
              Новый инсайт каждый день в 6:00
            </p>
            <p className="mt-2 text-xs text-tg-hint">
              Мы чередуем типы инсайтов: анализ паттернов, прогресс, техники CBT
              и оценку рисков
            </p>
          </div>
        </>
      )}

      {/* No insight available */}
      {!loading && !error && !insight && (
        <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
          <p className="mb-2 text-sm text-tg-text">
            Инсайт ещё не готов
          </p>
          <p className="text-xs text-tg-hint">
            Обновляется... Попробуйте позже.
          </p>
        </div>
      )}
    </div>
  );
};

export default InsightsPage;
