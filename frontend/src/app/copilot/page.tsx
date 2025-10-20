"use client";

import { ChangeEvent, FormEvent, useMemo, useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Send, Sparkles, Globe, Menu, Plus, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";

type Role = "user" | "assistant" | "system";

interface FollowUpAction {
  label: string;
  action: string;
  payload: Record<string, unknown>;
}

interface ActionResponse {
  status: string;
  message: string;
}

interface RetrievalSource {
  id: string;
  title: string;
  snippet: string | null;
  uri?: string | null;
  score?: number | null;
  metadata?: Record<string, string>;
}

interface ChatMessage {
  role: Role;
  content: string;
  timestamp: string;
  sources?: string[];
  followUps?: FollowUpAction[];
  references?: RetrievalSource[];
}

interface ChatResponse {
  session_id: string;
  reply: ChatMessage;
  sources: string[];
  references?: RetrievalSource[];
  follow_ups: FollowUpAction[];
}

const DEFAULT_ASSISTANT_MESSAGE: ChatMessage = {
  role: "assistant",
  content: "Hi! I'm EverydayElastic, your ops copilot. Ask me about active incidents, policies, runbooks, or chat history and I'll cite relevant sources.",
  timestamp: new Date().toISOString(),
};

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  sessionId?: string;
  lastUpdated: string;
}

export default function CopilotPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([DEFAULT_ASSISTANT_MESSAGE]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [input, setInput] = useState("");
  const [locale, setLocale] = useState("en-US");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [copiedMessage, setCopiedMessage] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [semanticSearchEnabled, setSemanticSearchEnabled] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxRetries = 2;

  const apiBaseUrl = useMemo(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  }, []);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('everydayelastic_conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Filter out duplicates and ensure unique IDs
        const uniqueConvs = parsed.filter((conv: Conversation, index: number, self: Conversation[]) =>
          index === self.findIndex(c => c.id === conv.id)
        );
        setConversations(uniqueConvs);
        if (uniqueConvs.length > 0) {
          const latest = uniqueConvs[0];
          setCurrentConversationId(latest.id);
          setMessages(latest.messages);
          setSessionId(latest.sessionId);
        }
      } catch (e) {
        console.error('Failed to load conversations', e);
      }
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('everydayelastic_conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  // Update current conversation when messages change
  useEffect(() => {
    if (currentConversationId && messages.length > 1) {
      setConversations(prev => prev.map(conv => 
        conv.id === currentConversationId
          ? {
              ...conv,
              messages,
              sessionId,
              lastUpdated: new Date().toISOString(),
              title: conv.title === 'New Chat' ? messages.find(m => m.role === 'user')?.content.slice(0, 50) || 'New Chat' : conv.title
            }
          : conv
      ));
    }
  }, [messages, currentConversationId, sessionId]);

  const startNewChat = () => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title: 'New Chat',
      messages: [DEFAULT_ASSISTANT_MESSAGE],
      lastUpdated: new Date().toISOString(),
    };
    setConversations(prev => [newConv, ...prev]);
    setCurrentConversationId(newConv.id);
    setMessages([DEFAULT_ASSISTANT_MESSAGE]);
    setSessionId(undefined);
    setError(null);
    setActionFeedback(null);
  };

  const switchConversation = (convId: string) => {
    const conv = conversations.find(c => c.id === convId);
    if (conv) {
      setCurrentConversationId(conv.id);
      setMessages(conv.messages);
      setSessionId(conv.sessionId);
      setError(null);
      setActionFeedback(null);
    }
  };

  const deleteConversation = (convId: string) => {
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== convId);
      if (currentConversationId === convId) {
        if (filtered.length > 0) {
          const next = filtered[0];
          setCurrentConversationId(next.id);
          setMessages(next.messages);
          setSessionId(next.sessionId);
        } else {
          startNewChat();
        }
      }
      return filtered;
    });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea (AI Elements style)
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [input]);

  const toggleSourceExpansion = (messageTimestamp: string) => {
    setExpandedSources((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(messageTimestamp)) {
        newSet.delete(messageTimestamp);
      } else {
        newSet.add(messageTimestamp);
      }
      return newSet;
    });
  };

  const copyToClipboard = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessage(messageId);
      setTimeout(() => setCopiedMessage(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const clearConversation = () => {
    if (currentConversationId) {
      setConversations(prev => prev.map(conv => 
        conv.id === currentConversationId
          ? { ...conv, messages: [DEFAULT_ASSISTANT_MESSAGE], sessionId: undefined }
          : conv
      ));
    }
    setMessages([DEFAULT_ASSISTANT_MESSAGE]);
    setSessionId(undefined);
    setError(null);
    setActionFeedback(null);
  };

  // Initialize first conversation if none exist
  useEffect(() => {
    if (conversations.length === 0) {
      startNewChat();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>, retry = false) {
    event.preventDefault();
    if (!input.trim() && !retry) {
      return;
    }

    const newUserMessage: ChatMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    const optimisticMessages = retry ? messages : [...messages, newUserMessage];
    if (!retry) {
      setMessages(optimisticMessages);
      setInput("");
    }
    setIsLoading(true);
    setError(null);
    setRetryCount(retry ? retryCount + 1 : 0);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const response = await fetch(`${apiBaseUrl}/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          messages: optimisticMessages,
          locale,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Request failed with status ${response.status}: ${errorText}`);
      }

      const data: ChatResponse = await response.json();
      setSessionId(data.session_id);
      const assistantMessage: ChatMessage = {
        ...data.reply,
        sources: data.sources,
        followUps: data.follow_ups,
        references: data.references,
      };
      if (retry) {
        setMessages((prev) => [...prev.slice(0, -1), assistantMessage]);
      } else {
        setMessages((prev) => [...prev, assistantMessage]);
      }
      setRetryCount(0);
    } catch (err) {
      console.error(err);
      const errorMessage = err instanceof Error ? err.message : "Unknown error occurred";
      if (errorMessage.includes("aborted")) {
        setError("Request timed out. The server took too long to respond. Please try again.");
      } else if (errorMessage.includes("Failed to fetch")) {
        setError("Cannot reach the backend server. Please check your connection and ensure the API is running.");
      } else {
        setError(`Error: ${errorMessage}`);
      }
    } finally {
      setIsLoading(false);
    }
  }

  const retryLastRequest = () => {
    const lastUserMessage = messages.findLast((m) => m.role === "user");
    if (lastUserMessage && retryCount < maxRetries) {
      setInput(lastUserMessage.content);
      const fakeEvent = { preventDefault: () => {} } as FormEvent<HTMLFormElement>;
      handleSubmit(fakeEvent, true);
    }
  };

  async function handleFollowUp(action: FollowUpAction) {
    setActionLoading(true);
    setActionFeedback(null);
    setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/chat/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: action.action, payload: action.payload }),
      });
      if (!response.ok) {
        throw new Error(`Action failed with status ${response.status}`);
      }
      const data: ActionResponse = await response.json();
      setActionFeedback(`${action.label}: ${data.message}`);
    } catch (err) {
      console.error(err);
      setError("Follow-up action failed. Check logs and try again.");
    } finally {
      setActionLoading(false);
    }
  }

  const quickPrompts = [
    "Show me Sev-1 incidents from the last 24 hours.",
    "What's the runbook for payment gateway timeouts?",
    "Summarize the latest chatbot deflection issue and recommend next steps.",
  ];

  return (
    <div className="min-h-screen bg-white flex">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 border-r border-gray-200 bg-gray-50 flex flex-col overflow-hidden`}>
        <div className="p-3 border-b border-gray-200">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700"
          >
            <Plus className="h-4 w-4" />
            New chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`w-full group flex items-center justify-between gap-2 px-3 py-2 rounded-lg mb-1 transition-colors cursor-pointer ${
                currentConversationId === conv.id
                  ? 'bg-white text-gray-900'
                  : 'text-gray-700 hover:bg-white/50'
              }`}
              onClick={() => switchConversation(conv.id)}
            >
              <span className="text-sm truncate flex-1">{conv.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-opacity"
                aria-label="Delete conversation"
              >
                <Trash2 className="h-3 w-3 text-gray-600" />
              </button>
            </div>
          ))}
        </div>
        
        <div className="p-3 border-t border-gray-200">
          <Link 
            href="/"
            className="text-xs text-gray-600 hover:text-gray-900 flex items-center gap-2"
          >
            <Sparkles className="h-3 w-3" />
            EverydayElastic
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between gap-4 max-w-4xl mx-auto">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="text-gray-600 hover:text-gray-900 p-1 rounded-lg hover:bg-gray-100"
              >
                <Menu className="h-5 w-5" />
              </button>
              <h1 className="text-lg font-semibold text-gray-900">EverydayElastic</h1>
            </div>
            <div className="flex items-center gap-2">
              {messages.length > 1 && (
                <button
                  onClick={clearConversation}
                  className="text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </header>

      <main className="flex-1 flex flex-col px-4 py-8 max-w-3xl mx-auto w-full">
        <section className="flex-1 overflow-y-auto space-y-6 mb-6">
            {messages.map((message, index) => (
            <article
              key={`${message.timestamp}-${index}`}
              className={`${
                message.role === "user"
                  ? "ml-auto max-w-2xl"
                  : "mr-auto max-w-full"
              }`}
            >
              <div className={`rounded-2xl px-5 py-3 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-50"
              }`}>
              <div className={`prose prose-sm max-w-none ${
                message.role === "user" ? "prose-invert" : ""
              }`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
              </div>
              {message.sources && message.sources.length > 0 ? (
                <div className="mt-3">
                  <button
                    onClick={() => toggleSourceExpansion(message.timestamp)}
                    className="flex items-center gap-2 text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors mb-2"
                  >
                    <span>{expandedSources.has(message.timestamp) ? "▼" : "▶"}</span>
                    <span>Sources ({message.sources.length})</span>
                  </button>
                  {expandedSources.has(message.timestamp) && (
                    <ul className="text-xs text-gray-700 space-y-2 pl-4 border-l-2 border-blue-300">
                    {message.sources.map((sourceId, idx) => {
                      const reference = message.references?.find(
                        (ref) => ref.uri === sourceId || ref.id === sourceId,
                      );
                      return (
                        <li key={`${sourceId}-${idx}`} className="pl-3">
                          <span className="font-semibold text-gray-900">
                            {reference?.title ?? sourceId}
                          </span>
                          {reference?.score ? (
                            <span className="ml-2 text-green-600 font-medium">
                              (relevance {reference.score.toFixed(2)})
                            </span>
                          ) : null}
                          {reference?.metadata && Object.keys(reference.metadata).length ? (
                            <div className="text-gray-600 text-xs mt-1">
                              {Object.entries(reference.metadata).map(([key, value]) => (
                                <div key={`${sourceId}-${key}`}>{`${key}: ${value}`}</div>
                              ))}
                            </div>
                          ) : null}
                          {reference?.snippet ? (
                            <div className="text-gray-600 italic mt-1">{reference.snippet}</div>
                          ) : null}
                        </li>
                      );
                    })}
                    </ul>
                  )}
                </div>
              ) : null}
              {message.followUps && message.followUps.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {message.followUps.map((action) => (
                    <button
                      key={action.label}
                      type="button"
                      onClick={() => handleFollowUp(action)}
                      disabled={actionLoading}
                      className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {actionLoading ? "Processing..." : action.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          {isLoading && (
            <div className="rounded-lg px-5 py-4 max-w-3xl mr-auto bg-gradient-to-br from-blue-50 to-purple-50 border border-blue-200 shadow-sm">
              <div className="flex items-center gap-2 text-sm font-semibold text-blue-700 mb-3">
                <Sparkles className="h-4 w-4 animate-pulse" />
                <span>Thinking...</span>
              </div>
              <div className="space-y-2 text-xs text-gray-600 italic">
                <p className="animate-fade-in">→ Searching 7,800+ knowledge sources...</p>
                <p className="animate-fade-in animation-delay-150">→ Analyzing semantic relevance...</p>
                <p className="animate-fade-in animation-delay-300">→ Reranking results...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
          {error ? (
            <div className="rounded-lg px-4 py-3 bg-red-50 border border-red-300 flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="text-sm font-semibold text-red-700 mb-1">Error</div>
                <div className="text-sm text-red-600">{error}</div>
              </div>
              {retryCount < maxRetries && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={retryLastRequest}
                  className="border-red-300 text-red-600 hover:bg-red-50"
                >
                  Retry
                </Button>
              )}
            </div>
          ) : null}
          {actionFeedback ? (
            <div className="rounded-lg px-4 py-3 bg-green-50 border border-green-300">
              <div className="text-sm font-semibold text-green-700 mb-1">Success</div>
              <div className="text-sm text-green-600">{actionFeedback}</div>
            </div>
          ) : null}
        </section>

        <section className="grid gap-3 sm:grid-cols-3 mb-4">
          {quickPrompts.map((prompt, idx) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setInput(prompt)}
              className="text-left rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </section>

        <form onSubmit={handleSubmit} className="relative bg-white rounded-3xl border border-gray-300 shadow-sm hover:shadow-md transition-shadow">
          <textarea
            ref={textareaRef}
            id="user-input"
            rows={1}
            className="w-full bg-transparent border-none rounded-3xl px-5 py-4 pr-14 resize-none focus:outline-none text-gray-900 placeholder:text-gray-500 text-[15px]"
            placeholder="Message EverydayElastic..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event as unknown as FormEvent<HTMLFormElement>);
              }
            }}
            disabled={isLoading}
            required
          />
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()} 
            className="absolute right-3 bottom-3 h-8 w-8 rounded-lg bg-gray-900 hover:bg-gray-700 text-white disabled:bg-gray-300 disabled:cursor-not-allowed transition-all flex items-center justify-center"
          >
            {isLoading ? (
              <Sparkles className="h-4 w-4 animate-pulse" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>
      </main>
      </div>
    </div>
  );
}
