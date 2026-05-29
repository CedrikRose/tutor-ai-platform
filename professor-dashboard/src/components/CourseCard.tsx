import { useNavigate } from 'react-router-dom';
import type { Course } from '../types';

interface CourseCardProps {
  course: Course;
  onDelete: (courseId: string) => void;
}

export default function CourseCard({ course, onDelete }: CourseCardProps) {
  const navigate = useNavigate();

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg shadow hover:shadow-lg transition-shadow duration-200 overflow-hidden">
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">{course.course_name}</h3>
          </div>
          <span className={`px-2 py-1 text-xs rounded-full ${course.is_active ? 'bg-green-900/30 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
            {course.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400 mb-4">
          {course.semester && <span>{course.semester}</span>}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => navigate(`/course/${course.course_id}`)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium"
          >
            Open Course
          </button>
          <button
            onClick={() => onDelete(course.course_id)}
            className="bg-red-900/30 hover:bg-red-900/50 text-red-400 py-2 px-4 rounded-md text-sm font-medium"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
