<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";
    import type { CandidateCause, Evidence, EvidenceLink, CauseImage } from "$lib/types/phenomenon";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";

    export let cause: CandidateCause;
    export let isActive: boolean;
    export let evidenceLinks: EvidenceLink[];
    export let expandedImagesCauseId: string | null;
    export let editingCauseId: string | null;
    export let editingCauseText: string;
    export let phenomenonEvidences: Evidence[] = [];
    export let phenomenonAttributes: { key: string; name: string; value: string; source?: string }[] = [];

    const dispatch = createEventDispatcher<{
        toggleActive: { id: string };
        startEdit: { id: string; text: string };
        saveEdit: void;
        cancelEdit: void;
        remove: { id: string };
        updateNotes: { id: string; notes: string };
        saveChanges: void;
        paste: { e: ClipboardEvent; causeId: string };
        toggleImagesExpand: { causeId: string };
        openImageModal: { image: CauseImage };
        closeImagesExpand: void;
        toggleEvidenceLink: { evidenceId: string };
    }>();

    function handleCauseNameKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            dispatch("saveEdit");
        } else if (e.key === "Escape") {
            dispatch("cancelEdit");
        }
    }

    function getEvidenceFromId(id: string): { type: "capture" | "attribute"; data: any } | null {
        if (id.startsWith("attr:")) {
            const key = id.split(":")[1];
            const attr = phenomenonAttributes.find((a) => a.key === key);
            if (attr) return { type: "attribute", data: attr };
        } else {
            const ev = phenomenonEvidences.find((e) => e.id === id);
            if (ev) return { type: "capture", data: ev };
        }
        return null;
    }

    function getCaptureColor(evidence: any) {
        const idx = phenomenonEvidences.findIndex((e) => e.id === evidence.id);
        if (idx !== -1) return EVIDENCE_COLORS[idx % EVIDENCE_COLORS.length];
        return EVIDENCE_COLORS[0];
    }

    function getImageCount(cause: CandidateCause): number {
        return cause.images?.length || 0;
    }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="bg-white border rounded-lg shadow-sm transition-all duration-200 cursor-pointer text-left
           {isActive ? 'border-blue-500 ring-1 ring-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-300'}"
    on:click={() => dispatch("toggleActive", { id: cause.id })}
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
                        <div class="w-1 h-1 bg-white rounded-full"></div>
                    {/if}
                </div>
            </div>

            <div class="flex-1 min-w-0">
                {#if editingCauseId === cause.id}
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <input
                        type="text"
                        value={editingCauseText}
                        on:input={(e) => dispatch("startEdit", { id: cause.id, text: e.currentTarget.value })}
                        class="w-full font-medium text-sm text-gray-800 border border-blue-500 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 mb-1"
                        on:keydown={handleCauseNameKeyDown}
                        on:blur={() => dispatch("saveEdit")}
                        on:click|stopPropagation
                        autofocus
                    />
                {:else}
                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                    <div
                        class="font-medium text-sm text-gray-800 break-words mb-1 hover:bg-gray-50 rounded px-1 py-0.5 -mx-1 cursor-text transition-colors"
                        on:click|stopPropagation={() => dispatch("startEdit", { id: cause.id, text: cause.text })}
                        title="클릭하여 수정"
                    >
                        {cause.text}
                    </div>
                {/if}
                <div class="text-[10px] text-gray-400 flex items-center gap-2">
                    {#if evidenceLinks.length === 0}
                        <span>연결된 근거 없음</span>
                    {:else}
                        <span>근거 {evidenceLinks.length}개</span>
                    {/if}
                    {#if getImageCount(cause) > 0}
                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <span
                            class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded cursor-pointer hover:bg-purple-100 transition-colors"
                            on:click|stopPropagation={() => dispatch("toggleImagesExpand", { causeId: cause.id })}
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
                on:click|stopPropagation={() => dispatch("remove", { id: cause.id })}
                title="삭제"
            >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
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
                    on:input={(e) => dispatch("updateNotes", { id: cause.id, notes: e.currentTarget.value })}
                    on:blur={() => dispatch("saveChanges")}
                    on:click|stopPropagation
                ></textarea>

                <!-- Image paste zone -->
                <div
                    class="mt-2 p-2 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50/50 text-center transition-colors hover:border-purple-300 hover:bg-purple-50/30 focus-within:border-purple-400"
                    role="button"
                    tabindex="0"
                    on:paste={(e) => dispatch("paste", { e, causeId: cause.id })}
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
            <div class="border-t border-gray-100 bg-purple-50/30 p-2" transition:slide on:click|stopPropagation>
                <div class="flex items-center justify-between mb-2">
                    <span class="text-[10px] font-bold text-purple-600 uppercase">첨부 이미지 ({cause.images.length})</span>
                    <button
                        class="text-gray-400 hover:text-gray-600 p-0.5"
                        on:click|stopPropagation={() => dispatch("closeImagesExpand")}
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
                            on:click|stopPropagation={() => dispatch("openImageModal", { image: img })}
                        >
                            <img src={img.data} alt={img.caption || '첨부 이미지'} class="w-full h-full object-cover" />
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

    <!-- Linked Evidences List -->
    {#if isActive && evidenceLinks.length > 0}
        <div class="border-t border-gray-100 bg-gray-50/50 p-2 space-y-2">
            {#each evidenceLinks as link (link.evidenceId)}
                {@const evidenceInfo = getEvidenceFromId(link.evidenceId)}
                {#if evidenceInfo}
                    <div class="bg-white border border-gray-200 rounded p-2 text-xs shadow-sm">
                        <div class="flex items-center gap-1.5">
                            {#if evidenceInfo.type === "capture"}
                                <div
                                    class="w-2 h-2 rounded-full"
                                    style="background-color: {getCaptureColor(evidenceInfo.data).border}"
                                ></div>
                                <span class="font-medium text-gray-700 truncate">{evidenceInfo.data.label || "캡처"}</span>
                            {:else}
                                <svg class="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                                </svg>
                                <span class="font-medium text-gray-700 truncate">{evidenceInfo.data.name}</span>
                            {/if}
                            <button
                                class="ml-auto text-gray-400 hover:text-red-500"
                                on:click|stopPropagation={() => dispatch("toggleEvidenceLink", { evidenceId: link.evidenceId })}
                            >
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>
                {/if}
            {/each}
        </div>
    {/if}
</div>
