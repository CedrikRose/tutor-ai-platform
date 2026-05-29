import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import './ContextSelectors.css';

interface Course {
  course_id: string;
  course_code: string;
  course_name: string;
  semester: string;
  material_count: number;
}

interface Lecture {
  sequence_number: number;
  display_name: string;
  chunk_count: number;
}

interface Material {
  material_id: string;
  display_name: string;
  material_type: string;
  sequence_number: number | null;
  chunk_count: number;
}

interface CourseFilters {
  lectures: Lecture[];
  material_types: any[];
}

interface CourseSelectorV2Props {
  conversationId: string;
  onContextChange: (context: any) => void;
  initialContext?: any; // Context from last exchange
}

function CourseSelectorV2({ conversationId, onContextChange, initialContext }: CourseSelectorV2Props) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [filters, setFilters] = useState<CourseFilters | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [selectedLecture, setSelectedLecture] = useState<number | null>(null);
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Load courses
  useEffect(() => {
    fetch(`${API_URL}/api/courses`)
      .then((res) => res.json())
      .then((data) => {
        setCourses(data);
      })
      .catch((err) => console.error('Error loading courses:', err));
  }, []);

  // FIX 2: Watch initialContext changes directly and update state
  // This fixes the "selectors reset on reload" bug
  useEffect(() => {
    if (initialContext) {
      // Load context from existing conversation
      console.log('🎯 Updating from context:', initialContext);

      const newCourse = initialContext.course_id || '';
      const newLecture = initialContext.max_lecture_sequence || null;
      const newMaterial = initialContext.selected_material_id || '';

      // Only update if values actually changed (prevent infinite loops)
      if (newCourse !== selectedCourse) {
        setSelectedCourse(newCourse);
      }
      if (newLecture !== selectedLecture) {
        setSelectedLecture(newLecture);
      }
      if (newMaterial !== selectedMaterial) {
        setSelectedMaterial(newMaterial);
      }

      console.log('✅ Updated CourseSelector from context');
    } else if (conversationId === 'new') {
      // New conversation - reset to defaults
      console.log('🆕 New conversation - resetting to defaults');
      setSelectedCourse('');
      setSelectedLecture(null);
      setSelectedMaterial('');
    }
  }, [initialContext, conversationId]);

  // Load filters when course changes
  useEffect(() => {
    if (selectedCourse) {
      setLoading(true);
      fetch(`${API_URL}/api/courses/${selectedCourse}/filters`)
        .then((res) => res.json())
        .then((data) => {
          setFilters(data);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Error loading filters:', err);
          setLoading(false);
        });

      // Load materials
      fetch(`${API_URL}/api/courses/${selectedCourse}/materials-list`)
        .then((res) => res.json())
        .then((data) => {
          setMaterials(data);
        })
        .catch((err) => console.error('Error loading materials:', err));
    } else {
      setFilters(null);
      setMaterials([]);
    }
  }, [selectedCourse]);

  // Update context whenever selection changes
  useEffect(() => {
    const context = {
      course_id: selectedCourse || null,
      max_lecture_sequence: selectedLecture,
      material_types: null, // For simplicity, not filtering by type
      selected_material_id: selectedMaterial || null,
    };
    onContextChange(context);
  }, [selectedCourse, selectedLecture, selectedMaterial]);

  const handleCourseChange = (courseId: string) => {
    setSelectedCourse(courseId);
    setSelectedLecture(null);
    setSelectedMaterial('');
  };

  return (
    <div className={`context-selectors ${isCollapsed ? 'collapsed' : ''}`}>
      <button
        className="collapse-toggle"
        onClick={() => setIsCollapsed(!isCollapsed)}
        title={isCollapsed ? 'Kontext einblenden' : 'Kontext ausblenden'}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path
            d={isCollapsed ? 'M19 9l-7 7-7-7' : 'M5 15l7-7 7 7'}
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span>{isCollapsed ? 'Kontext einblenden' : 'Kurs & Material'}</span>
      </button>

      {!isCollapsed && (
        <div className="selectors-content">
          <div className="selector">
        <label>Kurs:</label>
        <select
          value={selectedCourse}
          onChange={(e) => handleCourseChange(e.target.value)}
        >
          <option value="">Alle Kurse</option>
          {courses.map((course) => (
            <option key={course.course_id} value={course.course_id}>
              {course.course_code} - {course.course_name}
            </option>
          ))}
        </select>
      </div>

      {selectedCourse && filters && (
        <>
          <div className="selector">
            <label>Bis Vorlesung:</label>
            <select
              value={selectedLecture || ''}
              onChange={(e) => setSelectedLecture(e.target.value ? Number(e.target.value) : null)}
              disabled={loading}
            >
              <option value="">Alle Vorlesungen</option>
              {filters.lectures.map((lecture) => (
                <option key={lecture.sequence_number} value={lecture.sequence_number}>
                  {lecture.display_name}
                </option>
              ))}
            </select>
          </div>

          <div className="selector">
            <label>Spezifisches Material:</label>
            <select
              value={selectedMaterial}
              onChange={(e) => setSelectedMaterial(e.target.value)}
              disabled={loading}
            >
              <option value="">Kein spezifisches Material</option>
              {materials
                .filter((material) => material.material_type !== 'lecture_slide')
                .map((material) => (
                  <option key={material.material_id} value={material.material_id}>
                    {material.display_name} ({material.material_type})
                  </option>
                ))}
            </select>
          </div>
        </>
      )}
        </div>
      )}
    </div>
  );
}

export default CourseSelectorV2;
