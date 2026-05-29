import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import './ContextSelectors.css';

interface Module {
  id: string;
  name: string;
}

interface Homework {
  id: string;
  name: string;
  sequence: number;
}

interface Lecture {
  number: number;
  name: string;
}

interface ContextSelectorsProps {
  sessionId: string;
}

function ContextSelectors({ sessionId }: ContextSelectorsProps) {
  const [modules, setModules] = useState<Module[]>([]);
  const [homework, setHomework] = useState<Homework[]>([]);
  const [lectures, setLectures] = useState<Lecture[]>([]);

  const [selectedModule, setSelectedModule] = useState<string>('');
  const [selectedHomework, setSelectedHomework] = useState<string>('');
  const [selectedLecture, setSelectedLecture] = useState<number | null>(null);

  // Load modules
  useEffect(() => {
    fetch('${API_URL}/api/modules')
      .then((res) => res.json())
      .then((data) => setModules(data))
      .catch((err) => console.error('Error loading modules:', err));
  }, []);

  // Load homework and lectures when module changes
  useEffect(() => {
    if (selectedModule) {
      // Load homework
      fetch(`${API_URL}/api/modules/${selectedModule}/homework`)
        .then((res) => res.json())
        .then((data) => setHomework(data))
        .catch((err) => console.error('Error loading homework:', err));

      // Load lectures
      fetch(`${API_URL}/api/modules/${selectedModule}/lectures`)
        .then((res) => res.json())
        .then((data) => setLectures(data))
        .catch((err) => console.error('Error loading lectures:', err));
    } else {
      setHomework([]);
      setLectures([]);
    }
  }, [selectedModule]);

  // Update session context
  const updateContext = async (module: string | null, hw: string | null, lecture: number | null) => {
    try {
      await fetch(`${API_URL}/api/sessions/${sessionId}/context`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          course_module: module || null,
          homework_id: hw || null,
          lecture_number: lecture,
        }),
      });
    } catch (error) {
      console.error('Error updating context:', error);
    }
  };

  const handleModuleChange = (value: string) => {
    setSelectedModule(value);
    setSelectedHomework('');
    setSelectedLecture(null);
    updateContext(value || null, null, null);
  };

  const handleHomeworkChange = (value: string) => {
    setSelectedHomework(value);
    updateContext(selectedModule, value || null, selectedLecture);
  };

  const handleLectureChange = (value: string) => {
    const lectureNum = value ? parseInt(value) : null;
    setSelectedLecture(lectureNum);
    updateContext(selectedModule, selectedHomework || null, lectureNum);
  };

  return (
    <div className="context-selectors">
      <div className="selector">
        <label>Modul:</label>
        <select value={selectedModule} onChange={(e) => handleModuleChange(e.target.value)}>
          <option value="">Alle Module</option>
          {modules.map((mod) => (
            <option key={mod.id} value={mod.id}>
              {mod.name}
            </option>
          ))}
        </select>
      </div>

      {selectedModule && (
        <>
          <div className="selector">
            <label>Hausaufgabe:</label>
            <select value={selectedHomework} onChange={(e) => handleHomeworkChange(e.target.value)}>
              <option value="">Keine spezifische</option>
              {homework.map((hw) => (
                <option key={hw.id} value={hw.id}>
                  {hw.name}
                </option>
              ))}
            </select>
          </div>

          <div className="selector">
            <label>Bis Vorlesung:</label>
            <select
              value={selectedLecture || ''}
              onChange={(e) => handleLectureChange(e.target.value)}
            >
              <option value="">Alle Vorlesungen</option>
              {lectures.map((lec) => (
                <option key={lec.number} value={lec.number}>
                  Vorlesung {lec.number}
                </option>
              ))}
            </select>
          </div>
        </>
      )}
    </div>
  );
}

export default ContextSelectors;
