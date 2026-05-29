import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { de } from 'date-fns/locale/de';

// Helper to parse UTC timestamp and format in local timezone
const formatLocalTime = (utcTimestamp: string) => {
  // The timestamp from the server is in UTC, but doesn't have 'Z' suffix
  // so we add it to make it clear it's UTC
  const date = new Date(utcTimestamp.endsWith('Z') ? utcTimestamp : utcTimestamp + 'Z');
  return format(date, 'dd.MM.yyyy HH:mm', { locale: de });
};

interface Finding {
  finding_id: string;
  conversation_id: string;
  category: string;
  title: string;
  description: string;
  reasoning: string;
  reference_exchange_numbers: number[];
  related_material_id: string | null;
  related_topic: string | null;
  created_at: string;
  analysis_model: string | null;
  conversation_title: string | null;
  exchange_count: number;
}

interface FindingsListProps {
  courseId: string;
}

const CATEGORY_LABELS: Record<string, { label: string; color: string; icon: string }> = {
  difficulty: {
    label: 'Schwierigkeit',
    color: 'bg-red-900/30 text-red-400 border-red-700',
    icon: '⚠️',
  },
  feedback_professor: {
    label: 'Feedback zur Lehre',
    color: 'bg-purple-900/30 text-purple-400 border-purple-700',
    icon: '📚',
  },
  feedback_chatbot: {
    label: 'Feedback zum Bot',
    color: 'bg-blue-900/30 text-blue-400 border-blue-700',
    icon: '🤖',
  },
  question_pattern: {
    label: 'Fragemuster',
    color: 'bg-yellow-900/30 text-yellow-400 border-yellow-700',
    icon: '🔄',
  },
};

export default function FindingsList({ courseId }: FindingsListProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [offset, setOffset] = useState(0);
  const [allFindings, setAllFindings] = useState<Finding[]>([]);
  const LIMIT = 50;

  // Fetch findings with pagination
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['findings', courseId, selectedCategory, offset],
    queryFn: async () => {
      const params = new URLSearchParams({
        course_id: courseId,
        limit: String(LIMIT),
        offset: String(offset),
      });
      if (selectedCategory) {
        params.append('category', selectedCategory);
      }

      const response = await fetch(
        `/api/professor/findings?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch findings');
      }

      return response.json();
    },
  });

  // Update findings when data changes
  useEffect(() => {
    if (data?.findings) {
      if (offset === 0) {
        // First load or filter change - replace all
        setAllFindings(data.findings);
      } else {
        // Load more - append
        setAllFindings((prev) => [...prev, ...data.findings]);
      }
    }
  }, [data, offset]);

  // Reset when category changes
  const handleCategoryChange = (category: string | null) => {
    setSelectedCategory(category);
    setOffset(0);
    setAllFindings([]);
  };

  const handleLoadMore = () => {
    setOffset((prev) => prev + LIMIT);
  };

  // Fetch finding details when clicked
  const { data: findingDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['finding-detail', selectedFinding?.finding_id],
    queryFn: async () => {
      if (!selectedFinding) return null;

      const response = await fetch(
        `/api/professor/findings/${selectedFinding.finding_id}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch finding detail');
      }

      return response.json();
    },
    enabled: !!selectedFinding && showDetailModal,
  });

  const totalCount = data?.total_count || 0;
  const hasMore = allFindings.length < totalCount;

  const handleFindingClick = (finding: Finding) => {
    setSelectedFinding(finding);
    setShowDetailModal(true);
  };

  if (isLoading && offset === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-slate-400">Lade Erkenntnisse...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filter Buttons */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleCategoryChange(null)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            selectedCategory === null
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          Alle ({totalCount})
        </button>
        {Object.entries(CATEGORY_LABELS).map(([category, { label, icon }]) => {
          return (
            <button
              key={category}
              onClick={() => handleCategoryChange(category)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedCategory === category
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {icon} {label}
            </button>
          );
        })}
      </div>

      {/* Findings List */}
      {allFindings.length === 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 text-center">
          <p className="text-slate-400">
            {selectedCategory
              ? 'Keine Erkenntnisse in dieser Kategorie gefunden.'
              : 'Noch keine Erkenntnisse vorhanden. Warte auf die nächste automatische Analyse.'}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {allFindings.map((finding) => {
            const categoryInfo = CATEGORY_LABELS[finding.category] || {
              label: finding.category,
              color: 'bg-slate-700 text-slate-300',
              icon: '📝',
            };

            return (
              <div
                key={finding.finding_id}
                onClick={() => handleFindingClick(finding)}
                className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-blue-500 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-3 py-1 rounded-md text-xs font-medium border ${categoryInfo.color}`}
                    >
                      {categoryInfo.icon} {categoryInfo.label}
                    </span>
                    {finding.related_topic && (
                      <span className="px-2 py-1 rounded-md text-xs bg-slate-700 text-slate-300">
                        {finding.related_topic}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-500">
                    {formatLocalTime(finding.created_at)}
                  </span>
                </div>

                <h3 className="text-base font-semibold text-slate-200 mb-2">
                  {finding.title}
                </h3>

                <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                  {finding.description}
                </p>

                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Chat: {finding.conversation_title}</span>
                  <span>
                    {finding.exchange_count} Exchange{finding.exchange_count !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            );
          })}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="flex justify-center mt-6">
              <button
                onClick={handleLoadMore}
                disabled={isFetching}
                className={`px-6 py-3 rounded-md font-medium transition-colors ${
                  isFetching
                    ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                    : 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                }`}
              >
                {isFetching ? (
                  <span className="flex items-center gap-2">
                    <svg
                      className="animate-spin h-4 w-4"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Lade mehr...
                  </span>
                ) : (
                  `Mehr laden (${allFindings.length} von ${totalCount})`
                )}
              </button>
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedFinding && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-800 border-b border-slate-700 p-4 flex justify-between items-center">
              <h2 className="text-xl font-semibold text-slate-200">
                Erkenntnis Details
              </h2>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Category and Meta */}
              <div className="flex items-center gap-2">
                <span
                  className={`px-3 py-1 rounded-md text-sm font-medium border ${
                    CATEGORY_LABELS[selectedFinding.category]?.color ||
                    'bg-slate-700 text-slate-300'
                  }`}
                >
                  {CATEGORY_LABELS[selectedFinding.category]?.icon || '📝'}{' '}
                  {CATEGORY_LABELS[selectedFinding.category]?.label ||
                    selectedFinding.category}
                </span>
                {selectedFinding.related_topic && (
                  <span className="px-2 py-1 rounded-md text-sm bg-slate-700 text-slate-300">
                    {selectedFinding.related_topic}
                  </span>
                )}
              </div>

              {/* Title */}
              <div>
                <h3 className="text-lg font-semibold text-slate-200 mb-2">
                  {selectedFinding.title}
                </h3>
              </div>

              {/* Description */}
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-2">
                  Beschreibung
                </h4>
                <p className="text-slate-300">{selectedFinding.description}</p>
              </div>

              {/* Reasoning */}
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-2">
                  Begründung
                </h4>
                <p className="text-slate-300">{selectedFinding.reasoning}</p>
              </div>

              {/* Referenced Exchanges */}
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-3">
                  Betroffene Chat-Exchanges
                </h4>
                {isLoadingDetail ? (
                  <div className="text-slate-500">Lade Exchanges...</div>
                ) : (
                  <div className="space-y-4">
                    {findingDetail?.exchanges?.map((exchange: any) => (
                      <div
                        key={exchange.exchange_number}
                        className="bg-slate-900 border border-slate-700 rounded-lg p-4"
                      >
                        <div className="text-xs text-slate-500 mb-2">
                          Exchange #{exchange.exchange_number}
                        </div>
                        <div className="space-y-3">
                          <div>
                            <span className="text-blue-400 font-medium">
                              Student:
                            </span>
                            <p className="text-slate-300 mt-1">
                              {exchange.user_question}
                            </p>
                          </div>
                          <div>
                            <span className="text-green-400 font-medium">
                              Tutor:
                            </span>
                            <p className="text-slate-300 mt-1">
                              {exchange.assistant_answer}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="text-xs text-slate-500 space-y-1">
                <div>Chat: {selectedFinding.conversation_title}</div>
                <div>
                  Erstellt am:{' '}
                  {formatLocalTime(selectedFinding.created_at)}
                </div>
                {selectedFinding.analysis_model && (
                  <div>Modell: {selectedFinding.analysis_model}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
