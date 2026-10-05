'use client';

import { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

interface AppLayoutProps {
  children: React.ReactNode;
  onOpenUpload?: () => void;
  urgentCount?: number;
  totalCount?: number;
  title?: string;
  onSearchChange?: (query: string) => void;
  searchValue?: string;
}

export default function AppLayout({
  children,
  onOpenUpload,
  urgentCount = 0,
  totalCount = 0,
  title,
  onSearchChange,
  searchValue,
}: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      <Sidebar
        onOpenUpload={onOpenUpload}
        urgentCount={urgentCount}
        totalCount={totalCount}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="lg:pl-64">
        <Header
          title={title}
          onSearchChange={onSearchChange}
          searchValue={searchValue}
          onMenuToggle={() => setSidebarOpen((prev) => !prev)}
        />
        <main className="pt-16 min-h-[calc(100vh-4rem)]">
          {children}
        </main>
      </div>
    </div>
  );
}
