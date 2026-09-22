import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, Package, Users, TrendingUp, Plus, ArrowRight } from 'lucide-react';
import api from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import type { DashboardStats, Inspection, InspectionStatus } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';
import { EmptyState } from '@/components/ui/EmptyState';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

const STAT_CARDS = (stats: DashboardStats) => [
  {
    label: 'Total Inspections',
    value: stats.total_inspections,
    icon: ClipboardList,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
  },
  {
    label: 'Completed',
    value: stats.by_status['COMPLETED'] ?? 0,
    icon: TrendingUp,
    color: 'text-green-600',
    bg: 'bg-green-50',
  },
  {
    label: 'Needs Review',
    value: stats.by_status['REQUIRES_REVIEW'] ?? 0,
    icon: ClipboardList,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
  },
  {
    label: 'Products Registered',
    value: stats.total_products,
    icon: Package,
    color: 'text-purple-600',
    bg: 'bg-purple-50',
  },
];

export default function DashboardPage() {
  const user = getCurrentUser();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, recentRes] = await Promise.all([
          api.get<DashboardStats>('/api/dashboard/stats'),
          api.get<Inspection[]>('/api/dashboard/recent-inspections'),
        ]);
        setStats(statsRes.data);
        setRecent(recentRes.data);
      } catch {
        setError('Failed to load dashboard data. Please refresh.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Welcome back, {user?.name}. Here's your inspection overview.
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

      {loading && <LoadingSpinner className="py-20" label="Loading dashboard…" />}
      {error && <ErrorAlert message={error} />}

      {stats && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {STAT_CARDS(stats).map((card) => (
              <div key={card.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${card.bg}`}>
                    <card.icon className={`h-5 w-5 ${card.color}`} />
                  </div>
                </div>
                <p className="text-2xl font-bold text-slate-900">{card.value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{card.label}</p>
              </div>
            ))}
          </div>

          {/* Status breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
            <div className="lg:col-span-1 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900 mb-3">By Status</h2>
              <div className="space-y-2">
                {(Object.entries(stats.by_status) as [InspectionStatus, number][]).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <StatusBadge status={status} />
                    <span className="text-sm font-semibold text-slate-700">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent inspections */}
            <div className="lg:col-span-2 rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between px-4 pt-4 pb-2">
                <h2 className="text-sm font-semibold text-slate-900">Recent Inspections</h2>
                <Link to="/inspections" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {recent.length === 0 ? (
                <EmptyState
                  title="No inspections yet"
                  description="Create your first inspection to get started."
                  action={<Link to="/inspections/new" className="text-xs text-blue-600 hover:underline">New Inspection →</Link>}
                />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-y border-slate-100 bg-slate-50">
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">Inspection #</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">Status</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-slate-500">Date</th>
                      <th className="px-4 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((insp) => (
                      <tr key={insp.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs font-medium text-slate-800">{insp.inspection_number}</td>
                        <td className="px-4 py-3"><StatusBadge status={insp.status} /></td>
                        <td className="px-4 py-3 text-slate-500 text-xs">{formatDate(insp.created_at)}</td>
                        <td className="px-4 py-3 text-right">
                          <Link to={`/inspections/${insp.id}`} className="text-xs text-blue-600 hover:underline">
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
