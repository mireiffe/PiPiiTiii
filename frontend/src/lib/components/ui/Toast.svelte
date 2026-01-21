<script lang="ts">
    import { fly, fade } from 'svelte/transition';
    import { toastStore, type ToastMessage } from '$lib/stores/toast';

    let toasts: ToastMessage[] = [];
    toastStore.subscribe(value => toasts = value);

    function getTypeStyles(type: ToastMessage['type']): string {
        switch (type) {
            case 'error':
                return 'bg-red-500 text-white border-red-600';
            case 'warning':
                return 'bg-amber-500 text-white border-amber-600';
            case 'success':
                return 'bg-green-500 text-white border-green-600';
            default:
                return 'bg-blue-500 text-white border-blue-600';
        }
    }

    function getIcon(type: ToastMessage['type']): string {
        switch (type) {
            case 'error':
                return '!';
            case 'warning':
                return '!';
            case 'success':
                return '✓';
            default:
                return 'i';
        }
    }
</script>

<div class="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
    {#each toasts as toast (toast.id)}
        <div
            class="pointer-events-auto px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 border {getTypeStyles(toast.type)} max-w-sm"
            in:fly={{ x: 100, duration: 200 }}
            out:fade={{ duration: 150 }}
        >
            <span class="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold flex-shrink-0">
                {getIcon(toast.type)}
            </span>
            <span class="flex-1">{toast.message}</span>
            <button
                class="ml-2 opacity-70 hover:opacity-100 transition-opacity flex-shrink-0"
                on:click={() => toastStore.dismiss(toast.id)}
                aria-label="닫기"
            >
                ×
            </button>
        </div>
    {/each}
</div>
