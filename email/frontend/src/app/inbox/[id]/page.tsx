"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import { apiFetch } from '@/lib/api';
import { EmailDetail, AIReply } from '@/types';
import { fmtDateTime } from '@/lib/time';

export default function EmailDetailPage() {
  const params = useParams();
  const router = useRouter();
  const emailId = params.id;

  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [threadMessages, setThreadMessages] = useState<any[]>([]);
  const [showThread, setShowThread] = useState(true);
  const [loading, setLoading] = useState(true);
  const [summaryMode, setSummaryMode] = useState<'short' | 'detailed'>('short');

  // Smart Reply state
  const [selectedTone, setSelectedTone] = useState<string>('Professional');
  const [replyDraft, setReplyDraft] = useState<string>('');
  const [activeReplyObj, setActiveReplyObj] = useState<AIReply | null>(null);
  const [replyLoading, setReplyLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [approvedStatus, setApprovedStatus] = useState<string | null>(null);
  const [replyNotice, setReplyNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const [approving, setApproving] = useState(false);

  // Reject modal state
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejecting, setRejecting] = useState(false);

  const loadThread = async (tid: number) => {
    try {
      const threadData = await apiFetch(`/emails/threads/${tid}`);
      const msgs = threadData.messages || [];
      setThreadMessages((cur) => (JSON.stringify(cur.map((m: any) => m.id)) === JSON.stringify(msgs.map((m: any) => m.id)) ? cur : msgs));
    } catch (tErr) {
      console.error('Failed to load thread details:', tErr);
    }
  };

  const fetchEmailDetail = async () => {
    try {
      const data: EmailDetail = await apiFetch(`/emails/${emailId}`);
      setEmail(data);

      if (data.thread_id) await loadThread(data.thread_id);

      if (data.ai_replies && data.ai_replies.length > 0) {
        const latest = data.ai_replies[data.ai_replies.length - 1];
        setActiveReplyObj(latest);
        setReplyDraft(latest.edited_body || latest.suggested_body);
        setSelectedTone(latest.selected_tone);
        setApprovedStatus(latest.status);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmailDetail();
  }, [emailId]);

  // Live conversation: the customer's follow-up (picked up from the mailbox by the backend) appears here without a reload.
  const threadId = email?.thread_id;
  useEffect(() => {
    if (!threadId) return;
    const timer = setInterval(() => {
      if (!document.hidden) loadThread(threadId);
    }, 15000);
    return () => clearInterval(timer);
  }, [threadId]);

  const handleGenerateReply = async (toneOverride?: string, customRejectReason?: string) => {
    setReplyLoading(true);
    setApprovedStatus(null);
    setReplyNotice(null);
    const toneToUse = toneOverride || selectedTone;

    try {
      const res: AIReply = await apiFetch(`/emails/${emailId}/reply`, {
        method: 'POST',
        body: JSON.stringify({
          tone: toneToUse,
          reject_reason: customRejectReason || undefined,
        }),
      });

      setActiveReplyObj(res);
      setReplyDraft(res.suggested_body);
      setApprovedStatus(res.status);
    } catch (err: any) {
      console.error(err);
      setReplyNotice({ ok: false, text: err?.message || 'Could not generate a reply draft.' });
    } finally {
      setReplyLoading(false);
    }
  };

  const handleApproveReply = async () => {
    if (!activeReplyObj || approving) return;
    setApproving(true);
    setReplyNotice(null);
    try {
      const res: AIReply = await apiFetch(`/emails/${emailId}/reply/${activeReplyObj.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ edited_body: replyDraft }),
      });
      setApprovedStatus('approved');
      setActiveReplyObj(res);
      setReplyNotice({
        ok: !!res.delivered,
        text: res.delivery_note || (res.delivered ? 'Reply e-mailed.' : 'Reply recorded but NOT e-mailed.'),
      });
      if (email?.thread_id) loadThread(email.thread_id);  // our reply is now part of the conversation
    } catch (err: any) {
      // delivery failed: backend recorded nothing, so the draft stays editable and can be retried
      console.error(err);
      setReplyNotice({ ok: false, text: err?.message || 'Could not send the reply. Nothing was recorded.' });
    } finally {
      setApproving(false);
    }
  };

  const handleRejectReply = async () => {
    if (!activeReplyObj || !rejectReason.trim()) return;
    setRejecting(true);
    try {
      await apiFetch(`/emails/${emailId}/reply/${activeReplyObj.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: rejectReason }),
      });
      setApprovedStatus('rejected');
      setIsRejectOpen(false);
      handleGenerateReply(selectedTone, rejectReason);
      setRejectReason('');
    } catch (err) {
      console.error(err);
    } finally {
      setRejecting(false);
    }
  };

  const handleCopyReply = () => {
    navigator.clipboard.writeText(replyDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <AppLayout title="Loading Email...">
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
          <span className="material-symbols-outlined text-[36px] text-indigo-500 animate-spin">progress_activity</span>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Loading email & AI context...</p>
        </div>
      </AppLayout>
    );
  }

  if (!email) {
    return (
      <AppLayout title="Email Not Found">
        <div className="p-12 text-center text-rose-500 font-semibold">Email not found or deleted.</div>
      </AppLayout>
    );
  }

  const priorityColor =
    email.ai_analysis?.priority === 'CRITICAL'
      ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
      : email.ai_analysis?.priority === 'HIGH'
      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
      : 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20';

  return (
    <AppLayout title={`Email #${email.id}`}>
      <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto w-full" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
        
        {/* Top Navigation & Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm transition-colors">
          <Link
            href="/inbox"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 px-3 py-2 rounded-xl transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            Back to Inbox
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                await apiFetch(`/emails/${email.id}/unread`, { method: 'PATCH' });
                router.push('/inbox');
              }}
              className="px-3 py-2 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">mark_email_unread</span>
              <span>Mark unread</span>
            </button>

            <button
              onClick={async () => {
                await apiFetch(`/emails/${email.id}/toggle-star`, { method: 'PATCH' });
                fetchEmailDetail();
              }}
              className={`px-3 py-2 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-all ${
                email.is_starred
                  ? 'bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span className={`material-symbols-outlined text-[16px] ${email.is_starred ? 'fill-current' : ''}`}>star</span>
              <span>{email.is_starred ? 'Starred' : 'Star'}</span>
            </button>

            <button
              onClick={async () => {
                await apiFetch(`/emails/${email.id}/toggle-archive`, { method: 'PATCH' });
                router.push('/inbox');
              }}
              className="px-3 py-2 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">archive</span>
              <span>Archive</span>
            </button>

            <button
              onClick={async () => {
                if (confirm('Are you sure you want to delete this email?')) {
                  await apiFetch(`/emails/${email.id}`, { method: 'DELETE' });
                  router.push('/inbox');
                }
              }}
              className="px-3 py-2 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">delete</span>
              <span>Delete</span>
            </button>
          </div>
        </div>

        {/* Dual Panel Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Panel: Email Content */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 transition-colors">
              <div className="pb-4 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-slate-900 text-indigo-400 dark:bg-slate-800 dark:text-indigo-300 font-mono tracking-wider uppercase">
                    Original Email Message
                  </span>
                  {email.ai_analysis?.category && (
                    <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                      {email.ai_analysis.category}
                    </span>
                  )}
                </div>

                <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight leading-snug">{email.subject}</h1>
                
                <div className="flex items-center justify-between mt-3 text-xs text-slate-500 dark:text-slate-400">
                  <div className="min-w-0">
                    <span className="font-bold text-slate-900 dark:text-white">{email.sender_name}</span>{' '}
                    <span className="text-slate-400 dark:text-slate-500">&lt;{email.sender_email}&gt;</span>
                    {email.recipient_email && (
                      <div className="mt-0.5 truncate">
                        <span className="font-bold text-slate-500 dark:text-slate-400">To:</span>{' '}
                        <span className="text-slate-400 dark:text-slate-500">{email.recipient_email}</span>
                      </div>
                    )}
                  </div>
                  <span className="font-mono text-[11px] shrink-0">{fmtDateTime(email.received_at)}</span>
                </div>
              </div>

              {/* Email Body */}
              <div className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap py-2 font-sans">
                {email.body_plain}
              </div>
            </div>

            {/* Collapsible Thread Messages */}
            {threadMessages.length > 1 && (
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-colors">
                <button
                  onClick={() => setShowThread(!showThread)}
                  className="w-full p-4 bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-200 transition"
                >
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px] text-indigo-500">layers</span>
                    <span>Email Thread Conversation ({threadMessages.length} Messages)</span>
                  </div>
                  <span className="material-symbols-outlined text-[18px]">
                    {showThread ? 'expand_less' : 'expand_more'}
                  </span>
                </button>

                {showThread && (
                  <div className="p-4 space-y-4 divide-y divide-slate-100 dark:divide-slate-800">
                    {[...threadMessages].reverse().map((msg) => (  /* newest message first */
                      <div key={msg.id} className="pt-3 first:pt-0 space-y-1 text-xs">
                        <div className="flex justify-between text-slate-500 dark:text-slate-400">
                          <span className="font-bold text-slate-900 dark:text-white">
                            {msg.is_outbound ? 'You (Outbound Reply)' : msg.sender_name}
                          </span>
                          <span className="font-mono text-[10px]">{fmtDateTime(msg.received_at)}</span>
                        </div>
                        <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{msg.body_preview || msg.body_plain}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Panel: AI Analysis Summary & Metadata */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-slate-900 dark:bg-slate-900 text-white rounded-2xl p-5 border border-slate-800 shadow-xl space-y-4">
              
              {/* Header & Mode Switcher */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px] text-indigo-400">auto_awesome</span>
                  <h3 className="font-bold text-sm tracking-tight text-white">AI Email Analysis</h3>
                </div>

                <div className="bg-slate-800 p-0.5 rounded-lg flex text-[10px] font-bold">
                  <button
                    onClick={() => setSummaryMode('short')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      summaryMode === 'short' ? 'bg-indigo-500 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Short
                  </button>
                  <button
                    onClick={() => setSummaryMode('detailed')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      summaryMode === 'detailed' ? 'bg-indigo-500 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Detailed
                  </button>
                </div>
              </div>

              {/* Summary Box */}
              <div className="bg-slate-800/70 p-3.5 rounded-xl border border-slate-700/60 text-xs text-slate-200 leading-relaxed font-sans">
                {summaryMode === 'short'
                  ? email.ai_analysis?.short_summary
                  : email.ai_analysis?.detailed_summary}
              </div>

              {/* Priority & Reason */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-semibold">Priority Level</span>
                  <span className={`font-black px-2.5 py-0.5 rounded-full border text-[10px] ${priorityColor}`}>
                    ● {email.ai_analysis?.priority || 'MEDIUM'}
                  </span>
                </div>

                {email.ai_analysis?.priority_reason && (
                  <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-[11px] text-rose-300 flex items-start gap-2">
                    <span className="material-symbols-outlined text-[16px] text-rose-400 shrink-0 mt-0.5">error</span>
                    <span><strong>Reason:</strong> {email.ai_analysis.priority_reason}</span>
                  </div>
                )}
              </div>

              {/* Category & Sentiment */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 bg-slate-800/70 rounded-xl border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-0.5">Category</span>
                  <span className="font-bold text-indigo-400">{email.ai_analysis?.category}</span>
                </div>

                <div className="p-3 bg-slate-800/70 rounded-xl border border-slate-700/60">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-0.5">Sentiment & Conf.</span>
                  <span className="font-bold text-amber-400">
                    {email.ai_analysis?.sentiment}
                    {typeof email.ai_analysis?.sentiment_confidence === 'number' && email.ai_analysis.sentiment_confidence > 0
                      ? ` (${Math.round(email.ai_analysis.sentiment_confidence * 100)}%)`
                      : ''}
                  </span>
                </div>
              </div>

              {/* Detected Deadlines */}
              {email.deadlines && email.deadlines.length > 0 && (
                <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/60 space-y-1.5 text-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px] text-indigo-400">calendar_month</span>
                    Detected Deadlines
                  </span>
                  {email.deadlines.map((d) => (
                    <div key={d.id} className="flex justify-between items-center text-slate-300 pt-1 border-t border-slate-800 first:border-0 first:pt-0">
                      <span>{d.title}</span>
                      <span className="font-mono font-bold text-amber-400 text-[11px]">{d.due_date}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Structured Extracted Info */}
              {email.extracted_info && (
                <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/60 space-y-1.5 text-xs">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Structured Extracted Info
                  </span>
                  {email.extracted_info.order_number && (
                    <div className="flex justify-between text-slate-300">
                      <span>Order Number:</span>
                      <span className="font-mono font-bold text-white">#{email.extracted_info.order_number}</span>
                    </div>
                  )}
                  {email.extracted_info.amount && (
                    <div className="flex justify-between text-slate-300">
                      <span>Amount:</span>
                      <span className="font-mono font-bold text-emerald-400">{email.extracted_info.amount}</span>
                    </div>
                  )}
                  {email.extracted_info.requested_action && (
                    <div className="flex justify-between text-slate-300 gap-2">
                      <span className="shrink-0">Action Requested:</span>
                      <span className="font-medium text-indigo-300 text-right">{email.extracted_info.requested_action}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Panel: Smart Reply Assistant */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-md space-y-4 transition-colors">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px] text-indigo-500">psychology</span>
              <h3 className="font-bold text-slate-900 dark:text-white text-sm">Smart Reply — Context-Aware AI Assistant</h3>
            </div>

            {/* Tone Selection Dropdown */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Tone:</span>
              <select
                value={selectedTone}
                onChange={(e) => {
                  setSelectedTone(e.target.value);
                  handleGenerateReply(e.target.value);
                }}
                className="text-xs font-semibold bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-1.5 outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800 dark:text-slate-200"
              >
                {['Professional', 'Friendly', 'Short', 'Detailed', 'Apologetic', 'Formal'].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Smart Reply Textarea */}
          <div className="relative">
            <textarea
              value={replyDraft}
              onChange={(e) => setReplyDraft(e.target.value)}
              placeholder="Click 'Generate Smart Reply' to craft an AI response..."
              rows={5}
              className="w-full text-sm p-4 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-800 dark:text-slate-200 font-sans"
            />

            {approvedStatus === 'approved' && (
              <div className="absolute top-3 right-3 bg-emerald-500 text-white font-bold text-[10px] px-3 py-1 rounded-full shadow-md flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">check</span>
                <span>Approved by Human</span>
              </div>
            )}
            {approvedStatus === 'rejected' && (
              <div className="absolute top-3 right-3 bg-rose-500 text-white font-bold text-[10px] px-3 py-1 rounded-full shadow-md">
                Rejected by Human
              </div>
            )}
          </div>

          {replyNotice && (
            <div className={`text-xs font-medium rounded-xl px-3.5 py-2.5 border ${replyNotice.ok
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800'
              : 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800'}`}>
              {replyNotice.text}
            </div>
          )}

          {/* Smart Reply Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleGenerateReply()}
                disabled={replyLoading}
                className="px-4 py-2.5 bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-60"
              >
                {replyLoading ? (
                  <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                ) : (
                  <span className="material-symbols-outlined text-[16px]">refresh</span>
                )}
                <span>{replyDraft ? 'Regenerate Draft' : 'Generate Smart Reply'}</span>
              </button>

              <button
                onClick={handleCopyReply}
                disabled={!replyDraft}
                className="px-3.5 py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[16px]">{copied ? 'check' : 'content_copy'}</span>
                <span>{copied ? 'Copied!' : 'Copy'}</span>
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsRejectOpen(true)}
                disabled={!replyDraft || approvedStatus === 'approved'}
                className="px-4 py-2.5 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/40 text-rose-600 dark:text-rose-400 text-xs font-bold rounded-xl transition-all border border-rose-200 dark:border-rose-800 flex items-center gap-1.5 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[16px]">thumb_down</span>
                <span>Reject</span>
              </button>

              <button
                onClick={handleApproveReply}
                disabled={!replyDraft || approving || approvedStatus === 'approved'}
                className={`px-5 py-2.5 text-xs font-bold rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50 ${
                  approvedStatus === 'approved'
                    ? 'bg-emerald-600 text-white cursor-default'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">thumb_up</span>
                <span>{approving ? 'Sending…' : approvedStatus === 'approved' ? 'Reply Approved' : 'Approve Reply'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Reject Feedback Modal */}
      {isRejectOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 max-w-md w-full rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white">Reject Smart Reply Draft</h3>
            <p className="text-xs text-slate-400">
              Provide feedback or instructions on why this draft was rejected so the AI can regenerate a better draft.
            </p>

            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Too casual, please mention our refund policy for broken items..."
              rows={4}
              className="w-full text-xs p-3 bg-slate-800 border border-slate-700 rounded-xl text-white outline-none focus:border-indigo-500 font-sans"
            />

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsRejectOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleRejectReply}
                disabled={rejecting || !rejectReason.trim()}
                className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white rounded-xl shadow transition disabled:opacity-50"
              >
                {rejecting ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
