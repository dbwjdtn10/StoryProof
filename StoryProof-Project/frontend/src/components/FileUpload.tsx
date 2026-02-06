import { Upload, X, FileText } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { getChapters, uploadChapter, deleteChapter, getStoryboardStatus, Chapter, StoryboardProgress } from '../api/novel';

interface FileUploadProps {
    onFileClick: (chapter: Chapter) => void;
    novelId?: number;
}

interface ChapterWithProgress extends Chapter {
    storyboardProgress?: StoryboardProgress;
    storyboard_status?: string;
}

export function FileUpload({ onFileClick, novelId }: FileUploadProps) {
    const [uploadedFiles, setUploadedFiles] = useState<ChapterWithProgress[]>([]);
    const [dragActive, setDragActive] = useState(false);
    const [progressMap, setProgressMap] = useState<{ [key: number]: StoryboardProgress }>({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const progressIntervalRef = useRef<{ [key: number]: NodeJS.Timeout }>({});
    const [copyTargetId, setCopyTargetId] = useState<number | null>(null);

    const [isMergeMode, setIsMergeMode] = useState(false);
    const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);

    // 진행 상황 조회 함수
    const fetchStoryboardStatus = async (chapterId: number) => {
        if (!novelId) return;
        try {
            const status = await getStoryboardStatus(novelId, chapterId);
            setProgressMap(prev => ({ ...prev, [chapterId]: status }));

            // COMPLETED 또는 FAILED 상태면 폴링 중지 (대문자 지원)
            const statusUpper = status.status?.toUpperCase();
            if (statusUpper === 'COMPLETED' || statusUpper === 'FAILED') {
                if (progressIntervalRef.current[chapterId]) {
                    clearInterval(progressIntervalRef.current[chapterId]);
                    delete progressIntervalRef.current[chapterId];
                }
            }
        } catch (error) {
            // 조용히 무시
        }
    };

    // 진행 상황 폴링 시작
    const startProgressPolling = (chapterId: number) => {
        // 기존 폴링이 있으면 중지
        if (progressIntervalRef.current[chapterId]) {
            clearInterval(progressIntervalRef.current[chapterId]);
        }

        // 1초마다 상태 조회 (더 빠른 실시간 업데이트)
        progressIntervalRef.current[chapterId] = setInterval(() => {
            fetchStoryboardStatus(chapterId);
        }, 1000);

        // 초기 조회
        fetchStoryboardStatus(chapterId);
    };

    // Fetch existing chapters
    useEffect(() => {
        if (novelId) {
            loadChapters();
        }
    }, [novelId]);

    const loadChapters = async () => {
        if (!novelId) return;
        try {
            const chapters = await getChapters(novelId);
            setUploadedFiles(chapters);

            // [추가] 분석 중인 파일이 있다면 자동으로 폴링 재개
            chapters.forEach((chapter: ChapterWithProgress) => {
                const status = (chapter.storyboard_status || '').toUpperCase();
                if (status === 'PROCESSING' || status === 'PENDING') {
                    // 이미 폴링 중이지 않은 경우에만 시작
                    if (!progressIntervalRef.current[chapter.id]) {
                        startProgressPolling(chapter.id);
                    }
                }
            });
        } catch (error) {
            console.error("Failed to load chapters:", error);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleMerge = async () => {
        if (!novelId || selectedSourceIds.length < 2) {
            alert("합칠 파일을 2개 이상 선택해 주세요.");
            return;
        }
    
        const targetId = selectedSourceIds[0];
        const sourceIds = selectedSourceIds.slice(1);
    
        try {
            // 주소를 http://localhost:8000으로 명시하여 3000번 포트(프론트)에서 404가 나는 것을 방지합니다.
            const res = await fetch(`http://localhost:8000/api/v1/novels/${novelId}/merge-contents`, { 
                method: 'PATCH', 
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    source_ids: sourceIds, 
                    target_id: targetId 
                })
            });
        
            if (res.ok) {
                const data = await res.json();
                alert("파일이 합쳐졌습니다. 통합 분석을 시작합니다.");

                setIsMergeMode(false);
                setSelectedSourceIds([]);

                if (data.new_id) {
                    startProgressPolling(data.new_id);
                }
            
                await loadChapters();
            } else {
                const errorData = await res.json().catch(() => ({}));
                alert(`합치기 실패: ${errorData.message || '서버 응답 오류'}`);
            }
        } catch (error) {
            console.error("Network Error:", error);
            alert("네트워크 오류가 발생했습니다. 서버가 실행 중인지 확인해주세요.");
        }
    };
    
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFiles(e.dataTransfer.files);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFiles(e.target.files);
        }
    };

    const handleFiles = async (files: FileList) => {
        if (!novelId) {
            alert("소설 정보가 없습니다. 다시 로그인해주세요.");
            return;
        }

        const fileArray = Array.from(files);

        // Calculate max chapter number from existing files
        let maxChapterNum = uploadedFiles.reduce((max, file) => Math.max(max, file.chapter_number || 0), 0);

        for (const file of fileArray) {
            try {
                // Determine next chapter number based on current max
                maxChapterNum++;
                const nextChapterNum = maxChapterNum;
                const title = file.name; // Use filename as title by default

                const newChapter = await uploadChapter(novelId, file, nextChapterNum, title);

                // 진행 상황 폴링 시작
                startProgressPolling(newChapter.id);
            } catch (error) {
                alert(`${file.name} 업로드 실패: ${(error as any).message || '알 수 없는 오류'}`);
                // Decrease maxChapterNum back if failed, so we don't skip numbers unnecessarily? 
                // Actually if it failed due to conflict, we might want to skip or retry, but for now just let it be.
                // But if we continue the loop for next file, we should arguably keep incrementing to avoid same conflict 
                // if the conflict was the cause. 
                // Ideally we should probably fetch the latest list again if we suspect sync issues, but local max is safer.
            }
        }

        // Refresh list
        loadChapters();
    };

    const removeFile = async (id: number) => {
        if (!novelId) return;

        try {
            if (confirm("이 파일을 정말 삭제하시겠습니까?")) {
                await deleteChapter(novelId, id);
                setUploadedFiles((prev) => prev.filter((file) => file.id !== id));
            }
        } catch (error) {
            alert("파일 삭제 실패");
        }
    };

    const openFileDialog = () => {
        fileInputRef.current?.click();
    };

    return (
        <div
            className="upload-container"
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            {/* Drag Overlay */}
            {dragActive && (
                <div className="drag-overlay">
                    <div className="drag-overlay-content">
                        <Upload size={64} />
                        <p>파일을 여기에 놓으세요</p>
                    </div>
                </div>
            )}

            {/* Hidden File Input */}
            <input
                ref={fileInputRef}
                type="file"
                className="upload-input"
                onChange={handleChange}
                multiple
                accept=".pdf,.doc,.docx,.txt"
            />

            {/* Floating Upload Button */}
            <button className="floating-upload-btn" onClick={openFileDialog} title="파일 업로드">
                <Upload size={24} />
            </button>

            <div className="upload-main">
                <div className="upload-content">
                    {/* Header */}
                    <div className="upload-header">
                        <h1 className="upload-title">파일 업로드</h1>
                        <p className="upload-subtitle">StoryProof</p>
                    </div>

                    {/* Show upload area only if no files uploaded */}
                    {uploadedFiles.length === 0 && (
                        <div className="upload-area">
                            <label htmlFor="file-upload-input" className="upload-label">
                                <Upload size={48} className="upload-icon" />
                                <p className="upload-text-main">파일을 드래그하거나 클릭하여 업로드</p>
                                <p className="upload-text-sub">PDF, HWP, TXT 파일 지원</p>
                            </label>
                        </div>
                    )}

                    {/* Uploaded Files Grid */}
                    {uploadedFiles.length > 0 && (
                        <div className="uploaded-files-section">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 className="uploaded-files-title" style={{ margin: 0 }}>업로드된 파일</h2>

                                <div style={{ display: 'flex', gap: '8px' }}>
                                    {!isMergeMode ? (
                                        <button 
                                            onClick={() => setIsMergeMode(true)}
                                            style={{ padding: '6px 12px', background: '#000', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold' }}
                                        >
                                            파일 합치기
                                        </button>
                                    ) : (
                                        <>
                                            <button 
                                                onClick={(e) => { e.preventDefault(); handleMerge(); }}
                                                style={{ padding: '6px 12px', background: '#4CAF50', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold' }}
                                            >
                                                완료 ({selectedSourceIds.length})
                                            </button>
                                            <button 
                                                onClick={() => { setIsMergeMode(false); setSelectedSourceIds([]); }}
                                                style={{ padding: '6px 12px', background: '#eee', color: '#000', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}
                                            >
                                                취소
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>

                            <div className="uploaded-files-grid">
                                {uploadedFiles.map((file) => {
                                    const progress = progressMap[file.id];
                                    const statusUpper = progress?.status?.toUpperCase();
                                    const currentStatus = (progress?.status || file.storyboard_status || '').toUpperCase();
                                    const isProcessing = currentStatus === 'PROCESSING' || currentStatus === 'PENDING';
                                    const isCompleted = statusUpper === 'COMPLETED';
                                    const isFailed = statusUpper === 'FAILED';
                                    const isSelected = selectedSourceIds.includes(file.id);

                                    return (
                                        <div
                                            key={file.id}
                                            className={`uploaded-file-card group ${isProcessing ? 'is-analyzing' : ''}`}
                                            onClick={() => {
                                                if (isMergeMode) {
                                                    setSelectedSourceIds(prev => 
                                                        prev.includes(file.id) ? prev.filter(id => id !== file.id) : [...prev, file.id]
                                                    );
                                                } else if (isProcessing) {
                                                    alert("현재 통합 분석 중입니다. 잠시만 기다려 주세요.");
                                                } else {
                                                    onFileClick(file);
                                                }
                                            }}
                                            style={{ 
                                                cursor: isProcessing ? 'wait' : 'pointer', // 분석 중이면 커서를 로딩 모양으로
                                                position: 'relative',
                                                border: isSelected ? '2px solid #4CAF50' : (isProcessing ? '1px solid #4c6ef5' : 'none'),
                                                opacity: isProcessing ? 0.8 : 1 // 분석 중인 파일은 약간 흐리게 표시하여 '처리 중'임을 암시
                                            }}
                                        >
                                            {/* [추가] 클릭 순서 배지 표시 */}
                                            {isMergeMode && isSelected && (
                                                <div style={{
                                                    position: 'absolute',
                                                    top: '10px',
                                                    left: '10px',
                                                    width: '24px',
                                                    height: '24px',
                                                    backgroundColor: '#4CAF50',
                                                    color: 'white',
                                                    borderRadius: '50%',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    fontSize: '14px',
                                                    fontWeight: 'bold',
                                                    zIndex: 30,
                                                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                                                }}>
                                                    {selectedSourceIds.indexOf(file.id) + 1}
                                                </div>
                                            )}
                                            {/* 합치기 모드일 때는 삭제 버튼 영역을 렌더링하지 않아 충돌 방지 */}
                                            {!isMergeMode && (
                                                <div 
                                                    className="file-card-buttons" 
                                                    style={{ 
                                                        position: 'absolute', 
                                                        top: '0.75rem', 
                                                        right: '0.75rem', 
                                                        display: 'flex',
                                                        gap: '5px', 
                                                        alignItems: 'center', 
                                                        zIndex: 20 
                                                    }}
                                                >                        
                                                    <button
                                                        className="file-remove-btn"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            removeFile(file.id);
                                                        }}
                                                        disabled={isProcessing}
                                                        // style 속성에서 opacity를 제거하여 css 설정이 먹히게 함
                                                        style={{ position: 'static' }} 
                                                    >
                                                        <X size={16} />
                                                    </button>
                                                </div>
                                            )}

                                            <FileText size={40} className={`file-icon ${isProcessing ? 'animate-pulse' : ''}`} />
                                            <p className="file-name">{file.title}</p>

                                            {/* 스토리보드 처리 진행 상황 표시 */}
                                            {progress && (
                                                <div style={{ marginTop: '8px', width: '100%' }}>
                                                    {/* 상태 뱃지 */}
                                                    <div style={{ textAlign: 'center', marginBottom: '8px' }}>
                                                        <span style={{
                                                            display: 'inline-block',
                                                            fontSize: '11px',
                                                            fontWeight: 600,
                                                            padding: '4px 8px',
                                                            borderRadius: '4px',
                                                            backgroundColor: isFailed ? '#ffe0e0' : isCompleted ? '#e0ffe0' : '#e0e8ff',
                                                            color: isFailed ? '#ff6b6b' : isCompleted ? '#51cf66' : '#4c6ef5'
                                                        }}>
                                                            {isFailed ? '❌ 실패' : isCompleted ? '✅ 완료' : '⏳ 처리 중'}
                                                        </span>
                                                    </div>

                                                    {/* 진행률 텍스트 */}
                                                    {isProcessing && (
                                                        <div style={{ textAlign: 'center', marginBottom: '6px' }}>
                                                            <span style={{ fontSize: '13px', color: '#333', fontWeight: 600 }}>
                                                                {progress.progress}%
                                                            </span>
                                                        </div>
                                                    )}

                                                    {/* 진행 메시지 */}
                                                    {progress.message && (
                                                        <div style={{ textAlign: 'center', marginBottom: '6px' }}>
                                                            <span style={{ fontSize: '11px', color: '#666', fontWeight: 500 }}>
                                                                {progress.message}
                                                            </span>
                                                        </div>
                                                    )}

                                                    {/* 진행 막대 */}
                                                    {isProcessing && (
                                                        <div style={{
                                                            width: '100%',
                                                            height: '5px',
                                                            backgroundColor: '#e0e0e0',
                                                            borderRadius: '3px',
                                                            overflow: 'hidden',
                                                            marginBottom: '4px'
                                                        }}>
                                                            <div style={{
                                                                height: '100%',
                                                                width: `${progress.progress}%`,
                                                                backgroundColor: '#4c6ef5',
                                                                transition: 'width 0.3s ease',
                                                                borderRadius: '3px',
                                                                boxShadow: '0 0 10px rgba(76, 110, 245, 0.5)'
                                                            }} />
                                                        </div>
                                                    )}

                                                    {/* 완료 상태 */}
                                                    {isCompleted && (
                                                        <div style={{
                                                            width: '100%',
                                                            height: '5px',
                                                            backgroundColor: '#51cf66',
                                                            borderRadius: '3px',
                                                            boxShadow: '0 0 10px rgba(81, 207, 102, 0.5)'
                                                        }} />
                                                    )}

                                                    {/* 실패 상태 */}
                                                    {isFailed && (
                                                        <div>
                                                            <div style={{
                                                                width: '100%',
                                                                height: '5px',
                                                                backgroundColor: '#ff6b6b',
                                                                borderRadius: '3px',
                                                                boxShadow: '0 0 10px rgba(255, 107, 107, 0.5)',
                                                                marginBottom: '4px'
                                                            }} />
                                                            {progress.error && (
                                                                <div style={{ textAlign: 'center', marginTop: '4px' }}>
                                                                    <span style={{ fontSize: '10px', color: '#ff6b6b', fontWeight: 500 }}>
                                                                        {progress.error}
                                                                    </span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Theme Toggle */}
            <ThemeToggle />
        </div>
    );
}
