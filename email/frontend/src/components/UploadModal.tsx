"use client";

import { useState } from 'react';
import { Upload, X, Mail, FileText, Loader2, Clipboard } from 'lucide-react';
import { apiFetch } from '@/lib/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [activeTab, setActiveTab] = useState<'upload' | 'paste' | 'manual'>('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual form state
  const [senderName, setSenderName] = useState('');
  const [senderEmail, setSenderEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  // Raw paste state
  const [pastedText, setPastedText] = useState('');

  if (!isOpen) return null;

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const filename = file.name.toLowerCase();
      let endpoint = '/emails/upload';
      if (filename.endsWith('.json') || filename.endsWith('.csv')) {
        endpoint = '/emails/import-file';
      }

      await apiFetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pastedText.trim()) return;

    setLoading(true);
    setError(null);

    // Simple parsing logic for pasted RFC822 or plain text
    let parsedSenderName = 'Sender';
    let parsedSenderEmail = 'sender@example.com';
    let parsedSubject = 'Pasted Email Notice';
    let parsedBody = pastedText.trim();

    const lines = pastedText.split('\n');
    let bodyStartIndex = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) {
        bodyStartIndex = i + 1;
        break;
      }
      if (line.toLowerCase().startsWith('from:')) {
        const val = line.substring(5).trim();
        if (val.includes('<') && val.includes('>')) {
          parsedSenderName = val.split('<')[0].trim().replace(/^"/, '').replace(/"$/, '');
          parsedSenderEmail = val.split('<')[1].replace('>', '').trim();
        } else {
          parsedSenderEmail = val;
          parsedSenderName = val.split('@')[0];
        }
      } else if (line.toLowerCase().startsWith('subject:')) {
        parsedSubject = line.substring(8).trim();
      }
    }

    if (bodyStartIndex > 0 && bodyStartIndex < lines.length) {
      parsedBody = lines.slice(bodyStartIndex).join('\n').trim();
    }

    try {
      await apiFetch('/emails', {
        method: 'POST',
        body: JSON.stringify({
          sender_name: parsedSenderName || 'Raw Email Sender',
          sender_email: parsedSenderEmail || 'raw@example.com',
          subject: parsedSubject || 'Imported Raw Text Email',
          body_plain: parsedBody,
        }),
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to process pasted email');
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiFetch('/emails', {
        method: 'POST',
        body: JSON.stringify({
          sender_name: senderName,
          sender_email: senderEmail,
          subject,
          body_plain: body,
        }),
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <h3 className="font-bold text-slate-900 text-lg">Add New Email for AI Processing</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
            {error}
          </div>
        )}

        <div className="flex border-b border-slate-200 my-4 text-xs font-medium">
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex-1 py-2 text-center border-b-2 transition-colors ${
              activeTab === 'upload'
                ? 'border-sky-500 text-sky-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Upload className="w-3.5 h-3.5 inline mr-1" />
            File Upload (.eml/.json/.csv)
          </button>
          <button
            onClick={() => setActiveTab('paste')}
            className={`flex-1 py-2 text-center border-b-2 transition-colors ${
              activeTab === 'paste'
                ? 'border-sky-500 text-sky-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Clipboard className="w-3.5 h-3.5 inline mr-1" />
            Paste Raw Text
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`flex-1 py-2 text-center border-b-2 transition-colors ${
              activeTab === 'manual'
                ? 'border-sky-500 text-sky-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Mail className="w-3.5 h-3.5 inline mr-1" />
            Manual Form
          </button>
        </div>

        {activeTab === 'upload' && (
          <div className="py-8 border-2 border-dashed border-slate-300 rounded-xl bg-slate-50 text-center hover:bg-slate-100 transition-colors">
            {loading ? (
              <div className="flex flex-col items-center py-4">
                <Loader2 className="w-8 h-8 text-sky-500 animate-spin mb-2" />
                <p className="text-sm font-medium text-slate-700">Analyzing Email with AI...</p>
                <p className="text-xs text-slate-500 mt-1">Classifying intent, summary & extracting metadata</p>
              </div>
            ) : (
              <label className="cursor-pointer flex flex-col items-center p-4">
                <FileText className="w-10 h-10 text-sky-500 mb-2" />
                <span className="text-sm font-bold text-slate-800">Click to upload file</span>
                <span className="text-xs text-slate-500 mt-1">Supports .EML, .JSON, .CSV, or .TXT formats</span>
                <input
                  type="file"
                  accept=".eml,.txt,.json,.csv"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
            )}
          </div>
        )}

        {activeTab === 'paste' && (
          <form onSubmit={handlePasteSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                Paste Raw RFC 822 Header + Body or Plain Text
              </label>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                rows={6}
                placeholder="From: alex@example.com&#10;Subject: Urgent Server Downtime&#10;&#10;Hi support team, our database is down..."
                required
                className="w-full text-xs font-mono border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-sky-500 outline-none"
              />
            </div>
            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-xs font-medium bg-sky-600 hover:bg-sky-500 text-white rounded-lg flex items-center space-x-2"
              >
                {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{loading ? 'Processing...' : 'Parse & Import'}</span>
              </button>
            </div>
          </form>
        )}

        {activeTab === 'manual' && (
          <form onSubmit={handleManualSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Sender Name</label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                required
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-sky-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Sender Email</label>
              <input
                type="email"
                value={senderEmail}
                onChange={(e) => setSenderEmail(e.target.value)}
                required
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-sky-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-sky-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Email Content</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={4}
                required
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-sky-500 outline-none"
              />
            </div>
            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-xs font-medium bg-sky-600 hover:bg-sky-500 text-white rounded-lg flex items-center space-x-2"
              >
                {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{loading ? 'Processing...' : 'Run AI Analysis'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
