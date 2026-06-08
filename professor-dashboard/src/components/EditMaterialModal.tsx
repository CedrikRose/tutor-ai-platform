import { useState, useEffect } from 'react';
import { courseApi } from '../services/api';
import type { CourseMaterial } from '../types';

interface EditMaterialModalProps {
  material: CourseMaterial;
  onClose: () => void;
  onSaved: () => void;
}

export default function EditMaterialModal({ material, onClose, onSaved }: EditMaterialModalProps) {
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchContent();
  }, [material.material_id]);

  const fetchContent = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await courseApi.getMaterialContent(material.material_id);
      setContent(response.content);
      setOriginalContent(response.content);
    } catch (err: any) {
      console.error('Error fetching material content:', err);
      setError(err.response?.data?.detail || 'Fehler beim Laden des Contents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (content === originalContent) return;

    setIsSaving(true);
    setError(null);

    try {
      await courseApi.updateMaterialContent(material.material_id, content);
      onSaved();
    } catch (err: any) {
      console.error('Error saving material content:', err);
      setError(err.response?.data?.detail || 'Fehler beim Speichern');
      setIsSaving(false);
    }
  };

  const hasChanges = content !== originalContent;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg w-[95vw] max-w-[90rem] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-700 p-4 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">
              {material.display_name} bearbeiten
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Typ: {material.material_type} | {material.file_count} {material.file_count === 1 ? 'Datei' : 'Dateien'}
            </p>
            {material.material_type === 'lecture_slide' && (
              <p className="text-xs text-yellow-500 mt-2 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Nach dem Speichern werden alte Chunks gelöscht und neue erstellt (dauert ca. 10-30 Sekunden)
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-3xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Body - Textarea */}
        <div className="flex-1 overflow-hidden p-4">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <svg className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <p className="text-slate-400">Lade Content...</p>
              </div>
            </div>
          ) : error ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <svg className="w-12 h-12 text-red-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-red-400 mb-2">{error}</p>
                <button
                  onClick={fetchContent}
                  className="text-blue-400 hover:text-blue-300 underline text-sm"
                >
                  Erneut versuchen
                </button>
              </div>
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full bg-slate-900 border border-slate-700 rounded p-3 text-slate-200 font-mono text-sm resize-none focus:outline-none focus:border-slate-600"
              placeholder="Markdown content..."
            />
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700 p-4 flex justify-between items-center">
          <div className="text-sm text-slate-400">
            {content.length.toLocaleString()} Zeichen
            {content.length > 100000 && (
              <span className="ml-2 text-yellow-500">
                ⚠️ Sehr groß ({Math.round(content.length / 1000)}k chars)
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
            >
              Abbrechen
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !hasChanges || isLoading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving && (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
              {isSaving ? 'Speichert...' : 'Speichern'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
