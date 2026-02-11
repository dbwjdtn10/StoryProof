import { Lock, ArrowLeft } from 'lucide-react';
import { Card } from './Card';

// const navItems = [
//   { icon: Users, label: '사용자' },
//   { icon: TrendingUp, label: '통계' },
//   { icon: FileText, label: '문서' },
//   { icon: Video, label: '영상' },
//   { icon: CreditCard, label: '결제' },
//   { icon: Calendar, label: '일정' },
//   { icon: BarChart3, label: '분석' },
//   { icon: Settings, label: '설정' },
// ];

const cardData = [
  {
    id: 1,
    title: '1장. 토끼 굴속으로',
    description: '고궁과 전통 건축의 아름다움을 담은 작품입니다.',
    image: 'https://images.unsplash.com/photo-1663940019982-c14294717dbd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhcmNoaXRlY3R1cmUlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjkzNjM4ODh8MA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'round' as const,
  },
  {
    id: 2,
    title: '2장. 눈물 웅덩이',
    description: '세계 문화유산으로 지정된 역사적 장소입니다.',
    image: 'https://images.unsplash.com/photo-1717961867886-ba6473fa2107?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxoaXN0b3JpY2FsJTIwbW9udW1lbnR8ZW58MXx8fHwxNzY5NDAxMTkyfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 3,
    title: '3장. 코커스 경주와 긴 이야기',
    description: '현대와 전통이 조화를 이루는 아름다운 건축물입니다.',
    image: 'https://images.unsplash.com/photo-1642886450202-0cfda7d1017f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaXR5JTIwbGFuZG1hcmt8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 4,
    title: '4장. 토끼가 꼬마 도마뱀 빌을 (집 굴뚝 안으로) 들여보내다',
    description: '우리의 소중한 문화유산을 지키고 보존합니다.',
    image: 'https://images.unsplash.com/photo-1766814495643-fc11febde681?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx2aW50YWdlJTIwYmFkZ2V8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 5,
    title: '5장. 애벌레의 충고',
    description: '조선시대 왕실의 위엄과 품격을 느낄 수 있습니다.',
    image: 'https://images.unsplash.com/photo-1663940019982-c14294717dbd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhcmNoaXRlY3R1cmUlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjkzNjM4ODh8MA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 6,
    title: '6장. 돼지와 후춧가루',
    description: '유네스코가 인정한 귀중한 인류의 유산입니다.',
    image: 'https://images.unsplash.com/photo-1717961867886-ba6473fa2107?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxoaXN0b3JpY2FsJTIwbW9udW1lbnR8ZW58MXx8fHwxNzY5NDAxMTkyfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 7,
    title: '7장. 이상한 다과회',
    description: '정교한 건축 기법과 예술성이 돋보이는 작품입니다.',
    image: 'https://images.unsplash.com/photo-1642886450202-0cfda7d1017f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaXR5JTIwbGFuZG1hcmt8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 8,
    title: '8장. 여왕의 크로케 경기장',
    description: '역사와 문화가 살아 숨쉬는 특별한 장소입니다.',
    image: 'https://images.unsplash.com/photo-1766814495643-fc11febde681?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx2aW50YWdlJTIwYmFkZ2V8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 9,
    title: '9장. 가짜 거북이의 사연',
    description: '오랜 세월을 견뎌온 건축물의 역사를 담았습니다.',
    image: 'https://images.unsplash.com/photo-1663940019982-c14294717dbd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhcmNoaXRlY3R1cmUlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjkzNjM4ODh8MA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 10,
    title: '10장. 바닷가재의 카드리유(사교댄스 이름)',
    description: '많은 사람들이 찾는 인기 있는 관광 명소입니다.',
    image: 'https://images.unsplash.com/photo-1717961867886-ba6473fa2107?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxoaXN0b3JpY2FsJTIwbW9udW1lbnR8ZW58MXx8fHwxNzY5NDAxMTkyfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 11,
    title: '11장. 누가 과일 파이들을 훔쳤나?',
    description: '한국 전통 예술의 정수를 보여주는 걸작입니다.',
    image: 'https://images.unsplash.com/photo-1642886450202-0cfda7d1017f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaXR5JTIwbGFuZG1hcmt8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
  {
    id: 12,
    title: '12장. 앨리스의 증언',
    description: '우리 선조들의 지혜와 노력이 담긴 유산입니다.',
    image: 'https://images.unsplash.com/photo-1766814495643-fc11febde681?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx2aW50YWdlJTIwYmFkZ2V8ZW58MXx8fHwxNzY5NDAxMTkzfDA&ixlib=rb-4.1.0&q=80&w=1080',
    imageType: 'badge' as const,
  },
];

export function Dashboard({ mode = 'writer' }: { mode?: 'reader' | 'writer' }) {
  const isReader = mode === 'reader';
  const displayTitle = isReader ? "독자용 작품 요약 및 해설" : "이상한 나라의 앨리스";
  const displaySubtitle = isReader ? "작품의 이해를 돕는 AI 가이드" : "StoryProof 작가 분석 도구";

  const writerCards = [
    {
      id: 101,
      title: '플롯홀 탐지',
      description: 'AI가 스토리의 설정 모순이나 전개상 흐트러진 부분을 자동으로 찾아냅니다.',
      image: 'https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&q=80&w=1080',
      imageType: 'round' as const,
      category: 'WRITER_TOOL',
      tag: 'Plot Hole'
    },
    {
      id: 102,
      title: '일관성 리포트',
      description: '캐릭터의 말투, 외모, 하차 시점 등 설정이 끝까지 유지되는지 검사합니다.',
      image: 'https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&q=80&w=1080',
      imageType: 'badge' as const,
      category: 'WRITER_TOOL',
      tag: 'Character'
    },
    {
      id: 103,
      title: '설정 파괴 경고',
      description: '새로 쓴 내용이 기존 세계관(지명, 역사 등)과 충돌할 경우 실시간 알림을 줍니다.',
      image: 'https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&q=80&w=1080',
      imageType: 'badge' as const,
      category: 'WRITER_TOOL',
      tag: 'World'
    }
  ];

  const readerCards = [
    {
      id: 201,
      title: 'AI 어휘 사전',
      description: '작품 속 어려운 단어나 고어, 전문 용어를 AI가 바로 풀이해 드립니다.',
      image: 'https://images.unsplash.com/photo-1491841573634-28140fc7ced7?auto=format&fit=crop&q=80&w=1080',
      imageType: 'round' as const,
      category: 'READER_TOOL',
      tag: 'Dictionary'
    },
    {
      id: 202,
      title: '장면 코멘트',
      description: '특정 장면에 대한 다른 독자들의 생각과 반응을 실시간으로 확인하세요.',
      image: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&q=80&w=1080',
      imageType: 'badge' as const,
      category: 'READER_TOOL',
      tag: 'Social'
    },
    {
      id: 203,
      title: '인물 관계도',
      description: '현재까지 읽은 내용을 바탕으로 복잡한 등장인물 지도를 보여줍니다.',
      image: 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=1080',
      imageType: 'badge' as const,
      category: 'READER_TOOL',
      tag: 'Map'
    }
  ];

  // 작가 모드일 때는 기본 소설 목록 + 작가 도구
  // 독자 모드일 때는 독자 전용 도구만 표시 (또는 별도 구성)
  const cardsToDisplay = isReader ? readerCards : [...writerCards, ...cardData];

  return (
    <div className="dashboard-container">
      {/* Main Content */}
      <main className="dashboard-main">
        <div className="dashboard-content">
          {/* Header */}
          <div className="dashboard-header">
            <div className="dashboard-brand">
              <div className="dashboard-logo-icon">
                <Lock size={28} strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="dashboard-title">{displayTitle}</h1>
                <p className="dashboard-subtitle">{displaySubtitle}</p>
              </div>
            </div>
            <button className="dashboard-back-button">
              <ArrowLeft size={20} />
              <span>뒤로가기</span>
            </button>
          </div>

          {/* Mode Badge */}
          <div style={{ marginBottom: '20px' }}>
            <span style={{
              padding: '6px 12px',
              borderRadius: '20px',
              backgroundColor: isReader ? '#E0F2FE' : '#EEF2FF',
              color: isReader ? '#0369A1' : '#4F46E5',
              fontSize: '14px',
              fontWeight: 600,
              border: isReader ? '1px solid #BAE6FD' : '1px solid #C7D2FE'
            }}>
              {isReader ? '📖 독자 모드 활성화됨' : '✍️ 작가 모드 활성화됨'}
            </span>
          </div>

          {/* Cards Grid */}
          <div className="dashboard-grid">
            {cardsToDisplay.map((card) => (
              <Card key={card.id} {...card} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}