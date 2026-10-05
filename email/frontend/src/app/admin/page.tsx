"use client";

import { useEffect, useState } from 'react';
import AppLayout from '@/components/AppLayout';
import { apiFetch, getUserRole } from '@/lib/api';
import { fmtDateTime, fmtTime } from '@/lib/time';

type Tab = 'users' | 'processing' | 'usage' | 'categories' | 'settings' | 'ai-logs' | 'errors' | 'audit';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('users');
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [systemSettings, setSystemSettings] = useState<any[]>([]);
  const [aiLogs, setAiLogs] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [processing, setProcessing] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [aiErrors, setAiErrors] = useState<any[]>([]);
  const [opMessage, setOpMessage] = useState('');
  const [opBusy, setOpBusy] = useState(false);
  const isAdmin = getUserRole() === 'admin';
  const [loading, setLoading] = useState(true);

  const [newCatName, setNewCatName] = useState('');
  const [newCatDesc, setNewCatDesc] = useState('');
  const [newCatColor, setNewCatColor] = useState('#4f46e5');
  const [catCreating, setCatCreating] = useState(false);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, catRes, settingsRes, aiRes, auditRes, procRes, usageRes, errRes] = await Promise.all([
        apiFetch('/admin/stats').catch(() => null),
        apiFetch('/admin/users').catch(() => []),
        apiFetch('/admin/categories').catch(() => []),
        apiFetch('/admin/settings').catch(() => []),
        apiFetch('/admin/ai-logs?limit=50').catch(() => []),
        apiFetch('/admin/audit-logs?limit=50').catch(() => []),
        apiFetch('/admin/processing').catch(() => null),
        apiFetch('/admin/usage').catch(() => null),
        apiFetch('/admin/ai-errors?limit=50').catch(() => []),
      ]);
      setStats(statsRes);
      setUsers(usersRes);
      setCategories(catRes);
      setSystemSettings(settingsRes);
      setAiLogs(aiRes);
      setAuditLogs(auditRes);
      setProcessing(procRes);
      setUsage(usageRes);
      setAiErrors(errRes);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAdminData(); }, []);

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await apiFetch(`/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      });
      fetchAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to update role');
    }
  };

  const handleStatusToggle = async (userId: number, currentActive: boolean) => {
    try {
      await apiFetch(`/admin/users/${userId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !currentActive }),
      });
      fetchAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) return;
    setCatCreating(true);
    try {
      await apiFetch('/admin/categories', {
        method: 'POST',
        body: JSON.stringify({ name: newCatName, description: newCatDesc, color: newCatColor }),
      });
      setNewCatName(''); setNewCatDesc('');
      fetchAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to create category');
    } finally {
      setCatCreating(false);
    }
  };

  const handleUpdateSetting = async (key: string, value: string) => {
    try {
      await apiFetch(`/admin/settings/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
      });
    } catch (err: any) {
      alert(err.message || 'Failed to update setting');
    }
  };

  const runProcessingOp = async (path: string, okText: (r: any) => string) => {
    setOpBusy(true);
    setOpMessage('');
    try {
      const r = await apiFetch(path, { method: 'POST' });
      setOpMessage(okText(r));
      await fetchAdminData();
    } catch (err: any) {
      setOpMessage(err.message || 'Operation failed');
    } finally {
      setOpBusy(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: string; count?: number }[] = [
    { id: 'users', label: 'Users & RBAC', icon: 'group', count: users.length },
    { id: 'processing', label: 'Email Processing', icon: 'sync', count: processing?.failed?.length },
    { id: 'usage', label: 'AI Usage', icon: 'monitoring' },
    { id: 'categories', label: 'Categories', icon: 'label', count: categories.length },
    { id: 'settings', label: 'System Config', icon: 'tune' },
    { id: 'ai-logs', label: 'AI Execution', icon: 'memory', count: aiLogs.length },
    { id: 'errors', label: 'Errors', icon: 'error', count: aiErrors.length },
    { id: 'audit', label: 'System Activity', icon: 'history' },
  ];

  return (
    <AppLayout title="Admin Governance">
      <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto w-full" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

        {/* Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Users', value: stats?.total_users ?? users.length ?? 1, icon: 'group', color: 'bg-indigo-600' },
            { label: 'Emails Ingested', value: stats?.total_emails ?? 0, icon: 'inbox', color: 'bg-sky-600' },
            { label: 'AI Analyses', value: stats?.total_ai_analyses ?? 0, icon: 'psychology', color: 'bg-emerald-600' },
            { label: 'AI Engine', value: (stats?.effective_ai_provider ?? 'heuristic').toUpperCase(), icon: 'smart_toy', color: 'bg-violet-600', isText: true },
          ].map((s) => (
            <div key={s.label} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-5 flex items-center gap-4">
              <div className={`${s.color} w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md`}>
                <span className="material-symbols-outlined text-white text-[18px]">{s.icon}</span>
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{s.label}</p>
                <p className={`font-black mt-0.5 ${(s as any).isText ? 'text-sm text-violet-600 dark:text-violet-400' : 'text-xl text-slate-900 dark:text-white'}`}>{loading ? '—' : s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Tab Navigation */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs overflow-hidden">
          <div className="flex overflow-x-auto border-b border-slate-100 dark:border-slate-800 px-2 pt-2 bg-slate-50/50 dark:bg-slate-900/50">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex shrink-0 whitespace-nowrap items-center gap-1.5 px-4 py-2.5 text-[12px] font-bold rounded-t-xl border-b-2 transition-all -mb-px mr-1 ${
                  activeTab === t.id
                    ? 'border-indigo-600 dark:border-indigo-400 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60'
                    : 'border-transparent text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100/50 dark:hover:bg-slate-800/50'
                }`}
              >
                <span className="material-symbols-outlined text-[15px]">{t.icon}</span>
                {t.label}
                {t.count !== undefined && (
                  <span className="ml-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">{t.count}</span>
                )}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* USERS TAB */}
            {activeTab === 'users' && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">shield</span>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">User Management & Multi-Tenant RBAC</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['User', 'Email', 'Role', 'Status', 'Actions'].map((h) => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center text-xs font-bold">
                                {u.full_name?.[0] ?? 'U'}
                              </div>
                              <span className="text-sm font-bold text-slate-900 dark:text-white">{u.full_name}</span>
                            </div>
                          </td>
                          <td className="p-3 text-xs text-slate-500 dark:text-slate-400 font-mono">{u.email}</td>
                          <td className="p-3">
                            <select
                              value={u.role}
                              onChange={(e) => handleRoleChange(u.id, e.target.value)}
                              className="text-[11px] font-bold bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            >
                              <option value="user" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">USER</option>
                              <option value="manager" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">MANAGER</option>
                              <option value="admin" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">ADMIN</option>
                            </select>
                          </td>
                          <td className="p-3">
                            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${u.is_active ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-950/60 border-rose-100 dark:border-rose-800 text-rose-700 dark:text-rose-300'}`}>
                              {u.is_active ? 'ACTIVE' : 'SUSPENDED'}
                            </span>
                          </td>
                          <td className="p-3">
                            <button
                              onClick={() => handleStatusToggle(u.id, u.is_active)}
                              className={`text-[11px] font-bold px-3 py-1 rounded-lg border transition-colors ${
                                u.is_active
                                  ? 'bg-rose-50 dark:bg-rose-950/60 border-rose-100 dark:border-rose-800 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/60'
                                  : 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/60'
                              }`}
                            >
                              {u.is_active ? 'Suspend' : 'Activate'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* CATEGORIES TAB */}
            {activeTab === 'categories' && (
              <div className="space-y-5">
                <form onSubmit={handleCreateCategory} className="flex flex-wrap items-center gap-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-3">
                  <input
                    type="text"
                    placeholder="Category Name"
                    value={newCatName}
                    onChange={(e) => setNewCatName(e.target.value)}
                    className="text-xs border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 flex-1 focus:ring-2 focus:ring-indigo-500 outline-none bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Short description"
                    value={newCatDesc}
                    onChange={(e) => setNewCatDesc(e.target.value)}
                    className="text-xs border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 flex-1 focus:ring-2 focus:ring-indigo-500 outline-none bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                  <input type="color" value={newCatColor} onChange={(e) => setNewCatColor(e.target.value)}
                    className="h-9 w-12 rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer p-0.5 bg-white dark:bg-slate-800" />
                  <button type="submit" disabled={catCreating}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl flex items-center gap-1.5 disabled:opacity-50 shadow-md">
                    <span className="material-symbols-outlined text-[15px]">{catCreating ? 'hourglass_empty' : 'add'}</span>
                    Add Category
                  </button>
                </form>

                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['Color', 'Name', 'Description', 'Type'].map(h => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                      {categories.map((cat) => (
                        <tr key={cat.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50">
                          <td className="p-3">
                            <div className="w-5 h-5 rounded-full border-2 border-white dark:border-slate-800 shadow" style={{ backgroundColor: cat.color }} />
                          </td>
                          <td className="p-3 text-sm font-bold text-slate-900 dark:text-white">{cat.name}</td>
                          <td className="p-3 text-xs text-slate-500 dark:text-slate-400">{cat.description || '—'}</td>
                          <td className="p-3">
                            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${cat.is_system ? 'bg-violet-50 dark:bg-violet-950/60 border-violet-100 dark:border-violet-800 text-violet-700 dark:text-violet-300' : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'}`}>
                              {cat.is_system ? 'SYSTEM' : 'CUSTOM'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* SETTINGS TAB */}
            {activeTab === 'settings' && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">tune</span>
                  System & AI Engine Configuration
                </h3>
                {systemSettings.map((st) => (
                  <div key={st.key} className="p-4 bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="text-xs font-bold text-slate-900 dark:text-white font-mono uppercase">{st.key}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">{st.description || 'System parameter'}</p>
                    </div>
                    <input
                      type="text"
                      defaultValue={st.value}
                      onBlur={(e) => handleUpdateSetting(st.key, e.target.value)}
                      className="text-xs border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 font-mono w-48 text-slate-800 dark:text-white bg-white dark:bg-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                  </div>
                ))}
              </div>
            )}

            {/* AI LOGS TAB */}
            {activeTab === 'ai-logs' && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">memory</span>
                  AI Engine Diagnostics & Execution Logs
                </h3>
                <div className="overflow-x-auto max-h-[480px]">
                  <table className="w-full text-left">
                    <thead className="sticky top-0 bg-white dark:bg-slate-900">
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['Timestamp', 'Task', 'Provider', 'Latency', 'Status'].map(h => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono text-xs">
                      {aiLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50">
                          <td className="p-3 text-slate-400">{fmtTime(log.created_at)}</td>
                          <td className="p-3 font-bold text-slate-800 dark:text-slate-200">{log.operation}</td>
                          <td className="p-3 text-violet-600 dark:text-violet-400">{log.provider}</td>
                          <td className="p-3 text-slate-500 dark:text-slate-400">{log.latency_ms}ms</td>
                          <td className="p-3">
                            <span className={`flex items-center gap-1 text-[10px] font-bold ${log.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                              <span className="material-symbols-outlined text-[14px]">{log.success ? 'check_circle' : 'cancel'}</span>
                              {log.success ? 'SUCCESS' : 'FAILED'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {aiLogs.length === 0 && <p className="text-center py-8 text-xs text-slate-400">No AI logs found.</p>}
                </div>
              </div>
            )}

            {/* PROCESSING TAB */}
            {activeTab === 'processing' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">sync</span>
                    Email Processing Queue
                  </h3>
                  {isAdmin && (
                    <button
                      disabled={opBusy || !(processing?.failed?.length)}
                      onClick={() => runProcessingOp('/admin/emails/retry-failed', (r) => `Re-queued ${r.queued} failed email(s).`)}
                      className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-bold"
                    >
                      Retry all failed
                    </button>
                  )}
                </div>
                {opMessage && <p className="text-xs text-slate-600 dark:text-slate-300">{opMessage}</p>}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {['queued', 'processing', 'completed', 'failed'].map((k) => (
                    <div key={k} className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{k}</p>
                      <p className="text-xl font-black text-slate-900 dark:text-white">{processing?.by_status?.[k] ?? 0}</p>
                    </div>
                  ))}
                </div>
                <div className="overflow-x-auto max-h-[400px]">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['Email', 'User', 'Retries', 'Error', ''].map((h) => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
                      {(processing?.failed ?? []).map((f: any) => (
                        <tr key={f.id}>
                          <td className="p-3 font-mono">#{f.id}</td>
                          <td className="p-3 font-mono">{f.user_id}</td>
                          <td className="p-3">{f.retry_count}</td>
                          <td className="p-3 text-rose-600 dark:text-rose-400 max-w-md truncate" title={f.processing_error || ''}>{f.processing_error || 'Unknown error'}</td>
                          <td className="p-3 text-right">
                            {isAdmin && (
                              <button
                                disabled={opBusy}
                                onClick={() => runProcessingOp(`/admin/emails/${f.id}/reprocess`, () => `Re-queued email #${f.id}.`)}
                                className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 text-[11px] font-bold hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40"
                              >
                                Reprocess
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!(processing?.failed?.length) && <p className="text-center py-8 text-xs text-slate-400">No failed emails.</p>}
                </div>
              </div>
            )}

            {/* AI USAGE TAB */}
            {activeTab === 'usage' && (
              <div className="space-y-5">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">monitoring</span>
                  AI Usage Statistics
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Total calls', value: usage?.total_calls ?? 0 },
                    { label: 'Last 24h', value: usage?.calls_last_24h ?? 0 },
                    { label: 'Failed calls', value: usage?.failed_calls ?? 0 },
                    { label: 'Error rate', value: `${((usage?.error_rate ?? 0) * 100).toFixed(1)}%` },
                  ].map((c) => (
                    <div key={c.label} className="rounded-xl border border-slate-200 dark:border-slate-800 p-3">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{c.label}</p>
                      <p className="text-xl font-black text-slate-900 dark:text-white">{c.value}</p>
                    </div>
                  ))}
                </div>
                {[{ title: 'By operation', rows: usage?.by_operation }, { title: 'By provider', rows: usage?.by_provider }].map((tbl) => (
                  <div key={tbl.title} className="overflow-x-auto">
                    <p className="text-xs font-bold text-slate-500 mb-2">{tbl.title}</p>
                    <table className="w-full text-left">
                      <thead>
                        <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                          {['Name', 'Calls', 'Failures', 'Fallbacks', 'Avg latency'].map((h) => (
                            <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs font-mono">
                        {(tbl.rows ?? []).map((r: any) => (
                          <tr key={r.name}>
                            <td className="p-3 font-bold">{r.name}</td>
                            <td className="p-3">{r.calls}</td>
                            <td className="p-3">{r.failures}</td>
                            <td className="p-3">{r.fallbacks}</td>
                            <td className="p-3">{r.avg_latency_ms}ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!(tbl.rows?.length) && <p className="text-center py-4 text-xs text-slate-400">No AI calls recorded yet.</p>}
                  </div>
                ))}
              </div>
            )}

            {/* ERRORS TAB */}
            {activeTab === 'errors' && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-rose-600 dark:text-rose-400 text-[18px]">error</span>
                  AI Errors
                </h3>
                <div className="overflow-x-auto max-h-[480px]">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['Timestamp', 'Task', 'Provider', 'Fallback', 'Error'].map((h) => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs font-mono">
                      {aiErrors.map((e) => (
                        <tr key={e.id}>
                          <td className="p-3 text-slate-400">{fmtDateTime(e.created_at)}</td>
                          <td className="p-3 font-bold">{e.operation}</td>
                          <td className="p-3 text-violet-600 dark:text-violet-400">{e.provider}</td>
                          <td className="p-3">{e.fallback_used ? 'yes' : 'no'}</td>
                          <td className="p-3 text-rose-600 dark:text-rose-400 max-w-md truncate" title={e.error || ''}>{e.error || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {aiErrors.length === 0 && <p className="text-center py-8 text-xs text-slate-400">No AI errors recorded.</p>}
                </div>
              </div>
            )}

            {/* AUDIT TAB */}
            {activeTab === 'audit' && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[18px]">history</span>
                  System Action & Audit Trail
                </h3>
                <div className="overflow-x-auto max-h-[480px]">
                  <table className="w-full text-left">
                    <thead className="sticky top-0 bg-white dark:bg-slate-900">
                      <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800">
                        {['Timestamp', 'Action', 'Resource', 'IP Address'].map(h => (
                          <th key={h} className="p-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs">
                      {auditLogs.map((a) => (
                        <tr key={a.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50">
                          <td className="p-3 text-slate-400 font-mono">{fmtDateTime(a.timestamp)}</td>
                          <td className="p-3 font-bold text-slate-900 dark:text-white">{a.action}</td>
                          <td className="p-3 text-slate-500 dark:text-slate-400">{a.resource}</td>
                          <td className="p-3 font-mono text-slate-400">{a.ip_address || '127.0.0.1'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {auditLogs.length === 0 && <p className="text-center py-8 text-xs text-slate-400">No audit logs found.</p>}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
