<script lang="ts">
    import { slide, fade } from "svelte/transition";
    import { createEventDispatcher, onMount } from "svelte";
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

    // Toggle step expansion
    function toggleStepExpand(stepId: string) {
        expandedStepId = expandedStepId === stepId ? null : stepId;
    }

    // Start capture mode for a specific step
    function startCaptureForStep(stepId: string) {
        dispatch("toggleCaptureMode", { stepId });
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
                    <!-- Capture Mode Banner -->
                    {#if captureMode && captureTargetStepId}
                        <div class="bg-blue-100 border border-blue-300 rounded-lg px-3 py-2 text-sm text-blue-800 flex items-center justify-between">
                            <span>🎯 슬라이드에서 영역을 드래그하여 캡처하세요</span>
                            <button
                                class="text-blue-600 hover:text-blue-800 text-xs font-medium"
                                on:click={() => dispatch("toggleCaptureMode", { stepId: null })}
                            >
                                취소
                            </button>
                        </div>
                    {/if}

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
                                class="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-hidden flex flex-col"
                                transition:fade={{ duration: 150 }}
                                on:click|stopPropagation
                            >
                                <!-- Search -->
                                <div class="p-2 border-b border-gray-100">
                                    <input
                                        type="text"
                                        bind:value={searchQuery}
                                        placeholder="스텝 검색..."
                                        class="w-full px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>

                                <!-- Category Tabs -->
                                <div class="flex gap-1 p-2 border-b border-gray-100 overflow-x-auto flex-shrink-0">
                                    <button
                                        class="px-2 py-1 text-xs rounded whitespace-nowrap {selectedCategoryTab === 'all'
                                            ? 'bg-blue-100 text-blue-700'
                                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
                                        on:click={() => selectedCategoryTab = "all"}
                                    >
                                        전체
                                    </button>
                                    {#each categories as category}
                                        <button
                                            class="px-2 py-1 text-xs rounded whitespace-nowrap {selectedCategoryTab === category
                                                ? 'bg-blue-100 text-blue-700'
                                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
                                            on:click={() => selectedCategoryTab = category}
                                        >
                                            {category}
                                        </button>
                                    {/each}
                                </div>

                                <!-- Step List -->
                                <div class="flex-1 overflow-y-auto max-h-48">
                                    {#if filteredSteps.length === 0}
                                        <div class="p-4 text-center text-gray-400 text-sm">
                                            {searchQuery ? "검색 결과가 없습니다" : "등록된 스텝이 없습니다"}
                                        </div>
                                    {:else}
                                        {#each filteredSteps as step (step.id)}
                                            <button
                                                class="w-full px-3 py-2 text-left text-sm hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-b-0"
                                                on:click={() => handleAddStep(step)}
                                            >
                                                <div class="font-medium text-gray-800">
                                                    {#if step.values["step_category"]}
                                                        <span class="text-blue-600">[{step.values["step_category"]}]</span>
                                                    {/if}
                                                    {step.values["purpose"] || "(목적 없음)"}
                                                </div>
                                                {#if step.values["system"] || step.values["access_target"]}
                                                    <div class="text-xs text-gray-500 mt-0.5">
                                                        {[step.values["system"], step.values["access_target"]].filter(Boolean).join(" → ")}
                                                    </div>
                                                {/if}
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
                                            📷 슬라이드 캡처
                                        </button>
                                        <button
                                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded border bg-white border-gray-200 text-gray-600 hover:bg-green-50 hover:border-green-200 transition-colors"
                                            on:click={() => addingAttachmentToStepId = addingAttachmentToStepId === step.id ? null : step.id}
                                        >
                                            📎 이미지/텍스트 추가
                                        </button>
                                    </div>

                                    <!-- Add Attachment Section -->
                                    {#if addingAttachmentToStepId === step.id}
                                        <div class="border border-gray-200 rounded p-2 bg-white space-y-2" transition:slide={{ duration: 100 }}>
                                            <div
                                                class="border-2 border-dashed border-gray-300 rounded p-3 text-center text-sm text-gray-500"
                                                on:paste={(e) => handlePaste(e, step.id)}
                                                tabindex="0"
                                                role="button"
                                            >
                                                이미지를 붙여넣기 (Ctrl+V) 하거나<br/>
                                                아래에 텍스트를 입력하세요
                                            </div>
                                            <div class="flex gap-2">
                                                <input
                                                    type="text"
                                                    bind:value={attachmentTextInput}
                                                    placeholder="텍스트 입력..."
                                                    class="flex-1 px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    on:keypress={(e) => e.key === 'Enter' && addTextAttachment(step.id)}
                                                />
                                                <button
                                                    class="px-3 py-1 text-xs font-medium bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                                                    on:click={() => addTextAttachment(step.id)}
                                                >
                                                    추가
                                                </button>
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
