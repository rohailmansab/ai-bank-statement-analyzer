import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Eye, Calendar, Database } from 'lucide-react';

const reports = [
    { id: 1, name: 'GTBank_Statement_Jan.pdf', date: '2024-02-15', status: 'Success', size: '1.2 MB' },
    { id: 2, name: 'Access_Savings_Feb.xlsx', date: '2024-02-10', status: 'Success', size: '450 KB' },
    { id: 3, name: 'StandardChartered_Report.csv', date: '2024-01-28', status: 'Success', size: '200 KB' },
    { id: 4, name: 'UBA_Statement_2023.pdf', date: '2023-12-15', status: 'Processed', size: '2.5 MB' },
];

const ReportsView = () => {
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
                                        <button className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors">
                                            <Eye className="w-4 h-4 text-slate-400" />
                                        </button>
                                        <button className="p-2.5 bg-primary-500/10 hover:bg-primary-500/20 rounded-xl transition-colors">
                                            <Download className="w-4 h-4 text-primary-400" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </motion.div>
    );
};

export default ReportsView;
