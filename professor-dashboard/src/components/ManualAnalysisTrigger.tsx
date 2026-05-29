/**
 * Manual Analysis Trigger Button
 * Allows professor to run analysis immediately instead of waiting for 4 AM
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Play, Loader2, CheckCircle, AlertCircle, Info } from 'lucide-react';
import axios from 'axios';

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

interface AnalysisStatus {
  pending: number;
  analyzing: number;
  completed_today: number;
  sessions_without_snapshots?: number;
  sessions_with_new_messages?: number;
  can_analyze: boolean;
}

interface TriggerResponse {
  success: boolean;
  snapshots_created: number;
  analyses_completed: number;
  message: string;
}

async function getAnalysisStatus(): Promise<AnalysisStatus> {
  const response = await api.get('/api/professor/analysis-status');
  return response.data;
}

async function triggerAnalysis(): Promise<TriggerResponse> {
  const response = await api.post('/api/professor/trigger-analysis');
  return response.data;
}

export default function ManualAnalysisTrigger() {
  const [showDetails, setShowDetails] = useState(false);
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ['analysisStatus'],
    queryFn: getAnalysisStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const triggerMutation = useMutation({
    mutationFn: triggerAnalysis,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysisStatus'] });
      queryClient.invalidateQueries({ queryKey: ['summaries'] });
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
    },
  });

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2 text-slate-100">
            <Play className="w-5 h-5 text-blue-400" />
            Chat-Analyse
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Analysiere neue Chats sofort (sonst automatisch um 4 Uhr)
          </p>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-slate-400 hover:text-slate-300"
        >
          {showDetails ? 'Weniger' : 'Details'}
        </button>
      </div>

      {/* Status */}
      {status && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 bg-yellow-900/30 border border-yellow-800/50 rounded">
              <div className="text-2xl font-bold text-yellow-400">
                {status.pending}
              </div>
              <div className="text-xs text-yellow-500">Ausstehend</div>
            </div>
            <div className="text-center p-3 bg-blue-900/30 border border-blue-800/50 rounded">
              <div className="text-2xl font-bold text-blue-400">
                {status.analyzing}
              </div>
              <div className="text-xs text-blue-500">In Arbeit</div>
            </div>
            <div className="text-center p-3 bg-green-900/30 border border-green-800/50 rounded">
              <div className="text-2xl font-bold text-green-400">
                {status.completed_today}
              </div>
              <div className="text-xs text-green-500">Heute fertig</div>
            </div>
          </div>

          {status.sessions_without_snapshots !== undefined && status.sessions_without_snapshots > 0 && (
            <div className="mb-4 p-3 bg-purple-900/30 border border-purple-800/50 rounded">
              <div className="text-sm text-purple-300">
                <strong className="text-purple-200">{status.sessions_without_snapshots}</strong> Chat-Sessions
                warten auf erste Analyse
              </div>
            </div>
          )}

          {status.sessions_with_new_messages !== undefined && status.sessions_with_new_messages > 0 && (
            <div className="mb-4 p-3 bg-cyan-900/30 border border-cyan-800/50 rounded">
              <div className="text-sm text-cyan-300">
                <strong className="text-cyan-200">{status.sessions_with_new_messages}</strong> Chat-Sessions
                haben neue Nachrichten seit letzter Analyse
              </div>
            </div>
          )}
        </>
      )}

      {/* Details */}
      {showDetails && (
        <div className="mb-4 p-3 bg-slate-900 border border-slate-700 rounded text-sm text-slate-300">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 mt-0.5 text-slate-500 flex-shrink-0" />
            <div>
              <p className="font-medium mb-2">Wie funktioniert es?</p>
              <ul className="space-y-1 text-xs">
                <li>• <strong>Snapshots:</strong> Neue Chat-Segmente werden erfasst</li>
                <li>• <strong>Analyse:</strong> LLM analysiert Lernfortschritt</li>
                <li>• <strong>Keine Duplikate:</strong> Bereits analysierte Chats werden übersprungen</li>
                <li>• <strong>Um 4 Uhr:</strong> Cron-Job macht dasselbe automatisch</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Trigger Button */}
      <button
        onClick={() => triggerMutation.mutate()}
        disabled={triggerMutation.isPending || !status?.can_analyze}
        className="w-full px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
      >
        {triggerMutation.isPending ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Analysiere Chats...
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            Jetzt analysieren
          </>
        )}
      </button>

      {!status?.can_analyze && !triggerMutation.isPending && (
        <p className="text-sm text-slate-400 text-center mt-2">
          Keine neuen Chats zur Analyse vorhanden
        </p>
      )}

      {/* Success Message */}
      {triggerMutation.isSuccess && triggerMutation.data && (
        <div className="mt-4 p-3 bg-green-900/30 border border-green-800 rounded flex items-start gap-2">
          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-green-300">
            <p className="font-medium">Analyse erfolgreich!</p>
            <p className="mt-1">
              {triggerMutation.data.snapshots_created} Snapshots erstellt,{' '}
              {triggerMutation.data.analyses_completed} Analysen durchgeführt
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {triggerMutation.isError && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-300">
            <p className="font-medium">Fehler bei der Analyse</p>
            <p className="mt-1">
              {(triggerMutation.error as any)?.message || 'Unbekannter Fehler'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
