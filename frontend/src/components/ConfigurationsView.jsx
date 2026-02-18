import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Key, Sliders, Bell, Save, RefreshCw, Cpu } from 'lucide-react';

const ConfigurationsView = () => {
    const [config, setConfig] = useState({
        geminiKey: 'AIzaSyBHjP...0VrE',
        openaiKey: 'sk-proj-...kfkWMAA',
        threshold: '50000',
        engineMode: 'hybrid',
        autoClassification: true
    });

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-10"
        >
            <div>
                <h2 className="text-4xl font-black text-white font-outfit tracking-tight leading-tight">System Configurations</h2>
                <p className="text-slate-500 mt-2 font-semibold">Tweak engine parameters and managed cloud API integration.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* AI Credentials Card */}
                <div className="glass-card p-10 rounded-[3rem] border border-slate-800/50 space-y-8">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-primary-500/10 rounded-2xl">
                            <Key className="w-6 h-6 text-primary-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white">AI Cloud Services</h3>
                    </div>

                    <div className="space-y-6">
                        <div>
                            <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3">Google Gemini API Key</label>
                            <div className="relative">
                                <input
                                    type="password"
                                    value={config.geminiKey}
                                    className="w-full bg-[#020617] border border-slate-800 rounded-2xl px-5 py-4 text-slate-300 text-sm focus:border-primary-500/50 transition-all font-mono"
                                />
                                <button className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-slate-600 hover:text-primary-400">
                                    <RefreshCw className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3">OpenAI API Key</label>
                            <input
                                type="password"
                                value={config.openaiKey}
                                className="w-full bg-[#020617] border border-slate-800 rounded-2xl px-5 py-4 text-slate-300 text-sm focus:border-primary-500/50 transition-all font-mono"
                            />
                        </div>
                    </div>
                </div>

                {/* Extraction Parameters */}
                <div className="glass-card p-10 rounded-[3rem] border border-slate-800/50 space-y-8">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-secondary-500/10 rounded-2xl">
                            <Sliders className="w-6 h-6 text-secondary-400" />
                        </div>
                        <h3 className="text-xl font-bold text-white">Engine Optimization</h3>
                    </div>

                    <div className="space-y-6">
                        <div>
                            <label className="block text-xs font-black text-slate-500 uppercase tracking-widest mb-3">Unusual Deposit Threshold (NGN)</label>
                            <input
                                type="number"
                                value={config.threshold}
                                className="w-full bg-[#020617] border border-slate-800 rounded-2xl px-5 py-4 text-slate-300 text-sm focus:border-primary-500/50 transition-all font-bold"
                            />
                        </div>

                        <div className="flex items-center justify-between p-5 bg-slate-900/50 rounded-2xl border border-slate-800">
                            <div>
                                <div className="text-sm font-bold text-white">Auto-Classification</div>
                                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">AI-Enhanced Categorization</div>
                            </div>
                            <div className="w-12 h-6 bg-primary-600 rounded-full relative cursor-pointer">
                                <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex items-center justify-between p-8 glass-card rounded-[2.5rem] border border-slate-800/50 bg-primary-500/5 shadow-2xl shadow-primary-500/5">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-primary-500/10 rounded-2xl flex items-center justify-center">
                        <Cpu className="w-6 h-6 text-primary-400" />
                    </div>
                    <div>
                        <div className="text-lg font-black text-white font-outfit">Ready to Synchronize?</div>
                        <p className="text-slate-500 text-sm font-medium">Changes will take effect after engine hot-reload.</p>
                    </div>
                </div>
                <button className="h-14 px-8 bg-gradient-to-r from-primary-600 to-primary-500 hover:shadow-primary-500/20 shadow-xl rounded-2xl text-sm font-black text-white flex items-center gap-3 transition-all hover:scale-105 active:scale-95">
                    <Save className="w-5 h-5" /> Commit Changes
                </button>
            </div>
        </motion.div>
    );
};

export default ConfigurationsView;
