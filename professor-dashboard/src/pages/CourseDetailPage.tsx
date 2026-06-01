import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { courseApi } from '../services/api';
import { getReports, getReportDetail } from '../services/analysisApi';
import UploadMaterialModal from '../components/UploadMaterialModal';
import MaterialCard from '../components/MaterialCard';
import FindingsList from '../components/FindingsList';
import ManualAnalysisButton from '../components/ManualAnalysisButton';
import ReportControlBar from '../components/ReportControlBar';
import ReportSettingsPanel from '../components/ReportSettingsPanel';
import LatestReportCard from '../components/LatestReportCard';
import PreviousReportsList from '../components/PreviousReportsList';

export default function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'materials' | 'findings' | 'reports'>('materials');

  const { data: course, isLoading } = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => courseApi.getCourse(courseId!),
    enabled: !!courseId,
  });

  const { data: materials = [] } = useQuery({
    queryKey: ['materials', courseId],
    queryFn: () => courseApi.getMaterials(courseId!),
    enabled: !!courseId,
  });

  const { data: reports = [], isLoading: isLoadingReports, refetch: refetchReports } = useQuery({
    queryKey: ['reports', courseId],
    queryFn: () => getReports(courseId!, 10, 0),
    enabled: !!courseId && activeTab === 'reports',
  });

  const latestReportId = reports[0]?.report_id || null;

  const { data: latestReport = null, isLoading: isLoadingLatestReport } = useQuery({
    queryKey: ['latest-report', latestReportId],
    queryFn: () => getReportDetail(latestReportId!),
    enabled: !!latestReportId && activeTab === 'reports',
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading course...</div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-400">Course not found</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 text-blue-400 hover:text-blue-300"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const groupedMaterials = {
    lecture_slide: materials.filter((m: any) => m.material_type === 'lecture_slide'),
    homework: materials.filter((m: any) => m.material_type === 'homework'),
    tutorium: materials.filter((m: any) => m.material_type === 'tutorium'),
    other: materials.filter((m: any) => m.material_type === 'other'),
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="text-slate-400 hover:text-slate-300 mb-4 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Dashboard
        </button>

        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{course.course_name}</h1>
            <p className="text-slate-400 mt-1">{course.semester}</p>
          </div>
          <button
            onClick={() => setShowUploadModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload Material
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-slate-700">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('materials')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'materials'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-300'
            }`}
          >
            Materialien
          </button>
          <button
            onClick={() => setActiveTab('findings')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'findings'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-300'
            }`}
          >
            Erkenntnisse
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'reports'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-300'
            }`}
          >
            Berichte
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'materials' && (
        <div className="space-y-8">
        {/* Lecture Slides */}
        <section>
          <h2 className="text-xl font-semibold text-slate-200 mb-4">Vorlesungen</h2>
          {groupedMaterials.lecture_slide.length === 0 ? (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center text-slate-400">
              No lecture slides uploaded yet
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedMaterials.lecture_slide.map((material: any) => (
                <MaterialCard key={material.material_id} material={material} />
              ))}
            </div>
          )}
        </section>

        {/* Homework */}
        <section>
          <h2 className="text-xl font-semibold text-slate-200 mb-4">Hausaufgaben</h2>
          {groupedMaterials.homework.length === 0 ? (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center text-slate-400">
              No homework uploaded yet
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedMaterials.homework.map((material: any) => (
                <MaterialCard key={material.material_id} material={material} />
              ))}
            </div>
          )}
        </section>

        {/* Tutorium */}
        <section>
          <h2 className="text-xl font-semibold text-slate-200 mb-4">Übungen/Tutorium</h2>
          {groupedMaterials.tutorium.length === 0 ? (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center text-slate-400">
              No tutorium slides uploaded yet
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedMaterials.tutorium.map((material: any) => (
                <MaterialCard key={material.material_id} material={material} />
              ))}
            </div>
          )}
        </section>

        {/* Other */}
        {groupedMaterials.other.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold text-slate-200 mb-4">Sonstiges</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedMaterials.other.map((material: any) => (
                <MaterialCard key={material.material_id} material={material} />
              ))}
            </div>
          </section>
        )}
      </div>
      )}

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div className="space-y-6">
          <ManualAnalysisButton courseId={courseId!} />

          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-slate-200 mb-4">Erkenntnisse aus Studenten-Chats</h2>
            <p className="text-slate-400 mb-6">
              Hier werden automatisch Schwierigkeiten, Feedback und Fragemuster aus den Studenten-Chats extrahiert.
            </p>

            <FindingsList courseId={courseId!} />
          </div>
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <div className="space-y-6">
          <ReportControlBar
            courseId={courseId!}
            defaultDaysBack={course.report_days_back || 7}
            onReportGenerated={() => refetchReports()}
          />

          <ReportSettingsPanel
            courseId={courseId!}
            initialSettings={{
              report_days_back: course.report_days_back || 7,
              report_recipient_emails: course.report_recipient_emails || [],
              report_emails_enabled: course.report_emails_enabled || false,
            }}
            onSettingsUpdated={() => {
              // Optionally refetch course data to get updated settings
            }}
          />

          <LatestReportCard report={latestReport} isLoading={isLoadingReports || isLoadingLatestReport} />

          <PreviousReportsList courseId={courseId!} excludeLatest={latestReport?.report_id} />
        </div>
      )}

      {showUploadModal && (
        <UploadMaterialModal
          courseId={courseId!}
          onClose={() => setShowUploadModal(false)}
        />
      )}
    </div>
  );
}
