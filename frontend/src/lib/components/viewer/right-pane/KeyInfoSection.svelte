<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher, tick, onMount } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import Modal from "$lib/components/ui/Modal.svelte";
    import ActivityLogModal from "./ActivityLogModal.svelte";
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
        createKeyInfoItem,
        generateKeyInfoCaptureId,
    } from "$lib/types/keyInfo";
    import {
        uploadAttachmentImage,
        deleteAttachmentImage,
        getAttachmentImageUrl,
        generateTextStream,
        updateProjectKeyInfoCompleted,
        fetchKeyinfoUsageCounts,
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
    export let selectedSlideIndices: number[] = [];
    export let keyInfoCompleted: boolean = false;

    const dispatch = createEventDispatcher();

    // State
    let editingTextInstanceId: string | null = null;
    let textInputValue: string = "";

    // Empty Ticket 상태
    let editingEmptyCategoryId: string | null = null;
    let emptyTicketSearchText: string = "";

    // 새 항목 추가 모드 상태
    let addingNewItemToCategoryId: string | null = null;
    let newItemTitle: string = "";
    let newItemDescription: string = "";

    // Image viewer modal state
    let viewingImageId: string | null = null;
    let viewingInstanceId: string | null = null;
    let editingImageCaption: string = "";
    let isEditingCaption = false;

    // Activity log modal
    let showActivityLog = false;

    // Usage counts: how many projects use each keyinfo item
    let usageCounts: Record<string, number> = {};

    async function loadUsageCounts() {
        try {
            const res = await fetchKeyinfoUsageCounts();
            if (res.ok) {
                const data = await res.json();
                usageCounts = data.counts || {};
            }
        } catch (e) {
            console.error("Failed to load keyinfo usage counts", e);
        }
    }

    onMount(() => {
        loadUsageCounts();
    });

    function getItemUsageCount(categoryId: string, itemId: string): number {
        return usageCounts[`${categoryId}_${itemId}`] || 0;
    }

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

    // Get filtered items based on search text
    function getFilteredItems(category: KeyInfoCategoryDefinition): KeyInfoItemDefinition[] {
        const available = getAvailableItems(category);
        if (!emptyTicketSearchText.trim()) return available;

        const search = emptyTicketSearchText.toLowerCase();
        return available.filter(item =>
            item.title.toLowerCase().includes(search)
        );
    }

    // Check if search text matches any existing item (for showing "add new" option)
    function hasExactMatch(category: KeyInfoCategoryDefinition): boolean {
        if (!emptyTicketSearchText.trim()) return false;
        const search = emptyTicketSearchText.trim().toLowerCase();
        return category.items.some(item => item.title.toLowerCase() === search);
    }

    // Start editing empty ticket
    function startEmptyTicketEdit(categoryId: string) {
        editingEmptyCategoryId = categoryId;
        emptyTicketSearchText = "";
    }

    // Cancel empty ticket edit
    function cancelEmptyTicketEdit() {
        editingEmptyCategoryId = null;
        emptyTicketSearchText = "";
    }

    // Start add new item mode
    function startAddNewItem(categoryId: string, title: string) {
        addingNewItemToCategoryId = categoryId;
        newItemTitle = title;
        newItemDescription = "";
        editingEmptyCategoryId = null;
        emptyTicketSearchText = "";
    }

    // Cancel add new item
    function cancelAddNewItem() {
        addingNewItemToCategoryId = null;
        newItemTitle = "";
        newItemDescription = "";
    }

    // Confirm add new item
    async function confirmAddNewItem() {
        if (!addingNewItemToCategoryId || !newItemTitle.trim()) return;

        const category = keyInfoSettings.categories.find(c => c.id === addingNewItemToCategoryId);
        if (!category) return;

        // 1. Create new item definition
        const newItem = createKeyInfoItem(
            newItemTitle.trim(),
            newItemDescription.trim(),
            category.items.length
        );

        // 2. Update settings
        const updatedSettings = {
            ...keyInfoSettings,
            categories: keyInfoSettings.categories.map(c =>
                c.id === addingNewItemToCategoryId
                    ? { ...c, items: [...c.items, newItem] }
                    : c
            )
        };

        // 3. Notify parent about settings change
        dispatch("keyInfoSettingsChange", { keyInfoSettings: updatedSettings });

        // 4. Create new instance
        const categoryId = addingNewItemToCategoryId;
        cancelAddNewItem();
        await addItemToCategory(categoryId, newItem.id);
    }

    // Handle empty ticket keydown
    function handleEmptyTicketKeydown(e: KeyboardEvent, categoryId: string) {
        if (e.key === "Escape") {
            cancelEmptyTicketEdit();
        } else if (e.key === "Enter") {
            e.preventDefault();
            const category = keyInfoSettings.categories.find(c => c.id === categoryId);
            if (!category) return;

            const filtered = getFilteredItems(category);
            if (filtered.length === 1) {
                // Select the only matching item
                addItemToCategory(categoryId, filtered[0].id);
                cancelEmptyTicketEdit();
            } else if (filtered.length === 0 && emptyTicketSearchText.trim() && !hasExactMatch(category)) {
                // Start adding new item
                startAddNewItem(categoryId, emptyTicketSearchText.trim());
            }
        }
    }

    // Add item to category (create instance)
    async function addItemToCategory(categoryId: string, itemId: string) {
        // Close empty ticket edit first
        cancelEmptyTicketEdit();

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

    // LLM 자동 생성 상태
    let generatingInstanceId: string | null = null;

    // 템플릿 변수 치환
    function resolveTemplate(template: string, item: KeyInfoItemDefinition): string {
        return template
            .replace(/\{\{key_info_title\}\}/g, item.title)
            .replace(/\{\{key_info_description\}\}/g, item.description || '');
    }

    // LLM 자동 생성
    async function autoGenerate(instance: KeyInfoInstance) {
        const category = keyInfoSettings.categories.find(c => c.id === instance.categoryId);
        const item = category?.items.find(i => i.id === instance.itemId);
        if (!category || !item) return;

        if (!category.systemPrompt && !category.userPrompt) {
            alert('설정에서 이 카테고리의 LLM 프롬프트를 먼저 설정해주세요.');
            return;
        }

        const slideIndices = selectedSlideIndices.length > 0
            ? selectedSlideIndices
            : Array.from({ length: 20 }, (_, i) => i); // fallback: first 20 slides

        const systemPrompt = resolveTemplate(category.systemPrompt || '당신은 PPT 프레젠테이션을 분석하는 전문가입니다.', item);
        const userPrompt = resolveTemplate(category.userPrompt || '이 슬라이드에서 {{key_info_title}}에 해당하는 내용을 찾아 설명해주세요.', item);

        generatingInstanceId = instance.id;

        try {
            const stream = await generateTextStream(projectId, systemPrompt, userPrompt, slideIndices);
            if (!stream) return;

            const reader = stream.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                accumulated += decoder.decode(value, { stream: true });

                // 실시간 반영
                keyInfoData = {
                    ...keyInfoData,
                    instances: keyInfoData.instances.map(inst =>
                        inst.id === instance.id
                            ? { ...inst, textValue: accumulated, updatedAt: new Date().toISOString() }
                            : inst
                    )
                };
            }

            emitChange();
        } catch (e) {
            console.error('Auto-generate failed:', e);
            alert('자동 생성에 실패했습니다.');
        } finally {
            generatingInstanceId = null;
        }
    }

    // Toggle completed status
    let togglingCompleted = false;
    async function toggleCompleted() {
        togglingCompleted = true;
        try {
            const newValue = !keyInfoCompleted;
            const res = await updateProjectKeyInfoCompleted(projectId, newValue);
            if (res.ok) {
                keyInfoCompleted = newValue;
                dispatch("keyInfoCompletedChange", { completed: newValue });
            }
        } catch (e) {
            console.error("Failed to toggle completed status", e);
        } finally {
            togglingCompleted = false;
        }
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

    // Close empty ticket edit when clicking outside
    function handleClickOutside(event: MouseEvent) {
        const target = event.target as HTMLElement;
        // Don't close if clicking inside empty ticket or new item form
        if (target.closest('.empty-ticket-area')) {
            return;
        }
        // Use setTimeout to ensure any click handlers complete first
        setTimeout(() => {
            if (editingEmptyCategoryId) {
                cancelEmptyTicketEdit();
            }
        }, 10);
    }

    // Calculate thumbnail cropping styles for capture preview
    function getCaptureThumbStyle(capture: { x: number; y: number; width: number; height: number; slideIndex: number }): string {
        const thumbUrl = `/api/results/${projectId}/thumbnails/slide_${String(capture.slideIndex + 1).padStart(3, '0')}_thumb.png`;

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
        const containerW = 80;
        const containerH = 60;

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
    >
        <button
            slot="actions"
            class="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            on:click|stopPropagation={() => (showActivityLog = true)}
            title="활동 로그"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        </button>
    </AccordionHeader>

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
                    <div class="border rounded-lg bg-white shadow-sm">
                        <!-- Category Header -->
                        <div class="flex items-center gap-2 px-3 py-2 bg-blue-50/70 border-b border-blue-100 rounded-t-lg">
                            <span class="flex-1 font-semibold text-blue-900 text-sm">{category.name}</span>

                            <!-- 추가된 항목 수 표시 -->
                            {#if addedItems.length > 0}
                                <span class="text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full">
                                    {addedItems.length}
                                </span>
                            {/if}
                        </div>

                        <!-- Category Content -->
                        <div class="p-2.5 space-y-2.5">
                            {#each addedItems as { item, instance } (instance.id)}
                                    {@const captures = instance.captureValues || (instance.captureValue ? [instance.captureValue] : [])}
                                    {@const images = instance.imageIds || (instance.imageId ? [instance.imageId] : [])}
                                    <div class="border border-gray-200 rounded-lg p-2.5 bg-gray-50/80">
                                        <!-- Item Header -->
                                        <div class="flex items-start justify-between mb-2.5">
                                            <div class="flex-1 min-w-0">
                                                <div class="flex items-center gap-1.5">
                                                    <span class="font-bold text-gray-900 text-xs">{item.title}</span>
                                                    {#if getItemUsageCount(instance.categoryId, instance.itemId) > 0}
                                                        <span class="text-[9px] text-gray-400 bg-gray-100 px-1 py-0.5 rounded" title="{getItemUsageCount(instance.categoryId, instance.itemId)}개 프로젝트에서 사용">총 {getItemUsageCount(instance.categoryId, instance.itemId)}번 사용됨</span>
                                                    {/if}
                                                </div>
                                                {#if item.description}
                                                    <div class="text-[10px] text-gray-500 mt-0.5 leading-relaxed">{item.description}</div>
                                                {/if}
                                            </div>
                                            <div class="flex items-center gap-0.5 flex-shrink-0">
                                                <!-- 자동 생성 버튼 -->
                                                {#if generatingInstanceId === instance.id}
                                                    <div class="p-0.5 text-purple-500 animate-spin" title="생성 중...">
                                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                                        </svg>
                                                    </div>
                                                {:else}
                                                    <button
                                                        class="text-gray-400 hover:text-purple-500 transition-colors p-0.5"
                                                        on:click={() => autoGenerate(instance)}
                                                        title="LLM 자동 생성"
                                                    >
                                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                                        </svg>
                                                    </button>
                                                {/if}
                                                <button
                                                    class="text-gray-400 hover:text-red-500 transition-colors p-0.5"
                                                    on:click={() => removeItem(instance.id)}
                                                    title="항목 삭제"
                                                >
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            </div>
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
                                                    <div class="relative flex-shrink-0 w-[80px] h-[60px] bg-gray-200 rounded overflow-hidden border border-gray-200 group">
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
                                                        class="relative flex-shrink-0 w-[80px] h-[60px] rounded overflow-hidden border border-gray-200 group cursor-pointer hover:ring-2 hover:ring-blue-400"
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
                                                    class="flex-shrink-0 w-[80px] h-[60px] border border-dashed border-gray-300 rounded flex flex-col items-center justify-center text-gray-400 hover:border-blue-300 hover:text-blue-500 transition-colors gap-0.5
                                                        {captureTargetInstanceId === instance.id ? 'bg-blue-50 border-blue-400 text-blue-600' : ''}"
                                                    on:click={() => startCapture(instance.id)}
                                                    title="캡처 추가"
                                                >
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" />
                                                    </svg>
                                                    <span class="text-[8px]">{captureTargetInstanceId === instance.id ? "선택 중..." : "캡처"}</span>
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

                                <!-- Empty Ticket: 새 항목 추가를 위한 빈 티켓 -->
                                {#if addingNewItemToCategoryId === category.id}
                                    <!-- 새 항목 추가 폼 (제목 + 설명) -->
                                    <div class="empty-ticket-area border-2 border-blue-400 rounded p-3 bg-blue-50">
                                        <div class="flex items-center gap-2 mb-3">
                                            <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                            </svg>
                                            <span class="text-sm font-medium text-blue-700">새 항목 추가</span>
                                        </div>
                                        <div class="space-y-2">
                                            <div>
                                                <input
                                                    type="text"
                                                    bind:value={newItemTitle}
                                                    class="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    placeholder="제목"
                                                />
                                            </div>
                                            <div>
                                                <input
                                                    type="text"
                                                    bind:value={newItemDescription}
                                                    class="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    placeholder="설명 (선택)"
                                                />
                                            </div>
                                            <div class="flex gap-2 justify-end pt-1">
                                                <button
                                                    class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700"
                                                    on:click={cancelAddNewItem}
                                                >
                                                    취소
                                                </button>
                                                <button
                                                    class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                                    on:click={confirmAddNewItem}
                                                    disabled={!newItemTitle.trim()}
                                                >
                                                    추가
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                {:else if editingEmptyCategoryId === category.id}
                                    <!-- Autocomplete 입력 모드 -->
                                    {@const filteredItems = getFilteredItems(category)}
                                    {@const showAddNew = emptyTicketSearchText.trim() && !hasExactMatch(category)}
                                    <div class="empty-ticket-area border-2 border-blue-400 rounded p-2 bg-white relative">
                                        <div class="flex items-center gap-2">
                                            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                            </svg>
                                            <input
                                                type="text"
                                                bind:value={emptyTicketSearchText}
                                                on:keydown={(e) => handleEmptyTicketKeydown(e, category.id)}
                                                class="flex-1 border-none outline-none text-xs bg-transparent"
                                                placeholder="항목 검색 또는 새로 입력..."
                                                autofocus
                                            />
                                            <button
                                                class="text-gray-400 hover:text-gray-600"
                                                on:click={cancelEmptyTicketEdit}
                                                title="닫기"
                                            >
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                </svg>
                                            </button>
                                        </div>

                                        <!-- 드롭다운 목록 -->
                                        <div class="mt-2 border-t border-gray-100 pt-2 max-h-[200px] overflow-y-auto">
                                            {#if filteredItems.length > 0}
                                                <div class="text-[10px] text-gray-400 px-1 mb-1">사용 가능한 항목</div>
                                                {#each filteredItems as item (item.id)}
                                                    <button
                                                        class="w-full text-left px-2 py-1.5 text-xs rounded hover:bg-blue-50 hover:text-blue-700 transition-colors"
                                                        on:click={() => {
                                                            addItemToCategory(category.id, item.id);
                                                            cancelEmptyTicketEdit();
                                                        }}
                                                    >
                                                        <div class="flex items-center gap-1.5">
                                                            <span class="font-medium">{item.title}</span>
                                                            {#if getItemUsageCount(category.id, item.id) > 0}
                                                                <span class="text-[9px] text-gray-400 bg-gray-100 px-1 py-0.5 rounded">총 {getItemUsageCount(category.id, item.id)}번 사용됨</span>
                                                            {/if}
                                                        </div>
                                                        {#if item.description}
                                                            <div class="text-[10px] text-gray-400 mt-0.5">{item.description}</div>
                                                        {/if}
                                                    </button>
                                                {/each}
                                            {:else if emptyTicketSearchText.trim()}
                                                <div class="text-[10px] text-gray-400 px-1 mb-1">매칭되는 항목 없음</div>
                                            {/if}

                                            <!-- 새 항목 추가 옵션 -->
                                            {#if showAddNew}
                                                <div class="border-t border-gray-100 mt-1 pt-1">
                                                    <button
                                                        class="w-full text-left px-2 py-1.5 text-xs rounded hover:bg-green-50 hover:text-green-700 transition-colors flex items-center gap-1.5"
                                                        on:click={() => startAddNewItem(category.id, emptyTicketSearchText.trim())}
                                                    >
                                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                        </svg>
                                                        <span>"{emptyTicketSearchText.trim()}" 새 항목으로 추가</span>
                                                    </button>
                                                </div>
                                            {/if}
                                        </div>
                                    </div>
                                {:else if availableItems.length > 0 || category.items.length === 0}
                                    <!-- 빈 티켓 (클릭하여 항목 추가) -->
                                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                                    <div
                                        class="empty-ticket-area border border-dashed border-gray-300 rounded p-2 bg-gray-50/50 cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-colors"
                                        on:click={() => startEmptyTicketEdit(category.id)}
                                    >
                                        <div class="flex items-center gap-2 text-gray-400">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v16m8-8H4" />
                                            </svg>
                                            <span class="text-xs">항목을 선택하거나 새로 입력...</span>
                                        </div>
                                    </div>
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

            <!-- 완료 버튼 -->
            {#if keyInfoSettings.categories.length > 0}
                <div class="pt-2 pb-1">
                    <button
                        class="w-full py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2
                               {keyInfoCompleted
                            ? 'bg-emerald-100 text-emerald-700 border border-emerald-300 hover:bg-white hover:text-gray-600 hover:border-gray-300'
                            : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm hover:shadow-md'}"
                        on:click={toggleCompleted}
                        disabled={togglingCompleted}
                    >
                        {#if togglingCompleted}
                            <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        {:else if keyInfoCompleted}
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                            </svg>
                            완료됨 (클릭하여 해제)
                        {:else}
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                            </svg>
                            완료
                        {/if}
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>

<!-- Activity Log Modal -->
<ActivityLogModal
    isOpen={showActivityLog}
    {keyInfoData}
    {keyInfoSettings}
    on:close={() => (showActivityLog = false)}
/>

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
