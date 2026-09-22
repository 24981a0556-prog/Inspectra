import type { InspectionStatus, ComplianceStatus } from '@/types';
import { cn } from '@/lib/utils';

type Status = InspectionStatus | ComplianceStatus;

const STATUS_STYLES: Record<string, string> = {
  // Inspection statuses
  DRAFT:            'bg-slate-100 text-slate-700 border-slate-200',
  IN_PROGRESS:      'bg-blue-50  text-blue-700  border-blue-200',
  COMPLETED:        'bg-green-50 text-green-700 border-green-200',
  REQUIRES_REVIEW:  'bg-amber-50 text-amber-700 border-amber-200',
  CLOSED:           'bg-gray-100 text-gray-500  border-gray-200',
  // Compliance statuses
  NOT_CHECKED:      'bg-slate-100 text-slate-600 border-slate-200',
  PROCESSING:       'bg-blue-50  text-blue-600  border-blue-200',
  PASS:             'bg-green-50 text-green-700 border-green-200',
  FAIL:             'bg-red-50   text-red-700   border-red-200',
  NEEDS_VERIFICATION: 'bg-amber-50 text-amber-700 border-amber-200',
  NOT_APPLICABLE:   'bg-gray-100 text-gray-400  border-gray-200',
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT:             'Draft',
  IN_PROGRESS:       'In Progress',
  COMPLETED:         'Completed',
  REQUIRES_REVIEW:   'Needs Review',
  CLOSED:            'Closed',
  NOT_CHECKED:       'Not Checked',
  PROCESSING:        'Processing',
  PASS:              'Pass',
  FAIL:              'Fail',
  NEEDS_VERIFICATION:'Needs Verification',
  NOT_APPLICABLE:    'N/A',
};

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-600 border-slate-200';
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        style,
        className
      )}
    >
      {label}
    </span>
  );
}
