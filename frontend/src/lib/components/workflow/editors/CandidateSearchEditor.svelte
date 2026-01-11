<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowData, WorkflowNode, WorkflowAction, SlideCapture } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";
    import { CORE_NODE_IDS } from "../utils/constants";
    import { generateNodeId } from "../utils/workflowAdapter";

    export let nodeId: string;
    export let node: WorkflowNode;
    export let workflow: WorkflowData;
    export let workflowActions: WorkflowAction[] = [];

    const dispatch = createEventDispatcher();

    // Get phenomenon node to access captures
    $: phenomenonNodeId = workflow?.meta?.coreNodes?.[0] || CORE_NODE_IDS.PHENOMENON;
    $: phenomenonNode = workflow?.nodes?.[phenomenonNodeId];
    $: allCaptures = phenomenonNode?.captures || [];

    // Track selected capture for adding actions
    let selectedCaptureIndex: number | null = null;
    let selectedActionId: string = workflowActions.length > 0 ? workflowActions[0].id : '';

    // Reactive: rebuild capture node map when workflow changes
    $: captureNodeMap = buildCaptureNodeMap(workflow, node);

    function buildCaptureNodeMap(wf: WorkflowData, n: WorkflowNode): Map<number, { id: string; node: WorkflowNode }> {
        const map = new Map<number, { id: string; node: WorkflowNode }>();
        if (!n.children || !wf?.nodes) return map;
        for (const childId of n.children) {
            const childNode = wf.nodes[childId];
            if (childNode && childNode.captureRef !== undefined) {
                map.set(childNode.captureRef, { id: childId, node: childNode });
            }
        }
        return map;
    }

    // Find capture nodes that are children of this node (uses reactive map)
    function getCaptureNode(captureRef: number): { id: string; node: WorkflowNode } | null {
        return captureNodeMap.get(captureRef) || null;
    }

    // Check if a capture is already added as candidate (has a node in children)
    function isCaptureAdded(captureIndex: number): boolean {
        return captureNodeMap.has(captureIndex);
    }

    // Check if capture is currently being edited (selected for action editing)
    function isCaptureEditing(captureIndex: number): boolean {
        return selectedCaptureIndex === captureIndex;
    }

    function updateWorkflow(updatedWorkflow: WorkflowData) {
        dispatch('change', updatedWorkflow);
    }

    function selectCapture(index: number) {
        selectedCaptureIndex = index;
        // Notify parent to highlight this capture on canvas
        dispatch('captureSelect', {
            captureIndex: index,
            slideIndex: allCaptures[index]?.slideIndex
        });
    }

    function addCaptureNode(captureIndex: number) {
        if (captureIndex < 0 || captureIndex >= allCaptures.length) return;

        const existing = getCaptureNode(captureIndex);
        if (existing) {
            // Already exists, just select it
            selectedCaptureIndex = captureIndex;
            return;
        }

        const updated = JSON.parse(JSON.stringify(workflow));
        const newId = generateNodeId();
        const capture = allCaptures[captureIndex];

        // Create capture reference node
        updated.nodes[newId] = {
            type: "Sequence",
            name: `캡처 #${captureIndex + 1} (슬라이드 ${capture.slideIndex + 1})`,
            captureRef: captureIndex,
            children: []
        };

        // Add to this node's children
        if (!updated.nodes[nodeId].children) {
            updated.nodes[nodeId].children = [];
        }
        updated.nodes[nodeId].children.push(newId);

        // Select this capture immediately to show action editor
        selectedCaptureIndex = captureIndex;

        updateWorkflow(updated);
    }

    function addActionToCapture(captureIndex: number) {
        if (!selectedActionId) return;

        const captureNode = getCaptureNode(captureIndex);
        if (!captureNode) {
            // Create capture node first
            addCaptureNode(captureIndex);
            // Then add action (will be handled on next render)
            return;
        }

        const updated = JSON.parse(JSON.stringify(workflow));
        const actionId = generateNodeId();
        const action = workflowActions.find(a => a.id === selectedActionId);

        // Create action node
        updated.nodes[actionId] = {
            type: "Action",
            actionId: selectedActionId,
            name: action?.name || '액션',
            params: action?.params?.reduce((acc: Record<string, string>, p) => {
                acc[p.id] = '';
                return acc;
            }, {}) || {}
        };

        // Add to capture node's children
        if (!updated.nodes[captureNode.id].children) {
            updated.nodes[captureNode.id].children = [];
        }
        updated.nodes[captureNode.id].children.push(actionId);

        updateWorkflow(updated);
    }

    function removeActionFromCapture(captureIndex: number, actionIndex: number) {
        const captureNode = getCaptureNode(captureIndex);
        if (!captureNode || !captureNode.node.children) return;

        const actionId = captureNode.node.children[actionIndex];
        if (!actionId) return;

        const updated = JSON.parse(JSON.stringify(workflow));

        // Remove action from capture node's children
        updated.nodes[captureNode.id].children = updated.nodes[captureNode.id].children.filter(
            (id: string) => id !== actionId
        );

        // Delete the action node
        delete updated.nodes[actionId];

        updateWorkflow(updated);
    }

    function removeCaptureNode(captureIndex: number) {
        const captureNode = getCaptureNode(captureIndex);
        if (!captureNode) return;

        const updated = JSON.parse(JSON.stringify(workflow));

        // Remove all children (actions) of the capture node
        if (captureNode.node.children) {
            for (const childId of captureNode.node.children) {
                delete updated.nodes[childId];
            }
        }

        // Remove capture node from this node's children
        updated.nodes[nodeId].children = updated.nodes[nodeId].children?.filter(
            (id: string) => id !== captureNode.id
        ) || [];

        // Delete the capture node
        delete updated.nodes[captureNode.id];

        updateWorkflow(updated);
        if (selectedCaptureIndex === captureIndex) {
            selectedCaptureIndex = null;
        }
    }
</script>

<div class="h-full flex flex-col">
    <!-- Section 1: Capture Selection -->
    <section class="flex-1 border-b border-gray-200 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 class="text-sm font-semibold text-gray-700">
                발생현상 선택
            </h3>
            <p class="text-xs text-gray-500 mt-1">
                분석할 발생현상 영역을 선택하세요
            </p>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
            {#if allCaptures.length === 0}
                <div class="text-center py-8 text-gray-400">
                    <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p class="text-sm">발생현상이 없습니다</p>
                    <p class="text-xs mt-1">먼저 발생현상 노드에서 영역을 캡처하세요</p>
                </div>
            {:else}
                <div class="space-y-3">
                    {#each allCaptures as capture, idx}
                        {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                        {@const isAdded = isCaptureAdded(idx)}
                        {@const isEditing = isCaptureEditing(idx)}
                        {@const captureNode = getCaptureNode(idx)}

                        <div
                            class="rounded-lg border-2 transition-all
                                   {isAdded || isEditing ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-300'}"
                        >
                            <!-- Capture header -->
                            <button
                                class="w-full flex items-center gap-3 p-3 text-left"
                                on:click={() => selectCapture(idx)}
                            >
                                <div
                                    class="w-8 h-8 rounded-lg border-2 flex items-center justify-center text-xs font-bold shrink-0"
                                    style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                                >
                                    {idx + 1}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm font-medium text-gray-800">
                                        슬라이드 {capture.slideIndex + 1}
                                    </div>
                                    <div class="text-xs text-gray-500">
                                        ({capture.x}, {capture.y}) {capture.width}x{capture.height}
                                    </div>
                                </div>
                                {#if isAdded}
                                    <span class="text-xs text-blue-600 font-medium">선택됨</span>
                                {/if}
                            </button>

                            <!-- Actions for this capture - show when editing OR when already added -->
                            {#if isEditing || isAdded}
                                <div class="border-t border-gray-200 p-3 bg-gray-50/50">
                                    {#if captureNode}
                                        <div class="text-xs font-medium text-gray-600 mb-2">
                                            탐색 액션 ({captureNode.node.children?.length || 0}개)
                                        </div>

                                        {#if captureNode.node.children && captureNode.node.children.length > 0}
                                            <div class="space-y-1 mb-3">
                                                {#each captureNode.node.children as actionId, actionIdx}
                                                    {@const actionNode = workflow.nodes[actionId]}
                                                    {#if actionNode}
                                                        <div class="flex items-center gap-2 p-2 bg-white rounded border border-gray-200 group">
                                                            <span class="w-5 h-5 rounded bg-green-100 text-green-600 text-xs flex items-center justify-center">
                                                                {actionIdx + 1}
                                                            </span>
                                                            <span class="flex-1 text-sm text-gray-700">
                                                                {actionNode.name || '액션'}
                                                            </span>
                                                            <button
                                                                class="w-5 h-5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                on:click|stopPropagation={() => removeActionFromCapture(idx, actionIdx)}
                                                            >
                                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                                </svg>
                                                            </button>
                                                        </div>
                                                    {/if}
                                                {/each}
                                            </div>
                                        {/if}
                                    {:else}
                                        <div class="text-xs text-gray-500 mb-2">
                                            원인 후보에 추가 중...
                                        </div>
                                    {/if}

                                    <!-- Add action -->
                                    <div class="flex gap-2">
                                        <select
                                            class="flex-1 text-xs border border-gray-300 rounded px-2 py-1.5"
                                            bind:value={selectedActionId}
                                        >
                                            {#each workflowActions as action}
                                                <option value={action.id}>{action.name}</option>
                                            {/each}
                                        </select>
                                        <button
                                            class="px-3 py-1.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                                            on:click={() => addActionToCapture(idx)}
                                        >
                                            추가
                                        </button>
                                    </div>
                                </div>
                            {:else}
                                <!-- Quick add button -->
                                <div class="border-t border-gray-200 p-2">
                                    <button
                                        class="w-full py-1.5 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                        on:click={() => addCaptureNode(idx)}
                                    >
                                        + 원인 후보로 추가
                                    </button>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </section>

    <!-- Section 2: Summary -->
    <section class="h-32 shrink-0 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 class="text-sm font-semibold text-gray-700">
                선택된 원인 후보 요약
            </h3>
        </div>
        <div class="flex-1 p-4 overflow-y-auto">
            {#if node.children && node.children.length > 0}
                <div class="flex flex-wrap gap-2">
                    {#each node.children as childId}
                        {@const childNode = workflow.nodes[childId]}
                        {#if childNode && childNode.captureRef !== undefined}
                            {@const captureIdx = childNode.captureRef}
                            {@const color = CAPTURE_COLORS[captureIdx % CAPTURE_COLORS.length]}
                            <div
                                class="px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1"
                                style="background-color: {color.bg}; color: {color.border}; border: 1px solid {color.border};"
                            >
                                <span>캡처 #{captureIdx + 1}</span>
                                <span class="text-gray-500">
                                    ({childNode.children?.length || 0}개 액션)
                                </span>
                                <button
                                    class="ml-1 hover:text-red-500"
                                    on:click={() => removeCaptureNode(captureIdx)}
                                >
                                    x
                                </button>
                            </div>
                        {/if}
                    {/each}
                </div>
            {:else}
                <p class="text-sm text-gray-400 text-center">
                    선택된 원인 후보가 없습니다
                </p>
            {/if}
        </div>
    </section>
</div>
