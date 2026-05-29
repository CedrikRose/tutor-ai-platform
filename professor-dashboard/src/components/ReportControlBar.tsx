import { useState } from 'react';
import { generateReport } from '../services/analysisApi';

interface Props {
  courseId: string;
  defaultDaysBack: number;
  onReportGenerated: () => void;
}

export default function ReportControlBar({ courseId, defaultDaysBack, onReportGenerated }: Props) {
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      await generateReport(courseId, endDate);
      onReportGenerated();
    } catch (err: any) {
      console.error('Error generating report:', err);
      setError(err.response?.data?.detail || 'Fehler beim Erstellen des Berichts');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-slate-400 text-sm">Zeitraum:</label>
          <span className="text-slate-200 font-medium">{defaultDaysBack} Tage</span>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="end-date" className="text-slate-400 text-sm">
            Bis Datum:
          </label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            max={new Date().toISOString().split('T')[0]}
            disabled={isGenerating}
            className="bg-slate-700 border border-slate-600 text-slate-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="ml-auto bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white px-4 py-2 rounded-md flex items-center gap-2 text-sm font-medium transition-colors"
        >
          {isGenerating ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Bericht wird erstellt...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Bericht erstellen
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mt-3 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded px-3 py-2">
          {error}
        </div>
      )}
    </div>
  );
}
