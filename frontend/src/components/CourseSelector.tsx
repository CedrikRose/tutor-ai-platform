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
  material_types: any[];  // Not used anymore
}

interface CourseSelectorProps {
  sessionId: string;
}

function CourseSelector({ sessionId }: CourseSelectorProps) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [filters, setFilters] = useState<CourseFilters | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('');
  const [selectedLecture, setSelectedLecture] = useState<number | null>(null);
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // Load courses
  useEffect(() => {
    fetch('${API_URL}/api/courses')
      .then((res) => res.json())
      .then((data) => {
        setCourses(data);
        console.log('Loaded courses:', data);
      })
      .catch((err) => console.error('Error loading courses:', err));
  }, []);

  // Load filters and materials when course changes
  useEffect(() => {
    if (selectedCourse) {
      setLoading(true);

      // Load filters (lectures)
      fetch(`${API_URL}/api/courses/${selectedCourse}/filters`)
        .then((res) => res.json())
        .then((data: CourseFilters) => {
          setFilters(data);
          console.log('Loaded filters:', data);

          // Auto-select last lecture
          if (data.lectures.length > 0) {
            const lastLecture = data.lectures[data.lectures.length - 1];
            setSelectedLecture(lastLecture.sequence_number);
          }
        })
        .catch((err) => console.error('Error loading filters:', err));

      // Load all materials (for material dropdown)
      fetch(`${API_URL}/api/courses/${selectedCourse}/materials-list`)
        .then((res) => res.json())
        .then((data: Material[]) => {
          setMaterials(data);
          console.log('Loaded materials:', data);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Error loading materials:', err);
          setLoading(false);
        });
    } else {
      setFilters(null);
      setMaterials([]);
      setSelectedLecture(null);
      setSelectedMaterial('');
    }
  }, [selectedCourse]);

  // Update session context
  const updateContext = async (updates: {
    course_id?: string | null;
    max_lecture_sequence?: number | null;
    selected_material_id?: string | null;
  }) => {
    try {
      await fetch(`${API_URL}/api/sessions/${sessionId}/context`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(updates),
      });
      console.log('Updated session context:', updates);
    } catch (error) {
      console.error('Error updating context:', error);
    }
  };

  const handleCourseChange = (value: string) => {
    setSelectedCourse(value);
    setSelectedLecture(null);
    setSelectedMaterial('');
    updateContext({ course_id: value || null, max_lecture_sequence: null, selected_material_id: null });
  };

  const handleLectureChange = (value: string) => {
    const lectureNum = value ? parseInt(value) : null;
    setSelectedLecture(lectureNum);
    updateContext({ max_lecture_sequence: lectureNum });
  };

  const handleMaterialChange = (value: string) => {
    setSelectedMaterial(value);
    updateContext({ selected_material_id: value || null });
  };

  return (
    <div className="context-selectors">
      {/* Course Selector */}
      <div className="selector">
        <label>📚 Kurs:</label>
        <select value={selectedCourse} onChange={(e) => handleCourseChange(e.target.value)}>
          <option value="">Alle Kurse durchsuchen</option>
          {courses.map((course) => (
            <option key={course.course_id} value={course.course_id}>
              {course.course_name} ({course.semester})
            </option>
          ))}
        </select>
      </div>

      {/* Lecture Selector */}
      {selectedCourse && filters && filters.lectures.length > 0 && (
        <div className="selector">
          <label>🎓 Vorlesungen bis:</label>
          <select value={selectedLecture || ''} onChange={(e) => handleLectureChange(e.target.value)}>
            <option value="">Alle Vorlesungen</option>
            {filters.lectures.map((lec) => (
              <option key={lec.sequence_number} value={lec.sequence_number}>
                {lec.display_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Material Selector (specific material - loads ALL chunks) */}
      {selectedCourse && materials.length > 0 && (
        <div className="selector">
          <label>📋 Material:</label>
          <select value={selectedMaterial} onChange={(e) => handleMaterialChange(e.target.value)}>
            <option value="">Kein spezifisches Material</option>
            {materials
              .filter((mat) => mat.material_type !== 'lecture_slide')
              .map((mat) => {
                const icon = mat.material_type === 'homework' ? '✏️' : mat.material_type === 'tutorium' ? '📝' : '📄';
                return (
                  <option key={mat.material_id} value={mat.material_id}>
                    {icon} {mat.display_name}
                  </option>
                );
              })}
          </select>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div style={{ marginTop: '10px', fontSize: '12px', color: '#999' }}>
          Lade Materialien...
        </div>
      )}
    </div>
  );
}

export default CourseSelector;
