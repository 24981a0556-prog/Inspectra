import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import api from '@/lib/api';
import type { Inspection, InspectionStatus } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

const ALL_STATUSES: InspectionStatus[] = [
  'DRAFT', 'IN_PROGRESS', 'COMPLETED', 'REQUIRES_REVIEW', 'CLOSED',
];

export default function InspectionsListPage() {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<InspectionStatus | ''>('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const params: Record<string, string> = { limit: '100' };
        if (statusFilter) params.status = statusFilter;
        const res = await api.get<Inspection[]>('/api/inspections/', { params });
        setInspections(res.data);
      } catch {
        setError('Failed to load inspections.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [statusFilter]);

  const filtered = inspections.filter((i) =>
    search ? i.inspection_number.toLowerCase().includes(search.toLowerCase()) : true
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Inspections</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            All packaged commodity inspections
          </p>
        </div>
        <Link
          to="/inspections/new"
          id="btn-new-inspection"
          className="flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Inspection
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm flex-1 min-w-48">
          <Search className="h-4 w-4 text-slate-400 flex-shrink-0" />
          <input
            id="inp-search"
            placeholder="Search by inspection number…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="outline-none bg-transparent flex-1 text-sm placeholder:text-slate-400"
          />
        </div>
        <select
          id="sel-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as InspectionStatus | '')}
          className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      {loading && <LoadingSpinner className="py-20" label="Loading inspections…" />}
      {error && <ErrorAlert message={error} />}

      {!loading && !error && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          {filtered.length === 0 ? (
            <EmptyState
              title="No inspections found"
              description={statusFilter ? 'Try a different status filter.' : 'Create your first inspection to get started.'}
              action={
                !statusFilter
                  ? <Link to="/inspections/new" className="text-xs text-blue-600 hover:underline">New Inspection →</Link>
                  : undefined
              }
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Inspection #</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Started</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((insp, idx) => (
                  <tr
                    key={insp.id}
                    className={`border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors ${idx % 2 === 0 ? '' : 'bg-slate-50/30'}`}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-800">{insp.inspection_number}</td>
                    <td className="px-4 py-3"><StatusBadge status={insp.status} /></td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{formatDate(insp.created_at)}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {insp.started_at ? formatDate(insp.started_at) : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/inspections/${insp.id}`}
                        className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <p className="mt-3 text-xs text-slate-400 text-right">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</p>
      )}
    </div>
  );
}
