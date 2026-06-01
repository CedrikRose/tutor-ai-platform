/**
 * Scheduler Status Component
 * Shows the status of automated daily chat analysis
 */
import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle, AlertCircle } from 'lucide-react';
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

interface SchedulerJob {
  id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
}

interface SchedulerStatus {
  running: boolean;
  jobs: SchedulerJob[];
  message: string;
}

async function getSchedulerStatus(): Promise<SchedulerStatus> {
  const response = await api.get('/professor/scheduler-status');
  return response.data;
}

export default function SchedulerStatus() {
  const { data: status, isLoading } = useQuery({
    queryKey: ['schedulerStatus'],
    queryFn: getSchedulerStatus,
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <div className="text-slate-400 text-sm">Lade Scheduler-Status...</div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`mt-0.5 ${status.running ? 'text-green-400' : 'text-red-400'}`}>
          {status.running ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-100 mb-1">
            Automatische Analyse
          </h3>

          <p className="text-xs text-slate-400 mb-2">
            {status.message}
          </p>

          {/* Jobs */}
          {status.jobs && status.jobs.length > 0 && (
            <div className="space-y-2">
              {status.jobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-slate-900 border border-slate-700 rounded p-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-blue-400" />
                      <span className="text-xs font-medium text-slate-300">
                        {job.name}
                      </span>
                    </div>
                    {job.next_run_time && (
                      <span className="text-xs text-slate-500">
                        {new Date(job.next_run_time).toLocaleString('de-DE', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Info */}
          <div className="mt-3 text-xs text-slate-500 bg-slate-900/50 rounded p-2">
            <p>
              💡 <strong>Hinweis:</strong> Täglich um 3:00 Uhr werden automatisch
              alle nicht analysierten Chats in allen aktiven Kursen analysiert.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
