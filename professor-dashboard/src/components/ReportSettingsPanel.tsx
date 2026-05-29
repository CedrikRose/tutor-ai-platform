import { useState } from 'react';
import { updateReportSettings } from '../services/analysisApi';
import type { ReportSettings } from '../types/analysis';

interface Props {
  courseId: string;
  initialSettings: ReportSettings;
  onSettingsUpdated?: () => void;
}

export default function ReportSettingsPanel({ courseId, initialSettings, onSettingsUpdated }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [daysBack, setDaysBack] = useState(initialSettings.report_days_back || 7);
  const [emailsEnabled, setEmailsEnabled] = useState(initialSettings.report_emails_enabled || false);
  const [emails, setEmails] = useState<string[]>(initialSettings.report_recipient_emails || []);
  const [emailInput, setEmailInput] = useState('');

  const handleAddEmail = () => {
    const trimmedEmail = emailInput.trim();
    if (!trimmedEmail) return;

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Ungültige E-Mail-Adresse');
      return;
    }

    if (emails.includes(trimmedEmail)) {
      setError('Diese E-Mail-Adresse wurde bereits hinzugefügt');
      return;
    }

    if (emails.length >= 3) {
      setError('Maximal 3 E-Mail-Adressen erlaubt');
      return;
    }

    setEmails([...emails, trimmedEmail]);
    setEmailInput('');
    setError(null);
  };

  const handleRemoveEmail = (email: string) => {
    setEmails(emails.filter((e) => e !== email));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await updateReportSettings(courseId, {
        report_days_back: daysBack,
        report_recipient_emails: emails,
        report_emails_enabled: emailsEnabled,
      });

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);

      if (onSettingsUpdated) {
        onSettingsUpdated();
      }
    } catch (err: any) {
      console.error('Error updating settings:', err);
      setError(err.response?.data?.detail || 'Fehler beim Speichern der Einstellungen');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg mb-6 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-slate-200 font-medium">Report-Einstellungen</span>
        </div>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="p-4 border-t border-slate-700 space-y-4">
          {/* Days Back Setting */}
          <div>
            <label htmlFor="days-back" className="block text-slate-300 text-sm font-medium mb-2">
              Standard-Zeitraum (Tage)
            </label>
            <input
              id="days-back"
              type="number"
              min="1"
              max="50"
              value={daysBack}
              onChange={(e) => setDaysBack(Number(e.target.value))}
              className="w-full sm:w-32 bg-slate-700 border border-slate-600 text-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-slate-500 text-xs mt-1">Zwischen 1 und 50 Tagen</p>
          </div>

          {/* Email Settings */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <input
                id="emails-enabled"
                type="checkbox"
                checked={emailsEnabled}
                onChange={(e) => setEmailsEnabled(e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500"
              />
              <label htmlFor="emails-enabled" className="text-slate-300 text-sm font-medium">
                E-Mail-Versand aktiviert
              </label>
            </div>
            <p className="text-slate-500 text-xs mb-3">
              (Email-Feature wird in einer zukünftigen Version implementiert)
            </p>

            <label className="block text-slate-300 text-sm font-medium mb-2">
              E-Mail-Adressen (max. 3)
            </label>

            <div className="flex gap-2 mb-2">
              <input
                type="email"
                placeholder="email@example.com"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddEmail()}
                disabled={emails.length >= 3}
                className="flex-1 bg-slate-700 border border-slate-600 text-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleAddEmail}
                disabled={emails.length >= 3}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm"
              >
                Hinzufügen
              </button>
            </div>

            {emails.length > 0 && (
              <div className="space-y-1">
                {emails.map((email) => (
                  <div
                    key={email}
                    className="flex items-center justify-between bg-slate-700 rounded px-3 py-2 text-sm"
                  >
                    <span className="text-slate-200">{email}</span>
                    <button
                      onClick={() => handleRemoveEmail(email)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Save Button */}
          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm font-medium"
            >
              {isSaving ? 'Wird gespeichert...' : 'Speichern'}
            </button>

            {success && (
              <span className="text-green-400 text-sm flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Erfolgreich gespeichert
              </span>
            )}
          </div>

          {error && (
            <div className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded px-3 py-2">
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
