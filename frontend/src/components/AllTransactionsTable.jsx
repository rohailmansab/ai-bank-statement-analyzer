import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { List, ChevronDown, ChevronUp } from 'lucide-react';

const AllTransactionsTable = ({ transactions }) => {
    const [showAll, setShowAll] = useState(false);
    const list = transactions || [];
    const displayList = showAll ? list : list.slice(0, 50);
    const hasMore = list.length > 50;

    const fmtNum = (x) => {
        if (x == null || x === '') return '0.00';
        const n = typeof x === 'number' ? x : parseFloat(String(x).replace(/,/g, ''));
        return Number.isNaN(n) ? '0.00' : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    return (
        <div className="glass-card rounded-[2rem] border border-slate-800/50 overflow-hidden shadow-2xl shadow-black/40">
            <div className="px-6 py-5 border-b border-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <List className="w-6 h-6 text-primary-400" />
                    <h3 className="text-lg font-black text-white font-outfit tracking-tight">All Transactions</h3>
                </div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                    {list.length} transaction{list.length !== 1 ? 's' : ''} extracted
                </span>
            </div>
            <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-slate-900/95 backdrop-blur z-10">
                        <tr className="border-b border-slate-800/50">
                            <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Date</th>
                            <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest min-w-[200px]">Description</th>
                            <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right whitespace-nowrap">Debit (₦)</th>
                            <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right whitespace-nowrap">Credit (₦)</th>
                            <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right whitespace-nowrap">Balance (₦)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                        {displayList.length === 0 ? (
                            <tr>
                                <td colSpan="5" className="px-6 py-16 text-center text-slate-500 font-semibold">
                                    No transactions in this statement.
                                </td>
                            </tr>
                        ) : (
                            displayList.map((row, idx) => (
                                <motion.tr
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: Math.min(idx * 0.02, 0.3) }}
                                    key={idx}
                                    className="hover:bg-slate-800/30 transition-colors"
                                >
                                    <td className="px-6 py-4 text-sm font-semibold text-slate-300 whitespace-nowrap">{row.date || '—'}</td>
                                    <td className="px-6 py-4 text-sm text-slate-400" title={row.description}>
                                        <span className="line-clamp-2">{row.description || '—'}</span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-right font-mono text-rose-400/90">{fmtNum(row.debit)}</td>
                                    <td className="px-6 py-4 text-sm text-right font-mono text-emerald-400/90">{fmtNum(row.credit)}</td>
                                    <td className="px-6 py-4 text-sm text-right font-mono text-slate-300">{row.balance != null ? fmtNum(row.balance) : '—'}</td>
                                </motion.tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            {hasMore && (
                <div className="border-t border-slate-800/50 px-6 py-4 flex justify-center">
                    <button
                        type="button"
                        onClick={() => setShowAll(!showAll)}
                        className="flex items-center gap-2 px-5 py-2.5 bg-slate-800/80 hover:bg-slate-700/80 rounded-xl text-sm font-bold text-slate-300 transition-colors"
                    >
                        {showAll ? (
                            <>
                                <ChevronUp className="w-4 h-4" />
                                Show less
                            </>
                        ) : (
                            <>
                                <ChevronDown className="w-4 h-4" />
                                Show all {list.length} transactions
                            </>
                        )}
                    </button>
                </div>
            )}
        </div>
    );
};

export default AllTransactionsTable;
