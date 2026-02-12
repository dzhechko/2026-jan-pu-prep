import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner } from '@/shared/ui';
import { apiClient } from '@/shared/api/client';
import { useUserStore } from '@/entities/user/store';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface HistoryResponse {
  messages: ChatMessage[];
  has_more: boolean;
}

interface MessageResponse {
  message: ChatMessage;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const CoachPage: React.FC = () => {
  const navigate = useNavigate();
  const user = useUserStore((state) => state.user);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Premium guard
  useEffect(() => {
    if (user && user.subscription_status === 'free') {
      navigate('/paywall');
    }
  }, [user, navigate]);

  // Load chat history
  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<HistoryResponse>('/coach/history?limit=50');
      setMessages(response.data.messages);
    } catch (err: unknown) {
      const message =
        (err as { status?: number })?.status === 403
          ? null // Premium guard handles this
          : 'Не удалось загрузить историю чата.';
      if (message) setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Send message
  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    // Optimistically add user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setInput('');
    setSending(true);

    try {
      const response = await apiClient.post<MessageResponse>('/coach/message', {
        content: trimmed,
      });
      // Replace temp message and add assistant response
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
        return [
          ...withoutTemp,
          { ...tempUserMsg, id: `user-${Date.now()}` },
          response.data.message,
        ];
      });
    } catch (err: unknown) {
      const message =
        (err as { message?: string })?.message ||
        'Не удалось отправить сообщение.';
      setError(message);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }, [input, sending]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex h-screen flex-col bg-tg-bg">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-tg-hint/10 px-4 py-3">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-tg-button text-sm font-medium"
          aria-label="Назад"
        >
          {'\u2190'}
        </button>
        <div>
          <h1 className="text-base font-semibold text-tg-text">AI \u041A\u043E\u0443\u0447</h1>
          <p className="text-xs text-tg-hint">CBT-\u043A\u043E\u0443\u0447 \u043F\u043E \u043F\u0438\u0442\u0430\u043D\u0438\u044E</p>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        )}

        {!loading && messages.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="mb-4 text-5xl">{'\u{1F9E0}'}</span>
            <h2 className="mb-2 text-lg font-semibold text-tg-text">
              {'\u0414\u043E\u0431\u0440\u043E \u043F\u043E\u0436\u0430\u043B\u043E\u0432\u0430\u0442\u044C!'}
            </h2>
            <p className="max-w-xs text-sm text-tg-hint">
              {'\u042F \u0432\u0430\u0448 AI-\u043A\u043E\u0443\u0447 \u043F\u043E \u043E\u0441\u043E\u0437\u043D\u0430\u043D\u043D\u043E\u043C\u0443 \u043F\u0438\u0442\u0430\u043D\u0438\u044E. \u0417\u0430\u0434\u0430\u0439\u0442\u0435 \u043C\u043D\u0435 \u0432\u043E\u043F\u0440\u043E\u0441 \u043E \u043F\u0438\u0449\u0435\u0432\u043E\u043C \u043F\u043E\u0432\u0435\u0434\u0435\u043D\u0438\u0438 \u0438\u043B\u0438 \u043F\u043E\u043F\u0440\u043E\u0441\u0438\u0442\u0435 \u0441\u043E\u0432\u0435\u0442.'}
            </p>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-xl bg-red-500/10 p-3 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-3 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-tg-button text-tg-button-text'
                  : 'bg-tg-secondary-bg text-tg-text'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {sending && (
          <div className="mb-3 flex justify-start">
            <div className="rounded-2xl bg-tg-secondary-bg px-4 py-3">
              <Spinner size="sm" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-tg-hint/10 px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={'\u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435...'}
            maxLength={500}
            rows={1}
            className="
              flex-1 resize-none rounded-xl border border-tg-hint/20
              bg-tg-secondary-bg px-4 py-2.5
              text-sm text-tg-text
              placeholder:text-tg-hint
              focus:border-tg-button focus:outline-none
            "
            disabled={sending}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="
              rounded-xl bg-tg-button px-4 py-2.5
              text-sm font-medium text-tg-button-text
              transition-all duration-150
              hover:opacity-90 active:opacity-80
              disabled:cursor-not-allowed disabled:opacity-50
            "
          >
            {'\u27A4'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CoachPage;
