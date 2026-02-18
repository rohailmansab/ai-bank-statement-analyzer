import React from 'react';
import { motion } from 'framer-motion';

const MonthlySummaryTable = ({ summary }) => {
    return (
        <div className="glass-card rounded-3xl overflow-hidden shadow-2xl shadow-black/40 border border-slate-800/50">
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-900/80 border-b border-slate-800/50">
                            <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Transaction Period</th>
                            <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] text-right">Income (Credits)</th>
                            <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] text-right">Expenses (Debits)</th>
                            <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] text-right">Net Liquidity</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                        {summary?.map((row, idx) => {
                            const net = row.income - row.expenses;
                            return (
                                <motion.tr
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    key={idx}
                                    className="hover:bg-primary-500/[0.03] transition-colors group"
                                >
                                    <td className="px-8 py-6 text-sm font-bold text-white group-hover:text-primary-400 transition-colors font-outfit uppercase tracking-tighter">
                                        {row.month}
                                    </td>
                                    <td className="px-8 py-6 text-sm text-emerald-400 text-right font-mono font-bold tracking-tight">
                                        <span className="opacity-50 text-[10px] mr-1">₦</span>
                                        {new Intl.NumberFormat().format(row.income)}
                                    </td>
                                    <td className="px-8 py-6 text-sm text-rose-400 text-right font-mono font-bold tracking-tight">
                                        <span className="opacity-50 text-[10px] mr-1">₦</span>
                                        {new Intl.NumberFormat().format(row.expenses)}
                                    </td>
                                    <td className={`px-8 py-6 text-sm text-right font-black font-mono tracking-tight ${net >= 0 ? 'text-primary-400' : 'text-amber-500 bg-amber-500/5'}`}>
                                        <span className="opacity-40 text-[10px] mr-1">{net >= 0 ? '+' : ''}₦</span>
                                        {new Intl.NumberFormat().format(net)}
                                    </td>
                                </motion.tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            <div className="bg-slate-900/30 px-8 py-4 border-t border-slate-800/50">
                <p className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.2em]">Data verified by BSA Core Algorithm</p>
            </div>
        </div>
    );
};

export default MonthlySummaryTable;
