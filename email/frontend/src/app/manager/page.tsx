"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import { apiFetch, getUserRole, getUserName } from '@/lib/api';

export default function ManagerPage() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [teamEmails, setTeamEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const userName = getUserName();

  useEffect(() => {
    const role = getUserRole();
    if (role === 'admin') { router.replace('/admin'); return; }
    if (role === 'user') { router.replace('/dashboard'); return; }
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [overview, emails] = await Promise.all([
        apiFetch('/analytics/overview').catch(() => null),
        apiFetch('/emails?limit=10&priority=HIGH').catch(() => []),
      ]);
      setData(overview);
      setTeamEmails(Array.isArray(emails) ? emails : emails?.emails || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout title="Manager Overview">
      <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto w-full" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

        {/* Header Title Section */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white">Manager Portal & Team Intelligence</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">High-level overview of team email streams and critical action items</p>
          </div>
          <span className="text-[10px] font-bold font-mono px-3 py-1 rounded-full bg-violet-50 dark:bg-violet-950/60 border border-violet-100 dark:border-violet-800 text-violet-700 dark:text-violet-300 flex items-center gap-1.5 shadow-xs">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            MANAGER ROLE ACTIVE
          </span>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Total Emails', value: data?.total_emails ?? 0, icon: 'inbox', color: 'bg-violet-600' },
            { label: 'Urgent (P0)', value: data?.urgent_emails ?? 0, icon: 'crisis_alert', color: 'bg-rose-600' },
            { label: 'Reply Pending', value: data?.reply_required_emails ?? 0, icon: 'reply_all', color: 'bg-amber-500' },
            { label: 'Pending Actions', value: data?.pending_actions ?? 0, icon: 'task_alt', color: 'bg-emerald-600' },
          ].map((k) => (
            <div key={k.label} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-5 flex items-center gap-4">
              <div className={`${k.color} w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md`}>
                <span className="material-symbols-outlined text-white text-[20px]">{k.icon}</span>
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{k.label}</p>
                <p className="text-2xl font-black text-slate-900 dark:text-white">{loading ? '—' : k.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Permission Notice */}
        <div className="bg-violet-50 dark:bg-violet-950/40 border border-violet-100 dark:border-violet-800/80 rounded-2xl p-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-violet-600 dark:text-violet-400 text-[20px] mt-0.5">info</span>
          <div>
            <p className="text-sm font-bold text-violet-900 dark:text-violet-200">Manager Access Level</p>
            <p className="text-xs text-violet-700 dark:text-violet-300 mt-0.5">
              You have read access to team email analytics and can manage tasks. Role upgrades are granted by your Admin in the Admin Portal.
              Contact your administrator to request additional permissions.
            </p>
          </div>
        </div>

        {/* Category Distribution */}
        {data?.category_distribution && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-5">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-violet-600 dark:text-violet-400 text-[20px]">donut_small</span>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">Team Email Category Breakdown</h3>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {Object.entries(data.category_distribution).map(([cat, count]) => (
                <div key={cat} className="p-3 bg-violet-50/50 dark:bg-slate-800/60 border border-violet-100 dark:border-slate-700 rounded-xl text-center">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide truncate">{cat}</p>
                  <p className="text-xl font-black text-slate-900 dark:text-white mt-1">{count as number}</p>
                  <p className="text-[10px] text-slate-400">emails</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Urgent Emails Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs">
          <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-rose-500 text-[20px]">local_fire_department</span>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">High-Priority Emails Requiring Attention</h3>
            </div>
            <Link href="/inbox" className="text-[11px] font-bold text-violet-600 dark:text-violet-400 hover:underline flex items-center gap-1">
              View Inbox <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
          </div>
          <div className="p-4 space-y-2">
            {teamEmails.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                <span className="material-symbols-outlined text-[40px] text-slate-300 dark:text-slate-700">check_circle</span>
                <p className="text-xs mt-2 font-bold text-slate-600 dark:text-slate-400">No urgent emails pending</p>
              </div>
            ) : (
              teamEmails.slice(0, 8).map((email: any) => (
                <Link
                  key={email.id}
                  href={`/inbox?id=${email.id}`}
                  className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/60 hover:bg-violet-50 dark:hover:bg-violet-950/40 border border-slate-100 dark:border-slate-800 hover:border-violet-100 dark:hover:border-violet-800 rounded-xl transition-all"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold text-slate-900 dark:text-white">{email.sender_name || email.sender_email}</span>
                      <span className="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-rose-50 dark:bg-rose-950/60 border border-rose-100 dark:border-rose-800 text-rose-700 dark:text-rose-300">{email.priority}</span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">{email.subject}</p>
                  </div>
                  <span className="material-symbols-outlined text-slate-400 text-[16px] ml-2 flex-shrink-0">chevron_right</span>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { href: '/analytics', label: 'View Full Analytics', icon: 'analytics', desc: 'Category & sentiment reports', color: 'bg-violet-600' },
            { href: '/tasks', label: 'Manage Tasks', icon: 'checklist', desc: 'Review & complete action items', color: 'bg-emerald-600' },
            { href: '/assistant', label: 'AI Copilot', icon: 'smart_toy', desc: 'Ask AI about team emails', color: 'bg-sky-600' },
          ].map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-5 hover:border-violet-300 dark:hover:border-violet-700 hover:shadow-md transition-all flex items-center gap-4"
            >
              <div className={`${card.color} w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md`}>
                <span className="material-symbols-outlined text-white text-[18px]">{card.icon}</span>
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-white">{card.label}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">{card.desc}</p>
              </div>
            </Link>
          ))}
        </div>

      </div>
    </AppLayout>
  );
}
