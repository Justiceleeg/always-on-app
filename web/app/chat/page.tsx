"use client";

import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";

export default function ChatPage() {
  const { user, loading, isEnrolled } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  const handleSignOut = async () => {
    await signOut(auth);
    router.push("/");
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

      <main className="mx-auto w-full max-w-4xl flex-1 p-4">
        {!isEnrolled && (
          <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-900/20">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              Voice not enrolled. Complete enrollment on the mobile app to enable transcription.
            </p>
          </div>
        )}

        <div className="flex h-[60vh] flex-col items-center justify-center text-center">
          <div className="mb-4 text-6xl">🎙️</div>
          <h2 className="mb-2 text-2xl font-semibold text-black dark:text-zinc-50">
            Welcome, {user.displayName || "User"}
          </h2>
          <p className="max-w-md text-zinc-600 dark:text-zinc-400">
            Ask questions about your transcriptions. Chat functionality will be enabled in Slice 5.
          </p>
        </div>
      </main>

      <footer className="border-t border-black/[.08] bg-white p-4 dark:border-white/[.145] dark:bg-black">
        <div className="mx-auto max-w-4xl">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask about your conversations..."
              disabled
              className="h-12 flex-1 rounded-lg border border-black/[.08] bg-transparent px-4 opacity-50 dark:border-white/[.145]"
            />
            <button
              disabled
              className="flex h-12 items-center justify-center rounded-full bg-foreground px-6 text-background opacity-50"
            >
              Send
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-zinc-500">
            Chat functionality will be available after transcripts are captured.
          </p>
        </div>
      </footer>
    </div>
  );
}
