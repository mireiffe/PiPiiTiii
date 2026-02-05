<script lang="ts">
    import Modal from '$lib/components/ui/Modal.svelte';
    import { getAttachmentImageUrl } from '$lib/api/project';
    import type { KeyInfoCaptureValue } from '$lib/types/keyInfo';

    export let isOpen = false;
    export let itemTitle = '';
    export let itemDescription = '';
    export let usageCount = 0;
    export let instances: Array<{
        projectId: string;
        projectTitle: string;
        textValue?: string;
        captureValues?: KeyInfoCaptureValue[];
        imageIds?: string[];
        imageCaptions?: Record<string, string>;
        // deprecated fields for backwards compatibility
        captureValue?: KeyInfoCaptureValue;
        imageId?: string;
        imageCaption?: string;
    }> = [];
    export let slideThumbnails: Record<string, Record<number, string>> = {}; // projectId -> slideIndex -> thumbnailUrl

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

    function getThumbnailUrl(projectId: string, slideIndex: number): string | undefined {
        return slideThumbnails[projectId]?.[slideIndex];
    }

    function handleClose() {
        isOpen = false;
        expandedImageUrl = null;
    }
</script>

<Modal {isOpen} title="" size="full" on:close={handleClose}>
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
                        <span class="font-medium text-gray-900">{instance.projectTitle}</span>
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

                    <!-- Captures -->
                    {#if captures.length > 0}
                        <div class="mb-3">
                            <div class="text-xs text-gray-500 mb-2">캡처 ({captures.length}개)</div>
                            <div class="flex flex-wrap gap-2">
                                {#each captures as capture}
                                    {@const thumbnailUrl = getThumbnailUrl(instance.projectId, capture.slideIndex)}
                                    <div class="relative group">
                                        <div
                                            class="w-24 h-18 bg-gray-100 rounded border border-gray-200 overflow-hidden cursor-pointer hover:border-blue-400 transition-colors"
                                            on:click={() => {
                                                if (thumbnailUrl) expandedImageUrl = thumbnailUrl;
                                            }}
                                            on:keydown={(e) => {
                                                if (e.key === 'Enter' && thumbnailUrl) expandedImageUrl = thumbnailUrl;
                                            }}
                                            role="button"
                                            tabindex="0"
                                        >
                                            {#if thumbnailUrl}
                                                <div class="relative w-full h-full">
                                                    <img
                                                        src={thumbnailUrl}
                                                        alt="슬라이드 {capture.slideIndex + 1}"
                                                        class="w-full h-full object-cover"
                                                    />
                                                    <!-- Capture region overlay (simplified) -->
                                                    <div
                                                        class="absolute border-2 border-blue-500 bg-blue-500/10 pointer-events-none"
                                                        style="
                                                            left: {(capture.x / 960) * 100}%;
                                                            top: {(capture.y / 540) * 100}%;
                                                            width: {(capture.width / 960) * 100}%;
                                                            height: {(capture.height / 540) * 100}%;
                                                        "
                                                    ></div>
                                                </div>
                                            {:else}
                                                <div class="w-full h-full flex items-center justify-center">
                                                    <svg class="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                    </svg>
                                                </div>
                                            {/if}
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
