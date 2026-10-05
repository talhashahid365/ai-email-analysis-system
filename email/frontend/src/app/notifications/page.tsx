'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import { apiFetch } from '@/lib/api';
import { fmtDateTime } from '@/lib/time';

const TYPE_CONFIG: Record<string, { icon: string; color: string }> = {
  urgent_email: { icon: 'crisis_alert', color: 'text-rose-600 dark:text-rose-400' },
  customer_complaint: { icon: 'sentiment_dissatisfied', color: 'text-amber-600 dark:text-amber-400' },
  reply_required: { icon: 'reply', color: 'text-sky-600 dark:text-sky-400' },
  upcoming_deadline: { icon: 'schedule', color: 'text-amber-500 dark:text-amber-400' },
  action_item: { icon: 'checklist', color: 'text-indigo-600 dark:text-indigo-400' },
  ai_completed: { icon: 'smart_toy', color: 'text-emerald-600 dark:text-emerald-400' },
  default: { icon: 'notifications', color: 'text-slate-500 dark:text-slate-400' },
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [preferences, setPreferences] = useState<any>({});
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [activeTab, setActiveTab] = useState<'alerts' | 'preferences'>('alerts');

  useEffect(() => {
    fetchNotifications();
    fetchPreferences();
  }, [unreadOnly]);

  const fetchNotifications = async () => {
    try {
      const data = await apiFetch(`/notifications?unread_only=${unreadOnly}`);
      setNotifications(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPreferences = async () => {
    try {
      const data = await apiFetch('/notifications/preferences');
      setPreferences(data);
    } catch (err) { console.error(err); }
  };

  const markAsRead = async (id: number) => {
    try {
      await apiFetch(`/notifications/${id}/read`, { method: 'PATCH' });
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) { console.error(err); }
  };

  const markAllRead = async () => {
    try {
      await apiFetch('/notifications/read-all', { method: 'POST' });
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) { console.error(err); }
  };

  const handlePrefToggle = (field: string) => {
    setPreferences({ ...preferences, [field]: !preferences[field] });
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const updated = await apiFetch('/notifications/preferences', {
        method: 'PUT',
        body: JSON.stringify(preferences),
      });
      setPreferences(updated);
    } catch (err) {
      console.error('Failed to save preferences');
    } finally {
      setSavingPrefs(false);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <AppLayout title="Notifications">
      <div className="p-4 md:p-6 space-y-6 max-w-5xl mx-auto w-full" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

        {/* Page Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white">Notifications & Alert Preferences</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">AI-triggered alerts and configurable notification rules</p>
          </div>
          <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-1 shadow-xs">
            {[
              { id: 'alerts' as const, label: 'Alert History', icon: 'notifications_active' },
              { id: 'preferences' as const, label: 'Preferences', icon: 'tune' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  activeTab === t.id
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">{t.icon}</span>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* ALERTS TAB */}
        {activeTab === 'alerts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs px-5 py-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={unreadOnly}
                  onChange={(e) => setUnreadOnly(e.target.checked)}
                  className="rounded border-slate-300 dark:border-slate-700 text-indigo-600 focus:ring-indigo-500"
                />
                Show Unread Only
                {unreadCount > 0 && (
                  <span className="ml-1 text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400">{unreadCount} unread</span>
                )}
              </label>
              <button
                onClick={markAllRead}
                className="flex items-center gap-1.5 text-xs font-bold text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">done_all</span>
                Mark All Read
              </button>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-16 text-slate-400">
                <span className="material-symbols-outlined text-[40px] animate-spin text-indigo-500">progress_activity</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-slate-400">
                <span className="material-symbols-outlined text-[56px] text-slate-300 dark:text-slate-700">notifications_off</span>
                <p className="text-sm mt-3 font-bold text-slate-700 dark:text-slate-300">No notifications found</p>
                <p className="text-xs mt-1 text-slate-400">You're all caught up!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {notifications.map((n) => {
                  const tc = TYPE_CONFIG[n.type] ?? TYPE_CONFIG.default;
                  return (
                    <div
                      key={n.id}
                      className={`bg-white dark:bg-slate-900 border rounded-2xl shadow-xs p-4 flex items-start justify-between gap-4 transition-all ${
                        n.is_read
                          ? 'border-slate-200 dark:border-slate-800/80 opacity-75'
                          : 'border-indigo-200 dark:border-indigo-800/80 ring-1 ring-indigo-100 dark:ring-indigo-950/60'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${n.is_read ? 'bg-slate-100 dark:bg-slate-800' : 'bg-indigo-50 dark:bg-indigo-950/60'}`}>
                          <span className={`material-symbols-outlined text-[18px] ${tc.color}`}>{tc.icon}</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-bold text-slate-900 dark:text-white">{n.title}</span>
                            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                              {n.type.replace('_', ' ')}
                            </span>
                            {!n.is_read && <span className="w-2 h-2 rounded-full bg-indigo-500" />}
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">{n.message}</p>
                          <p className="text-[10px] text-slate-400 font-mono mt-1">{fmtDateTime(n.created_at)}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 flex-shrink-0">
                        {n.email_id && (
                          <Link
                            href={`/inbox?id=${n.email_id}`}
                            className="px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 rounded-xl text-xs font-bold flex items-center gap-1 transition-all"
                          >
                            <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                            View
                          </Link>
                        )}

                        {!n.is_read && (
                          <button
                            onClick={() => markAsRead(n.id)}
                            className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl text-xs font-bold flex items-center gap-1 transition-all"
                          >
                            <span className="material-symbols-outlined text-[14px]">check</span>
                            Read
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* PREFERENCES TAB */}
        {activeTab === 'preferences' && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-6 space-y-5">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">tune</span>
                Notification Alert Preferences
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Configure which email triggers send push or email alerts</p>
            </div>

            <div className="space-y-3 divide-y divide-slate-100 dark:divide-slate-800">
              {[
                { field: 'notify_urgent', label: 'Urgent Emails & Critical Incidents', desc: 'Alert when AI flags high or critical priority' },
                { field: 'notify_complaints', label: 'Customer Complaints & Disputes', desc: 'Alert when negative sentiment or complaint is detected' },
                { field: 'notify_deadlines', label: 'Upcoming Deadlines & Actions', desc: 'Alert 24-48h before extracted deadlines' },
                { field: 'notify_replies', label: 'Smart Reply Required', desc: 'Alert when an email strictly requires a reply' },
                { field: 'email_digest', label: 'Daily Executive Digest (Email)', desc: 'Receive a daily email summary of top inbox intelligence' },
              ].map((pref) => (
                <div key={pref.field} className="pt-3 first:pt-0 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-900 dark:text-white">{pref.label}</p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">{pref.desc}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!preferences[pref.field]}
                      onChange={() => handlePrefToggle(pref.field)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-slate-600 peer-checked:bg-indigo-600" />
                  </label>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={savePreferences}
                disabled={savingPrefs}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {savingPrefs ? (
                  <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                ) : (
                  <span className="material-symbols-outlined text-[16px]">save</span>
                )}
                <span>{savingPrefs ? 'Saving...' : 'Save Preferences'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
