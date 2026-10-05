"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { clearAuthToken, getUserRole, getUserName } from '@/lib/api';

interface HeaderProps {
  title?: string;
  onSearchChange?: (val: string) => void;
  searchValue?: string;
  onMenuToggle?: () => void;
}

export default function Header({ title = 'Dashboard', onSearchChange, searchValue = '', onMenuToggle }: HeaderProps) {
  const router = useRouter();
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [role, setRole] = useState<string>('user');
  const [userName, setUserNameState] = useState<string>('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
    setRole(getUserRole() || 'user');
    setUserNameState(getUserName() || '');
    setMounted(true);
  }, []);

  const toggleDarkMode = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('mailnexa_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('mailnexa_theme', 'light');
    }
  };

  const roleColor = role === 'admin'
    ? 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950/60 dark:border-indigo-800 dark:text-indigo-300'
    : role === 'manager'
    ? 'bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-950/60 dark:border-violet-800 dark:text-violet-300'
    : 'bg-sky-50 border-sky-200 text-sky-700 dark:bg-sky-950/60 dark:border-sky-800 dark:text-sky-300';

  const avatarBg = role === 'admin' ? 'bg-indigo-600' : role === 'manager' ? 'bg-violet-600' : 'bg-sky-600';
  const roleLabel = role === 'admin' ? 'Admin' : role === 'manager' ? 'Manager' : 'User';
  const avatarInitial = mounted && userName ? userName[0].toUpperCase() : '?';
  const displayName = mounted && userName ? userName : 'User';

  const handleLogout = () => {
    clearAuthToken();
    router.replace('/select-portal');
  };

  return (
    <header className="fixed top-0 left-0 lg:left-64 right-0 h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 z-40 flex items-center justify-between px-4 md:px-6 shadow-xs transition-colors duration-200">
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        {/* Hamburger menu for mobile */}
        {(
          <button
            onClick={() => (onMenuToggle ? onMenuToggle() : window.dispatchEvent(new Event('mailnexa:toggle-sidebar')))}
            className="lg:hidden p-1.5 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Open navigation menu"
          >
            <span className="material-symbols-outlined text-[24px]">menu</span>
          </button>
        )}

        {/* Engine badge */}
        <div className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${roleColor}`}>
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-bold uppercase tracking-wider">MailNexa v4.8 — {roleLabel}</span>
        </div>

        {onSearchChange && (
          <div className="flex items-center flex-1 gap-2.5 px-3 py-1.5 bg-slate-100/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-400 focus-within:border-indigo-500 dark:focus-within:border-indigo-400 focus-within:bg-white dark:focus-within:bg-slate-900 transition-all">
            <span className="material-symbols-outlined text-[18px]">search</span>
            <input
              type="text"
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search emails, tasks, queries..."
              className="bg-transparent text-xs text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none w-full"
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        {/* Dark / Light Mode Toggle Switch */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all flex items-center justify-center"
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          <span className="material-symbols-outlined text-[20px]">
            {isDark ? 'light_mode' : 'dark_mode'}
          </span>
        </button>

        {/* Notifications */}
        <Link href="/notifications" className="relative p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <span className="material-symbols-outlined text-[21px]">notifications</span>
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900" />
        </Link>

        {/* Profile Dropdown */}
        <div className="relative border-l border-slate-200 dark:border-slate-800 pl-2 md:pl-3">
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="flex items-center gap-2 focus:outline-none"
          >
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-bold text-slate-900 dark:text-white leading-tight" suppressHydrationWarning>{displayName}</span>
              <span className="text-[10px] text-slate-400 font-mono font-bold">{roleLabel.toUpperCase()} PORTAL</span>
            </div>
            <div className={`w-8 h-8 md:w-9 md:h-9 rounded-xl ${avatarBg} text-white font-bold text-xs flex items-center justify-center ring-2 ring-white dark:ring-slate-900 shadow-sm`}>
              <span suppressHydrationWarning>{avatarInitial}</span>
            </div>
            <span className="material-symbols-outlined text-slate-400 text-[16px]">expand_more</span>
          </button>

          {showProfileMenu && (
            <div className="absolute right-0 top-full mt-2 w-52 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50">
              <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800">
                <p className="text-xs font-bold text-slate-900 dark:text-white" suppressHydrationWarning>{displayName}</p>
                <p className="text-[10px] font-mono font-bold text-slate-400 uppercase">{roleLabel} Portal</p>
              </div>
              <button onClick={() => { toggleDarkMode(); setShowProfileMenu(false); }}
                className="w-full flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left">
                <span className="material-symbols-outlined text-[16px]">{isDark ? 'light_mode' : 'dark_mode'}</span>
                {isDark ? 'Light Mode' : 'Dark Mode'}
              </button>
              <Link href="/profile" onClick={() => setShowProfileMenu(false)}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                <span className="material-symbols-outlined text-[16px]">manage_accounts</span>
                My Profile
              </Link>
              <Link href="/notifications" onClick={() => setShowProfileMenu(false)}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                <span className="material-symbols-outlined text-[16px]">notifications</span>
                Notifications
              </Link>
              <Link href="/select-portal" onClick={() => setShowProfileMenu(false)}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                <span className="material-symbols-outlined text-[16px]">swap_horiz</span>
                Switch Portal
              </Link>
              <div className="border-t border-slate-100 dark:border-slate-800 mt-1 pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">logout</span>
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
