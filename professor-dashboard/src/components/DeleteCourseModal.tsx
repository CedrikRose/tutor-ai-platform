import { useState } from 'react';

interface DeleteCourseModalProps {
  courseName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export default function DeleteCourseModal({
  courseName,
  onConfirm,
  onCancel,
  isDeleting = false,
}: DeleteCourseModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const isConfirmValid = confirmText === 'Bestätigen';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isConfirmValid) {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 rounded-lg shadow-xl max-w-md w-full border border-slate-700">
        <div className="p-6">
          {/* Warning Icon */}
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 rounded-full bg-red-900/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>

          {/* Title */}
          <h3 className="text-xl font-bold text-slate-100 text-center mb-2">
            Kurs löschen?
          </h3>

          {/* Warning Message */}
          <div className="mb-4 p-3 bg-red-900/20 border border-red-800/50 rounded-md">
            <p className="text-sm text-red-300">
              <strong>Achtung:</strong> Diese Aktion kann nicht rückgängig gemacht werden!
            </p>
          </div>

          {/* Course Name */}
          <p className="text-slate-300 text-center mb-4">
            Du bist dabei, den Kurs <strong className="text-slate-100">"{courseName}"</strong> zu löschen.
          </p>

          <p className="text-sm text-slate-400 text-center mb-4">
            Alle Materialien, Analysen und zugehörigen Daten werden permanent gelöscht.
          </p>

          {/* Confirmation Input */}
          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label htmlFor="confirmText" className="block text-sm font-medium text-slate-300 mb-2">
                Gib <span className="font-bold text-slate-100">"Bestätigen"</span> ein, um fortzufahren:
              </label>
              <input
                id="confirmText"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="Bestätigen"
                autoComplete="off"
                autoFocus
                disabled={isDeleting}
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onCancel}
                disabled={isDeleting}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium py-2 px-4 rounded-md transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                disabled={!isConfirmValid || isDeleting}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? 'Wird gelöscht...' : 'Kurs löschen'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
