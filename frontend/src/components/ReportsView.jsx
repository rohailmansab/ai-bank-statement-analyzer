import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, Calendar, Database } from 'lucide-react';

const ReportsView = ({ reports = [], onViewReport, onDownloadReport }) => {
    const handleView = (e, report) => {
        e.preventDefault();
        e.stopPropagation();
        if (typeof onViewReport === 'function') onViewReport(report);
    };

    const handleDownload = (e, report) => {
        e.preventDefault();
        e.stopPropagation();
        if (typeof onDownloadReport === 'function') onDownloadReport(report);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
        >
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-4xl font-black text-white font-outfit">Extraction Reports</h2>
                    <p className="text-slate-500 mt-2 font-semibold">History of all successfully analyzed documents.</p>
                </div>
                <div className="px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs font-bold text-slate-400 flex items-center gap-2">
                    <Database className="w-4 h-4" /> {reports.length} Total Records
                </div>
            </div>

            <div className="glass-card rounded-[2.5rem] overflow-hidden border border-slate-800/50">
                {reports.length === 0 ? (
                    <div className="px-8 py-16 text-center">
                        <FileText className="w-14 h-14 text-slate-600 mx-auto mb-4" />
                        <p className="text-slate-500 font-semibold">No reports yet</p>
                        <p className="text-slate-600 text-sm mt-1">Analyze a bank statement from Overview to see it here.</p>
                    </div>
                ) : (
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-900/50">
                                <th className="px-8 py-6 text-xs font-black uppercase tracking-widest text-slate-500 border-b border-slate-800/50">File Name</th>
                                <th className="px-8 py-6 text-xs font-black uppercase tracking-widest text-slate-500 border-b border-slate-800/50">Date</th>
                                <th className="px-8 py-6 text-xs font-black uppercase tracking-widest text-slate-500 border-b border-slate-800/50">Status</th>
                                <th className="px-8 py-6 text-xs font-black uppercase tracking-widest text-slate-500 border-b border-slate-800/50 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/30">
                            {reports.map((report) => (
                                <tr key={report.id} className="group hover:bg-primary-500/5 transition-colors">
                                    <td className="px-8 py-6">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center group-hover:bg-primary-500/20 transition-colors">
                                                <FileText className="w-5 h-5 text-slate-400 group-hover:text-primary-400" />
                                            </div>
                                            <div>
                                                <div className="text-sm font-bold text-white mb-0.5">{report.name}</div>
                                                <div className="text-[10px] font-bold text-slate-600 uppercase tracking-tighter">{report.size}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-8 py-6">
                                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-400">
                                            <Calendar className="w-4 h-4 text-slate-600" />
                                            {report.date}
                                        </div>
                                    </td>
                                    <td className="px-8 py-6">
                                        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-black uppercase tracking-widest rounded-lg border border-emerald-500/20">
                                            {report.status}
                                        </span>
                                    </td>
                                    <td className="px-8 py-6 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <button
                                                type="button"
                                                onClick={(e) => handleView(e, report)}
                                                className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                                title="View report"
                                            >
                                                <Eye className="w-4 h-4 text-slate-400" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={(e) => handleDownload(e, report)}
                                                className="p-2.5 bg-primary-500/10 hover:bg-primary-500/20 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                                title="Download report"
                                            >
                                                <Download className="w-4 h-4 text-primary-400" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </motion.div>
    );
};

export default ReportsView;
