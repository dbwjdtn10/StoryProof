import React, { useState } from 'react';
import {
    RotateCcw,
    RotateCw,
    ChevronDown,
    AlignLeft,
    AlignCenter,
    AlignRight,
    AlignJustify,
    Bold,
    Italic,
    Strikethrough,
    Underline,
    List,
    ListOrdered,
    Languages,
    Type,
    Highlighter,
    Search,
    FileText,
    Table,
    Settings2,
    Baseline,
    ChevronUp
} from 'lucide-react';
import { Separator } from './ui/separator';
import { Menu, MenuItem, Popover, IconButton, Tooltip } from '@mui/material';

interface WritingToolbarProps {
    onExecute: (command: string, value?: string) => void;
}

export function WritingToolbar({ onExecute }: WritingToolbarProps) {
    // 1. 상태 관리 (폰트, 크기, 목표 설정 팝업용)
    const [fontAnchor, setFontAnchor] = useState<null | HTMLElement>(null);
    const [sizeAnchor, setSizeAnchor] = useState<null | HTMLElement>(null);
    const [spacingAnchor, setSpacingAnchor] = useState<null | HTMLElement>(null);
    const [goalAnchor, setGoalAnchor] = useState<null | HTMLElement>(null);

    // Placeholder state for demonstration
    const [fontFamily, setFontFamily] = useState("Inter");
    const [fontSize, setFontSize] = useState("12 pt");
    const [lineSpacing, setLineSpacing] = useState("1.5");

    const commonMenuProps = {
        PaperProps: {
            sx: {
                bgcolor: 'white',
                color: '#1a1a1a',
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                '& .MuiMenuItem-root:hover': {
                    bgcolor: '#f3f4f6'
                }
            }
        }
    };

    return (
        <div className="flex items-center w-full px-4 py-1 bg-white text-[#4b5563] border-b border-gray-200 select-none sticky top-[65px] z-[50] h-11">
            <div className="flex items-center gap-1 w-full max-w-7xl mx-auto">
                {/* 1. History Controls */}
                <div className="flex items-center">
                    <button
                        onClick={() => onExecute('undo')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="실행 취소"
                    >
                        <RotateCcw size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('redo')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="다시 실행"
                    >
                        <RotateCw size={16} />
                    </button>
                </div>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 2. Font Family */}
                <button
                    onClick={(e) => setFontAnchor(e.currentTarget)}
                    className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-100 rounded text-sm font-medium transition-colors min-w-[100px] justify-between"
                >
                    <span className="text-[#3b82f6]">{fontFamily}</span>
                    <div className="flex flex-col scale-75 opacity-70">
                        <ChevronUp size={10} className="-mb-1" />
                        <ChevronDown size={10} />
                    </div>
                </button>
                <Menu
                    anchorEl={fontAnchor}
                    open={Boolean(fontAnchor)}
                    onClose={() => setFontAnchor(null)}
                    {...commonMenuProps}
                >
                    <MenuItem onClick={() => { onExecute('fontName', 'Inter'); setFontFamily("Inter"); setFontAnchor(null); }}>Inter</MenuItem>
                    <MenuItem onClick={() => { onExecute('fontName', '나눔고딕'); setFontFamily("나눔고딕"); setFontAnchor(null); }}>나눔고딕</MenuItem>
                    <MenuItem onClick={() => { onExecute('fontName', 'Pretendard'); setFontFamily("Pretendard"); setFontAnchor(null); }}>Pretendard</MenuItem>
                </Menu>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 3. Font Size */}
                <button
                    onClick={(e) => setSizeAnchor(e.currentTarget)}
                    className="flex items-center gap-1 px-2 py-1.5 hover:bg-gray-100 rounded text-sm font-medium transition-colors"
                >
                    <span className="min-w-[40px] text-left">{fontSize}</span>
                    <ChevronDown size={14} className="opacity-70" />
                </button>
                <Menu
                    anchorEl={sizeAnchor}
                    open={Boolean(sizeAnchor)}
                    onClose={() => setSizeAnchor(null)}
                    {...commonMenuProps}
                >
                    <MenuItem onClick={() => { onExecute('fontSize', '3'); setFontSize("10 pt"); setSizeAnchor(null); }}>10 pt</MenuItem>
                    <MenuItem onClick={() => { onExecute('fontSize', '4'); setFontSize("12 pt"); setSizeAnchor(null); }}>12 pt</MenuItem>
                    <MenuItem onClick={() => { onExecute('fontSize', '5'); setFontSize("14 pt"); setSizeAnchor(null); }}>14 pt</MenuItem>
                </Menu>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 4. Line Spacing */}
                <button
                    onClick={(e) => setSpacingAnchor(e.currentTarget)}
                    className="flex items-center gap-1 px-2 py-1.5 hover:bg-gray-100 rounded text-sm font-medium transition-colors"
                >
                    <div className="flex items-center gap-1.5">
                        <div className="flex flex-col gap-[2px] opacity-70">
                            <div className="w-3 h-[1.5px] bg-current"></div>
                            <div className="w-3 h-[1.5px] bg-current"></div>
                            <div className="w-3 h-[1.5px] bg-current"></div>
                        </div>
                        <span>{lineSpacing}</span>
                    </div>
                    <div className="flex flex-col scale-75 opacity-70">
                        <ChevronUp size={10} className="-mb-1" />
                        <ChevronDown size={10} />
                    </div>
                </button>
                <Menu
                    anchorEl={spacingAnchor}
                    open={Boolean(spacingAnchor)}
                    onClose={() => setSpacingAnchor(null)}
                    {...commonMenuProps}
                >
                    <MenuItem onClick={() => { setLineSpacing("1.0"); setSpacingAnchor(null); }}>1.0</MenuItem>
                    <MenuItem onClick={() => { setLineSpacing("1.5"); setSpacingAnchor(null); }}>1.5</MenuItem>
                    <MenuItem onClick={() => { setLineSpacing("2.0"); setSpacingAnchor(null); }}>2.0</MenuItem>
                </Menu>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 5. Alignment Controls */}
                <div className="flex bg-gray-100/50 rounded-md p-0.5">
                    <button
                        onClick={() => onExecute('justifyLeft')}
                        className="p-1.5 bg-white shadow-sm rounded text-[#3b82f6]"
                        title="왼쪽 맞춤"
                    >
                        <AlignLeft size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('justifyCenter')}
                        className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                        title="가운데 맞춤"
                    >
                        <AlignCenter size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('justifyRight')}
                        className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                        title="오른쪽 맞춤"
                    >
                        <AlignRight size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('justifyFull')}
                        className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                        title="양쪽 맞춤"
                    >
                        <AlignJustify size={16} />
                    </button>
                </div>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 6. Formatting Controls */}
                <div className="flex items-center">
                    <button
                        onClick={() => onExecute('bold')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="굵게"
                    >
                        <Bold size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('italic')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="기울임"
                    >
                        <Italic size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('strikeThrough')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="취소선"
                    >
                        <Strikethrough size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('underline')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="밑줄"
                    >
                        <Underline size={16} />
                    </button>
                </div>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 7. List Controls */}
                <div className="flex items-center">
                    <button
                        onClick={() => onExecute('insertUnorderedList')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="글머리 기호"
                    >
                        <List size={16} />
                    </button>
                    <button
                        onClick={() => onExecute('insertOrderedList')}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="번호 매기기"
                    >
                        <ListOrdered size={16} />
                    </button>
                </div>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 8. Extra Tools */}
                <div className="flex items-center">
                    <Tooltip title="언어 설정"><IconButton size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><Languages size={16} /></IconButton></Tooltip>
                    <Tooltip title="글자 색상"><IconButton onClick={() => onExecute('foreColor', 'red')} size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><Baseline size={16} /></IconButton></Tooltip>
                    <Tooltip title="형광펜"><IconButton onClick={() => onExecute('hiliteColor', 'yellow')} size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><Highlighter size={16} /></IconButton></Tooltip>
                    <Tooltip title="찾기"><IconButton size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><Search size={16} /></IconButton></Tooltip>
                    <Tooltip title="문서 정보"><IconButton size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><FileText size={16} /></IconButton></Tooltip>
                    <Tooltip title="표 삽입"><IconButton size="small" sx={{ color: 'inherit', p: 1, '&:hover': { bgcolor: '#f3f4f6' } }}><Table size={16} /></IconButton></Tooltip>
                </div>

                <div className="w-[1px] h-6 bg-gray-200 mx-1" />

                {/* 9. Word Count & Goals (Far Right) */}
                <div className="flex-1" />

                <div className="flex items-center gap-1">
                    <button
                        onClick={(e) => setGoalAnchor(e.currentTarget)}
                        className="flex items-center gap-1.5 px-3 py-1.5 hover:bg-gray-100 rounded text-sm font-medium transition-colors"
                    >
                        <span>0자</span>
                        <ChevronDown size={14} className="opacity-70" />
                    </button>
                    <Popover
                        open={Boolean(goalAnchor)}
                        anchorEl={goalAnchor}
                        onClose={() => setGoalAnchor(null)}
                        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
                        PaperProps={{
                            sx: {
                                bgcolor: 'white',
                                border: '1px solid #e5e7eb',
                                color: '#1a1a1a',
                                width: 280,
                                p: 2,
                                mt: 1,
                                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                            }
                        }}
                    >
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-sm font-bold">목표 상세</span>
                                <span className="text-xs text-gray-500">0 / 1,000자</span>
                            </div>
                            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 w-[0%]"></div>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between items-center bg-gray-50 p-2 rounded text-sm border border-gray-100">
                                    <span>일일 목표</span>
                                    <input type="number" className="bg-transparent w-20 text-right outline-none text-blue-600 font-medium" placeholder="1000" />
                                </div>
                                <div className="flex justify-between items-center bg-gray-50 p-2 rounded text-sm border border-gray-100">
                                    <span>주간 목표</span>
                                    <input type="number" className="bg-transparent w-20 text-right outline-none text-blue-600 font-medium" placeholder="7000" />
                                </div>
                            </div>
                        </div>
                    </Popover>

                    <button
                        onClick={() => alert("환경설정 사이드바 열림")}
                        className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                        title="설정"
                    >
                        <Settings2 size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
}
