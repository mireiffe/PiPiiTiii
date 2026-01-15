<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";
    import type { PhenomenonData, CandidateCause, EvidenceLink, CauseImage } from "$lib/types/phenomenon";
    import { generateCauseImageId } from "$lib/types/phenomenon";
    import ImageModal from "./ImageModal.svelte";
    import CandidateCauseCard from "./CandidateCauseCard.svelte";
    import AttributeSelector from "./AttributeSelector.svelte";

    export let phenomenon: PhenomenonData;
    export let phenomenonAttributes: { key: string; name: string; value: string; source?: string }[] = [];

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
        evidenceHover: { evidenceId: string | null };
        linkingModeChange: { isLinking: boolean; causeId: string | null; linkedEvidenceIds: string[] };
    }>();

    let newCauseText = "";
    let isAddingCause = false;
    let activeCauseId: string | null = null;
    let editingCauseId: string | null = null;
    let editingCauseText: string = "";
    let expandedImagesCauseId: string | null = null;
    let selectedImage: CauseImage | null = null;
    let showImageModal = false;

    function getCauseEvidenceIds(cause: CandidateCause): string[] {
        if (cause.evidenceLinks) return cause.evidenceLinks.map((l) => l.evidenceId);
        return cause.evidenceIds || [];
    }

    function getCauseEvidenceLinks(cause: CandidateCause): EvidenceLink[] {
        if (cause.evidenceLinks) return cause.evidenceLinks;
        return (cause.evidenceIds || []).map((id) => ({ evidenceId: id, description: "" }));
    }

    // Emit linking mode change whenever activeCauseId changes
    $: {
        if (activeCauseId) {
            const cause = phenomenon.candidateCauses.find((c) => c.id === activeCauseId);
            if (cause) {
                dispatch("linkingModeChange", {
                    isLinking: true,
                    causeId: activeCauseId,
                    linkedEvidenceIds: getCauseEvidenceIds(cause),
                });
            } else {
                dispatch("linkingModeChange", { isLinking: false, causeId: null, linkedEvidenceIds: [] });
            }
        } else {
            dispatch("linkingModeChange", { isLinking: false, causeId: null, linkedEvidenceIds: [] });
        }
    }

    function startAddCause() {
        isAddingCause = true;
        newCauseText = "";
        activeCauseId = null;
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
        phenomenon.candidateCauses = [...(phenomenon.candidateCauses || []), newCause];
        dispatch("change", phenomenon);
        newCauseText = "";
        isAddingCause = false;
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
        phenomenon.candidateCauses = phenomenon.candidateCauses.filter((c) => c.id !== id);
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
        activeCauseId = activeCauseId === id ? null : id;
        if (activeCauseId) isAddingCause = false;
    }

    export function toggleEvidenceLink(evidenceId: string) {
        if (!activeCauseId) {
            alert("증거를 연결할 원인 후보를 먼저 선택하세요.");
            return;
        }
        const cause = phenomenon.candidateCauses.find((c) => c.id === activeCauseId);
        if (!cause) return;

        if (!cause.evidenceLinks) {
            cause.evidenceLinks = (cause.evidenceIds || []).map((eid) => ({ evidenceId: eid, description: "" }));
        }

        const existingIndex = cause.evidenceLinks.findIndex((l) => l.evidenceId === evidenceId);
        if (existingIndex >= 0) {
            cause.evidenceLinks.splice(existingIndex, 1);
        } else {
            cause.evidenceLinks.push({ evidenceId, description: "" });
        }
        cause.evidenceIds = cause.evidenceLinks.map((l) => l.evidenceId);
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    function toggleAttributeLink(attrKey: string) {
        toggleEvidenceLink(`attr:${attrKey}`);
    }

    function saveChanges() {
        dispatch("change", phenomenon);
    }

    function startEditCauseName(id: string, text: string) {
        editingCauseId = id;
        editingCauseText = text;
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

    // Image handling
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

        const isFirstImage = !cause.images || cause.images.length === 0;
        cause.images = [...(cause.images || []), newImage];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        expandedImagesCauseId = causeId;
        if (isFirstImage) openImageModal(newImage);
    }

    function toggleImagesExpand(causeId: string) {
        expandedImagesCauseId = expandedImagesCauseId === causeId ? null : causeId;
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

    // Get linked evidence IDs for active cause
    $: activeCauseEvidenceIds = (() => {
        if (!activeCauseId) return [];
        const cause = phenomenon.candidateCauses.find((c) => c.id === activeCauseId);
        return cause ? getCauseEvidenceIds(cause) : [];
    })();
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
                    <div class="text-center py-8 text-gray-400 text-xs border-2 border-dashed border-gray-200 rounded-lg">
                        등록된 원인 후보가 없습니다.<br />
                        새로운 후보를 추가해보세요.
                    </div>
                {/if}
            {:else}
                {#each phenomenon.candidateCauses as cause (cause.id)}
                    <CandidateCauseCard
                        {cause}
                        isActive={activeCauseId === cause.id}
                        evidenceLinks={getCauseEvidenceLinks(cause)}
                        {expandedImagesCauseId}
                        {editingCauseId}
                        {editingCauseText}
                        phenomenonEvidences={phenomenon.evidences}
                        {phenomenonAttributes}
                        on:toggleActive={(e) => toggleActiveCause(e.detail.id)}
                        on:startEdit={(e) => startEditCauseName(e.detail.id, e.detail.text)}
                        on:saveEdit={saveEditCauseName}
                        on:cancelEdit={cancelEditCauseName}
                        on:remove={(e) => removeCause(e.detail.id)}
                        on:updateNotes={(e) => updateCauseNotes(e.detail.id, e.detail.notes)}
                        on:saveChanges={saveChanges}
                        on:paste={(e) => handlePaste(e.detail.e, e.detail.causeId)}
                        on:toggleImagesExpand={(e) => toggleImagesExpand(e.detail.causeId)}
                        on:openImageModal={(e) => openImageModal(e.detail.image)}
                        on:closeImagesExpand={() => expandedImagesCauseId = null}
                        on:toggleEvidenceLink={(e) => toggleEvidenceLink(e.detail.evidenceId)}
                    />
                {/each}
            {/if}

            {#if isAddingCause}
                <div class="bg-white border border-blue-200 rounded-lg p-3 shadow-sm" transition:slide>
                    <input
                        type="text"
                        bind:value={newCauseText}
                        placeholder="새로운 원인 후보 입력..."
                        class="w-full text-sm border-b border-gray-200 focus:border-blue-500 focus:outline-none py-1 mb-2"
                        on:keydown={handleKeyDown}
                        autoFocus
                    />
                    <div class="flex justify-end gap-2 text-xs">
                        <button class="px-2 py-1 text-gray-500 hover:text-gray-700" on:click={cancelAddCause}>취소</button>
                        <button class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 font-medium" on:click={saveNewCause}>저장</button>
                    </div>
                </div>
            {/if}
        </div>

        <!-- 하단: 속성 추가 영역 (활성화된 원인이 있을 때만 표시) -->
        {#if activeCauseId}
            <AttributeSelector
                {phenomenonAttributes}
                linkedEvidenceIds={activeCauseEvidenceIds}
                on:toggleAttribute={(e) => toggleAttributeLink(e.detail.key)}
            />
        {/if}

        <!-- 하단: 추가 버튼 -->
        {#if !isAddingCause && !activeCauseId}
            <div class="p-4 border-t border-gray-200 bg-white">
                <button
                    class="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
                    on:click={startAddCause}
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
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
