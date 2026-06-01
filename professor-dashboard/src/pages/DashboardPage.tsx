import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { courseApi } from '../services/api';
import CourseCard from '../components/CourseCard';
import CreateCourseModal from '../components/CreateCourseModal';
import DeleteCourseModal from '../components/DeleteCourseModal';
import SchedulerStatus from '../components/SchedulerStatus';
import type { Course } from '../types';

export default function DashboardPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState<Course | null>(null);
  const queryClient = useQueryClient();

  const { data: courses, isLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: courseApi.getCourses,
  });

  const deleteMutation = useMutation({
    mutationFn: courseApi.deleteCourse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses'] });
      setCourseToDelete(null);
    },
  });

  const handleDeleteClick = (courseId: string) => {
    const course = courses?.find((c: Course) => c.course_id === courseId);
    if (course) {
      setCourseToDelete(course);
    }
  };

  const handleDeleteConfirm = async () => {
    if (courseToDelete) {
      await deleteMutation.mutateAsync(courseToDelete.course_id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading courses...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My Courses</h1>
          <p className="text-slate-400 mt-1">Manage your courses and materials</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Course
        </button>
      </div>

      {/* Scheduler Status */}
      <div className="mb-6">
        <SchedulerStatus />
      </div>

      {courses && courses.length === 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-lg shadow p-12 text-center">
          <svg className="w-16 h-16 text-slate-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <h3 className="text-lg font-medium text-slate-200 mb-2">No courses yet</h3>
          <p className="text-slate-400 mb-4">Get started by creating your first course</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md"
          >
            Create Your First Course
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses?.map((course: Course) => (
            <CourseCard
              key={course.course_id}
              course={course}
              onDelete={handleDeleteClick}
            />
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateCourseModal onClose={() => setShowCreateModal(false)} />
      )}

      {courseToDelete && (
        <DeleteCourseModal
          courseName={courseToDelete.course_name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setCourseToDelete(null)}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
