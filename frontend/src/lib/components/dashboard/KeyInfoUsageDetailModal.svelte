<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import Modal from '$lib/components/ui/Modal.svelte';
    import { getAttachmentImageUrl, API_BASE_URL } from '$lib/api/project';
    import type {
        KeyInfoCategoryDefinition,
        KeyInfoItemDefinition,
        KeyInfoUsageDetail,
        KeyInfoCaptureValue,
    } from '$lib/types/keyInfo';

    export let category: KeyInfoCategoryDefinition;
    export let item: KeyInfoItemDefinition;
    export let details: KeyInfoUsageDetail[];

    const dispatch = createEventDispatcher<{ close: void }>();

    function handleClose() {
        dispatch('close');
    }

    function hasContent(detail: KeyInfoUsageDetail): boolean {
        const hasText = !!detail.textValue && detail.textValue.trim().length > 0;
        const hasCaptures = detail.captureValues && detail.captureValues.length > 0;
        const hasImages = detail.imageIds && detail.imageIds.length > 0;
        return hasText || hasCaptures || hasImages;
    }

    function getSlideThumbnailUrl(projectId: string, slideIndex: number): string {
        const paddedIndex = slideIndex.toString().padStart(3, '0');
        return `${API_BASE_URL}/api/results/${projectId}/thumbnails/slide_${paddedIndex}_thumb.png`;
    }
</script>

<Modal isOpen={true} size="full" on:close={handleClose}>
    <svelte:fragment slot="header">
        <div class="flex items-center gap-3">
            <div class="flex items-center gap-2">
                <span class="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                    {category.name}
                </span>
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">{item.title}</h2>
            <span class="text-sm text-blue-600 font-medium">{details.length}회 사용</span>
        </div>
    </svelte:fragment>

    <div class="space-y-4">
        {#if details.length === 0}
            <div class="text-center py-8 text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p class="text-sm">사용 내역이 없습니다</p>
            </div>
        {:else}
            {#each details as detail, index (detail.projectId)}
                <div class="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                    <!-- Project Header -->
                    <div class="px-4 py-3 bg-white border-b border-gray-100 flex items-center gap-2">
                        <svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                        <span class="font-medium text-gray-800 truncate" title={detail.projectName}>
                            {detail.projectName}
                        </span>
                    </div>

                    <!-- Content -->
                    <div class="p-4 space-y-3">
                        {#if !hasContent(detail)}
                            <p class="text-sm text-gray-400 italic">내용 없음</p>
                        {:else}
                            <!-- Text Value -->
                            {#if detail.textValue && detail.textValue.trim()}
                                <div class="flex items-start gap-2">
                                    <svg class="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <p class="text-sm text-gray-700 whitespace-pre-wrap flex-1">
                                        {detail.textValue}
                                    </p>
                                </div>
                            {/if}

                            <!-- Captures with cropped thumbnails -->
                            {#if detail.captureValues && detail.captureValues.length > 0}
                                <div class="flex items-start gap-2">
                                    <svg class="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    <div class="flex-1">
                                        <p class="text-xs text-gray-500 mb-2">
                                            슬라이드 캡처 ({detail.captureValues.length}개)
                                        </p>
                                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3">
                                            {#each detail.captureValues as capture (capture.id)}
                                                {@const scaleX = 100 / capture.width}
                                                {@const scaleY = 100 / capture.height}
                                                {@const scale = Math.min(scaleX, scaleY)}
                                                {@const translateX = -capture.x * scale}
                                                {@const translateY = -capture.y * scale}
                                                <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                                    <!-- Cropped capture region -->
                                                    <div class="relative aspect-video bg-gray-100 overflow-hidden">
                                                        <img
                                                            src={getSlideThumbnailUrl(detail.projectId, capture.slideIndex)}
                                                            alt="Slide {capture.slideIndex + 1} capture"
                                                            class="absolute origin-top-left"
                                                            style="transform: translate({translateX}%, {translateY}%) scale({scale}); width: 100%; height: auto;"
                                                        />
                                                    </div>
                                                    <!-- Capture info -->
                                                    <div class="p-2 text-xs">
                                                        <div class="flex items-center gap-1 text-gray-600">
                                                            <span class="font-medium">Slide {capture.slideIndex + 1}</span>
                                                            {#if capture.label}
                                                                <span class="text-gray-400">- {capture.label}</span>
                                                            {/if}
                                                        </div>
                                                        {#if capture.caption}
                                                            <p class="text-gray-500 mt-1 italic truncate" title={capture.caption}>
                                                                "{capture.caption}"
                                                            </p>
                                                        {/if}
                                                    </div>
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                </div>
                            {/if}

                            <!-- Images -->
                            {#if detail.imageIds && detail.imageIds.length > 0}
                                <div class="flex items-start gap-2">
                                    <svg class="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    <div class="flex-1">
                                        <p class="text-xs text-gray-500 mb-2">
                                            이미지 ({detail.imageIds.length}개)
                                        </p>
                                        <div class="grid grid-cols-2 lg:grid-cols-3 gap-3">
                                            {#each detail.imageIds as imageId (imageId)}
                                                <div class="bg-white border border-gray-200 rounded-lg overflow-hidden">
                                                    <div class="aspect-video bg-gray-100">
                                                        <img
                                                            src={getAttachmentImageUrl(imageId)}
                                                            alt="첨부 파일"
                                                            class="w-full h-full object-contain"
                                                        />
                                                    </div>
                                                    {#if detail.imageCaptions && detail.imageCaptions[imageId]}
                                                        <div class="p-2 text-xs text-gray-600 truncate" title={detail.imageCaptions[imageId]}>
                                                            {detail.imageCaptions[imageId]}
                                                        </div>
                                                    {/if}
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                </div>
                            {/if}
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>

    <svelte:fragment slot="footer">
        <div class="flex justify-end">
            <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                on:click={handleClose}
            >
                닫기
            </button>
        </div>
    </svelte:fragment>
</Modal>
