import { PenLine } from 'lucide-react';

interface CardProps {
  id: number;
  title: string;
  description: string;
  image: string;
  imageType: 'round' | 'badge';
}

export function Card({ title, description, image, imageType }: CardProps) {
  return (
    <div className="card-container">
      {/* Title Section with Gradient Background */}
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>

      {/* Content Area for Text */}
      <div className="card-content">
        <div className="card-text-area">
          {/* 텍스트가 여기에 들어갈 예정 */}
        </div>
      </div>
    </div>
  );
}