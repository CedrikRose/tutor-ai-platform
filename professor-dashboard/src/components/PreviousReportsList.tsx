import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getReports, getReportDetail } from '../services/analysisApi';
import type { ReportDetail } from '../types/analysis';

interface Props {
  courseId: string;
  excludeLatest?: string;
}

export default function PreviousReportsList({ courseId, excludeLatest }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 10;

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['reports-list', courseId, offset],
    queryFn: () => getReports(courseId, limit + 1, offset), // +1 to check if more exist
    enabled: !!courseId,
  });

  // Filter out the latest report if provided
  const filteredReports = reports.filter((r) => r.report_id !== excludeLatest);
  const displayReports = filteredReports.slice(0, limit);
  const hasMore = filteredReports.length > limit;

  const { data: expandedReport, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['report-detail', expandedId],
    queryFn: () => getReportDetail(expandedId!),
    enabled: !!expandedId,
  });

  const handleToggle = (reportId: string) => {
    setExpandedId(expandedId === reportId ? null : reportId);
  };

  const handleLoadMore = () => {
    setOffset((prev) => prev + limit);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  if (isLoading && offset === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (displayReports.length === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center">
        <p className="text-slate-400">Keine früheren Berichte vorhanden.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-slate-200">Frühere Berichte</h3>
      </div>

      <div className="divide-y divide-slate-700">
        {displayReports.map((report) => (
          <div key={report.report_id} className="transition-colors">
            <button
              onClick={() => handleToggle(report.report_id)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-750 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-slate-200 font-medium">
                    {formatDate(report.end_date)}
                  </span>
                  <span className="text-slate-500 text-sm">
                    ({report.days_back} Tage)
                  </span>
                  {report.statistics && (
                    <span className="text-slate-400 text-sm">
                      {report.statistics.total_findings} Erkenntnisse
                    </span>
                  )}
                </div>
                <p className="text-slate-500 text-xs">
                  {formatDate(report.start_date)} - {formatDate(report.end_date)}
                </p>
              </div>

              <svg
                className={`w-5 h-5 text-slate-400 transition-transform flex-shrink-0 ${
                  expandedId === report.report_id ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {expandedId === report.report_id && (
              <div className="px-4 pb-4 border-t border-slate-700">
                {isLoadingDetail ? (
                  <div className="py-8 text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
                  </div>
                ) : expandedReport ? (
                  <ReportContent report={expandedReport} />
                ) : (
                  <div className="py-4 text-center text-slate-400">
                    Fehler beim Laden des Berichts
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {hasMore && (
        <div className="p-4 border-t border-slate-700 text-center">
          <button
            onClick={handleLoadMore}
            disabled={isLoading}
            className="text-blue-400 hover:text-blue-300 disabled:text-slate-500 text-sm font-medium"
          >
            {isLoading ? 'Wird geladen...' : 'Mehr laden...'}
          </button>
        </div>
      )}
    </div>
  );
}

function ReportContent({ report }: { report: ReportDetail }) {
  return (
    <div className="mt-4 space-y-4">
      <div className="prose prose-invert prose-sm max-w-none">
        <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
          {report.report_text}
        </div>
      </div>

      {report.statistics && (
        <div className="border-t border-slate-700 pt-3 mt-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-slate-500 text-xs">Erkenntnisse</p>
              <p className="text-slate-200 font-medium">{report.statistics.total_findings}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs">Konversationen</p>
              <p className="text-slate-200 font-medium">{report.statistics.unique_conversations}</p>
            </div>
            {Object.keys(report.statistics.by_category).length > 0 && (
              <div className="col-span-2 sm:col-span-1">
                <p className="text-slate-500 text-xs mb-1">Nach Kategorie</p>
                {Object.entries(report.statistics.by_category).map(([category, count]) => (
                  <p key={category} className="text-slate-300 text-xs">
                    {category}: {count}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
