import { useEffect } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Underline } from '@tiptap/extension-underline';
import { Color } from '@tiptap/extension-color';
import { TextStyle } from '@tiptap/extension-text-style';
import { TextAlign } from '@tiptap/extension-text-align';
import { Highlight } from '@tiptap/extension-highlight';
import { Heading } from '@tiptap/extension-heading';
import { FontFamily } from '@tiptap/extension-font-family';
import { TaskList } from '@tiptap/extension-task-list';
import { TaskItem } from '@tiptap/extension-task-item';
import { Image } from '@tiptap/extension-image';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableHeader } from '@tiptap/extension-table-header';
import { TableCell } from '@tiptap/extension-table-cell';
import { Extension } from '@tiptap/core';
import { Placeholder } from '@tiptap/extension-placeholder';

// Custom Font Size Extension
const FontSize = Extension.create({
    name: 'fontSize',
    addOptions() {
        return {
            types: ['textStyle'],
        };
    },
    addGlobalAttributes() {
        return [
            {
                types: this.options.types,
                attributes: {
                    fontSize: {
                        default: null,
                        parseHTML: element => element.style.fontSize.replace(/['"]+/g, ''),
                        renderHTML: attributes => {
                            if (!attributes.fontSize) {
                                return {};
                            }
                            return {
                                style: `font-size: ${attributes.fontSize}`,
                            };
                        },
                    },
                },
            },
        ];
    },
    addCommands() {
        return {
            setFontSize: (fontSize: string) => ({ chain }: any) => {
                return chain()
                    .setMark('textStyle', { fontSize })
                    .run();
            },
            unsetFontSize: () => ({ chain }: any) => {
                return chain()
                    .setMark('textStyle', { fontSize: null })
                    .removeEmptyTextStyle()
                    .run();
            },
        } as any;
    },
});

// Custom Line Height Extension
const LineHeight = Extension.create({
    name: 'lineHeight',
    addOptions() {
        return {
            types: ['paragraph', 'heading'],
            defaultLineHeight: 'normal',
        };
    },
    addGlobalAttributes() {
        return [
            {
                types: this.options.types,
                attributes: {
                    lineHeight: {
                        default: this.options.defaultLineHeight,
                        parseHTML: element => element.style.lineHeight || this.options.defaultLineHeight,
                        renderHTML: attributes => {
                            if (attributes.lineHeight === this.options.defaultLineHeight) {
                                return {};
                            }
                            return {
                                style: `line-height: ${attributes.lineHeight}`,
                            };
                        },
                    },
                },
            },
        ];
    },
    addCommands() {
        return {
            setLineHeight: (lineHeight: string) => ({ commands }: any) => {
                return this.options.types.every((type: string) => commands.updateAttributes(type, { lineHeight }));
            },
            unsetLineHeight: () => ({ commands }: any) => {
                return this.options.types.every((type: string) => commands.resetAttributes(type, 'lineHeight'));
            },
        } as any;
    },
});

interface NovelEditorProps {
    content: string;
    onUpdate: (html: string) => void;
    onFocus: (editor: Editor) => void;
    onCreated?: (editor: Editor) => void;
    editable: boolean;
    className?: string;
    placeholder?: string;
    style?: React.CSSProperties;
}

export const NovelEditor = ({ content, onUpdate, onFocus, onCreated, editable, className, placeholder, style }: NovelEditorProps) => {
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                heading: false,
            }),
            Heading.configure({
                levels: [1, 2, 3, 4],
            }),
            Underline,
            TextStyle,
            FontFamily,
            FontSize,
            LineHeight,
            Color,
            TextAlign.configure({
                types: ['heading', 'paragraph'],
            }),
            Highlight.configure({
                multicolor: true,
            }),
            TaskList,
            TaskItem.configure({
                nested: true,
            }),
            Image.configure({
                inline: true,
                allowBase64: true,
            }),
            Table.configure({
                resizable: true,
            }),
            TableRow,
            TableHeader,
            TableCell,
            Placeholder.configure({
                placeholder: placeholder || '내용을 입력하세요...',
            }),
        ],
        content: content,
        editable: editable,
        onUpdate: ({ editor }) => {
            onUpdate(editor.getHTML());
        },
        onFocus: ({ editor }) => {
            onFocus(editor);
        },
        onCreate: ({ editor }) => {
            if (onCreated) onCreated(editor);
        },
    });

    // Update content if it changes externally (e.g. from API)
    useEffect(() => {
        if (!editor) return;

        // Only update if content is different AND the editor is not focused
        // This prevents cursor jumps and history loss while typing
        const isSame = editor.getHTML() === content;
        if (!isSame && !editor.isFocused) {
            editor.commands.setContent(content, { emitUpdate: false });
        }
    }, [content, editor]);


    // Update editable state
    useEffect(() => {
        if (editor) {
            editor.setEditable(editable);
        }
    }, [editable, editor]);

    return (
        <EditorContent
            editor={editor}
            className={className}
            style={style}
            onMouseUp={() => {
                // Optional: handle selection for AI dictionary if needed
            }}
        />
    );
};
