'use client';

import Sidebar from '@/components/Sidebar';
import { AudioWaveform, Sparkles, MessageCircle, Info, Lightbulb, RefreshCw, Trash2, ArrowLeft, Play, Pause, AlertCircle, Loader2, SkipBack, SkipForward } from 'lucide-react';
import { useRouter, useParams } from 'next/navigation';
import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Whisper segment format (มี start/end เป็นวินาที)
interface TranscriptionSegment {
  id?: number;
  start: number;
  end: number;
  text: string;
  // Llama fallback fields
  speaker?: string;
  time?: string;
}

interface AnalysisData {
  analysis_id: string;
  file_id: string;
  agent_id: string;
  agent_name: string;
  phone_number_used: string;
  call_duration_seconds: number;
  audio_duration_seconds: number;
  call_timestamp: string;
  brand_name: string;
  brand_names: string[];
  product_category: string;
  sale_channel: string;
  csat_score: number;
  intent: string;
  qa_score: number;
  sentiment: string;
  sentiment_score: number;
  summary: string;
  summary_points: string[];
  transcription: TranscriptionSegment[];
  key_insights: string;
  keywords: string[];
  created_at: string;
}

interface FileData {
  file_id: string;
  original_filename: string;
  customer_phone: string;
  agent_id: string;
  agent_name: string;
  call_direction: string;
  call_date: string;
  call_duration_seconds: number;
}

export default function FileAnalysisDetail() {
  const router = useRouter();
  const params = useParams();
  const fileId = params.id as string;

  const [fileData, setFileData] = useState<FileData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audio state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeSeconds, setCurrentTimeSeconds] = useState(0);
  const [durationSeconds, setDurationSeconds] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Subtitle auto-scroll
  const activeSegmentRef = useRef<HTMLDivElement | null>(null);
  const transcriptionContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchDetail();
  }, [fileId]);

  // ★ หยุดเสียงเมื่อออกจากหน้านี้
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }
    };
  }, []);

  // Auto-poll: ถ้ายังไม่มี analysis ให้ poll ทุก 3 วินาที
  useEffect(() => {
    if (!fileData || analysis) return;
    const fileStatus = (fileData as any)?.status;
    if (fileStatus === 'processing' || fileStatus === 'ready') {
      setAnalyzing(true);
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/v1/audio/detail/${fileId}`);
          if (!res.ok) return;
          const data = await res.json();
          if (data.analysis) {
            setAnalysis(data.analysis);
            setFileData(data.file);
            setAnalyzing(false);
            clearInterval(interval);
          }
        } catch {}
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [fileData, analysis, fileId]);

  // Auto-scroll to active subtitle
  useEffect(() => {
    if (activeSegmentRef.current && transcriptionContainerRef.current) {
      const container = transcriptionContainerRef.current;
      const element = activeSegmentRef.current;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();

      if (elementRect.top < containerRect.top || elementRect.bottom > containerRect.bottom) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [currentTimeSeconds]);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/audio/detail/${fileId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFileData(data.file);
      setAnalysis(data.analysis);
    } catch (err: any) {
      setError('ไม่สามารถโหลดข้อมูลไฟล์ได้');
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalysis = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ai/analyze/${fileId}`, { method: 'POST' });
      if (!res.ok) throw new Error('Analysis failed');
      const data = await res.json();
      const taskId = data.task_id;

      // Poll สถานะ — รอได้สูงสุด 5 นาที (150 attempts × 2s)
      let attempts = 0;
      while (attempts < 150) {
        await new Promise(r => setTimeout(r, 2000));
        const statusRes = await fetch(`${API_BASE}/api/v1/ai/status/${taskId}`);
        const statusData = await statusRes.json();

        if (statusData.status === 'completed') {
          await fetchDetail(); // โหลดผลใหม่
          break;
        }
        if (statusData.status === 'failed') {
          throw new Error(statusData.error || 'Analysis failed');
        }
        attempts++;
      }
    } catch (err: any) {
      setError('การวิเคราะห์ล้มเหลว: ' + (err.message || ''));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('ต้องการลบไฟล์นี้จริงหรือไม่?')) return;
    try {
      await fetch(`${API_BASE}/api/v1/audio/delete/${fileId}`, { method: 'DELETE' });
      router.push('/files');
    } catch {
      setError('ลบไฟล์ไม่สำเร็จ');
    }
  };

  // =============================================================================
  // Audio Player Controls
  // =============================================================================

  const initAudio = useCallback(() => {
    if (audioRef.current) return audioRef.current;
    const audio = new Audio(`${API_BASE}/api/v1/audio/play/${fileId}`);
    audioRef.current = audio;

    audio.addEventListener('loadedmetadata', () => {
      setDurationSeconds(audio.duration);
    });
    audio.addEventListener('timeupdate', () => {
      setCurrentTimeSeconds(audio.currentTime);
    });
    audio.addEventListener('ended', () => {
      setIsPlaying(false);
    });

    return audio;
  }, [fileId]);

  const togglePlay = () => {
    const audio = initAudio();
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const seekTo = (seconds: number) => {
    const audio = initAudio();
    audio.currentTime = seconds;
    setCurrentTimeSeconds(seconds);
    if (!isPlaying) {
      audio.play();
      setIsPlaying(true);
    }
  };

  const skipForward = () => {
    const audio = initAudio();
    audio.currentTime = Math.min(audio.currentTime + 10, durationSeconds);
  };

  const skipBackward = () => {
    const audio = initAudio();
    audio.currentTime = Math.max(audio.currentTime - 10, 0);
  };

  // =============================================================================
  // Helpers
  // =============================================================================

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const getActiveSegmentIndex = (): number => {
    if (!analysis?.transcription) return -1;
    for (let i = analysis.transcription.length - 1; i >= 0; i--) {
      const segStart = typeof analysis.transcription[i].start === 'number' ? analysis.transcription[i].start : 0;
      if (currentTimeSeconds >= segStart) {
        return i;
      }
    }
    return -1;
  };

  const getSentimentBadge = (sentiment: string) => {
    const s = sentiment?.toLowerCase();
    if (s === 'positive') return { label: 'POSITIVE SENTIMENT', color: 'bg-emerald-50 text-emerald-600', dot: 'bg-emerald-500' };
    if (s === 'negative') return { label: 'NEGATIVE SENTIMENT', color: 'bg-red-50 text-red-600', dot: 'bg-red-500' };
    return { label: 'NEUTRAL SENTIMENT', color: 'bg-slate-100 text-slate-600', dot: 'bg-slate-400' };
  };

  const progressPercent = durationSeconds > 0 ? (currentTimeSeconds / durationSeconds) * 100 : 0;

  // =============================================================================
  // Render
  // =============================================================================

  if (loading) {
    return (
      <div className="flex h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 size={32} className="animate-spin text-blue-600 mx-auto mb-3" />
            <p className="text-sm text-slate-500">กำลังโหลดข้อมูล...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error && !fileData) {
    return (
      <div className="flex h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle size={32} className="text-red-500 mx-auto mb-3" />
            <p className="text-sm text-red-600">{error}</p>
            <button onClick={() => router.back()} className="mt-4 text-sm text-blue-600 hover:underline cursor-pointer">กลับหน้าก่อน</button>
          </div>
        </main>
      </div>
    );
  }

  const sentimentBadge = analysis ? getSentimentBadge(analysis.sentiment) : null;
  const activeSegmentIdx = getActiveSegmentIndex();

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-7xl mx-auto space-y-6">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
            <div className="flex flex-col items-start">
              <button
                onClick={() => router.push('/files')}
                className="flex items-center text-slate-500 hover:text-slate-800 transition-colors mb-4 cursor-pointer group w-fit -ml-1"
              >
                <ArrowLeft size={18} className="mr-1.5 group-hover:-translate-x-1 transition-transform" />
                <span className="text-[13px] font-bold">Back to Files</span>
              </button>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center text-slate-800">
                  <AudioWaveform size={24} />
                </div>
                <h1 className="text-2xl font-bold text-slate-800 tracking-tight truncate max-w-[500px]">
                  {fileData?.original_filename || 'Unknown File'}
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-2.5">
              <button
                onClick={triggerAnalysis}
                disabled={analyzing}
                className="flex items-center space-x-2 px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-xs font-bold hover:bg-slate-50 transition-all cursor-pointer shadow-sm active:scale-95 disabled:opacity-50"
              >
                <RefreshCw size={16} className={`text-slate-400 ${analyzing ? 'animate-spin' : ''}`} />
                <span>{analyzing ? 'กำลังวิเคราะห์...' : 're-Analyze'}</span>
              </button>
              <button
                onClick={handleDelete}
                className="flex items-center space-x-2 px-4 py-2.5 bg-red-50 border border-red-100 text-red-600 rounded-xl text-xs font-bold hover:bg-red-100 transition-all cursor-pointer shadow-sm active:scale-95"
              >
                <Trash2 size={16} />
                <span>Delete</span>
              </button>
            </div>
          </div>

          {/* No Analysis State */}
          {!analysis && (
            <div className={`${analyzing ? 'bg-blue-50 border-blue-200' : 'bg-amber-50 border-amber-200'} border rounded-2xl p-8 text-center`}>
              {analyzing ? (
                <>
                  <Loader2 size={40} className="text-blue-600 mx-auto mb-4 animate-spin" />
                  <h3 className="text-lg font-bold text-blue-800 mb-2">AI กำลังวิเคราะห์ไฟล์เสียง...</h3>
                  <p className="text-sm text-blue-600 mb-2">Whisper กำลังถอดข้อความ → Llama กำลังวิเคราะห์</p>
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-xs text-blue-500 ml-2">กรุณารอสักครู่ อาจใช้เวลา 15-45 วินาที</span>
                  </div>
                </>
              ) : (
                <>
                  <AlertCircle size={32} className="text-amber-500 mx-auto mb-3" />
                  <h3 className="text-lg font-bold text-amber-800 mb-2">ยังไม่ได้วิเคราะห์ไฟล์นี้</h3>
                  <p className="text-sm text-amber-600 mb-4">กดปุ่ม &quot;re-Analyze&quot; เพื่อเริ่มวิเคราะห์ด้วย AI</p>
                  <button
                    onClick={triggerAnalysis}
                    disabled={analyzing}
                    className="bg-blue-700 hover:bg-blue-800 text-white px-6 py-3 rounded-xl font-bold text-sm cursor-pointer disabled:opacity-50"
                  >
                    เริ่มวิเคราะห์ด้วย AI
                  </button>
                </>
              )}
            </div>
          )}

          {analysis && (
            <>
              {/* Re-analyzing banner */}
              {analyzing && (
                <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
                  <Loader2 size={20} className="text-blue-600 animate-spin shrink-0" />
                  <div>
                    <p className="text-sm font-bold text-blue-800">กำลังวิเคราะห์ใหม่...</p>
                    <p className="text-xs text-blue-600">เข้าคิวแล้ว รอประมวลผล ผลเดิมยังแสดงอยู่ด้านล่าง</p>
                  </div>
                </div>
              )}
            <div className="grid grid-cols-3 gap-6">
              {/* Left Column */}
              <div className="col-span-2 space-y-6">
                
                {/* Conversation Summary — Llama */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                  <div className="flex items-center space-x-3 mb-6">
                    <Sparkles className="text-slate-800" size={24} />
                    <h2 className="text-lg font-bold text-slate-800">Conversation Summary</h2>
                  </div>
                  {analysis.summary_points && analysis.summary_points.length > 0 ? (
                    <ul className="space-y-4 text-slate-500 text-sm list-disc pl-5 marker:text-slate-300">
                      {analysis.summary_points.map((point, i) => (
                        <li key={i}>{point}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-500 text-sm">{analysis.summary}</p>
                  )}
                </div>

                {/* Transcription Detail — Whisper Segments (Subtitle Sync) */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                  {/* Header */}
                  <div className="p-6 pb-0">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <MessageCircle className="text-slate-800" size={24} />
                        <h2 className="text-lg font-bold text-slate-800">Transcription Detail</h2>
                      </div>
                      {sentimentBadge && (
                        <span className={`px-3 py-1 ${sentimentBadge.color} text-xs font-bold rounded-full flex items-center space-x-1`}>
                          <span className={`w-1.5 h-1.5 ${sentimentBadge.dot} rounded-full`}></span>
                          <span>{sentimentBadge.label}</span>
                        </span>
                      )}
                    </div>

                    {/* Audio Player — inside Transcription */}
                    <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 mb-4">
                      <div className="flex items-center space-x-3">
                        <button
                          onClick={skipBackward}
                          className="w-7 h-7 text-slate-400 hover:text-slate-600 flex items-center justify-center cursor-pointer transition-colors shrink-0"
                          title="-10s"
                        >
                          <SkipBack size={14} />
                        </button>
                        <button
                          onClick={togglePlay}
                          className="w-10 h-10 bg-blue-700 text-white rounded-full flex items-center justify-center shadow-sm cursor-pointer hover:bg-blue-800 transition-colors shrink-0"
                        >
                          {isPlaying ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
                        </button>
                        <button
                          onClick={skipForward}
                          className="w-7 h-7 text-slate-400 hover:text-slate-600 flex items-center justify-center cursor-pointer transition-colors shrink-0"
                          title="+10s"
                        >
                          <SkipForward size={14} />
                        </button>

                        {/* Progress bar */}
                        <div className="flex-1 flex items-center space-x-3">
                          <span className="text-[11px] font-mono text-slate-500 w-10 text-right shrink-0">
                            {formatTime(currentTimeSeconds)}
                          </span>
                          <div
                            className="flex-1 h-1.5 bg-slate-200 rounded-full cursor-pointer relative group"
                            onClick={(e) => {
                              const rect = e.currentTarget.getBoundingClientRect();
                              const percent = (e.clientX - rect.left) / rect.width;
                              const dur = durationSeconds || (fileData?.call_duration_seconds ?? 0);
                              seekTo(percent * dur);
                            }}
                          >
                            <div
                              className="h-full bg-blue-600 rounded-full relative transition-all"
                              style={{ width: `${progressPercent}%` }}
                            >
                              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-blue-700 rounded-full shadow-sm opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400 w-10 shrink-0">
                            {formatTime(durationSeconds || fileData?.call_duration_seconds || analysis?.audio_duration_seconds || analysis?.call_duration_seconds || 0)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Subtitle Segments */}
                  {analysis.transcription && analysis.transcription.length > 0 ? (
                    <div
                      ref={transcriptionContainerRef}
                      className="max-h-[480px] overflow-y-auto px-6 pb-6"
                    >
                      <div className="space-y-1">
                        {analysis.transcription.map((seg, idx) => {
                          const segStart = typeof seg.start === 'number' ? seg.start : 0;
                          const segEnd = typeof seg.end === 'number' ? seg.end : segStart + 5;
                          const segText = seg.text || '';
                          const isActive = idx === activeSegmentIdx && isPlaying;
                          const isPast = currentTimeSeconds > segEnd && isPlaying;

                          if (!segText) return null; // ข้าม segment ที่ไม่มีข้อความ

                          return (
                            <div
                              key={`seg-${idx}`}
                              ref={isActive ? activeSegmentRef : null}
                              onClick={() => seekTo(segStart)}
                              className={`flex items-start gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all duration-200 group ${
                                isActive
                                  ? 'bg-blue-50 border border-blue-200 shadow-sm'
                                  : isPast
                                    ? 'opacity-50 hover:opacity-80 hover:bg-slate-50'
                                    : 'hover:bg-slate-50'
                              }`}
                            >
                              {/* Timestamp */}
                              <span className={`text-[11px] font-mono shrink-0 pt-0.5 w-12 text-right ${
                                isActive ? 'text-blue-600 font-bold' : 'text-slate-400'
                              }`}>
                                {formatTime(segStart)}
                              </span>

                              {/* Active indicator */}
                              <div className={`w-1.5 shrink-0 rounded-full mt-1.5 transition-all ${
                                isActive
                                  ? 'h-4 bg-blue-600 animate-pulse'
                                  : 'h-1.5 bg-slate-200 group-hover:bg-slate-300'
                              }`} />

                              {/* Text */}
                              <p className={`text-sm leading-relaxed flex-1 ${
                                isActive
                                  ? 'text-slate-900 font-medium'
                                  : 'text-slate-600'
                              }`}>
                                {segText}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="px-6 pb-6">
                      <p className="text-slate-400 text-sm text-center py-8">ไม่มีข้อมูล Transcription</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column */}
              <div className="space-y-6">
                
                {/* Metadata / Details */}
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                  <div className="flex items-center space-x-3 mb-6 pb-6 border-b border-slate-100">
                    <Info className="text-slate-800" size={24} />
                    <h2 className="text-lg font-bold text-slate-800">Metadata / Details</h2>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-y-6 gap-x-4">
                    <div className="col-span-2">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">CUSTOMER PHONE</p>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-slate-800">
                          {fileData?.customer_phone || analysis?.phone_number_used || 'N/A'}
                        </p>
                        {fileData?.call_direction && fileData.call_direction !== 'Unknown' && (
                          <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                            fileData.call_direction === 'Inbound'
                              ? 'bg-green-50 text-green-600'
                              : 'bg-orange-50 text-orange-600'
                          }`}>
                            {fileData.call_direction === 'Inbound' ? '📞 Inbound' : '📱 Outbound'}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="col-span-2">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">AGENT ID</p>
                      <p className="text-sm font-semibold text-slate-800">
                        {analysis?.agent_id || fileData?.agent_id || 'N/A'}
                        {(analysis?.agent_name || fileData?.agent_name) &&
                          ` (${analysis?.agent_name || fileData?.agent_name})`}
                      </p>
                    </div>

                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">BRAND</p>
                      <div className="flex flex-wrap gap-1">
                        {(analysis?.brand_names && analysis.brand_names.length > 0
                          ? analysis.brand_names
                          : analysis?.brand_name && analysis.brand_name !== 'Unknown'
                            ? [analysis.brand_name]
                            : []
                        ).map((b, i) => (
                          <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-bold rounded">{b}</span>
                        ))}
                        {(!analysis?.brand_names || analysis.brand_names.length === 0) && !analysis?.brand_name && (
                          <span className="text-sm text-slate-400">-</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">PRODUCT</p>
                      <p className="text-sm font-semibold text-slate-800">{analysis?.product_category || '-'}</p>
                    </div>

                    <div className="col-span-2">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">SALE CHANNEL</p>
                      <p className="text-sm font-semibold text-slate-800">{analysis?.sale_channel || '-'}</p>
                    </div>

                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">QA SCORE</p>
                      <p className="text-sm font-semibold text-slate-800">{analysis?.qa_score ? `${analysis.qa_score}/10` : '-'}</p>
                    </div>

                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">CSAT</p>
                      <p className="text-sm font-semibold text-slate-800">{analysis?.csat_score ? `${analysis.csat_score}/5` : '-'}</p>
                    </div>

                    <div className="col-span-2">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">ANALYSIS DATE</p>
                      <p className="text-sm font-semibold text-slate-800">
                        {analysis?.created_at
                          ? new Date(analysis.created_at).toLocaleString('en-US', {
                              month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
                            })
                          : '-'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Key Insights */}
                {analysis?.key_insights && (
                  <div className="bg-blue-800 rounded-2xl p-6 text-white relative overflow-hidden shadow-md">
                    <div className="absolute -bottom-4 right-0 text-[80px] font-bold text-blue-700/50 leading-none select-none pointer-events-none">
                      bulb
                    </div>
                    <div className="relative z-10">
                      <div className="flex items-center space-x-3 mb-4">
                        <div className="bg-blue-700/50 p-2 rounded-lg">
                          <Lightbulb size={20} className="text-white" />
                        </div>
                        <h2 className="text-lg font-bold">Key Insights</h2>
                      </div>
                      <p className="text-sm text-blue-100 leading-relaxed">
                        {analysis.key_insights}
                      </p>
                    </div>
                  </div>
                )}

                {/* Keywords */}
                {analysis?.keywords && analysis.keywords.length > 0 && (
                  <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
                    <h3 className="text-sm font-bold text-slate-800 mb-3">Keywords</h3>
                    <div className="flex flex-wrap gap-2">
                      {analysis.keywords.map((kw, i) => (
                        <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
