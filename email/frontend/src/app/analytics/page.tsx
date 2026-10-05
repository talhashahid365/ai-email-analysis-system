"use client";

import { useCallback, useEffect, useState } from 'react';
import AppLayout from '@/components/AppLayout';
import { apiFetch } from '@/lib/api';
import { DashboardOverview } from '@/types';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { AXIS_TICK, CURSOR_LINE, GRID_PROPS, LEGEND_PROPS, ChartTooltip, gradientDefs } from '@/components/charts';

const SENTIMENT_COLORS: Record<string, string> = {
  Positive: '#10b981', Neutral: '#3b82f6', Negative: '#f97316', Angry: '#ef4444', Urgent: '#a855f7',
};
const PRIORITY_COLORS: Record<string, string> = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#eab308', LOW: '#22c55e' };
const CARD = 'bg-white dark:bg-[#0F172A] border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-sm p-5 min-w-0';

function shortDate(value: string): string {
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatHours(h?: number): string {
  if (!h) return '—';
  if (h < 1) return `${Math.round(h * 60)} min`;
  if (h < 48) return `${h.toFixed(1)} h`;
  return `${(h / 24).toFixed(1)} days`;
}

function Empty({ text }: { text: string }) {
  return <div className="h-48 flex items-center justify-center text-xs text-slate-400 text-center px-6">{text}</div>;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch('/analytics/overview'));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const exportJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), ...data }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'email-analytics.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const categories = Object.entries(data?.category_distribution ?? {}).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  const sentiments = Object.entries(data?.sentiment_distribution ?? {}).map(([name, value]) => ({ name, value }));
  const priorities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    .map((name) => ({ name, value: data?.priority_distribution?.[name] ?? 0 })).filter((p) => p.value > 0);
  const trend = (data?.sentiment_trend ?? []).map((d) => ({ ...d, label: shortDate(d.date) }));
  const hasTrend = trend.some((d) => d.Positive + d.Neutral + d.Negative + d.Angry + d.Urgent > 0);
  const activity = (data?.daily_activity ?? []).map((d) => ({ ...d, label: shortDate(d.date) }));
  const hasActivity = activity.some((d) => d.total > 0);
  const total = data?.total_emails ?? 0;

  const stats = [
    { label: 'Emails received', value: total },
    { label: 'Emails replied to', value: data?.replied_count ?? 0 },
    { label: 'Avg response time', value: formatHours(data?.avg_response_time_hours) },
    { label: 'Urgent emails', value: data?.urgent_emails ?? 0 },
    { label: 'Customer complaints', value: data?.complaint_count ?? data?.customer_emails ?? 0 },
    { label: 'Sales inquiries', value: data?.sales_emails ?? 0 },
    { label: 'Support requests', value: data?.support_emails ?? 0 },
    { label: 'Pending actions', value: data?.pending_actions ?? 0 },
  ];

  return (
    <AppLayout title="Analytics" totalCount={total} urgentCount={data?.urgent_emails ?? 0}>
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-6 space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-extrabold text-slate-900 dark:text-white">Analytics</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Calculated from your own emails and replies.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={load} className="px-3 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">Refresh</button>
            <button onClick={exportJson} disabled={!data} className="px-3 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white">Export JSON</button>
          </div>
        </div>

        {error && <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</div>}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div key={s.label} className={CARD}>
              <div className="text-[11px] font-bold uppercase tracking-wide text-slate-400">{s.label}</div>
              <div className="mt-1 text-2xl font-extrabold text-slate-900 dark:text-white">{loading ? '–' : s.value}</div>
            </div>
          ))}
        </div>

        {!loading && !error && total === 0 ? (
          <div className={`${CARD} text-center py-12 text-sm text-slate-500 dark:text-slate-400`}>
            No analytics yet. Add emails from the dashboard or inbox and the charts will fill in.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <section className={CARD}>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Emails by category</h2>
                {categories.length ? (
                  <div style={{ height: Math.max(220, categories.length * 34) }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={categories} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
                        <CartesianGrid {...GRID_PROPS} />
                        <XAxis type="number" allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                        <YAxis type="category" dataKey="name" width={130} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
                        <Bar dataKey="value" name="Emails" fill="#4f46e5" radius={[0, 8, 8, 0]} barSize={14} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : <Empty text="No analysed emails yet." />}
              </section>

              <section className={CARD}>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Email volume (14 days)</h2>
                {hasActivity ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={activity} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                        {gradientDefs({ received: '#4f46e5', replied: '#10b981' })}
                        <CartesianGrid {...GRID_PROPS} />
                        <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                        <YAxis allowDecimals={false} tick={AXIS_TICK} tickLine={false} axisLine={false} />
                        <Tooltip content={<ChartTooltip />} cursor={CURSOR_LINE} />
                        <Legend {...LEGEND_PROPS} />
                        <Area type="monotone" dataKey="total" name="Received" stroke="#4f46e5" fill="url(#grad-received)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
                        <Area type="monotone" dataKey="replied" name="Replied" stroke="#10b981" fill="url(#grad-replied)" strokeWidth={2.5} dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : <Empty text="No emails received in the last 14 days." />}
              </section>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <section className={`${CARD} xl:col-span-2`}>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Sentiment trend</h2>
                {hasTrend ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trend} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
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
              </section>

              <section className={CARD}>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Priority &amp; sentiment mix</h2>
                {priorities.length || sentiments.length ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={priorities} dataKey="value" nameKey="name" innerRadius={30} outerRadius={55} paddingAngle={3} cornerRadius={4} stroke="none">
                          {priorities.map((p) => <Cell key={p.name} fill={PRIORITY_COLORS[p.name]} />)}
                        </Pie>
                        <Pie data={sentiments} dataKey="value" nameKey="name" innerRadius={65} outerRadius={85} paddingAngle={3} cornerRadius={4} stroke="none">
                          {sentiments.map((s) => <Cell key={s.name} fill={SENTIMENT_COLORS[s.name] ?? '#94a3b8'} />)}
                        </Pie>
                        <Tooltip content={<ChartTooltip />} />
                      </PieChart>
                    </ResponsiveContainer>
                    <p className="text-[11px] text-center text-slate-400 -mt-2">Inner ring: priority · Outer ring: sentiment</p>
                  </div>
                ) : <Empty text="No data yet." />}
              </section>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
