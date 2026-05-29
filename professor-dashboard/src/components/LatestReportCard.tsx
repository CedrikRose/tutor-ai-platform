import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReportDetail } from "../types/analysis";

interface Props {
  report: ReportDetail | null;
  isLoading: boolean;
}

export default function LatestReportCard({ report, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-700 rounded w-1/3" />
          <div className="space-y-2">
            <div className="h-4 bg-slate-700 rounded" />
            <div className="h-4 bg-slate-700 rounded w-5/6" />
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 text-center">
        <svg className="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-slate-400 text-lg mb-2">Noch keine Berichte erstellt</p>
        <p className="text-slate-500 text-sm">Klicken Sie auf "Bericht erstellen", um Ihren ersten Bericht zu generieren.</p>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("de-DE", { day: "2-digit", month: "long", year: "numeric" });
  };

  const { statistics } = report;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
      <div className="border-b border-slate-700 pb-4">
        <h2 className="text-xl font-semibold text-slate-100 mb-1">Neuester Bericht</h2>
        <p className="text-slate-400 text-sm">Erstellt am {formatDate(report.generated_at)}</p>
        <p className="text-slate-500 text-sm">Zeitraum: {formatDate(report.start_date)} bis {formatDate(report.end_date)} ({report.days_back} Tage)</p>
      </div>

      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1 className="text-2xl font-bold text-slate-100 mt-6 mb-4">{children}</h1>,
            h2: ({ children }) => <h2 className="text-xl font-semibold text-slate-100 mt-6 mb-3">{children}</h2>,
            h3: ({ children }) => <h3 className="text-lg font-semibold text-slate-100 mt-4 mb-2">{children}</h3>,
            p: ({ children }) => <p className="text-slate-300 leading-relaxed mb-3">{children}</p>,
            ul: ({ children }) => <ul className="list-disc list-inside text-slate-300 space-y-1 mb-3">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside text-slate-300 space-y-1 mb-3">{children}</ol>,
            li: ({ children }) => <li className="ml-4">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-slate-100">{children}</strong>,
            table: ({ children }) => (
              <div className="overflow-x-auto my-4">
                <table className="min-w-full border border-slate-600 rounded-lg">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="bg-slate-700">{children}</thead>,
            tbody: ({ children }) => <tbody className="divide-y divide-slate-600">{children}</tbody>,
            tr: ({ children }) => <tr>{children}</tr>,
            th: ({ children }) => <th className="px-4 py-2 text-left text-slate-200 font-semibold border-b border-slate-600">{children}</th>,
            td: ({ children }) => <td className="px-4 py-2 text-slate-300">{children}</td>,
          }}
        >
          {report.report_text}
        </ReactMarkdown>
      </div>

      {statistics && (
        <div className="border-t border-slate-700 pt-4">
          <h3 className="text-slate-200 font-medium mb-3">Statistiken</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-slate-700 rounded-lg p-3">
              <p className="text-slate-400 text-xs mb-1">Erkenntnisse</p>
              <p className="text-slate-100 text-2xl font-semibold">{statistics.total_findings}</p>
            </div>
            <div className="bg-slate-700 rounded-lg p-3">
              <p className="text-slate-400 text-xs mb-1">Konversationen</p>
              <p className="text-slate-100 text-2xl font-semibold">{statistics.unique_conversations}</p>
            </div>
            {Object.keys(statistics.by_category).length > 0 && (
              <div className="bg-slate-700 rounded-lg p-3">
                <p className="text-slate-400 text-xs mb-2">Nach Kategorie</p>
                <div className="space-y-1">
                  {Object.entries(statistics.by_category).map(([category, count]) => (
                    <div key={category} className="flex justify-between text-sm">
                      <span className="text-slate-300 capitalize">{getCategoryLabel(category)}</span>
                      <span className="text-slate-100 font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          {statistics.topics_mentioned && statistics.topics_mentioned.length > 0 && (
            <div className="mt-4">
              <p className="text-slate-400 text-xs mb-2">Häufigste Themen</p>
              <div className="flex flex-wrap gap-2">
                {statistics.topics_mentioned.slice(0, 10).map((topic) => (
                  <span key={topic.topic} className="bg-blue-900/30 text-blue-300 text-xs px-2 py-1 rounded">{topic.topic} ({topic.count})</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = { difficulty: "Schwierigkeiten", feedback_professor: "Feedback (Professor)", feedback_chatbot: "Feedback (Chatbot)", question_pattern: "Fragemuster" };
  return labels[category] || category;
}
