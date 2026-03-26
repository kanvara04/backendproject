'use client';

import Sidebar from '@/components/Sidebar';
import { FileUp, Music, X, ArrowRight, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useState, useRef, DragEvent } from 'react';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const SUPPORTED_FORMATS = ['MP3', 'WAV', 'M4A', 'AAC', 'OGG', 'FLAC', 'WMA', 'OPUS'];

interface QueuedFile {
  id: string;
  file: File;
  name: string;
  size: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const addFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    const newFiles: QueuedFile[] = [];
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const ext = file.name.split('.').pop()?.toUpperCase() || '';
      if (!SUPPORTED_FORMATS.includes(ext)) continue;
      // Prevent duplicates
      if (queue.some(q => q.name === file.name && q.file.size === file.size)) continue;

      newFiles.push({
        id: `${Date.now()}-${i}`,
        file,
        name: file.name,
        size: formatSize(file.size),
        status: 'pending',
      });
    }
    setQueue(prev => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setQueue(prev => prev.filter(f => f.id !== id));
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const handleSelectFiles = () => {
    fileInputRef.current?.click();
  };

  const processUpload = async () => {
    if (queue.length === 0 || isProcessing) return;
    setIsProcessing(true);

    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];
      if (item.status !== 'pending') continue;

      // Update status to uploading
      setQueue(prev => prev.map(f => f.id === item.id ? { ...f, status: 'uploading' as const } : f));

      try {
        const formData = new FormData();
        formData.append('file', item.file);
        formData.append('customer_phone', 'N/A');
        formData.append('agent_id', 'N/A');

        const res = await fetch(`${API_BASE}/api/v1/audio/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // อัปโหลดสำเร็จ + AI เริ่มวิเคราะห์อัตโนมัติแล้ว
        setQueue(prev => prev.map(f =>
          f.id === item.id ? { ...f, status: 'done' as const } : f
        ));
      } catch (err: any) {
        setQueue(prev => prev.map(f =>
          f.id === item.id ? { ...f, status: 'error' as const, error: err.message } : f
        ));
      }
    }

    setIsProcessing(false);
  };

  const allDone = queue.length > 0 && queue.every(f => f.status === 'done' || f.status === 'error');
  const doneCount = queue.filter(f => f.status === 'done').length;

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        <h1 className="text-3xl font-semibold text-slate-800 mb-8">Upload File</h1>

        <div className="flex gap-8">
          {/* Upload Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleSelectFiles}
            className={`flex-1 border-2 border-dashed rounded-[32px] flex flex-col items-center justify-center p-10 min-h-[420px] transition-all cursor-pointer group ${
              isDragging
                ? 'border-blue-500 bg-blue-50/50'
                : 'border-slate-200 bg-slate-50/30 hover:bg-slate-50 hover:border-blue-200'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.wma,.opus"
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110 ${
              isDragging ? 'bg-blue-100 text-blue-700 scale-110' : 'bg-blue-50 text-blue-700'
            }`}>
              <FileUp size={32} />
            </div>
            <h3 className="text-xl font-bold text-slate-800 mb-2">
              {isDragging ? 'วางไฟล์ที่นี่' : 'Drag and drop file'}
            </h3>
            <p className="text-slate-400 text-xs mb-8 text-center max-w-[280px] leading-relaxed">
              Maximum 60mb. Supported formats: <span className="text-slate-500 font-medium">{SUPPORTED_FORMATS.join(', ')}</span>
            </p>
            <button
              onClick={(e) => { e.stopPropagation(); handleSelectFiles(); }}
              className="bg-blue-700 hover:bg-blue-800 text-white px-10 py-3 rounded-xl font-bold text-sm transition-all shadow-lg shadow-blue-200 hover:shadow-blue-300 cursor-pointer active:scale-95"
            >
              Select Files
            </button>
          </div>

          {/* Right Sidebar - File Queue */}
          <div className="w-80 flex flex-col">
            <h2 className="text-lg font-medium text-slate-800 mb-4">
              File Queue {queue.length > 0 && <span className="text-sm text-slate-400">({queue.length})</span>}
            </h2>

            <div className="space-y-2 mb-6 max-h-[350px] overflow-y-auto pr-2">
              {queue.length === 0 ? (
                <div className="text-center py-12 text-slate-300">
                  <Music size={32} className="mx-auto mb-2 opacity-50" />
                  <p className="text-xs">เลือกหรือลากไฟล์มาวาง</p>
                </div>
              ) : (
                queue.map((item) => (
                  <div key={item.id} className={`flex items-center p-2.5 bg-white border rounded-xl shadow-sm transition-colors ${
                    item.status === 'done' ? 'border-emerald-200 bg-emerald-50/50' :
                    item.status === 'error' ? 'border-red-200 bg-red-50/50' :
                    item.status === 'uploading' ? 'border-blue-200 bg-blue-50/50' :
                    'border-slate-100 hover:border-blue-100'
                  }`}>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center mr-3 shrink-0 ${
                      item.status === 'done' ? 'bg-emerald-100 text-emerald-600' :
                      item.status === 'error' ? 'bg-red-100 text-red-600' :
                      item.status === 'uploading' ? 'bg-blue-100 text-blue-600' :
                      'bg-slate-50 text-blue-600'
                    }`}>
                      {item.status === 'done' ? <CheckCircle2 size={16} /> :
                       item.status === 'error' ? <AlertCircle size={16} /> :
                       item.status === 'uploading' ? <Loader2 size={16} className="animate-spin" /> :
                       <Music size={16} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-800 truncate">{item.name}</p>
                      <p className="text-[10px] text-slate-400">
                        {item.status === 'done' ? '✓ Uploaded' :
                         item.status === 'error' ? `✗ ${item.error || 'Failed'}` :
                         item.status === 'uploading' ? 'Uploading...' :
                         `${item.size} • ${item.name.split('.').pop()?.toUpperCase()}`}
                      </p>
                    </div>
                    {item.status === 'pending' && (
                      <button
                        onClick={() => removeFile(item.id)}
                        className="text-slate-300 hover:text-slate-500 p-1 cursor-pointer shrink-0"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>

            {allDone ? (
              <button
                onClick={() => router.push('/files')}
                className="bg-emerald-600 hover:bg-emerald-700 text-white w-full py-4 rounded-xl font-medium flex items-center justify-center space-x-2 transition-colors cursor-pointer"
              >
                <CheckCircle2 size={20} />
                <span>ดูไฟล์ทั้งหมด ({doneCount} uploaded — กำลังวิเคราะห์)</span>
              </button>
            ) : (
              <button
                onClick={processUpload}
                disabled={queue.length === 0 || isProcessing}
                className="bg-blue-700 hover:bg-blue-800 text-white w-full py-4 rounded-xl font-medium flex items-center justify-center space-x-2 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isProcessing ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <span>Process Upload</span>
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            )}
            <p className="text-[10px] text-slate-400 text-center mt-3 px-4">
              By uploading, you agree to our Terms of Service
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
