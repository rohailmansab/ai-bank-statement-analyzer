import React, { useState, useEffect } from 'react';
import { LogOut, Upload, FileText, FileDown, AlertCircle, Download, BarChart3, LayoutDashboard, Settings, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';
import { downloadReportAsPdf } from '../utils/pdfExport';
import SummaryCards from '../components/SummaryCards';
import MonthlySummaryTable from '../components/MonthlySummaryTable';
import UnusualDepositsTable from '../components/UnusualDepositsTable';
import FileUpload from '../components/FileUpload';
import ReportsView from '../components/ReportsView';
import AuditLogView from '../components/AuditLogView';
import ConfigurationsView from '../components/ConfigurationsView';

const REPORTS_STORAGE_KEY = 'bsa_report_history';

const getStoredReports = () => {
    try {
        const raw = localStorage.getItem(REPORTS_STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
};

const Dashboard = ({ onLogout }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('overview');
    const [reportHistory, setReportHistory] = useState([]);

    useEffect(() => {
        setReportHistory(getStoredReports());
    }, []);

    const saveReportHistory = (next) => {
        setReportHistory(next);
        try {
            localStorage.setItem(REPORTS_STORAGE_KEY, JSON.stringify(next));
        } catch (e) {
            console.warn('Could not save report history', e);
        }
    };

    const handleUploadSuccess = (result) => {
        setData(result);
        setError('');
        setActiveTab('overview');
        const name = result?.filename || 'Statement';
        const size = (result?.metadata?.total_transactions != null)
            ? `${String(Math.round(JSON.stringify(result).length / 1024))} KB`
            : '—';
        const entry = {
            id: Date.now(),
            name,
            date: new Date().toISOString().slice(0, 10),
            status: 'Success',
            size,
            fullReport: result,
        };
        const next = [entry, ...getStoredReports()].slice(0, 50);
        saveReportHistory(next);
    };

    const downloadReport = (reportData = data) => {
        if (!reportData) return;
        const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BSA_Report_${reportData.filename || 'report'}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const [pdfLoading, setPdfLoading] = useState(false);
    const downloadPdfReport = (reportData = data) => {
        if (!reportData) return;
        setPdfLoading(true);
        setError('');
        try {
            const name = (reportData.filename || 'BSA_Report').replace(/\s+/g, '_');
            downloadReportAsPdf(reportData, name.endsWith('.pdf') ? name : `${name}.pdf`);
        } catch (err) {
            console.error('PDF export failed', err);
            setError(err?.message || 'PDF export failed');
        } finally {
            setPdfLoading(false);
        }
    };

    const handleViewReport = (report) => {
        if (report?.fullReport) {
            setData(report.fullReport);
            setActiveTab('overview');
        }
    };

    const handleDownloadReport = (report) => {
        if (report?.fullReport) {
            downloadReport(report.fullReport);
        }
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'reports':
                return (
                    <ReportsView
                        reports={reportHistory}
                        onViewReport={handleViewReport}
                        onDownloadReport={handleDownloadReport}
                    />
                );
            case 'audit':
                return <AuditLogView />;
            case 'config':
                return <ConfigurationsView />;
            default:
                return !data ? (
                    <motion.div
                        key="upload"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="max-w-2xl mx-auto mt-8 xl:mt-20"
                    >
                        <div className="text-center mb-10">
                            <div className="inline-block p-4 bg-primary-500/10 rounded-3xl mb-6">
                                <Upload className="w-10 h-10 text-primary-500" />
                            </div>
                            <h2 className="text-4xl font-black text-white font-outfit tracking-tight leading-tight">
                                Financial Analysis <br /> Engine
                            </h2>
                            <p className="text-slate-500 mt-4 text-lg font-medium max-w-sm mx-auto leading-relaxed">
                                Upload your digital bank statement (PDF, Excel, or CSV) for instant verification.
                            </p>
                        </div>

                        <FileUpload
                            onSuccess={handleUploadSuccess}
                            onError={setError}
                            setLoading={setLoading}
                            loading={loading}
                        />

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mt-6 p-5 bg-rose-500/10 border border-rose-500/20 rounded-3xl text-rose-400 flex items-center gap-4 shadow-xl shadow-rose-500/5"
                            >
                                <div className="w-10 h-10 bg-rose-500/10 rounded-xl flex items-center justify-center flex-shrink-0">
                                    <AlertCircle className="w-5 h-5" />
                                </div>
                                <p className="text-sm font-bold">{error}</p>
                            </motion.div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="dashboard"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-10"
                    >
                        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                            <div>
                                <div className="flex items-center gap-3 text-primary-400 mb-2">
                                    <div className="px-2.5 py-1 bg-primary-500/10 border border-primary-500/20 rounded-lg text-xs font-bold uppercase tracking-widest">
                                        Verified Analysis
                                    </div>
                                </div>
                                <h2 className="text-4xl font-black text-white font-outfit">Financial Summary</h2>
                                <p className="text-slate-500 mt-2 font-semibold italic flex items-center gap-2">
                                    <FileText className="w-4 h-4" />
                                    Dataset: {data.filename}
                                </p>
                                <p className="text-slate-600 mt-1 text-xs font-medium">
                                    All calculations and figures are from this uploaded statement only.
                                </p>
                            </div>
                            <div className="flex flex-wrap gap-4 w-full md:w-auto">
                                <button
                                    onClick={() => setData(null)}
                                    className="flex-1 md:flex-none h-14 px-6 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-2xl text-sm font-bold transition-all flex items-center justify-center gap-3 text-slate-300"
                                >
                                    <Upload className="w-4 h-4" />
                                    Deep Scan New
                                </button>
                                <button
                                    onClick={() => downloadReport()}
                                    className="flex-1 md:flex-none h-14 px-6 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-2xl text-sm font-bold transition-all flex items-center justify-center gap-3 text-slate-300"
                                >
                                    <Download className="w-4 h-4" />
                                    Export JSON
                                </button>
                                <button
                                    onClick={() => downloadPdfReport()}
                                    disabled={pdfLoading}
                                    className="flex-1 md:flex-none h-14 px-8 bg-gradient-to-r from-primary-600 to-primary-500 hover:shadow-primary-500/20 shadow-xl rounded-2xl text-sm font-bold transition-all flex items-center justify-center gap-3 text-white disabled:opacity-70"
                                >
                                    <FileDown className="w-4 h-4" />
                                    {pdfLoading ? 'Generating…' : 'Export as PDF'}
                                </button>
                            </div>
                        </div>

                        <SummaryCards totals={data.totals} />

                        <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
                            <div className="xl:col-span-7 space-y-6">
                                <div className="flex items-center justify-between px-2">
                                    <div className="flex items-center gap-3">
                                        <BarChart3 className="w-6 h-6 text-primary-400" />
                                        <h3 className="text-xl font-black text-white font-outfit tracking-tight">Financial Summary: Monthly Performance</h3>
                                    </div>
                                    <div className="bg-slate-900/50 p-1 rounded-xl border border-slate-800">
                                        <div className="px-3 py-1 text-[10px] font-black uppercase text-slate-500 tracking-tighter">Section 1 Output</div>
                                    </div>
                                </div>
                                <MonthlySummaryTable summary={data.monthly_summary} />
                            </div>

                            <div className="xl:col-span-5 space-y-6">
                                <div className="flex items-center justify-between px-2">
                                    <div className="flex items-center gap-3">
                                        <AlertCircle className="w-6 h-6 text-amber-500" />
                                        <h3 className="text-xl font-black text-white font-outfit tracking-tight">Large / Unusual Deposits</h3>
                                    </div>
                                    <div className="px-3 py-1 bg-amber-500/10 rounded-full text-[10px] font-black text-amber-500 uppercase tracking-widest border border-amber-500/20">
                                        Section 2 Audit
                                    </div>
                                </div>
                                <UnusualDepositsTable deposits={data.large_deposits} />
                            </div>
                        </div>
                    </motion.div>
                );
        }
    };

    return (
        <div className="min-h-screen bg-[#020617] text-slate-200 w-full overflow-x-hidden font-sans">
            {/* Sidebar for Desktop */}
            <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col z-20">
                <div className="flex flex-col flex-grow bg-slate-900/50 backdrop-blur-3xl border-r border-slate-800/50 pt-8 overflow-y-auto">
                    <div className="flex items-center flex-shrink-0 px-8 mb-10 gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-400 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
                            <BarChart3 className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-2xl font-black font-outfit text-white tracking-tight">
                            BSA <span className="text-primary-500">Pro</span>
                        </span>
                    </div>

                    <div className="flex-grow px-4 space-y-1">
                        <button
                            onClick={() => setActiveTab('overview')}
                            className={`flex items-center w-full px-4 py-3.5 rounded-2xl text-sm font-bold border transition-all group ${activeTab === 'overview' ? 'bg-primary-500/10 text-primary-400 border-primary-500/20' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border-transparent'}`}
                        >
                            <LayoutDashboard className="w-5 h-5 mr-3" />
                            Overview
                        </button>
                        <button
                            onClick={() => setActiveTab('reports')}
                            className={`flex items-center w-full px-4 py-3.5 rounded-2xl text-sm font-bold border transition-all group ${activeTab === 'reports' ? 'bg-primary-500/10 text-primary-400 border-primary-500/20' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border-transparent'}`}
                        >
                            <FileText className="w-5 h-5 mr-3 group-hover:text-primary-400 transition-colors" />
                            Reports
                        </button>
                        <button
                            onClick={() => setActiveTab('audit')}
                            className={`flex items-center w-full px-4 py-3.5 rounded-2xl text-sm font-bold border transition-all group ${activeTab === 'audit' ? 'bg-primary-500/10 text-primary-400 border-primary-500/20' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border-transparent'}`}
                        >
                            <User className="w-5 h-5 mr-3 group-hover:text-primary-400 transition-colors" />
                            Audit Log
                        </button>
                        <button
                            onClick={() => setActiveTab('config')}
                            className={`flex items-center w-full px-4 py-3.5 rounded-2xl text-sm font-bold border transition-all group ${activeTab === 'config' ? 'bg-primary-500/10 text-primary-400 border-primary-500/20' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border-transparent'}`}
                        >
                            <Settings className="w-5 h-5 mr-3 group-hover:text-primary-400 transition-colors" />
                            Configurations
                        </button>
                    </div>

                    <div className="p-4 mt-auto border-t border-slate-800/50">
                        <button
                            onClick={onLogout}
                            className="flex items-center w-full px-4 py-3.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/5 rounded-2xl text-sm font-bold transition-all group"
                        >
                            <LogOut className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
                            Terminate Session
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="lg:pl-72 flex flex-col flex-1 min-h-screen">
                {/* Top Navbar for Mobile/Tablet */}
                <nav className="glass-nav border-b border-slate-800/50 sticky top-0 z-30 lg:hidden">
                    <div className="px-6 py-4 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="w-6 h-6 text-primary-500" />
                            <span className="text-xl font-black font-outfit text-white">BSA Pro</span>
                        </div>
                        <button onClick={onLogout} className="p-2 text-slate-400 hover:text-white transition-colors">
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </nav>

                <main className="flex-1 p-6 lg:p-10 max-w-7xl mx-auto w-full">
                    <AnimatePresence mode="wait">
                        {renderContent()}
                    </AnimatePresence>
                </main>
            </div>
        </div>
    );
};

export default Dashboard;
