import { auth } from "./firebase";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getAuthHeaders(): Promise<HeadersInit> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("Not authenticated");
  }
  const token = await user.getIdToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export interface RegisterResponse {
  user_id: string;
  is_enrolled: boolean;
  created: boolean;
}

export async function registerUser(): Promise<RegisterResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Registration failed");
  }

  return response.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
  timezone: string;
}

export interface Citation {
  transcript_id: string;
  speaker_name: string;
  timestamp: string;
  location: string | null;
  text_snippet: string;
}

export interface ChatStreamEvent {
  type: "text" | "citation" | "done" | "error";
  content?: string;
  message?: string;
  transcript_id?: string;
  speaker_name?: string;
  timestamp?: string;
  location?: string | null;
  text_snippet?: string;
}

export async function* streamChat(
  request: ChatRequest
): AsyncGenerator<ChatStreamEvent> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Chat request failed");
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data as ChatStreamEvent;
        } catch {
          // Ignore parse errors
        }
      }
    }
  }
}
