import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';
import { useUserStore } from '@/entities/user/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PatternType = 'time' | 'mood' | 'context' | 'sequence' | 'skip';
type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

interface PatternData {
  id: string;
  type: PatternType;
  description_ru: string;
  confidence: number;
  discovered_at: string;
}

interface RiskScore {
  level: RiskLevel;
  time_window: string | null;
  recommendation: string | null;
}

interface PatternsResponse {
  patterns: PatternData[];
  risk_today: RiskScore | null;
}

interface FeedbackResponse {
  status: string;
  new_confidence: number;
  active: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PATTERN_TYPE_ICONS: Record<PatternType, string> = {
  time: '\u{1F550}',
  mood: '\u{1F614}',
  context: '\u{1F4CD}',
  skip: '\u{23ED}\uFE0F',
  sequence: '\u{1F504}',
};

const RISK_LEVEL_CLASSES: Record<RiskLevel, string> = {
  low: 'bg-green-500/15 border-green-500/30 text-green-700',
  medium: 'bg-yellow-400/15 border-yellow-500/30 text-yellow-700',
  high: 'bg-orange-500/15 border-orange-500/30 text-orange-700',
  critical: 'bg-red-500/15 border-red-500/30 text-red-700',
};

const RISK_LEVEL_DOT_CLASSES: Record<RiskLevel, string> = {
  low: 'bg-green-500',
  medium: 'bg-yellow-400',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getConfidenceBarColor(confidence: number): string {
  if (confidence >= 0.7) return 'bg-green-500';
  if (confidence >= 0.5) return 'bg-yellow-400';
  return 'bg-orange-500';
}

function triggerHaptic(style: 'light' | 'medium' | 'heavy'): void {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style);
  } catch {
    // Haptic feedback is best-effort
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface PatternCardProps {
  pattern: PatternData;
  onDispute: (id: string) => Promise<void>;
  disputing: string | null;
}

const PatternCard: React.FC<PatternCardProps> = ({
  pattern,
  onDispute,
  disputing,
}) => {
  const isDisputing = disputing === pattern.id;
  const confidencePercent = Math.round(pattern.confidence * 100);
  const barColor = getConfidenceBarColor(pattern.confidence);
  const isColdStart = pattern.confidence <= 0.4;

  return (
    <div className="rounded-2xl bg-tg-secondary-bg p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-start gap-3">
          <span className="text-2xl leading-none">
            {PATTERN_TYPE_ICONS[pattern.type] || '\u{2753}'}
          </span>
          <div className="min-w-0 flex-1">
            {isColdStart && (
              <span className="mb-1 inline-block rounded-md bg-yellow-400/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-yellow-700">
                Предварительный анализ
              </span>
            )}
            <p className="text-sm text-tg-text">{pattern.description_ru}</p>
          </div>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs text-tg-hint">Уверенность</span>
          <span className="text-xs font-medium text-tg-hint">
            {confidencePercent}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-tg-bg">
          <div
            className={`h-full rounded-full transition-all duration-300 ${barColor}`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Dispute button */}
      <button
        type="button"
        disabled={isDisputing}
        onClick={() => onDispute(pattern.id)}
        className="
          rounded-xl border border-tg-hint/20
          bg-tg-bg px-4 py-2
          text-sm font-medium text-tg-hint
          transition-all duration-150
          hover:opacity-90 active:opacity-80
          disabled:cursor-not-allowed disabled:opacity-50
        "
      >
        {isDisputing ? (
          <span className="inline-flex items-center gap-2">
            <Spinner size="sm" />
            Отправка...
          </span>
        ) : (
          'Это неверно'
        )}
      </button>
    </div>
  );
};

interface RiskCardProps {
  risk: RiskScore;
}

const RiskCard: React.FC<RiskCardProps> = ({ risk }) => {
  return (
    <div
      className={`rounded-2xl border p-4 ${RISK_LEVEL_CLASSES[risk.level]}`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-block h-3 w-3 rounded-full ${RISK_LEVEL_DOT_CLASSES[risk.level]}`}
        />
        <span className="text-sm font-semibold">
          Риск сегодня
        </span>
      </div>

      {risk.recommendation && (
        <p className="mb-2 text-sm">{risk.recommendation}</p>
      )}

      {risk.time_window && (
        <p className="text-xs opacity-70">
          Период: {risk.time_window}
        </p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useUserStore((state) => state.user);

  // Data state
  const [patterns, setPatterns] = useState<PatternData[]>([]);
  const [riskToday, setRiskToday] = useState<RiskScore | null>(null);

  // Loading & error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dispute in-flight tracker
  const [disputingId, setDisputingId] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Fetch patterns
  // -------------------------------------------------------------------------

  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<PatternsResponse>('/patterns');
      setPatterns(response.data.patterns);
      setRiskToday(response.data.risk_today);
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить данные. Попробуйте ещё раз.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  // -------------------------------------------------------------------------
  // Dispute handler
  // -------------------------------------------------------------------------

  const handleDispute = useCallback(
    async (patternId: string) => {
      triggerHaptic('medium');
      setDisputingId(patternId);

      try {
        const response = await apiClient.post<FeedbackResponse>(
          `/patterns/${patternId}/feedback`,
        );

        const { new_confidence, active } = response.data;

        if (!active) {
          // Pattern deactivated -- remove from list
          setPatterns((prev) => prev.filter((p) => p.id !== patternId));
        } else {
          // Update confidence locally
          setPatterns((prev) =>
            prev.map((p) =>
              p.id === patternId ? { ...p, confidence: new_confidence } : p,
            ),
          );
        }
      } catch {
        // Best-effort -- silently fail for disputes
      } finally {
        setDisputingId(null);
      }
    },
    [],
  );

  // -------------------------------------------------------------------------
  // Navigation handler
  // -------------------------------------------------------------------------

  const handleNavigate = useCallback(
    (path: string) => {
      triggerHaptic('light');
      navigate(path);
    },
    [navigate],
  );

  // -------------------------------------------------------------------------
  // Greeting
  // -------------------------------------------------------------------------

  const greeting = user?.first_name
    ? `Привет, ${user.first_name}!`
    : 'Привет!';

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tg-text">НутриМайнд</h1>
        <p className="mt-1 text-sm text-tg-hint">{greeting}</p>
      </div>

      {/* Quick actions */}
      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => handleNavigate('/food-log')}
          className="
            flex-1 rounded-xl bg-tg-button px-4 py-2
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          Записать еду
        </button>
        <button
          type="button"
          onClick={() => handleNavigate('/lessons')}
          className="
            flex-1 rounded-xl bg-tg-button px-4 py-2
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          Уроки CBT
        </button>
        <button
          type="button"
          onClick={() => handleNavigate('/profile')}
          className="
            flex-1 rounded-xl bg-tg-button px-4 py-2
            text-sm font-medium text-tg-button-text
            transition-all duration-150
            hover:opacity-90 active:opacity-80
          "
        >
          Профиль
        </button>
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
            onClick={fetchPatterns}
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

      {/* Content (loaded successfully) */}
      {!loading && !error && (
        <>
          {/* Risk score card */}
          {riskToday && (
            <div className="mb-6">
              <RiskCard risk={riskToday} />
            </div>
          )}

          {/* Patterns section */}
          <div>
            <h2 className="mb-3 text-lg font-semibold text-tg-text">
              Паттерны питания
            </h2>

            {patterns.length === 0 ? (
              <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
                <p className="text-sm text-tg-hint">
                  Недостаточно данных для анализа. Продолжайте записывать приёмы
                  пищи!
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {patterns.map((pattern) => (
                  <PatternCard
                    key={pattern.id}
                    pattern={pattern}
                    onDispute={handleDispute}
                    disputing={disputingId}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardPage;
