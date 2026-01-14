<script lang="ts">
    import { slide, fade, fly } from "svelte/transition";
    import { createEventDispatcher, onMount, onDestroy } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import type {
        WorkflowSteps,
        WorkflowStepRow,
        WorkflowStepInstance,
        ProjectWorkflowData,
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
    export let captureTargetStepId: string | null = null;

    const dispatch = createEventDispatcher();

    let viewMode: "list" | "graph" = "list";
    let showAddStepPopup = false;
    let searchQuery = "";
    let selectedCategoryTab = "all";
    let expandedStepId: string | null = null;
    let addingAttachmentToStepId: string | null = null;
    let attachmentTextInput = "";
    let popupRef: HTMLDivElement | null = null;

    // --- Helpers & Handlers ---

    function exitCaptureMode() {
        if (captureMode) {
            dispatch("toggleCaptureMode", { stepId: null });
        }
    }

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

    const CAPTURE_COLORS = [
        { bg: 'rgba(59, 130, 246, 0.1)', border: '#3b82f6', text: '#2563eb' },
        { bg: 'rgba(34, 197, 94, 0.1)', border: '#22c55e', text: '#16a34a' },
        { bg: 'rgba(168, 85, 247, 0.1)', border: '#a855f7', text: '#9333ea' },
        { bg: 'rgba(249, 115, 22, 0.1)', border: '#f97316', text: '#ea580c' },
        { bg: 'rgba(236, 72, 153, 0.1)', border: '#ec4899', text: '#db2777' },
        { bg: 'rgba(20, 184, 166, 0.1)', border: '#14b8a6', text: '#0d9488' },
    ];

    $: categories = [...new Set(workflowSteps.rows.map(r => r.values["step_category"]).filter(Boolean))];

    $: filteredSteps = workflowSteps.rows.filter(row => {
        if (selectedCategoryTab !== "all") {
            if (row.values["step_category"] !== selectedCategoryTab) return false;
        }
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            return Object.values(row.values).some(v => v?.toLowerCase().includes(query));
        }
        return true;
    });

    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find(r => r.id === stepId);
    }

    function getStepDisplayText(step: WorkflowStepInstance): string {
        const def = getStepDefinition(step.stepId);
        if (!def) return "Unknown Step";
        return def.values["purpose"] || def.values["step_category"] || def.id;
    }

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

    function handleRemoveStep(stepId: string) {
        if (confirm("이 스텝을 정말 삭제하시겠습니까?")) {
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

    function toggleStepExpand(stepId: string) {
        if (captureMode) exitCaptureMode();
        expandedStepId = expandedStepId === stepId ? null : stepId;
        addingAttachmentToStepId = null;
    }

    function startCaptureForStep(stepId: string) {
        if (captureMode && captureTargetStepId === stepId) {
            exitCaptureMode();
        } else {
            dispatch("toggleCaptureMode", { stepId });
        }
    }

    function toggleAttachmentSection(stepId: string) {
        if (captureMode) exitCaptureMode();
        addingAttachmentToStepId = addingAttachmentToStepId === stepId ? null : stepId;
    }

    export function addCapture(capture: { slideIndex: number; x: number; y: number; width: number; height: number; }) {
        if (!captureTargetStepId) return;
        const stepIndex = workflowData.steps.findIndex(s => s.id === captureTargetStepId);
        if (stepIndex === -1) return;
        
        const newCapture = createStepCapture(capture.slideIndex, capture.x, capture.y, capture.width, capture.height);
        workflowData.steps[stepIndex].captures = [...workflowData.steps[stepIndex].captures, newCapture];
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function removeCapture(stepId: string, captureId: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;
        workflowData.steps[stepIndex].captures = workflowData.steps[stepIndex].captures.filter(c => c.id !== captureId);
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    async function handlePaste(event: ClipboardEvent, stepId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;
        for (const item of items) {
            if (item.type.startsWith('image/')) {
                event.preventDefault();
                const blob = item.getAsFile();
                if (!blob) continue;
                const reader = new FileReader();
                reader.onload = () => addImageAttachment(stepId, reader.result as string);
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    function addImageAttachment(stepId: string, base64Data: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;
        const attachment = createAttachment('image', base64Data);
        workflowData.steps[stepIndex].attachments = [...workflowData.steps[stepIndex].attachments, attachment];
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function addTextAttachment(stepId: string) {
        if (!attachmentTextInput.trim()) return;
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;
        const attachment = createAttachment('text', attachmentTextInput.trim());
        workflowData.steps[stepIndex].attachments = [...workflowData.steps[stepIndex].attachments, attachment];
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
        attachmentTextInput = "";
        addingAttachmentToStepId = null;
    }

    function removeAttachment(stepId: string, attachmentId: string) {
        const stepIndex = workflowData.steps.findIndex(s => s.id === stepId);
        if (stepIndex === -1) return;
        workflowData.steps[stepIndex].attachments = workflowData.steps[stepIndex].attachments.filter(a => a.id !== attachmentId);
        workflowData = { ...workflowData, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    export function getCaptureOverlays() {
        const overlays: any[] = [];
        let colorIndex = 0;
        for (const step of workflowData.steps) {
            const color = CAPTURE_COLORS[colorIndex % CAPTURE_COLORS.length];
            for (const capture of step.captures) {
                overlays.push({ ...capture, stepId: step.id, color, colorIndex });
            }
            colorIndex++;
        }
        return overlays;
    }

    function handleDeleteWorkflow() {
        if (confirm("워크플로우 전체를 삭제하시겠습니까?")) {
            dispatch("deleteWorkflow");
        }
    }

    function moveStepUp(index: number) {
        if (index === 0) return;
        const steps = [...workflowData.steps];
        [steps[index - 1], steps[index]] = [steps[index], steps[index - 1]];
        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function moveStepDown(index: number) {
        if (index === workflowData.steps.length - 1) return;
        const steps = [...workflowData.steps];
        [steps[index], steps[index + 1]] = [steps[index + 1], steps[index]];
        workflowData = { ...workflowData, steps, updatedAt: new Date().toISOString() };
        dispatch("workflowChange", workflowData);
    }

    function handleClickOutside(event: MouseEvent) {
        if (popupRef && !popupRef.contains(event.target as Node)) {
            showAddStepPopup = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="border-b border-gray-200 bg-white flex flex-col {isExpanded ? 'flex-1 min-h-0' : ''}">
    <AccordionHeader
        icon="⚡"
        title="Workflow"
        {isExpanded}
        on:click={() => dispatch("toggleExpand")}
    >
        <svelte:fragment slot="actions">
            {#if isExpanded}
                <div class="flex items-center gap-1 mr-2">
                    <div class="flex bg-gray-100 p-0.5 rounded-md border border-gray-200">
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode === 'list' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() => viewMode = "list"}
                        >
                            List
                        </button>
                        <button
                            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode === 'graph' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-gray-700'}"
                            on:click|stopPropagation={() => viewMode = "graph"}
                        >
                            Graph
                        </button>
                    </div>
                    <button
                        class="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        on:click|stopPropagation={handleDeleteWorkflow}
                        title="전체 초기화"
                    >
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                </div>
            {/if}
        </svelte:fragment>
    </AccordionHeader>

    {#if isExpanded}
        <div transition:slide={{ duration: 200 }} class="flex-1 flex flex-col min-h-[400px] bg-gray-50/50 relative overflow-hidden">
            
            {#if viewMode === "graph"}
                <WorkflowGraph {workflowData} {workflowSteps} />
            {:else}
                <div class="flex-1 overflow-y-auto p-3 space-y-2 relative">
                    <div class="absolute left-[23px] top-3 bottom-3 w-px bg-gray-200 z-0"></div>

                    {#each workflowData.steps as step, index (step.id)}
                        {@const stepDef = getStepDefinition(step.stepId)}
                        {@const color = CAPTURE_COLORS[index % CAPTURE_COLORS.length]}
                        {@const isCapturing = captureTargetStepId === step.id}
                        {@const isAddingAttach = addingAttachmentToStepId === step.id}

                        <div class="relative z-10 pl-7" transition:fly={{ y: 20, duration: 200 }}>
                            <div 
                                class="absolute left-0 top-2.5 w-5 h-5 rounded-full border-2 bg-white flex items-center justify-center text-[9px] font-bold shadow-sm transition-colors duration-300"
                                style="border-color: {color.border}; color: {color.border};"
                            >
                                {index + 1}
                            </div>

                            <div 
                                class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden transition-all duration-200 hover:border-blue-300 group
                                {expandedStepId === step.id ? 'ring-1 ring-blue-500/20 shadow-md' : ''}"
                            >
                                <div 
                                    class="p-2 cursor-pointer hover:bg-gray-50/50 flex items-start justify-between gap-2"
                                    on:click={() => toggleStepExpand(step.id)}
                                >
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center flex-wrap gap-1.5 mb-0.5">
                                            {#if stepDef?.values["step_category"]}
                                                <span 
                                                    class="inline-flex px-1.5 py-px rounded text-[10px] font-semibold tracking-tight bg-gray-100 text-gray-500 border border-gray-100"
                                                >
                                                    {stepDef.values["step_category"]}
                                                </span>
                                            {/if}
                                            <h4 class="text-xs font-medium text-gray-800 leading-tight break-words flex-1">
                                                {getStepDisplayText(step)}
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

                                    <div class="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity {expandedStepId === step.id ? 'opacity-100' : ''}">
                                        <button 
                                            class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                                            on:click|stopPropagation={() => moveStepUp(index)}
                                            disabled={index === 0}
                                        >
                                            <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" /></svg>
                                        </button>
                                        <button 
                                            class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500 disabled:opacity-10"
                                            on:click|stopPropagation={() => moveStepDown(index)}
                                            disabled={index === workflowData.steps.length - 1}
                                        >
                                            <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                                        </button>
                                    </div>
                                </div>

                                {#if expandedStepId === step.id}
                                    <div class="px-2 pb-2 space-y-2" transition:slide|local={{ duration: 150 }}>
                                        
                                        {#if stepDef}
                                            <div class="bg-gray-50 rounded p-2 grid grid-cols-1 gap-1 text-[11px] text-gray-600 border border-gray-100">
                                                {#each workflowSteps.columns.filter(col => stepDef.values[col.id]) as col}
                                                    <div class="flex gap-2 items-start">
                                                        <span class="font-medium text-gray-400 min-w-[50px] text-[10px] uppercase tracking-wider">{col.name}</span>
                                                        <span class="text-gray-700 break-all leading-tight">{stepDef.values[col.id]}</span>
                                                    </div>
                                                {/each}
                                            </div>
                                        {/if}

                                        <div class="grid grid-cols-2 gap-2">
                                            <button
                                                class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                                                {isCapturing 
                                                    ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-inner' 
                                                    : 'bg-white border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-600 hover:shadow-sm'}"
                                                on:click|stopPropagation={() => startCaptureForStep(step.id)}
                                            >
                                                <span>{isCapturing ? '📷' : '📷'}</span>
                                                {isCapturing ? '캡처 중...' : '영역 캡처'}
                                            </button>

                                            <button
                                                class="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-[11px] font-medium border transition-all
                                                {isAddingAttach
                                                    ? 'bg-amber-50 border-amber-200 text-amber-700 shadow-inner'
                                                    : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300 hover:text-amber-600 hover:shadow-sm'}"
                                                on:click|stopPropagation={() => toggleAttachmentSection(step.id)}
                                            >
                                                <span>📎</span>
                                                첨부 추가
                                            </button>
                                        </div>

                                        {#if isAddingAttach}
                                            <div class="bg-amber-50/50 border border-amber-100 rounded p-1.5" transition:slide={{ duration: 150 }}>
                                                <div class="relative flex items-center">
                                                    <input
                                                        type="text"
                                                        bind:value={attachmentTextInput}
                                                        class="w-full pl-2 pr-8 py-1.5 text-[11px] border border-amber-200 rounded focus:outline-none focus:ring-1 focus:ring-amber-400 bg-white"
                                                        placeholder="내용 입력 또는 이미지 붙여넣기 (Ctrl+V)"
                                                        on:keypress={(e) => e.key === 'Enter' && addTextAttachment(step.id)}
                                                        on:paste={(e) => handlePaste(e, step.id)}
                                                        autoFocus
                                                    />
                                                    <button 
                                                        class="absolute right-1 px-1.5 py-0.5 text-[10px] font-bold text-amber-600 hover:bg-amber-100 rounded"
                                                        disabled={!attachmentTextInput.trim()}
                                                        on:click={() => addTextAttachment(step.id)}
                                                    >
                                                        ↵
                                                    </button>
                                                </div>
                                            </div>
                                        {/if}

                                        {#if step.captures.length > 0 || step.attachments.length > 0}
                                            <div class="pt-1 border-t border-gray-50 flex flex-col gap-1.5">
                                                {#if step.captures.length > 0}
                                                    <div class="flex flex-wrap gap-1">
                                                        {#each step.captures as capture (capture.id)}
                                                            <div class="group inline-flex items-center gap-1 pl-1.5 pr-1 py-0.5 bg-blue-50/50 border border-blue-100 rounded text-[10px] text-blue-700">
                                                                <span class="opacity-80">슬라이드 {capture.slideIndex + 1}</span>
                                                                <button class="p-px hover:bg-blue-200 rounded-full text-blue-400 hover:text-blue-600" on:click={() => removeCapture(step.id, capture.id)}>
                                                                    <svg class="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18M6 6l12 12"/></svg>
                                                                </button>
                                                            </div>
                                                        {/each}
                                                    </div>
                                                {/if}

                                                {#if step.attachments.length > 0}
                                                    <div class="grid grid-cols-2 gap-1.5">
                                                        {#each step.attachments as attachment (attachment.id)}
                                                            <div class="relative group bg-gray-50 rounded border border-gray-100 overflow-hidden flex items-center">
                                                                {#if attachment.type === 'image'}
                                                                    <img src={attachment.data} alt="att" class="w-full h-12 object-cover" />
                                                                    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors"></div>
                                                                {:else}
                                                                    <div class="p-1.5 text-[10px] text-gray-600 leading-snug break-words w-full line-clamp-2">
                                                                        {attachment.data}
                                                                    </div>
                                                                {/if}
                                                                <button 
                                                                    class="absolute top-0.5 right-0.5 w-4 h-4 bg-white/90 shadow-sm rounded-full flex items-center justify-center text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    on:click={() => removeAttachment(step.id, attachment.id)}
                                                                >
                                                                    <svg class="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                                                                </button>
                                                            </div>
                                                        {/each}
                                                    </div>
                                                {/if}
                                            </div>
                                        {/if}

                                        <div class="pt-1 border-t border-gray-50 flex justify-end">
                                            <button 
                                                class="text-[10px] text-red-300 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors"
                                                on:click={() => handleRemoveStep(step.id)}
                                            >
                                                삭제
                                            </button>
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/each}

                    <div class="relative z-10 pl-7 pt-1 pb-4">
                        <button
                            class="w-full py-2 border border-dashed border-gray-300 rounded-lg text-gray-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-center gap-1.5 group bg-white/50"
                            on:click|stopPropagation={() => showAddStepPopup = !showAddStepPopup}
                        >
                            <span class="text-xs font-medium">＋ 다음 스텝 연결</span>
                        </button>

                        {#if showAddStepPopup}
                            <div
                                bind:this={popupRef}
                                class="absolute bottom-full left-7 right-0 mb-1 bg-white rounded-lg shadow-xl border border-gray-200 z-50 flex flex-col max-h-[350px] overflow-hidden"
                                transition:fly={{ y: 10, duration: 150 }}
                                on:click|stopPropagation
                            >
                                <div class="p-2 border-b border-gray-100 bg-gray-50/80 backdrop-blur sticky top-0">
                                    <div class="relative mb-1.5">
                                        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                                        <input
                                            type="text"
                                            bind:value={searchQuery}
                                            placeholder="작업 검색..."
                                            class="w-full pl-8 pr-2 py-1.5 text-xs bg-white border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                                            autoFocus
                                        />
                                    </div>
                                    <div class="flex gap-1 overflow-x-auto no-scrollbar pb-0.5">
                                        <button
                                            class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === 'all' ? 'bg-gray-700 text-white' : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                                            on:click={() => selectedCategoryTab = "all"}
                                        >
                                            All
                                        </button>
                                        {#each categories as category}
                                            <button
                                                class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === category ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                                                on:click={() => selectedCategoryTab = category}
                                            >
                                                {category}
                                            </button>
                                        {/each}
                                    </div>
                                </div>

                                <div class="flex-1 overflow-y-auto p-1 bg-white">
                                    {#if filteredSteps.length === 0}
                                        <div class="py-6 text-center text-gray-400">
                                            <p class="text-[10px]">일치하는 스텝이 없습니다</p>
                                        </div>
                                    {:else}
                                        {#each filteredSteps as step (step.id)}
                                            <button
                                                class="w-full text-left p-2 hover:bg-blue-50 rounded-md group transition-colors flex items-start gap-2 border-b border-gray-50 last:border-0"
                                                on:click={() => handleAddStep(step)}
                                            >
                                                <div class="flex-1 min-w-0">
                                                    <div class="flex items-center gap-1.5 mb-0.5">
                                                        <span class="inline-block px-1.5 py-px rounded bg-blue-100 text-blue-700 text-[9px] font-bold tracking-tight">
                                                            {step.values["step_category"] || "ETC"}
                                                        </span>
                                                        <span class="text-xs font-medium text-gray-800 group-hover:text-blue-700 truncate">
                                                            {step.values["purpose"] || "목적 없음"}
                                                        </span>
                                                    </div>
                                                    <div class="text-[10px] text-gray-400 truncate pl-0.5">
                                                        {step.values["action"] || step.values["expected_result"] || "-"}
                                                    </div>
                                                </div>
                                            </button>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    </div>

                    {#if workflowData.steps.length === 0}
                        <div class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 pointer-events-none pb-8">
                            <span class="text-xs opacity-50">스텝을 추가하세요</span>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    /* Custom Scrollbar for popup chips */
    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }
    .no-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
</style>
