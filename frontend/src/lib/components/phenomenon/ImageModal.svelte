<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { fade, scale } from 'svelte/transition';
    import type { CauseImage } from '$lib/types/phenomenon';

    export let image: CauseImage;
    export let isOpen = false;

    const dispatch = createEventDispatcher<{
        close: void;
        updateCaption: { id: string; caption: string };
        delete: { id: string };
    }>();

    let editingCaption = false;
    let captionText = image.caption || '';

    function handleClose() {
        dispatch('close');
    }

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            handleClose();
        }
    }

    function startEditCaption() {
        captionText = image.caption || '';
        editingCaption = true;
    }

    function saveCaption() {
        dispatch('updateCaption', { id: image.id, caption: captionText });
        editingCaption = false;
    }

    function cancelEditCaption() {
        captionText = image.caption || '';
        editingCaption = false;
    }

    function handleCaptionKeyDown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveCaption();
        } else if (e.key === 'Escape') {
            cancelEditCaption();
        }
    }

    function handleDelete() {
        if (confirm('이 이미지를 삭제하시겠습니까?')) {
            dispatch('delete', { id: image.id });
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape' && !editingCaption) {
            handleClose();
        }
    }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
        on:click={handleBackdropClick}
        transition:fade={{ duration: 150 }}
    >
        <div
            class="relative bg-white rounded-lg shadow-2xl max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
            transition:scale={{ duration: 150, start: 0.95 }}
        >
            <!-- Header -->
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
                <h3 class="text-sm font-semibold text-gray-700">이미지 상세보기</h3>
                <div class="flex items-center gap-2">
                    <button
                        class="p-1.5 text-red-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        on:click={handleDelete}
                        title="삭제"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                    <button
                        class="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                        on:click={handleClose}
                        title="닫기"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Image -->
            <div class="flex-1 overflow-auto p-4 bg-gray-100 flex items-center justify-center">
                <img
                    src={image.data}
                    alt={image.caption || '첨부 이미지'}
                    class="max-w-full max-h-[60vh] object-contain rounded shadow-lg"
                />
            </div>

            <!-- Caption -->
            <div class="px-4 py-3 border-t border-gray-200 bg-white">
                {#if editingCaption}
                    <div class="flex flex-col gap-2">
                        <textarea
                            bind:value={captionText}
                            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="이미지에 대한 설명을 입력하세요..."
                            rows="2"
                            on:keydown={handleCaptionKeyDown}
                            autofocus
                        ></textarea>
                        <div class="flex justify-end gap-2">
                            <button
                                class="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 transition-colors"
                                on:click={cancelEditCaption}
                            >
                                취소
                            </button>
                            <button
                                class="px-3 py-1.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors font-medium"
                                on:click={saveCaption}
                            >
                                저장
                            </button>
                        </div>
                    </div>
                {:else}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div
                        class="flex items-start gap-2 cursor-pointer group"
                        on:click={startEditCaption}
                    >
                        <svg class="w-4 h-4 text-gray-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                        </svg>
                        {#if image.caption}
                            <p class="text-sm text-gray-700 flex-1 group-hover:text-blue-600 transition-colors">
                                {image.caption}
                            </p>
                        {:else}
                            <p class="text-sm text-gray-400 italic flex-1 group-hover:text-blue-500 transition-colors">
                                클릭하여 캡션 추가...
                            </p>
                        {/if}
                        <svg class="w-3.5 h-3.5 text-gray-300 group-hover:text-blue-500 transition-colors shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}
</script>
