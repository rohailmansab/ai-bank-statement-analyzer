import React from 'react';
import { DollarSign, ArrowUpRight, ArrowDownRight, Wallet, BadgePercent, Target } from 'lucide-react';
import { motion } from 'framer-motion';

const SummaryCards = ({ totals }) => {
    const cards = [
        {
            title: 'Monthly Revenue',
            label: 'Average Inflow',
            value: totals.average_income,
            icon: ArrowUpRight,
            color: 'from-emerald-600 to-emerald-400',
            shadow: 'shadow-emerald-500/20',
            text: 'text-emerald-400'
        },
        {
            title: 'Monthly Expenditure',
            label: 'Average Outflow',
            value: totals.average_expense,
            icon: ArrowDownRight,
            color: 'from-rose-600 to-rose-400',
            shadow: 'shadow-rose-500/20',
            text: 'text-rose-400'
        },
        {
            title: 'Capital Reserves',
            label: 'Disposable Balance',
            value: totals.average_income - totals.average_expense,
            icon: Wallet,
            color: 'from-primary-600 to-primary-400',
            shadow: 'shadow-primary-500/20',
            text: 'text-primary-400'
        }
    ];

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full">
            {cards.map((card, idx) => (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={idx}
                    className="glass-card rounded-[2rem] p-8 border border-slate-800/50 shadow-2xl relative overflow-hidden group hover:border-primary-500/30 transition-all duration-500"
                >
                    <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${card.color} opacity-[0.03] rounded-bl-[100px] -mr-8 -mt-8 transition-all group-hover:scale-110 group-hover:opacity-[0.08]`} />

                    <div className="flex flex-col gap-6 relative z-10">
                        <div className="flex justify-between items-start">
                            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${card.color} flex items-center justify-center shadow-lg ${card.shadow} group-hover:scale-110 transition-transform duration-500`}>
                                <card.icon className="w-7 h-7 text-white" />
                            </div>
                            <div className="text-right">
                                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{card.title}</span>
                                <p className={`text-xs font-bold mt-1 ${card.text}`}>{card.label}</p>
                            </div>
                        </div>

                        <div>
                            <div className="flex items-baseline gap-1">
                                <span className="text-xl font-black text-slate-500 font-outfit leading-none mb-1">₦</span>
                                <h4 className="text-4xl font-black text-white font-outfit tracking-tighter transition-all group-hover:scale-[1.02] transform origin-left">
                                    {new Intl.NumberFormat().format(card.value)}
                                </h4>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-slate-800/40">
                            <div className="w-1.5 h-1.5 rounded-full bg-slate-700 animate-pulse" />
                            <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-widest leading-none">Real-time Verified</span>
                        </div>
                    </div>
                </motion.div>
            ))}
        </div>
    );
};

export default SummaryCards;
