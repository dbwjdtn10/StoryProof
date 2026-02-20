import { Component, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false };

    static getDerivedStateFromError(): State {
        return { hasError: true };
    }

    componentDidCatch(error: Error) {
        console.error('[ErrorBoundary]', error);
    }

    render() {
        if (this.state.hasError) {
            return this.props.fallback ?? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: '12px' }}>
                    <p style={{ color: 'var(--muted-foreground)', fontSize: '14px' }}>문제가 발생했습니다.</p>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--background)', cursor: 'pointer' }}
                    >
                        다시 시도
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}
