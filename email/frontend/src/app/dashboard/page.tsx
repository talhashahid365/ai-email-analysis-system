"use client";

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import UploadModal from '@/components/UploadModal';
import { apiFetch, getUserName } from '@/lib/api';
import { DashboardOverview } from '@/types';
import {
  Area, AreaChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { AXIS_TICK, CURSOR_LINE, GRID_PROPS, LEGEND_PROPS, ChartTooltip, gradientDefs } from '@/components/charts';

const CATEGORY_COLORS: Record<string, string> = {
  'Sales Inquiry': '#2563eb', 'Customer Complaint': '#dc2626', 'Support Request': '#7c3aed',
  'Meeting Request': '#0891b2', 'Invoice / Payment': '#d97706', 'Job Application': '#059669',
  'General Information': '#64748b', Spam: '#9ca3af', Urgent: '#b91c1c', Other: '#475569',
};
const SENTIMENT_COLORS: Record<string, string> = {
  Positive: '#10b981', Neutral: '#3b82f6', Negative: '#f97316', Angry: '#ef4444', Urgent: '#a855f7',
};
const PRIORITY_STYLE: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
  HIGH: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
  MEDIUM: 'bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300',
  LOW: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
};

function parseUtc(value?: string | null): Date | null {
  if (!value) return null;
  const hasZone = /Z$|[+-]\d{2}:?\d{2}$/.test(value);
  const d = new Date(hasZone ? value : `${value}Z`);
  return isNaN(d.getTime()) ? null : d;
}

function timeAgo(value?: string | null): string {
  const d = parseUtc(value);
  if (!d) return '';
  const mins = Math.max(0, Math.floor((Date.now() - d.getTime()) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

function shortDate(value?: string | null): string {
  const d = parseUtc(value) ?? (value ? new Date(value) : null);
  return d && !isNaN(d.getTime()) ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';
}

function formatHours(h?: number): string {
  if (!h) return '—';
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 48) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

const CARD = 'bg-white dark:bg-[#0F172A] border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-sm';

function Card({ title, icon, action, children, className = '' }: {
  title: string; icon: string; action?: { href: string; label: string }; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={`${CARD} p-5 flex flex-col min-w-0 ${className}`}>
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
          <span className="material-symbols-outlined text-[20px] text-indigo-600 dark:text-indigo-400">{icon}</span>
          {title}
        </h2>
        {action && (
          <Link href={action.href} className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap">
            {action.label} →
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex-1 min-h-[120px] flex items-center justify-center text-center text-xs text-slate-400 dark:text-slate-500 px-4">
      {text}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [userName, setUserName] = useState('');

  useEffect(() => { setUserName((getUserName() || '').split(' ')[0]); }, []);

  const load = useCallback(async () => {
    try {
      setData(await apiFetch('/analytics/overview'));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  const total = data?.total_emails ?? 0;
  const kpis = [
    { label: 'Total Emails', value: total, icon: 'mail', tone: 'text-blue-600 bg-blue-50 dark:bg-blue-950/50 dark:text-blue-400' },
    { label: 'Unread', value: data?.unread_emails ?? 0, icon: 'mark_email_unread', tone: 'text-violet-600 bg-violet-50 dark:bg-violet-950/50 dark:text-violet-400' },
    { label: 'Urgent', value: data?.urgent_emails ?? 0, icon: 'error', tone: 'text-red-600 bg-red-50 dark:bg-red-950/50 dark:text-red-400' },
    { label: 'Need Reply', value: data?.reply_required_emails ?? 0, icon: 'reply_all', tone: 'text-amber-600 bg-amber-50 dark:bg-amber-950/50 dark:text-amber-400' },
    { label: 'Customer Complaints', value: data?.customer_emails ?? 0, icon: 'sentiment_dissatisfied', tone: 'text-rose-600 bg-rose-50 dark:bg-rose-950/50 dark:text-rose-400' },
    { label: 'Sales', value: data?.sales_emails ?? 0, icon: 'trending_up', tone: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 dark:text-emerald-400' },
    { label: 'Support', value: data?.support_emails ?? 0, icon: 'support_agent', tone: 'text-cyan-600 bg-cyan-50 dark:bg-cyan-950/50 dark:text-cyan-400' },
    { label: 'Pending Actions', value: data?.pending_actions ?? 0, icon: 'task_alt', tone: 'text-indigo-600 bg-indigo-50 dark:bg-indigo-950/50 dark:text-indigo-400' },
  ];

  const categories = Object.entries(data?.category_distribution ?? {}).sort((a, b) => b[1] - a[1]);
  const categoryTotal = categories.reduce((n, [, c]) => n + c, 0);
  const activity = (data?.daily_activity ?? []).map((d) => ({ ...d, label: shortDate(d.date) }));
  const hasActivity = activity.some((d) => d.total > 0);
  const sentimentTrend = (data?.sentiment_trend ?? []).map((d) => ({ ...d, label: shortDate(d.date) }));
  const hasSentiment = sentimentTrend.some((d) => d.Positive + d.Neutral + d.Negative + d.Angry + d.Urgent > 0);
  const heat = data?.activity_heatmap;
  const heatMax = heat ? Math.max(0, ...heat.grid.flat()) : 0;
  const sla = data?.sla;
  const slaData = sla ? [
    { name: 'Responded', value: sla.responded, color: '#10b981' },
    { name: 'Pending', value: sla.pending, color: '#3b82f6' },
    { name: 'Overdue', value: sla.overdue, color: '#ef4444' },
  ].filter((s) => s.value > 0) : [];
  const queue = data?.critical_queue ?? [];

  return (
    <AppLayout
      title="Dashboard"
      onOpenUpload={() => setIsUploadOpen(true)}
      urgentCount={data?.urgent_emails ?? 0}
      totalCount={total}
    >
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-6 space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-extrabold text-slate-900 dark:text-white">
              {userName ? `Welcome back, ${userName}` : 'Welcome back'}
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Everything below is calculated from your own emails.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="px-3 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">
              Refresh
            </button>
            <button onClick={() => setIsUploadOpen(true)} className="px-4 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm">
              + Add emails
            </button>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            Couldn&apos;t load your dashboard: {error}
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpis.map((k) => (
            <div key={k.label} className={`${CARD} p-4 flex items-center gap-3`}>
              <span className={`material-symbols-outlined w-10 h-10 rounded-xl flex items-center justify-center text-[22px] ${k.tone}`}>{k.icon}</span>
              <div className="min-w-0">
                <div className="text-2xl font-extrabold text-slate-900 dark:text-white leading-none">{loading ? '–' : k.value}</div>
                <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mt-1 truncate">{k.label}</div>
              </div>
            </div>
          ))}
        </div>

        {!loading && !error && total === 0 ? (
          <div className={`${CARD} p-10 text-center`}>
            <span className="material-symbols-outlined text-[44px] text-indigo-500">inbox</span>
            <h2 className="mt-2 text-lg font-bold text-slate-900 dark:text-white">No emails yet</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Your dashboard is empty because you haven&apos;t added any emails. Upload an .eml file, paste an email, import a
              CSV/JSON file or create one manually. Charts and AI results appear here as soon as the first email is processed.
            </p>
            <button onClick={() => setIsUploadOpen(true)} className="mt-5 px-5 py-2.5 text-sm font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white">
              Add your first email
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <Card title="Email Activity (14 days)" icon="show_chart" className="xl:col-span-2">
                {hasActivity ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={activity} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                        {gradientDefs({ received: '#4f46e5', critical: '#ef4444', replied: '#10b981' })}
                        <CartesianGrid {...GRID_PROPS} />
                        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                        <YAxis allowDecimals={false} domain={[0, (max: number) => Math.max(4, max)]} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                        <Tooltip content={<ChartTooltip />} cursor={CURSOR_LINE} />
                        <Legend {...LEGEND_PROPS} />
                        <Area type="monotone" dataKey="total" name="Received" stroke="#4f46e5" fill="url(#grad-received)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
                        <Area type="monotone" dataKey="critical" name="High / Critical" stroke="#ef4444" fill="url(#grad-critical)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
                        <Area type="monotone" dataKey="replied" name="Replied" stroke="#10b981" fill="url(#grad-replied)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : <Empty text="No emails received in the last 14 days." />}
              </Card>

              <Card title="Category Distribution" icon="category" action={{ href: '/inbox', label: 'View inbox' }}>
                {categories.length ? (
                  <ul className="space-y-3">
                    {categories.map(([name, count]) => {
                      const pct = categoryTotal ? Math.round((count / categoryTotal) * 100) : 0;
                      return (
                        <li key={name}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-slate-700 dark:text-slate-200 truncate pr-2">{name}</span>
                            <span className="font-mono text-slate-500 dark:text-slate-400">{count} ({pct}%)</span>
                          </div>
                          <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: CATEGORY_COLORS[name] ?? '#64748b' }} />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                ) : <Empty text="Categories appear after your emails are analysed." />}
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card title="Busiest Times" icon="calendar_month">
                {heat && heatMax > 0 ? (
                  <div className="overflow-x-auto">
                    <div className="grid gap-1.5 min-w-[280px]" style={{ gridTemplateColumns: `44px repeat(${heat.days.length}, minmax(0, 1fr))` }}>
                      <div />
                      {heat.days.map((d) => <div key={d} className="text-center text-[10px] font-bold text-slate-400">{d}</div>)}
                      {heat.slots.map((slot, si) => (
                        <div key={slot} className="contents">
                          <div className="text-[10px] font-semibold text-slate-400 flex items-center">{slot}</div>
                          {heat.days.map((d, di) => {
                            const v = heat.grid[di]?.[si] ?? 0;
                            return (
                              <div
                                key={`${slot}-${d}`}
                                title={`${d} ${slot}: ${v} email${v === 1 ? '' : 's'}`}
                                className={`h-8 rounded-md ${v === 0 ? 'bg-slate-100 dark:bg-slate-800/70' : ''}`}
                                style={v > 0 ? { backgroundColor: `rgba(79,70,229,${0.2 + 0.8 * (v / heatMax)})` } : undefined}
                              />
                            );
                          })}
                        </div>
                      ))}
                    </div>
                    <p className="mt-3 text-[11px] text-slate-400">Emails received by weekday and time of day (last 90 days).</p>
                  </div>
                ) : <Empty text="Not enough data yet." />}
              </Card>

              <Card title="Sentiment Trend" icon="mood">
                {hasSentiment ? (
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={sentimentTrend} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                        {gradientDefs(SENTIMENT_COLORS, 0.7)}
                        <CartesianGrid {...GRID_PROPS} />
                        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                        <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                        <Tooltip content={<ChartTooltip />} cursor={CURSOR_LINE} />
                        <Legend {...LEGEND_PROPS} />
                        {Object.keys(SENTIMENT_COLORS).map((k) => (
                          <Area key={k} type="monotone" dataKey={k} stackId="s" stroke={SENTIMENT_COLORS[k]} fill={`url(#grad-${k})`} strokeWidth={1.5} />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : <Empty text="Sentiment trend appears once emails are analysed." />}
              </Card>

              <Card title="Response Status" icon="schedule">
                {slaData.length ? (
                  <>
                    <div className="h-44">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={slaData} dataKey="value" nameKey="name" innerRadius={48} outerRadius={72} paddingAngle={3} cornerRadius={4} stroke="none">
                            {slaData.map((s) => <Cell key={s.name} fill={s.color} />)}
                          </Pie>
                          <Tooltip content={<ChartTooltip />} />
                          <Legend {...LEGEND_PROPS} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-2 text-center text-xs text-slate-500 dark:text-slate-400">
                      Average response time: <span className="font-bold text-slate-800 dark:text-slate-100">{formatHours(data?.avg_response_time_hours)}</span>
                    </div>
                  </>
                ) : <Empty text="No replies are pending or sent yet." />}
              </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card title="Critical Queue" icon="local_fire_department" action={{ href: '/inbox', label: 'View all' }}>
                {queue.length ? (
                  <ul className="space-y-3">
                    {queue.map((q) => (
                      <li key={q.id}>
                        <Link href={`/inbox/${q.id}`} className="block rounded-xl border border-slate-200 dark:border-slate-800 p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${PRIORITY_STYLE[q.priority] ?? PRIORITY_STYLE.LOW}`}>{q.priority}</span>
                            <span className="text-[10px] font-mono text-slate-400">{q.confidence}% sentiment confidence</span>
                          </div>
                          <div className="text-sm font-bold text-slate-900 dark:text-white truncate">{q.subject}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 truncate">{q.summary}</div>
                          <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500">
                            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">{q.category}</span>
                            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">{q.sentiment}</span>
                            <span className="ml-auto">{timeAgo(q.received_at)}</span>
                          </div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="No high-priority emails are waiting. 🎉" />}
              </Card>

              <Card title="Upcoming Deadlines" icon="event" action={{ href: '/tasks', label: 'All tasks' }}>
                {data?.upcoming_deadlines?.length ? (
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {data.upcoming_deadlines.map((d) => (
                      <li key={d.id} className="py-2.5 flex items-center justify-between gap-3">
                        <Link href={`/inbox/${d.email_id}`} className="text-sm text-slate-800 dark:text-slate-100 truncate hover:underline">{d.title}</Link>
                        <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">{shortDate(d.due_date)}</span>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="No upcoming deadlines were found in your emails." />}
              </Card>

              <Card title="Pending Actions" icon="checklist" action={{ href: '/tasks', label: 'All tasks' }}>
                {data?.recent_actions?.length ? (
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {data.recent_actions.map((a) => (
                      <li key={a.id} className="py-2.5">
                        <Link href={`/inbox/${a.email_id}`} className="text-sm text-slate-800 dark:text-slate-100 hover:underline line-clamp-2">{a.task}</Link>
                        {a.deadline_text && <div className="text-[11px] text-slate-400 mt-0.5">Due: {a.deadline_text}</div>}
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="No pending actions." />}
              </Card>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <Card title="Recent Emails" icon="inbox" action={{ href: '/inbox', label: 'Open inbox' }} className="xl:col-span-2">
                {data?.recent_emails?.length ? (
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {data.recent_emails.map((e) => (
                      <li key={e.id}>
                        <Link href={`/inbox/${e.id}`} className="flex items-center gap-3 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/40 -mx-2 px-2 rounded-lg">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${e.is_read ? 'bg-transparent' : 'bg-indigo-500'}`} />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className={`text-sm truncate ${e.is_read ? 'font-medium' : 'font-bold'} text-slate-900 dark:text-white`}>{e.sender_name}</span>
                              <span className="text-[10px] text-slate-400 whitespace-nowrap">{timeAgo(e.received_at)}</span>
                            </div>
                            <div className="text-xs text-slate-600 dark:text-slate-300 truncate">{e.subject}</div>
                          </div>
                          <span className="hidden sm:inline text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 whitespace-nowrap">{e.category}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${PRIORITY_STYLE[e.priority] ?? PRIORITY_STYLE.LOW}`}>{e.priority}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="No emails yet." />}
              </Card>

              <Card title="Recent AI Actions" icon="smart_toy">
                {data?.recent_ai_actions?.length ? (
                  <ul className="space-y-3">
                    {data.recent_ai_actions.map((a) => (
                      <li key={a.id} className="flex items-start gap-2.5">
                        <span className={`material-symbols-outlined text-[18px] mt-0.5 ${a.success ? 'text-emerald-500' : 'text-red-500'}`}>{a.success ? 'check_circle' : 'error'}</span>
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-slate-800 dark:text-slate-100 capitalize">
                            {a.operation}{a.fallback_used ? ' (fallback)' : ''} · {a.provider}
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{a.subject || 'Email'} · {timeAgo(a.created_at)}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : <Empty text="AI activity will be listed here." />}
              </Card>
            </div>
          </>
        )}
      </div>

      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} onSuccess={() => { setIsUploadOpen(false); load(); }} />
    </AppLayout>
  );
}
