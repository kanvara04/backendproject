'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, CloudUpload, FileText, Folder } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-slate-50 border-r border-slate-200 flex flex-col justify-between">
      <div>
        <div className="p-6 flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-700 rounded-xl flex items-center justify-center text-white">
            <Folder size={24} />
          </div>
          <span className="text-xl font-bold text-slate-800">File Manager</span>
        </div>

        <nav className="mt-6 px-4 space-y-2">
          <Link href="/dashboard" className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${pathname === '/dashboard' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-100'}`}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </Link>
          <Link href="/upload" className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${pathname === '/upload' ? 'bg-blue-700 text-white' : 'text-slate-500 hover:bg-slate-100'}`}>
            <CloudUpload size={20} />
            <span>Upload File</span>
          </Link>
          <Link href="/files" className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${pathname.includes('/files') ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:bg-slate-100'}`}>
            <FileText size={20} />
            <span>Files</span>
          </Link>
        </nav>
      </div>
    </aside>
  );
}
