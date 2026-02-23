import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Shield, Upload, Info, AlertTriangle, X, Copy, Check } from 'lucide-react';

const logs = [
    { id: 1, type: 'info', action: 'System Init', details: 'BSA Engine v2.4 initialized successfully.', time: '2024-02-16 13:45' },
    { id: 2, type: 'security', action: 'Admin Login', details: 'Successful login from IP 192.168.1.1', time: '2024-02-16 13:40' },
    { id: 3, type: 'upload', action: 'File Processed', details: 'GTBank_Statement.pdf (32 pages) parsed via gtbank_parser', time: '2024-02-16 13:30' },
    { id: 4, type: 'warning', action: 'AI Fallback', details: 'Standard parsing failed on Page 12, switching to Gemini Fallback', time: '2024-02-16 13:25' },
    { id: 5, type: 'info', action: 'Config Change', details: 'GEMINI_API_KEY updated by administrator', time: '2024-02-16 12:50' },
];

const AuditLogView = () => {
    const [rawDataLogId, setRawDataLogId] = useState(null);
    const [copied, setCopied] = useState(false);

    const getIcon = (type) => {
        switch (type) {
            case 'security': return <Shield className="w-4 h-4" />;
            case 'upload': return <Upload className="w-4 h-4" />;
            case 'warning': return <AlertTriangle className="w-4 h-4" />;
            default: return <Info className="w-4 h-4" />;
        }
    };

    const getColor = (type) => {
        switch (type) {
            case 'security': return 'text-primary-400 bg-primary-500/10 border-primary-500/20';
            case 'upload': return 'text-secondary-400 bg-secondary-500/10 border-secondary-500/20';
            case 'warning': return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
            default: return 'text-slate-400 bg-slate-800 border-slate-700';
        }
    };

    const handleRawDataClick = (e, log) => {
        e.preventDefault();
        e.stopPropagation();
        setRawDataLogId(log.id);
        setCopied(false);
    };

    const handleCopyRaw = () => {
        const log = logs.find((l) => l.id === rawDataLogId);
        if (!log) return;
        const raw = JSON.stringify(log, null, 2);
        navigator.clipboard.writeText(raw).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const handleCloseModal = () => setRawDataLogId(null);

    const selectedLog = rawDataLogId ? logs.find((l) => l.id === rawDataLogId) : null;
    const rawJson = selectedLog ? JSON.stringify(selectedLog, null, 2) : '';

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-8"
        >
            <div>
                <h2 className="text-4xl font-black text-white font-outfit">Security Audit Log</h2>
                <p className="text-slate-500 mt-2 font-semibold text-lg">Real-time chronicle of engine activities and administrative actions.</p>
            </div>

            <div className="grid gap-4">
                {logs.map((log) => (
                    <div
                        key={log.id}
                        className="glass-card p-6 rounded-[2rem] border border-slate-800/50 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-primary-500/30 transition-all group"
                    >
                        <div className="flex items-center gap-5">
                            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 border ${getColor(log.type)}`}>
                                {getIcon(log.type)}
                            </div>
                            <div>
                                <div className="flex items-center gap-3 mb-1">
                                    <span className="text-sm font-black text-white uppercase tracking-wider">{log.action}</span>
                                    <span className="text-[10px] font-bold text-slate-600 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-md">
                                        {log.time}
                                    </span>
                                </div>
                                <p className="text-slate-400 text-sm font-medium leading-relaxed">
                                    {log.details}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                            <button
                                type="button"
                                onClick={(e) => handleRawDataClick(e, log)}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-[10px] font-black uppercase text-slate-400 hover:text-white tracking-widest transition-all focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                            >
                                Raw Data
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <AnimatePresence>
                {rawDataLogId && (
                    <>
                        <div
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                            onClick={handleCloseModal}
                            aria-hidden="true"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg max-h-[80vh] z-50 rounded-[2rem] border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden flex flex-col"
                        >
                            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                                <span className="text-sm font-black text-white uppercase tracking-wider">
                                    Raw Data — {selectedLog?.action}
                                </span>
                                <div className="flex items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={handleCopyRaw}
                                        className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-xs font-bold text-slate-300 flex items-center gap-2 transition-colors"
                                    >
                                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                                        {copied ? 'Copied' : 'Copy'}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleCloseModal}
                                        className="p-2 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-white transition-colors"
                                        aria-label="Close"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                            <pre className="p-6 text-xs text-slate-300 font-mono overflow-auto flex-1 whitespace-pre-wrap break-words">
                                {rawJson}
                            </pre>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            <div className="flex justify-center pt-4">
                <button type="button" className="px-8 py-4 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl text-xs font-bold text-slate-500 transition-all flex items-center gap-3">
                    <Terminal className="w-4 h-4" /> Load Extended History
                </button>
            </div>
        </motion.div>
    );
};

export default AuditLogView;
