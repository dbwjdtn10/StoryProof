import { Upload, FileText, X } from 'lucide-react';
import { useState, useRef } from 'react';
import { ThemeToggle } from './ThemeToggle';

interface UploadedFile {
    id: number;
    name: string;
}

interface FileUploadProps {
    onFileClick: (fileName: string) => void;
}

export function FileUpload({ onFileClick }: FileUploadProps) {
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

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

    const handleFiles = (files: FileList) => {
        const newFiles: UploadedFile[] = Array.from(files).map((file, index) => ({
            id: Date.now() + index,
            name: file.name,
        }));
        setUploadedFiles((prev) => [...prev, ...newFiles]);
    };

    const removeFile = (id: number) => {
        setUploadedFiles((prev) => prev.filter((file) => file.id !== id));
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
                                <p className="upload-text-sub">PDF, DOC, DOCX, TXT 파일 지원</p>
                            </label>
                        </div>
                    )}

                    {/* Uploaded Files Grid */}
                    {uploadedFiles.length > 0 && (
                        <div className="uploaded-files-section">
                            <h2 className="uploaded-files-title">업로드된 파일</h2>
                            <div className="uploaded-files-grid">
                                {uploadedFiles.map((file) => (
                                    <div
                                        key={file.id}
                                        className="uploaded-file-card"
                                        onClick={() => onFileClick(file.name)}
                                    >
                                        <button
                                            className="file-remove-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                removeFile(file.id);
                                            }}
                                        >
                                            <X size={16} />
                                        </button>
                                        <FileText size={40} className="file-icon" />
                                        <p className="file-name">{file.name}</p>
                                    </div>
                                ))}
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
