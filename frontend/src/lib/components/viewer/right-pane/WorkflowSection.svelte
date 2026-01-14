<script lang="ts">
    import { slide, fade } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        ProjectWorkflowData,
        StepCapture,
        StepAttachment,
    } from "$lib/types/workflow";
    import {
        createEmptyWorkflowData,
        createStepInstance,
        createStepCapture,
        createAttachment,
    } from "$lib/types/workflow";
    import WorkflowGraph from "$lib/components/phenomenon/WorkflowGraph.svelte";

    export let isExpanded = false;
    export let workflowData: ProjectWorkflowData = createEmptyWorkflowData();
    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let savingWorkflow = false;
    export let captureMode = false;

    // Selected step for capture
    export let captureTargetStepId: string | null = null;

    const dispatch = createEventDispatcher();

    let viewMode: "list" | "graph" = "list";
    let showAddStepPopup = false;
    let searchQuery = "";
    let selectedCategoryTab = "all"; // "all" or a step_category value
    let expandedStepId: string | null = null;
    let addingAttachmentToStepId: string | null = null;
    let attachmentTextInput = "";
    let popupRef: HTMLDivElement | null = null;

    // Exit capture mode helper
    function exitCaptureMode() {
        if (captureMode) {
            dispatch("toggleCaptureMode", { stepId: null });
        }
    }

    // Handle ESC key to exit capture mode
    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === "Escape" && captureMode) {
            exitCaptureMode();
        }
    }

    onMount(() => {
        window.addEventListener("keydown", handleKeyDown);
    });

    onDestroy(() => {
        window.removeEventListener("keydown", handleKeyDown);
    });

    // Color palette for step captures
    const CAPTURE_COLORS = [
        { bg: 'rgba(59, 130, 246, 0.2)', border: '#3b82f6' },   // blue
        { bg: 'rgba(34, 197, 94, 0.2)', border: '#22c55e' },    // green
        { bg: 'rgba(168, 85, 247, 0.2)', border: '#a855f7' },   // purple
        { bg: 'rgba(249, 115, 22, 0.2)', border: '#f97316' },   // orange
        { bg: 'rgba(236, 72, 153, 0.2)', border: '#ec4899' },   // pink
        { bg: 'rgba(20, 184, 166, 0.2)', border: '#14b8a6' },   // teal
        { bg: 'rgba(234, 179, 8, 0.2)', border: '#eab308' },    // yellow
        { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444' },    // red
    ];

    // Get all unique categories from workflow steps
    $: categories = [...new Set(
        workflowSteps.rows
            .map(r => r.values["step_category"])
            .filter(Boolean)
    )];

    // Filter steps based on search and category
    $: filteredSteps = workflowSteps.rows.filter(row => {
        // Category filter
        if (selectedCategoryTab !== "all") {
            if (row.values["step_category"] !== selectedCategoryTab) return false;
        }

        // Search filter
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            return Object.values(row.values).some(v =>
                v?.toLowerCase().includes(query)
            );
        }
        return true;
    });

    // Get step definition by ID
    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find(r => r.id === stepId);
    }

    // Get step display text
    function getStepDisplayText(step: WorkflowStepInstance): string {
        const def = getStepDefinition(step.stepId);
        if (!def) return "(알 수 없는 스텝)";
        const category = def.values["step_category"];
        const purpose = def.values["purpose"];
        if (category && purpose) return `[${category}] ${purpose}`;
        if (category) return `[${category}]`;
        if (purpose) return purpose;
        return def.id;
    }

    // Handle adding a new step
    function handleAddStep(stepRow: WorkflowStepRow) {
        const newStep = createStepInstance(stepRow.id, workflowData.steps.length);
        workflowData = {
            ...workflowData,
            steps: [...workflowData.steps, newStep],
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        showAddStepPopup = false;
        searchQuery = "";
        expandedStepId = newStep.id;
    }

    // Handle removing a step
    function handleRemoveStep(stepId: string) {
        if (confirm("이 스텝을 삭제하시겠습니까?")) {
            // Turn off capture mode if this step was being captured
            if (captureTargetStepId === stepId) {
                dispatch("toggleCaptureMode", { stepId: null });
            }
            workflowData = {
                ...workflowData,
                steps: workflowData.steps.filter(s => s.id !== stepId),
                updatedAt: new Date().toISOString(),
            };
            dispatch("workflowChange", workflowData);
        }
    }

    // Toggle step expansion (exit capture mode when collapsing or switching steps)
    function toggleStepExpand(stepId: string) {
        // Exit capture mode when closing step or switching to another step
        if (captureMode) {
            exitCaptureMode();
        }
        expandedStepId = expandedStepId === stepId ? null : stepId;
        // Also close attachment input when switching steps
        addingAttachmentToStepId = null;
    }

    // Start capture mode for a specific step (toggle behavior)
    function startCaptureForStep(stepId: string) {
        if (captureMode && captureTargetStepId === stepId) {
            // If already capturing for this step, toggle off
            exitCaptureMode();
        } else {
            // Start capture for this step
            dispatch("toggleCaptureMode", { stepId });
        }
    }

    // Toggle attachment section (exit capture mode when opening)
    function toggleAttachmentSection(stepId: string) {
        // Exit capture mode when opening attachment section
        if (captureMode) {
            exitCaptureMode();
        }
        addingAttachmentToStepId = addingAttachmentToStepId === stepId ? null : stepId;
    }

    // Add capture to step (called from parent via export)
    export function addCapture(capture: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
    }) {
        if (!captureTargetStepId) return;

        const stepIndex = workflowData.steps.findIndex(s => s.id === captureTargetStepId);
        if (stepIndex === -1) return;

        const newCapture = createStepCapture(
            capture.slideIndex,
            capture.x,
            capture.y,
            capture.width,
            capture.height
        );

        workflowData.steps[stepIndex].captures = [
            ...workflowData.steps[stepIndex].captures,
            newCapture,
        ];
        workflowData = {
            ...workflowData,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Remove capture from step
    function removeCapture(stepId: string, captureId: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;

        workflowData.steps[stepIndex].captures = workflowData.steps[stepIndex].captures.filter(
            c => c.id !== captureId
        );
        workflowData = {
            ...workflowData,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Handle paste for image attachment
    async function handlePaste(event: ClipboardEvent, stepId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith('image/')) {
                event.preventDefault();
                const blob = item.getAsFile();
                if (!blob) continue;

                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result as string;
                    addImageAttachment(stepId, base64);
                };
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    // Add image attachment
    function addImageAttachment(stepId: string, base64Data: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;

        const attachment = createAttachment('image', base64Data);
        workflowData.steps[stepIndex].attachments = [
            ...workflowData.steps[stepIndex].attachments,
            attachment,
        ];
        workflowData = {
            ...workflowData,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Add text attachment
    function addTextAttachment(stepId: string) {
        if (!attachmentTextInput.trim()) return;

        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;

        const attachment = createAttachment('text', attachmentTextInput.trim());
        workflowData.steps[stepIndex].attachments = [
            ...workflowData.steps[stepIndex].attachments,
            attachment,
        ];
        workflowData = {
            ...workflowData,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
        attachmentTextInput = "";
        addingAttachmentToStepId = null;
    }

    // Remove attachment
    function removeAttachment(stepId: string, attachmentId: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;

        workflowData.steps[stepIndex].attachments = workflowData.steps[stepIndex].attachments.filter(
            a => a.id !== attachmentId
        );
        workflowData = {
            ...workflowData,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Get capture overlays for display on canvas
    export function getCaptureOverlays() {
        const overlays: any[] = [];
        let colorIndex = 0;

        for (const step of workflowData.steps) {
            const color = CAPTURE_COLORS[colorIndex % CAPTURE_COLORS.length];
            for (const capture of step.captures) {
                overlays.push({
                    ...capture,
                    stepId: step.id,
                    color,
                    colorIndex,
                });
            }
            colorIndex++;
        }
        return overlays;
    }

    // Delete entire workflow
    function handleDeleteWorkflow() {
        if (confirm("워크플로우를 삭제하시겠습니까? 모든 스텝과 데이터가 삭제됩니다.")) {
            dispatch("deleteWorkflow");
        }
    }

    // Move step up/down
    function moveStepUp(index: number) {
        if (index === 0) return;
        const steps = [...workflowData.steps];
        [steps[index - 1], steps[index]] = [steps[index], steps[index - 1]];
        workflowData = {
            ...workflowData,
            steps,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    function moveStepDown(index: number) {
        if (index === workflowData.steps.length - 1) return;
        const steps = [...workflowData.steps];
        [steps[index], steps[index + 1]] = [steps[index + 1], steps[index]];
        workflowData = {
            ...workflowData,
            steps,
            updatedAt: new Date().toISOString(),
        };
        dispatch("workflowChange", workflowData);
    }

    // Close popup when clicking outside
    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <!-- Header -->
    <div class="flex flex-col border-b border-gray-100">
        <AccordionHeader
            icon="⚡"
            title="워크플로우"
            {isExpanded}
            on:click={() => dispatch("toggleExpand")}
        >
            <svelte:fragment slot="actions">
                {#if isExpanded}
                    <!-- View Toggle -->
                    <div class="flex items-center gap-1 mr-2 bg-gray-100 rounded p-0.5">
                        <button
                            class="px-2 py-0.5 text-xs rounded transition-colors {viewMode === 'list'
                                ? 'bg-white shadow-sm text-gray-800'
                                : 'text-gray-500 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "list")}
                            title="리스트 뷰"
                        >
                            <span class="text-[10px]">☰</span>
                        </button>
                        <button
                            class="px-2 py-0.5 text-xs rounded transition-colors {viewMode === 'graph'
                                ? 'bg-white shadow-sm text-gray-800'
                                : 'text-gray-500 hover:text-gray-700'}"
                            on:click|stopPropagation={() => (viewMode = "graph")}
                            title="그래프 뷰"
                        >
                            <span class="text-[10px]">☊</span>
                        </button>
                    </div>
                    <!-- Delete Button -->
                    <button
                        class="px-2 py-1 text-xs font-medium rounded transition-colors mr-2 bg-red-50 text-red-600 hover:bg-red-100 hover:text-red-700"
                        on:click|stopPropagation={handleDeleteWorkflow}
                        title="워크플로우 삭제"
                    >
                        <span class="text-[10px]">🗑️</span>
                    </button>
                {/if}
            </svelte:fragment>
        </AccordionHeader>
    </div>

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="bg-gray-50/30 flex-1 flex flex-col min-h-[350px] overflow-hidden relative"
        >
            {#if viewMode === "graph"}
                <WorkflowGraph
                    {workflowData}
                    {workflowSteps}
                />
            {:else}
                <!-- List View -->
                <div class="flex-1 overflow-y-auto p-3 space-y-3">
                    <!-- Add Step Button -->
                    <div class="relative">
                        <button
                            class="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-colors text-sm font-medium"
                            on:click|stopPropagation={() => showAddStepPopup = !showAddStepPopup}
                        >
                            + 스텝 추가
                        </button>

                        <!-- Step Selector Popup -->
                        {#if showAddStepPopup}
                            <div
                                bind:this={popupRef}
                                class="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50 max-h-[500px] overflow-hidden flex flex-col"
                                transition:fade={{ duration: 150 }}
                                on:click|stopPropagation
                            >
                                <!-- Header -->
                                <div class="px-3 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                                    <span class="text-sm font-medium text-gray-700">스텝 선택</span>
                                    <span class="text-xs text-gray-400">{filteredSteps.length}개</span>
                                </div>

                                <!-- Search -->
                                <div class="p-2 border-b border-gray-100">
                                    <div class="relative">
                                        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                        </svg>
                                        <input
                                            type="text"
                                            bind:value={searchQuery}
                                            placeholder="스텝 검색..."
                                            class="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>

                                <!-- Category Tabs -->
                                <div class="flex gap-1.5 p-2 border-b border-gray-100 overflow-x-auto flex-shrink-0 bg-gray-50/50">
                                    <button
                                        class="px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === 'all'
                                            ? 'bg-blue-500 text-white shadow-sm'
                                            : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-100'}"
                                        on:click={() => selectedCategoryTab = "all"}
                                    >
                                        전체
                                    </button>
                                    {#each categories as category}
                                        <button
                                            class="px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === category
                                                ? 'bg-blue-500 text-white shadow-sm'
                                                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-100'}"
                                            on:click={() => selectedCategoryTab = category}
                                        >
                                            {category}
                                        </button>
                                    {/each}
                                </div>

                                <!-- Step List -->
                                <div class="flex-1 overflow-y-auto">
                                    {#if filteredSteps.length === 0}
                                        <div class="p-6 text-center text-gray-400">
                                            <svg class="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            <div class="text-sm">{searchQuery ? "검색 결과가 없습니다" : "등록된 스텝이 없습니다"}</div>
                                        </div>
                                    {:else}
                                        {#each filteredSteps as step (step.id)}
                                            <button
                                                class="w-full px-3 py-3 text-left hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 group"
                                                on:click={() => handleAddStep(step)}
                                            >
                                                <div class="flex items-start gap-3">
                                                    <!-- Category Icon/Badge -->
                                                    <div class="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
                                                        {step.values["step_category"]?.charAt(0) || "S"}
                                                    </div>
                                                    <!-- Content -->
                                                    <div class="flex-1 min-w-0">
                                                        <div class="flex items-center gap-2 mb-0.5">
                                                            {#if step.values["step_category"]}
                                                                <span class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                                                                    {step.values["step_category"]}
                                                                </span>
                                                            {/if}
                                                        </div>
                                                        <div class="font-medium text-sm text-gray-800 truncate group-hover:text-blue-700">
                                                            {step.values["purpose"] || "(목적 없음)"}
                                                        </div>
                                                        {#if step.values["system"] || step.values["access_target"]}
                                                            <div class="flex items-center gap-1 text-xs text-gray-500 mt-1">
                                                                <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                                                </svg>
                                                                <span class="truncate">
                                                                    {[step.values["system"], step.values["access_target"]].filter(Boolean).join(" → ")}
                                                                </span>
                                                            </div>
                                                        {/if}
                                                        {#if step.values["action"] || step.values["expected_result"]}
                                                            <div class="text-xs text-gray-400 mt-1 truncate">
                                                                {step.values["action"] || step.values["expected_result"]}
                                                            </div>
                                                        {/if}
                                                    </div>
                                                    <!-- Arrow indicator -->
                                                    <svg class="w-4 h-4 text-gray-300 group-hover:text-blue-500 flex-shrink-0 mt-2 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                    </svg>
                                                </div>
                                            </button>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    </div>

                    <!-- Step List -->
                    {#each workflowData.steps as step, index (step.id)}
                        {@const stepDef = getStepDefinition(step.stepId)}
                        {@const color = CAPTURE_COLORS[index % CAPTURE_COLORS.length]}
                        <div
                            class="bg-white border rounded-lg overflow-hidden shadow-sm"
                            style="border-left: 4px solid {color.border};"
                        >
                            <!-- Step Header -->
                            <div class="flex items-center gap-2 p-3">
                                <div class="flex flex-col gap-0.5">
                                    <button
                                        class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs leading-none"
                                        on:click={() => moveStepUp(index)}
                                        disabled={index === 0}
                                    >▲</button>
                                    <button
                                        class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs leading-none"
                                        on:click={() => moveStepDown(index)}
                                        disabled={index === workflowData.steps.length - 1}
                                    >▼</button>
                                </div>

                                <div class="flex-1 min-w-0">
                                    <div class="font-medium text-sm text-gray-800 truncate">
                                        {getStepDisplayText(step)}
                                    </div>
                                    <div class="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                                        {#if step.captures.length > 0}
                                            <span class="flex items-center gap-0.5">
                                                📷 {step.captures.length}
                                            </span>
                                        {/if}
                                        {#if step.attachments.length > 0}
                                            <span class="flex items-center gap-0.5">
                                                📎 {step.attachments.length}
                                            </span>
                                        {/if}
                                    </div>
                                </div>

                                <button
                                    class="text-gray-400 hover:text-blue-600 p-1 transition-colors"
                                    on:click={() => toggleStepExpand(step.id)}
                                    title="상세 보기"
                                >
                                    {expandedStepId === step.id ? "▼" : "▶"}
                                </button>

                                <button
                                    class="text-gray-400 hover:text-red-500 p-1 transition-colors"
                                    on:click={() => handleRemoveStep(step.id)}
                                    title="스텝 삭제"
                                >
                                    ✕
                                </button>
                            </div>

                            <!-- Expanded Content -->
                            {#if expandedStepId === step.id}
                                <div class="border-t border-gray-100 p-3 bg-gray-50/50 space-y-3" transition:slide={{ duration: 150 }}>
                                    <!-- Step Details -->
                                    {#if stepDef}
                                        <div class="grid grid-cols-2 gap-2 text-xs">
                                            {#each workflowSteps.columns as col}
                                                {#if stepDef.values[col.id]}
                                                    <div>
                                                        <span class="text-gray-500">{col.name}:</span>
                                                        <span class="text-gray-700 ml-1">{stepDef.values[col.id]}</span>
                                                    </div>
                                                {/if}
                                            {/each}
                                        </div>
                                    {/if}

                                    <!-- Action Buttons -->
                                    <div class="flex gap-2">
                                        <button
                                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded border transition-colors
                                                {captureTargetStepId === step.id
                                                    ? 'bg-blue-100 border-blue-300 text-blue-700'
                                                    : 'bg-white border-gray-200 text-gray-600 hover:bg-blue-50 hover:border-blue-200'}"
                                            on:click={() => startCaptureForStep(step.id)}
                                        >
                                            📷 {captureTargetStepId === step.id ? '캡처 중...' : '슬라이드 캡처'}
                                        </button>
                                        <button
                                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded border transition-colors
                                                {addingAttachmentToStepId === step.id
                                                    ? 'bg-green-100 border-green-300 text-green-700'
                                                    : 'bg-white border-gray-200 text-gray-600 hover:bg-green-50 hover:border-green-200'}"
                                            on:click={() => toggleAttachmentSection(step.id)}
                                        >
                                            📎 이미지/텍스트 추가
                                        </button>
                                    </div>

                                    <!-- Add Attachment Section (Combined Image/Text Input) -->
                                    {#if addingAttachmentToStepId === step.id}
                                        <div class="border border-gray-200 rounded-lg bg-white overflow-hidden" transition:slide={{ duration: 100 }}>
                                            <!-- Combined input area -->
                                            <div
                                                class="relative"
                                                on:paste={(e) => handlePaste(e, step.id)}
                                                tabindex="0"
                                                role="button"
                                            >
                                                <div class="flex items-stretch">
                                                    <!-- Text input area -->
                                                    <input
                                                        type="text"
                                                        bind:value={attachmentTextInput}
                                                        placeholder="텍스트 입력 또는 이미지 붙여넣기 (Ctrl+V)"
                                                        class="flex-1 px-3 py-2.5 text-sm border-0 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                                                        on:keypress={(e) => e.key === 'Enter' && addTextAttachment(step.id)}
                                                        on:paste={(e) => handlePaste(e, step.id)}
                                                    />
                                                    <!-- Add button -->
                                                    <button
                                                        class="px-4 py-2 text-xs font-medium bg-blue-500 text-white hover:bg-blue-600 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                                                        on:click={() => addTextAttachment(step.id)}
                                                        disabled={!attachmentTextInput.trim()}
                                                    >
                                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                                        </svg>
                                                        추가
                                                    </button>
                                                </div>
                                                <!-- Helper text -->
                                                <div class="px-3 py-1.5 bg-gray-50 border-t border-gray-100 text-[10px] text-gray-400 flex items-center gap-3">
                                                    <span class="flex items-center gap-1">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                        </svg>
                                                        Ctrl+V로 이미지 붙여넣기
                                                    </span>
                                                    <span class="flex items-center gap-1">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                        </svg>
                                                        Enter로 텍스트 추가
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    {/if}

                                    <!-- Captures -->
                                    {#if step.captures.length > 0}
                                        <div class="space-y-1">
                                            <div class="text-xs font-medium text-gray-600">캡처</div>
                                            <div class="flex flex-wrap gap-1">
                                                {#each step.captures as capture (capture.id)}
                                                    <div
                                                        class="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs"
                                                    >
                                                        <span class="text-blue-700">📷 슬라이드 {capture.slideIndex + 1}</span>
                                                        <button
                                                            class="text-blue-400 hover:text-red-500 ml-1"
                                                            on:click={() => removeCapture(step.id, capture.id)}
                                                        >✕</button>
                                                    </div>
                                                {/each}
                                            </div>
                                        </div>
                                    {/if}

                                    <!-- Attachments -->
                                    {#if step.attachments.length > 0}
                                        <div class="space-y-1">
                                            <div class="text-xs font-medium text-gray-600">첨부</div>
                                            <div class="flex flex-wrap gap-2">
                                                {#each step.attachments as attachment (attachment.id)}
                                                    {#if attachment.type === 'image'}
                                                        <div class="relative group">
                                                            <img
                                                                src={attachment.data}
                                                                alt="첨부 이미지"
                                                                class="w-16 h-16 object-cover rounded border border-gray-200"
                                                            />
                                                            <button
                                                                class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                                                on:click={() => removeAttachment(step.id, attachment.id)}
                                                            >✕</button>
                                                        </div>
                                                    {:else}
                                                        <div
                                                            class="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 border border-gray-200 rounded text-xs max-w-full"
                                                        >
                                                            <span class="text-gray-700 truncate max-w-32">💬 {attachment.data}</span>
                                                            <button
                                                                class="text-gray-400 hover:text-red-500 ml-1 flex-shrink-0"
                                                                on:click={() => removeAttachment(step.id, attachment.id)}
                                                            >✕</button>
                                                        </div>
                                                    {/if}
                                                {/each}
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    {/each}

                    <!-- Empty State -->
                    {#if workflowData.steps.length === 0}
                        <div class="text-center text-gray-400 py-8">
                            <div class="text-3xl mb-2">📋</div>
                            <div class="text-sm">워크플로우 스텝이 없습니다</div>
                            <div class="text-xs mt-1">위의 버튼을 눌러 스텝을 추가하세요</div>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>
