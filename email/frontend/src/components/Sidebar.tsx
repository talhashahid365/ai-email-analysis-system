"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { apiFetch, getAuthToken, getRoleHomePage, getUserRole, getUserName, setUserRole, setUserName, clearAuthToken } from '@/lib/api';
import { useTheme } from '@/lib/theme';

interface SidebarProps {
  onOpenUpload?: () => void;
  urgentCount?: number;
  totalCount?: number;
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ onOpenUpload, urgentCount = 0, isOpen = false, onClose = () => {} }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const [role, setRole] = useState<string>('user');
  const [userName, setUserNameState] = useState<string>('');
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setRole(getUserRole() || 'user');
    setUserNameState(getUserName() || '');
    setMounted(true);

    // The saved role can be stale (an admin may have promoted or demoted this account since login).
    // Always re-read it from the server so admin features appear, or disappear, immediately.
    if (!getAuthToken()) return;
    apiFetch('/auth/me')
      .then((me: any) => {
        if (!me?.role) return;
        const previous = getUserRole();
        setUserRole(me.role);
        setRole(me.role);
        if (me.full_name) { setUserName(me.full_name); setUserNameState(me.full_name); }
        // Lost access to the page they are on (e.g. demoted while on /admin): send them to their own home page.
        if (previous && previous !== me.role && (pathname.startsWith('/admin') || pathname.startsWith('/manager'))) {
          if (!(pathname.startsWith('/admin') && me.role === 'admin') && !(pathname.startsWith('/manager') && me.role !== 'user')) {
            router.replace(getRoleHomePage(me.role));
          }
        }
      })
      .catch(() => { /* apiFetch already handles an expired login */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Header's hamburger button asks the sidebar to open on pages that don't manage this state themselves
  useEffect(() => {
    const toggle = () => setMenuOpen((prev) => !prev);
    window.addEventListener('mailnexa:toggle-sidebar', toggle);
    return () => window.removeEventListener('mailnexa:toggle-sidebar', toggle);
  }, []);

  // Close the drawer after navigating
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  const open = isOpen || menuOpen;
  const closeMenu = () => { setMenuOpen(false); onClose(); };

  const handleLogout = () => {
    clearAuthToken();
    router.replace('/select-portal');
  };

  const navItems: { name: string; href: string; icon: string; hasBadge?: boolean }[] = [
    { name: 'Command Center', href: '/dashboard', icon: 'grid_view' },
    { name: 'Email Inbox', href: '/inbox', icon: 'mail', hasBadge: true },
    { name: 'Cognitive Analytics', href: '/analytics', icon: 'bar_chart' },
    { name: 'AI Email Assistant', href: '/assistant', icon: 'auto_awesome' },
    { name: 'Tasks & Deadlines', href: '/tasks', icon: 'task_alt' },
    { name: 'Notifications', href: '/notifications', icon: 'notifications' },
    { name: 'User Profile', href: '/profile', icon: 'settings' },
  ];
  // Always visible for admins (and managers) so the Users & RBAC tab is one click away from every page.
  if (role === 'admin') navItems.splice(1, 0, { name: 'Admin Panel (Users & RBAC)', href: '/admin', icon: 'admin_panel_settings' });
  else if (role === 'manager') navItems.splice(1, 0, { name: 'Manager Overview', href: '/manager', icon: 'supervisor_account' });

  const avatarInitial = mounted && userName ? userName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : '?';
  const displayName = mounted && userName ? userName : 'User';

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-sm"
          onClick={closeMenu}
          aria-label="Close menu"
        />
      )}
      <aside className={`fixed left-0 top-0 h-screen w-64 bg-[#0F172A] text-slate-300 border-r border-slate-800 z-50 flex flex-col justify-between p-4 overflow-y-auto transition-transform duration-300 ease-in-out select-none ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <button
          onClick={closeMenu}
          className="absolute top-4 right-4 lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          aria-label="Close sidebar"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>

        <div className="flex flex-col gap-6">
          {/* Logo Brand Header — MailNexa AI (PDF Project) */}
          <div className="flex items-center gap-3 px-2 pt-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 flex-shrink-0">
              <span className="material-symbols-outlined text-[24px]">mark_email_unread</span>
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-extrabold text-base text-white tracking-tight leading-none font-sans">MailNexa AI</span>
              <span className="text-[11px] text-slate-400 font-medium mt-1 truncate">Email Intelligence System</span>
            </div>
          </div>

          {/* Upload Button */}
          {onOpenUpload && (
            <button
              onClick={onOpenUpload}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-all shadow-md shadow-blue-600/25"
            >
              <span className="material-symbols-outlined text-[18px]">upload</span>
              <span>Upload Email</span>
            </button>
          )}

          {/* Main Navigation List */}
          <nav className="flex flex-col gap-1.5">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center justify-between px-4 py-3 rounded-xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                      : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`material-symbols-outlined text-[20px] ${isActive ? 'text-white' : 'text-slate-400'}`}>
                      {item.icon}
                    </span>
                    <span className="tracking-wide">{item.name}</span>
                  </div>
                  {item.hasBadge && urgentCount > 0 && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500 text-white shadow-xs">{urgentCount}</span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Theme Switcher & AI Status Card */}
        <div className="flex flex-col gap-3">
          
          {/* Light / Dark Mode Switcher Pill */}
          <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-2 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 px-2 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[18px] text-amber-400">
                {theme === 'dark' ? 'dark_mode' : 'light_mode'}
              </span>
              {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
            </span>
            <button
              onClick={toggleTheme}
              className="px-3 py-1.5 rounded-xl bg-slate-700 text-white shadow-xs text-xs font-bold transition-all hover:bg-slate-600 flex items-center gap-1.5 cursor-pointer active:scale-95"
            >
              <span className="material-symbols-outlined text-[16px] text-amber-400">
                {theme === 'dark' ? 'wb_sunny' : 'nightlight'}
              </span>
              <span>Switch</span>
            </button>
          </div>

          {/* AI Status Card */}
          <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-3.5 flex flex-col gap-2 relative overflow-hidden backdrop-blur-xs">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <span className="material-symbols-outlined text-[18px]">smart_toy</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-bold text-white leading-tight">AI is working for you</span>
                <span className="text-[10px] text-slate-400 mt-0.5">Classifying, analyzing and finding what matters.</span>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-700/50">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] font-medium text-emerald-400">System Online</span>
            </div>
          </div>

          {/* User Profile Footer */}
          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center text-xs font-bold font-mono">
                {avatarInitial}
              </div>
              <div className="min-w-0 flex flex-col">
                <span className="text-xs font-bold text-white truncate" suppressHydrationWarning>{displayName}</span>
                <span className="text-[10px] text-slate-400 font-mono capitalize">{role}</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
            >
              <span className="material-symbols-outlined text-[18px]">logout</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
