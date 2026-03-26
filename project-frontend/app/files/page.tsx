'use client';

import Sidebar from '@/components/Sidebar';
import { Search, RotateCw, Calendar, Tag, CheckCircle2, RefreshCw, FileAudio, Package, AlertCircle, ChevronDown, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const BRANDS = ['LOTUS', 'OMAZZ', 'DUNLOPILLO', 'MIDAS', 'BEDGEAR', 'LALABED', 'ZINUS', 'EASTMAN HOUSE', 'MALOUF', 'LOTO MOBILI', 'WOODFIELD', 'RESTONIC'];
const PRODUCTS = ['Mattress', 'Pillow', 'Bedding', 'Bed Frame', 'Topper', 'Protector'];

interface FileRecord {
  file_id: string;
  name: string;
  customer: string;
  agent: string;
  agent_name: string;
  brand: string;
  brands: string[];
  product: string;
  sentiment: string;
  status: string;
  date: string;
  call_direction: string;
}

export default function FilesPage() {
  const router = useRouter();
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 10;

  // Filters
  const [filterBrand, setFilterBrand] = useState('');
  const [filterProduct, setFilterProduct] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  // Dropdown visibility
  const [showBrand, setShowBrand] = useState(false);
  const [showProduct, setShowProduct] = useState(false);
  const [showDate, setShowDate] = useState(false);

  const brandRef = useRef<HTMLDivElement>(null);
  const productRef = useRef<HTMLDivElement>(null);
  const dateRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (brandRef.current && !brandRef.current.contains(e.target as Node)) setShowBrand(false);
      if (productRef.current && !productRef.current.contains(e.target as Node)) setShowProduct(false);
      if (dateRef.current && !dateRef.current.contains(e.target as Node)) setShowDate(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (search) params.set('search', search);
      if (filterBrand) params.set('brand', filterBrand);
      if (filterProduct) params.set('product', filterProduct);
      if (filterDateFrom) params.set('date_from', filterDateFrom);
      if (filterDateTo) params.set('date_to', filterDateTo);

      const res = await fetch(`${API_BASE}/api/v1/audio/list?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFiles(data.files || []);
      setTotalPages(data.total_pages || 1);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError('ไม่สามารถเชื่อมต่อกับ API ได้ — กรุณาเปิด Backend Server (uvicorn)');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterBrand, filterProduct, filterDateFrom, filterDateTo]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  useEffect(() => {
    const hasProcessing = files.some(f => f.status === 'PROCESSING');
    if (!hasProcessing) return;
    const interval = setInterval(() => { fetchFiles(); }, 5000);
    return () => clearInterval(interval);
  }, [files, fetchFiles]);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch { return dateStr; }
  };

  const getSentimentStyle = (sentiment: string) => {
    switch (sentiment?.toUpperCase()) {
      case 'POSITIVE': return 'bg-emerald-50 text-emerald-500';
      case 'NEGATIVE': return 'bg-red-50 text-red-500';
      default: return 'bg-slate-100 text-slate-500';
    }
  };

  const getStatusIcon = (status: string) => {
    if (status === 'COMPLETE') return <CheckCircle2 size={14} />;
    return <RefreshCw size={14} className="animate-spin" />;
  };

  const getStatusColor = (status: string) => {
    return status === 'COMPLETE' ? 'text-emerald-500' : 'text-orange-500';
  };

  const activeFilterCount = [filterBrand, filterProduct, filterDateFrom || filterDateTo].filter(Boolean).length;

  const clearAllFilters = () => {
    setFilterBrand('');
    setFilterProduct('');
    setFilterDateFrom('');
    setFilterDateTo('');
    setPage(1);
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-full mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
              <span className="text-blue-600"><FileAudio size={24}/></span> Files
            </h1>
          </div>

          {/* Toolbar */}
          <div className="bg-white p-4 rounded-t-2xl flex items-center space-x-4 shadow-sm border-b border-slate-100">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
              <input
                type="text"
                placeholder="ค้นหาชื่อไฟล์, เบอร์โทร, Agent, Brand..."
                className="w-full pl-12 pr-4 py-3 bg-slate-50 rounded-xl border-none outline-none focus:ring-2 focus:ring-blue-100 text-sm"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                onKeyDown={(e) => { if (e.key === 'Enter') fetchFiles(); }}
              />
            </div>
            <button
              onClick={fetchFiles}
              className="p-3 bg-slate-50 text-slate-500 rounded-xl hover:bg-slate-100 cursor-pointer transition-colors"
            >
              <RotateCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Filters */}
          <div className="bg-white p-4 flex items-center space-x-3 shadow-sm">
            {/* Date Filter */}
            <div ref={dateRef} className="relative">
              <button
                onClick={() => { setShowDate(!showDate); setShowBrand(false); setShowProduct(false); }}
                className={`px-4 py-2 border rounded-lg text-sm font-medium flex items-center space-x-2 cursor-pointer transition-colors ${
                  filterDateFrom || filterDateTo ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Calendar size={16} />
                <span>{filterDateFrom || filterDateTo ? `${filterDateFrom || '...'} ~ ${filterDateTo || '...'}` : 'Date'}</span>
                <ChevronDown size={14} />
              </button>
              {showDate && (
                <div className="absolute top-full left-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-lg p-4 z-50 w-72">
                  <p className="text-xs font-bold text-slate-400 uppercase mb-2">ช่วงวันที่</p>
                  <div className="flex items-center gap-2 mb-3">
                    <input
                      type="date"
                      value={filterDateFrom}
                      onChange={(e) => { setFilterDateFrom(e.target.value); setPage(1); }}
                      className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-blue-300"
                    />
                    <span className="text-slate-400 text-xs">ถึง</span>
                    <input
                      type="date"
                      value={filterDateTo}
                      onChange={(e) => { setFilterDateTo(e.target.value); setPage(1); }}
                      className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-blue-300"
                    />
                  </div>
                  {(filterDateFrom || filterDateTo) && (
                    <button onClick={() => { setFilterDateFrom(''); setFilterDateTo(''); setPage(1); }} className="text-xs text-red-500 hover:underline cursor-pointer">ล้าง</button>
                  )}
                </div>
              )}
            </div>

            {/* Brand Filter */}
            <div ref={brandRef} className="relative">
              <button
                onClick={() => { setShowBrand(!showBrand); setShowDate(false); setShowProduct(false); }}
                className={`px-4 py-2 border rounded-lg text-sm font-medium flex items-center space-x-2 cursor-pointer transition-colors ${
                  filterBrand ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Tag size={16} />
                <span>{filterBrand || 'Brand'}</span>
                <ChevronDown size={14} />
              </button>
              {showBrand && (
                <div className="absolute top-full left-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-lg py-2 z-50 w-52 max-h-72 overflow-y-auto">
                  <button
                    onClick={() => { setFilterBrand(''); setPage(1); setShowBrand(false); }}
                    className={`w-full text-left px-4 py-2 text-sm cursor-pointer transition-colors ${!filterBrand ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-600 hover:bg-slate-50'}`}
                  >
                    ทั้งหมด
                  </button>
                  {BRANDS.map((b) => (
                    <button
                      key={b}
                      onClick={() => { setFilterBrand(b); setPage(1); setShowBrand(false); }}
                      className={`w-full text-left px-4 py-2 text-sm cursor-pointer transition-colors ${filterBrand === b ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-600 hover:bg-slate-50'}`}
                    >
                      {b}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Product Filter */}
            <div ref={productRef} className="relative">
              <button
                onClick={() => { setShowProduct(!showProduct); setShowDate(false); setShowBrand(false); }}
                className={`px-4 py-2 border rounded-lg text-sm font-medium flex items-center space-x-2 cursor-pointer transition-colors ${
                  filterProduct ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Package size={16} />
                <span>{filterProduct || 'Product'}</span>
                <ChevronDown size={14} />
              </button>
              {showProduct && (
                <div className="absolute top-full left-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-lg py-2 z-50 w-48">
                  <button
                    onClick={() => { setFilterProduct(''); setPage(1); setShowProduct(false); }}
                    className={`w-full text-left px-4 py-2 text-sm cursor-pointer transition-colors ${!filterProduct ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-600 hover:bg-slate-50'}`}
                  >
                    ทั้งหมด
                  </button>
                  {PRODUCTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => { setFilterProduct(p); setPage(1); setShowProduct(false); }}
                      className={`w-full text-left px-4 py-2 text-sm cursor-pointer transition-colors ${filterProduct === p ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-600 hover:bg-slate-50'}`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Clear filters */}
            {activeFilterCount > 0 && (
              <button
                onClick={clearAllFilters}
                className="px-3 py-2 text-xs text-red-500 hover:text-red-700 font-medium flex items-center gap-1 cursor-pointer"
              >
                <X size={14} /> ล้างตัวกรอง ({activeFilterCount})
              </button>
            )}
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 m-4 flex items-start space-x-3">
              <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={20} />
              <div>
                <p className="text-sm font-medium text-red-800">{error}</p>
                <p className="text-xs text-red-600 mt-1">ตรวจสอบว่ารัน: <code className="bg-red-100 px-1.5 py-0.5 rounded">cd project-backend && uvicorn main:app --reload --port 8000</code></p>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-b-2xl shadow-sm overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="p-4 pl-6">File Name</th>
                  <th className="p-4">Sentiment</th>
                  <th className="p-4">Customer</th>
                  <th className="p-4">Agent</th>
                  <th className="p-4">Brand</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-slate-400">
                      <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
                      <p className="text-sm">กำลังโหลดข้อมูล...</p>
                    </td>
                  </tr>
                ) : files.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-slate-400">
                      <FileAudio size={32} className="mx-auto mb-2 opacity-50" />
                      <p className="text-sm font-medium">ไม่พบไฟล์</p>
                      <p className="text-xs mt-1">ลอง upload ไฟล์ใหม่จากหน้า Upload</p>
                    </td>
                  </tr>
                ) : (
                  files.map((file) => (
                    <tr
                      key={file.file_id}
                      onClick={() => router.push(`/files/${file.file_id}`)}
                      className="hover:bg-slate-50 transition-colors cursor-pointer group"
                    >
                      <td className="p-4 pl-6 flex items-center space-x-3">
                        <div className="w-8 h-8 bg-slate-50 rounded flex items-center justify-center text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                          <FileAudio size={16} />
                        </div>
                        <span className="font-medium text-slate-800 text-sm truncate max-w-[220px]">{file.name}</span>
                      </td>
                      <td className="p-4">
                        <span className={`px-3 py-1 rounded-full text-[11px] font-bold ${getSentimentStyle(file.sentiment)}`}>
                          {file.sentiment}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-slate-600">{file.customer}</td>
                      <td className="p-4 text-sm text-slate-600">{file.agent}</td>
                      <td className="p-4">
                        <div className="flex flex-wrap gap-1">
                          {(file.brands && file.brands.length > 0 ? file.brands : (file.brand ? [file.brand] : [])).map((b, i) => (
                            <span key={i} className="px-2 py-0.5 bg-slate-50 text-slate-800 text-[11px] font-bold rounded uppercase">{b}</span>
                          ))}
                          {!file.brand && (!file.brands || file.brands.length === 0) && <span className="text-slate-400">-</span>}
                        </div>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center space-x-1 text-xs font-bold ${getStatusColor(file.status)}`}>
                          {getStatusIcon(file.status)}
                          <span>{file.status}</span>
                        </span>
                      </td>
                      <td className="p-4 text-sm text-slate-500 whitespace-nowrap">{formatDate(file.date)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="p-4 border-t border-slate-100 flex items-center justify-between text-sm text-slate-500">
              <span>
                Showing <span className="font-bold text-slate-800">{files.length}</span> of {total} entries
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="px-4 py-2 text-slate-400 cursor-pointer hover:text-slate-600 transition-colors disabled:opacity-30"
                >
                  PREVIOUS
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-medium cursor-pointer transition-colors ${
                      p === page
                        ? 'bg-blue-700 text-white shadow-sm'
                        : 'hover:bg-slate-100 text-slate-600'
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                  className="px-4 py-2 text-slate-600 font-medium hover:text-slate-800 transition-colors cursor-pointer disabled:opacity-30"
                >
                  NEXT
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
