import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface ManualAnalysisButtonProps {
  courseId: string;
}

export default function ManualAnalysisButton({ courseId }: ManualAnalysisButtonProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const analysisMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/professor/trigger-analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ course_id: courseId }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Analysis failed');
      }

      return response.json();
    },
    onSuccess: (data) => {
      setResult(`Analyse erfolgreich! ${data.snapshots_created} Snapshots erstellt, ${data.findings_created} Erkenntnisse gefunden.`);
      // Refresh findings list
      queryClient.invalidateQueries({ queryKey: ['findings', courseId] });
      setIsRunning(false);
    },
    onError: (error: Error) => {
      setResult(`Fehler: ${error.message}`);
      setIsRunning(false);
    },
  });

  const handleAnalyze = () => {
    setIsRunning(true);
    setResult(null);
    analysisMutation.mutate();
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-base font-semibold text-slate-200">Chat-Analyse</h3>
          <p className="text-sm text-slate-400 mt-1">
            Analysiere alle noch nicht analysierten Chats für diesen Kurs
          </p>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={isRunning}
          className={`px-4 py-2 rounded-md font-medium transition-colors ${
            isRunning
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isRunning ? (
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
              Analysiere...
            </span>
          ) : (
            'Analyse starten'
          )}
        </button>
      </div>

      {result && (
        <div
          className={`mt-3 p-3 rounded-md text-sm ${
            result.includes('Fehler')
              ? 'bg-red-900/30 border border-red-700 text-red-300'
              : 'bg-green-900/30 border border-green-700 text-green-300'
          }`}
        >
          {result}
        </div>
      )}
    </div>
  );
}
