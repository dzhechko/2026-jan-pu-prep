import React from 'react';
import { useParams } from 'react-router-dom';

const LessonDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="min-h-screen bg-tg-bg p-4">
      <h1 className="text-2xl font-bold text-tg-text">Lesson Detail</h1>
      <p className="mt-2 text-tg-hint">Lesson ID: {id}</p>
    </div>
  );
};

export default LessonDetailPage;
