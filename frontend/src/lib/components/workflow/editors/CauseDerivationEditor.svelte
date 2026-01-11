<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowData, WorkflowNode, WorkflowAction } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";
    import { CORE_NODE_IDS } from "../utils/constants";
    import { generateNodeId } from "../utils/workflowAdapter";

    export let nodeId: string;
    export let node: WorkflowNode;
    export let workflow: WorkflowData;
    export let workflowActions: WorkflowAction[] = [];

    const dispatch = createEventDispatcher();

    // Get candidate search node to access analyzed captures
    $: candidateSearchNodeId = workflow?.meta?.coreNodes?.[1] || CORE_NODE_IDS.CANDIDATE_SEARCH;
    $: candidateSearchNode = workflow?.nodes?.[candidateSearchNodeId];

    // Get phenomenon node for capture colors
    $: phenomenonNodeId = workflow?.meta?.coreNodes?.[0] || CORE_NODE_IDS.PHENOMENON;
    $: phenomenonNode = workflow?.nodes?.[phenomenonNodeId];
    $: allCaptures = phenomenonNode?.captures || [];

    // Get candidates (capture nodes from candidate search)
    $: candidates = getCandidates();

    function getCandidates(): Array<{ id: string; node: WorkflowNode; captureRef: number }> {
        if (!candidateSearchNode?.children) return [];

        return candidateSearchNode.children
            .map((childId: string) => {
                const childNode = workflow.nodes[childId];
                if (childNode && childNode.captureRef !== undefined) {
                    return { id: childId, node: childNode, captureRef: childNode.captureRef };
                }
                return null;
            })
            .filter((c): c is { id: string; node: WorkflowNode; captureRef: number } => c !== null);
    }

    let selectedCandidateId: string | null = null;
    let selectedActionId: string = workflowActions.length > 0 ? workflowActions[0].id : '';

    function updateWorkflow(updatedWorkflow: WorkflowData) {
        dispatch('change', updatedWorkflow);
    }

    // Get analysis nodes for this cause derivation node
    function getAnalysisNodes(): Array<{ id: string; node: WorkflowNode }> {
        if (!node.children) return [];

        return node.children
            .map((childId: string) => {
                const childNode = workflow.nodes[childId];
                if (childNode) {
                    return { id: childId, node: childNode };
                }
                return null;
            })
            .filter((c): c is { id: string; node: WorkflowNode } => c !== null);
    }

    $: analysisNodes = getAnalysisNodes();

    function addAnalysisForCandidate(candidateId: string) {
        const candidate = candidates.find(c => c.id === candidateId);
        if (!candidate) return;

        const updated = JSON.parse(JSON.stringify(workflow));
        const analysisId = generateNodeId();

        // Create analysis sequence node
        updated.nodes[analysisId] = {
            type: "Sequence",
            name: `${candidate.node.name} 분석`,
            candidateRef: candidateId,
            children: []
        };

        // Add to this node's children
        if (!updated.nodes[nodeId].children) {
            updated.nodes[nodeId].children = [];
        }
        updated.nodes[nodeId].children.push(analysisId);

        updateWorkflow(updated);
    }

    function addActionToAnalysis(analysisId: string) {
        if (!selectedActionId) return;

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

        // Add to analysis node's children
        if (!updated.nodes[analysisId].children) {
            updated.nodes[analysisId].children = [];
        }
        updated.nodes[analysisId].children.push(actionId);

        updateWorkflow(updated);
    }

    function addConditionToAnalysis(analysisId: string) {
        const updated = JSON.parse(JSON.stringify(workflow));
        const conditionId = generateNodeId();

        // Create condition node
        updated.nodes[conditionId] = {
            type: "Condition",
            name: "조건 분기"
        };

        // Add to analysis node's children
        if (!updated.nodes[analysisId].children) {
            updated.nodes[analysisId].children = [];
        }
        updated.nodes[analysisId].children.push(conditionId);

        updateWorkflow(updated);
    }

    function removeAnalysis(analysisId: string) {
        const updated = JSON.parse(JSON.stringify(workflow));

        // Remove all children of the analysis node
        const analysisNode = updated.nodes[analysisId];
        if (analysisNode?.children) {
            for (const childId of analysisNode.children) {
                delete updated.nodes[childId];
            }
        }

        // Remove from this node's children
        updated.nodes[nodeId].children = updated.nodes[nodeId].children?.filter(
            (id: string) => id !== analysisId
        ) || [];

        // Delete the analysis node
        delete updated.nodes[analysisId];

        updateWorkflow(updated);
    }

    function removeNodeFromAnalysis(analysisId: string, childId: string) {
        const updated = JSON.parse(JSON.stringify(workflow));

        // Remove from analysis node's children
        updated.nodes[analysisId].children = updated.nodes[analysisId].children?.filter(
            (id: string) => id !== childId
        ) || [];

        // Delete the child node
        delete updated.nodes[childId];

        updateWorkflow(updated);
    }
</script>

<div class="h-full flex flex-col">
    <!-- Section 1: Candidates List -->
    <section class="flex-1 border-b border-gray-200 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 class="text-sm font-semibold text-gray-700">
                도출된 원인 후보
            </h3>
            <p class="text-xs text-gray-500 mt-1">
                원인후보탐색에서 선택된 후보들입니다
            </p>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
            {#if candidates.length === 0}
                <div class="text-center py-8 text-gray-400">
                    <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    <p class="text-sm">도출된 원인 후보가 없습니다</p>
                    <p class="text-xs mt-1">먼저 원인후보탐색에서 후보를 선택하세요</p>
                </div>
            {:else}
                <div class="space-y-2">
                    {#each candidates as candidate}
                        {@const color = CAPTURE_COLORS[candidate.captureRef % CAPTURE_COLORS.length]}
                        {@const hasAnalysis = analysisNodes.some(a => a.node.candidateRef === candidate.id)}

                        <div class="p-3 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-shadow">
                            <div class="flex items-center gap-3">
                                <div
                                    class="w-8 h-8 rounded-lg border-2 flex items-center justify-center text-xs font-bold shrink-0"
                                    style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                                >
                                    {candidate.captureRef + 1}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm font-medium text-gray-800">
                                        {candidate.node.name}
                                    </div>
                                    <div class="text-xs text-gray-500">
                                        {candidate.node.children?.length || 0}개 탐색 액션
                                    </div>
                                </div>
                                {#if hasAnalysis}
                                    <span class="text-xs text-purple-600 font-medium">분석 중</span>
                                {:else}
                                    <button
                                        class="px-2 py-1 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
                                        on:click={() => addAnalysisForCandidate(candidate.id)}
                                    >
                                        분석 추가
                                    </button>
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </section>

    <!-- Section 2: Analysis Management -->
    <section class="flex-1 overflow-hidden flex flex-col">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 class="text-sm font-semibold text-gray-700">
                분석 항목 ({analysisNodes.length}개)
            </h3>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
            {#if analysisNodes.length === 0}
                <div class="text-center py-6 text-gray-400">
                    <p class="text-sm">분석 항목이 없습니다</p>
                    <p class="text-xs mt-1">위 후보에서 "분석 추가"를 클릭하세요</p>
                </div>
            {:else}
                <div class="space-y-4">
                    {#each analysisNodes as analysis, idx}
                        <div class="border border-purple-200 rounded-lg overflow-hidden">
                            <!-- Analysis header -->
                            <div class="flex items-center justify-between px-3 py-2 bg-purple-50">
                                <div class="flex items-center gap-2">
                                    <span class="w-5 h-5 rounded bg-purple-500 text-white text-xs flex items-center justify-center">
                                        {idx + 1}
                                    </span>
                                    <span class="text-sm font-medium text-purple-700">
                                        {analysis.node.name}
                                    </span>
                                </div>
                                <button
                                    class="text-xs text-red-500 hover:text-red-700"
                                    on:click={() => removeAnalysis(analysis.id)}
                                >
                                    삭제
                                </button>
                            </div>

                            <!-- Analysis children -->
                            <div class="p-3 space-y-2">
                                {#if analysis.node.children && analysis.node.children.length > 0}
                                    {#each analysis.node.children as childId, childIdx}
                                        {@const childNode = workflow.nodes[childId]}
                                        {#if childNode}
                                            <div class="flex items-center gap-2 p-2 bg-gray-50 rounded group">
                                                <span class="text-xs text-gray-400">{childIdx + 1}.</span>
                                                <span class="px-1.5 py-0.5 text-[10px] rounded
                                                    {childNode.type === 'Action' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}">
                                                    {childNode.type === 'Action' ? '액션' : '조건'}
                                                </span>
                                                <span class="flex-1 text-sm text-gray-700">
                                                    {childNode.name || (childNode.type === 'Condition' ? '조건 분기' : '액션')}
                                                </span>
                                                <button
                                                    class="w-5 h-5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    on:click={() => removeNodeFromAnalysis(analysis.id, childId)}
                                                >
                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            </div>
                                        {/if}
                                    {/each}
                                {/if}

                                <!-- Add buttons -->
                                <div class="flex gap-2 pt-2">
                                    <select
                                        class="flex-1 text-xs border border-gray-300 rounded px-2 py-1.5"
                                        bind:value={selectedActionId}
                                    >
                                        {#each workflowActions as action}
                                            <option value={action.id}>{action.name}</option>
                                        {/each}
                                    </select>
                                    <button
                                        class="px-2 py-1.5 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                                        on:click={() => addActionToAnalysis(analysis.id)}
                                    >
                                        액션
                                    </button>
                                    <button
                                        class="px-2 py-1.5 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
                                        on:click={() => addConditionToAnalysis(analysis.id)}
                                    >
                                        조건
                                    </button>
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </section>
</div>
