"use client";

import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';
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

  const fetchHistory = async () => {
    try {
      // Assuming we have an endpoint for this (or we need to add it)
      // For now, let's assume get /api/ingest/history exists or we'll add a helper
      const response = await api.get('/api/ingest/history');
      setHistory(response.data);
    } catch (err) {
      console.error("Failed to fetch ingestion history");
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000); // Poll for status changes
    return () => clearInterval(interval);
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

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
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

            {message && (
              <p className={cn(
                "mt-4 text-sm font-medium",
                message.includes('success') ? "text-emerald-500" : "text-red-500"
              )}>
                {message}
              </p>
            )}
          </form>
        </div>

        <div>
          <h3 className="text-xl font-bold mb-6">Ingestion History</h3>
          <div className="glass rounded-3xl overflow-hidden border border-[#1e293b]">
            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-left">
                <thead className="bg-[#111113] border-b border-[#1e293b]">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Filename</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Uploaded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]">
                  {history.map((doc) => (
                    <tr key={doc.id} className="hover:bg-white/[0.02] transition-all">
                      <td className="px-6 py-4 font-medium">{doc.filename}</td>
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
                        {new Date(doc.created_at).toLocaleString()}
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
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
