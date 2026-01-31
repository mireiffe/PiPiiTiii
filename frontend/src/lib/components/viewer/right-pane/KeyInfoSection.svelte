<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, tick } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import Modal from "$lib/components/ui/Modal.svelte";
    import type {
        ProjectKeyInfoData,
        KeyInfoSettings,
        KeyInfoCategoryDefinition,
        KeyInfoItemDefinition,
        KeyInfoInstance,
    } from "$lib/types/keyInfo";
    import {
        createEmptyKeyInfoData,
        createKeyInfoInstance,
        generateKeyInfoCaptureId,
    } from "$lib/types/keyInfo";
    import {
        uploadAttachmentImage,
        deleteAttachmentImage,
        getAttachmentImageUrl,
    } from "$lib/api/project";
    import { generateAttachmentId } from "$lib/types/workflow";

    export let isExpanded = false;
    export let projectId: string = "";
    export let keyInfoData: ProjectKeyInfoData = createEmptyKeyInfoData();
    export let keyInfoSettings: KeyInfoSettings = { categories: [] };
    export let savingKeyInfo = false;
    export let captureMode = false;
    export let captureTargetInstanceId: string | null = null;
    export let slideWidth: number = 960;
    export let slideHeight: number = 540;

    const dispatch = createEventDispatcher();

    // State
    let addingItemToCategoryId: string | null = null;
    let editingTextInstanceId: string | null = null;
    let textInputValue: string = "";

    // Image viewer modal state
    let viewingImageId: string | null = null;
    let viewingInstanceId: string | null = null;
    let editingImageCaption: string = "";
    let isEditingCaption = false;

    // Reactive: precompute instance lookup for each category
    // Svelte 5에서 IIFE 패턴은 의존성 추적이 안될 수 있으므로 명시적 체인 사용
    $: keyInfoInstances = keyInfoData.instances;
    $: instancesByCategory = buildInstancesByCategory(keyInfoInstances);

    function buildInstancesByCategory(instances: KeyInfoInstance[]): Map<string, Map<string, KeyInfoInstance>> {
        const map = new Map<string, Map<string, KeyInfoInstance>>();
        for (const inst of instances) {
            if (!map.has(inst.categoryId)) {
                map.set(inst.categoryId, new Map());
            }
            map.get(inst.categoryId)!.set(inst.itemId, inst);
        }
        return map;
    }

    // Get added items for a category (items that have instances)
    function getAddedItems(category: KeyInfoCategoryDefinition): Array<{ item: KeyInfoItemDefinition; instance: KeyInfoInstance }> {
        const categoryInstances = instancesByCategory.get(category.id);
        if (!categoryInstances) return [];

        return category.items
            .map(item => ({
                item,
                instance: categoryInstances.get(item.id)
            }))
            .filter((entry): entry is { item: KeyInfoItemDefinition; instance: KeyInfoInstance } =>
                entry.instance !== undefined
            )
            .sort((a, b) => a.instance.order - b.instance.order);
    }

    // Get available items for a category (items that don't have instances yet)
    function getAvailableItems(category: KeyInfoCategoryDefinition): KeyInfoItemDefinition[] {
        const categoryInstances = instancesByCategory.get(category.id);
        if (!categoryInstances) return category.items;

        return category.items.filter(item => !categoryInstances.has(item.id));
    }

    // Add item to category (create instance)
    async function addItemToCategory(categoryId: string, itemId: string) {
        // Close dropdown first to prevent race conditions
        addingItemToCategoryId = null;

        // Wait for Svelte to process the state change
        await tick();

        // Create and add the new instance
        const instance = createKeyInfoInstance(categoryId, itemId, keyInfoData.instances.length);
        // Create a new object to ensure Svelte detects the change
        keyInfoData = {
            ...keyInfoData,
            instances: [...keyInfoData.instances, instance]
        };

        // Emit change after state is settled
        emitChange();
    }

    // Remove item (delete instance) - 확인 창 표시
    async function removeItem(instanceId: string) {
        const instance = keyInfoData.instances.find(i => i.id === instanceId);
        if (!instance) return;

        const category = keyInfoSettings.categories.find(c => c.id === instance.categoryId);
        const item = category?.items.find(i => i.id === instance.itemId);

        if (!confirm(`'${item?.title || '이 항목'}'을(를) 삭제하시겠습니까?`)) {
            return;
        }

        // 연결된 이미지들 삭제
        const imageIds = instance.imageIds || (instance.imageId ? [instance.imageId] : []);
        for (const imgId of imageIds) {
            try {
                await deleteAttachmentImage(imgId);
            } catch (e) {
                console.error("Failed to delete image", e);
            }
        }

        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.filter(inst => inst.id !== instanceId)
        };
        emitChange();
    }

    // Start capture mode
    function startCapture(instanceId: string) {
        dispatch("toggleCaptureMode", { instanceId });
    }

    // Add capture to instance (called from parent via exported function)
    // 배열에 추가 (다중 캡처 지원)
    export function addCapture(
        instanceId: string,
        captureData: { slideIndex: number; x: number; y: number; width: number; height: number }
    ) {
        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.map(inst =>
                inst.id === instanceId
                    ? {
                        ...inst,
                        captureValues: [
                            ...(inst.captureValues || []),
                            {
                                id: generateKeyInfoCaptureId(),
                                ...captureData,
                            }
                        ],
                        // deprecated 필드 정리
                        captureValue: undefined,
                        updatedAt: new Date().toISOString(),
                    }
                    : inst
            )
        };
        emitChange();
        dispatch("toggleCaptureMode", { instanceId: null }); // End capture mode
    }

    // Start text editing
    function startTextEdit(instance: KeyInfoInstance) {
        editingTextInstanceId = instance.id;
        textInputValue = instance.textValue || "";
    }

    // Save text
    function saveText(instanceId: string) {
        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.map(inst =>
                inst.id === instanceId
                    ? {
                        ...inst,
                        textValue: textInputValue,
                        updatedAt: new Date().toISOString(),
                    }
                    : inst
            )
        };
        editingTextInstanceId = null;
        textInputValue = "";
        emitChange();
    }

    // Cancel text editing
    function cancelTextEdit() {
        editingTextInstanceId = null;
        textInputValue = "";
    }

    // Handle image paste (배열에 추가 - 다중 이미지 지원)
    async function handleImagePaste(event: ClipboardEvent, instanceId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;

        for (const item of Array.from(items)) {
            if (item.type.startsWith("image/")) {
                event.preventDefault();
                const blob = item.getAsFile();
                if (!blob) continue;

                const reader = new FileReader();
                reader.onload = async () => {
                    const base64Data = reader.result as string;
                    const imageId = generateAttachmentId();

                    try {
                        const res = await uploadAttachmentImage(imageId, projectId, base64Data);
                        if (res.ok) {
                            keyInfoData = {
                                ...keyInfoData,
                                instances: keyInfoData.instances.map(inst =>
                                    inst.id === instanceId
                                        ? {
                                            ...inst,
                                            imageIds: [...(inst.imageIds || []), imageId],
                                            // deprecated 필드 정리
                                            imageId: undefined,
                                            imageCaption: undefined,
                                            updatedAt: new Date().toISOString(),
                                        }
                                        : inst
                                )
                            };
                            emitChange();

                            // Auto-open modal for caption entry
                            openImageViewer(instanceId, imageId);
                            isEditingCaption = true;
                        }
                    } catch (e) {
                        console.error("Failed to upload image", e);
                    }
                };
                reader.readAsDataURL(blob);
                break;
            }
        }
    }

    // Delete image (배열에서 특정 이미지 삭제)
    async function deleteImage(instanceId: string, imageIdToDelete: string) {
        try {
            await deleteAttachmentImage(imageIdToDelete);
        } catch (e) {
            console.error("Failed to delete image", e);
        }

        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.map(inst => {
                if (inst.id !== instanceId) return inst;
                const newCaptions = { ...(inst.imageCaptions || {}) };
                delete newCaptions[imageIdToDelete];
                return {
                    ...inst,
                    imageIds: (inst.imageIds || []).filter(id => id !== imageIdToDelete),
                    imageCaptions: Object.keys(newCaptions).length > 0 ? newCaptions : undefined,
                    // deprecated 필드 정리
                    imageId: undefined,
                    imageCaption: undefined,
                    updatedAt: new Date().toISOString(),
                };
            })
        };
        emitChange();
    }

    // Delete capture (배열에서 특정 캡처 삭제)
    function deleteCapture(instanceId: string, captureIdToDelete: string) {
        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.map(inst =>
                inst.id === instanceId
                    ? {
                        ...inst,
                        captureValues: (inst.captureValues || []).filter(c => c.id !== captureIdToDelete),
                        // deprecated 필드 정리
                        captureValue: undefined,
                        updatedAt: new Date().toISOString(),
                    }
                    : inst
            )
        };
        emitChange();
    }

    // Get capture overlays for viewer (배열 지원)
    export function getCaptureOverlays(): Array<{
        instanceId: string;
        captureId: string;
        label: string;
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        color: string;
    }> {
        const overlays: Array<{
            instanceId: string;
            captureId: string;
            label: string;
            slideIndex: number;
            x: number;
            y: number;
            width: number;
            height: number;
            color: string;
        }> = [];

        for (const instance of keyInfoData.instances) {
            // 신규 배열 필드 또는 deprecated 단일 필드 처리
            const captures = instance.captureValues ||
                (instance.captureValue ? [instance.captureValue] : []);

            for (const capture of captures) {
                const category = keyInfoSettings.categories.find(c => c.id === instance.categoryId);
                const item = category?.items.find(i => i.id === instance.itemId);

                overlays.push({
                    instanceId: instance.id,
                    captureId: capture.id,
                    label: item?.title || "캡처",
                    slideIndex: capture.slideIndex,
                    x: capture.x,
                    y: capture.y,
                    width: capture.width,
                    height: capture.height,
                    color: "#3b82f6", // Blue
                });
            }
        }

        return overlays;
    }

    // Emit change event
    function emitChange() {
        dispatch("keyInfoChange", { keyInfoData });
    }

    // Auto-resize textarea
    function autoResizeTextarea(textarea: HTMLTextAreaElement) {
        const resize = () => {
            textarea.style.height = "auto";
            textarea.style.height = textarea.scrollHeight + "px";
        };
        resize();
        textarea.addEventListener("input", resize);
        return {
            destroy() {
                textarea.removeEventListener("input", resize);
            },
        };
    }

    // Handle keyboard shortcuts
    function handleTextKeydown(e: KeyboardEvent, instanceId: string) {
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
            e.preventDefault();
            saveText(instanceId);
        } else if (e.key === "Escape") {
            cancelTextEdit();
        }
    }

    // Close dropdown when clicking outside (with delay to allow item click to process)
    function handleClickOutside(event: MouseEvent) {
        const target = event.target as HTMLElement;
        // Don't close if clicking inside dropdown area
        if (target.closest('.item-dropdown')) {
            return;
        }
        // Use setTimeout to ensure any dropdown item click handlers complete first
        setTimeout(() => {
            addingItemToCategoryId = null;
        }, 10);
    }

    // Calculate thumbnail cropping styles for capture preview
    function getCaptureThumbStyle(capture: { x: number; y: number; width: number; height: number; slideIndex: number }): string {
        const thumbUrl = `/api/results/${projectId}/thumbnails/slide_${String(capture.slideIndex).padStart(3, '0')}_thumb.png`;

        // Guard against zero-size captures
        if (capture.width <= 0 || capture.height <= 0) {
            return `background-image: url('${thumbUrl}'); background-size: cover; background-position: center;`;
        }

        // Thumbnail is rendered at max 1920px width
        const thumbMaxWidth = 1920;
        const thumbScale = thumbMaxWidth / slideWidth;
        const thumbHeight = slideHeight * thumbScale;

        // Scale capture coordinates to thumbnail space
        const thumbX = capture.x * thumbScale;
        const thumbY = capture.y * thumbScale;
        const thumbW = capture.width * thumbScale;
        const thumbH = capture.height * thumbScale;

        // Container size
        const containerW = 60;
        const containerH = 45;

        // Calculate scale to fit capture region into container
        const displayScale = Math.max(containerW / thumbW, containerH / thumbH);

        // Calculate background size
        const bgWidth = thumbMaxWidth * displayScale;
        const bgHeight = thumbHeight * displayScale;

        // Calculate background position (negative values to offset)
        const offsetX = -thumbX * displayScale + (containerW - thumbW * displayScale) / 2;
        const offsetY = -thumbY * displayScale + (containerH - thumbH * displayScale) / 2;

        return `background-image: url('${thumbUrl}'); background-size: ${bgWidth}px ${bgHeight}px; background-position: ${offsetX}px ${offsetY}px;`;
    }

    // Open image viewer modal
    function openImageViewer(instanceId: string, imageId: string) {
        viewingInstanceId = instanceId;
        viewingImageId = imageId;

        // Load existing caption
        const instance = keyInfoData.instances.find(i => i.id === instanceId);
        editingImageCaption = instance?.imageCaptions?.[imageId] || "";
        isEditingCaption = false;
    }

    // Close image viewer modal
    function closeImageViewer() {
        // Auto-save caption if changed
        if (viewingInstanceId && viewingImageId && isEditingCaption) {
            saveImageCaption();
        }
        viewingImageId = null;
        viewingInstanceId = null;
        editingImageCaption = "";
        isEditingCaption = false;
    }

    // Save image caption
    function saveImageCaption() {
        if (!viewingInstanceId || !viewingImageId) return;

        keyInfoData = {
            ...keyInfoData,
            instances: keyInfoData.instances.map(inst => {
                if (inst.id !== viewingInstanceId) return inst;
                return {
                    ...inst,
                    imageCaptions: {
                        ...(inst.imageCaptions || {}),
                        [viewingImageId!]: editingImageCaption,
                    },
                    updatedAt: new Date().toISOString(),
                };
            })
        };
        isEditingCaption = false;
        emitChange();
    }

    // Start editing caption
    function startEditCaption() {
        isEditingCaption = true;
    }

    // Handle caption keydown
    function handleCaptionKeydown(e: KeyboardEvent) {
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
            e.preventDefault();
            saveImageCaption();
        } else if (e.key === "Escape") {
            // Revert to saved caption
            const instance = keyInfoData.instances.find(i => i.id === viewingInstanceId);
            editingImageCaption = instance?.imageCaptions?.[viewingImageId!] || "";
            isEditingCaption = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="border-t border-gray-200 {isExpanded ? 'flex-1 flex flex-col min-h-0' : ''}">
    <AccordionHeader
        title="핵심정보"
        {isExpanded}
        on:click={() => dispatch("toggleExpand")}
    />

    {#if isExpanded}
        <div class="p-2 space-y-2 overflow-y-auto flex-1 min-h-0" transition:slide={{ duration: 200 }}>
            {#if keyInfoSettings.categories.length === 0}
                <div class="text-center text-gray-400 py-6 border border-dashed border-gray-300 rounded-lg">
                    <div class="text-blue-400 mb-2">
                        <svg class="w-10 h-10 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </div>
                    <p class="text-sm">핵심정보 카테고리가 정의되지 않았습니다.</p>
                    <p class="text-xs text-gray-400 mt-1">설정에서 카테고리를 추가해주세요.</p>
                </div>
            {:else}
                {#key keyInfoData.instances}
                {#each keyInfoSettings.categories.sort((a, b) => a.order - b.order) as category (category.id)}
                    {@const addedItems = getAddedItems(category)}
                    {@const availableItems = getAvailableItems(category)}
                    <div class="border rounded-lg bg-white">
                        <!-- Category Header -->
                        <div class="flex items-center gap-2 px-2.5 py-1.5 bg-gray-50 border-b border-gray-100">
                            <span class="flex-1 font-medium text-gray-800 text-sm">{category.name}</span>

                            <!-- 추가된 항목 수 표시 -->
                            {#if addedItems.length > 0}
                                <span class="text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full">
                                    {addedItems.length}
                                </span>
                            {/if}

                            <!-- "+" 추가 버튼 - 더 크고 눈에 띄게 -->
                            <div class="relative item-dropdown">
                                <button
                                    class="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors
                                        {availableItems.length === 0
                                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                            : 'bg-blue-500 text-white hover:bg-blue-600 shadow-sm'}"
                                    on:click|stopPropagation={() => {
                                        if (availableItems.length > 0) {
                                            addingItemToCategoryId = addingItemToCategoryId === category.id ? null : category.id;
                                        }
                                    }}
                                    disabled={availableItems.length === 0}
                                    title={availableItems.length === 0 ? "추가할 수 있는 항목이 없습니다" : "항목 추가"}
                                >
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
                                    </svg>
                                    <span>추가</span>
                                </button>

                                <!-- 항목 선택 드롭다운 -->
                                {#if addingItemToCategoryId === category.id}
                                    <div
                                        class="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg min-w-[200px] py-1"
                                        transition:slide={{ duration: 100 }}
                                    >
                                        <div class="px-3 py-1.5 text-xs text-gray-500 font-medium border-b border-gray-100">
                                            추가할 항목 선택
                                        </div>
                                        {#each availableItems as item (item.id)}
                                            <button
                                                class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors"
                                                on:click|stopPropagation={() => addItemToCategory(category.id, item.id)}
                                            >
                                                <div class="font-medium">{item.title}</div>
                                                {#if item.description}
                                                    <div class="text-xs text-gray-400 mt-0.5">{item.description}</div>
                                                {/if}
                                            </button>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        </div>

                        <!-- Category Content -->
                        <div class="p-2 space-y-2">
                            {#if addedItems.length === 0}
                                <div class="text-center text-gray-400 py-3 text-xs border border-dashed border-gray-200 rounded">
                                    항목 없음 - 위 '추가' 버튼을 클릭하세요
                                </div>
                            {:else}
                                {#each addedItems as { item, instance } (instance.id)}
                                    {@const captures = instance.captureValues || (instance.captureValue ? [instance.captureValue] : [])}
                                    {@const images = instance.imageIds || (instance.imageId ? [instance.imageId] : [])}
                                    <div class="border rounded p-2 bg-gray-50">
                                        <!-- Item Header -->
                                        <div class="flex items-start justify-between mb-2">
                                            <div class="flex-1 min-w-0">
                                                <div class="font-medium text-gray-800 text-xs">{item.title}</div>
                                                {#if item.description}
                                                    <div class="text-[10px] text-gray-500 mt-0.5 truncate">{item.description}</div>
                                                {/if}
                                            </div>
                                            <button
                                                class="text-gray-400 hover:text-red-500 transition-colors p-0.5 flex-shrink-0"
                                                on:click={() => removeItem(instance.id)}
                                                title="항목 삭제"
                                            >
                                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>

                                        <!-- 1. 텍스트 영역 (항상 표시) -->
                                        <div class="mb-2">
                                            {#if editingTextInstanceId === instance.id}
                                                <div class="space-y-1.5">
                                                    <textarea
                                                        bind:value={textInputValue}
                                                        use:autoResizeTextarea
                                                        on:keydown={(e) => handleTextKeydown(e, instance.id)}
                                                        on:paste={(e) => handleImagePaste(e, instance.id)}
                                                        class="w-full border border-blue-400 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none bg-white"
                                                        rows="2"
                                                        placeholder="텍스트를 입력하세요..."
                                                        autofocus
                                                    ></textarea>
                                                    <div class="flex gap-1.5 justify-between items-center">
                                                        <span class="text-[9px] text-gray-400">
                                                            Ctrl+S 저장 | Ctrl+V 이미지 | Esc 취소
                                                        </span>
                                                        <div class="flex gap-1.5">
                                                            <button
                                                                class="text-[10px] bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                                                                on:click={() => saveText(instance.id)}
                                                            >
                                                                저장
                                                            </button>
                                                            <button
                                                                class="text-[10px] text-gray-500 px-2 py-1 hover:text-gray-700"
                                                                on:click={cancelTextEdit}
                                                            >
                                                                취소
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            {:else}
                                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                <div
                                                    class="min-h-[40px] p-2 border rounded bg-white cursor-pointer hover:border-blue-300 transition-colors
                                                        {instance.textValue ? 'text-gray-800' : 'text-gray-400 italic'}"
                                                    on:click={() => startTextEdit(instance)}
                                                >
                                                    {#if instance.textValue}
                                                        <div class="text-xs whitespace-pre-wrap">{instance.textValue}</div>
                                                    {:else}
                                                        <div class="text-xs">클릭하여 텍스트 입력...</div>
                                                    {/if}
                                                </div>
                                            {/if}
                                        </div>

                                        <!-- 2. 첨부 영역 (캡처 + 이미지 수평 갤러리) -->
                                        {#if captures.length > 0 || images.length > 0}
                                            <!-- 수평 스크롤 썸네일 갤러리 -->
                                            <div class="flex gap-1.5 overflow-x-auto pb-1" style="scrollbar-width: thin;">
                                                <!-- 캡처 썸네일들 -->
                                                {#each captures as capture (capture.id)}
                                                    <div class="relative flex-shrink-0 w-[60px] h-[45px] bg-gray-200 rounded overflow-hidden border border-gray-200 group">
                                                        <div
                                                            class="absolute inset-0"
                                                            style={getCaptureThumbStyle(capture)}
                                                        ></div>
                                                        <div class="absolute top-0.5 left-0.5 text-[7px] bg-blue-600 text-white px-0.5 rounded">
                                                            S{capture.slideIndex + 1}
                                                        </div>
                                                        <button
                                                            class="absolute top-0.5 right-0.5 p-0.5 bg-red-500 text-white rounded hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            on:click={() => deleteCapture(instance.id, capture.id)}
                                                            title="캡처 삭제"
                                                        >
                                                            <svg class="w-2 h-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                {/each}

                                                <!-- 이미지 썸네일들 -->
                                                {#each images as imageId (imageId)}
                                                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                    <div
                                                        class="relative flex-shrink-0 w-[60px] h-[45px] rounded overflow-hidden border border-gray-200 group cursor-pointer hover:ring-2 hover:ring-blue-400"
                                                        on:click={() => openImageViewer(instance.id, imageId)}
                                                        title="클릭하여 이미지 보기"
                                                    >
                                                        <img
                                                            src={getAttachmentImageUrl(imageId)}
                                                            alt="첨부 이미지"
                                                            class="w-full h-full object-cover"
                                                        />
                                                        <!-- Caption indicator -->
                                                        {#if instance.imageCaptions?.[imageId]}
                                                            <div class="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[7px] px-0.5 truncate">
                                                                {instance.imageCaptions[imageId]}
                                                            </div>
                                                        {/if}
                                                        <button
                                                            class="absolute top-0.5 right-0.5 p-0.5 bg-red-500 text-white rounded hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            on:click|stopPropagation={() => deleteImage(instance.id, imageId)}
                                                            title="이미지 삭제"
                                                        >
                                                            <svg class="w-2 h-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                {/each}

                                                <!-- 추가 버튼 -->
                                                <button
                                                    class="flex-shrink-0 w-[60px] h-[45px] border border-dashed border-gray-300 rounded flex flex-col items-center justify-center text-gray-400 hover:border-blue-300 hover:text-blue-500 transition-colors
                                                        {captureTargetInstanceId === instance.id ? 'bg-blue-50 border-blue-400 text-blue-600' : ''}"
                                                    on:click={() => startCapture(instance.id)}
                                                    title="캡처 추가"
                                                >
                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v16m8-8H4" />
                                                    </svg>
                                                </button>
                                            </div>
                                        {:else}
                                            <!-- 첨부 없음 - 작은 버튼들 -->
                                            <div class="flex gap-1.5 items-center">
                                                <button
                                                    class="px-2 py-1 text-[9px] border border-dashed border-gray-300 rounded flex items-center gap-1 text-gray-500 hover:border-blue-300 hover:text-blue-600 transition-colors
                                                        {captureTargetInstanceId === instance.id ? 'bg-blue-50 border-blue-400 text-blue-600' : ''}"
                                                    on:click={() => startCapture(instance.id)}
                                                >
                                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" />
                                                    </svg>
                                                    {captureTargetInstanceId === instance.id ? "선택 중..." : "캡처"}
                                                </button>
                                                <span class="text-[9px] text-gray-400">Ctrl+V로 이미지 붙여넣기</span>
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            {/if}
                        </div>
                    </div>
                {/each}
                {/key}
            {/if}

            <!-- Saving indicator -->
            {#if savingKeyInfo}
                <div class="text-center text-xs text-blue-600 py-1">
                    저장 중...
                </div>
            {/if}
        </div>
    {/if}
</div>

<!-- Image Viewer Modal -->
<Modal
    isOpen={viewingImageId !== null}
    title="이미지 보기"
    size="lg"
    on:close={closeImageViewer}
>
    {#if viewingImageId}
        <div class="flex flex-col gap-4">
            <!-- Full-size image -->
            <div class="flex justify-center bg-gray-100 rounded-lg p-2">
                <img
                    src={getAttachmentImageUrl(viewingImageId)}
                    alt="첨부 이미지"
                    class="max-w-full max-h-[60vh] object-contain"
                />
            </div>

            <!-- Caption section -->
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <label class="text-sm font-medium text-gray-700">캡션</label>
                    {#if !isEditingCaption && editingImageCaption}
                        <button
                            class="text-xs text-blue-600 hover:text-blue-800"
                            on:click={startEditCaption}
                        >
                            수정
                        </button>
                    {/if}
                </div>

                {#if isEditingCaption || !editingImageCaption}
                    <div class="space-y-2">
                        <textarea
                            bind:value={editingImageCaption}
                            on:keydown={handleCaptionKeydown}
                            on:input={() => isEditingCaption = true}
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                            rows="2"
                            placeholder="이미지에 대한 설명을 입력하세요..."
                        ></textarea>
                        {#if isEditingCaption}
                            <div class="flex gap-2 justify-end">
                                <button
                                    class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                    on:click={saveImageCaption}
                                >
                                    저장
                                </button>
                                <button
                                    class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                                    on:click={() => {
                                        const instance = keyInfoData.instances.find(i => i.id === viewingInstanceId);
                                        editingImageCaption = instance?.imageCaptions?.[viewingImageId!] || "";
                                        isEditingCaption = false;
                                    }}
                                >
                                    취소
                                </button>
                            </div>
                            <p class="text-xs text-gray-400">Ctrl+S 저장 | Esc 취소</p>
                        {/if}
                    </div>
                {:else}
                    <p class="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                        {editingImageCaption}
                    </p>
                {/if}
            </div>
        </div>
    {/if}
</Modal>
