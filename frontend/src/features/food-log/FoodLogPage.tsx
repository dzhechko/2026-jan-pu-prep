import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button, Card, Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Mood = 'great' | 'ok' | 'meh' | 'bad' | 'awful';
type Context = 'home' | 'work' | 'street' | 'restaurant';
type ColorCategory = 'green' | 'yellow' | 'orange';

interface MoodOption {
  value: Mood;
  emoji: string;
  label: string;
}

interface ContextOption {
  value: Context;
  emoji: string;
  label: string;
}

interface ParsedFoodItem {
  name: string;
  calories: number;
  color: ColorCategory;
}

interface FoodLogResponse {
  id: string;
  raw_text: string;
  items: ParsedFoodItem[];
  total_calories: number;
  mood: Mood | null;
  context: Context | null;
  created_at: string;
}

interface HistoryEntry {
  id: string;
  raw_text: string;
  total_calories: number;
  mood: Mood | null;
  context: Context | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_CHARS = 500;

const MOOD_OPTIONS: MoodOption[] = [
  { value: 'great', emoji: '😊', label: 'Отлично' },
  { value: 'ok', emoji: '😐', label: 'Нормально' },
  { value: 'meh', emoji: '😟', label: 'Так себе' },
  { value: 'bad', emoji: '😡', label: 'Плохо' },
  { value: 'awful', emoji: '😴', label: 'Устал(а)' },
];

const CONTEXT_OPTIONS: ContextOption[] = [
  { value: 'home', emoji: '🏠', label: 'Дом' },
  { value: 'work', emoji: '💼', label: 'Работа' },
  { value: 'street', emoji: '🚶', label: 'Улица' },
  { value: 'restaurant', emoji: '🍽', label: 'Ресторан' },
];

const COLOR_DOT_CLASSES: Record<ColorCategory, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  orange: 'bg-orange-500',
};

const MOOD_EMOJI_MAP: Record<Mood, string> = {
  great: '😊',
  ok: '😐',
  meh: '😟',
  bad: '😡',
  awful: '😴',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear();

    const time = date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });

    if (isToday) {
      return `Сегодня, ${time}`;
    }

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday =
      date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear();

    if (isYesterday) {
      return `Вчера, ${time}`;
    }

    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    }) + `, ${time}`;
  } catch {
    return isoString;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const FoodLogPage: React.FC = () => {
  // Form state
  const [rawText, setRawText] = useState('');
  const [selectedMood, setSelectedMood] = useState<Mood | null>(null);
  const [selectedContext, setSelectedContext] = useState<Context | null>(null);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  // Parse results
  const [parseResult, setParseResult] = useState<FoodLogResponse | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // History
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // -------------------------------------------------------------------------
  // Fetch history
  // -------------------------------------------------------------------------

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const response = await apiClient.get<HistoryEntry[]>('/food/history', {
        params: { limit: 10 },
      });
      setHistory(response.data);
    } catch {
      // Silently fail — history is non-critical
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // -------------------------------------------------------------------------
  // Auto-dismiss parse results after 3 seconds
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (parseResult) {
      dismissTimerRef.current = setTimeout(() => {
        setParseResult(null);
      }, 3_000);
    }

    return () => {
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
    };
  }, [parseResult]);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const handleTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      if (value.length <= MAX_CHARS) {
        setRawText(value);
        setValidationError(null);
      }
    },
    [],
  );

  const handleMoodToggle = useCallback((mood: Mood) => {
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    setSelectedMood((prev) => (prev === mood ? null : mood));
  }, []);

  const handleContextToggle = useCallback((ctx: Context) => {
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
    setSelectedContext((prev) => (prev === ctx ? null : ctx));
  }, []);

  const handleDismissResult = useCallback(() => {
    setParseResult(null);
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current);
      dismissTimerRef.current = null;
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    // Validation
    const trimmed = rawText.trim();
    if (!trimmed) {
      setValidationError('Введите что вы съели');
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
      return;
    }

    setValidationError(null);
    setApiError(null);
    setSubmitting(true);

    try {
      const payload: { raw_text: string; mood?: Mood; context?: Context } = {
        raw_text: trimmed,
      };
      if (selectedMood) payload.mood = selectedMood;
      if (selectedContext) payload.context = selectedContext;

      const response = await apiClient.post<FoodLogResponse>(
        '/food/log',
        payload,
      );

      // Success
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');

      // Show parsed results
      setParseResult(response.data);

      // Clear form
      setRawText('');
      setSelectedMood(null);
      setSelectedContext(null);

      // Refresh history
      fetchHistory();
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Произошла ошибка. Попробуйте ещё раз.';
      setApiError(message);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSubmitting(false);
    }
  }, [rawText, selectedMood, selectedContext, fetchHistory]);

  // -------------------------------------------------------------------------
  // Derived
  // -------------------------------------------------------------------------

  const isSubmitDisabled = rawText.trim().length === 0;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tg-text">Запись еды</h1>
        <p className="mt-1 text-sm text-tg-hint">
          Опишите что вы съели — мы посчитаем калории
        </p>
      </div>

      {/* Food input */}
      <Card padding="md" className="mb-4">
        <div className="relative">
          <textarea
            className="
              w-full resize-none rounded-xl
              bg-tg-secondary-bg p-3
              text-sm text-tg-text
              placeholder-tg-hint
              outline-none
              focus:ring-2 focus:ring-tg-button/30
              transition-all duration-150
            "
            rows={3}
            placeholder="Что вы съели?"
            value={rawText}
            onChange={handleTextChange}
            maxLength={MAX_CHARS}
          />
          <span className="absolute bottom-2 right-3 text-xs text-tg-hint">
            {rawText.length}/{MAX_CHARS}
          </span>
        </div>

        {/* Validation error */}
        {validationError && (
          <p className="mt-2 text-sm font-medium text-tg-destructive">
            {validationError}
          </p>
        )}
      </Card>

      {/* Mood selector */}
      <Card padding="md" className="mb-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-tg-hint">
          Настроение
        </p>
        <div className="flex justify-between gap-1">
          {MOOD_OPTIONS.map((option) => {
            const isSelected = selectedMood === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleMoodToggle(option.value)}
                className={`
                  flex flex-1 flex-col items-center gap-1
                  rounded-xl py-2
                  transition-all duration-150 ease-in-out
                  ${
                    isSelected
                      ? 'bg-tg-button/15 ring-2 ring-tg-button/40'
                      : 'bg-tg-secondary-bg hover:opacity-90 active:opacity-80'
                  }
                `.trim()}
              >
                <span className="text-xl">{option.emoji}</span>
                <span
                  className={`text-[10px] leading-tight ${
                    isSelected
                      ? 'font-semibold text-tg-text'
                      : 'text-tg-hint'
                  }`}
                >
                  {option.label}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Context selector */}
      <Card padding="md" className="mb-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-tg-hint">
          Контекст
        </p>
        <div className="flex justify-between gap-2">
          {CONTEXT_OPTIONS.map((option) => {
            const isSelected = selectedContext === option.value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleContextToggle(option.value)}
                className={`
                  flex flex-1 flex-col items-center gap-1
                  rounded-xl py-2
                  transition-all duration-150 ease-in-out
                  ${
                    isSelected
                      ? 'bg-tg-button/15 ring-2 ring-tg-button/40'
                      : 'bg-tg-secondary-bg hover:opacity-90 active:opacity-80'
                  }
                `.trim()}
              >
                <span className="text-lg">{option.emoji}</span>
                <span
                  className={`text-[10px] leading-tight ${
                    isSelected
                      ? 'font-semibold text-tg-text'
                      : 'text-tg-hint'
                  }`}
                >
                  {option.label}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Submit button */}
      <div className="mb-6">
        <Button
          fullWidth
          disabled={isSubmitDisabled}
          loading={submitting}
          onClick={handleSubmit}
        >
          Записать
        </Button>
      </div>

      {/* API error */}
      {apiError && (
        <p className="mb-4 text-center text-sm font-medium text-tg-destructive">
          {apiError}
        </p>
      )}

      {/* Parse results */}
      {parseResult && (
        <Card
          padding="md"
          className="mb-6 border border-tg-button/20"
          onClick={handleDismissResult}
        >
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-tg-hint">
            Результат
          </p>
          <div className="flex flex-col gap-2">
            {parseResult.items.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-lg bg-tg-secondary-bg px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${COLOR_DOT_CLASSES[item.color]}`}
                  />
                  <span className="text-sm text-tg-text">{item.name}</span>
                </div>
                <span className="text-sm font-medium text-tg-hint">
                  {item.calories} ккал
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-tg-hint/10 pt-3">
            <span className="text-sm font-semibold text-tg-text">Итого</span>
            <span className="text-sm font-bold text-tg-text">
              {parseResult.total_calories} ккал
            </span>
          </div>
        </Card>
      )}

      {/* History section */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-tg-text">История</h2>

        {historyLoading && history.length === 0 && (
          <div className="flex justify-center py-8">
            <Spinner size="md" />
          </div>
        )}

        {!historyLoading && history.length === 0 && (
          <p className="py-8 text-center text-sm text-tg-hint">
            Записей пока нет
          </p>
        )}

        <div className="flex flex-col gap-3">
          {history.map((entry) => (
            <Card key={entry.id} padding="sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-tg-text">
                    {entry.raw_text}
                  </p>
                  <p className="mt-1 text-xs text-tg-hint">
                    {formatTime(entry.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {entry.mood && (
                    <span className="text-base">
                      {MOOD_EMOJI_MAP[entry.mood]}
                    </span>
                  )}
                  <span className="text-sm font-semibold text-tg-text">
                    {entry.total_calories} ккал
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Loading overlay during submission */}
      {submitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-tg-bg/60">
          <Spinner size="lg" />
        </div>
      )}
    </div>
  );
};

export default FoodLogPage;
