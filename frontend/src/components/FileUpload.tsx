import { Upload, X, FileText } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { getChapters, uploadChapter, deleteChapter, getStoryboardStatus, Chapter, StoryboardProgress } from '../api/novel';

interface FileUploadProps {
    onFileClick: (chapter: Chapter) => void;
}

interface ChapterWithProgress extends Chapter {
    storyboardProgress?: StoryboardProgress;
}

export function FileUpload({ onFileClick }: FileUploadProps) {
    const [uploadedFiles, setUploadedFiles] = useState<ChapterWithProgress[]>([]);
    const [dragActive, setDragActive] = useState(false);
    const [progressMap, setProgressMap] = useState<{ [key: number]: StoryboardProgress }>({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const progressIntervalRef = useRef<{ [key: number]: NodeJS.Timeout }>({});

    // 진행 상황 조회 함수
    const fetchStoryboardStatus = async (novelId: number, chapterId: number) => {
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
    const startProgressPolling = (novelId: number, chapterId: number) => {
        // 기존 폴링이 있으면 중지
        if (progressIntervalRef.current[chapterId]) {
            clearInterval(progressIntervalRef.current[chapterId]);
        }

        // 1초마다 상태 조회 (더 빠른 실시간 업데이트)
        progressIntervalRef.current[chapterId] = setInterval(() => {
            fetchStoryboardStatus(novelId, chapterId);
        }, 1000);

        // 초기 조회
        fetchStoryboardStatus(novelId, chapterId);
    };

    // Load all chapters from all novels
    useEffect(() => {
        loadAllChapters();
    }, []);

    const loadAllChapters = async () => {
        try {
            // Get all novels
            const { getNovels } = await import('../api/novel');
            const novelsResponse = await getNovels(0, 100);

            // Collect all chapters from all novels
            const allChapters: ChapterWithProgress[] = [];
            for (const novel of novelsResponse.novels) {
                const chapters = await getChapters(novel.id);
                allChapters.push(...chapters);
            }
            setUploadedFiles(allChapters);
        } catch (error) {
            console.error("Failed to load files:", error);
            alert("업로드된 파일 목록을 불러오는데 실패했습니다. 페이지를 새로고침해주세요.");
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
        const fileArray = Array.from(files);
        const { createNovel } = await import('../api/novel');

        for (const file of fileArray) {
            try {
                // Create a new Novel for each file
                const title = file.name.replace(/\.[^/.]+$/, ''); // Remove file extension
                const newNovel = await createNovel({
                    title: title,
                    description: `Uploaded from ${file.name}`,
                    genre: "General"
                });

                // Upload the file as Chapter #1 of this novel
                const newChapter = await uploadChapter(newNovel.id, file, 1, title);

                // 진행 상황 폴링 시작
                startProgressPolling(newNovel.id, newChapter.id);
            } catch (error) {
                alert(`${file.name} 업로드 실패: ${(error as any).message || '알 수 없는 오류'}`);
            }
        }

        // Refresh list
        loadAllChapters();
    };

    const removeFile = async (id: number) => {
        try {
            // Find the chapter to get its novel_id
            const chapter = uploadedFiles.find(f => f.id === id);
            if (!chapter) return;

            if (confirm("이 파일을 정말 삭제하시겠습니까?")) {
                await deleteChapter(chapter.novel_id, id);
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
                            <h2 className="uploaded-files-title">업로드된 파일</h2>
                            <div className="uploaded-files-grid">
                                {uploadedFiles.map((file) => {
                                    const progress = progressMap[file.id];
                                    const statusUpper = progress?.status?.toUpperCase();
                                    const isProcessing = statusUpper === 'PROCESSING';
                                    const isCompleted = statusUpper === 'COMPLETED';
                                    const isFailed = statusUpper === 'FAILED';

                                    return (
                                        <div
                                            key={file.id}
                                            className="uploaded-file-card"
                                            onClick={() => !isProcessing && onFileClick(file)}
                                            style={{ cursor: isProcessing ? 'wait' : 'pointer' }}
                                        >
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
                                            <FileText size={40} className="file-icon" />
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
