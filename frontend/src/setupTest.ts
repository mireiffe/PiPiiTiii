import '@testing-library/svelte/vitest';

// Polyfill for Web Animations API (JSDOM doesn't support it)
if (typeof Element !== 'undefined' && !Element.prototype.animate) {
    Element.prototype.animate = function() {
        return {
            cancel: () => {},
            finish: () => {},
            pause: () => {},
            play: () => {},
            reverse: () => {},
            onfinish: null,
            oncancel: null,
            finished: Promise.resolve(),
            effect: null,
            currentTime: 0,
            playState: 'finished' as AnimationPlayState,
            playbackRate: 1,
            pending: false,
            id: '',
            timeline: null,
            startTime: 0,
            replaceState: 'active' as AnimationReplaceState,
            persist: () => {},
            commitStyles: () => {},
            addEventListener: () => {},
            removeEventListener: () => {},
            dispatchEvent: () => false,
            updatePlaybackRate: () => {},
        } as unknown as Animation;
    };
}

// Polyfill for ClipboardEvent (JSDOM doesn't support it)
if (typeof globalThis.ClipboardEvent === 'undefined') {
    (globalThis as any).ClipboardEvent = class ClipboardEvent extends Event {
        public clipboardData: DataTransfer | null;
        constructor(type: string, eventInitDict?: ClipboardEventInit) {
            super(type, eventInitDict);
            this.clipboardData = eventInitDict?.clipboardData || null;
        }
    };
}
