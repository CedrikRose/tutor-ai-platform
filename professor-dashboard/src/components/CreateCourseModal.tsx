import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { courseApi } from '../services/api';
import type { CreateCourseRequest } from '../types';

interface CreateCourseModalProps {
  onClose: () => void;
}

const SEMESTER_OPTIONS = [
  'WS 2024/25',
  'SS 2025',
  'WS 2025/26',
  'SS 2026',
  'WS 2026/27',
  'SS 2027',
];

export default function CreateCourseModal({ onClose }: CreateCourseModalProps) {
  const [formData, setFormData] = useState<CreateCourseRequest>({
    course_name: '',
    semester: SEMESTER_OPTIONS[0],
    student_access: true,
  });

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: courseApi.createCourse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses'] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Generate course_code from course_name (lowercase, no spaces)
    const courseCode = formData.course_name.toLowerCase().replace(/\s+/g, '_');
    createMutation.mutate({ ...formData, course_code: courseCode });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-w-md w-full">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-slate-100">Create New Course</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-300">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Course Name *
              </label>
              <input
                type="text"
                value={formData.course_name}
                onChange={(e) => setFormData({ ...formData, course_name: e.target.value })}
                required
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., Programmieren 2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Semester *
              </label>
              <select
                value={formData.semester}
                onChange={(e) => setFormData({ ...formData, semester: e.target.value })}
                required
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {SEMESTER_OPTIONS.map((sem) => (
                  <option key={sem} value={sem}>{sem}</option>
                ))}
              </select>
            </div>

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
                disabled={createMutation.isPending}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md font-medium disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Course'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
