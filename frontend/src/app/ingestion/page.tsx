"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

interface DocumentMetadata {
  id: number;
  filename: string;
  status: string;
  created_at: string;
}

export default function IngestionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [history, setHistory] = useState<DocumentMetadata[]>([]);
  const [message, setMessage] = useState('');
  const [rawText, setRawText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'raw'>('upload');
  
  // Pagination state
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 10;

  const fetchHistory = useCallback(async () => {
    try {
      const offset = (page - 1) * limit;
      const response = await api.get(`/api/ingest/history?limit=${limit}&offset=${offset}`);
      setHistory(response.data.items);
      setTotal(response.data.total);
    } catch (err) {
      console.error("Failed to fetch ingestion history");
    }
  }, [page]);

  useEffect(() => {
    fetchHistory();

    // SSE for real-time updates
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/ingest/events`, {
      withCredentials: true
    });

    eventSource.addEventListener('update', (event) => {
      const data = JSON.parse(event.data);
      setHistory(prev => {
        const index = prev.findIndex(item => item.id === data.id);
        if (index !== -1) {
          const newHistory = [...prev];
          newHistory[index] = { ...newHistory[index], status: data.status };
          return newHistory;
        } else {
          return [data, ...prev];
        }
      });
    });

    eventSource.onerror = (err) => {
      console.error("SSE Connection Error:", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage('');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/api/ingest/upload-contract', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage('Document uploaded successfully and queued for analysis.');
      setFile(null);
      fetchHistory();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleRawSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;

    setAnalyzing(true);
    setMessage('');
    try {
      await api.post('/api/ingest/analyze-raw-text', { text: rawText });
      setMessage('Text analyzed successfully.');
      setRawText('');
      fetchHistory();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="flex space-x-4 mb-8">
        <button 
          onClick={() => setActiveTab('upload')}
          className={cn(
            "px-6 py-2 rounded-xl text-sm font-semibold transition-all",
            activeTab === 'upload' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "bg-white/5 text-slate-400 hover:bg-white/10"
          )}
        >
          PDF Upload
        </button>
        <button 
          onClick={() => setActiveTab('raw')}
          className={cn(
            "px-6 py-2 rounded-xl text-sm font-semibold transition-all",
            activeTab === 'raw' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "bg-white/5 text-slate-400 hover:bg-white/10"
          )}
        >
          Raw Text Analysis
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          {activeTab === 'upload' ? (
            <>
              <h3 className="text-xl font-bold mb-6">Contract Ingestion</h3>
              <form onSubmit={handleUpload} className="glass p-8 rounded-3xl border-2 border-dashed border-[#1e293b] hover:border-blue-500/50 transition-all text-center">
                <div className="flex flex-col items-center">
                  <div className="w-16 h-16 bg-blue-600/10 rounded-2xl flex items-center justify-center text-blue-500 mb-4">
                    <Upload size={32} />
                  </div>
                  <h4 className="text-lg font-semibold">Upload PDF Contract</h4>
                  <p className="text-slate-400 text-sm mt-2 mb-6">Drag and drop your file here, or click to browse</p>
                  
                  <input 
                    type="file" 
                    accept=".pdf" 
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden" 
                    id="file-upload"
                  />
                  <label 
                    htmlFor="file-upload"
                    className="px-6 py-3 bg-[#1e293b] hover:bg-[#2d3a4f] text-white rounded-xl text-sm font-semibold cursor-pointer transition-all inline-block"
                  >
                    {file ? file.name : 'Select File'}
                  </label>

                  {file && (
                    <button
                      type="submit"
                      disabled={uploading}
                      className="mt-6 w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold shadow-lg shadow-blue-500/20 flex items-center justify-center space-x-2 disabled:opacity-50"
                    >
                      {uploading ? <Loader2 className="animate-spin" size={20} /> : <FileText size={20} />}
                      <span>{uploading ? 'Processing...' : 'Start Extraction'}</span>
                    </button>
                  )}
                </div>
              </form>
            </>
          ) : (
            <>
              <h3 className="text-xl font-bold mb-6">Raw Text Analysis</h3>
              <form onSubmit={handleRawSubmit} className="glass p-6 rounded-3xl border border-[#1e293b]">
                <textarea 
                  className="w-full h-64 bg-[#0d0d0f] border border-[#1e293b] rounded-2xl p-4 text-sm focus:border-blue-500 outline-none transition-all mb-4 font-mono"
                  placeholder="Paste text prefixed with [TYPE: CONTRACT_PDF] or [TYPE: NEWS_FEED]..."
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={analyzing}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold shadow-lg shadow-blue-500/20 flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {analyzing ? <Loader2 className="animate-spin" size={20} /> : <FileText size={20} />}
                  <span>{analyzing ? 'Analyzing...' : 'Execute Analysis'}</span>
                </button>
              </form>
            </>
          )}

          {message && (
            <p className={cn(
              "mt-4 text-sm font-medium p-4 rounded-xl",
              message.includes('success') || message.includes('successfully') ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
            )}>
              {message}
            </p>
          )}
        </div>

        <div>
          <h3 className="text-xl font-bold mb-6">Ingestion History</h3>
          <div className="glass rounded-3xl overflow-hidden border border-[#1e293b]">
            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-left">
                <thead className="bg-[#111113] border-b border-[#1e293b]">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Resource</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]">
                  {history.map((doc) => (
                    <tr key={doc.id} className="hover:bg-white/[0.02] transition-all">
                      <td className="px-6 py-4 font-medium truncate max-w-[150px]">{doc.filename || "Raw Text"}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-2">
                          {doc.status === 'processed' ? (
                            <CheckCircle size={16} className="text-emerald-500" />
                          ) : doc.status === 'failed' ? (
                            <XCircle size={16} className="text-red-500" />
                          ) : (
                            <Loader2 size={16} className="text-blue-500 animate-spin" />
                          )}
                          <span className={cn(
                            "text-xs font-bold uppercase",
                            doc.status === 'processed' ? "text-emerald-500" :
                            doc.status === 'failed' ? "text-red-500" : "text-blue-500"
                          )}>
                            {doc.status}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">
                        {new Date(doc.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                  {history.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-6 py-12 text-center text-slate-500">
                        No ingestion records found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Pagination Controls */}
            {total > limit && (
              <div className="bg-[#111113] border-t border-[#1e293b] px-6 py-4 flex items-center justify-between">
                <div className="text-xs text-slate-500">
                  Showing <span className="text-white">{(page - 1) * limit + 1}</span> to <span className="text-white">{Math.min(page * limit, total)}</span> of <span className="text-white">{total}</span>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 bg-[#1e293b] hover:bg-[#2d3a4f] text-white rounded-lg disabled:opacity-30 transition-all"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(Math.ceil(total / limit), p + 1))}
                    disabled={page >= Math.ceil(total / limit)}
                    className="p-2 bg-[#1e293b] hover:bg-[#2d3a4f] text-white rounded-lg disabled:opacity-30 transition-all"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
