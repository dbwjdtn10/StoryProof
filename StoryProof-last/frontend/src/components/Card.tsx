import { PenLine, BookOpen, Hash } from 'lucide-react';

interface CardProps {
  id: number;
  title: string;
  description: string;
  image: string;
  imageType: 'round' | 'badge';
  category?: string;
  tag?: string;
}

export function Card({ title, description, category, tag }: CardProps) {
  const isTool = !!category;

  return (
    <div className={`card-container ${isTool ? 'tool-card' : ''}`}>
      {/* Category Icon & Tag */}
      <div className="card-overlay-top">
        {category === 'WRITER_TOOL' && <PenLine size={16} className="tool-icon writer" />}
        {category === 'READER_TOOL' && <BookOpen size={16} className="tool-icon reader" />}
        {!category && <Hash size={16} className="tool-icon" />}
        {tag && <span className="card-tag">{tag}</span>}
      </div>

      {/* Title Section with Gradient Background */}
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>

      {/* Content Area for Text */}
      <div className="card-content">
        <p className="card-description">{description}</p>
        <div className="card-action">
          <span>{isTool ? '실행하기' : '읽기 시작'}</span>
          <div className="action-arrow">→</div>
        </div>
      </div>
    </div>
  );
}