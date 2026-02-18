import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Zap, Cpu } from 'lucide-react';

const UnusualDepositsTable = ({ deposits }) => {
    const getCategoryTheme = (category) => {
        const themes = {
            'Salary': 'bg-primary-500/10 text-primary-400 border-primary-500/20 shadow-primary-500/5',
            'Business Income': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-500/5',
            'Loan': 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-amber-500/5',
            'Gift': 'bg-purple-500/10 text-purple-400 border-purple-500/20 shadow-purple-500/5',
            'Refund': 'bg-blue-500/10 text-blue-400 border-blue-500/20 shadow-blue-500/5',
            'Unknown': 'bg-slate-800 text-slate-400 border-slate-700 shadow-none'
        };
        return themes[category] || themes['Unknown'];
    };

    return (
        <div className="glass-card rounded-[2rem] border border-slate-800/50 overflow-hidden shadow-2xl shadow-black/40">
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-900/80 border-b border-slate-800/50">
                            <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Audit Info</th>
                            <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] text-right">Value</th>
                            <th className="px-6 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">AI Intelligence</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                        {deposits.length === 0 ? (
                            <tr>
                                <td colSpan="3" className="px-6 py-20 text-center">
                                    <div className="flex flex-col items-center gap-4">
                                        <div className="w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center border border-slate-800">
                                            <ShieldAlert className="w-8 h-8 text-slate-600" />
                                        </div>
                                        <p className="text-slate-500 font-bold uppercase text-[10px] tracking-[0.3em]">No Risk Signals Detected</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            deposits.map((row, idx) => (
                                <motion.tr
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    key={idx}
                                    className="hover:bg-amber-500/[0.02] transition-colors group"
                                >
                                    <td className="px-6 py-6">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">{row.Date}</span>
                                            <span className="text-sm font-bold text-white max-w-[140px] truncate leading-tight group-hover:text-primary-400 transition-colors" title={row.Description}>
                                                {row.Description}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-6 text-sm text-white text-right font-mono font-black tracking-tighter">
                                        <span className="text-xs mr-0.5 opacity-50">₦</span>
                                        {new Intl.NumberFormat().format(row.Amount)}
                                    </td>
                                    <td className="px-6 py-6">
                                        <div className="flex flex-col gap-2">
                                            <span className={`px-3 py-1.5 rounded-xl text-[10px] font-black border flex items-center gap-1.5 w-fit shadow-lg ${getCategoryTheme(row.Category)}`}>
                                                <Cpu className="w-3 h-3" />
                                                {row.Category}
                                            </span>
                                        </div>
                                    </td>
                                </motion.tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            <div className="bg-slate-900/50 p-6 flex items-center justify-between border-t border-slate-800/40">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em]">Neural Classification Active</span>
                </div>
            </div>
        </div>
    );
};

export default UnusualDepositsTable;
