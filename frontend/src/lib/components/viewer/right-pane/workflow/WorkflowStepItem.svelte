<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        StepAttachment,
    } from "$lib/types/workflow";
    import { getAttachmentImageUrl } from "$lib/api/project";

    export let step: WorkflowStepInstance;
    export let index: number;
    export let stepDef: WorkflowStepRow | undefined;
    export let color: { border: string; bg: string };
    export let workflowSteps: WorkflowSteps;
    export let isExpanded = false;
    export let isCapturing = false;
    export let isAddingAttachment = false;
    export let isBeingDragged = false;
    export let showDropIndicatorTop = false;
    export let showDropIndicatorBottom = false;
    export let isLastStep = false;
    export let attachmentTextInput = "";
    export let isSelected = false;
    export let showSelectionCheckbox = false;
    export let hideBadge = false;  // Hide the step number badge
    export let supportIndicator = false;  // Show support indicator (this step supports another)
    export let phaseColor: string | undefined = undefined;  // Phase color for supporter
    export let phaseName: string | undefined = undefined;  // Phase name for supporter
    export let displayNumber: string | number | undefined = undefined;  // Custom display number for badge

    const dispatch = createEventDispatcher<{
        toggleExpand: void;
        startCapture: void;
        toggleAttachment: void;
        moveUp: void;
        moveDown: void;
        remove: void;
        removeCapture: { captureId: string };
        openAttachmentModal: { attachment: StepAttachment };
        addTextAttachment: void;
        paste: ClipboardEvent;
        checkboxClick: MouseEvent;
        cardClick: MouseEvent;
        removeSupport: void;
    }>();

    function handleCardClick(e: MouseEvent) {
        // 먼저 cardClick 이벤트 발생시켜서 부모가 처리할 기회 제공
        dispatch("cardClick", e);
        // 이벤트가 stopPropagation 되지 않았으면 toggleExpand 실행
        if (!e.defaultPrevented) {
            dispatch("toggleExpand");
        }
    }

    function getStepDisplayText(): string {
        if (!stepDef) return "Unknown Step";
        return stepDef.values["purpose"] || stepDef.values["step_category"] || stepDef.id;
    }

    // Auto-focus action for input element
    function autoFocus(node: HTMLInputElement) {
        node.focus();
    }
</script>

<div
    class="step-item relative z-10 transition-all duration-200 {supportIndicator ? 'pl-14' : 'pl-7'}"
    style={isBeingDragged ? "opacity: 0.5;" : ""}
>
    {#if showDropIndicatorTop}
        <div
            class="absolute top-0 left-7 right-0 h-0.5 bg-blue-500 rounded-full z-50 pointer-events-none transform -translate-y-1/2 shadow-sm"
        ></div>
    {/if}

    {#if showDropIndicatorBottom && isLastStep}
        <div
            class="absolute bottom-0 left-7 right-0 h-0.5 bg-blue-500 rounded-full z-50 pointer-events-none transform translate-y-1/2 shadow-sm"
        ></div>
    {/if}

    <!-- Step Number Badge (or Support Indicator) -->
    {#if supportIndicator}
        <!-- Support indicator with phase color and phase name -->
        <div class="absolute left-0 top-2.5 group/support">
            <div
                class="h-5 px-1.5 rounded-full flex items-center justify-center shadow-sm transition-all duration-200 text-[9px] font-medium text-white whitespace-nowrap"
                style="background-color: {phaseColor || '#a855f7'}"
                title="{phaseName || '위상'} 지원"
            >
                {displayNumber !== undefined ? displayNumber : phaseName || '위상'}
            </div>
            <!-- Support remove button (appears on hover) -->
            <button
                class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center shadow-md transition-all duration-200 opacity-0 scale-75 group-hover/support:opacity-100 group-hover/support:scale-100 z-10"
                title="지원 해제"
                on:click|stopPropagation={() => dispatch("removeSupport")}
            >
                <svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    {:else if !hideBadge}
        <div
            class="absolute left-0 top-2.5 w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold shadow-sm transition-all duration-200"
            style="background-color: {color.border}; color: white;"
        >
            {displayNumber !== undefined ? displayNumber : index + 1}
        </div>
    {/if}

    <!-- Step Card -->
    <div
        class="bg-white rounded-lg border shadow-sm overflow-hidden transition-all duration-200 group
        {isExpanded ? 'ring-1 ring-blue-500/20 shadow-md border-blue-300' : 'border-gray-200 hover:border-blue-300'}
        {isBeingDragged ? 'shadow-none border-blue-200 bg-blue-50/20 ring-0' : ''}
        {isSelected ? 'ring-2 ring-blue-400 border-blue-400 bg-blue-50/30' : ''}"
    >
        <!-- Card Header -->
        <div
            class="p-2 cursor-pointer hover:bg-gray-50/50 flex items-start justify-between gap-2"
            on:click={handleCardClick}
        >
            <!-- Selection Checkbox (only shown in selection mode) -->
            {#if showSelectionCheckbox}
                <button
                    class="flex-shrink-0 w-4 h-4 rounded border-2 transition-all self-center flex items-center justify-center
                    {isSelected
                        ? 'bg-blue-500 border-blue-500'
                        : 'border-gray-300 hover:border-blue-400 bg-white'}"
                    on:click|stopPropagation={(e) => dispatch("checkboxClick", e)}
                    title="선택 토글"
                >
                    {#if isSelected}
                        <svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                        </svg>
                    {/if}
                </button>
            {/if}

            <!-- Drag Handle -->
            <div
                class="flex items-center pr-1 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-400 {showSelectionCheckbox ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity self-center"
            >
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="9" cy="6" r="2" /><circle cx="15" cy="6" r="2" />
                    <circle cx="9" cy="12" r="2" /><circle cx="15" cy="12" r="2" />
                    <circle cx="9" cy="18" r="2" /><circle cx="15" cy="18" r="2" />
                </svg>
            </div>

            <div class="flex-1 min-w-0">
                <div class="flex items-center flex-wrap gap-1.5 mb-0.5">
                    {#if stepDef?.values["step_category"]}
                        <span class="inline-flex px-1.5 py-px rounded text-[10px] font-semibold tracking-tight bg-gray-100 text-gray-500 border border-gray-100">
                            {stepDef.values["step_category"]}
                        </span>
                    {/if}
                    <h4 class="text-xs font-medium text-gray-800 leading-tight break-words flex-1">
                        {getStepDisplayText()}
                    </h4>
                </div>

                {#if step.captures.length > 0 || step.attachments.length > 0}
                    <div class="flex gap-2 mt-1">
                        {#if step.captures.length > 0}
                            <span class="text-[9px] text-blue-600 flex items-center gap-0.5 opacity-80">
                                📷 {step.captures.length}
                            </span>
                        {/if}
                        {#if step.attachments.length > 0}
                            <span class="text-[9px] text-amber-600 flex items-center gap-0.5 opacity-80">
                                📎 {step.attachments.length}
                            </span>
                        {/if}
                    </div>
                {/if}
            </div>

            <!-- Up/Down Buttons -->
            <div class="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity {isExpanded ? 'opacity-100' : ''}">
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                    on:click|stopPropagation={() => dispatch("moveUp")}
                    disabled={index === 0}
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                </button>
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                    on:click|stopPropagation={() => dispatch("moveDown")}
                    disabled={isLastStep}
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Expanded Content -->
        {#if isExpanded}
            <div class="px-2 pb-2 space-y-2" transition:slide|local={{ duration: 150 }}>
                <!-- Step Definition Details -->
                {#if stepDef}
                    <div class="bg-gray-50 rounded-lg p-3 border border-gray-100 flex flex-wrap gap-x-4 gap-y-3">
                        {#each workflowSteps.columns.filter((col) => stepDef.values[col.id]) as col}
                            <div class="flex flex-col gap-0.5 min-w-[120px] flex-1">
                                <span class="font-bold text-gray-400 text-[9px] uppercase tracking-wider">{col.name}</span>
                                <span class="text-[11px] text-gray-700 leading-relaxed whitespace-pre-wrap break-words">
                                    {stepDef.values[col.id]}
                                </span>
                            </div>
                        {/each}
                    </div>
                {/if}

                <!-- Action Buttons -->
                <div class="grid grid-cols-2 gap-2">
                    <button
                        class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                        {isCapturing
                            ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-inner'
                            : 'bg-white border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:shadow-sm'}"
                        on:click|stopPropagation={() => dispatch("startCapture")}
                    >
                        <span>📷</span>
                        {isCapturing ? "캡처 중..." : "영역 캡처"}
                    </button>

                    <button
                        class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                        {isAddingAttachment
                            ? 'bg-amber-50 border-amber-200 text-amber-700 shadow-inner'
                            : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300 hover:text-amber-600 hover:shadow-sm'}"
                        on:click|stopPropagation={() => dispatch("toggleAttachment")}
                    >
                        <span>📎</span>
                        첨부 추가
                    </button>
                </div>

                <!-- Attachment Input -->
                {#if isAddingAttachment}
                    <div class="bg-amber-50/50 border border-amber-100 rounded p-1.5" transition:slide={{ duration: 150 }}>
                        <div class="relative flex items-center">
                            <input
                                type="text"
                                bind:value={attachmentTextInput}
                                class="w-full pl-2 pr-8 py-1.5 text-[11px] border border-amber-200 rounded focus:outline-none focus:ring-1 focus:ring-amber-400 bg-white"
                                placeholder="내용 입력 또는 이미지 붙여넣기 (Ctrl+V)"
                                on:keydown={(e) => e.key === "Enter" && dispatch("addTextAttachment")}
                                on:paste={(e) => dispatch("paste", e)}
                                use:autoFocus
                            />
                            <button
                                class="absolute right-1 px-1.5 py-0.5 text-[10px] font-bold text-amber-600 hover:bg-amber-100 rounded"
                                disabled={!attachmentTextInput.trim()}
                                on:click={() => dispatch("addTextAttachment")}
                            >
                                ↵
                            </button>
                        </div>
                    </div>
                {/if}

                <!-- Captures & Attachments -->
                {#if step.captures.length > 0 || step.attachments.length > 0}
                    <div class="pt-1 border-t border-gray-50 flex flex-col gap-1.5">
                        {#if step.captures.length > 0}
                            <div class="flex flex-wrap gap-1">
                                {#each step.captures as capture (capture.id)}
                                    <div class="group inline-flex items-center gap-1 pl-1.5 pr-1 py-0.5 bg-blue-50/50 border border-blue-100 rounded text-[10px] text-blue-700">
                                        <span class="opacity-80">슬라이드 {capture.slideIndex + 1}</span>
                                        <button
                                            class="p-px hover:bg-blue-200 rounded-full text-blue-400 hover:text-blue-600"
                                            on:click={() => dispatch("removeCapture", { captureId: capture.id })}
                                        >
                                            <svg class="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                                <path d="M18 6L6 18M6 6l12 12" />
                                            </svg>
                                        </button>
                                    </div>
                                {/each}
                            </div>
                        {/if}

                        {#if step.attachments.length > 0}
                            <div class="grid grid-cols-2 gap-1.5">
                                {#each step.attachments as attachment (attachment.id)}
                                    <button
                                        class="relative group bg-gray-50 rounded border border-gray-100 overflow-hidden flex items-center text-left hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
                                        on:click={() => dispatch("openAttachmentModal", { attachment })}
                                    >
                                        {#if attachment.type === "image" && attachment.imageId}
                                            <img
                                                src={getAttachmentImageUrl(attachment.imageId)}
                                                alt="att"
                                                class="w-full h-12 object-cover"
                                            />
                                            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                                                <span class="opacity-0 group-hover:opacity-100 text-white text-[10px] font-medium bg-black/50 px-1.5 py-0.5 rounded transition-opacity">
                                                    클릭하여 보기
                                                </span>
                                            </div>
                                            {#if attachment.caption}
                                                <div class="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[9px] px-1 py-0.5 truncate">
                                                    {attachment.caption}
                                                </div>
                                            {/if}
                                        {:else}
                                            <div class="p-1.5 text-[10px] text-gray-600 leading-snug break-words w-full line-clamp-2">
                                                {attachment.data}
                                            </div>
                                        {/if}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- Delete Button -->
                <div class="pt-1 border-t border-gray-50 flex justify-end">
                    <button
                        class="text-[10px] text-red-300 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors"
                        on:click={() => dispatch("remove")}
                    >
                        삭제
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>

<style>
    .step-item {
        cursor: grab;
    }
    .step-item:active {
        cursor: grabbing;
    }
</style>
