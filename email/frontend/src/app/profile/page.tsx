'use client';

import { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { apiFetch } from '@/lib/api';
import { fmtDate } from '@/lib/time';

export default function UserProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [fullName, setFullName] = useState('');
  const [company, setCompany] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const data = await apiFetch('/auth/me');
      setProfile(data);
      setFullName(data.full_name || '');
      setCompany(data.company || '');
      setJobTitle(data.job_title || '');
    } catch (err: any) {
      setError(err.message || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const updated = await apiFetch('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ full_name: fullName, company, job_title: jobTitle }),
      });
      setProfile(updated);
      setMessage('Profile updated successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const initials = profile?.full_name
    ? profile.full_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  return (
    <AppLayout title="Profile">
      <div className="p-4 md:p-6 space-y-6 max-w-4xl mx-auto w-full" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

        {/* Profile Hero */}
        <div className="relative bg-gradient-to-r from-indigo-700 via-indigo-600 to-violet-600 dark:from-indigo-900 dark:via-indigo-800 dark:to-violet-900 rounded-2xl p-6 text-white shadow-lg overflow-hidden border border-indigo-500/30">
          <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 80% 50%, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
          <div className="relative flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-white/20 border-2 border-white/30 flex items-center justify-center text-2xl font-black text-white flex-shrink-0">
              {initials}
            </div>
            <div>
              <h2 className="text-xl font-black">{profile?.full_name || 'Loading...'}</h2>
              <p className="text-indigo-200 text-sm">{profile?.email}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-white/20 border border-white/30 text-white capitalize">
                  {profile?.role ?? 'user'}
                </span>
                <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${profile?.is_active ? 'bg-emerald-400/20 border-emerald-300/30 text-emerald-200' : 'bg-rose-400/20 border-rose-300/30 text-rose-200'}`}>
                  {profile?.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
                {profile?.is_verified && (
                  <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-sky-400/20 border border-sky-300/30 text-sky-200">VERIFIED</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Account Info Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'Member Since', value: profile?.created_at ? fmtDate(profile.created_at) : 'N/A', icon: 'calendar_today' },
            { label: 'Last Login', value: profile?.last_login ? fmtDate(profile.last_login) : 'N/A', icon: 'login' },
            { label: 'Emails Owned', value: profile?.email_count ?? '—', icon: 'inbox' },
          ].map((s) => (
            <div key={s.label} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-4 flex items-center gap-3">
              <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">{s.icon}</span>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{s.label}</p>
                <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{loading ? '—' : s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Edit Form */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-6 space-y-5">
          <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
            <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">manage_accounts</span>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Edit Profile Details</h3>
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-100 dark:border-rose-800 text-rose-700 dark:text-rose-300 p-3 rounded-xl text-xs font-semibold">
              <span className="material-symbols-outlined text-[16px]">error</span>
              {error}
            </div>
          )}
          {message && (
            <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 p-3 rounded-xl text-xs font-semibold">
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              {message}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-300 dark:text-slate-600">
              <span className="material-symbols-outlined text-[48px] animate-spin text-indigo-500">progress_activity</span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Read-only fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Email Address</label>
                  <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-500 dark:text-slate-400 font-mono">{profile?.email}</div>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">System Role</label>
                  <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-500 dark:text-slate-400 capitalize">{profile?.role}</div>
                </div>
              </div>

              {/* Editable fields */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Full Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
                  placeholder="Your full name"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Company</label>
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
                    placeholder="e.g. Enterprise IO"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Job Title</label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
                    placeholder="e.g. VP of Operations"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm py-2.5 px-6 rounded-xl transition-colors disabled:opacity-50 shadow-md"
                >
                  <span className="material-symbols-outlined text-[16px]">{saving ? 'hourglass_empty' : 'save'}</span>
                  {saving ? 'Saving...' : 'Save Profile Changes'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Security Section */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4">
            <span className="material-symbols-outlined text-indigo-600 dark:text-indigo-400 text-[20px]">security</span>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">Security & Access</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-xl flex items-center gap-3">
              <span className="material-symbols-outlined text-emerald-500 text-[20px]">verified_user</span>
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-white">Email Verification</p>
                <p className="text-[11px] text-slate-400">{profile?.is_verified ? 'Account verified' : 'Not verified'}</p>
              </div>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-xl flex items-center gap-3">
              <span className="material-symbols-outlined text-indigo-500 text-[20px]">lock</span>
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-white">Password</p>
                <p className="text-[11px] text-slate-400">Use "Forgot Password" to reset</p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </AppLayout>
  );
}
