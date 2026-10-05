"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken, getUserRole, getRoleHomePage } from '@/lib/api';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getAuthToken();
    const role = getUserRole();
    if (token && role) {
      router.replace(getRoleHomePage(role));
    } else {
      router.replace('/select-portal');
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm font-medium">Loading NexusMail AI...</p>
      </div>
    </div>
  );
}
