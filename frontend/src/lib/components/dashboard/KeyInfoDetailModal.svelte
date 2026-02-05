<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import Modal from '$lib/components/ui/Modal.svelte';
    import { getAttachmentImageUrl } from '$lib/api/project';
    import { BASE_URL } from '$lib/api/client';
    import type { KeyInfoCaptureValue } from '$lib/types/keyInfo';

    const dispatch = createEventDispatcher();

    // Type for modal title config
    type ModalTitleConfigItem = string | { key: string; prefix?: string; suffix?: string };

    export let isOpen = false;
    export let itemTitle = '';
    export let itemDescription = '';
    export let usageCount = 0;
    export let modalTitleConfig: ModalTitleConfigItem[] = ["title"];

    interface ProjectAttributes {
        [key: string]: string | number | boolean | null | undefined;
    }

    export let instances: Array<{
        projectId: string;
        projectTitle: string;
        projectAttributes?: ProjectAttributes;
        textValue?: string;
        captureValues?: KeyInfoCaptureValue[];
        imageIds?: string[];
        imageCaptions?: Record<string, string>;
        // deprecated fields for backwards compatibility
        captureValue?: KeyInfoCaptureValue;
        imageId?: string;
        imageCaption?: string;
    }> = [];

    // Generate display title from config and project attributes
    function getDisplayTitle(instance: typeof instances[0]): string {
        const parts: string[] = [];
        const attrs = instance.projectAttributes || {};

        for (const configItem of modalTitleConfig) {
            let key: string;
            let prefix = '';
            let suffix = '';

            if (typeof configItem === 'string') {
                key = configItem;
            } else {
                key = configItem.key;
                prefix = configItem.prefix || '';
                suffix = configItem.suffix || '';
            }

            // Check in projectAttributes first, then fallback to instance properties
            let value: string | undefined;
            if (key === 'title') {
                value = attrs.title as string || instance.projectTitle;
            } else if (key in attrs && attrs[key] != null) {
                value = String(attrs[key]);
            }

            if (value) {
                parts.push(`${prefix}${value}${suffix}`);
            }
        }

        return parts.join(' ') || instance.projectTitle || 'Untitled';
    }

    // Expanded image state
    let expandedImageUrl: string | null = null;

    function getCaptures(instance: typeof instances[0]): KeyInfoCaptureValue[] {
        return instance.captureValues || (instance.captureValue ? [instance.captureValue] : []);
    }

    function getImageIds(instance: typeof instances[0]): string[] {
        return instance.imageIds || (instance.imageId ? [instance.imageId] : []);
    }

    function getImageCaption(instance: typeof instances[0], imageId: string): string | undefined {
        if (instance.imageCaptions && instance.imageCaptions[imageId]) {
            return instance.imageCaptions[imageId];
        }
        if (instance.imageId === imageId && instance.imageCaption) {
            return instance.imageCaption;
        }
        return undefined;
    }

    // Generate slide thumbnail URL from project results
    function getSlideImageUrl(projectId: string, slideIndex: number): string {
        return `${BASE_URL}/results/${projectId}/images/slide_${slideIndex + 1}.png`;
    }

    // Get thumbnail URL for capture
    function getCaptureThumbUrl(projectId: string, slideIndex: number): string {
        return `/api/results/${projectId}/thumbnails/slide_${String(slideIndex + 1).padStart(3, '0')}_thumb.png`;
    }

    // Calculate thumbnail cropping styles for capture preview (snippet mode)
    // Default slide dimensions: 960x540
    const DEFAULT_SLIDE_WIDTH = 960;
    const DEFAULT_SLIDE_HEIGHT = 540;

    function getCaptureThumbStyle(
        projectId: string,
        capture: { x: number; y: number; width: number; height: number; slideIndex: number },
        containerW: number = 96,
        containerH: number = 68
    ): string {
        const thumbUrl = getCaptureThumbUrl(projectId, capture.slideIndex);

        // Guard against zero-size captures
        if (capture.width <= 0 || capture.height <= 0) {
            return `background-image: url('${thumbUrl}'); background-size: cover; background-position: center;`;
        }

        // Thumbnail is rendered at max 1920px width
        const thumbMaxWidth = 1920;
        const thumbScale = thumbMaxWidth / DEFAULT_SLIDE_WIDTH;
        const thumbHeight = DEFAULT_SLIDE_HEIGHT * thumbScale;

        // Scale capture coordinates to thumbnail space
        const thumbX = capture.x * thumbScale;
        const thumbY = capture.y * thumbScale;
        const thumbW = capture.width * thumbScale;
        const thumbH = capture.height * thumbScale;

        // Calculate scale to fit capture region into container (use Math.min for contain behavior)
        const displayScale = Math.min(containerW / thumbW, containerH / thumbH);

        // Calculate background size
        const bgWidth = thumbMaxWidth * displayScale;
        const bgHeight = thumbHeight * displayScale;

        // Calculate background position (negative values to offset)
        const offsetX = -thumbX * displayScale + (containerW - thumbW * displayScale) / 2;
        const offsetY = -thumbY * displayScale + (containerH - thumbH * displayScale) / 2;

        return `background-image: url('${thumbUrl}'); background-size: ${bgWidth}px ${bgHeight}px; background-position: ${offsetX}px ${offsetY}px;`;
    }

    function handleClose() {
        expandedImageUrl = null;
        dispatch('close');
    }
</script>

<Modal {isOpen} title="" size="2xl" on:close={handleClose}>
    <svelte:fragment slot="header">
        <div class="flex items-center gap-3">
            <div class="p-2 bg-blue-100 rounded-lg">
                <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
            </div>
            <div>
                <h2 class="text-lg font-bold text-gray-900">{itemTitle}</h2>
                {#if itemDescription}
                    <p class="text-sm text-gray-500">{itemDescription}</p>
                {/if}
            </div>
            <span class="ml-auto mr-8 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                {usageCount}개 프로젝트에서 사용
            </span>
        </div>
    </svelte:fragment>

    <div class="space-y-4 min-h-[400px]">
        {#if instances.length === 0}
            <div class="flex items-center justify-center h-48 text-gray-400">
                사용된 프로젝트가 없습니다
            </div>
        {:else}
            {#each instances as instance, i}
                {@const captures = getCaptures(instance)}
                {@const images = getImageIds(instance)}
                <div class="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-sm transition-shadow">
                    <!-- Project Title -->
                    <div class="flex items-center gap-2 mb-3">
                        <div class="p-1.5 bg-gray-100 rounded">
                            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <span class="font-medium text-gray-900">{getDisplayTitle(instance)}</span>
                        <a
                            href="/viewer/{instance.projectId}"
                            class="ml-auto text-xs text-blue-600 hover:text-blue-800 hover:underline"
                            target="_blank"
                        >
                            열기
                        </a>
                    </div>

                    <!-- Text Value -->
                    {#if instance.textValue}
                        <div class="mb-3">
                            <div class="text-xs text-gray-500 mb-1">텍스트</div>
                            <div class="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap">
                                {instance.textValue}
                            </div>
                        </div>
                    {/if}

                    <!-- Captures (snippet mode - shows cropped region) -->
                    {#if captures.length > 0}
                        <div class="mb-3">
                            <div class="text-xs text-gray-500 mb-2">캡처 ({captures.length}개)</div>
                            <div class="flex flex-wrap gap-2">
                                {#each captures as capture}
                                    {@const slideImageUrl = getSlideImageUrl(instance.projectId, capture.slideIndex)}
                                    <div class="relative group">
                                        <div
                                            class="w-24 h-[68px] bg-gray-200 rounded border border-gray-200 overflow-hidden cursor-pointer hover:border-blue-400 transition-colors"
                                            style={getCaptureThumbStyle(instance.projectId, capture, 96, 68)}
                                            on:click={() => expandedImageUrl = slideImageUrl}
                                            on:keydown={(e) => {
                                                if (e.key === 'Enter') expandedImageUrl = slideImageUrl;
                                            }}
                                            role="button"
                                            tabindex="0"
                                            title="클릭하여 전체 슬라이드 보기"
                                        >
                                        </div>
                                        <span class="absolute -top-1 -right-1 bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded-full font-medium">
                                            S{capture.slideIndex + 1}
                                        </span>
                                        {#if capture.caption}
                                            <div class="mt-1 text-[10px] text-gray-500 max-w-24 truncate" title={capture.caption}>
                                                {capture.caption}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Images -->
                    {#if images.length > 0}
                        <div>
                            <div class="text-xs text-gray-500 mb-2">이미지 ({images.length}개)</div>
                            <div class="flex flex-wrap gap-2">
                                {#each images as imageId}
                                    {@const imageUrl = getAttachmentImageUrl(imageId)}
                                    {@const caption = getImageCaption(instance, imageId)}
                                    <div class="relative group">
                                        <div
                                            class="w-24 h-18 bg-gray-100 rounded border border-gray-200 overflow-hidden cursor-pointer hover:border-blue-400 transition-colors"
                                            on:click={() => expandedImageUrl = imageUrl}
                                            on:keydown={(e) => {
                                                if (e.key === 'Enter') expandedImageUrl = imageUrl;
                                            }}
                                            role="button"
                                            tabindex="0"
                                        >
                                            <img
                                                src={imageUrl}
                                                alt="첨부 이미지"
                                                class="w-full h-full object-cover"
                                            />
                                        </div>
                                        {#if caption}
                                            <div class="mt-1 text-[10px] text-gray-500 max-w-24 truncate" title={caption}>
                                                {caption}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- No content message -->
                    {#if !instance.textValue && captures.length === 0 && images.length === 0}
                        <div class="text-sm text-gray-400 italic">내용 없음</div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</Modal>

<!-- Expanded Image Modal -->
{#if expandedImageUrl}
    <div
        class="fixed inset-0 bg-black/80 z-[60] flex items-center justify-center p-8"
        on:click={() => expandedImageUrl = null}
        on:keydown={(e) => {
            if (e.key === 'Escape') expandedImageUrl = null;
        }}
        role="button"
        tabindex="0"
    >
        <img
            src={expandedImageUrl}
            alt="확대 이미지"
            class="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
            on:click|stopPropagation
        />
        <button
            class="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
            on:click={() => expandedImageUrl = null}
        >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    </div>
{/if}
