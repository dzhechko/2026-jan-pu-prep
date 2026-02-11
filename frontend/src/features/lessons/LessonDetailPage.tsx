import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LessonData {
  id: string;
  title: string;
  content_md: string;
  duration_min: number;
}

interface ProgressData {
  current: number;
  total: number;
}

interface LessonResponse {
  lesson: LessonData;
  progress: ProgressData;
}

interface CompleteResponse {
  status: string;
  newly_completed: boolean;
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
// Main Component
// ---------------------------------------------------------------------------

const LessonDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Data state
  const [lesson, setLesson] = useState<LessonData | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);

  // Loading & error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Completion state
  const [completed, setCompleted] = useState(false);
  const [completing, setCompleting] = useState(false);

  // -------------------------------------------------------------------------
  // Fetch lesson
  // -------------------------------------------------------------------------

  const fetchLesson = useCallback(async () => {
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<LessonResponse>(`/lessons/${id}`);
      setLesson(response.data.lesson);
      setProgress(response.data.progress);
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить урок. Попробуйте ещё раз.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchLesson();
  }, [fetchLesson]);

  // -------------------------------------------------------------------------
  // Complete lesson
  // -------------------------------------------------------------------------

  const handleComplete = useCallback(async () => {
    if (!id || completing) return;

    setCompleting(true);

    try {
      await apiClient.post<CompleteResponse>(`/lessons/${id}/complete`);
      triggerHapticNotification('success');
      setCompleted(true);

      // Update progress locally
      if (progress) {
        setProgress({
          ...progress,
          current: Math.min(progress.current + 1, progress.total),
        });
      }
    } catch {
      triggerHapticNotification('error');
    } finally {
      setCompleting(false);
    }
  }, [id, completing, progress]);

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    triggerHapticImpact('light');
    navigate('/lessons');
  }, [navigate]);

  const handleNextLesson = useCallback(() => {
    triggerHapticImpact('light');
    // Navigate to lessons list so user can pick the next recommended one
    navigate('/lessons');
  }, [navigate]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <button
          type="button"
          onClick={handleBack}
          className="mb-3 text-sm font-medium text-tg-button transition-opacity hover:opacity-80"
        >
          {'\u2190'} К урокам
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
            onClick={fetchLesson}
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

      {/* Lesson content */}
      {!loading && !error && lesson && (
        <>
          {/* Title & meta */}
          <div className="mb-4">
            <h1 className="text-2xl font-bold text-tg-text">{lesson.title}</h1>
            <div className="mt-2 flex items-center gap-3">
              {progress && (
                <span className="text-sm text-tg-hint">
                  Урок {progress.current + (completed ? 0 : 1)} из {progress.total}
                </span>
              )}
              <span className="text-sm text-tg-hint">
                ~{lesson.duration_min} минут
              </span>
            </div>
          </div>

          {/* Content */}
          <div className="mb-6 rounded-2xl bg-tg-secondary-bg p-4">
            <div className="whitespace-pre-line text-sm leading-relaxed text-tg-text">
              {lesson.content_md}
            </div>
          </div>

          {/* Completion button */}
          {!completed ? (
            <button
              type="button"
              disabled={completing}
              onClick={handleComplete}
              className="
                w-full rounded-xl bg-tg-button px-4 py-3
                text-base font-medium text-tg-button-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
                disabled:cursor-not-allowed disabled:opacity-50
              "
            >
              {completing ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner size="sm" />
                  Отправка...
                </span>
              ) : (
                'Пройден'
              )}
            </button>
          ) : (
            <div className="text-center">
              <p className="mb-4 text-sm font-medium text-green-600">
                {'\u2705'} Урок завершён!
              </p>
              <button
                type="button"
                onClick={handleNextLesson}
                className="
                  w-full rounded-xl bg-tg-button px-4 py-3
                  text-base font-medium text-tg-button-text
                  transition-all duration-150
                  hover:opacity-90 active:opacity-80
                "
              >
                Следующий урок
              </button>
            </div>
          )}
        </>
      )}

      {/* No lesson found */}
      {!loading && !error && !lesson && (
        <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
          <p className="text-sm text-tg-hint">
            Урок не найден.
          </p>
        </div>
      )}
    </div>
  );
};

export default LessonDetailPage;
