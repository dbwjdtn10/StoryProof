/**
 * Shared SSE (Server-Sent Events) stream parsing utility.
 *
 * Accumulates raw SSE data into a buffer, splits on double-newline boundaries,
 * and invokes `onMessage` for each successfully parsed JSON payload.
 *
 * @param buffer   The current incomplete buffer from previous reads.
 * @param newData  Newly decoded text from the stream.
 * @param onMessage  Callback invoked with each parsed JSON object.
 * @returns The remaining incomplete buffer to carry forward.
 */
export function parseSSEBuffer(
    buffer: string,
    newData: string,
    onMessage: (parsed: any) => void
): string {
    buffer += newData;
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') continue;
        try {
            const parsed = JSON.parse(data);
            onMessage(parsed);
        } catch (e) {
            console.warn('[SSE] parse error:', data);
        }
    }
    return buffer;
}
