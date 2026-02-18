import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, Shield, LogIn, Upload, Info, AlertTriangle } from 'lucide-react';

const logs = [
    { id: 1, type: 'info', action: 'System Init', details: 'BSA Engine v2.4 initialized successfully.', time: '2024-02-16 13:45' },
    { id: 2, type: 'security', action: 'Admin Login', details: 'Successful login from IP 192.168.1.1', time: '2024-02-16 13:40' },
    { id: 3, type: 'upload', action: 'File Processed', details: 'GTBank_Statement.pdf (32 pages) parsed via gtbank_parser', time: '2024-02-16 13:30' },
    { id: 4, type: 'warning', action: 'AI Fallback', details: 'Standard parsing failed on Page 12, switching to Gemini Fallback', time: '2024-02-16 13:25' },
    { id: 5, type: 'info', action: 'Config Change', details: 'GEMINI_API_KEY updated by administrator', time: '2024-02-16 12:50' },
];

const AuditLogView = () => {
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
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-[10px] font-black uppercase text-slate-400 tracking-widest transition-all">
                                Raw Data
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="flex justify-center pt-4">
                <button className="px-8 py-4 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl text-xs font-bold text-slate-500 transition-all flex items-center gap-3">
                    <Terminal className="w-4 h-4" /> Load Extended History
                </button>
            </div>
        </motion.div>
    );
};

export default AuditLogView;
