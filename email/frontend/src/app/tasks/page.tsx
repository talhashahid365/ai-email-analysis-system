"use client";

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import { apiFetch } from '@/lib/api';
import { ActionItem, Deadline } from '@/types';

type Filter = 'all' | 'pending' | 'completed';

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whole days from today (local) until the due date. Negative = overdue. null = unparseable date. */
function daysUntil(due: string): number | null {
  const parsed = new Date(due);
  if (Number.isNaN(parsed.getTime())) return null;
  const today = new Date();
  const a = Date.UTC(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  const b = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((a - b) / DAY_MS);
}

function formatDue(due: string): string {
  const parsed = new Date(due);
  if (Number.isNaN(parsed.getTime())) return due;
  return parsed.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}

function relativeLabel(days: number | null): string {
  if (days === null) return '';
  if (days < -1) return `${Math.abs(days)} days overdue`;
  if (days === -1) return '1 day overdue';
  if (days === 0) return 'Due today';
  if (days === 1) return 'Due tomorrow';
  return `In ${days} days`;
}

type DeadlineGroup = { key: string; label: string; tone: string; items: Deadline[] };

export default function TasksPage() {
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');

  const fetchData = async () => {
    try {
      const [actData, dlData] = await Promise.all([apiFetch('/actions'), apiFetch('/deadlines')]);
      setActions(Array.isArray(actData) ? actData : []);
      setDeadlines(Array.isArray(dlData) ? dlData : []);
      setError('');
    } catch (err) {
      console.error(err);
      setError('Could not load your tasks. Check that the backend is running, then retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Optimistic toggles: update the UI immediately, resync with the server if the request fails.
  const handleToggleAction = async (id: number) => {
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, status: a.status === 'completed' ? 'pending' : 'completed' } : a)));
    try {
      await apiFetch(`/actions/${id}/toggle`, { method: 'PATCH' });
    } catch (err) {
      console.error(err);
      fetchData();
    }
  };

  const handleToggleDeadline = async (id: number) => {
    setDeadlines((prev) => prev.map((d) => (d.id === id ? { ...d, is_completed: !d.is_completed } : d)));
    try {
      await apiFetch(`/deadlines/${id}/toggle`, { method: 'PATCH' });
    } catch (err) {
      console.error(err);
      fetchData();
    }
  };

  const q = query.trim().toLowerCase();

  const filteredActions = useMemo(() => {
    return actions
      .filter((a) => (filter === 'all' ? true : filter === 'pending' ? a.status !== 'completed' : a.status === 'completed'))
      .filter((a) => !q || a.task.toLowerCase().includes(q) || (a.deadline_text || '').toLowerCase().includes(q))
      .sort((x, y) => Number(x.status === 'completed') - Number(y.status === 'completed'));
  }, [actions, filter, q]);

  const filteredDeadlines = useMemo(() => {
    return deadlines
      .filter((d) => (filter === 'all' ? true : filter === 'pending' ? !d.is_completed : d.is_completed))
      .filter((d) => !q || d.title.toLowerCase().includes(q));
  }, [deadlines, filter, q]);

  const groups: DeadlineGroup[] = useMemo(() => {
    const overdue: Deadline[] = [];
    const soon: Deadline[] = [];
    const later: Deadline[] = [];
    const done: Deadline[] = [];
    filteredDeadlines.forEach((d) => {
      if (d.is_completed) { done.push(d); return; }
      const days = daysUntil(d.due_date);
      if (days !== null && days < 0) overdue.push(d);
      else if (days !== null && days <= 7) soon.push(d);
      else later.push(d);
    });
    const byDate = (x: Deadline, y: Deadline) => new Date(x.due_date).getTime() - new Date(y.due_date).getTime();
    return [
      { key: 'overdue', label: 'Overdue', tone: 'text-rose-600 dark:text-rose-400', items: overdue.sort(byDate) },
      { key: 'soon', label: 'Due within 7 days', tone: 'text-amber-600 dark:text-amber-400', items: soon.sort(byDate) },
      { key: 'later', label: 'Later / no date', tone: 'text-slate-500 dark:text-slate-400', items: later.sort(byDate) },
      { key: 'done', label: 'Completed', tone: 'text-emerald-600 dark:text-emerald-400', items: done },
    ].filter((g) => g.items.length > 0);
  }, [filteredDeadlines]);

  const pendingCount = actions.filter((a) => a.status !== 'completed').length;
  const doneCount = actions.filter((a) => a.status === 'completed').length;
  const openDeadlines = deadlines.filter((d) => !d.is_completed).length;
  const overdueCount = deadlines.filter((d) => {
    if (d.is_completed) return false;
    const days = daysUntil(d.due_date);
    return days !== null && days < 0;
  }).length;
  const completionPct = actions.length ? Math.round((doneCount / actions.length) * 100) : 0;

  const stats = [
    { label: 'Pending tasks', value: pendingCount, icon: 'pending_actions', tint: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400' },
    { label: 'Completed', value: doneCount, icon: 'task_alt', tint: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400' },
    { label: 'Open deadlines', value: openDeadlines, icon: 'event_upcoming', tint: 'bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-400' },
    { label: 'Overdue', value: overdueCount, icon: 'event_busy', tint: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400' },
  ];

  const filterCounts: Record<Filter, number> = {
    all: actions.length + deadlines.length,
    pending: pendingCount + openDeadlines,
    completed: doneCount + deadlines.filter((d) => d.is_completed).length,
  };

  const card = 'bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm';

  const skeleton = (
    <div className="space-y-2.5 animate-pulse">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-14 rounded-xl bg-slate-100 dark:bg-slate-800/60" />
      ))}
    </div>
  );

  const emptyState = (icon: string, title: string, hint: string) => (
    <div className="flex flex-col items-center justify-center text-center py-14 px-4">
      <div className="w-14 h-14 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-3">
        <span className="material-symbols-outlined text-[28px]">{icon}</span>
      </div>
      <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title}</p>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-xs">{hint}</p>
    </div>
  );

  const hasFilterOrQuery = filter !== 'all' || q !== '';

  return (
    <AppLayout title="Tasks & Deadlines">
      <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto w-full">

        {/* Page heading */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <h1 className="text-xl md:text-2xl font-black tracking-tight text-slate-900 dark:text-white">Tasks &amp; Deadlines</h1>
            <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-1">
              Action items and dates the AI found in your emails. Click an item to mark it done.
            </p>
          </div>
          <button
            onClick={() => { setLoading(true); fetchData(); }}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-bold text-slate-600 dark:text-slate-200 hover:border-indigo-300 dark:hover:border-indigo-500 transition-colors"
          >
            <span className={`material-symbols-outlined text-[16px] ${loading ? 'animate-spin' : ''}`}>refresh</span>
            Refresh
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-3 p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 text-xs font-semibold">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span className="flex-1">{error}</span>
            <button onClick={() => { setLoading(true); fetchData(); }} className="underline font-bold">Retry</button>
          </div>
        )}

        {/* KPI cards */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 md:gap-4">
          {stats.map((s) => (
            <div key={s.label} className={`${card} p-4 md:p-5 flex items-center gap-3 md:gap-4`}>
              <div className={`${s.tint} w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0`}>
                <span className="material-symbols-outlined text-[22px]">{s.icon}</span>
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider truncate">{s.label}</p>
                <p className="text-2xl font-black text-slate-900 dark:text-white leading-tight">{loading ? '—' : s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Progress */}
        {!loading && actions.length > 0 && (
          <div className={`${card} p-4 md:p-5`}>
            <div className="flex items-center justify-between text-xs font-bold mb-2">
              <span className="text-slate-600 dark:text-slate-300">Task completion</span>
              <span className="text-slate-900 dark:text-white font-mono">{doneCount}/{actions.length} · {completionPct}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500" style={{ width: `${completionPct}%` }} />
            </div>
          </div>
        )}

        {/* Toolbar: filter + search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="inline-flex p-1 rounded-xl bg-slate-100 dark:bg-slate-800/70 self-start">
            {(['all', 'pending', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3.5 py-1.5 text-xs font-bold rounded-lg capitalize transition-all flex items-center gap-1.5 ${
                  filter === f
                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                {f}
                <span className="text-[10px] font-mono opacity-70">{loading ? '' : filterCounts[f]}</span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/70 text-slate-400 focus-within:border-indigo-500 w-full md:w-72 transition-colors">
            <span className="material-symbols-outlined text-[18px]">search</span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search tasks and deadlines..."
              className="bg-transparent text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none w-full"
            />
            {query && (
              <button onClick={() => setQuery('')} aria-label="Clear search" className="hover:text-slate-600 dark:hover:text-slate-200">
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            )}
          </div>
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 items-start">

          {/* Action items */}
          <section className={`${card} flex flex-col overflow-hidden`}>
            <div className="flex items-center gap-2.5 px-5 py-4 border-b border-slate-100 dark:border-slate-800">
              <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">checklist</span>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">AI-extracted action items</h2>
              <span className="ml-auto text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-800 text-indigo-600 dark:text-indigo-300">
                {filteredActions.length} {filteredActions.length === 1 ? 'item' : 'items'}
              </span>
            </div>

            <div className="p-4 space-y-2 max-h-[560px] overflow-y-auto">
              {loading ? skeleton : filteredActions.length === 0 ? (
                hasFilterOrQuery
                  ? emptyState('filter_alt_off', 'Nothing matches', 'Try another filter or clear the search box.')
                  : emptyState('task_alt', 'No action items yet', 'Upload or process an email and any requests found in it will show up here.')
              ) : (
                filteredActions.map((act) => {
                  const done = act.status === 'completed';
                  return (
                    <div
                      key={act.id}
                      className={`group flex items-start gap-3 p-3.5 border rounded-xl transition-all ${
                        done
                          ? 'bg-emerald-50/60 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/50'
                          : 'bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-700/70 hover:border-indigo-300 dark:hover:border-indigo-500'
                      }`}
                    >
                      <button
                        onClick={() => handleToggleAction(act.id)}
                        aria-label={done ? 'Mark as pending' : 'Mark as done'}
                        className={`mt-0.5 flex-shrink-0 transition-colors ${done ? 'text-emerald-500' : 'text-slate-300 dark:text-slate-600 group-hover:text-indigo-400'}`}
                      >
                        <span className="material-symbols-outlined text-[22px]">{done ? 'check_circle' : 'radio_button_unchecked'}</span>
                      </button>
                      <div className="min-w-0 flex-1">
                        <p className={`text-[13px] font-semibold leading-snug break-words ${done ? 'line-through text-slate-400 dark:text-slate-500' : 'text-slate-800 dark:text-slate-100'}`}>
                          {act.task}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 mt-1.5">
                          {act.deadline_text && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold font-mono px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950/50 border border-amber-100 dark:border-amber-800 text-amber-700 dark:text-amber-300">
                              <span className="material-symbols-outlined text-[12px]">schedule</span>
                              {act.deadline_text}
                            </span>
                          )}
                          <Link
                            href={`/inbox/${act.email_id}`}
                            className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                          >
                            <span className="material-symbols-outlined text-[12px]">mail</span>
                            View email #{act.email_id}
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          {/* Deadlines */}
          <section className={`${card} flex flex-col overflow-hidden`}>
            <div className="flex items-center gap-2.5 px-5 py-4 border-b border-slate-100 dark:border-slate-800">
              <span className="material-symbols-outlined text-rose-500 text-[20px]">event</span>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">Upcoming deadlines</h2>
              <span className="ml-auto text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-rose-50 dark:bg-rose-950/60 border border-rose-100 dark:border-rose-800 text-rose-600 dark:text-rose-300">
                {filteredDeadlines.length} total
              </span>
            </div>

            <div className="p-4 space-y-4 max-h-[560px] overflow-y-auto">
              {loading ? skeleton : groups.length === 0 ? (
                hasFilterOrQuery
                  ? emptyState('filter_alt_off', 'Nothing matches', 'Try another filter or clear the search box.')
                  : emptyState('event_available', 'No deadlines detected', 'Dates mentioned in your emails, like "by Friday" or "due 15 Oct", will appear here.')
              ) : (
                groups.map((g) => (
                  <div key={g.key} className="space-y-2">
                    <p className={`text-[10px] font-black uppercase tracking-wider px-1 ${g.tone}`}>
                      {g.label} <span className="font-mono opacity-70">({g.items.length})</span>
                    </p>
                    {g.items.map((dl) => {
                      const days = daysUntil(dl.due_date);
                      const overdue = !dl.is_completed && days !== null && days < 0;
                      const soon = !dl.is_completed && days !== null && days >= 0 && days <= 3;
                      return (
                        <div
                          key={dl.id}
                          className={`group flex items-start gap-3 p-3.5 border rounded-xl transition-all ${
                            dl.is_completed
                              ? 'bg-emerald-50/60 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/50'
                              : overdue
                              ? 'bg-rose-50/70 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/60'
                              : 'bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-700/70 hover:border-indigo-300 dark:hover:border-indigo-500'
                          }`}
                        >
                          <button
                            onClick={() => handleToggleDeadline(dl.id)}
                            aria-label={dl.is_completed ? 'Reopen deadline' : 'Mark deadline done'}
                            className={`mt-0.5 flex-shrink-0 transition-colors ${
                              dl.is_completed ? 'text-emerald-500' : overdue ? 'text-rose-400' : 'text-slate-300 dark:text-slate-600 group-hover:text-indigo-400'
                            }`}
                          >
                            <span className="material-symbols-outlined text-[22px]">{dl.is_completed ? 'check_circle' : overdue ? 'event_busy' : 'schedule'}</span>
                          </button>
                          <div className="min-w-0 flex-1">
                            <p className={`text-[13px] font-semibold leading-snug break-words ${dl.is_completed ? 'line-through text-slate-400 dark:text-slate-500' : 'text-slate-800 dark:text-slate-100'}`}>
                              {dl.title}
                            </p>
                            <div className="flex flex-wrap items-center gap-2 mt-1.5">
                              <span className="text-[10px] font-bold font-mono text-slate-500 dark:text-slate-400">{formatDue(dl.due_date)}</span>
                              {!dl.is_completed && days !== null && (
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                                  overdue
                                    ? 'bg-rose-100 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                                    : soon
                                    ? 'bg-amber-50 dark:bg-amber-950/50 border-amber-100 dark:border-amber-800 text-amber-700 dark:text-amber-300'
                                    : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300'
                                }`}>
                                  {relativeLabel(days)}
                                </span>
                              )}
                              <Link
                                href={`/inbox/${dl.email_id}`}
                                className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                              >
                                <span className="material-symbols-outlined text-[12px]">mail</span>
                                View email #{dl.email_id}
                              </Link>
                            </div>
                          </div>
                          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md border flex-shrink-0 ${
                            dl.is_completed
                              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
                              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-100 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                          }`}>
                            {dl.is_completed ? 'DONE' : 'OPEN'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </AppLayout>
  );
}
