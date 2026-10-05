"use client";

import { useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import { apiFetch } from '@/lib/api';
import { EmailListItem } from '@/types';

interface ChatTurn {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  citedEmails?: EmailListItem[];
  confidence?: number;
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatTurn[]>([
    {
      id: '1',
      sender: 'assistant',
      text: 'Hello! I am your Neural Copilot Engine. Analyzed incoming corpus of active email threads. I am ready to resolve queries, locate urgent SLA risks, or summarize pending invoices.',
      timestamp: '10:40 AM',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const fillQuery = (q: string) => {
    setInput(q);
    handleSend(q);
  };

  const handleSend = async (queryText?: string) => {
    const textToSubmit = queryText || input;
    if (!textToSubmit.trim() || loading) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userTurn: ChatTurn = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSubmit,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, userTurn]);
    setInput('');
    setLoading(true);

    try {
      const res = await apiFetch('/search/ai', {
        method: 'POST',
        body: JSON.stringify({
          question: textToSubmit,
          conversation_id: conversationId,
        }),
      });

      setConversationId(res.conversation_id);
      const botTurn: ChatTurn = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citedEmails: res.cited_emails,
        };
      setMessages((prev) => [...prev, botTurn]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: 'Sorry, I encountered an issue searching the vector index.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-800 dark:text-slate-100 transition-colors duration-200">
      <Sidebar />

      <div className="lg:pl-64 w-full flex flex-col min-w-0">
        <Header title="Neural Email Copilot Studio" />

        <main className="relative w-full pt-16 bg-slate-50 dark:bg-[#0B0F19] px-4 md:px-6 min-h-screen pb-12 transition-colors">
          <div className="flex flex-col w-full gap-6 pt-5">
            
            {/* Header */}
            <header className="flex flex-col gap-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-indigo-600 dark:bg-indigo-400 shadow-md animate-pulse" />
                    <span className="text-[10px] font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider">
                      Autonomous Context Engine
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded bg-slate-200/70 dark:bg-slate-800 font-mono">
                      Cluster #04-West
                    </span>
                  </div>
                  <h1 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">Neural Email Copilot Studio</h1>
                </div>

                {/* Telemetry Chips */}
                <div className="flex flex-wrap items-center gap-2 bg-white dark:bg-[#0F172A] p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700">
                    <span className="material-symbols-outlined text-[15px] text-indigo-600 dark:text-indigo-400">memory</span>
                    <span className="text-[9px] font-mono text-slate-400">MODEL</span>
                    <span className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200">v4.8-LLM-EXEC</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700">
                    <span className="material-symbols-outlined text-[15px] text-sky-600 dark:text-sky-400">database</span>
                    <span className="text-[9px] font-mono text-slate-400">INDEXED</span>
                    <span className="text-xs font-mono font-bold text-sky-700 dark:text-sky-300">1,420 msgs</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-800">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span className="text-[10px] font-bold text-indigo-900 dark:text-indigo-200">RAG PIPELINE: ACTIVE</span>
                  </div>
                </div>
              </div>

              {/* Directive Chips */}
              <div className="flex items-center gap-2 overflow-x-auto py-1">
                <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1 shrink-0">
                  <span className="material-symbols-outlined text-[15px] text-indigo-600 dark:text-indigo-400">auto_awesome</span> Directives:
                </span>
                <button
                  onClick={() => fillQuery('Which emails need my reply today?')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-[#0F172A] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-800 text-xs font-medium shrink-0 transition-all shadow-xs"
                >
                  <span className="material-symbols-outlined text-[15px] text-indigo-600 dark:text-indigo-400">reply</span>
                  <span>Which emails need my reply today?</span>
                </button>
                <button
                  onClick={() => fillQuery('Show urgent customer complaints')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-[#0F172A] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-800 text-xs font-medium shrink-0 transition-all shadow-xs"
                >
                  <span className="material-symbols-outlined text-[15px] text-rose-600 dark:text-rose-400">warning</span>
                  <span>Show urgent customer complaints</span>
                </button>
                <button
                  onClick={() => fillQuery('Summarize pending invoices > $5,000')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-[#0F172A] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-800 text-xs font-medium shrink-0 transition-all shadow-xs"
                >
                  <span className="material-symbols-outlined text-[15px] text-sky-600 dark:text-sky-400">request_quote</span>
                  <span>Summarize pending invoices &gt; $5,000</span>
                </button>
              </div>
            </header>

            {/* Chat Workspace */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              <section className="xl:col-span-8 flex flex-col gap-6 min-w-0">
                <div className="flex flex-col gap-6">
                  {messages.map((msg) => (
                    <div key={msg.id}>
                      {msg.sender === 'user' ? (
                        <div className="flex items-start gap-3 justify-end pl-12">
                          <div className="flex flex-col items-end gap-1.5 max-w-2xl">
                            <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                              <span className="text-[10px] font-bold uppercase">Chief Executive</span>
                              <span className="text-[10px]">• {msg.timestamp}</span>
                            </div>
                            <div className="p-4 rounded-2xl rounded-tr-sm bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700 shadow-xs">
                              <p className="text-xs font-medium leading-relaxed">{msg.text}</p>
                            </div>
                          </div>
                          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
                            CX
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start gap-3 pr-4">
                          <div className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-950 border border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 shadow-xs">
                            <span className="material-symbols-outlined text-[18px]">psychology</span>
                          </div>
                          <div className="flex flex-col gap-3 flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider">
                                Neural Copilot Engine
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
                                RAG Scan Vector Embeddings
                              </span>
                              {msg.confidence && (
                                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300">
                                  Confidence: {msg.confidence}%
                                </span>
                              )}
                            </div>

                            <div className="p-5 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col gap-4">
                              <p className="text-xs text-slate-900 dark:text-white leading-relaxed font-sans whitespace-pre-wrap">
                                {msg.text}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {loading && (
                    <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600" />
                      <span>Searching index & generating vector response...</span>
                    </div>
                  )}
                </div>

                {/* Input Bar */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSend();
                  }}
                  className="sticky bottom-4 z-30 p-3.5 rounded-2xl bg-white/95 dark:bg-[#0F172A]/95 backdrop-blur-md border border-slate-300 dark:border-slate-800 shadow-xl flex flex-col gap-2.5"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask anything about your emails, extract data, or draft batch replies..."
                      className="w-full bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder:text-slate-400 px-3.5 py-2.5 rounded-xl text-xs focus:outline-hidden font-medium"
                    />
                    <button
                      type="submit"
                      disabled={loading || !input.trim()}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-all shadow-md flex items-center gap-1.5 shrink-0 disabled:opacity-50"
                    >
                      <span>Send Query</span>
                      <span className="material-symbols-outlined text-[16px]">send</span>
                    </button>
                  </div>
                </form>
              </section>

              {/* Right Sidebar Inspector */}
              <aside className="xl:col-span-4 flex flex-col gap-5">
                <div className="p-5 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[20px] text-sky-600 dark:text-sky-400">network_intelligence</span>
                      <h2 className="font-bold text-sm text-slate-900 dark:text-white">Semantic Cluster</h2>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/60 border border-sky-200 dark:border-sky-800 px-2 py-0.5 rounded">
                      Live Telemetry
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex flex-col gap-0.5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">RESOLUTION RATE</span>
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-base font-bold text-slate-900 dark:text-white">92.4%</span>
                        <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1 py-0.2 rounded">+3.8%</span>
                      </div>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400">Avg close: 18 mins</span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex flex-col gap-0.5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">ACTIVE ACCOUNTS</span>
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-base font-bold text-indigo-600 dark:text-indigo-400">14</span>
                        <span className="text-[10px] text-slate-500 dark:text-slate-400">Connected</span>
                      </div>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400">Exchange, IMAP, Gmail</span>
                    </div>
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col gap-3.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[19px] text-indigo-600 dark:text-indigo-400">data_object</span>
                      <h2 className="font-bold text-sm text-slate-900 dark:text-white">Entity Quick-Inspector</h2>
                    </div>
                    <span className="text-[10px] font-mono font-semibold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded">
                      3 Auto-Parsed
                    </span>
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="material-symbols-outlined text-[18px] text-rose-600 dark:text-rose-400">hub</span>
                        <div className="flex flex-col min-w-0">
                          <span className="font-bold text-xs text-slate-900 dark:text-white truncate">API Gateway #4092</span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate">Apex Global EU Cluster</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="material-symbols-outlined text-[18px] text-sky-600 dark:text-sky-400">credit_card</span>
                        <div className="flex flex-col min-w-0">
                          <span className="font-bold text-xs text-slate-900 dark:text-white truncate">AWS Billing $14,850</span>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate">Annual RI Renewal</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
