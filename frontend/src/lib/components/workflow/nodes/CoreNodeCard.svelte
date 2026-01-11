<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import { NODE_TYPE_COLORS, NODE_TYPE_NAMES, CORE_NODE_IDS } from "../utils/constants";
    import type { WorkflowNode } from "$lib/api/project";

    export let id: string;
    export let data: {
        nodeId: string;
        workflowNode: WorkflowNode;
        label: string;
        isCoreNode?: boolean;
        coreNodeType?: 'phenomenon' | 'candidateSearch' | 'causeDerivation';
    };
    export let selected: boolean = false;

    // Props for state control
    export let disabled: boolean = false;

    // Use data.workflowNode directly for better reactivity
    $: node = data.workflowNode;
    $: coreType = data.coreNodeType;
    // Force reactivity by tracking captures/children directly from data
    $: nodeCaptures = data.workflowNode?.captures;
    $: nodeChildren = data.workflowNode?.children;
    $: nodeDescription = data.workflowNode?.description;

    // Core node display names
    const coreNodeNames: Record<string, string> = {
        phenomenon: '발생현상',
        candidateSearch: '원인후보탐색',
        causeDerivation: '원인도출'
    };

    // Core node colors
    const coreNodeColors: Record<string, { bg: string; border: string; text: string; darkBg: string }> = {
        phenomenon: {
            bg: 'bg-red-50',
            border: 'border-red-400',
            text: 'text-red-700',
            darkBg: 'bg-red-500'
        },
        candidateSearch: {
            bg: 'bg-blue-50',
            border: 'border-blue-400',
            text: 'text-blue-700',
            darkBg: 'bg-blue-500'
        },
        causeDerivation: {
            bg: 'bg-purple-50',
            border: 'border-purple-400',
            text: 'text-purple-700',
            darkBg: 'bg-purple-500'
        }
    };

    $: colors = coreType ? coreNodeColors[coreType] : coreNodeColors.phenomenon;
    $: displayName = coreType ? coreNodeNames[coreType] : data.label;

    // Calculate state based on node content (reactive)
    type NodeState = 'empty' | 'partial' | 'complete';

    // Use reactive variables to trigger state recalculation
    $: state = (() => {
        if (coreType === 'phenomenon') {
            const hasCaptures = nodeCaptures && nodeCaptures.length > 0;
            const hasDescription = !!nodeDescription;
            if (!hasCaptures && !hasDescription) return 'empty' as NodeState;
            if (hasCaptures) return 'complete' as NodeState;
            return 'partial' as NodeState;
        }
        if (coreType === 'candidateSearch' || coreType === 'causeDerivation') {
            const hasChildren = nodeChildren && nodeChildren.length > 0;
            return hasChildren ? 'complete' as NodeState : 'empty' as NodeState;
        }
        return 'empty' as NodeState;
    })();

    // State-based styling
    $: stateStyles = {
        empty: 'border-dashed opacity-70',
        partial: 'border-solid',
        complete: 'border-solid'
    };

    // Summary text based on state (reactive)
    $: summaryText = (() => {
        if (state === 'empty') return '클릭하여 시작';

        if (coreType === 'phenomenon') {
            const captureCount = nodeCaptures?.length || 0;
            return captureCount > 0 ? `${captureCount}개 영역 캡처됨` : '설명 입력됨';
        }
        if (coreType === 'candidateSearch') {
            const childCount = nodeChildren?.length || 0;
            return `${childCount}개 원인 후보`;
        }
        if (coreType === 'causeDerivation') {
            const childCount = nodeChildren?.length || 0;
            return `${childCount}개 분석 항목`;
        }
        return '';
    })();

    // Index for display (1-based)
    $: nodeIndex = coreType === 'phenomenon' ? 1 : coreType === 'candidateSearch' ? 2 : 3;
</script>

<div
    class="rounded-xl border-2 shadow-md transition-all duration-200 cursor-pointer
           {colors.bg} {colors.border} {stateStyles[state]}
           {selected ? 'ring-2 ring-blue-500 shadow-xl scale-105' : 'hover:shadow-lg hover:scale-102'}
           {disabled ? 'opacity-40 cursor-not-allowed' : ''}"
    style="width: 200px; height: 120px;"
>
    <!-- Step Number Badge -->
    <div
        class="absolute -top-3 -left-3 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold text-white shadow-md {colors.darkBg}"
    >
        {nodeIndex}
    </div>

    <!-- Complete Check Badge -->
    {#if state === 'complete'}
        <div
            class="absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-white bg-green-500 shadow-md"
        >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
        </div>
    {/if}

    <!-- Content -->
    <div class="flex flex-col h-full p-4 justify-between">
        <!-- Title -->
        <div class="text-center">
            <h3 class="text-base font-bold {colors.text}">
                {displayName}
            </h3>
        </div>

        <!-- Summary -->
        <div class="text-center">
            <p class="text-xs text-gray-500 mt-1">
                {summaryText}
            </p>
        </div>

        <!-- Progress Indicator -->
        <div class="flex justify-center gap-1 mt-2">
            {#if state === 'empty'}
                <span class="w-2 h-2 rounded-full bg-gray-300"></span>
                <span class="w-2 h-2 rounded-full bg-gray-300"></span>
                <span class="w-2 h-2 rounded-full bg-gray-300"></span>
            {:else if state === 'partial'}
                <span class="w-2 h-2 rounded-full {colors.darkBg}"></span>
                <span class="w-2 h-2 rounded-full {colors.darkBg} opacity-50"></span>
                <span class="w-2 h-2 rounded-full bg-gray-300"></span>
            {:else}
                <span class="w-2 h-2 rounded-full {colors.darkBg}"></span>
                <span class="w-2 h-2 rounded-full {colors.darkBg}"></span>
                <span class="w-2 h-2 rounded-full {colors.darkBg}"></span>
            {/if}
        </div>
    </div>

    <!-- Handles for connections -->
    <!-- Left handle (for receiving from previous core node) -->
    {#if coreType !== 'phenomenon'}
        <Handle
            type="target"
            position={Position.Left}
            id="left"
            class="!bg-gray-500 !border-gray-600 !w-3 !h-3"
        />
    {/if}

    <!-- Right handle (for connecting to next core node) -->
    {#if coreType !== 'causeDerivation'}
        <Handle
            type="source"
            position={Position.Right}
            id="right"
            class="!bg-gray-500 !border-gray-600 !w-3 !h-3"
        />
    {/if}

    <!-- Bottom handle (for children) -->
    <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        class="!bg-gray-400 !border-gray-500 !w-2 !h-2"
    />
</div>

<style>
    .scale-102 {
        transform: scale(1.02);
    }
</style>
