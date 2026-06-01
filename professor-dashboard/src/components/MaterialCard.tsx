import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { courseApi } from '../services/api';
import DeleteMaterialModal from './DeleteMaterialModal';
import type { CourseMaterial } from '../types';

interface MaterialCardProps {
  material: CourseMaterial;
}

export default function MaterialCard({ material }: MaterialCardProps) {
  const queryClient = useQueryClient();
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const PROCESSING_MARKER = new Date('1970-01-01T00:00:00Z');
  const isProcessed = !!material.processed_at && new Date(material.processed_at) > PROCESSING_MARKER;
  const isProcessingBackground = !!material.processed_at && new Date(material.processed_at).getTime() === PROCESSING_MARKER.getTime();

  // Auto-refresh materials list while processing in background
  useEffect(() => {
    if (isProcessingBackground) {
      const interval = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ['materials', material.course_id] });
      }, 2000);
      
      return () => clearInterval(interval);
    }
  }, [isProcessingBackground, material.course_id, queryClient]);

  const deleteMutation = useMutation({
    mutationFn: () => courseApi.deleteMaterial(material.material_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials', material.course_id] });
      setShowDeleteModal(false);
    },
  });

  const processMutation = useMutation({
    mutationFn: () => courseApi.processMaterial(material.material_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials', material.course_id] });
    },
    onError: (error: any) => {
      console.error('Failed to start processing:', error);
      alert(`Fehler beim Starten der Verarbeitung: ${error.response?.data?.detail || error.message}`);
    }
  });

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleDeleteConfirm = () => {
    deleteMutation.mutate();
  };

  const handleProcess = () => {
    processMutation.mutate();
  };

  const isProcessing = processMutation.isPending || isProcessingBackground;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1">
          <h3 className="font-semibold text-slate-100">{material.display_name}</h3>
          <p className="text-xs text-slate-500 mt-1">
            {material.file_count} {material.file_count === 1 ? 'Datei' : 'Dateien'}
          </p>
        </div>

        {/* Status badge */}
        {isProcessed && (
          <span className="px-2 py-1 text-xs bg-green-900/30 text-green-400 rounded-full flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Verarbeitet
          </span>
        )}
      </div>

      {/* File list with collapse */}
      <div className="mb-3 space-y-1">
        {(showAllFiles ? material.files : material.files.slice(0, 3)).map((file) => (
          <div key={file.file_id} className="text-sm text-slate-400 truncate flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <span className="truncate">{file.filename}</span>
          </div>
        ))}
        {material.files.length > 3 && (
          <button
            onClick={() => setShowAllFiles(!showAllFiles)}
            className="text-xs text-blue-400 hover:text-blue-300 underline flex items-center gap-1 mt-1"
          >
            {showAllFiles ? (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
                Weniger anzeigen
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
                {material.files.length - 3} weitere Dateien anzeigen
              </>
            )}
          </button>
        )}
      </div>

      {/* Processing status banner */}
      {isProcessing && (
        <div className="mb-3 text-xs text-yellow-500 bg-yellow-900/20 rounded px-3 py-2 flex items-center gap-2">
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Material wird verarbeitet...</span>
        </div>
      )}

      {/* Not processed yet warning */}
      {!isProcessed && !isProcessing && (
        <div className="mb-3 text-xs text-orange-500 bg-orange-900/20 rounded px-3 py-2 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Noch nicht verarbeitet. Klicke auf "Verarbeiten" um es für Studenten verfügbar zu machen.
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        {!isProcessed && (
          <button
            onClick={handleProcess}
            disabled={isProcessing}
            className="flex-1 bg-blue-900/30 hover:bg-blue-900/50 text-blue-400 py-2 px-3 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isProcessing ? 'Wird verarbeitet...' : 'Verarbeiten'}
          </button>
        )}
        <button
          onClick={handleDeleteClick}
          disabled={deleteMutation.isPending}
          className={`${!isProcessed ? 'flex-1' : 'w-full'} bg-red-900/30 hover:bg-red-900/50 text-red-400 py-2 px-3 rounded-md text-sm disabled:opacity-50`}
        >
          {deleteMutation.isPending ? 'Lösche...' : 'Löschen'}
        </button>
      </div>

      {showDeleteModal && (
        <DeleteMaterialModal
          materialName={material.display_name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
