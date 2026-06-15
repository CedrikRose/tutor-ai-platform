import { useState, useEffect } from 'react';
import { courseApi } from '../services/api';
import EditRawMaterialsModal from './EditRawMaterialsModal';
import type { CourseMaterial } from '../types';

interface MaterialChunk {
  chunk_id: string;
  chunk_index: number;
  content: string;
  pages?: number[];
  source_type?: string;
  metadata?: {
    pages?: number[];
    source?: string;
    synthesized_at?: string;
    batch_index?: number;
  };
}

interface EditChunksModalProps {
  material: CourseMaterial;
  onClose: () => void;
  onSaved?: () => void;
}

export default function EditChunksModal({ material, onClose }: EditChunksModalProps) {
  const [chunks, setChunks] = useState<MaterialChunk[]>([]);
  const [originalChunks, setOriginalChunks] = useState<MaterialChunk[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingChunk, setEditingChunk] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showRawMaterialsModal, setShowRawMaterialsModal] = useState(false);

  useEffect(() => {
    fetchChunks();
  }, [material.material_id]);

  const fetchChunks = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await courseApi.getMaterialChunks(material.material_id);
      setChunks(response.chunks || []);
      setOriginalChunks(response.chunks || []);
    } catch (err: any) {
      console.error('Error fetching chunks:', err);
      setError(err.response?.data?.detail || 'Fehler beim Laden der Chunks');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveChunk = async (chunkId: string, newContent: string) => {
    setIsSaving(true);
    setError(null);

    try {
      await courseApi.updateChunk(material.material_id, chunkId, newContent);

      // Update local state
      setChunks(chunks.map(c =>
        c.chunk_id === chunkId ? { ...c, content: newContent } : c
      ));
      setOriginalChunks(originalChunks.map(c =>
        c.chunk_id === chunkId ? { ...c, content: newContent } : c
      ));

      setEditingChunk(null);
    } catch (err: any) {
      console.error('Error saving chunk:', err);
      setError(err.response?.data?.detail || 'Fehler beim Speichern');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChunkChange = (chunkId: string, newContent: string) => {
    setChunks(chunks.map(c =>
      c.chunk_id === chunkId ? { ...c, content: newContent } : c
    ));
  };

  const isChunkModified = (chunkId: string) => {
    const original = originalChunks.find(c => c.chunk_id === chunkId);
    const current = chunks.find(c => c.chunk_id === chunkId);
    return original && current && original.content !== current.content;
  };

  const filteredChunks = chunks.filter(chunk =>
    searchTerm === '' ||
    chunk.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
    chunk.chunk_index.toString().includes(searchTerm)
  );

  const getPageDisplay = (chunk: MaterialChunk) => {
    const pages = chunk.metadata?.pages || chunk.pages || [];
    if (pages.length === 0) return '';
    if (pages.length === 1) return `Seite ${pages[0]}`;
    return `Seiten ${pages[0]}-${pages[pages.length - 1]}`;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg w-[95vw] max-w-[90rem] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-700 p-4">
          <div className="flex justify-between items-start mb-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                {material.display_name} - Chunks bearbeiten
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                {chunks.length} Chunks | Synthesized mit Reducto + Kimi K2.5
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowRawMaterialsModal(true)}
                className="text-slate-400 hover:text-slate-200 text-sm px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded"
              >
                📁 Rohmaterialien
              </button>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-slate-200 text-3xl leading-none"
              >
                ×
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Chunks durchsuchen..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-4 py-2 text-slate-200 text-sm focus:outline-none focus:border-slate-600 pl-10"
            />
            <svg className="w-5 h-5 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Body - Chunks List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <svg className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <p className="text-slate-400">Lade Chunks...</p>
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
                  onClick={fetchChunks}
                  className="text-blue-400 hover:text-blue-300 underline text-sm"
                >
                  Erneut versuchen
                </button>
              </div>
            </div>
          ) : filteredChunks.length === 0 ? (
            <div className="text-center text-slate-400 py-8">
              {searchTerm ? `Keine Chunks gefunden für "${searchTerm}"` : 'Keine Chunks vorhanden'}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredChunks.map((chunk) => {
                const isEditing = editingChunk === chunk.chunk_id;
                const isModified = isChunkModified(chunk.chunk_id);
                const pageDisplay = getPageDisplay(chunk);

                return (
                  <div
                    key={chunk.chunk_id}
                    className={`border-2 rounded-lg p-4 transition-colors ${
                      isModified
                        ? 'border-yellow-500/50 bg-yellow-500/5'
                        : 'border-slate-700 bg-slate-900/50'
                    }`}
                  >
                    {/* Chunk Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-slate-400 font-mono text-sm bg-slate-800 px-2 py-1 rounded">
                          #{chunk.chunk_index}
                        </span>
                        {pageDisplay && (
                          <span className="text-slate-400 text-xs bg-slate-800 px-2 py-1 rounded">
                            📄 {pageDisplay}
                          </span>
                        )}
                        {chunk.metadata?.source && (
                          <span className="text-slate-400 text-xs bg-slate-800 px-2 py-1 rounded">
                            🔄 {chunk.metadata.source}
                          </span>
                        )}
                        {isModified && (
                          <span className="text-yellow-500 text-xs bg-yellow-500/10 px-2 py-1 rounded">
                            ● Geändert
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        {isEditing ? (
                          <>
                            <button
                              onClick={() => {
                                // Reset to original
                                const original = originalChunks.find(c => c.chunk_id === chunk.chunk_id);
                                if (original) {
                                  handleChunkChange(chunk.chunk_id, original.content);
                                }
                                setEditingChunk(null);
                              }}
                              className="text-xs px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                            >
                              Abbrechen
                            </button>
                            <button
                              onClick={() => handleSaveChunk(chunk.chunk_id, chunk.content)}
                              disabled={isSaving || !isModified}
                              className="text-xs px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                            >
                              {isSaving && (
                                <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                              )}
                              Speichern
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setEditingChunk(chunk.chunk_id)}
                            className="text-xs px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
                          >
                            ✏️ Bearbeiten
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Chunk Content */}
                    {isEditing ? (
                      <textarea
                        value={chunk.content}
                        onChange={(e) => handleChunkChange(chunk.chunk_id, e.target.value)}
                        className="w-full h-48 bg-slate-800 border border-slate-700 rounded p-3 text-slate-200 font-mono text-sm resize-y focus:outline-none focus:border-slate-600"
                      />
                    ) : (
                      <div className="text-slate-300 text-sm whitespace-pre-wrap font-mono bg-slate-800 p-3 rounded max-h-48 overflow-y-auto">
                        {chunk.content}
                      </div>
                    )}

                    {/* Chunk Footer */}
                    <div className="mt-2 text-xs text-slate-500">
                      {chunk.content.length.toLocaleString()} Zeichen
                      {chunk.metadata?.synthesized_at && (
                        <span className="ml-3">
                          Erstellt: {new Date(chunk.metadata.synthesized_at).toLocaleString('de-DE')}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-700 p-4 flex justify-between items-center">
          <div className="text-sm text-slate-400">
            {filteredChunks.length} von {chunks.length} Chunks angezeigt
            {chunks.filter(c => isChunkModified(c.chunk_id)).length > 0 && (
              <span className="ml-3 text-yellow-500">
                ● {chunks.filter(c => isChunkModified(c.chunk_id)).length} ungespeicherte Änderungen
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded"
          >
            Schließen
          </button>
        </div>
      </div>

      {/* Raw Materials Modal */}
      {showRawMaterialsModal && (
        <EditRawMaterialsModal
          material={material}
          onClose={() => setShowRawMaterialsModal(false)}
          onSaved={() => {
            setShowRawMaterialsModal(false);
            fetchChunks(); // Reload chunks after raw materials change
          }}
        />
      )}
    </div>
  );
}
