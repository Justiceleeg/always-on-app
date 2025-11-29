"use client";

import { useAuth } from "@/components/AuthProvider";
import { CitationCard } from "@/components/CitationCard";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef, FormEvent } from "react";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { streamChat, ChatMessage, Citation } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

const SUGGESTED_QUERIES = [
  "What did I discuss at the job site yesterday?",
  "Summarize my conversations from this week",
  "What did I say about the electrical work?",
  "What topics came up today?",
];

export default function ChatPage() {
  const { user, loading, isEnrolled } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSignOut = async () => {
    await signOut(auth);
    router.push("/");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput("");
    setError(null);

    // Add user message
    const newMessages: Message[] = [...messages, { role: "user", content: userMessage }];
    setMessages(newMessages);

    // Prepare conversation history (exclude current message)
    const conversationHistory: ChatMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setIsStreaming(true);

    try {
      // Get user's timezone
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      let assistantContent = "";
      const citations: Citation[] = [];

      // Add placeholder assistant message
      setMessages([...newMessages, { role: "assistant", content: "", citations: [] }]);

      for await (const event of streamChat({
        message: userMessage,
        conversation_history: conversationHistory,
        timezone,
      })) {
        if (event.type === "text" && event.content) {
          assistantContent += event.content;
          setMessages([
            ...newMessages,
            { role: "assistant", content: assistantContent, citations },
          ]);
        } else if (event.type === "citation") {
          citations.push({
            transcript_id: event.transcript_id!,
            speaker_name: event.speaker_name!,
            timestamp: event.timestamp!,
            location: event.location ?? null,
            text_snippet: event.text_snippet!,
          });
          setMessages([
            ...newMessages,
            { role: "assistant", content: assistantContent, citations: [...citations] },
          ]);
        } else if (event.type === "error") {
          setError(event.message || "An error occurred");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Remove the empty assistant message on error
      setMessages(newMessages);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSuggestedQuery = (query: string) => {
    setInput(query);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-black">
      <header className="border-b border-black/[.08] dark:border-white/[.145]">
        <div className="mx-auto flex max-w-4xl items-center justify-between p-4">
          <h1 className="text-xl font-bold text-black dark:text-zinc-50">Frontier Audio</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-zinc-600 dark:text-zinc-400">
              {user.displayName || user.email}
            </span>
            <button
              onClick={handleSignOut}
              className="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto p-4">
        {!isEnrolled && (
          <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Voice not enrolled. Complete enrollment on the mobile app to enable transcription.
            </p>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {!hasMessages ? (
          // Empty state
          <div className="flex h-[60vh] flex-col items-center justify-center text-center">
            <div className="mb-4 text-6xl">🎙️</div>
            <h2 className="mb-2 text-2xl font-semibold text-black dark:text-zinc-50">
              Welcome, {user.displayName || "User"}
            </h2>
            <p className="mb-8 max-w-md text-zinc-600 dark:text-zinc-400">
              Ask questions about your transcribed conversations. Try one of these:
            </p>
            <div className="grid max-w-lg gap-2">
              {SUGGESTED_QUERIES.map((query, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestedQuery(query)}
                  className="rounded-lg border border-black/[.08] bg-white px-4 py-3 text-left text-sm text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-white/[.145] dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          // Messages
          <div className="space-y-6 pb-4">
            {messages.map((message, index) => (
              <div key={index} className="space-y-3">
                <div
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-white text-zinc-900 shadow-sm dark:bg-zinc-800 dark:text-zinc-100"
                    }`}
                  >
                    {message.content || (
                      <span className="inline-block h-4 w-4 animate-pulse rounded-full bg-zinc-300 dark:bg-zinc-600" />
                    )}
                  </div>
                </div>

                {/* Citations */}
                {message.role === "assistant" &&
                  message.citations &&
                  message.citations.length > 0 && (
                    <div className="ml-0 space-y-2">
                      <p className="text-xs font-medium text-zinc-500">Sources</p>
                      {message.citations.map((citation, citationIndex) => (
                        <CitationCard key={citationIndex} citation={citation} />
                      ))}
                    </div>
                  )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      <footer className="border-t border-black/[.08] bg-white p-4 dark:border-white/[.145] dark:bg-black">
        <form onSubmit={handleSubmit} className="mx-auto max-w-4xl">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your conversations..."
              disabled={isStreaming}
              className="h-12 flex-1 rounded-lg border border-black/[.08] bg-transparent px-4 focus:border-blue-500 focus:outline-none disabled:opacity-50 dark:border-white/[.145]"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="flex h-12 items-center justify-center rounded-full bg-blue-600 px-6 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isStreaming ? (
                <svg
                  className="h-5 w-5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : (
                "Send"
              )}
            </button>
          </div>
        </form>
      </footer>
    </div>
  );
}
