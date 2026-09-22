import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Package, User2, Calendar, ImageIcon, FileText, Play, CheckCircle,
} from 'lucide-react';
import api from '@/lib/api';
import type { InspectionDetail, InspectionStatus } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { EmptyState } from '@/components/ui/EmptyState';
import { getCurrentUser } from '@/lib/auth';

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function InspectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = getCurrentUser();

  const [inspection, setInspection] = useState<InspectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get<InspectionDetail>(`/api/inspections/${id}`);
      setInspection(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load inspection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const updateStatus = async (status: InspectionStatus) => {
    if (!inspection) return;
    setUpdatingStatus(true);
    try {
      await api.patch(`/api/inspections/${inspection.id}/status`, { status });
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update status.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  if (loading) return <div className="p-6"><LoadingSpinner className="py-20" label="Loading inspection…" /></div>;
  if (error) return <div className="p-6"><ErrorAlert message={error} /></div>;
  if (!inspection) return null;

  const canEdit = user?.role !== 'INSPECTOR' || inspection.inspector_id === user?.id;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-sm">
        <button onClick={() => navigate('/inspections')} className="flex items-center gap-1 text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-4 w-4" /> Inspections
        </button>
        <span className="text-slate-300">/</span>
        <span className="font-mono text-slate-700 font-medium">{inspection.inspection_number}</span>
      </div>

      {/* Header row */}
      <div className="flex flex-wrap items-start gap-4 justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 font-mono">{inspection.inspection_number}</h1>
            <StatusBadge status={inspection.status} />
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {inspection.product.product_name} · {inspection.product.product_code}
          </p>
        </div>

        {/* Status actions */}
        {canEdit && (
          <div className="flex gap-2">
            {inspection.status === 'DRAFT' && (
              <button
                id="btn-start-inspection"
                onClick={() => updateStatus('IN_PROGRESS')}
                disabled={updatingStatus}
                className="flex items-center gap-2 rounded-md bg-blue-700 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-60 transition-colors"
              >
                <Play className="h-3.5 w-3.5" />
                {updatingStatus ? 'Updating…' : 'Start Inspection'}
              </button>
            )}
            {inspection.status === 'IN_PROGRESS' && (
              <button
                id="btn-complete-inspection"
                onClick={() => updateStatus('COMPLETED')}
                disabled={updatingStatus}
                className="flex items-center gap-2 rounded-md bg-green-700 px-3 py-2 text-xs font-semibold text-white hover:bg-green-800 disabled:opacity-60 transition-colors"
              >
                <CheckCircle className="h-3.5 w-3.5" />
                {updatingStatus ? 'Updating…' : 'Mark Complete'}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Meta cards */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            <Package className="h-4 w-4" /> Product
          </div>
          <p className="font-medium text-slate-900 text-sm">{inspection.product.product_name}</p>
          <p className="text-xs text-slate-500 mt-1">Code: {inspection.product.product_code}</p>
          {inspection.product.category && <p className="text-xs text-slate-500">Category: {inspection.product.category}</p>}
          {inspection.product.manufacturer && <p className="text-xs text-slate-500">Manufacturer: {inspection.product.manufacturer}</p>}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            <User2 className="h-4 w-4" /> Inspector
          </div>
          <p className="font-medium text-slate-900 text-sm">{inspection.inspector.name}</p>
          <p className="text-xs text-slate-500 mt-1">{inspection.inspector.email}</p>
          <p className="text-xs text-slate-400 mt-0.5">{inspection.inspector.role}</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            <Calendar className="h-4 w-4" /> Timeline
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Created</span>
              <span className="text-slate-700 font-medium">{formatDate(inspection.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Started</span>
              <span className="text-slate-700 font-medium">{formatDate(inspection.started_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Completed</span>
              <span className="text-slate-700 font-medium">{formatDate(inspection.completed_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Notes */}
      {inspection.notes && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm mb-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            <FileText className="h-4 w-4" /> Notes
          </div>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{inspection.notes}</p>
        </div>
      )}

      {/* Images */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm mb-4 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <ImageIcon className="h-4 w-4" /> Package Images
            <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-slate-600 font-medium">
              {inspection.images.length}
            </span>
          </div>
          {canEdit && (
            <Link
              to={`/inspections/${inspection.id}/upload`}
              className="text-xs text-blue-600 hover:underline"
            >
              + Add images
            </Link>
          )}
        </div>

        {inspection.images.length === 0 ? (
          <EmptyState
            title="No images uploaded yet"
            description="Upload package images to begin the inspection analysis."
          />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 p-4">
            {inspection.images.map((img) => (
              <div key={img.id} className="group relative rounded-lg border border-slate-200 overflow-hidden bg-slate-50">
                <img
                  src={`${BASE_URL}${img.image_url}`}
                  alt={img.view_type}
                  className="w-full h-28 object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23f1f5f9" width="100" height="100"/></svg>'; }}
                />
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent px-2 py-1.5">
                  <span className="text-white text-[10px] font-semibold">{img.view_type}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compliance Checks — stub placeholder */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Compliance Checks</div>
        </div>
        <div className="p-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 border border-amber-200 px-4 py-2 text-xs font-medium text-amber-700">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
            AI Agents not yet implemented — Compliance analysis will appear here in Phase 2
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Compliance checks will be automatically generated once Label, Quantity, and Declaration agents are implemented.
          </p>
        </div>
      </div>
    </div>
  );
}
