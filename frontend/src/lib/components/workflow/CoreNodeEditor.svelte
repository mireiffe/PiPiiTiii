<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowData, WorkflowNode, WorkflowAction, SlideCapture } from "$lib/api/project";
    import { CORE_NODE_IDS } from "./utils/constants";
    import PhenomenonEditor from "./editors/PhenomenonEditor.svelte";
    import CandidateSearchEditor from "./editors/CandidateSearchEditor.svelte";
    import CauseDerivationEditor from "./editors/CauseDerivationEditor.svelte";

    export let nodeId: string;
    export let workflow: WorkflowData;
    export let workflowActions: WorkflowAction[] = [];
    export let captureMode: boolean = false;

    const dispatch = createEventDispatcher();

    $: node = workflow?.nodes?.[nodeId];
    $: coreNodeType = getCoreNodeType(nodeId);

    function getCoreNodeType(id: string): 'phenomenon' | 'candidateSearch' | 'causeDerivation' | null {
        const coreNodes = workflow?.meta?.coreNodes || [
            CORE_NODE_IDS.PHENOMENON,
            CORE_NODE_IDS.CANDIDATE_SEARCH,
            CORE_NODE_IDS.CAUSE_DERIVATION
        ];

        if (id === CORE_NODE_IDS.PHENOMENON || coreNodes[0] === id) {
            return 'phenomenon';
        }
        if (id === CORE_NODE_IDS.CANDIDATE_SEARCH || coreNodes[1] === id) {
            return 'candidateSearch';
        }
        if (id === CORE_NODE_IDS.CAUSE_DERIVATION || coreNodes[2] === id) {
            return 'causeDerivation';
        }
        return null;
    }

    const coreNodeTitles: Record<string, string> = {
        phenomenon: '발생현상',
        candidateSearch: '원인후보탐색',
        causeDerivation: '원인도출'
    };

    const coreNodeColors: Record<string, { bg: string; border: string; text: string }> = {
        phenomenon: { bg: 'bg-red-50', border: 'border-red-400', text: 'text-red-700' },
        candidateSearch: { bg: 'bg-blue-50', border: 'border-blue-400', text: 'text-blue-700' },
        causeDerivation: { bg: 'bg-purple-50', border: 'border-purple-400', text: 'text-purple-700' }
    };

    $: colors = coreNodeType ? coreNodeColors[coreNodeType] : coreNodeColors.phenomenon;
    $: title = coreNodeType ? coreNodeTitles[coreNodeType] : '노드 편집';

    function handleClose() {
        dispatch('close');
    }

    function handleChange(event: CustomEvent<WorkflowData>) {
        dispatch('change', event.detail);
    }

    function handleRequestCaptureMode() {
        dispatch('requestCaptureMode');
    }

    function handleCaptureSelect(event: CustomEvent<{ captureIndex: number; slideIndex: number }>) {
        dispatch('captureSelect', event.detail);
    }
</script>

<div class="h-full flex flex-col bg-white">
    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 border-b {colors.border} {colors.bg}">
        <div class="flex items-center gap-3">
            <button
                class="p-1 hover:bg-white/50 rounded transition-colors"
                on:click={handleClose}
                title="뒤로가기"
            >
                <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                </svg>
            </button>
            <h2 class="text-lg font-bold {colors.text}">
                {title}
            </h2>
        </div>
        <button
            class="px-3 py-1.5 text-sm text-gray-600 hover:bg-white/50 rounded transition-colors"
            on:click={handleClose}
        >
            닫기
        </button>
    </header>

    <!-- Content -->
    <div class="flex-1 overflow-hidden">
        {#if coreNodeType === 'phenomenon' && node}
            <PhenomenonEditor
                {nodeId}
                {node}
                {workflow}
                {captureMode}
                on:change={handleChange}
                on:requestCaptureMode={handleRequestCaptureMode}
            />
        {:else if coreNodeType === 'candidateSearch' && node}
            <CandidateSearchEditor
                {nodeId}
                {node}
                {workflow}
                {workflowActions}
                on:change={handleChange}
                on:captureSelect={handleCaptureSelect}
            />
        {:else if coreNodeType === 'causeDerivation' && node}
            <CauseDerivationEditor
                {nodeId}
                {node}
                {workflow}
                {workflowActions}
                on:change={handleChange}
            />
        {:else}
            <div class="flex items-center justify-center h-full text-gray-400">
                노드를 찾을 수 없습니다
            </div>
        {/if}
    </div>
</div>
