import { useState, useEffect, useCallback, useRef } from 'react';
import { courseApi } from '../services/api';
import type { CourseMaterial, RawMaterialFile } from '../types';

interface EditRawMaterialsModalProps {
  material: CourseMaterial;
  onClose: () => void;
  onSaved?: () => void;
}

export default function EditRawMaterialsModal({
  material,
  onClose,
  onSaved
}: EditRawMaterialsModalProps) {
  // State
  const [files, setFiles] = useState<RawMaterialFile[]>([]);
  const [fileImportances, setFileImportances] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileToDelete, setFileToDelete] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load files on mount
  useEffect(() => {
    fetchFiles();
  }, [material.material_id]);

  const fetchFiles = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await courseApi.getRawFiles(material.material_id);
      setFiles(response.files || []);

      // Initialize importance state
      const importances: Record<string, boolean> = {};
      response.files.forEach((file: RawMaterialFile) => {
        importances[file.file_id] = file.is_important;
      });
      setFileImportances(importances);
    } catch (err: any) {
      console.error('Error fetching raw files:', err);
      setError(err.response?.data?.detail || 'Fehler beim Laden der Dateien');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleImportance = (fileId: string) => {
    setFileImportances(prev => ({ ...prev, [fileId]: !prev[fileId] }));
  };

  const handleDeleteClick = (fileId: string) => {
    setFileToDelete(fileId);
  };

  const handleConfirmDelete = async () => {
    if (!fileToDelete) return;

    try {
      await courseApi.deleteRawFile(material.material_id, fileToDelete);
      setFileToDelete(null);
      await fetchFiles(); // Reload
    } catch (err: any) {
      console.error('Error deleting file:', err);
      alert(`Fehler beim Löschen: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;

    await uploadFiles(Array.from(selectedFiles));
  };

  const uploadFiles = async (filesToUpload: File[]) => {
    setIsUploading(true);
    setError(null);

    try {
      await courseApi.uploadRawFiles(material.material_id, filesToUpload);
      await fetchFiles(); // Reload
    } catch (err: any) {
      console.error('Error uploading files:', err);
      setError(err.response?.data?.detail || 'Fehler beim Hochladen');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      await uploadFiles(droppedFiles);
    }
  }, [material.material_id]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);

    try {
      // Check if at least one file is important
      const hasImportantFiles = Object.values(fileImportances).some(v => v);

      if (!hasImportantFiles) {
        const confirm = window.confirm(
          'Keine Dateien sind als wichtig markiert. ' +
          'Das Material wird als "nicht verfügbar" markiert. Fortfahren?'
        );
        if (!confirm) {
          setIsSaving(false);
          return;
        }
      }

      await courseApi.updateFileImportance(material.material_id, fileImportances);
      onSaved?.();
      onClose();
    } catch (err: any) {
      console.error('Error saving:', err);
      setError(err.response?.data?.detail || 'Fehler beim Speichern');
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = () => {
    return files.some(file => fileImportances[file.file_id] !== file.is_important);
  };

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg w-[95vw] max-w-5xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-700 p-4">
          <div className="flex justify-between items-start mb-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                {material.display_name} - Rohmaterialien bearbeiten
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                {files.length} {files.length === 1 ? 'Datei' : 'Dateien'} |{' '}
                {Object.values(fileImportances).filter(v => v).length} als wichtig markiert
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 text-3xl leading-none"
            >
              ×
            </button>
          </div>

          {error && (
            <div className="text-red-400 text-sm bg-red-900/20 rounded px-3 py-2 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <svg className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <p className="text-slate-400">Lade Dateien...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Drag & Drop Upload Zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={`border-2 border-dashed rounded-lg p-6 mb-4 transition-colors ${
                  isDragging
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-600 bg-slate-900/50 hover:border-slate-500'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                <div className="text-center">
                  {isUploading ? (
                    <div className="flex items-center justify-center gap-2 text-blue-400">
                      <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Lade hoch...</span>
                    </div>
                  ) : (
                    <>
                      <svg className="w-12 h-12 text-slate-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-slate-300 mb-1">Dateien hierher ziehen</p>
                      <p className="text-slate-500 text-sm mb-3">oder</p>
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2 bg-blue-900/30 hover:bg-blue-900/50 text-blue-400 rounded-md text-sm"
                      >
                        Dateien auswählen
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* File List */}
              {files.length === 0 ? (
                <div className="text-center text-slate-400 py-8">
                  Keine Dateien vorhanden
                </div>
              ) : (
                <div className="space-y-2">
                  {files.map((file) => {
                    const isImportant = fileImportances[file.file_id];

                    return (
                      <div
                        key={file.file_id}
                        className={`border rounded-lg p-3 transition-colors ${
                          isImportant
                            ? 'border-green-700 bg-green-900/10'
                            : 'border-slate-700 bg-slate-900/50'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Checkbox */}
                          <label className="flex items-center cursor-pointer mt-0.5">
                            <input
                              type="checkbox"
                              checked={isImportant}
                              onChange={() => handleToggleImportance(file.file_id)}
                              className="w-5 h-5 rounded border-slate-600 text-green-600 focus:ring-green-500 focus:ring-offset-slate-800"
                            />
                          </label>

                          {/* File Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <svg className="w-4 h-4 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                              <span className={`font-medium truncate ${isImportant ? 'text-slate-100' : 'text-slate-400'}`}>
                                {file.filename}
                              </span>
                              <span className="text-xs text-slate-500 flex-shrink-0">
                                {formatFileSize(file.file_size)}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500">
                              {file.importance_reason}
                            </p>
                          </div>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDeleteClick(file.file_id)}
                            className="flex-shrink-0 text-red-400 hover:text-red-300 px-2 py-1 text-xs rounded hover:bg-red-900/20"
                          >
                            🗑️ Löschen
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700 p-4 flex justify-between items-center">
          <div className="text-sm text-slate-400">
            {hasChanges() && (
              <span className="text-yellow-500">
                ● Ungespeicherte Änderungen
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-md"
            >
              Abbrechen
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !hasChanges()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving && (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
              {isSaving ? 'Speichert...' : 'Speichern & Verarbeiten'}
            </button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {fileToDelete && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-700 p-6 rounded-lg max-w-md">
            <h3 className="text-lg font-semibold text-slate-100 mb-2">
              Datei wirklich löschen?
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Diese Aktion kann nicht rückgängig gemacht werden. Die Datei wird
              physisch aus dem Speicher gelöscht.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setFileToDelete(null)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-md"
              >
                Abbrechen
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md"
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
