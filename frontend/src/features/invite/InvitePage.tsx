import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GenerateResponse {
  invite_code: string;
  share_url: string;
}

interface InviteRecord {
  code: string;
  status: 'pending' | 'redeemed';
  created_at: string;
  redeemed_at: string | null;
}

interface MyInvitesResponse {
  invites: InviteRecord[];
  total_redeemed: number;
}

// ---------------------------------------------------------------------------
// Haptic helper
// ---------------------------------------------------------------------------

function triggerHaptic(style: 'light' | 'medium' | 'heavy'): void {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(style);
  } catch {
    // Best-effort
  }
}

// ---------------------------------------------------------------------------
// Date formatting helper
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateString;
  }
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const InvitePage: React.FC = () => {
  const navigate = useNavigate();

  // Generate invite state
  const [inviteCode, setInviteCode] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Copied indicator
  const [copied, setCopied] = useState(false);

  // My invites state
  const [invites, setInvites] = useState<InviteRecord[]>([]);
  const [totalRedeemed, setTotalRedeemed] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Fetch my invites
  // ---------------------------------------------------------------------------

  const fetchInvites = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<MyInvitesResponse>('/invite/my');
      setInvites(response.data.invites);
      setTotalRedeemed(response.data.total_redeemed);
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось загрузить приглашения. Попробуйте ещё раз.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvites();
  }, [fetchInvites]);

  // ---------------------------------------------------------------------------
  // Generate invite
  // ---------------------------------------------------------------------------

  const handleGenerate = useCallback(async () => {
    triggerHaptic('medium');
    setGenerating(true);
    setGenerateError(null);

    try {
      const response = await apiClient.post<GenerateResponse>('/invite/generate');
      setInviteCode(response.data.invite_code);
      setShareUrl(response.data.share_url);
      // Refresh the invites list
      fetchInvites();
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось создать приглашение. Попробуйте ещё раз.';
      setGenerateError(message);
    } finally {
      setGenerating(false);
    }
  }, [fetchInvites]);

  // ---------------------------------------------------------------------------
  // Share via Telegram
  // ---------------------------------------------------------------------------

  const handleShare = useCallback(() => {
    if (!shareUrl) return;

    triggerHaptic('light');

    const shareText = `Присоединяйся к НутриМайнд! Используй мою ссылку и получи 7 дней Premium: ${shareUrl}`;
    const telegramShareUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;
    window.open(telegramShareUrl, '_blank');
  }, [shareUrl]);

  // ---------------------------------------------------------------------------
  // Copy link to clipboard
  // ---------------------------------------------------------------------------

  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;

    triggerHaptic('light');

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may not be available
    }
  }, [shareUrl]);

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  const handleBack = useCallback(() => {
    triggerHaptic('light');
    navigate('/');
  }, [navigate]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-tg-bg px-4 pb-8 pt-6">
      {/* Header */}
      <div className="mb-6">
        <button
          type="button"
          onClick={handleBack}
          className="mb-3 text-sm font-medium text-tg-button transition-all duration-150 hover:opacity-90 active:opacity-80"
        >
          {'\u2190'} Назад
        </button>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{'\u{1F465}'}</span>
          <h1 className="text-2xl font-bold text-tg-text">Пригласить друга</h1>
        </div>
      </div>

      {/* Explanation card */}
      <div className="mb-6 rounded-2xl bg-tg-secondary-bg p-4">
        <p className="text-sm leading-relaxed text-tg-text">
          Пригласите друга и получите 7 дней Premium бесплатно! Ваш друг тоже
          получит 7 дней Premium.
        </p>
      </div>

      {/* Generate button */}
      {!inviteCode && (
        <div className="mb-6">
          <button
            type="button"
            disabled={generating}
            onClick={handleGenerate}
            className="
              w-full rounded-xl bg-tg-button px-4 py-3
              text-sm font-medium text-tg-button-text
              transition-all duration-150
              hover:opacity-90 active:opacity-80
              disabled:cursor-not-allowed disabled:opacity-50
            "
          >
            {generating ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" />
                Создание...
              </span>
            ) : (
              'Создать приглашение'
            )}
          </button>

          {generateError && (
            <p className="mt-2 text-center text-xs text-red-500">
              {generateError}
            </p>
          )}
        </div>
      )}

      {/* Generated invite code */}
      {inviteCode && shareUrl && (
        <div className="mb-6">
          {/* Code display */}
          <div className="mb-4 rounded-2xl bg-tg-secondary-bg p-4 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-tg-hint">
              Код приглашения
            </p>
            <p className="text-2xl font-bold tracking-widest text-tg-text">
              {inviteCode}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleShare}
              className="
                flex-1 rounded-xl bg-tg-button px-4 py-3
                text-sm font-medium text-tg-button-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
              "
            >
              Поделиться
            </button>
            <button
              type="button"
              onClick={handleCopy}
              className="
                flex-1 rounded-xl border border-tg-hint/20
                bg-tg-secondary-bg px-4 py-3
                text-sm font-medium text-tg-text
                transition-all duration-150
                hover:opacity-90 active:opacity-80
              "
            >
              {copied ? 'Скопировано!' : 'Копировать ссылку'}
            </button>
          </div>

          {/* Generate another */}
          <button
            type="button"
            disabled={generating}
            onClick={handleGenerate}
            className="
              mt-3 w-full rounded-xl border border-tg-hint/20
              bg-tg-bg px-4 py-2
              text-sm font-medium text-tg-hint
              transition-all duration-150
              hover:opacity-90 active:opacity-80
              disabled:cursor-not-allowed disabled:opacity-50
            "
          >
            {generating ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="sm" />
                Создание...
              </span>
            ) : (
              'Создать ещё одно'
            )}
          </button>
        </div>
      )}

      {/* My invites section */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-tg-text">
          Мои приглашения
        </h2>

        {/* Loading state */}
        {loading && (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
            <p className="mb-4 text-sm text-tg-text">{error}</p>
            <button
              type="button"
              onClick={fetchInvites}
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

        {/* Invites loaded */}
        {!loading && !error && (
          <>
            {/* Summary */}
            <div className="mb-3 rounded-2xl bg-tg-secondary-bg p-4">
              <p className="text-sm text-tg-text">
                Использовано: {totalRedeemed} из {invites.length}
              </p>
            </div>

            {/* Invites list */}
            {invites.length === 0 ? (
              <div className="rounded-2xl bg-tg-secondary-bg p-6 text-center">
                <p className="text-sm text-tg-hint">
                  У вас пока нет приглашений. Создайте первое!
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {invites.map((invite) => (
                  <div
                    key={invite.code}
                    className="rounded-2xl bg-tg-secondary-bg p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium tracking-wide text-tg-text">
                          {invite.code}
                        </p>
                        <p className="mt-1 text-xs text-tg-hint">
                          {formatDate(invite.created_at)}
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          invite.status === 'redeemed'
                            ? 'bg-green-500/15 text-green-700'
                            : 'bg-yellow-400/15 text-yellow-700'
                        }`}
                      >
                        {invite.status === 'redeemed'
                          ? 'Активировано'
                          : 'Ожидание'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default InvitePage;
