# ChapterDetail.tsx 통합 가이드

## 개요
`ChapterDetail.tsx`에 설정파괴분석기 기능을 통합하기 위한 코드 스니펫입니다.

## 1. Import 추가

파일 상단에 다음 import를 추가하세요:

```typescript
import { requestConsistencyCheck, getTaskResult, ConsistencyResult } from '../api/analysis';
import { FloatingMenu } from './FloatingMenu';
```

## 2. State 추가

컴포넌트 내부에 다음 state를 추가하세요:

```typescript
const [isCheckingConsistency, setIsCheckingConsistency] = useState(false);
const [consistencyResult, setConsistencyResult] = useState<ConsistencyResult | null>(null);
```

## 3. handleCheckConsistency 함수 추가

다음 함수를 컴포넌트에 추가하세요:

```typescript
const handleCheckConsistency = async () => {
    if (!chapter || !novel) {
        alert('챕터 정보를 불러올 수 없습니다.');
        return;
    }

    // 현재 편집 중인 텍스트 가져오기
    const textToCheck = chapter.content; // 또는 현재 편집 중인 텍스트

    setIsCheckingConsistency(true);
    setConsistencyResult(null);

    try {
        // 1. 분석 요청
        const { task_id } = await requestConsistencyCheck({
            novel_id: novel.id,
            chapter_id: chapter.id,
            text: textToCheck
        });

        // 2. 폴링으로 결과 확인 (2초 간격)
        const pollInterval = setInterval(async () => {
            try {
                const result = await getTaskResult(task_id);
                
                if (result.status === 'COMPLETED') {
                    clearInterval(pollInterval);
                    setConsistencyResult(result);
                    setIsCheckingConsistency(false);
                    
                    // 결과 표시
                    if (result.result?.status === '설정 파괴 감지') {
                        alert(`설정 파괴가 감지되었습니다!\n${result.result.results.length}개의 문제점이 발견되었습니다.`);
                    } else {
                        alert('설정 일관성 검사 완료: 문제 없음');
                    }
                } else if (result.status === 'FAILED') {
                    clearInterval(pollInterval);
                    setIsCheckingConsistency(false);
                    alert('분석 중 오류가 발생했습니다: ' + result.error);
                }
            } catch (error) {
                console.error('폴링 오류:', error);
            }
        }, 2000);

        // 최대 60초 후 타임아웃
        setTimeout(() => {
            clearInterval(pollInterval);
            if (isCheckingConsistency) {
                setIsCheckingConsistency(false);
                alert('분석 시간이 초과되었습니다.');
            }
        }, 60000);

    } catch (error) {
        console.error('설정 일관성 검사 오류:', error);
        alert('분석 요청 중 오류가 발생했습니다.');
        setIsCheckingConsistency(false);
    }
};
```

## 4. FloatingMenu 컴포넌트 추가

JSX 반환 부분에 FloatingMenu를 추가하세요:

```typescript
return (
    <div className="chapter-detail">
        {/* 기존 코드 */}
        
        {/* FloatingMenu 추가 */}
        <FloatingMenu
            onCheckConsistency={handleCheckConsistency}
            novelId={novel?.id}
            chapterId={chapter?.id}
        />
        
        {/* 로딩 인디케이터 (선택사항) */}
        {isCheckingConsistency && (
            <div className="consistency-checking-overlay">
                <div className="spinner">분석 중...</div>
            </div>
        )}
        
        {/* 결과 표시 모달 (선택사항) */}
        {consistencyResult && consistencyResult.result && (
            <div className="consistency-result-modal">
                <h3>{consistencyResult.result.status}</h3>
                <ul>
                    {consistencyResult.result.results.map((item, idx) => (
                        <li key={idx}>
                            <strong>{item.type}</strong>
                            <p>문제: {item.quote}</p>
                            <p>설명: {item.description}</p>
                            <p>제안: {item.suggestion}</p>
                        </li>
                    ))}
                </ul>
                <button onClick={() => setConsistencyResult(null)}>닫기</button>
            </div>
        )}
    </div>
);
```

## 5. CSS 추가 (선택사항)

```css
.consistency-checking-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.spinner {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    font-size: 1.2rem;
}

.consistency-result-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 2rem;
    border-radius: 8px;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
```

## 완료!

이제 FloatingMenu의 설정파괴분석기 버튼을 클릭하면 분석이 시작됩니다.
