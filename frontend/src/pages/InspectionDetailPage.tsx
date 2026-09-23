import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Package, User2, Calendar, ImageIcon, Brain, Shield,
  AlertTriangle, CheckCircle2, XCircle, Clock, ClipboardCheck,
  FileText, Loader2, AlertCircle, Play, RefreshCw, ChevronDown, ChevronUp,
  Info, Eye,
} from 'lucide-react';
import api from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import type {
  InspectionDetail, InspectionStatus, AnalysisStatus, AIResult,
  Evidence, ComplianceCheck, ComplianceStatus, FinalDecision,
} from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

function fmtDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function fmtPct(v: number | null | undefined) {
  if (v == null) return '—';
  return `${(v * 100).toFixed(0)}%`;
}

// ── Status pill ────────────────────────────────────────────────────────────

function CheckStatusPill({ status }: { status: ComplianceStatus }) {
  const cfg: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    PASS:               { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
    FAIL:               { bg: 'bg-red-50 border-red-200',         text: 'text-red-700',     icon: <XCircle className="h-3.5 w-3.5" /> },
    NEEDS_VERIFICATION: { bg: 'bg-amber-50 border-amber-200',     text: 'text-amber-700',   icon: <AlertTriangle className="h-3.5 w-3.5" /> },
    NOT_CHECKED:        { bg: 'bg-slate-50 border-slate-200',      text: 'text-slate-500',   icon: <Clock className="h-3.5 w-3.5" /> },
    NOT_APPLICABLE:     { bg: 'bg-slate-50 border-slate-200',      text: 'text-slate-500',   icon: <Info className="h-3.5 w-3.5" /> },
    PROCESSING:         { bg: 'bg-blue-50 border-blue-200',        text: 'text-blue-600',    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" /> },
  };
  const c = cfg[status] ?? cfg.NOT_CHECKED;
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-semibold ${c.bg} ${c.text}`}>
      {c.icon} {status.replace('_', ' ')}
    </span>
  );
}

function SeverityPill({ severity }: { severity: string | null }) {
  if (!severity) return null;
  const cfg: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-800',
    HIGH:     'bg-orange-100 text-orange-800',
    MEDIUM:   'bg-amber-100 text-amber-800',
    LOW:      'bg-slate-100 text-slate-600',
  };
  return <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${cfg[severity] ?? 'bg-slate-100 text-slate-600'}`}>{severity}</span>;
}

// ── Tab nav ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',      label: 'Overview',          icon: Package },
  { id: 'images',        label: 'Images',             icon: ImageIcon },
  { id: 'analysis',      label: 'AI Analysis',        icon: Brain },
  { id: 'evidence',      label: 'Evidence',           icon: Eye },
  { id: 'compliance',    label: 'Rule Validation',    icon: Shield },
  { id: 'findings',      label: 'Findings',           icon: AlertTriangle },
  { id: 'verification',  label: 'Human Verification', icon: ClipboardCheck },
  { id: 'report',        label: 'Report',             icon: FileText },
] as const;

type TabId = typeof TABS[number]['id'];

// ══════════════════════════════════════════════════════════════════════════════
// Main component
// ══════════════════════════════════════════════════════════════════════════════

export default function InspectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const user = getCurrentUser();

  const [activeTab, setActiveTab] = useState<TabId>((searchParams.get('tab') as TabId) || 'overview');
  const [inspection, setInspection] = useState<InspectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Analysis data
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [aiResults, setAiResults] = useState<AIResult[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [compliance, setCompliance] = useState<ComplianceCheck[]>([]);
  const [analysing, setAnalysing] = useState(false);
  const [pollingActive, setPollingActive] = useState(false);

  // Human verification
  const [reviewSubmitting, setReviewSubmitting] = useState<number | null>(null);
  const [reviewComments, setReviewComments] = useState<Record<number, string>>({});
  const [finalising, setFinalising] = useState(false);
  const [finalDecision, setFinalDecision] = useState<FinalDecision | ''>('');
  const [finalComment, setFinalComment] = useState('');
  const [confirmFinalise, setConfirmFinalise] = useState(false);

  // Report
  const [reportGenerating, setReportGenerating] = useState(false);

  const loadInspection = useCallback(async () => {
    try {
      const res = await api.get<InspectionDetail>(`/api/inspections/${id}`);
      setInspection(res.data);
      return res.data;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load inspection.');
      return null;
    }
  }, [id]);

  const loadAnalysisData = useCallback(async () => {
    if (!id) return;
    try {
      const [statusRes, aiRes, evRes, compRes] = await Promise.all([
        api.get<AnalysisStatus>(`/api/inspections/${id}/analysis`),
        api.get<AIResult[]>(`/api/inspections/${id}/ai-results`),
        api.get<Evidence[]>(`/api/inspections/${id}/evidence`),
        api.get<ComplianceCheck[]>(`/api/inspections/${id}/compliance`),
      ]);
      setAnalysisStatus(statusRes.data);
      setAiResults(aiRes.data);
      setEvidence(evRes.data);
      setCompliance(compRes.data);
      return statusRes.data;
    } catch {
      return null;
    }
  }, [id]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const insp = await loadInspection();
      if (insp && ['ANALYZING', 'REQUIRES_REVIEW', 'COMPLETED'].includes(insp.status)) {
        await loadAnalysisData();
      }
      setLoading(false);

      // Auto-start analysis if coming from NewInspectionPage
      if (insp && searchParams.get('autostart') === '1' &&
          (insp.status === 'DRAFT' || insp.status === 'IN_PROGRESS') &&
          insp.images.length > 0) {
        // Remove the autostart param to avoid re-triggering on refresh
        setSearchParams({ tab: 'analysis' });
        try {
          await api.post(`/api/inspections/${insp.id}/analyze`);
          setPollingActive(true);
          setAnalysing(true);
        } catch (e: any) {
          setError(e?.response?.data?.detail || 'Failed to auto-start analysis.');
        }
      }
    };
    init();
  }, [id]);

  // Polling when analyzing
  useEffect(() => {
    if (!pollingActive) return;
    const interval = setInterval(async () => {
      const [insp, status] = await Promise.all([loadInspection(), loadAnalysisData()]);
      if (insp && insp.status !== 'ANALYZING') {
        setPollingActive(false);
        setAnalysing(false);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [pollingActive, loadInspection, loadAnalysisData]);

  const switchTab = (tab: TabId) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const startAnalysis = async () => {
    if (!inspection) return;
    setAnalysing(true);
    try {
      await api.post(`/api/inspections/${inspection.id}/analyze`);
      setPollingActive(true);
      switchTab('analysis');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to start analysis.');
      setAnalysing(false);
    }
  };

  const submitReview = async (checkId: number, action: string) => {
    setReviewSubmitting(checkId);
    try {
      await api.post(`/api/inspections/${id}/review/${checkId}`, {
        action,
        comment: reviewComments[checkId] || null,
      });
      await loadAnalysisData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit review.');
    } finally {
      setReviewSubmitting(null);
    }
  };

  const finalize = async () => {
    if (!finalDecision || !inspection) return;
    setFinalising(true);
    try {
      await api.post(`/api/inspections/${inspection.id}/finalize`, {
        decision: finalDecision,
        comment: finalComment || null,
      });
      setConfirmFinalise(false);
      await loadInspection();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to finalize inspection.');
    } finally {
      setFinalising(false);
    }
  };

  const downloadReport = async () => {
    if (!inspection) return;
    setReportGenerating(true);
    try {
      const res = await api.get(`/api/inspections/${inspection.id}/report`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `INSPECTRA_Report_${inspection.inspection_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError('Failed to generate report. Ensure analysis has been completed.');
    } finally {
      setReportGenerating(false);
    }
  };

  if (loading) return <div className="p-8"><LoadingSpinner className="py-20" label="Loading inspection…" /></div>;
  if (error && !inspection) return <div className="p-8"><ErrorAlert message={error} /></div>;
  if (!inspection) return null;

  const isAnalyzingOrDone = ['ANALYZING', 'REQUIRES_REVIEW', 'COMPLETED'].includes(inspection.status);
  const findings = compliance.filter(c => c.status === 'FAIL' || c.status === 'NEEDS_VERIFICATION');
  const pendingReview = findings.filter(c => !c.human_reviewed);

  return (
    <div className="flex flex-col min-h-full bg-slate-50">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-2 text-sm mb-2">
            <button onClick={() => navigate('/inspections')} className="flex items-center gap-1 text-slate-500 hover:text-slate-800 transition-colors">
              <ArrowLeft className="h-4 w-4" /> Inspections
            </button>
            <span className="text-slate-300">/</span>
            <span className="font-mono text-slate-800 font-medium">{inspection.inspection_number}</span>
            {inspection.is_demo && (
              <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-100 border border-amber-300 px-2 py-0.5 text-[10px] font-bold text-amber-700 uppercase tracking-wide">
                Demo
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-slate-900 font-mono">{inspection.inspection_number}</h1>
              <StatusBadge status={inspection.status} />
              {inspection.final_decision && (
                <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-bold ${
                  inspection.final_decision === 'COMPLIANT' ? 'bg-emerald-50 border-emerald-300 text-emerald-800' :
                  inspection.final_decision === 'NON_COMPLIANT' ? 'bg-red-50 border-red-300 text-red-800' :
                  'bg-amber-50 border-amber-300 text-amber-800'
                }`}>
                  {inspection.final_decision === 'COMPLIANT' ? <CheckCircle2 className="h-3 w-3" /> : inspection.final_decision === 'NON_COMPLIANT' ? <XCircle className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
                  {inspection.final_decision.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {(inspection.status === 'DRAFT' || inspection.status === 'IN_PROGRESS') && inspection.images.length > 0 && (
                <button
                  id="btn-start-analysis"
                  onClick={startAnalysis}
                  disabled={analysing}
                  className="flex items-center gap-2 rounded-md bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
                >
                  {analysing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  {analysing ? 'Analysing…' : 'Start Analysis'}
                </button>
              )}
              {inspection.status === 'ANALYZING' && (
                <span className="flex items-center gap-2 text-xs text-blue-600 font-medium">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Analysis running…
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-slate-200 px-6">
        <div className="max-w-7xl mx-auto flex gap-0 overflow-x-auto">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const hasBadge = tab.id === 'findings' && findings.length > 0;
            const reviewBadge = tab.id === 'verification' && pendingReview.length > 0;
            return (
              <button
                key={tab.id}
                onClick={() => switchTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-blue-700 text-blue-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
                {hasBadge && <span className="ml-1 rounded-full bg-red-500 text-white text-[9px] font-bold px-1.5 py-0.5">{findings.length}</span>}
                {reviewBadge && <span className="ml-1 rounded-full bg-amber-500 text-white text-[9px] font-bold px-1.5 py-0.5">{pendingReview.length}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 px-6 py-6">
        <div className="max-w-7xl mx-auto">
          {error && <div className="mb-4"><ErrorAlert message={error} /></div>}

          {/* ── Overview ── */}
          {activeTab === 'overview' && (
            <OverviewTab inspection={inspection} />
          )}

          {/* ── Images ── */}
          {activeTab === 'images' && (
            <ImagesTab inspection={inspection} baseUrl={BASE_URL} />
          )}

          {/* ── AI Analysis ── */}
          {activeTab === 'analysis' && (
            <AnalysisTab
              inspection={inspection}
              analysisStatus={analysisStatus}
              aiResults={aiResults}
              baseUrl={BASE_URL}
              onRefresh={loadAnalysisData}
            />
          )}

          {/* ── Evidence ── */}
          {activeTab === 'evidence' && (
            <EvidenceTab
              evidence={evidence}
              images={inspection.images}
              baseUrl={BASE_URL}
            />
          )}

          {/* ── Rule Validation ── */}
          {activeTab === 'compliance' && (
            <ComplianceTab compliance={compliance} />
          )}

          {/* ── Findings ── */}
          {activeTab === 'findings' && (
            <FindingsTab
              findings={findings}
              evidence={evidence}
              images={inspection.images}
              baseUrl={BASE_URL}
              onGoToVerification={() => switchTab('verification')}
            />
          )}

          {/* ── Human Verification ── */}
          {activeTab === 'verification' && (
            <VerificationTab
              inspection={inspection}
              findings={findings}
              reviewComments={reviewComments}
              reviewSubmitting={reviewSubmitting}
              finalDecision={finalDecision}
              finalComment={finalComment}
              finalising={finalising}
              confirmFinalise={confirmFinalise}
              onSetComment={(id, v) => setReviewComments(prev => ({ ...prev, [id]: v }))}
              onSubmitReview={submitReview}
              onSetFinalDecision={setFinalDecision}
              onSetFinalComment={setFinalComment}
              onSetConfirmFinalise={setConfirmFinalise}
              onFinalize={finalize}
            />
          )}

          {/* ── Report ── */}
          {activeTab === 'report' && (
            <ReportTab
              inspection={inspection}
              compliance={compliance}
              generating={reportGenerating}
              onDownload={downloadReport}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Tab sub-components
// ══════════════════════════════════════════════════════════════════════════════

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>{children}</div>;
}

function SectionHead({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="px-5 py-4 border-b border-slate-100">
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────

function OverviewTab({ inspection }: { inspection: InspectionDetail }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="p-5">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">
          <Package className="h-4 w-4" /> Product
        </div>
        <p className="font-semibold text-slate-900">{inspection.product.product_name}</p>
        <p className="text-xs text-slate-500 mt-1">Code: {inspection.product.product_code}</p>
        {inspection.product.category && <p className="text-xs text-slate-500">Category: {inspection.product.category}</p>}
        {inspection.product.manufacturer && <p className="text-xs text-slate-500">Manufacturer: {inspection.product.manufacturer}</p>}
      </Card>
      <Card className="p-5">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">
          <User2 className="h-4 w-4" /> Inspector
        </div>
        <p className="font-semibold text-slate-900">{inspection.inspector.name}</p>
        <p className="text-xs text-slate-500 mt-1">{inspection.inspector.email}</p>
        <p className="text-xs text-slate-400 mt-0.5">{inspection.inspector.role}</p>
      </Card>
      <Card className="p-5">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">
          <Calendar className="h-4 w-4" /> Timeline
        </div>
        <div className="space-y-1.5 text-xs">
          {[['Created', inspection.created_at], ['Started', inspection.started_at], ['Completed', inspection.completed_at]].map(([l, v]) => (
            <div key={l as string} className="flex justify-between">
              <span className="text-slate-500">{l}</span>
              <span className="text-slate-800 font-medium">{fmtDate(v as string | null)}</span>
            </div>
          ))}
        </div>
      </Card>
      {inspection.notes && (
        <Card className="lg:col-span-3 p-5">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
            <FileText className="h-4 w-4" /> Notes
          </div>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{inspection.notes}</p>
        </Card>
      )}
      {inspection.analysis_error && (
        <div className="lg:col-span-3">
          <ErrorAlert message={`Analysis error: ${inspection.analysis_error}`} />
        </div>
      )}
    </div>
  );
}

// ── Images Tab ────────────────────────────────────────────────────────────

function ImagesTab({ inspection, baseUrl }: { inspection: InspectionDetail; baseUrl: string }) {
  if (inspection.images.length === 0) {
    return (
      <Card className="p-10 text-center">
        <ImageIcon className="h-10 w-10 text-slate-300 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-600">No images uploaded</p>
        <p className="text-xs text-slate-400 mt-1">Upload package images to begin analysis.</p>
      </Card>
    );
  }
  return (
    <Card>
      <SectionHead title={`Package Images (${inspection.images.length})`} subtitle="Multiple package surfaces can be analyzed as one inspection." />
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 p-5">
        {inspection.images.map((img) => (
          <div key={img.id} className="group relative rounded-lg border border-slate-200 overflow-hidden bg-slate-50">
            <img
              src={`${baseUrl}${img.image_url}`}
              alt={img.view_type}
              className="w-full h-36 object-cover"
              onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23f1f5f9" width="100" height="100"/><text x="50" y="55" text-anchor="middle" font-size="12" fill="%2394a3b8">No preview</text></svg>'; }}
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
              <span className="text-white text-[10px] font-bold">{img.view_type}</span>
              {img.original_filename && <p className="text-white/70 text-[9px] truncate">{img.original_filename}</p>}
            </div>
            <div className="absolute top-2 right-2 bg-slate-900/60 rounded text-white text-[9px] px-1.5 py-0.5 font-mono">
              #{img.id}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Analysis Tab ──────────────────────────────────────────────────────────

type AnalysisTabProps = {
  inspection: InspectionDetail;
  analysisStatus: AnalysisStatus | null;
  aiResults: AIResult[];
  baseUrl: string;
  onRefresh: () => void;
};

function AnalysisTab({ inspection, analysisStatus, aiResults, baseUrl, onRefresh }: AnalysisTabProps) {
  const isAnalyzing = inspection.status === 'ANALYZING';

  const STEPS = [
    { key: 'images',        label: 'Uploading package images',                done: true },
    { key: 'ocr',           label: 'Running OCR / Vision extraction',          done: aiResults.some(r => r.agent_type === 'label_agent') },
    { key: 'label_agent',   label: 'Running Label Agent',                      done: aiResults.some(r => r.agent_type === 'label_agent') },
    { key: 'qty_agent',     label: 'Running Quantity Agent',                   done: aiResults.some(r => r.agent_type === 'quantity_agent') },
    { key: 'decl_agent',    label: 'Running Declaration Agent',                done: aiResults.some(r => r.agent_type === 'declaration_agent') },
    { key: 'evidence',      label: 'Generating structured evidence',           done: (analysisStatus?.evidence_count ?? 0) > 0 },
    { key: 'decl_engine',   label: 'Running Declaration Rule Engine',          done: (analysisStatus?.compliance_checks_count ?? 0) > 0 },
    { key: 'meas_engine',   label: 'Running Measurement & Presentation Rules', done: (analysisStatus?.compliance_checks_count ?? 0) > 4 },
    { key: 'ready',         label: 'Ready for Human Verification',             done: !isAnalyzing && (analysisStatus?.compliance_checks_count ?? 0) > 0 },
  ];

  const labelResult = aiResults.find(r => r.agent_type === 'label_agent');
  const qtyResult = aiResults.find(r => r.agent_type === 'quantity_agent');
  const declResult = aiResults.find(r => r.agent_type === 'declaration_agent');

  return (
    <div className="space-y-4">
      {/* Processing pipeline */}
      <Card>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <SectionHead title="Processing Pipeline" subtitle={isAnalyzing ? "Analysis is running — results appear as each step completes" : "Analysis complete"} />
          <button onClick={onRefresh} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded px-2 py-1">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>
        <div className="p-5 space-y-2">
          {STEPS.map((step, i) => {
            const isDone = step.done;
            const isNext = !isDone && STEPS.slice(0, i).every(s => s.done) && isAnalyzing;
            return (
              <div key={step.key} className={`flex items-center gap-3 p-2.5 rounded-lg ${isDone ? 'bg-emerald-50' : isNext ? 'bg-blue-50' : 'bg-slate-50'}`}>
                <div className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  isDone ? 'bg-emerald-500 text-white' : isNext ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-500'
                }`}>
                  {isDone ? <CheckCircle2 className="h-3.5 w-3.5" /> : isNext ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : i + 1}
                </div>
                <span className={`text-sm font-medium ${isDone ? 'text-emerald-800' : isNext ? 'text-blue-800' : 'text-slate-400'}`}>
                  {step.label}
                </span>
                {isDone && <CheckCircle2 className="h-4 w-4 text-emerald-500 ml-auto" />}
              </div>
            );
          })}
        </div>
        {analysisStatus && !isAnalyzing && (
          <div className="px-5 pb-4">
            <div className="flex gap-4 text-xs">
              <span className="text-slate-500">{analysisStatus.ai_results_count} agent results</span>
              <span className="text-slate-500">{analysisStatus.evidence_count} evidence records</span>
              <span className="text-slate-500">{analysisStatus.compliance_checks_count} compliance checks</span>
              {analysisStatus.analysis_error && <span className="text-red-600">Error: {analysisStatus.analysis_error}</span>}
            </div>
          </div>
        )}
      </Card>

      {/* Label Agent results */}
      {labelResult && (
        <AgentPanel
          title="Label Agent"
          agentType="label_agent"
          result={labelResult}
          color="violet"
        >
          <LabelAgentContent result={labelResult} />
        </AgentPanel>
      )}

      {/* Quantity Agent results */}
      {qtyResult && (
        <AgentPanel title="Quantity Agent" agentType="quantity_agent" result={qtyResult} color="blue">
          <QuantityAgentContent result={qtyResult} />
        </AgentPanel>
      )}

      {/* Declaration Agent results */}
      {declResult && (
        <AgentPanel title="Declaration Agent" agentType="declaration_agent" result={declResult} color="indigo">
          <DeclarationAgentContent result={declResult} images={[]} />
        </AgentPanel>
      )}
    </div>
  );
}

function AgentPanel({ title, agentType, result, color, children }: {
  title: string; agentType: string; result: AIResult; color: string; children: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(true);
  const colorMap: Record<string, string> = {
    violet: 'bg-violet-700',
    blue:   'bg-blue-700',
    indigo: 'bg-indigo-700',
  };
  return (
    <Card>
      <button
        onClick={() => setExpanded(e => !e)}
        className={`w-full flex items-center justify-between px-5 py-3 ${colorMap[color]} rounded-t-xl text-white`}
      >
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 opacity-80" />
          <span className="text-sm font-bold">{title}</span>
          <span className="text-xs opacity-70">· {result.model_name} v{result.model_version}</span>
          {result.provider && (
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${result.provider === 'demo' ? 'bg-amber-400 text-amber-900' : 'bg-emerald-400 text-emerald-900'}`}>
              {result.provider}
            </span>
          )}
        </div>
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {expanded && <div className="p-5">{children}</div>}
    </Card>
  );
}

function LabelAgentContent({ result }: { result: AIResult }) {
  const data = result.result_json || {};
  const obs = data.observations || [];
  const placement = data.placement_observations || [];
  const readability = data.readability_observations || [];

  return (
    <div className="space-y-4">
      {obs.length > 0 && (
        <div>
          <p className="text-xs font-bold text-slate-600 mb-2 uppercase tracking-wide">Text Observations ({obs.length})</p>
          <div className="overflow-auto rounded border border-slate-200">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">OBS ID</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Text</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">View</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Confidence</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Position</th>
                </tr>
              </thead>
              <tbody>
                {obs.slice(0, 15).map((o: any, i: number) => (
                  <tr key={i} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                    <td className="px-3 py-2 font-mono text-slate-500">{o.obs_id}</td>
                    <td className="px-3 py-2 text-slate-800 max-w-xs truncate">{o.text}</td>
                    <td className="px-3 py-2 text-slate-500">{o.view_type}</td>
                    <td className="px-3 py-2">
                      <span className={`font-semibold ${o.confidence >= 0.9 ? 'text-emerald-600' : o.confidence >= 0.75 ? 'text-amber-600' : 'text-red-600'}`}>
                        {fmtPct(o.confidence)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{o.position_hint}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {obs.length > 15 && <p className="text-xs text-slate-400 mt-1">+ {obs.length - 15} more observations</p>}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {placement.length > 0 && (
          <div>
            <p className="text-xs font-bold text-slate-600 mb-2 uppercase tracking-wide">Placement Observations</p>
            <div className="space-y-1">
              {placement.map((p: any, i: number) => (
                <div key={i} className="flex items-start gap-2 text-xs bg-slate-50 rounded p-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-600">{p.observation}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {readability.length > 0 && (
          <div>
            <p className="text-xs font-bold text-slate-600 mb-2 uppercase tracking-wide">Readability Observations</p>
            <div className="space-y-1">
              {readability.map((r: any, i: number) => (
                <div key={i} className="flex items-start gap-2 text-xs bg-slate-50 rounded p-2">
                  <Eye className="h-3.5 w-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-600">{r.observation}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function QuantityAgentContent({ result }: { result: AIResult }) {
  const data = result.result_json || {};
  const primary = data.primary_quantity;
  const quantities = data.quantities || [];

  if (!data.detected) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-4 border border-red-100">
        <XCircle className="h-5 w-5" />
        Net quantity declaration not detected in the submitted images.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {primary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ['Declared Value', primary.raw_value, 'font-mono font-bold text-slate-900'],
            ['Unit', primary.unit, 'text-slate-700'],
            ['Normalised', `${primary.normalized_value} ${primary.normalized_unit}`, 'text-slate-700'],
            ['Confidence', fmtPct(primary.confidence), `font-bold ${primary.confidence >= 0.9 ? 'text-emerald-600' : primary.confidence >= 0.75 ? 'text-amber-600' : 'text-red-600'}`],
          ].map(([label, value, cls]) => (
            <div key={label as string} className="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide mb-1">{label}</p>
              <p className={`text-sm ${cls}`}>{value}</p>
            </div>
          ))}
        </div>
      )}
      {quantities.length > 1 && (
        <div>
          <p className="text-xs font-bold text-slate-500 mb-2">All Detected Quantities ({quantities.length})</p>
          <div className="space-y-1">
            {quantities.map((q: any, i: number) => (
              <div key={i} className="flex items-center gap-3 text-xs bg-slate-50 rounded p-2 border border-slate-100">
                {q.is_primary && <span className="text-[9px] bg-blue-600 text-white rounded px-1 font-bold">PRIMARY</span>}
                <span className="font-mono font-semibold text-slate-800">{q.raw_value}</span>
                <span className="text-slate-400">→ {q.normalized_value} {q.normalized_unit}</span>
                <span className="ml-auto text-slate-500">conf: {fmtPct(q.confidence)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DeclarationAgentContent({ result, images }: { result: AIResult; images: any[] }) {
  const data = result.result_json || {};
  const declarations = data.declarations || [];
  const notDetected = data.fields_not_detected || [];

  return (
    <div className="space-y-4">
      {declarations.length > 0 ? (
        <div className="overflow-auto rounded border border-slate-200">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-3 py-2 text-left text-slate-500 font-semibold">Field</th>
                <th className="px-3 py-2 text-left text-slate-500 font-semibold">Extracted Value</th>
                <th className="px-3 py-2 text-left text-slate-500 font-semibold">Confidence</th>
                <th className="px-3 py-2 text-left text-slate-500 font-semibold">Source Image</th>
              </tr>
            </thead>
            <tbody>
              {declarations.map((d: any, i: number) => (
                <tr key={i} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="px-3 py-2 font-semibold text-slate-700">{d.display_name}</td>
                  <td className="px-3 py-2 text-slate-800 max-w-xs font-mono text-[11px]">{d.value}</td>
                  <td className="px-3 py-2">
                    <span className={`font-semibold ${(d.confidence ?? 0) >= 0.9 ? 'text-emerald-600' : (d.confidence ?? 0) >= 0.75 ? 'text-amber-600' : 'text-red-600'}`}>
                      {fmtPct(d.confidence)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    {d.source_image_id ? `Image #${d.source_image_id}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-slate-500">No declarations extracted.</p>
      )}
      {notDetected.length > 0 && (
        <div>
          <p className="text-xs font-bold text-slate-500 mb-2">Fields Not Detected ({notDetected.length})</p>
          <div className="flex flex-wrap gap-1.5">
            {notDetected.map((f: string) => (
              <span key={f} className="inline-flex items-center gap-1 rounded bg-red-50 border border-red-200 px-2 py-0.5 text-[11px] text-red-600">
                <XCircle className="h-3 w-3" /> {f.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Evidence Tab ──────────────────────────────────────────────────────────

function EvidenceTab({ evidence, images, baseUrl }: {
  evidence: Evidence[];
  images: any[];
  baseUrl: string;
}) {
  const [selectedEv, setSelectedEv] = useState<Evidence | null>(null);
  const imageMap = Object.fromEntries(images.map(i => [i.id, i]));

  if (evidence.length === 0) {
    return (
      <Card className="p-10 text-center">
        <Eye className="h-10 w-10 text-slate-300 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-600">No evidence records yet</p>
        <p className="text-xs text-slate-400 mt-1">Run analysis to generate structured evidence.</p>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div className="xl:col-span-2">
        <Card>
          <SectionHead title={`Structured Evidence (${evidence.length})`} subtitle="Every observation is linked to its source image and agent. Click a record to view source." />
          <div className="overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Ref</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Agent</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Field</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Extracted Value</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Confidence</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-semibold">Source</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map(ev => (
                  <tr
                    key={ev.id}
                    onClick={() => setSelectedEv(ev)}
                    className={`border-b border-slate-100 last:border-0 cursor-pointer transition-colors ${selectedEv?.id === ev.id ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                  >
                    <td className="px-3 py-2 font-mono font-bold text-blue-700">{ev.evidence_ref_id || `EV-${ev.id}`}</td>
                    <td className="px-3 py-2">
                      <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                        {ev.agent_type?.replace('_', ' ').replace('agent', '').trim() || '—'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-700">{ev.field_name?.replace(/_/g, ' ') || ev.evidence_type || '—'}</td>
                    <td className="px-3 py-2 text-slate-800 font-mono max-w-xs truncate">{ev.extracted_value || ev.ocr_text || '—'}</td>
                    <td className="px-3 py-2">
                      <span className={`font-semibold ${(ev.confidence ?? 0) >= 0.9 ? 'text-emerald-600' : (ev.confidence ?? 0) >= 0.75 ? 'text-amber-600' : 'text-red-600'}`}>
                        {fmtPct(ev.confidence)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{ev.image_id ? `Image #${ev.image_id}` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Evidence detail / image viewer */}
      <div>
        {selectedEv ? (
          <Card className="sticky top-4">
            <SectionHead title={selectedEv.evidence_ref_id || `Evidence #${selectedEv.id}`} subtitle="Source details" />
            <div className="p-4 space-y-3">
              {selectedEv.image_id && imageMap[selectedEv.image_id] ? (
                <div>
                  <p className="text-[10px] text-slate-500 font-semibold uppercase mb-1.5">Source Image</p>
                  <img
                    src={`${baseUrl}${imageMap[selectedEv.image_id].image_url}`}
                    alt={imageMap[selectedEv.image_id].view_type}
                    className="w-full rounded-lg border border-slate-200 object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><rect fill="%23f1f5f9" width="100" height="60"/><text x="50" y="35" text-anchor="middle" font-size="10" fill="%2394a3b8">Image unavailable</text></svg>'; }}
                  />
                  <p className="text-[10px] text-slate-400 mt-1 text-center">{imageMap[selectedEv.image_id].view_type} view · Image #{selectedEv.image_id}</p>
                </div>
              ) : (
                <div className="rounded bg-slate-50 border border-slate-200 p-4 text-center text-xs text-slate-400">
                  <ImageIcon className="h-6 w-6 mx-auto mb-1 opacity-50" />
                  No specific image linked to this evidence
                </div>
              )}
              <div className="space-y-2 text-xs">
                {[
                  ['Agent', selectedEv.agent_type?.replace(/_/g, ' ')],
                  ['Field', selectedEv.field_name?.replace(/_/g, ' ') || selectedEv.evidence_type],
                  ['Extracted Value', selectedEv.extracted_value || selectedEv.ocr_text],
                  ['Confidence', fmtPct(selectedEv.confidence)],
                ].map(([l, v]) => v && (
                  <div key={l as string} className="flex justify-between gap-2">
                    <span className="text-slate-500 font-medium flex-shrink-0">{l}</span>
                    <span className="text-slate-800 text-right font-mono">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ) : (
          <Card className="p-8 text-center">
            <Eye className="h-8 w-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs text-slate-400">Click an evidence record to view source details</p>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── Compliance Tab ────────────────────────────────────────────────────────

function ComplianceTab({ compliance }: { compliance: ComplianceCheck[] }) {
  const decl = compliance.filter(c => c.engine_type === 'declaration');
  const meas = compliance.filter(c => c.engine_type === 'measurement');

  const Summary = ({ checks }: { checks: ComplianceCheck[] }) => {
    const pass = checks.filter(c => c.status === 'PASS').length;
    const fail = checks.filter(c => c.status === 'FAIL').length;
    const nv   = checks.filter(c => c.status === 'NEEDS_VERIFICATION').length;
    return (
      <div className="flex gap-3 text-xs">
        <span className="flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />{pass} Pass</span>
        <span className="flex items-center gap-1 text-red-600"><XCircle className="h-3.5 w-3.5" />{fail} Fail</span>
        <span className="flex items-center gap-1 text-amber-600"><AlertTriangle className="h-3.5 w-3.5" />{nv} Needs Verification</span>
      </div>
    );
  };

  const ChecksTable = ({ checks }: { checks: ComplianceCheck[] }) => (
    checks.length === 0 ? (
      <div className="p-6 text-center text-xs text-slate-400">No checks in this category yet.</div>
    ) : (
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Rule ID</th>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Rule Name</th>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Status</th>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Severity</th>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Evidence</th>
              <th className="px-3 py-2 text-left text-slate-500 font-semibold">Reason</th>
            </tr>
          </thead>
          <tbody>
            {checks.map(c => (
              <tr key={c.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                <td className="px-3 py-2 font-mono text-slate-700 font-semibold whitespace-nowrap">{c.rule_id}</td>
                <td className="px-3 py-2 text-slate-600 whitespace-nowrap">{c.rule_name || '—'}</td>
                <td className="px-3 py-2 whitespace-nowrap"><CheckStatusPill status={c.status} /></td>
                <td className="px-3 py-2 whitespace-nowrap"><SeverityPill severity={c.severity} /></td>
                <td className="px-3 py-2">
                  {(c.evidence_ref_ids || []).length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {c.evidence_ref_ids!.map(ref => (
                        <span key={ref} className="font-mono text-[10px] bg-blue-50 text-blue-700 rounded px-1.5 py-0.5 border border-blue-200">{ref}</span>
                      ))}
                    </div>
                  ) : '—'}
                </td>
                <td className="px-3 py-2 text-slate-500 max-w-xs">{c.message || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  );

  if (compliance.length === 0) {
    return (
      <Card className="p-10 text-center">
        <Shield className="h-10 w-10 text-slate-300 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-600">No rule validations yet</p>
        <p className="text-xs text-slate-400 mt-1">Run analysis to generate compliance checks.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Declaration Rule Engine</h3>
            <p className="text-xs text-slate-500 mt-0.5">Deterministic validation of mandatory label declarations (Rule 6, Rule 18)</p>
          </div>
          <Summary checks={decl} />
        </div>
        <ChecksTable checks={decl} />
      </Card>
      <Card>
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Measurement & Presentation Rule Engine</h3>
            <p className="text-xs text-slate-500 mt-0.5">Deterministic validation of net quantity and presentation requirements</p>
          </div>
          <Summary checks={meas} />
        </div>
        <ChecksTable checks={meas} />
      </Card>
    </div>
  );
}

// ── Findings Tab ──────────────────────────────────────────────────────────

function FindingsTab({ findings, evidence, images, baseUrl, onGoToVerification }: {
  findings: ComplianceCheck[];
  evidence: Evidence[];
  images: any[];
  baseUrl: string;
  onGoToVerification: () => void;
}) {
  const evMap = Object.fromEntries(evidence.map(e => [e.evidence_ref_id, e]));
  const imgMap = Object.fromEntries(images.map(i => [i.id, i]));

  if (findings.length === 0) {
    return (
      <Card className="p-10 text-center">
        <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto mb-3" />
        <p className="text-sm font-bold text-emerald-700">No findings requiring attention</p>
        <p className="text-xs text-slate-400 mt-1">All rule checks passed or are not applicable.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <span className="text-sm font-bold text-slate-800">{findings.length} Finding{findings.length > 1 ? 's' : ''} Requiring Attention</span>
        </div>
        <button onClick={onGoToVerification} className="flex items-center gap-2 rounded-md bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 transition-colors">
          <ClipboardCheck className="h-3.5 w-3.5" /> Go to Human Verification
        </button>
      </div>

      {findings.map(finding => {
        const isFail = finding.status === 'FAIL';
        const evRefs = finding.evidence_ref_ids || [];
        const firstEv = evRefs.length > 0 ? evMap[evRefs[0]] : null;
        const srcImage = firstEv?.image_id ? imgMap[firstEv.image_id] : null;

        return (
          <div
            key={finding.id}
            className={`rounded-xl border ${isFail ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'} overflow-hidden`}
          >
            {/* Header */}
            <div className={`px-5 py-3 flex items-center gap-3 ${isFail ? 'bg-red-100' : 'bg-amber-100'}`}>
              {isFail ? <XCircle className="h-5 w-5 text-red-600 flex-shrink-0" /> : <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-bold uppercase ${isFail ? 'text-red-700' : 'text-amber-700'}`}>
                    {isFail ? 'Potential Non-Compliance' : 'Requires Verification'}
                  </span>
                  <SeverityPill severity={finding.severity} />
                  {finding.human_reviewed && (
                    <span className="text-[10px] bg-slate-700 text-white rounded px-1.5 py-0.5 font-bold">REVIEWED</span>
                  )}
                </div>
              </div>
            </div>

            <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Finding details */}
              <div className="md:col-span-2 space-y-3">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-slate-500 font-semibold mb-0.5">Rule</p>
                    <p className="font-mono font-bold text-slate-800">{finding.rule_id}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 font-semibold mb-0.5">Status</p>
                    <CheckStatusPill status={finding.status} />
                  </div>
                  {finding.confidence != null && (
                    <div>
                      <p className="text-slate-500 font-semibold mb-0.5">Confidence</p>
                      <p className="font-semibold text-slate-800">{fmtPct(finding.confidence)}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-slate-500 font-semibold mb-0.5">Verification</p>
                    <p className={`font-semibold ${finding.requires_human_review ? 'text-red-600' : 'text-slate-500'}`}>
                      {finding.requires_human_review ? 'Required' : 'Not required'}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-semibold mb-1">Reason</p>
                  <p className="text-xs text-slate-700 leading-relaxed">{finding.message}</p>
                </div>
                {evRefs.length > 0 && (
                  <div>
                    <p className="text-xs text-slate-500 font-semibold mb-1">Evidence</p>
                    <div className="flex flex-wrap gap-1">
                      {evRefs.map(ref => (
                        <span key={ref} className="font-mono text-[10px] bg-blue-50 text-blue-700 rounded px-2 py-0.5 border border-blue-200 font-bold">{ref}</span>
                      ))}
                    </div>
                  </div>
                )}
                {finding.human_reviewed && (
                  <div className="rounded-lg bg-slate-100 border border-slate-200 p-3 text-xs">
                    <span className="font-semibold text-slate-700">Inspector action: </span>
                    <span className="font-bold">{finding.human_action}</span>
                    {finding.human_comment && <p className="text-slate-500 mt-1 italic">"{finding.human_comment}"</p>}
                  </div>
                )}
              </div>

              {/* Source image */}
              <div>
                {srcImage ? (
                  <div>
                    <p className="text-[10px] text-slate-500 font-semibold uppercase mb-1.5">Evidence Source</p>
                    <img
                      src={`${baseUrl}${srcImage.image_url}`}
                      alt={srcImage.view_type}
                      className="w-full rounded-lg border border-slate-200 object-cover h-32"
                      onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><rect fill="%23f8fafc" width="100" height="60"/></svg>'; }}
                    />
                    <p className="text-[10px] text-slate-400 mt-1 text-center">{srcImage.view_type} · {firstEv?.evidence_ref_id}</p>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full rounded-lg border border-dashed border-slate-300 bg-white p-4 text-center text-xs text-slate-400 min-h-[80px]">
                    <div>
                      <ImageIcon className="h-6 w-6 mx-auto mb-1 opacity-40" />
                      No specific image source
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Human Verification Tab ────────────────────────────────────────────────

type VerificationTabProps = {
  inspection: InspectionDetail;
  findings: ComplianceCheck[];
  reviewComments: Record<number, string>;
  reviewSubmitting: number | null;
  finalDecision: FinalDecision | '';
  finalComment: string;
  finalising: boolean;
  confirmFinalise: boolean;
  onSetComment: (id: number, v: string) => void;
  onSubmitReview: (id: number, action: string) => void;
  onSetFinalDecision: (d: FinalDecision | '') => void;
  onSetFinalComment: (s: string) => void;
  onSetConfirmFinalise: (b: boolean) => void;
  onFinalize: () => void;
};

function VerificationTab({
  inspection, findings, reviewComments, reviewSubmitting,
  finalDecision, finalComment, finalising, confirmFinalise,
  onSetComment, onSubmitReview, onSetFinalDecision, onSetFinalComment,
  onSetConfirmFinalise, onFinalize,
}: VerificationTabProps) {
  const isFinalized = !!inspection.final_decision;

  return (
    <div className="space-y-4">
      {/* Per-finding reviews */}
      {findings.length > 0 && (
        <Card>
          <SectionHead title="Review Findings" subtitle="Review each finding before making the final inspection decision. AI provides evidence — you make the determination." />
          <div className="p-5 space-y-4">
            {findings.map(finding => (
              <div key={finding.id} className={`rounded-lg border p-4 ${finding.human_reviewed ? 'border-slate-200 bg-slate-50' : 'border-amber-200 bg-white'}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="font-mono text-xs font-bold text-slate-700">{finding.rule_id}</span>
                  <CheckStatusPill status={finding.status} />
                  {finding.human_reviewed && <span className="text-[10px] bg-emerald-600 text-white rounded px-1.5 py-0.5 font-bold">✓ REVIEWED</span>}
                </div>
                <p className="text-xs text-slate-600 mb-3">{finding.message}</p>

                {!isFinalized && (
                  <>
                    <textarea
                      value={reviewComments[finding.id] || ''}
                      onChange={e => onSetComment(finding.id, e.target.value)}
                      placeholder="Add a comment (optional)…"
                      rows={2}
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-blue-500 resize-none mb-2"
                    />
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { action: 'CONFIRM', label: 'Confirm Finding', cls: 'bg-red-600 hover:bg-red-700 text-white', icon: <XCircle className="h-3.5 w-3.5" /> },
                        { action: 'REJECT', label: 'Reject Finding', cls: 'bg-emerald-600 hover:bg-emerald-700 text-white', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
                        { action: 'NEEDS_VERIFICATION', label: 'Needs Further Review', cls: 'bg-amber-500 hover:bg-amber-600 text-white', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
                      ].map(({ action, label, cls, icon }) => (
                        <button
                          key={action}
                          onClick={() => onSubmitReview(finding.id, action)}
                          disabled={reviewSubmitting === finding.id}
                          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60 ${cls}`}
                        >
                          {reviewSubmitting === finding.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
                          {label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {finding.human_reviewed && (
                  <div className="mt-2 text-xs text-slate-500">
                    Inspector action: <span className="font-bold text-slate-800">{finding.human_action}</span>
                    {finding.human_comment && <span className="italic ml-2">— "{finding.human_comment}"</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Final Decision */}
      <Card>
        <SectionHead title="Final Inspection Decision" subtitle="This is the authoritative human decision — AI provides evidence only." />
        <div className="p-5">
          {isFinalized ? (
            <div className="space-y-3">
              <div className={`rounded-xl border-2 p-5 flex items-center gap-4 ${
                inspection.final_decision === 'COMPLIANT' ? 'border-emerald-400 bg-emerald-50' :
                inspection.final_decision === 'NON_COMPLIANT' ? 'border-red-400 bg-red-50' :
                'border-amber-400 bg-amber-50'
              }`}>
                {inspection.final_decision === 'COMPLIANT' ? <CheckCircle2 className="h-8 w-8 text-emerald-600 flex-shrink-0" /> :
                 inspection.final_decision === 'NON_COMPLIANT' ? <XCircle className="h-8 w-8 text-red-600 flex-shrink-0" /> :
                 <AlertTriangle className="h-8 w-8 text-amber-600 flex-shrink-0" />}
                <div>
                  <p className="text-base font-bold text-slate-900">{inspection.final_decision?.replace(/_/g, ' ')}</p>
                  {inspection.final_decision_comment && <p className="text-xs text-slate-600 mt-1 italic">"{inspection.final_decision_comment}"</p>}
                  {inspection.finalized_at && <p className="text-xs text-slate-400 mt-1">Recorded {fmtDate(inspection.finalized_at)}</p>}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-2">Final Decision *</label>
                <div className="flex gap-3 flex-wrap">
                  {[
                    { value: 'COMPLIANT', label: 'Compliant', icon: <CheckCircle2 className="h-4 w-4" />, cls: 'border-emerald-400 bg-emerald-50 text-emerald-800' },
                    { value: 'NON_COMPLIANT', label: 'Non-Compliant', icon: <XCircle className="h-4 w-4" />, cls: 'border-red-400 bg-red-50 text-red-800' },
                    { value: 'REQUIRES_FURTHER_REVIEW', label: 'Requires Further Review', icon: <AlertTriangle className="h-4 w-4" />, cls: 'border-amber-400 bg-amber-50 text-amber-800' },
                  ].map(({ value, label, icon, cls }) => (
                    <button
                      key={value}
                      onClick={() => onSetFinalDecision(value as FinalDecision)}
                      className={`flex items-center gap-2 rounded-lg border-2 px-4 py-2.5 text-xs font-bold transition-all ${
                        finalDecision === value ? cls : 'border-slate-200 bg-white text-slate-600 hover:border-slate-400'
                      }`}
                    >
                      {icon} {label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Inspector Comment (optional)</label>
                <textarea
                  value={finalComment}
                  onChange={e => onSetFinalComment(e.target.value)}
                  rows={3}
                  placeholder="Record any relevant observations, exceptions, or context for this decision…"
                  className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-blue-500 resize-none"
                />
              </div>
              {!confirmFinalise ? (
                <button
                  onClick={() => onSetConfirmFinalise(true)}
                  disabled={!finalDecision}
                  className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
                >
                  <ClipboardCheck className="h-4 w-4" />
                  Record Final Decision
                </button>
              ) : (
                <div className="rounded-lg border-2 border-blue-300 bg-blue-50 p-4">
                  <p className="text-sm font-bold text-blue-900 mb-3">
                    Confirm: Record final decision as <span className="underline">{finalDecision?.replace(/_/g, ' ')}</span>?
                  </p>
                  <p className="text-xs text-blue-700 mb-4">This action will be permanently recorded in the inspection database.</p>
                  <div className="flex gap-2">
                    <button
                      onClick={onFinalize}
                      disabled={finalising}
                      className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
                    >
                      {finalising ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                      {finalising ? 'Saving…' : 'Confirm & Save'}
                    </button>
                    <button
                      onClick={() => onSetConfirmFinalise(false)}
                      className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// ── Report Tab ────────────────────────────────────────────────────────────

function ReportTab({ inspection, compliance, generating, onDownload }: {
  inspection: InspectionDetail;
  compliance: ComplianceCheck[];
  generating: boolean;
  onDownload: () => void;
}) {
  const pass = compliance.filter(c => c.status === 'PASS').length;
  const fail = compliance.filter(c => c.status === 'FAIL').length;
  const nv   = compliance.filter(c => c.status === 'NEEDS_VERIFICATION').length;
  const canGenerate = compliance.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <SectionHead title="Inspection Report" subtitle="Generate a PDF report of this inspection — suitable for record-keeping and regulatory reference." />
        <div className="p-5 space-y-4">
          {/* Report summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ['Total Checks', compliance.length, 'text-slate-800'],
              ['Pass', pass, 'text-emerald-700'],
              ['Fail', fail, 'text-red-700'],
              ['Needs Verification', nv, 'text-amber-700'],
            ].map(([l, v, cls]) => (
              <div key={l as string} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
                <p className={`text-xl font-bold ${cls}`}>{v}</p>
                <p className="text-xs text-slate-500 mt-0.5">{l}</p>
              </div>
            ))}
          </div>

          {inspection.final_decision ? (
            <div className={`flex items-center gap-3 rounded-lg border p-4 ${
              inspection.final_decision === 'COMPLIANT' ? 'border-emerald-300 bg-emerald-50' :
              inspection.final_decision === 'NON_COMPLIANT' ? 'border-red-300 bg-red-50' :
              'border-amber-300 bg-amber-50'
            }`}>
              {inspection.final_decision === 'COMPLIANT' ? <CheckCircle2 className="h-6 w-6 text-emerald-600" /> :
               inspection.final_decision === 'NON_COMPLIANT' ? <XCircle className="h-6 w-6 text-red-600" /> :
               <AlertTriangle className="h-6 w-6 text-amber-600" />}
              <div>
                <p className="text-sm font-bold text-slate-900">Final Decision: {inspection.final_decision.replace(/_/g, ' ')}</p>
                {inspection.final_decision_comment && <p className="text-xs text-slate-500 mt-0.5 italic">"{inspection.final_decision_comment}"</p>}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <AlertTriangle className="h-4 w-4" />
              No final decision recorded yet. The report can still be generated, but will note that verification is pending.
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              id="btn-download-report"
              onClick={onDownload}
              disabled={generating || !canGenerate}
              className="flex items-center gap-2 rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900 disabled:opacity-60 transition-colors"
            >
              {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              {generating ? 'Generating PDF…' : 'Download PDF Report'}
            </button>
            {!canGenerate && (
              <span className="text-xs text-slate-400">Complete analysis first to generate report.</span>
            )}
          </div>

          <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-xs text-slate-500 space-y-1">
            <p className="font-semibold text-slate-700">Report contains:</p>
            <ul className="list-disc list-inside space-y-0.5 ml-2">
              <li>Inspection header and metadata</li>
              <li>Product information and submitted images list</li>
              <li>Extracted declarations table (with evidence references)</li>
              <li>Quantity information</li>
              <li>Declaration Rule Engine results</li>
              <li>Measurement & Presentation Rule Engine results</li>
              <li>Potential violation findings</li>
              <li>Human verification summary</li>
              <li>Final inspection decision</li>
            </ul>
            <p className="mt-2 italic">This report is produced by the INSPECTRA prototype system. AI-extracted information assists the human inspector. The final compliance determination is made exclusively by the authorised human inspector.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
