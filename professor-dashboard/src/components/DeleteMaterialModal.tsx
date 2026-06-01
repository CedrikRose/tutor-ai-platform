interface DeleteMaterialModalProps {
  materialName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export default function DeleteMaterialModal({
  materialName,
  onConfirm,
  onCancel,
  isDeleting = false,
}: DeleteMaterialModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 rounded-lg shadow-xl max-w-md w-full border border-slate-700">
        <div className="p-6">
          {/* Warning Icon */}
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 rounded-full bg-red-900/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
          </div>

          {/* Title */}
          <h3 className="text-xl font-bold text-slate-100 text-center mb-4">
            Material löschen?
          </h3>

          {/* Material Name */}
          <p className="text-slate-300 text-center mb-4">
            Möchtest du das Material <strong className="text-slate-100">"{materialName}"</strong> wirklich löschen?
          </p>

          <p className="text-sm text-slate-400 text-center mb-6">
            Diese Aktion kann nicht rückgängig gemacht werden.
          </p>

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
              type="button"
              onClick={onConfirm}
              disabled={isDeleting}
              className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDeleting ? 'Wird gelöscht...' : 'Löschen'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
