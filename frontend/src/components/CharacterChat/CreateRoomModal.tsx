import React, { useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import { generatePersona, createRoom, CharacterChatRoom } from '../../api/characterChat';

interface CreateRoomModalProps {
    novelId: number;
    onClose: () => void;
    onCreated?: (room: CharacterChatRoom) => void;
    onUpdated?: (room: CharacterChatRoom) => void;
    initialData?: CharacterChatRoom;
    mode?: 'create' | 'edit';
}

export function CreateRoomModal({ novelId, onClose, onCreated, onUpdated, initialData, mode = 'create' }: CreateRoomModalProps) {
    const [characterName, setCharacterName] = useState(initialData?.character_name || '');
    const [personaPrompt, setPersonaPrompt] = useState(initialData?.persona_prompt || '');
    const [step, setStep] = useState<'input' | 'review'>(mode === 'edit' ? 'review' : 'input');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleGenerate = async () => {
        if (!characterName.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const result = await generatePersona(novelId, characterName);
            setPersonaPrompt(result.persona_prompt);
            setStep('review');
        } catch (err: any) {
            setError(err.message || "페르소나 생성 실패");
        } finally {
            setLoading(false);
        }
    };

    const handleCreateOrUpdate = async () => {
        if (!personaPrompt.trim()) return;
        setLoading(true);
        try {
            if (mode === 'create') {
                const room = await createRoom(novelId, characterName, personaPrompt);
                onCreated?.(room);
            } else {
                // Update mode
                if (initialData?.id) {
                    const { updateRoom } = await import('../../api/characterChat'); // Dynamic import to avoid cycles if any, or just import at top
                    const room = await updateRoom(initialData.id, personaPrompt);
                    onUpdated?.(room);
                }
            }
        } catch (err: any) {
            setError(err.message || (mode === 'create' ? "대화방 생성 실패" : "대화방 수정 실패"));
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'white',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            padding: '20px'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                <h3 style={{ margin: 0 }}>{mode === 'create' ? '새 대화 시작' : '페르소나 수정'}</h3>
                <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                    <X size={20} />
                </button>
            </div>

            {error && (
                <div style={{
                    backgroundColor: '#ffebee',
                    color: '#c62828',
                    padding: '10px',
                    borderRadius: '8px',
                    marginBottom: '10px',
                    fontSize: '0.9rem'
                }}>
                    {error}
                </div>
            )}

            {step === 'input' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>캐릭터 이름</label>
                        <input
                            type="text"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="예: 셜록 홈즈"
                            style={{
                                width: '100%', padding: '12px', borderRadius: '8px',
                                border: '1px solid #ddd', fontSize: '1rem'
                            }}
                        />
                        <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '4px' }}>
                            * 분석된 데이터에 있는 캐릭터 이름을 입력하세요.
                        </p>
                    </div>

                    <button
                        onClick={handleGenerate}
                        disabled={loading || !characterName}
                        style={{
                            backgroundColor: '#fee500',
                            color: '#3b1e1e',
                            border: 'none',
                            padding: '14px',
                            borderRadius: '8px',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? '생성 중...' : (
                            <>
                                <Sparkles size={18} />
                                페르소나 생성
                            </>
                        )}
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <label style={{ fontWeight: 'bold' }}>페르소나 프롬프트 (수정 가능)</label>
                            <button
                                onClick={handleGenerate}
                                title="AI 자동 업데이트 (현재 분석 데이터 기반)"
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: '#666', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem'
                                }}
                            >
                                <Sparkles size={14} />
                                AI 자동 갱신
                            </button>
                        </div>
                        <textarea
                            value={personaPrompt}
                            onChange={(e) => setPersonaPrompt(e.target.value)}
                            style={{
                                flex: 1,
                                width: '100%',
                                padding: '12px',
                                borderRadius: '8px',
                                border: '1px solid #ddd',
                                fontSize: '0.9rem',
                                resize: 'none',
                                fontFamily: 'monospace'
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                        {mode !== 'edit' && (
                            <button
                                onClick={() => setStep('input')}
                                style={{
                                    flex: 1,
                                    backgroundColor: '#f0f0f0',
                                    color: '#333',
                                    border: 'none',
                                    padding: '14px',
                                    borderRadius: '8px',
                                    fontWeight: 'bold',
                                    cursor: 'pointer'
                                }}
                            >
                                뒤로
                            </button>
                        )}
                        <button
                            onClick={handleCreateOrUpdate}
                            disabled={loading}
                            style={{
                                flex: 2,
                                backgroundColor: '#fee500',
                                color: '#3b1e1e',
                                border: 'none',
                                padding: '14px',
                                borderRadius: '8px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                opacity: loading ? 0.7 : 1
                            }}
                        >
                            {loading ? (mode === 'create' ? '생성 중...' : '저장 중...') : (mode === 'create' ? '대화 시작' : '수정 저장')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
