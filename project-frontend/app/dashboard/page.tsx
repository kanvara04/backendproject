'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { 
  FileAudio,
  Smile, 
  Meh, 
  Frown,
  CheckCircle2,
  RefreshCw,
  BarChart3,
  Tag,
  Calendar,
  Clock,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function DashboardPage() {
  const [filterType, setFilterType] = useState('Day');
  const [showCalendar, setShowCalendar] = useState(false);
  const [selectedDate, setSelectedDate] = useState({ 
    day: 11, 
    month: 'Mar', 
    year: 2026,
    view: 'days' // 'days' | 'months' | 'years'
  });

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const years = [2024, 2025, 2026, 2027];

  // ข้อมูลจำลองสำหรับแต่ละช่วงเวลา
  const dataMockup = {
    Day: {
      files: [
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'NEUTRAL', brand: 'dunlopillo', status: 'PROCESSING' },
      ],
      insight: `Most callers on ${selectedDate.day} ${selectedDate.month} are inquiring about "Smart Home Hub" setup.`
    },
    Month: {
      files: [
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'NEUTRAL', brand: 'dunlopillo', status: 'PROCESSING' },
        { sentiment: 'NEGATIVE', brand: 'slumberland', status: 'COMPLETE' },
        { sentiment: 'POSITIVE', brand: 'omazz', status: 'COMPLETE' },
      ],
      insight: `Sentiment for ${selectedDate.month} ${selectedDate.year} improved by 15% compared to previous month.`
    },
    Year: {
      files: [
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'NEUTRAL', brand: 'dunlopillo', status: 'PROCESSING' },
        { sentiment: 'NEGATIVE', brand: 'slumberland', status: 'COMPLETE' },
        { sentiment: 'NEGATIVE', brand: 'omazz', status: 'COMPLETE' },
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'POSITIVE', brand: 'lotus', status: 'COMPLETE' },
        { sentiment: 'POSITIVE', brand: 'omazz', status: 'COMPLETE' },
        { sentiment: 'NEUTRAL', brand: 'dunlopillo', status: 'COMPLETE' },
      ],
      insight: `Omazz remains the most analyzed brand in ${selectedDate.year}.`
    }
  };

  const activeData = dataMockup[filterType as keyof typeof dataMockup];
  const filesData = activeData.files;

  // ฟังก์ชันสลับวันในปฏิทิน (Mockup)
  const handleDateSelect = (day: number) => {
    setSelectedDate({ ...selectedDate, day });
    setFilterType('Day');
    setShowCalendar(false);
  };

  const handleMonthSelect = (month: string) => {
    setSelectedDate({ ...selectedDate, month, view: 'days' });
    setFilterType('Month');
  };

  const handleYearSelect = (year: number) => {
    setSelectedDate({ ...selectedDate, year, view: 'months' });
    setFilterType('Year');
  };

  // คำนวณข้อมูลง่ายๆ
  const totalFiles = filesData.length;
  const positiveCount = filesData.filter(f => f.sentiment === 'POSITIVE').length;
  const neutralCount = filesData.filter(f => f.sentiment === 'NEUTRAL').length;
  const negativeCount = filesData.filter(f => f.sentiment === 'NEGATIVE').length;
  const processingCount = filesData.filter(f => f.status === 'PROCESSING').length;

  const stats = [
    { label: 'Total Files', value: totalFiles, icon: FileAudio, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Positive Analysis', value: positiveCount, icon: Smile, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Processing', value: processingCount, icon: RefreshCw, color: 'text-orange-600', bg: 'bg-orange-50' },
    { label: 'Completed', value: totalFiles - processingCount, icon: CheckCircle2, color: 'text-blue-600', bg: 'bg-blue-50' },
  ];

  const sentimentData = [
    { label: 'Positive', count: positiveCount, percentage: Math.round((positiveCount/totalFiles)*100), color: 'bg-emerald-500', icon: Smile },
    { label: 'Neutral', count: neutralCount, percentage: Math.round((neutralCount/totalFiles)*100), color: 'bg-slate-400', icon: Meh },
    { label: 'Negative', count: negativeCount, percentage: Math.round((negativeCount/totalFiles)*100), color: 'bg-red-500', icon: Frown },
  ];

  const brands = Array.from(new Set(filesData.map(f => f.brand)));
  const brandDistribution = brands.map(b => ({
    name: b,
    count: filesData.filter(f => f.brand === b).length
  }));

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden text-slate-800">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-7xl mx-auto space-y-6">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-800">Voice Analytics Dashboard</h1>
              <p className="text-slate-500 text-sm">Viewing {filterType} Report for {selectedDate.day} {selectedDate.month} {selectedDate.year}</p>
            </div>
            
            <div className="flex items-center gap-3 relative">
              <div className="flex bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden text-[13px]">
                {['Day', 'Month', 'Year'].map((type) => (
                  <button 
                    key={type}
                    onClick={() => setFilterType(type)}
                    className={`px-4 py-2 font-bold transition-colors cursor-pointer ${filterType === type ? 'text-blue-600 bg-blue-50' : 'text-slate-500 hover:bg-slate-50'} ${type !== 'Year' ? 'border-r border-slate-100' : ''}`}
                  >
                    {type}
                  </button>
                ))}
              </div>
              
              <button 
                onClick={() => {
                  setFilterType('Day');
                  setSelectedDate({ day: 11, month: 'Mar', year: 2026, view: 'days' });
                }}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl shadow-sm hover:bg-slate-50 transition-colors cursor-pointer text-slate-700"
              >
                <Clock size={16} className="text-slate-400" />
                <span className="text-[13px] font-bold uppercase tracking-tight">Today</span>
              </button>
              
              <div className="h-8 w-px bg-slate-200 mx-1"></div>
              
              <div className="relative">
                <button 
                  onClick={() => setShowCalendar(!showCalendar)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-700 text-white rounded-xl shadow-md hover:bg-blue-800 transition-all cursor-pointer"
                >
                  <Calendar size={18} />
                  <span className="text-[13px] font-bold">{selectedDate.day} {selectedDate.month}, {selectedDate.year}</span>
                </button>

                {/* ADVANCED Calendar Mockup Dropdown */}
                {showCalendar && (
                  <div className="absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-2xl border border-slate-100 z-50 p-4 animate-in fade-in slide-in-from-top-2 duration-200">
                    
                    {/* Header View Switchers */}
                    <div className="flex justify-between items-center mb-4">
                      <div className="flex gap-2">
                        <button 
                          onClick={() => setSelectedDate({...selectedDate, view: 'years'})}
                          className="text-xs font-bold text-slate-400 hover:text-blue-600 cursor-pointer"
                        >
                          {selectedDate.year}
                        </button>
                        <span className="text-slate-300">/</span>
                        <button 
                          onClick={() => setSelectedDate({...selectedDate, view: 'months'})}
                          className="text-xs font-bold text-slate-400 hover:text-blue-600 cursor-pointer"
                        >
                          {selectedDate.month}
                        </button>
                      </div>
                      <div className="flex items-center gap-1">
                        <button className="p-1 hover:bg-slate-50 rounded text-slate-400 cursor-pointer"><ChevronLeft size={16} /></button>
                        <button className="p-1 hover:bg-slate-50 rounded text-slate-400 cursor-pointer"><ChevronRight size={16} /></button>
                      </div>
                    </div>

                    {/* DAYS VIEW */}
                    {selectedDate.view === 'days' && (
                      <>
                        <div className="grid grid-cols-7 gap-1 text-center mb-2">
                          {['S', 'M', 'T', 'W', 'TH', 'F', 'S'].map((d, idx) => (
                            <span key={idx} className="text-[10px] font-bold text-slate-300">{d}</span>
                          ))}
                        </div>
                        <div className="grid grid-cols-7 gap-1">
                          {Array.from({ length: 31 }).map((_, i) => {
                            const day = i + 1;
                            const isSelected = selectedDate.day === day;
                            return (
                              <button
                                key={day}
                                onClick={() => handleDateSelect(day)}
                                className={`h-8 text-xs rounded-lg transition-colors cursor-pointer flex items-center justify-center
                                  ${isSelected ? 'bg-blue-600 text-white font-bold' : 'text-slate-600 hover:bg-blue-50'}
                                `}
                              >
                                {day}
                              </button>
                            );
                          })}
                        </div>
                      </>
                    )}

                    {/* MONTHS VIEW */}
                    {selectedDate.view === 'months' && (
                      <div className="grid grid-cols-3 gap-2">
                        {months.map(m => (
                          <button
                            key={m}
                            onClick={() => handleMonthSelect(m)}
                            className={`py-3 text-xs rounded-xl transition-colors cursor-pointer font-medium
                              ${selectedDate.month === m ? 'bg-blue-600 text-white font-bold' : 'text-slate-600 hover:bg-blue-50'}
                            `}
                          >
                            {m}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* YEARS VIEW */}
                    {selectedDate.view === 'years' && (
                      <div className="grid grid-cols-2 gap-2">
                        {years.map(y => (
                          <button
                            key={y}
                            onClick={() => handleYearSelect(y)}
                            className={`py-4 text-sm rounded-xl transition-colors cursor-pointer font-medium
                              ${selectedDate.year === y ? 'bg-blue-600 text-white font-bold' : 'text-slate-600 hover:bg-blue-50'}
                            `}
                          >
                            {y}
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="mt-4 pt-3 border-t border-slate-50 flex justify-between items-center text-[10px] text-slate-400">
                      <span>Selecting {selectedDate.view}</span>
                      <button onClick={() => setShowCalendar(false)} className="font-bold text-blue-600 cursor-pointer">Close</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((stat, i) => (
              <div key={i} className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 transition-all duration-300">
                <div className={`${stat.bg} ${stat.color} w-10 h-10 rounded-xl flex items-center justify-center mb-4`}>
                  <stat.icon size={20} />
                </div>
                <div>
                  <p className="text-slate-500 text-xs font-medium uppercase tracking-wider">{stat.label}</p>
                  <p className="text-2xl font-bold text-slate-800 mt-1">{stat.value}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 className="font-bold text-slate-800 mb-6 flex items-center">
                <BarChart3 size={18} className="mr-2 text-blue-600" /> Sentiment Analysis Distribution
              </h3>
              <div className="space-y-6">
                {sentimentData.map((data, i) => (
                  <div key={i}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-semibold text-slate-700 flex items-center">
                        <data.icon size={16} className="mr-2 text-slate-400" /> {data.label} ({data.count} Files)
                      </span>
                      <span className="text-sm font-bold text-slate-800">{data.percentage}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                      <div 
                        className={`${data.color} h-full rounded-full transition-all duration-700 ease-out`} 
                        style={{ width: `${data.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h3 className="font-bold text-slate-800 mb-6 flex items-center">
                <Tag size={18} className="mr-2 text-orange-500" /> Files by Brand
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {brandDistribution.map((brand, i) => (
                  <div key={i} className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center transition-all">
                    <span className="text-sm font-bold text-slate-700 uppercase">{brand.name}</span>
                    <span className="bg-white px-2.5 py-1 rounded-lg border border-slate-200 text-xs font-bold text-blue-600">
                      {brand.count}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-8 p-4 bg-orange-50 rounded-xl border border-orange-100 min-h-[80px] flex items-center transition-all">
                <p className="text-xs text-orange-700 font-medium leading-relaxed">
                  💡 <strong>Summary:</strong> {activeData.insight}
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
