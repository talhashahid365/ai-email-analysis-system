"use client";

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import UploadModal from '@/components/UploadModal';
import { apiFetch } from '@/lib/api';
import { EmailListItem, EmailDetail, ThreadDetail, AIReply } from '@/types';
import { fmtDateTime, timeValue } from '@/lib/time';

function InboxContent() {
  const searchParams = useSearchParams();
  const targetId = searchParams.get('id') || searchParams.get('selected');

  const [emails, setEmails] = useState<EmailListItem[]>([]);
  const [activeEmail, setActiveEmail] = useState<EmailDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedPriority, setSelectedPriority] = useState<string>('ALL');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [replyOnly, setReplyOnly] = useState(false);
  const [actionOnly, setActionOnly] = useState(false);
  const [sentiment, setSentiment] = useState<string>('ALL');
  const [datePreset, setDatePreset] = useState<string>('ALL');
  const [senderFilter, setSenderFilter] = useState('');
  const [view, setView] = useState<'inbox' | 'starred' | 'archived'>('inbox');
  const [actionError, setActionError] = useState('');
  const [thread, setThread] = useState<ThreadDetail | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [replyNotice, setReplyNotice] = useState<{ ok: boolean; text: string } | null>(null);

  // Smart reply state
  const [selectedTone, setSelectedTone] = useState<string>('Professional');
  const [replyDraft, setReplyDraft] = useState<string>('');
  const [activeReplyObj, setActiveReplyObj] = useState<AIReply | null>(null);
  const [replyLoading, setReplyLoading] = useState(false);
  const [approvedStatus, setApprovedStatus] = useState<string | null>(null);

  const fetchEmails = async (silent = false) => {
    if (!silent) setLoadingList(true);
    try {
      let query = `/emails?`;
      if (selectedCategory !== 'ALL') query += `category=${encodeURIComponent(selectedCategory)}&`;
      if (selectedPriority !== 'ALL') query += `priority=${selectedPriority}&`;
      if (search) query += `search_text=${encodeURIComponent(search)}&`;
      if (unreadOnly) query += `unread_only=true&`;
      if (replyOnly) query += `reply_required_only=true&`;
      if (actionOnly) query += `action_required_only=true&`;
      if (sentiment !== 'ALL') query += `sentiment=${encodeURIComponent(sentiment)}&`;
      if (datePreset !== 'ALL') query += `date_preset=${datePreset}&`;
      if (senderFilter.trim()) query += `sender=${encodeURIComponent(senderFilter.trim())}&`;
      if (view === 'archived') query += `archived=true&`;
      if (view === 'starred') query += `starred_only=true&`;

      const data: EmailListItem[] = await apiFetch(query);
      // newest first, by the time that is shown on screen
      setEmails([...data].sort((a, b) => timeValue(b.received_at) - timeValue(a.received_at) || b.id - a.id));

      if (silent) return;
      if (targetId) {
        loadEmailDetail(Number(targetId));
      } else if (data.length > 0 && !activeEmail) {
        loadEmailDetail(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load emails:', err);
    } finally {
      setLoadingList(false);
    }
  };

  const loadEmailDetail = async (id: number) => {
    setLoadingDetail(true);
    try {
      const data: EmailDetail = await apiFetch(`/emails/${id}`);
      setActiveEmail(data);
      setReplyNotice((n) => (n && activeEmail && activeEmail.id === id ? n : null));
      setEmails((prev) => prev.map((e) => (e.id === id ? { ...e, is_read: true } : e)));

      if (data.ai_replies && data.ai_replies.length > 0) {
        const latest = data.ai_replies[data.ai_replies.length - 1];
        setActiveReplyObj(latest);
        setReplyDraft(latest.edited_body || latest.suggested_body);
        setSelectedTone(latest.selected_tone);
        setApprovedStatus(latest.status);
      } else {
        setActiveReplyObj(null);
        setReplyDraft('');
        setApprovedStatus(null);
      }
    } catch (err) {
      console.error('Failed to load email detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, [selectedCategory, selectedPriority, search, unreadOnly, replyOnly, actionOnly, sentiment, datePreset, senderFilter, view]);

  // Live inbox: the backend pulls new mail from the real mailbox on its own; here we just re-read the list every 15 s.
  const threadId = activeEmail?.thread_id;
  const loadThread = async (tid: number) => {
    try {
      const t: ThreadDetail = await apiFetch(`/emails/threads/${tid}`);
      setThread((cur) => (cur && cur.id === tid && JSON.stringify(cur.messages.map((m) => m.id)) === JSON.stringify(t.messages.map((m) => m.id)) ? cur : t));
    } catch { /* thread is optional */ }
  };
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.hidden) return;
      fetchEmails(true).then(() => setLastRefresh(new Date()));
      if (threadId) loadThread(threadId);
    }, 15000);
    return () => clearInterval(timer);
  }, [selectedCategory, selectedPriority, search, unreadOnly, replyOnly, actionOnly, sentiment, datePreset, senderFilter, view, threadId]);

  // Conversation (customer message, your reply, customer's follow-up) of the open email.
  useEffect(() => {
    setThread(null);
    if (threadId) loadThread(threadId);
  }, [threadId, activeEmail?.id]);

  // While the AI is still analysing the open email, quietly re-fetch it until the result is ready.
  useEffect(() => {
    if (!activeEmail || activeEmail.ai_analysis || !['queued', 'processing'].includes(activeEmail.processing_status)) return;
    const id = activeEmail.id;
    const timer = setTimeout(async () => {
      try {
        const fresh: EmailDetail = await apiFetch(`/emails/${id}`);
        setActiveEmail((cur) => (cur && cur.id === id ? fresh : cur));
      } catch { /* try again on next render */ }
    }, 3000);
    return () => clearTimeout(timer);
  }, [activeEmail]);

  const generateReply = async (emailId: number, tone: string) => {
    setReplyLoading(true);
    try {
      const res: AIReply = await apiFetch(`/emails/${emailId}/reply`, {
        method: 'POST',
        body: JSON.stringify({ tone }),
      });
      setActiveReplyObj(res);
      setReplyDraft(res.suggested_body);
      setApprovedStatus(res.status);
    } catch (err) {
      console.error('Failed to generate reply:', err);
    } finally {
      setReplyLoading(false);
    }
  };

  const syncMailbox = async () => {
    setSyncing(true);
    setSyncMsg('');
    try {
      const r = await apiFetch('/emails/sync-inbox', { method: 'POST' });
      setSyncMsg(`Checked ${r.checked}: ${r.imported} new, ${r.duplicates} already imported${r.skipped_own ? `, ${r.skipped_own} own mail skipped` : ''}.`);
      await fetchEmails();
    } catch (err: any) {
      setSyncMsg(err?.message || 'Mailbox sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleApproveReply = async () => {
    if (!activeEmail || !activeReplyObj) return;
    setReplyNotice(null);
    try {
      const res: AIReply = await apiFetch(`/emails/${activeEmail.id}/reply/${activeReplyObj.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ edited_body: replyDraft }),
      });
      setApprovedStatus('approved');
      setActiveReplyObj(res);
      setReplyNotice({
        ok: !!res.delivered,
        text: res.delivery_note || (res.delivered ? 'Reply e-mailed.' : 'Reply recorded.'),
      });
      // reply is now an outbound message in the thread: refresh the open email and the list counters
      loadEmailDetail(activeEmail.id);
      if (activeEmail.thread_id) loadThread(activeEmail.thread_id);
      fetchEmails(true);
    } catch (err: any) {
      setReplyNotice({ ok: false, text: err?.message || 'Could not send the reply. Nothing was recorded.' });
    }
  };

  const dropFromList = (id: number) => {
    setEmails((prev) => prev.filter((e) => e.id !== id));
    setActiveEmail((cur) => (cur && cur.id === id ? null : cur));
  };

  const runEmailAction = async (id: number, action: 'read' | 'unread' | 'star' | 'archive' | 'delete') => {
    setActionError('');
    try {
      if (action === 'delete') {
        if (!window.confirm('Delete this email? It will be removed from your inbox.')) return;
        await apiFetch(`/emails/${id}`, { method: 'DELETE' });
        dropFromList(id);
      } else if (action === 'archive') {
        await apiFetch(`/emails/${id}/toggle-archive`, { method: 'PATCH' });
        dropFromList(id);
      } else if (action === 'star') {
        await apiFetch(`/emails/${id}/toggle-star`, { method: 'PATCH' });
        setEmails((prev) =>
          view === 'starred'
            ? prev.filter((e) => e.id !== id)
            : prev.map((e) => (e.id === id ? { ...e, is_starred: !e.is_starred } : e))
        );
        setActiveEmail((cur) => (cur && cur.id === id ? { ...cur, is_starred: !cur.is_starred } : cur));
      } else {
        await apiFetch(`/emails/${id}/${action}`, { method: 'PATCH' });
        const isRead = action === 'read';
        setEmails((prev) => prev.map((e) => (e.id === id ? { ...e, is_read: isRead } : e)));
        setActiveEmail((cur) => (cur && cur.id === id ? { ...cur, is_read: isRead } : cur));
      }
    } catch (err: any) {
      setActionError(err?.message || 'Action failed. Please try again.');
    }
  };

  const urgentCount = emails.filter((e) => e.priority === 'CRITICAL' || e.priority === 'HIGH').length;
  const filtersActive =
    search.trim() !== '' || selectedCategory !== 'ALL' || selectedPriority !== 'ALL' ||
    unreadOnly || replyOnly || actionOnly || sentiment !== 'ALL' || datePreset !== 'ALL' ||
    senderFilter.trim() !== '';

  return (
    <AppLayout
      title="Inbox Intelligence"
      onOpenUpload={() => setIsUploadOpen(true)}
      urgentCount={urgentCount}
      totalCount={emails.length}
      onSearchChange={(val) => setSearch(val)}
      searchValue={search}
    >
        <div className="relative w-full bg-slate-50 dark:bg-[#0B0F19] px-4 md:px-6 py-6 transition-colors">
          <div className="flex flex-col w-full gap-4">
            
            {/* Top Triage Bar */}
            <section className="w-full flex flex-col gap-3">
              <div className="flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-3 bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 p-3.5 rounded-2xl shadow-xs transition-colors">
                
                {/* Natural Language Omnibox */}
                <div className="flex-1 flex items-center gap-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 px-3.5 py-2 rounded-xl">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">psychology</span>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Filter by intent: 'Find angry customers', 'Urgent SLA breaches', 'Invoices pending approval'..."
                    className="bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 text-xs w-full focus:outline-hidden font-medium"
                  />
                  {search && (
                    <button onClick={() => setSearch('')} className="text-slate-400 hover:text-slate-600 dark:hover:text-white">
                      <span className="material-symbols-outlined text-[16px]">close</span>
                    </button>
                  )}
                </div>

                {/* Buttons */}
                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  <button
                    onClick={syncMailbox}
                    disabled={syncing}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold text-xs transition-all shadow-xs"
                  >
                    <span className={`material-symbols-outlined text-[18px] ${syncing ? 'animate-spin' : ''}`}>sync</span>
                    <span>{syncing ? 'Syncing…' : 'Sync Mailbox'}</span>
                  </button>
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400" title="The inbox refreshes by itself every 15 seconds">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    Live{lastRefresh ? ` · ${lastRefresh.toLocaleTimeString()}` : ''}
                  </span>
                  <button
                    onClick={() => setIsUploadOpen(true)}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs transition-all shadow-xs"
                  >
                    <span className="material-symbols-outlined text-[18px]">upload_file</span>
                    <span>Import .EML / JSON</span>
                  </button>
                  <button
                    onClick={() => fetchEmails()}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs transition-all shadow-xs"
                  >
                    <span className="material-symbols-outlined text-[18px] text-sky-600 dark:text-sky-400">auto_mode</span>
                    <span>Batch AI Triage</span>
                  </button>
                </div>
              </div>

              {/* Filters row */}
              <div className="flex flex-wrap items-center gap-2">
                {([
                  ['Unread', unreadOnly, setUnreadOnly],
                  ['Reply Required', replyOnly, setReplyOnly],
                  ['Action Required', actionOnly, setActionOnly],
                ] as [string, boolean, (v: boolean) => void][]).map(([label, on, set]) => (
                  <button
                    key={label}
                    onClick={() => set(!on)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition-all shadow-xs ${
                      on
                        ? 'bg-indigo-600 text-white'
                        : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
                <select
                  value={sentiment}
                  onChange={(e) => setSentiment(e.target.value)}
                  className="px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200"
                >
                  <option value="ALL">Any sentiment</option>
                  {['Positive', 'Neutral', 'Negative', 'Angry', 'Urgent'].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <select
                  value={datePreset}
                  onChange={(e) => setDatePreset(e.target.value)}
                  className="px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200"
                >
                  <option value="ALL">Any date</option>
                  <option value="today">Today</option>
                  <option value="yesterday">Yesterday</option>
                  <option value="this_week">This week</option>
                </select>
              </div>
            </section>

            {/* View tabs */}
            <div className="flex items-center gap-2">
              {(['inbox', 'starred', 'archived'] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => { setView(v); setActiveEmail(null); }}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-semibold capitalize border transition-colors ${
                    view === v
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {v}
                </button>
              ))}
              {actionError && <span className="text-xs text-rose-600 dark:text-rose-400">{actionError}</span>}
              {syncMsg && <span className="text-xs text-indigo-600 dark:text-indigo-400">{syncMsg}</span>}
            </div>

            {/* Master-Detail Email Grid */}
            <div className="grid grid-cols-12 gap-4 items-start w-full">
              
              {/* Left Column: Email Thread List */}
              <div className="col-span-12 lg:col-span-5 xl:col-span-4 flex flex-col gap-2.5 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1">
                {loadingList ? (
                  <div className="p-8 text-center text-xs text-slate-400">Loading inbox telemetry...</div>
                ) : emails.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400 bg-white dark:bg-[#0F172A] rounded-2xl border border-slate-200 dark:border-slate-800">
                    {filtersActive ? (
                      'No emails match the current filters.'
                    ) : (
                      <div className="flex flex-col items-center gap-3">
                        <span>Your inbox is empty.</span>
                        <button
                          onClick={() => setIsUploadOpen(true)}
                          className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs"
                        >
                          Add your first email
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  emails.map((email) => {
                    const isSelected = activeEmail?.id === email.id;
                    const priorityBg =
                      email.priority === 'CRITICAL' || email.priority === 'HIGH'
                        ? 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                        : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300';

                    return (
                      <article
                        key={email.id}
                        onClick={() => loadEmailDetail(email.id)}
                        className={`p-4 rounded-2xl transition-all cursor-pointer shadow-xs relative ${
                          isSelected
                            ? 'bg-white dark:bg-slate-800 border-2 border-indigo-500 dark:border-indigo-400 text-slate-900 dark:text-white shadow-md'
                            : 'bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-50/60 dark:hover:bg-slate-800/40'
                        }`}
                      >
                        {email.priority === 'CRITICAL' && (
                          <div className="absolute left-0 top-3 bottom-3 w-1.5 bg-rose-500 rounded-r-full" />
                        )}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-xs shrink-0 border border-indigo-200 dark:border-indigo-800">
                              {email.sender_name.charAt(0)}
                            </div>
                            <div className="flex flex-col min-w-0">
                              <span className={`text-xs text-slate-900 dark:text-white truncate flex items-center gap-1.5 ${email.is_read ? 'font-medium' : 'font-bold'}`}>
                                {!email.is_read && <span aria-label="Unread" className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" />}
                                {email.sender_name}
                              </span>
                              <span className="text-[10px] text-slate-400 truncate">{email.sender_email}</span>
                            </div>
                          </div>
                          <span className="text-[10px] font-mono text-slate-400 shrink-0">
                            {fmtDateTime(email.received_at, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <h3 className={`text-xs text-slate-900 dark:text-white mb-1 line-clamp-1 ${email.is_read ? 'font-medium' : 'font-bold'}`}>{email.subject}</h3>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mb-3 leading-relaxed">
                          {email.body_preview}
                        </p>

                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${priorityBg}`}>
                            {email.priority}
                          </span>
                          <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
                            {email.category}
                          </span>
                          {email.processing_status && email.processing_status !== 'completed' && (
                            <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300">
                              AI: {email.processing_status}
                            </span>
                          )}
                          {email.processing_status === 'completed' && (
                            <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300">
                              AI: done
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800" onClick={(e) => e.stopPropagation()}>
                          <button title={email.is_starred ? 'Unstar' : 'Star'} aria-label="Toggle star" onClick={() => runEmailAction(email.id, 'star')} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700">
                            <span className={`material-symbols-outlined text-[18px] ${email.is_starred ? 'text-amber-500' : 'text-slate-400'}`} style={email.is_starred ? { fontVariationSettings: "'FILL' 1" } : undefined}>star</span>
                          </button>
                          <button title={email.is_read ? 'Mark as unread' : 'Mark as read'} aria-label={email.is_read ? 'Mark as unread' : 'Mark as read'} onClick={() => runEmailAction(email.id, email.is_read ? 'unread' : 'read')} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700">
                            <span className="material-symbols-outlined text-[18px] text-slate-400">{email.is_read ? 'mark_email_unread' : 'drafts'}</span>
                          </button>
                          <button title={view === 'archived' ? 'Move to inbox' : 'Archive'} aria-label="Toggle archive" onClick={() => runEmailAction(email.id, 'archive')} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700">
                            <span className="material-symbols-outlined text-[18px] text-slate-400">{view === 'archived' ? 'unarchive' : 'archive'}</span>
                          </button>
                          <button title="Delete" aria-label="Delete email" onClick={() => runEmailAction(email.id, 'delete')} className="p-1 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40">
                            <span className="material-symbols-outlined text-[18px] text-slate-400 hover:text-rose-500">delete</span>
                          </button>
                        </div>
                      </article>
                    );
                  })
                )}
              </div>

              {/* Right Column: Email Detail Workspace */}
              <div className="col-span-12 lg:col-span-7 xl:col-span-8 flex flex-col gap-4">
                {loadingDetail ? (
                  <div className="p-12 text-center text-xs text-slate-400 bg-white dark:bg-[#0F172A] rounded-2xl border border-slate-200 dark:border-slate-800">
                    Loading email detail & AI synthesis...
                  </div>
                ) : !activeEmail ? (
                  <div className="p-12 text-center text-xs text-slate-500 dark:text-slate-400 bg-white dark:bg-[#0F172A] rounded-2xl border border-slate-200 dark:border-slate-800">
                    Select an email thread from the left list to inspect details.
                  </div>
                ) : (
                  <>
                    {/* Header */}
                    <header className="p-4 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 flex flex-col gap-3 shadow-xs transition-colors">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300">
                            INCIDENT #{activeEmail.id}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                            <span className="material-symbols-outlined text-[14px]">lock</span> TLS 1.3 ENCRYPTED
                          </span>
                        </div>
                      </div>

                      <h2 className="text-base font-extrabold text-slate-900 dark:text-white leading-tight">
                        {activeEmail.subject}
                      </h2>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        From <span className="font-bold text-slate-900 dark:text-white">{activeEmail.sender_name}</span> ({activeEmail.sender_email})
                      </div>
                    </header>

                    {/* AI Cognitive Synthesis Box */}
                    <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-50/70 via-white to-sky-50/50 dark:from-slate-900 dark:via-[#0F172A] dark:to-slate-900 border border-indigo-100 dark:border-slate-800 shadow-xs space-y-4 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">auto_awesome</span>
                          <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">AI Cognitive Synthesis</h3>
                        </div>
                        {activeEmail.ai_analysis?.sentiment_confidence ? (
                          <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 font-bold bg-indigo-100 dark:bg-indigo-950/60 px-2 py-0.5 rounded">
                            CONFIDENCE {Math.round(activeEmail.ai_analysis.sentiment_confidence * 100)}%
                          </span>
                        ) : null}
                      </div>

                      {(() => {
                        const a = activeEmail.ai_analysis;
                        const pending = !a && ['queued', 'processing'].includes(activeEmail.processing_status);
                        const failed = !a && activeEmail.processing_status === 'failed';
                        const category = a?.category || activeEmail.category;
                        const priority = a?.priority || activeEmail.priority;
                        const sentiment = a?.sentiment || activeEmail.sentiment;
                        const prioStyle: Record<string, string> = {
                          CRITICAL: 'text-rose-600 dark:text-rose-400', HIGH: 'text-amber-600 dark:text-amber-400',
                          MEDIUM: 'text-sky-600 dark:text-sky-400', LOW: 'text-slate-500 dark:text-slate-400',
                        };
                        const sentStyle: Record<string, string> = {
                          Positive: 'text-emerald-600 dark:text-emerald-400', Neutral: 'text-blue-600 dark:text-blue-400',
                          Negative: 'text-orange-600 dark:text-orange-400', Angry: 'text-red-600 dark:text-red-400',
                          Urgent: 'text-purple-600 dark:text-purple-400',
                        };
                        const cell = 'p-3 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700';
                        const label = 'text-[10px] font-bold text-slate-400 uppercase block';
                        const value = (cls: string, text?: string) => (
                          <span className={`text-xs font-extrabold block mt-0.5 ${cls}`}>
                            {pending ? <span className="inline-block h-3 w-16 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" /> : (a || !failed ? text : '—')}
                          </span>
                        );
                        return (
                          <>
                            <div className="grid grid-cols-3 gap-3">
                              <div className={cell}><span className={label}>Category</span>{value('text-slate-900 dark:text-white', category)}</div>
                              <div className={cell}><span className={label}>Priority</span>{value(prioStyle[priority] || 'text-slate-900 dark:text-white', priority)}</div>
                              <div className={cell}><span className={label}>Sentiment</span>{value(sentStyle[sentiment] || 'text-slate-900 dark:text-white', sentiment)}</div>
                            </div>
                            {pending && <p className="text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">AI is analysing this email… it will appear here in a few seconds.</p>}
                            {failed && <p className="text-[11px] text-rose-600 dark:text-rose-400 font-medium">Analysis failed{activeEmail.processing_error ? `: ${activeEmail.processing_error}` : ''}. Re-run analysis to try again.</p>}
                          </>
                        );
                      })()}

                      <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-200 leading-relaxed font-medium">
                        <span className="font-bold text-indigo-600 dark:text-indigo-400">Core Summary: </span>
                        {activeEmail.ai_analysis?.short_summary || activeEmail.body_preview}
                      </div>
                    </div>

                    {/* Conversation: every message of this thread, oldest first */}
                    {thread && thread.messages.length > 1 && (
                      <div className="p-6 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 shadow-xs space-y-3 transition-colors">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Conversation ({thread.messages.length} messages)</h3>
                        <ol className="space-y-2.5">
                          {[...thread.messages].reverse().map((m) => (  /* newest message first */
                            <li key={m.id}>
                              <button
                                onClick={() => m.id !== activeEmail.id && loadEmailDetail(m.id)}
                                className={`w-full text-left rounded-xl border px-3.5 py-2.5 transition-colors ${m.id === activeEmail.id ? 'ring-2 ring-indigo-400/60 ' : ''}${m.is_outbound
                                  ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-900 ml-6'
                                  : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 mr-6'}`}
                              >
                                <div className="flex items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wide">
                                  <span className={m.is_outbound ? 'text-indigo-600 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'}>
                                    {m.is_outbound ? 'You replied' : m.sender_name}
                                  </span>
                                  <span className="text-slate-400 font-medium normal-case">{fmtDateTime(m.received_at)}</span>
                                </div>
                                <p className="mt-1 text-xs text-slate-700 dark:text-slate-200 line-clamp-3 whitespace-pre-line">{m.body_preview}</p>
                                {!m.is_outbound && m.reply_status === 'pending' && (
                                  <span className="mt-1.5 inline-block text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300">Waiting for your reply</span>
                                )}
                              </button>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}

                    {/* Email Message Content Body */}
                    <div className="p-6 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 shadow-xs space-y-3 transition-colors">
                      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Original Message Content</h3>
                      <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-line font-mono bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200/70 dark:border-slate-700/70">
                        {activeEmail.body_plain || activeEmail.body_preview}
                      </div>
                    </div>

                    {/* Smart Reply Generator */}
                    <div className="p-5 rounded-2xl bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 shadow-xs space-y-4 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-blue-600 dark:text-blue-400 text-[20px]">reply_all</span>
                          <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">AI Smart Reply Studio</h3>
                        </div>
                        {approvedStatus === 'approved' && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                            Approved & Recorded
                          </span>
                        )}
                      </div>

                      {/* Tone selector */}
                      <div className="flex items-center gap-2 overflow-x-auto pb-1">
                        {['Professional', 'Friendly', 'Short', 'Detailed', 'Apologetic', 'Formal'].map((tone) => (
                          <button
                            key={tone}
                            onClick={() => {
                              setSelectedTone(tone);
                              generateReply(activeEmail.id, tone);
                            }}
                            className={`px-3 py-1 rounded-xl text-xs font-bold transition-all shadow-xs ${
                              selectedTone === tone
                                ? 'bg-indigo-600 text-white'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                            }`}
                          >
                            {tone}
                          </button>
                        ))}
                      </div>

                      {/* Textarea */}
                      <textarea
                        rows={4}
                        value={replyDraft}
                        onChange={(e) => setReplyDraft(e.target.value)}
                        placeholder="AI suggested response will appear here..."
                        className="w-full p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-white focus:outline-hidden font-medium"
                      />

                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => generateReply(activeEmail.id, selectedTone)}
                          disabled={replyLoading}
                          className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-bold text-xs transition-all flex items-center gap-1.5"
                        >
                          <span className="material-symbols-outlined text-[16px]">refresh</span>
                          <span>Regenerate</span>
                        </button>
                        <button
                          onClick={handleApproveReply}
                          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-600/25 transition-all flex items-center gap-1.5"
                        >
                          <span className="material-symbols-outlined text-[16px]">send</span>
                          <span>Approve & Transmit</span>
                        </button>
                      </div>
                      {replyNotice && (
                        <div className={`text-xs font-medium rounded-xl px-3.5 py-2.5 border ${replyNotice.ok
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                          : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'}`}>
                          {replyNotice.text}
                        </div>
                      )}
                    </div>

                  </>
                )}
              </div>

            </div>

          </div>
        </div>

      {isUploadOpen && (
        <UploadModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onSuccess={() => {
            fetchEmails();
            setIsUploadOpen(false);
          }}
        />
      )}
    </AppLayout>
  );
}

export default function InboxPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-400">Loading Inbox...</div>}>
      <InboxContent />
    </Suspense>
  );
}
