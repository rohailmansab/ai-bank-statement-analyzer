import React, { useRef } from 'react';
import { Upload, File, HelpCircle, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../services/api';

const FileUpload = ({ onSuccess, onError, setLoading, loading }) => {
    const fileInputRef = useRef(null);

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        try {
            const response = await api.post('/analyze-statement', formData);
            onSuccess(response.data);
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Extraction failed. Please verify the bank statement format.';
            console.error('File Upload Error:', err);
            onError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full">
            <motion.div
                whileHover={!loading ? { scale: 1.01 } : {}}
                onClick={() => !loading && fileInputRef.current?.click()}
                className={`
          relative group cursor-pointer overflow-hidden
          ${loading ? 'cursor-not-allowed opacity-80' : ''}
        `}
            >
                <div className={`
          absolute inset-0 bg-gradient-to-br from-primary-500/10 to-transparent transition-opacity duration-300
          ${loading ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
        `} />

                <div className={`
          relative border-2 border-dashed rounded-[2.5rem] p-16 text-center transition-all duration-300 glass-card
          ${loading ? 'border-primary-500/40 bg-slate-900/60' : 'border-slate-800 hover:border-primary-500/50 hover:bg-slate-900/30 shadow-none hover:shadow-2xl hover:shadow-primary-500/10'}
        `}>
                    <input
                        type="file"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".pdf,.csv,.xlsx,.xls"
                    />

                    <div className="flex flex-col items-center">
                        <div className={`
              w-24 h-24 rounded-[2rem] flex items-center justify-center mb-8 transition-all duration-500 relative
              ${loading ? 'bg-primary-500/20 scale-110 shadow-2xl shadow-primary-500/20' : 'bg-slate-800 group-hover:bg-primary-600 group-hover:rotate-6 group-hover:scale-110 shadow-xl shadow-black/50'}
            `}>
                            {loading ? (
                                <>
                                    <div className="absolute inset-0 rounded-[2rem] border-4 border-primary-500 border-t-transparent animate-spin" />
                                    <File className="w-10 h-10 text-primary-400" />
                                </>
                            ) : (
                                <Upload className={`w-10 h-10 transition-colors duration-300 ${loading ? 'text-primary-400' : 'text-slate-400 group-hover:text-white'}`} />
                            )}
                        </div>

                        <h3 className="text-2xl font-black text-white mb-3 font-outfit tracking-tight">
                            {loading ? 'Initializing Deep Scan...' : 'Drop Statement Here'}
                        </h3>
                        <p className="text-slate-500 text-base max-w-xs mx-auto leading-relaxed font-semibold">
                            PDF, CSV, or Excel accepted. <br />
                            <span className="text-primary-500/80 uppercase text-[10px] tracking-[0.2em] font-black mt-4 block">Secure Extraction Interface</span>
                        </p>
                    </div>
                </div>
            </motion.div>

            <div className="mt-8 flex items-center justify-center gap-8 py-4 opacity-50">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-widest leading-none">
                    <ShieldCheck className="w-4 h-4" /> Encrypted
                </div>
                <div className="w-1 h-1 bg-slate-700 rounded-full" />
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-widest leading-none">
                    <HelpCircle className="w-4 h-4" /> OCR Optimized
                </div>
            </div>
        </div>
    );
};

export default FileUpload;
