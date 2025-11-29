"use client";

import { useState } from "react";
import { Citation } from "@/lib/api";

interface CitationCardProps {
  citation: Citation;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function CitationCard({ citation }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div
      className="cursor-pointer rounded-lg border border-black/[.08] bg-zinc-50 transition-all hover:border-black/[.16] dark:border-white/[.145] dark:bg-zinc-900 dark:hover:border-white/[.25]"
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="flex items-start gap-3 p-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
          {citation.speaker_name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-black dark:text-zinc-100">
              {citation.speaker_name}
            </span>
            <span className="text-xs text-zinc-500">
              {formatTimestamp(citation.timestamp)}
            </span>
          </div>
          {citation.location && (
            <div className="mt-0.5 text-xs text-zinc-500">
              {citation.location}
            </div>
          )}
          <p
            className={`mt-1 text-sm text-zinc-600 dark:text-zinc-400 ${
              isExpanded ? "" : "line-clamp-2"
            }`}
          >
            "{citation.text_snippet}"
          </p>
        </div>
        <div className="shrink-0 text-zinc-400">
          <svg
            className={`h-4 w-4 transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}
