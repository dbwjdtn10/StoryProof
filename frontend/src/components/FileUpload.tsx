import { Upload, X, FileText, Merge, CheckSquare, Square } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { getChapters, uploadChapter, deleteChapter, getStoryboardStatus, Chapter, StoryboardProgress } from '../api/novel';
import { useFileMerge } from '../hooks/useFileMerge';

interface FileUploadProps {
    onFileClick: (chapter: Chapter) => void;
    novelId?: number;
    mode?: 'reader' | 'writer';
}

interface ChapterWithProgress extends Chapter {
    storyboardProgress?: StoryboardProgress;
}

export function FileUpload({ onFileClick, novelId, mode = 'writer' }: FileUploadProps) {
    const [uploadedFiles, setUploadedFiles] = useState<ChapterWithProgress[]>([]);
    const [dragActive, setDragActive] = useState(false);
    const [progressMap, setProgressMap] = useState<{ [key: number]: StoryboardProgress }>({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const progressIntervalRef = useRef<{ [key: number]: NodeJS.Timeout }>({});

    const {
        isMergeMode,
        selectedSourceIds,
        isMerging,
        toggleMergeMode,
        handleFileSelect,
        executeMerge,
        cancelMerge
    } = useFileMerge({
        novelId,
        onSuccess: () => {
            loadChapters(); // Refresh UI after merge
        }
    });

    // 진행 상황 조회 함수
    const fetchStoryboardStatus = async (chapterId: number) => {
        if (!novelId) return;
        try {
            const status = await getStoryboardStatus(novelId, chapterId);
            // console.log(`[Status] Chapter ${chapterId}:`, status); // 디버깅용
            setProgressMap(prev => ({ ...prev, [chapterId]: status }));

            // COMPLETED 또는 FAILED 상태면 폴링 중지
            const statusUpper = status.status?.toUpperCase();
            if (statusUpper === 'COMPLETED' || statusUpper === 'FAILED') {
                if (progressIntervalRef.current[chapterId]) {
                    clearInterval(progressIntervalRef.current[chapterId]);
                    delete progressIntervalRef.current[chapterId];
                }
            }
        } catch (error) {
            // console.error(`[Error] Failed to fetch status for ${chapterId}:`, error);
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

            // 기존 파일 중 처리 중인 파일이 있으면 폴링 시작
            chapters.forEach(chapter => {
                // chapter 객체에 storyboard_status가 없는 경우를 대비해 초기화
                const status = (chapter as any).storyboard_status?.toUpperCase();
                if (status === 'PROCESSING' || status === 'PENDING') {
                    startProgressPolling(chapter.id);
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
                id="file-upload-input"
                type="file"
                className="upload-input"
                onChange={handleChange}
                multiple
                accept=".pdf,.doc,.docx,.txt"
            />

            {/* Floating Upload Button */}
            {!isMergeMode && (
                <button className="floating-upload-btn" onClick={openFileDialog} title="파일 업로드">
                    <Upload size={24} />
                </button>
            )}

            <div className="upload-main">
                <div className="upload-content">
                    {/* Header */}
                    <div className="upload-header" style={{ textAlign: 'center', justifyContent: 'center' }}>
                        <div>
                            <h1 className="upload-title">{mode === 'reader' ? '작품 라이브러리' : '파일 업로드'}</h1>
                            <p className="upload-subtitle">StoryProof</p>
                        </div>
                    </div>

                    {/* Show upload area only if no files uploaded */}
                    {uploadedFiles.length === 0 && (
                        <div className="upload-area" onClick={openFileDialog} style={{ cursor: 'pointer' }}>
                            <label htmlFor="file-upload-input" className="upload-label" style={{ cursor: 'pointer' }}>
                                <Upload size={48} className="upload-icon" />
                                <p className="upload-text-main">
                                    {mode === 'reader'
                                        ? '자품 파일을 추가하여 읽기 시작하기'
                                        : '파일을 드래그하거나 클릭하여 업로드'}
                                </p>
                                <p className="upload-text-sub">PDF, HWP, TXT 파일 지원</p>
                            </label>
                        </div>
                    )}

                    {/* Uploaded Files Grid */}
                    {uploadedFiles.length > 0 && (
                        <div className="uploaded-files-section">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 className="uploaded-files-title" style={{ marginBottom: 0 }}>
                                    {isMergeMode ? '병합할 파일 선택' : '업로드된 파일'}
                                </h2>

                                {/* Merge Controls */}
                                {mode === 'writer' && uploadedFiles.length > 1 && (
                                    <div>
                                        {!isMergeMode ? (
                                            <button
                                                onClick={toggleMergeMode}
                                                className="merge-toggle-btn"
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px',
                                                    padding: '8px 16px',
                                                    borderRadius: '8px',
                                                    border: '1px solid #e5e7eb',
                                                    backgroundColor: 'white',
                                                    cursor: 'pointer',
                                                    fontWeight: 500,
                                                    color: '#374151',
                                                    fontSize: '14px'
                                                }}
                                            >
                                                <Merge size={16} />
                                                파일 병합
                                            </button>
                                        ) : (
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button
                                                    onClick={cancelMerge}
                                                    style={{
                                                        padding: '8px 16px',
                                                        borderRadius: '8px',
                                                        border: '1px solid #e5e7eb',
                                                        backgroundColor: 'white',
                                                        cursor: 'pointer',
                                                        color: '#6b7280',
                                                        fontSize: '14px'
                                                    }}
                                                >
                                                    취소
                                                </button>
                                                <button
                                                    onClick={executeMerge}
                                                    disabled={selectedSourceIds.length < 2 || isMerging}
                                                    style={{
                                                        padding: '8px 16px',
                                                        borderRadius: '8px',
                                                        border: 'none',
                                                        backgroundColor: selectedSourceIds.length < 2 ? '#e5e7eb' : '#4F46E5',
                                                        cursor: selectedSourceIds.length < 2 ? 'not-allowed' : 'pointer',
                                                        color: selectedSourceIds.length < 2 ? '#9ca3af' : 'white',
                                                        fontSize: '14px',
                                                        fontWeight: 600
                                                    }}
                                                >
                                                    {isMerging ? '병합 중...' : `${selectedSourceIds.length}개 병합`}
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="uploaded-files-grid">
                                {uploadedFiles.map((file) => {
                                    const progress = progressMap[file.id];
                                    const statusUpper = progress?.status?.toUpperCase();
                                    const isProcessing = statusUpper === 'PROCESSING';
                                    const isCompleted = statusUpper === 'COMPLETED';
                                    const isFailed = statusUpper === 'FAILED';

                                    const isSelected = selectedSourceIds.includes(file.id);

                                    return (
                                        <div
                                            key={file.id}
                                            className={`uploaded-file-card ${isSelected ? 'selected' : ''}`}
                                            onClick={() => {
                                                if (isMergeMode) {
                                                    handleFileSelect(file.id);
                                                } else if (!isProcessing) {
                                                    onFileClick(file);
                                                }
                                            }}
                                            style={{
                                                cursor: isMergeMode ? 'pointer' : (isProcessing ? 'wait' : 'pointer'),
                                                border: isSelected ? '2px solid #4F46E5' : '1px solid #e5e7eb',
                                                position: 'relative'
                                            }}
                                        >
                                            {/* Selection Checkbox (Merge Mode) */}
                                            {isMergeMode && (
                                                <div
                                                    style={{
                                                        position: 'absolute',
                                                        top: '12px',
                                                        left: '12px',
                                                        color: isSelected ? '#4F46E5' : '#9ca3af'
                                                    }}
                                                >
                                                    {isSelected ? <CheckSquare size={20} /> : <Square size={20} />}
                                                </div>
                                            )}

                                            {!isMergeMode && (
                                                <button
                                                    className="file-remove-btn"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        removeFile(file.id);
                                                    }}
                                                    disabled={isProcessing}
                                                >
                                                    <X size={16} />
                                                </button>
                                            )}

                                            <FileText
                                                size={40}
                                                className="file-icon"
                                                style={{ color: isSelected ? '#4F46E5' : undefined }}
                                            />
                                            <p className="file-name">{file.title}</p>

                                            {/* Badge or indicator for target */}
                                            {isMergeMode && isSelected && selectedSourceIds[0] === file.id && (
                                                <span style={{
                                                    fontSize: '10px',
                                                    backgroundColor: '#EEF2FF',
                                                    color: '#4F46E5',
                                                    padding: '2px 6px',
                                                    borderRadius: '4px',
                                                    marginTop: '4px'
                                                }}>
                                                    대표(저장) 파일
                                                </span>
                                            )}

                                            {/* 스토리보드 처리 진행 상황 표시 (Not in merge mode or simplified) */}
                                            {!isMergeMode && progress && (
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
