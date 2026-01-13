<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import { slide } from "svelte/transition";
    import type {
        PhenomenonData,
        CandidateCause,
        Evidence,
        EvidenceLink,
        CauseImage,
    } from "$lib/types/phenomenon";
    import { EVIDENCE_COLORS, generateCauseImageId } from "$lib/types/phenomenon";
    import ImageModal from "./ImageModal.svelte";

    export let phenomenon: PhenomenonData;
    export let phenomenonAttributes: {
        key: string;
        name: string;
        value: string;
        source?: string;
    }[] = [];

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
        evidenceHover: { evidenceId: string | null };
        linkingModeChange: {
            isLinking: boolean;
            causeId: string | null;
            linkedEvidenceIds: string[];
        };
    }>();

    let newCauseText = "";
    let isAddingCause = false;
    let activeCauseId: string | null = null;
    let editingDescriptionId: string | null = null; // Evidence ID being described
    let editingCauseId: string | null = null; // Cause ID being renamed
    let editingCauseText: string = ""; // Temporary text during edit

    // Image related state
    let expandedImagesCauseId: string | null = null; // Which cause's images are expanded
    let selectedImage: CauseImage | null = null; // Image for modal view
    let showImageModal = false;

    // Helper to get evidence IDs from a cause (handling both legacy and new structure)
    function getCauseEvidenceIds(cause: CandidateCause): string[] {
        if (cause.evidenceLinks) {
            return cause.evidenceLinks.map((l) => l.evidenceId);
        }
        return cause.evidenceIds || [];
    }

    function getCauseEvidenceLinks(cause: CandidateCause): EvidenceLink[] {
        if (cause.evidenceLinks) return cause.evidenceLinks;
        // Migrate legacy IDs to links
        return (cause.evidenceIds || []).map((id) => ({
            evidenceId: id,
            description: "",
        }));
    }

    // Emit linking mode change whenever activeCauseId or its evidence changes
    $: {
        if (activeCauseId) {
            const cause = phenomenon.candidateCauses.find(
                (c) => c.id === activeCauseId,
            );
            if (cause) {
                dispatch("linkingModeChange", {
                    isLinking: true,
                    causeId: activeCauseId,
                    linkedEvidenceIds: getCauseEvidenceIds(cause),
                });
            } else {
                dispatch("linkingModeChange", {
                    isLinking: false,
                    causeId: null,
                    linkedEvidenceIds: [],
                });
            }
        } else {
            dispatch("linkingModeChange", {
                isLinking: false,
                causeId: null,
                linkedEvidenceIds: [],
            });
        }
    }

    function startAddCause() {
        isAddingCause = true;
        newCauseText = "";
        activeCauseId = null; // Exit linking mode when adding new cause
    }

    function cancelAddCause() {
        isAddingCause = false;
        newCauseText = "";
    }

    function saveNewCause() {
        if (!newCauseText.trim()) return;

        const newCause: CandidateCause = {
            id: `cause_${Date.now()}`,
            text: newCauseText.trim(),
            evidenceIds: [],
            evidenceLinks: [],
            createdAt: new Date().toISOString(),
        };

        phenomenon.candidateCauses = [
            ...(phenomenon.candidateCauses || []),
            newCause,
        ];
        dispatch("change", phenomenon);

        newCauseText = "";
        isAddingCause = false;

        // Auto-select the new cause for linking
        toggleActiveCause(newCause.id);
    }

    function handleKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            saveNewCause();
        } else if (e.key === "Escape") {
            cancelAddCause();
        }
    }

    function removeCause(id: string) {
        if (!confirm("이 원인 후보를 삭제하시겠습니까?")) return;
        phenomenon.candidateCauses = phenomenon.candidateCauses.filter(
            (c) => c.id !== id,
        );
        if (activeCauseId === id) activeCauseId = null;
        dispatch("change", phenomenon);
    }

    function updateCauseText(id: string, text: string) {
        const cause = phenomenon.candidateCauses.find((c) => c.id === id);
        if (cause) {
            cause.text = text;
            phenomenon.candidateCauses = [...phenomenon.candidateCauses];
            dispatch("change", phenomenon);
        }
    }

    function updateCauseNotes(id: string, notes: string) {
        const cause = phenomenon.candidateCauses.find((c) => c.id === id);
        if (cause) {
            cause.notes = notes;
            phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        }
    }

    function toggleActiveCause(id: string) {
        if (activeCauseId === id) {
            activeCauseId = null;
        } else {
            activeCauseId = id;
            isAddingCause = false;
        }
    }

    // Called by parent (WorkflowSection) when canvas evidence is clicked
    export function toggleEvidenceLink(evidenceId: string) {
        if (!activeCauseId) {
            // If no cause is active, maybe prompt user to select one?
            // For now, ignore or flash UI.
            alert("증거를 연결할 원인 후보를 먼저 선택하세요.");
            return;
        }

        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause) return;

        // Ensure evidenceLinks exists
        if (!cause.evidenceLinks) {
            cause.evidenceLinks = (cause.evidenceIds || []).map((eid) => ({
                evidenceId: eid,
                description: "",
            }));
        }

        const existingIndex = cause.evidenceLinks.findIndex(
            (l) => l.evidenceId === evidenceId,
        );

        if (existingIndex >= 0) {
            // Remove
            cause.evidenceLinks.splice(existingIndex, 1);
        } else {
            // Add
            cause.evidenceLinks.push({ evidenceId, description: "" });
        }

        // Sync legacy id list for compat
        cause.evidenceIds = cause.evidenceLinks.map((l) => l.evidenceId);

        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    // Toggle Attribute Evidence (generated ID logic)
    function toggleAttributeLink(attrKey: string) {
        if (!activeCauseId) return;
        const attrId = `attr:${attrKey}`;
        toggleEvidenceLink(attrId);
    }

    function getEvidenceFromId(
        id: string,
    ): { type: "capture" | "attribute"; data: any } | null {
        if (id.startsWith("attr:")) {
            const key = id.split(":")[1];
            const attr = phenomenonAttributes.find((a) => a.key === key);
            if (attr) return { type: "attribute", data: attr };
        } else {
            const ev = phenomenon.evidences.find((e) => e.id === id);
            if (ev) return { type: "capture", data: ev };
        }
        return null;
    }

    function getCaptureColor(evidence: any) {
        const idx = phenomenon.evidences.findIndex((e) => e.id === evidence.id);
        if (idx !== -1) return EVIDENCE_COLORS[idx % EVIDENCE_COLORS.length];
        return EVIDENCE_COLORS[0];
    }

    function saveChanges() {
        dispatch("change", phenomenon);
    }

    function startEditCauseName(id: string, currentText: string) {
        editingCauseId = id;
        editingCauseText = currentText;
    }

    function cancelEditCauseName() {
        editingCauseId = null;
        editingCauseText = "";
    }

    function saveEditCauseName() {
        if (!editingCauseId || !editingCauseText.trim()) {
            cancelEditCauseName();
            return;
        }

        updateCauseText(editingCauseId, editingCauseText.trim());
        cancelEditCauseName();
    }

    function handleCauseNameKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            saveEditCauseName();
        } else if (e.key === "Escape") {
            cancelEditCauseName();
        }
    }

    // ===== Image handling functions =====

    // Handle paste event for images
    function handlePaste(e: ClipboardEvent, causeId: string) {
        const items = e.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        const imageData = event.target?.result as string;
                        addImageToCause(causeId, imageData);
                    };
                    reader.readAsDataURL(file);
                }
                break;
            }
        }
    }

    function addImageToCause(causeId: string, imageData: string) {
        const cause = phenomenon.candidateCauses.find((c) => c.id === causeId);
        if (!cause) return;

        const newImage: CauseImage = {
            id: generateCauseImageId(),
            data: imageData,
            createdAt: new Date().toISOString(),
        };

        if (!cause.images) {
            cause.images = [];
        }
        cause.images = [...cause.images, newImage];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);

        // Auto-expand images section
        expandedImagesCauseId = causeId;
    }

    function toggleImagesExpand(causeId: string) {
        if (expandedImagesCauseId === causeId) {
            expandedImagesCauseId = null;
        } else {
            expandedImagesCauseId = causeId;
        }
    }

    function openImageModal(image: CauseImage) {
        selectedImage = image;
        showImageModal = true;
    }

    function closeImageModal() {
        showImageModal = false;
        selectedImage = null;
    }

    function handleUpdateImageCaption(event: CustomEvent<{ id: string; caption: string }>) {
        const { id, caption } = event.detail;
        for (const cause of phenomenon.candidateCauses) {
            if (cause.images) {
                const img = cause.images.find((i) => i.id === id);
                if (img) {
                    img.caption = caption;
                    phenomenon.candidateCauses = [...phenomenon.candidateCauses];
                    dispatch("change", phenomenon);
                    // Update selectedImage to reflect changes
                    if (selectedImage && selectedImage.id === id) {
                        selectedImage = { ...selectedImage, caption };
                    }
                    break;
                }
            }
        }
    }

    function handleDeleteImage(event: CustomEvent<{ id: string }>) {
        const { id } = event.detail;
        for (const cause of phenomenon.candidateCauses) {
            if (cause.images) {
                const idx = cause.images.findIndex((i) => i.id === id);
                if (idx !== -1) {
                    cause.images.splice(idx, 1);
                    phenomenon.candidateCauses = [...phenomenon.candidateCauses];
                    dispatch("change", phenomenon);
                    closeImageModal();
                    break;
                }
            }
        }
    }

    function getImageCount(cause: CandidateCause): number {
        return cause.images?.length || 0;
    }
</script>

<div class="flex flex-col h-full bg-gray-50/50">
    <!-- 헤더 -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-orange-500"></div>
            <h2 class="text-sm font-semibold text-gray-800">원인후보 탐색</h2>
        </div>
        <p class="text-xs text-gray-500 mt-1">
            원인 후보를 선택하여 우측 캡처나 속성을 근거로 연결하세요.
        </p>
    </div>

    <div class="flex-1 flex flex-col min-h-0">
        <!-- 상단: 원인 후보 목록 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
            {#if !phenomenon.candidateCauses || phenomenon.candidateCauses.length === 0}
                {#if !isAddingCause}
                    <div
                        class="text-center py-8 text-gray-400 text-xs text-center border-2 border-dashed border-gray-200 rounded-lg"
                    >
                        등록된 원인 후보가 없습니다.<br />
                        새로운 후보를 추가해보세요.
                    </div>
                {/if}
            {:else}
                {#each phenomenon.candidateCauses as cause (cause.id)}
                    {@const isActive = activeCauseId === cause.id}
                    {@const links = getCauseEvidenceLinks(cause)}

                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div
                        class="bg-white border rounded-lg shadow-sm transition-all duration-200 cursor-pointer text-left
                               {isActive
                            ? 'border-blue-500 ring-1 ring-blue-500 shadow-md'
                            : 'border-gray-200 hover:border-gray-300'}"
                        on:click={() => toggleActiveCause(cause.id)}
                    >
                        <!-- Card Header -->
                        <div class="p-3">
                            <div class="flex items-start gap-2">
                                <div class="mt-0.5">
                                    <div
                                        class="w-3 h-3 rounded-full border border-gray-300 flex items-center justify-center {isActive
                                            ? 'bg-blue-500 border-blue-500'
                                            : 'bg-white'}"
                                    >
                                        {#if isActive}
                                            <div
                                                class="w-1 h-1 bg-white rounded-full"
                                            ></div>
                                        {/if}
                                    </div>
                                </div>

                                <div class="flex-1 min-w-0">
                                    {#if editingCauseId === cause.id}
                                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                                        <input
                                            type="text"
                                            bind:value={editingCauseText}
                                            class="w-full font-medium text-sm text-gray-800 border border-blue-500 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 mb-1"
                                            on:keydown={handleCauseNameKeyDown}
                                            on:blur={saveEditCauseName}
                                            on:click|stopPropagation
                                            autofocus
                                        />
                                    {:else}
                                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                                        <div
                                            class="font-medium text-sm text-gray-800 break-words mb-1 hover:bg-gray-50 rounded px-1 py-0.5 -mx-1 cursor-text transition-colors"
                                            on:click|stopPropagation={() =>
                                                startEditCauseName(
                                                    cause.id,
                                                    cause.text,
                                                )}
                                            title="클릭하여 수정"
                                        >
                                            {cause.text}
                                        </div>
                                    {/if}
                                    <div class="text-[10px] text-gray-400 flex items-center gap-2">
                                        {#if links.length === 0}
                                            <span>연결된 근거 없음</span>
                                        {:else}
                                            <span>근거 {links.length}개</span>
                                        {/if}
                                        {#if getImageCount(cause) > 0}
                                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                                            <span
                                                class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded cursor-pointer hover:bg-purple-100 transition-colors"
                                                on:click|stopPropagation={() => toggleImagesExpand(cause.id)}
                                                title="이미지 보기"
                                            >
                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                </svg>
                                                {getImageCount(cause)}
                                            </span>
                                        {/if}
                                    </div>
                                </div>

                                <button
                                    class="text-gray-400 hover:text-red-500 p-1 rounded-md hover:bg-gray-100 transition-colors"
                                    on:click|stopPropagation={() =>
                                        removeCause(cause.id)}
                                    title="삭제"
                                >
                                    <svg
                                        class="w-3.5 h-3.5"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M6 18L18 6M6 6l12 12"
                                        />
                                    </svg>
                                </button>
                            </div>

                            <!-- Notes textarea for active cause -->
                            {#if isActive}
                                <div class="mt-3 pt-3 border-t border-gray-100">
                                    <textarea
                                        class="w-full text-xs bg-white border border-gray-200 rounded p-2 focus:border-blue-500 focus:outline-none resize-none placeholder-gray-400"
                                        placeholder="이 원인 후보에 대한 설명을 입력하세요..."
                                        rows="3"
                                        value={cause.notes || ""}
                                        on:input={(e) =>
                                            updateCauseNotes(
                                                cause.id,
                                                e.currentTarget.value,
                                            )}
                                        on:blur={saveChanges}
                                        on:click|stopPropagation
                                    ></textarea>

                                    <!-- Image paste zone -->
                                    <div
                                        class="mt-2 p-2 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50/50 text-center transition-colors hover:border-purple-300 hover:bg-purple-50/30 focus-within:border-purple-400"
                                        role="button"
                                        tabindex="0"
                                        on:paste={(e) => handlePaste(e, cause.id)}
                                        on:click|stopPropagation
                                        on:keydown|stopPropagation
                                    >
                                        <div class="flex items-center justify-center gap-1.5 text-xs text-gray-400">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                            </svg>
                                            <span>클릭 후 Ctrl+V로 이미지 붙여넣기</span>
                                        </div>
                                    </div>
                                </div>
                            {/if}

                            <!-- Expanded images section -->
                            {#if expandedImagesCauseId === cause.id && cause.images && cause.images.length > 0}
                                <div
                                    class="border-t border-gray-100 bg-purple-50/30 p-2"
                                    transition:slide
                                    on:click|stopPropagation
                                >
                                    <div class="flex items-center justify-between mb-2">
                                        <span class="text-[10px] font-bold text-purple-600 uppercase">첨부 이미지 ({cause.images.length})</span>
                                        <button
                                            class="text-gray-400 hover:text-gray-600 p-0.5"
                                            on:click|stopPropagation={() => expandedImagesCauseId = null}
                                        >
                                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                            </svg>
                                        </button>
                                    </div>
                                    <div class="grid grid-cols-4 gap-1.5">
                                        {#each cause.images as img (img.id)}
                                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                                            <div
                                                class="relative aspect-square bg-white rounded border border-gray-200 overflow-hidden cursor-pointer hover:border-purple-400 hover:shadow-sm transition-all group"
                                                on:click|stopPropagation={() => openImageModal(img)}
                                            >
                                                <img
                                                    src={img.data}
                                                    alt={img.caption || '첨부 이미지'}
                                                    class="w-full h-full object-cover"
                                                />
                                                {#if img.caption}
                                                    <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[8px] px-1 py-0.5 truncate">
                                                        {img.caption}
                                                    </div>
                                                {/if}
                                                <div class="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/10 transition-colors"></div>
                                            </div>
                                        {/each}
                                    </div>
                                </div>
                            {/if}
                        </div>

                        <!-- Linked Evidences List (Expand only when active or always? Let's show always but brief if not active) -->
                        {#if isActive && links.length > 0}
                            <div
                                class="border-t border-gray-100 bg-gray-50/50 p-2 space-y-2"
                            >
                                {#each links as link (link.evidenceId)}
                                    {@const evidenceInfo = getEvidenceFromId(
                                        link.evidenceId,
                                    )}
                                    {#if evidenceInfo}
                                        <div
                                            class="bg-white border border-gray-200 rounded p-2 text-xs shadow-sm"
                                        >
                                            <!-- Evidence Label -->
                                            <div
                                                class="flex items-center gap-1.5"
                                            >
                                                {#if evidenceInfo.type === "capture"}
                                                    <div
                                                        class="w-2 h-2 rounded-full"
                                                        style="background-color: {getCaptureColor(
                                                            evidenceInfo.data,
                                                        ).border}"
                                                    ></div>
                                                    <span
                                                        class="font-medium text-gray-700 truncate"
                                                        >{evidenceInfo.data
                                                            .label ||
                                                            "캡처"}</span
                                                    >
                                                {:else}
                                                    <svg
                                                        class="w-3 h-3 text-blue-500"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            stroke-linecap="round"
                                                            stroke-linejoin="round"
                                                            stroke-width="2"
                                                            d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                                                        />
                                                    </svg>
                                                    <span
                                                        class="font-medium text-gray-700 truncate"
                                                        >{evidenceInfo.data
                                                            .name}</span
                                                    >
                                                {/if}
                                                <button
                                                    class="ml-auto text-gray-400 hover:text-red-500"
                                                    on:click|stopPropagation={() =>
                                                        toggleEvidenceLink(
                                                            link.evidenceId,
                                                        )}
                                                >
                                                    <svg
                                                        class="w-3 h-3"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            stroke-linecap="round"
                                                            stroke-linejoin="round"
                                                            stroke-width="2"
                                                            d="M6 18L18 6M6 6l12 12"
                                                        />
                                                    </svg>
                                                </button>
                                            </div>
                                        </div>
                                    {:else}
                                        <!-- Evidence not found (maybe deleted?) -->
                                    {/if}
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/each}
            {/if}

            {#if isAddingCause}
                <div
                    class="bg-white border border-blue-200 rounded-lg p-3 shadow-sm"
                    transition:slide
                >
                    <input
                        type="text"
                        bind:value={newCauseText}
                        placeholder="새로운 원인 후보 입력..."
                        class="w-full text-sm border-b border-gray-200 focus:border-blue-500 focus:outline-none py-1 mb-2"
                        on:keydown={handleKeyDown}
                        autoFocus
                    />
                    <div class="flex justify-end gap-2 text-xs">
                        <button
                            class="px-2 py-1 text-gray-500 hover:text-gray-700"
                            on:click={cancelAddCause}>취소</button
                        >
                        <button
                            class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 font-medium"
                            on:click={saveNewCause}>저장</button
                        >
                    </div>
                </div>
            {/if}
        </div>

        <!-- 하단: 속성 추가 영역 (활성화된 원인이 있을 때만 표시) -->
        {#if activeCauseId}
            <div class="border-t border-gray-200 bg-white" transition:slide>
                <div
                    class="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between"
                >
                    <span class="text-xs font-bold text-gray-500 uppercase"
                        >속성 추가하기</span
                    >
                </div>
                <div
                    class="max-h-48 overflow-y-auto p-2 grid grid-cols-2 gap-2"
                >
                    {#each phenomenonAttributes as attr}
                        {@const attrId = `attr:${attr.key}`}
                        {@const cause = phenomenon.candidateCauses.find(
                            (c) => c.id === activeCauseId,
                        )}
                        {@const isLinked =
                            cause &&
                            getCauseEvidenceIds(cause).includes(attrId)}

                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="px-2 py-1.5 rounded border text-xs cursor-pointer flex items-center gap-1.5 transition-colors
                                   {isLinked
                                ? 'bg-blue-50 border-blue-200 text-blue-700'
                                : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}"
                            on:click={() => toggleAttributeLink(attr.key)}
                        >
                            <svg
                                class="w-3 h-3 flex-shrink-0"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                                />
                            </svg>
                            <span
                                class="truncate"
                                title="{attr.name}: {attr.value}"
                                >{attr.name}: {attr.value}</span
                            >
                        </div>
                    {/each}
                    {#if phenomenonAttributes.length === 0}
                        <div
                            class="col-span-2 text-center text-xs text-gray-400 py-2"
                        >
                            사용 가능한 속성이 없습니다.
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- 하단: 추가 버튼 -->
        {#if !isAddingCause && !activeCauseId}
            <div class="p-4 border-t border-gray-200 bg-white">
                <button
                    class="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
                    on:click={startAddCause}
                >
                    <svg
                        class="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 4v16m8-8H4"
                        />
                    </svg>
                    원인 후보 추가
                </button>
            </div>
        {/if}
    </div>
</div>

<!-- Image Modal -->
{#if selectedImage}
    <ImageModal
        image={selectedImage}
        isOpen={showImageModal}
        on:close={closeImageModal}
        on:updateCaption={handleUpdateImageCaption}
        on:delete={handleDeleteImage}
    />
{/if}
