<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import type { Evidence, CaptureEvidence, AttributeEvidence } from '$lib/types/phenomenon';

    export let evidence: Evidence;
    export let color: { bg: string; border: string; name: string } | undefined = undefined;
    export let index: number | undefined = undefined;

    const dispatch = createEventDispatcher<{
        delete: void;
        updateLabel: string;
        updateDescription: string;
        mouseenter: void;
        mouseleave: void;
    }>();

    let isEditingLabel = false;
    let labelInput: HTMLInputElement;
    let editingLabelValue = '';

    let isEditingDescription = false;
    let descriptionInput: HTMLTextAreaElement;
    let editingDescriptionValue = '';

    function startEditLabel() {
        if (evidence.type === 'capture') {
            editingLabelValue = evidence.label || '';
            isEditingLabel = true;
            setTimeout(() => labelInput?.focus(), 0);
        }
    }

    function saveLabel() {
        dispatch('updateLabel', editingLabelValue);
        isEditingLabel = false;
    }

    function cancelEdit() {
        isEditingLabel = false;
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            saveLabel();
        } else if (e.key === 'Escape') {
            cancelEdit();
        }
    }

    function startEditDescription() {
        if (evidence.type === 'capture') {
            editingDescriptionValue = evidence.description || '';
            isEditingDescription = true;
            setTimeout(() => descriptionInput?.focus(), 0);
        }
    }

    function saveDescription() {
        dispatch('updateDescription', editingDescriptionValue);
        isEditingDescription = false;
    }

    function cancelEditDescription() {
        isEditingDescription = false;
    }

    function handleDescriptionKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveDescription();
        } else if (e.key === 'Escape') {
            cancelEditDescription();
        }
    }

    // 타입 가드
    function isCaptureEvidence(e: Evidence): e is CaptureEvidence {
        return e.type === 'capture';
    }

    function isAttributeEvidence(e: Evidence): e is AttributeEvidence {
        return e.type === 'attribute';
    }
</script>

<div
    class="group relative bg-white border rounded-lg p-2 transition-all hover:shadow-sm"
    style={color ? `border-color: ${color.border}20; background: ${color.bg.replace('0.2', '0.05')};` : ''}
    role="listitem"
    on:mouseenter={() => dispatch('mouseenter')}
    on:mouseleave={() => dispatch('mouseleave')}
>
    {#if isCaptureEvidence(evidence)}
        <!-- 캡처 증거 카드 -->
        <div class="flex items-start gap-2">
            <!-- 색상 인덱스 배지 -->
            {#if index !== undefined && color}
                <div
                    class="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold text-white"
                    style="background-color: {color.border};"
                >
                    {index + 1}
                </div>
            {/if}

            <div class="flex-1 min-w-0">
                <!-- 라벨 (편집 가능) -->
                {#if isEditingLabel}
                    <input
                        bind:this={labelInput}
                        bind:value={editingLabelValue}
                        on:blur={saveLabel}
                        on:keydown={handleKeydown}
                        class="w-full px-1 py-0.5 text-xs border border-blue-400 rounded focus:outline-none"
                        placeholder="라벨 입력..."
                    />
                {:else}
                    <button
                        class="text-xs font-medium text-gray-700 hover:text-blue-600 cursor-pointer text-left"
                        on:click={startEditLabel}
                    >
                        {evidence.label || `캡처 #${(index ?? 0) + 1}`}
                        <span class="text-gray-400 ml-1 text-[10px]">(클릭하여 편집)</span>
                    </button>
                {/if}

                <!-- 캡처 정보 -->
                <div class="mt-1 text-[10px] text-gray-500 flex flex-wrap gap-x-2">
                    <span>슬라이드 {evidence.slideIndex + 1}</span>
                    <span>{Math.round(evidence.width)} x {Math.round(evidence.height)}</span>
                    <span>({Math.round(evidence.x)}, {Math.round(evidence.y)})</span>
                </div>

                <!-- 설명 입력란 -->
                <div class="mt-2">
                    {#if isEditingDescription}
                        <textarea
                            bind:this={descriptionInput}
                            bind:value={editingDescriptionValue}
                            on:blur={saveDescription}
                            on:keydown={handleDescriptionKeydown}
                            class="w-full px-2 py-1 text-xs border border-blue-400 rounded resize-none focus:outline-none"
                            placeholder="설명 입력..."
                            rows="2"
                        ></textarea>
                    {:else}
                        <button
                            class="w-full text-left text-xs text-gray-500 hover:text-blue-600 cursor-pointer px-2 py-1 rounded hover:bg-gray-50"
                            on:click={startEditDescription}
                        >
                            {#if evidence.description}
                                <span class="text-gray-600">{evidence.description}</span>
                            {:else}
                                <span class="italic text-gray-400">+ 설명 추가</span>
                            {/if}
                        </button>
                    {/if}
                </div>
            </div>

            <!-- 삭제 버튼 -->
            <button
                class="flex-shrink-0 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                on:click={() => dispatch('delete')}
                title="삭제"
            >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

    {:else if isAttributeEvidence(evidence)}
        <!-- 속성 증거 카드 -->
        <div class="flex items-start gap-2">
            <!-- 태그 아이콘 -->
            <div class="flex-shrink-0 w-5 h-5 rounded bg-purple-100 flex items-center justify-center">
                <svg class="w-3 h-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
            </div>

            <div class="flex-1 min-w-0">
                <div class="text-xs">
                    <span class="font-medium text-gray-700">{evidence.name}</span>
                    <span class="text-gray-500">:</span>
                    <span class="text-gray-600 ml-1">{evidence.value}</span>
                </div>
                {#if evidence.source}
                    <div class="mt-0.5 text-[10px] text-gray-400">
                        출처: {evidence.source}
                    </div>
                {/if}
            </div>

            <!-- 삭제 버튼 -->
            <button
                class="flex-shrink-0 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-all"
                on:click={() => dispatch('delete')}
                title="삭제"
            >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    {/if}
</div>
