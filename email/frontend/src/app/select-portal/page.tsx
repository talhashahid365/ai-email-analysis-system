"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiFetch, getAuthToken, getRoleHomePage, getUserRole, setAuthToken, setUserName, setUserRole } from '@/lib/api';
import MailNexaLogo from '@/components/MailNexaLogo';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    const role = getUserRole();
    if (token && role) router.replace(getRoleHomePage(role));
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), password }),
      });
      setAuthToken(data.access_token);
      const profile = await apiFetch('/auth/me');
      setUserRole(profile.role || 'user');
      setUserName(profile.full_name || 'User');
      router.replace(getRoleHomePage(profile.role || 'user'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed. Please check your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", background: 'radial-gradient(ellipse at 50% 20%, #110d38 0%, #08061a 55%, #020208 100%)' }}
    >
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center text-center mb-6">
          <MailNexaLogo size="xl" />
          <h1 className="mt-4 text-3xl font-black tracking-tight text-white">
            MailNexa<span className="text-indigo-400"> AI</span>
          </h1>
          <p className="mt-1 text-xs font-bold tracking-[0.2em] uppercase text-indigo-300/70">Intelligent Email Command Center</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-3xl border border-indigo-500/30 bg-[#0d0f2e]/80 backdrop-blur-xl p-6 sm:p-8 space-y-4 shadow-[0_0_40px_rgba(99,102,241,0.2)]">
          <h2 className="text-lg font-extrabold text-white">Sign in</h2>

          {error && (
            <div role="alert" className="rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-semibold px-3 py-2.5">
              {error}
            </div>
          )}

          <label className="block">
            <span className="text-xs font-semibold text-slate-300">Email</span>
            <input
              type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="mt-1 w-full px-3 py-2.5 rounded-xl bg-[#141845]/80 border border-indigo-500/30 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold text-slate-300">Password</span>
            <div className="relative mt-1">
              <input
                type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="Your password"
                className="w-full px-3 py-2.5 pr-16 rounded-xl bg-[#141845]/80 border border-indigo-500/30 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-400"
              />
              <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-semibold text-indigo-300 hover:text-white">
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </label>

          <button
            type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-60 text-white font-bold text-sm shadow-lg shadow-indigo-600/30 transition-all"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="flex items-center justify-between text-xs font-semibold text-indigo-300/90 pt-2 border-t border-indigo-900/40">
            <Link href="/forgot-password" className="hover:underline">Forgot password?</Link>
            <Link href="/signup" className="hover:underline">Create an account</Link>
          </div>
        </form>

        <p className="mt-6 text-center text-[11px] text-slate-500">MailNexa AI © 2026</p>
      </div>
    </div>
  );
}
