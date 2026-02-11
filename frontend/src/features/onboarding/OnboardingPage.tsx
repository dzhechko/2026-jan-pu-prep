import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';
import { useUserStore } from '@/entities/user/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Option {
  id: string;
  label: string;
}

interface Question {
  id: string;
  text: string;
  options: Option[];
}

interface SavedAnswers {
  [questionId: string]: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'nutrimind-onboarding-answers';

const QUESTIONS: Question[] = [
  {
    id: 'eating_schedule',
    text: 'Как бы вы описали свой режим питания?',
    options: [
      { id: 'regular', label: 'Регулярное — 3 раза в день' },
      { id: 'irregular', label: 'Нерегулярное — когда придётся' },
      { id: 'frequent', label: 'Частое — 5-6 раз в день' },
      { id: 'restrictive', label: 'Ограниченное — пропускаю приёмы пищи' },
    ],
  },
  {
    id: 'biggest_challenge',
    text: 'Какая ваша главная трудность?',
    options: [
      { id: 'overeating', label: 'Переедание' },
      { id: 'emotional_eating', label: 'Эмоциональное переедание' },
      { id: 'lack_of_structure', label: 'Отсутствие режима' },
      { id: 'unhealthy_choices', label: 'Нездоровый выбор продуктов' },
      { id: 'portion_control', label: 'Контроль порций' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadSavedAnswers(): SavedAnswers {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw) as SavedAnswers;
    }
  } catch {
    // Corrupted data — ignore
  }
  return {};
}

function persistAnswers(answers: SavedAnswers): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

function clearSavedAnswers(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const updateUser = useUserStore((s) => s.updateUser);

  const [answers, setAnswers] = useState<SavedAnswers>(loadSavedAnswers);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Persist answers to localStorage whenever they change
  useEffect(() => {
    persistAnswers(answers);
  }, [answers]);

  const allAnswered = QUESTIONS.every((q) => answers[q.id]);

  const handleSelect = useCallback((questionId: string, optionId: string) => {
    // Haptic feedback for native feel
    window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();

    setValidationError(null);
    setAnswers((prev) => ({ ...prev, [questionId]: optionId }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!allAnswered) {
      setValidationError('Ответьте на все вопросы');
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const payload = {
        answers: QUESTIONS.map((q) => ({
          question_id: q.id,
          answer_id: answers[q.id],
        })),
      };

      await apiClient.post('/onboarding/interview', payload);

      // Success — update store and clean up
      updateUser({ onboarding_complete: true });
      clearSavedAnswers();

      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
      navigate('/');
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Произошла ошибка. Попробуйте ещё раз.';
      setError(message);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error');
    } finally {
      setSubmitting(false);
    }
  }, [allAnswered, answers, navigate, updateUser]);

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tg-text">
          Давайте познакомимся
        </h1>
        <p className="mt-1 text-sm text-tg-hint">
          Ответьте на пару вопросов, чтобы мы настроили приложение под вас
        </p>
      </div>

      {/* Questions */}
      <div className="flex flex-col gap-6">
        {QUESTIONS.map((question, qIndex) => (
          <Card key={question.id} padding="lg">
            <p className="mb-3 text-sm font-medium text-tg-hint">
              Вопрос {qIndex + 1} из {QUESTIONS.length}
            </p>
            <h2 className="mb-4 text-base font-semibold text-tg-text">
              {question.text}
            </h2>

            <div className="flex flex-col gap-2">
              {question.options.map((option) => {
                const isSelected = answers[question.id] === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => handleSelect(question.id, option.id)}
                    className={`
                      w-full rounded-xl px-4 py-3 text-left text-sm
                      transition-all duration-150 ease-in-out
                      ${
                        isSelected
                          ? 'bg-tg-button text-tg-button-text font-medium'
                          : 'bg-tg-secondary-bg text-tg-text hover:opacity-90 active:opacity-80'
                      }
                    `.trim()}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      {/* Validation error */}
      {validationError && (
        <p className="mt-4 text-center text-sm font-medium text-tg-destructive">
          {validationError}
        </p>
      )}

      {/* API error */}
      {error && (
        <p className="mt-4 text-center text-sm font-medium text-tg-destructive">
          {error}
        </p>
      )}

      {/* Submit */}
      <div className="mt-6">
        <Button
          fullWidth
          disabled={!allAnswered}
          loading={submitting}
          onClick={handleSubmit}
        >
          Готово
        </Button>
      </div>

      {/* Loading overlay */}
      {submitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-tg-bg/60">
          <Spinner size="lg" />
        </div>
      )}
    </div>
  );
};

export default OnboardingPage;
