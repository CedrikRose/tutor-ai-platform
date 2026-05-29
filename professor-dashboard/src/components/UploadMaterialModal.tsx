import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { courseApi } from '../services/api';

interface UploadMaterialModalProps {
  courseId: string;
  onClose: () => void;
}

const MATERIAL_TYPES = [
  { value: 'lecture_slide', label: 'Vorlesung' },
  { value: 'homework', label: 'Hausaufgabe' },
  { value: 'tutorium', label: 'Übung/Tutorium' },
  { value: 'other', label: 'Sonstiges' },
];

export default function UploadMaterialModal({ courseId, onClose }: UploadMaterialModalProps) {
  const [materialType, setMaterialType] = useState<string>('lecture_slide');
  const [customName, setCustomName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async () => {
      return courseApi.uploadMaterial(courseId, selectedFiles, materialType, customName || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials', courseId] });
      onClose();
    },
    onError: (error: any) => {
      console.error('Upload error:', error);
      alert(`Fehler beim Upload: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleFileSelect = (files: FileList | null) => {
    if (files) {
      setSelectedFiles(Array.from(files));
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const items = e.dataTransfer.items;
    const files: File[] = [];

    // Handle both files and folders
    if (items) {
      const promises: Promise<void>[] = [];
      for (let i = 0; i < items.length; i++) {
        const item = items[i].webkitGetAsEntry();
        if (item) {
          promises.push(traverseFileTree(item, files));
        }
      }
      await Promise.all(promises);
      setSelectedFiles(files);
    } else {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  // Recursively traverse folder structure
  const traverseFileTree = async (item: any, files: File[], path = ''): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (item.isFile) {
        item.file((file: File) => {
          // Preserve folder structure in file name
          const fullPath = path ? `${path}/${file.name}` : file.name;
          const fileWithPath = new File([file], fullPath, { type: file.type });
          files.push(fileWithPath);
          resolve();
        }, (error: any) => {
          console.error('Error reading file:', error);
          reject(error);
        });
      } else if (item.isDirectory) {
        const dirReader = item.createReader();
        dirReader.readEntries(async (entries: any[]) => {
          try {
            const entryPromises = entries.map(entry =>
              traverseFileTree(entry, files, path ? `${path}/${item.name}` : item.name)
            );
            await Promise.all(entryPromises);
            resolve();
          } catch (error) {
            console.error('Error reading directory:', error);
            reject(error);
          }
        }, (error: any) => {
          console.error('Error reading directory entries:', error);
          reject(error);
        });
      } else {
        // Neither file nor directory, skip
        resolve();
      }
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFiles.length > 0) {
      uploadMutation.mutate();
    }
  };

  const showCustomName = materialType === 'other';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-w-lg w-full">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-slate-100">Upload Material</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-300">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* File Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragging
                  ? 'border-blue-500 bg-blue-900/20'
                  : 'border-slate-600 hover:border-slate-500 bg-slate-700/50'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <svg className="w-12 h-12 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-slate-300 mb-2">
                {selectedFiles.length > 0
                  ? `${selectedFiles.length} file(s) selected`
                  : 'Drop files/folders here or click to select'}
              </p>
              <p className="text-sm text-slate-500">
                PDF, code files, folders, or ZIP archives
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                {...({ webkitdirectory: '' } as any)}
                onChange={(e) => handleFileSelect(e.target.files)}
                className="hidden"
              />
            </div>

            {selectedFiles.length > 0 && (
              <div className="bg-slate-700/50 rounded-lg p-3 max-h-32 overflow-y-auto">
                {selectedFiles.map((file, idx) => (
                  <div key={idx} className="text-sm text-slate-300 truncate">
                    {file.name}
                  </div>
                ))}
              </div>
            )}

            {/* Material Type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Material Type *
              </label>
              <select
                value={materialType}
                onChange={(e) => setMaterialType(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {MATERIAL_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Custom Name (only for "other") */}
            {showCustomName && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Custom Display Name
                </label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter custom name..."
                />
                <p className="text-xs text-slate-500 mt-1">
                  Leave empty to use filename
                </p>
              </div>
            )}

            {/* Info Box */}
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
              <p className="text-sm text-blue-300 mb-2">
                <strong>Hinweis:</strong> Du kannst mehrere Dateien auf einmal hochladen (z.B. PDF + Projektordner).
                Sie werden als EIN Material behandelt.
              </p>
              <p className="text-sm text-blue-300 mb-2">
                <strong>Ordner hochladen:</strong> Einfach per Drag & Drop reinziehen. ZIP-Dateien werden automatisch entpackt.
              </p>
              <p className="text-sm text-blue-300">
                Uploads werden 1 Stunde geprüft, bevor sie verarbeitet werden.
                Löschen in dieser Zeit = keine LLM-Kosten.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 px-4 rounded-md font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploadMutation.isPending || selectedFiles.length === 0}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md font-medium disabled:opacity-50"
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
