import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LessonListItem {
  id: string;
  title: string;
  lesson_order: number;
  duration_min: number;
  completed: boolean;
}

interface ProgressData {
  current: number;
  total: number;
}

interface LessonsListResponse {
  lessons: LessonListItem[];
  progress: ProgressData;
}

interface LessonData {
  id: string;
  title: string;
  content_md: string;
  duration_min: number;
}

interface RecommendedResponse {
  lesson: LessonData;
  progress: ProgressData;
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface LessonCardProps {
  lesson: LessonListItem;
  isRecommended: boolean;
  onTap: (id: string) => void;
}

const LessonCard: React.FC<LessonCardProps> = ({ lesson, isRecommended, onTap }) => {
  const completedClasses = lesson.completed ? 'opacity-60' : '';
  const recommendedBorder = isRecommended ? 'border-2 border-tg-button' : '';

  return (
    <button
      type="button"
      onClick={() => onTap(lesson.id)}
      className={`
        w-full rounded-2xl bg-tg-secondary-bg p-4
        text-left transition-all duration-150
        hover:opacity-90 active:opacity-80
        ${completedClasses}
        ${recommendedBorder}
      `}
    >
      <div className="flex items-center gap-3">
        {/* Lesson number circle */}
        <div
          className={`
            flex h-10 w-10 flex-shrink-0 items-center justify-center
            rounded-full text-sm font-bold
            ${lesson.completed
              ? 'bg-green-500/20 text-green-600'
              : 'bg-tg-button/15 text-tg-button'}
          `}
        >
          {lesson.completed ? '\u2713' : lesson.lesson_order}
        </div>

        {/* Lesson info */}
        <div className="min-w-0 flex-1">
          {isRecommended && (
            <span className="mb-1 inline-block rounded-md bg-tg-button/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-tg-button">
              Рекомендуем
            </span>
          )}
          <h3 className="text-sm font-semibold text-tg-text">{lesson.title}</h3>
          <p className="mt-0.5 text-xs text-tg-hint">~{lesson.duration_min} мин</p>
        </div>

        {/* Completed checkmark */}
        {lesson.completed && (
          <span className="flex-shrink-0 text-lg text-green-500">{'\u2705'}</span>
        )}
      </div>
    </button>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const LessonsPage: React.FC = () => {
  const navigate = useNavigate();

  // Data state
  const [lessons, setLessons] = useState<LessonListItem[]>([]);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [recommendedId, setRecommendedId] = useState<string | null>(null);

  // Loading & error
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Fetch lessons list
  // -------------------------------------------------------------------------

  const fetchLessons = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [listResponse, recommendedResponse] = await Promise.allSettled([
        apiClient.get<LessonsListResponse>('/lessons'),
        apiClient.get<RecommendedResponse>('/lessons/recommended'),
      ]);

      if (listResponse.status === 'fulfilled') {
        setLessons(listResponse.value.data.lessons);
        setProgress(listResponse.value.data.progress);
      } else {
        throw listResponse.reason;
      }

      if (recommendedResponse.status === 'fulfilled') {
        setRecommendedId(recommendedResponse.value.data.lesson.id);
      }
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить уроки. Попробуйте ещё раз.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLessons();
  }, [fetchLessons]);

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleLessonTap = useCallback(
    (id: string) => {
      triggerHapticImpact('light');
      navigate(`/lessons/${id}`);
    },
    [navigate],
  );

  const handleBack = useCallback(() => {
    triggerHapticImpact('light');
    navigate('/');
  }, [navigate]);

  // -------------------------------------------------------------------------
  // Derived data
  // -------------------------------------------------------------------------

  const sortedLessons = [...lessons].sort((a, b) => a.lesson_order - b.lesson_order);
  const uncompletedLessons = sortedLessons.filter((l) => !l.completed);
  const completedLessons = sortedLessons.filter((l) => l.completed);

  const progressPercent =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

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
          {'\u2190'} Назад
        </button>
        <h1 className="text-2xl font-bold text-tg-text">Уроки CBT</h1>
        <p className="mt-1 text-sm text-tg-hint">
          Когнитивно-поведенческая терапия для здоровых привычек питания
        </p>
      </div>

      {/* Progress bar */}
      {progress && (
        <div className="mb-6 rounded-2xl bg-tg-secondary-bg p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-tg-text">
              Прогресс: {progress.current} / {progress.total} уроков
            </span>
            <span className="text-sm font-medium text-tg-hint">
              {progressPercent}%
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-tg-bg">
            <div
              className="h-full rounded-full bg-tg-button transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

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
            onClick={fetchLessons}
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

      {/* Lessons list */}
      {!loading && !error && (
        <>
          {/* Uncompleted lessons */}
          {uncompletedLessons.length > 0 && (
            <div className="mb-6">
              <h2 className="mb-3 text-lg font-semibold text-tg-text">
                Доступные уроки
              </h2>
              <div className="flex flex-col gap-3">
                {uncompletedLessons.map((lesson) => (
                  <LessonCard
                    key={lesson.id}
                    lesson={lesson}
                    isRecommended={lesson.id === recommendedId}
                    onTap={handleLessonTap}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Completed lessons */}
          {completedLessons.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold text-tg-hint">
                Пройденные
              </h2>
              <div className="flex flex-col gap-3">
                {completedLessons.map((lesson) => (
                  <LessonCard
                    key={lesson.id}
                    lesson={lesson}
                    isRecommended={false}
                    onTap={handleLessonTap}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {lessons.length === 0 && (
            <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
              <p className="text-sm text-tg-hint">
                Уроки пока не доступны. Попробуйте позже.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LessonsPage;
