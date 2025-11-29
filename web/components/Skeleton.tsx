"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-zinc-200 dark:bg-zinc-700",
        className
      )}
    />
  );
}

export function MessageSkeleton() {
  return (
    <div className="space-y-3">
      {/* User message skeleton */}
      <div className="flex justify-end">
        <Skeleton className="h-12 w-48 rounded-2xl" />
      </div>
      {/* Assistant message skeleton */}
      <div className="flex justify-start">
        <div className="space-y-2">
          <Skeleton className="h-4 w-64 rounded" />
          <Skeleton className="h-4 w-56 rounded" />
          <Skeleton className="h-4 w-48 rounded" />
        </div>
      </div>
    </div>
  );
}

export function ChatLoadingSkeleton() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-black">
      {/* Header skeleton */}
      <header className="border-b border-black/[.08] dark:border-white/[.145]">
        <div className="mx-auto flex max-w-4xl items-center justify-between p-4">
          <Skeleton className="h-7 w-36" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-8 w-8 rounded-full" />
          </div>
        </div>
      </header>

      {/* Main content skeleton */}
      <main className="mx-auto w-full max-w-4xl flex-1 p-4">
        <div className="flex h-[60vh] flex-col items-center justify-center">
          <Skeleton className="mb-4 h-16 w-16 rounded-full" />
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="mb-8 h-5 w-64" />
          <div className="grid max-w-lg gap-2 w-full">
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
          </div>
        </div>
      </main>

      {/* Footer skeleton */}
      <footer className="border-t border-black/[.08] bg-white p-4 dark:border-white/[.145] dark:bg-black">
        <div className="mx-auto max-w-4xl">
          <div className="flex gap-2">
            <Skeleton className="h-12 flex-1 rounded-lg" />
            <Skeleton className="h-12 w-20 rounded-full" />
          </div>
        </div>
      </footer>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.3s]" />
      <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:-0.15s]" />
      <div className="h-2 w-2 animate-bounce rounded-full bg-zinc-400" />
    </div>
  );
}
