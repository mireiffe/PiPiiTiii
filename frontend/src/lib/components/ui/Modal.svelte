<script lang="ts">
    import { createEventDispatcher, onMount, onDestroy } from 'svelte';
    import { fade, scale } from 'svelte/transition';
    import { browser } from '$app/environment';

    export let isOpen: boolean = false;
    export let title: string = '';
    export let size: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full' = 'md';
    export let closeOnBackdrop: boolean = true;
    export let closeOnEscape: boolean = true;
    export let showCloseButton: boolean = true;

    const dispatch = createEventDispatcher<{ close: void }>();

    const sizes: Record<typeof size, string> = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-lg',
        xl: 'max-w-xl',
        '2xl': 'max-w-6xl',
        full: 'max-w-4xl',
    };

    function handleClose() {
        dispatch('close');
    }

    function handleBackdropClick(event: MouseEvent) {
        if (closeOnBackdrop && event.target === event.currentTarget) {
            handleClose();
        }
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (closeOnEscape && event.key === 'Escape' && isOpen) {
            event.preventDefault();
            handleClose();
        }
    }

    onMount(() => {
        if (closeOnEscape) {
            window.addEventListener('keydown', handleKeyDown);
        }
    });

    onDestroy(() => {
        if (browser) {
            window.removeEventListener('keydown', handleKeyDown);
        }
    });

    // Prevent body scroll when modal is open
    $: if (browser) {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
</script>

{#if isOpen}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        transition:fade={{ duration: 150 }}
        on:click={handleBackdropClick}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
    >
        <!-- Modal Content -->
        <div
            class="bg-white rounded-xl shadow-2xl w-full {sizes[size]} max-h-[90vh] flex flex-col"
            transition:scale={{ duration: 150, start: 0.95 }}
            on:click|stopPropagation
        >
            <!-- Header -->
            {#if title || showCloseButton || $$slots.header}
                <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                    {#if $$slots.header}
                        <slot name="header" />
                    {:else if title}
                        <h2 id="modal-title" class="text-lg font-semibold text-gray-900">
                            {title}
                        </h2>
                    {:else}
                        <div></div>
                    {/if}

                    {#if showCloseButton}
                        <button
                            type="button"
                            class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                            on:click={handleClose}
                            aria-label="닫기"
                        >
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    {/if}
                </div>
            {/if}

            <!-- Body -->
            <div class="flex-1 overflow-y-auto p-4">
                <slot />
            </div>

            <!-- Footer -->
            {#if $$slots.footer}
                <div class="px-4 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
                    <slot name="footer" />
                </div>
            {/if}
        </div>
    </div>
{/if}
