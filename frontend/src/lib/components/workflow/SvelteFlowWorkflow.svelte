<script lang="ts">
    import { createEventDispatcher, onMount, setContext } from "svelte";
    import {
        SvelteFlow,
        Background,
        Controls,
        MiniMap,
        type Node,
        type Edge,
    } from "@xyflow/svelte";
    import "@xyflow/svelte/dist/style.css";

    import type {
        WorkflowData,
        WorkflowNode,
        WorkflowAction,
        SlideCapture,
    } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";

    import { nodeTypes } from "./nodes";
    import { NODE_TYPE_NAMES, MAX_HISTORY, CORE_NODE_IDS } from "./utils/constants";
    import { workflowToNodes, workflowToEdges, generateNodeId } from "./utils/workflowAdapter";
    import { isCoreNodeWorkflow } from "./utils/layoutTree";
    import CoreNodeEditor from "./CoreNodeEditor.svelte";

    // Props
    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];
    export let readonly = false;

    const dispatch = createEventDispatcher();

    // Provide workflow actions to child node components via context
    setContext("workflowActions", workflowActions);

    // SvelteFlow node/edge arrays (reactive)
    let nodes: Node[] = [];
    let edges: Edge[] = [];

    // State
    let selectedNodeId: string | null = null;
    let contextMenu = { show: false, x: 0, y: 0, nodeId: "" };

    // Core node editing state
    let editingCoreNode: string | null = null;
    export let captureMode: boolean = false;

    // History
    let historyStack: WorkflowData[] = [];
    let historyIndex = -1;

    // Modal
    let showAddModal = false;
    let addModalParentId: string | null = null;
    let newNodeType: "Selector" | "Sequence" | "Condition" | "Action" = "Action";
    let newNodeActionId: string = "";

    // Reactivity
    $: if (workflow && historyStack.length === 0) {
        pushHistory(workflow);
    }

    $: if (workflow) {
        updateFlowData();
        // Reset selection if node no longer exists
        if (selectedNodeId && !workflow.nodes[selectedNodeId]) {
            selectedNodeId = null;
        }
    } else {
        nodes = [];
        edges = [];
    }

    $: selectedNode = selectedNodeId && workflow?.nodes?.[selectedNodeId]
        ? workflow.nodes[selectedNodeId]
        : null;

    $: selectedAction = selectedNode?.type === "Action"
        ? getActionInfo(selectedNode.actionId)
        : null;

    // Dispatch event when node selection changes
    $: {
        dispatch("nodeSelect", {
            nodeId: selectedNodeId,
            isPhenomenon: selectedNode?.type === "Phenomenon"
        });
    }

    $: canUndo = historyIndex > 0;
    $: canRedo = historyIndex < historyStack.length - 1;

    // Update SvelteFlow data when workflow changes
    function updateFlowData() {
        if (!workflow) {
            nodes = [];
            edges = [];
            return;
        }
        const newNodes = workflowToNodes(workflow);
        const newEdges = workflowToEdges(workflow);

        // Mark root node
        newNodes.forEach((node) => {
            node.data.isRoot = node.id === workflow?.rootId;
        });

        nodes = newNodes;
        edges = newEdges;
    }

    // History Management
    function pushHistory(state: WorkflowData) {
        historyStack = historyStack.slice(0, historyIndex + 1);
        historyStack.push(JSON.parse(JSON.stringify(state)));
        if (historyStack.length > MAX_HISTORY) {
            historyStack = historyStack.slice(1);
        }
        historyIndex = historyStack.length - 1;
    }

    function undo() {
        if (historyIndex > 0) {
            historyIndex--;
            dispatch("change", JSON.parse(JSON.stringify(historyStack[historyIndex])));
        }
    }

    function redo() {
        if (historyIndex < historyStack.length - 1) {
            historyIndex++;
            dispatch("change", JSON.parse(JSON.stringify(historyStack[historyIndex])));
        }
    }

    function updateWorkflow(newWorkflow: WorkflowData) {
        pushHistory(newWorkflow);
        dispatch("change", newWorkflow);
    }

    // Check if workflow uses core node layout
    $: useCoreLayout = isCoreNodeWorkflow(workflow);

    // Check if phenomenon is filled (has captures or description)
    function isPhenomenonFilled(): boolean {
        if (!workflow) return false;
        const phenomenonId = workflow.meta?.coreNodes?.[0] || CORE_NODE_IDS.PHENOMENON;
        const phenomenonNode = workflow.nodes[phenomenonId];
        if (!phenomenonNode) return false;
        return (phenomenonNode.captures && phenomenonNode.captures.length > 0) ||
               !!phenomenonNode.description;
    }

    // Check if a node is a core node
    function isCoreNode(nodeId: string): boolean {
        if (!workflow?.meta?.coreNodes) {
            return nodeId === CORE_NODE_IDS.PHENOMENON ||
                   nodeId === CORE_NODE_IDS.CANDIDATE_SEARCH ||
                   nodeId === CORE_NODE_IDS.CAUSE_DERIVATION;
        }
        return workflow.meta.coreNodes.includes(nodeId);
    }

    // Get core node type
    function getCoreNodeType(nodeId: string): 'phenomenon' | 'candidateSearch' | 'causeDerivation' | null {
        const coreNodes = workflow?.meta?.coreNodes || [
            CORE_NODE_IDS.PHENOMENON,
            CORE_NODE_IDS.CANDIDATE_SEARCH,
            CORE_NODE_IDS.CAUSE_DERIVATION
        ];

        if (nodeId === coreNodes[0]) return 'phenomenon';
        if (nodeId === coreNodes[1]) return 'candidateSearch';
        if (nodeId === coreNodes[2]) return 'causeDerivation';
        return null;
    }

    // Event Handlers (xyflow/svelte uses props-based handlers)
    function handleNodeClick({ node, event }: { node: Node; event: MouseEvent | TouchEvent }) {
        console.log("handleNodeClick", node.id);

        // If this is a core node in core layout mode, open editor
        if (useCoreLayout && isCoreNode(node.id)) {
            const coreType = getCoreNodeType(node.id);

            // Check if phenomenon is filled before allowing other nodes
            if (coreType !== 'phenomenon' && !isPhenomenonFilled()) {
                // Could show a toast here
                console.log("Please fill phenomenon first");
                return;
            }

            // IMPORTANT: Set selectedNodeId first so nodeSelect event fires
            selectedNodeId = node.id;
            editingCoreNode = node.id;
            return;
        }

        selectedNodeId = node.id;
        closeContextMenu();
    }

    function handleNodeContextMenu({ node, event }: { node: Node; event: MouseEvent }) {
        console.log("handleNodeContextMenu", node.id);
        if (readonly) return;
        event.preventDefault();
        selectedNodeId = node.id;
        contextMenu = {
            show: true,
            x: event.clientX,
            y: event.clientY,
            nodeId: node.id,
        };
    }

    function handlePaneClick({ event }: { event: MouseEvent }) {
        console.log("handlePaneClick");
        selectedNodeId = null;
        closeContextMenu();
    }

    function closeContextMenu() {
        contextMenu.show = false;
    }

    // Node Operations
    function openAddModal(parentId: string) {
        addModalParentId = parentId;
        newNodeType = "Action";
        newNodeActionId = workflowActions.length > 0 ? workflowActions[0].id : "";
        showAddModal = true;
        closeContextMenu();
    }

    function confirmAddNode() {
        if (!workflow || !addModalParentId) return;
        const newId = generateNodeId();

        const newNode: WorkflowNode = {
            type: newNodeType,
            children: newNodeType !== "Action" && newNodeType !== "Condition" ? [] : undefined,
        };

        if (newNodeType === "Action" && newNodeActionId) {
            newNode.actionId = newNodeActionId;
            const action = getActionInfo(newNodeActionId);
            if (action) {
                newNode.name = action.name;
                newNode.params = {};
                action.params.forEach((p) => (newNode.params![p.id] = ""));
            }
        } else {
            newNode.name = NODE_TYPE_NAMES[newNodeType];
        }

        const updated = JSON.parse(JSON.stringify(workflow));
        updated.nodes[newId] = newNode;
        updated.nodes[addModalParentId].children = updated.nodes[addModalParentId].children || [];
        updated.nodes[addModalParentId].children.push(newId);

        updateWorkflow(updated);
        showAddModal = false;
        selectedNodeId = newId;
    }

    function deleteNode(nodeId: string) {
        if (!workflow || nodeId === workflow.rootId) return;
        const updated = JSON.parse(JSON.stringify(workflow));

        // Unlink from parent
        Object.values(updated.nodes).forEach((n: any) => {
            if (n.children?.includes(nodeId)) {
                n.children = n.children.filter((c: string) => c !== nodeId);
            }
        });

        // Collect garbage (delete node and all descendants)
        const toRemove = new Set<string>();
        const collect = (id: string) => {
            toRemove.add(id);
            updated.nodes[id]?.children?.forEach(collect);
        };
        collect(nodeId);
        toRemove.forEach((id) => delete updated.nodes[id]);

        updateWorkflow(updated);
        selectedNodeId = null;
        closeContextMenu();
    }

    function deleteWorkflow() {
        if (confirm("워크플로우 전체를 삭제하시겠습니까?")) {
            dispatch("change", null);
            historyStack = [];
            historyIndex = -1;
        }
    }

    function createInitialWorkflow() {
        updateWorkflow({
            rootId: "phenomenon",
            nodes: {
                "phenomenon": {
                    type: "Phenomenon",
                    name: "발생현상",
                    description: "",
                    captures: [],
                    children: []
                },
                "candidate_search": {
                    type: "Sequence",
                    name: "원인후보탐색",
                    children: []
                },
                "cause_derivation": {
                    type: "Selector",
                    name: "원인도출",
                    children: []
                }
            },
            meta: {
                coreNodes: ["phenomenon", "candidate_search", "cause_derivation"],
                version: 2
            },
        });
        selectedNodeId = "phenomenon";
    }

    // Helpers
    function getActionInfo(actionId: string | undefined) {
        return actionId ? workflowActions.find((a) => a.id === actionId) : undefined;
    }

    function getNodeDisplayName(node: WorkflowNode): string {
        if (node.type === "Action") {
            const action = getActionInfo(node.actionId);
            return action ? action.name : node.name || "알 수 없는 액션";
        }
        return node.name || NODE_TYPE_NAMES[node.type];
    }

    // Node Updates
    function updateNodeName(nodeId: string, name: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]) {
            updated.nodes[nodeId].name = name;
            updateWorkflow(updated);
        }
    }

    function updateNodeDescription(nodeId: string, description: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]) {
            updated.nodes[nodeId].description = description;
            updateWorkflow(updated);
        }
    }

    function updateNodeType(nodeId: string, newType: any) {
        if (!workflow || nodeId === workflow.rootId) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (!node) return;

        node.type = newType;
        if (newType === "Action" || newType === "Condition") {
            if (node.children) {
                const collect = (id: string) => {
                    const n = updated.nodes[id];
                    if (n?.children) n.children.forEach(collect);
                    delete updated.nodes[id];
                };
                node.children.forEach(collect);
                delete node.children;
            }
            if (newType === "Action") {
                node.actionId = workflowActions[0]?.id;
                const action = getActionInfo(node.actionId);
                if (action) {
                    node.name = action.name;
                    node.params = {};
                    action.params.forEach((p) => (node.params![p.id] = ""));
                }
            }
        } else if (!node.children) {
            node.children = [];
        }

        if (newType !== "Action") {
            delete node.actionId;
            delete node.params;
            node.name = NODE_TYPE_NAMES[newType];
        }
        updateWorkflow(updated);
    }

    function updateNodeAction(nodeId: string, actionId: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Action") {
            node.actionId = actionId;
            const action = getActionInfo(actionId);
            if (action) {
                node.name = action.name;
                node.params = {};
                action.params.forEach((p) => (node.params![p.id] = ""));
            }
            updateWorkflow(updated);
        }
    }

    function updateNodeParam(nodeId: string, paramId: string, value: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Action") {
            node.params = node.params || {};
            node.params[paramId] = value;
            updateWorkflow(updated);
        }
    }

    // Capture functions
    function addCapture(nodeId: string, capture: SlideCapture) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Phenomenon") {
            if (!node.captures) node.captures = [];
            node.captures.push(capture);
            updateWorkflow(updated);
        }
    }

    function removeCapture(nodeId: string, captureIndex: number) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.captures && captureIndex >= 0 && captureIndex < node.captures.length) {
            node.captures.splice(captureIndex, 1);
            updateWorkflow(updated);
        }
    }

    // Export functions for external use
    export function addCaptureToNode(nodeId: string, capture: SlideCapture) {
        addCapture(nodeId, capture);
    }

    export function getPhenomenonNodeId(): string | null {
        if (!workflow) return null;
        for (const [id, node] of Object.entries(workflow.nodes)) {
            if (node.type === "Phenomenon") return id;
        }
        return null;
    }

    export function getSelectedPhenomenonCaptures(): Array<SlideCapture & { colorIndex: number }> {
        if (!selectedNodeId || !workflow) return [];
        const node = workflow.nodes[selectedNodeId];
        if (!node || node.type !== "Phenomenon" || !node.captures) return [];
        return node.captures.map((capture, idx) => ({
            ...capture,
            colorIndex: idx
        }));
    }

    export function getPhenomenonCaptures(): Array<SlideCapture & { colorIndex: number }> {
        if (!workflow) return [];
        const phenomenonId = getPhenomenonNodeId();
        if (!phenomenonId) return [];
        const node = workflow.nodes[phenomenonId];
        if (!node || node.type !== "Phenomenon" || !node.captures) return [];
        return node.captures.map((capture, idx) => ({
            ...capture,
            colorIndex: idx
        }));
    }

    export function isPhenomenonSelected(): boolean {
        if (!selectedNodeId || !workflow) return false;
        const node = workflow.nodes[selectedNodeId];
        return node?.type === "Phenomenon";
    }

    // Keyboard handling
    function handleKeydown(e: KeyboardEvent) {
        if (readonly) return;
        if ((e.ctrlKey || e.metaKey) && e.key === "z") {
            e.preventDefault();
            e.shiftKey ? redo() : undo();
        }
        if (e.key === "Delete" && selectedNodeId && selectedNodeId !== workflow?.rootId) {
            deleteNode(selectedNodeId);
        }
    }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="workflow-container flex flex-col h-full bg-gray-50 select-none overflow-hidden relative">
    {#if !workflow || !workflow.nodes || Object.keys(workflow.nodes).length === 0}
        <!-- Empty State -->
        <div class="flex flex-col items-center justify-center h-full text-gray-400 z-10">
            <svg class="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            <p class="mb-4">워크플로우가 비어있습니다</p>
            {#if !readonly}
                <button
                    class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                    on:click={createInitialWorkflow}
                >
                    워크플로우 생성
                </button>
            {/if}
        </div>
    {:else if editingCoreNode && useCoreLayout}
        <!-- Core Node Editor (Full Screen) -->
        <CoreNodeEditor
            nodeId={editingCoreNode}
            {workflow}
            {workflowActions}
            {captureMode}
            on:close={() => editingCoreNode = null}
            on:change={(e) => updateWorkflow(e.detail)}
            on:requestCaptureMode={() => dispatch('requestCaptureMode')}
            on:captureSelect={(e) => dispatch('captureSelect', e.detail)}
        />
    {:else}
        <!-- Toolbar -->
        {#if !readonly}
            <div class="absolute top-2 left-2 right-2 z-20 flex justify-between pointer-events-none">
                <div class="bg-white/90 backdrop-blur border border-gray-200 rounded-lg shadow-sm p-1 flex items-center gap-1 pointer-events-auto">
                    <button
                        class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
                        on:click={undo}
                        disabled={!canUndo}
                        title="실행취소 (Ctrl+Z)"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                        </svg>
                    </button>
                    <button
                        class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
                        on:click={redo}
                        disabled={!canRedo}
                        title="다시실행 (Ctrl+Shift+Z)"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                        </svg>
                    </button>
                </div>
                <button
                    class="bg-white/90 text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm text-xs font-medium pointer-events-auto"
                    on:click={deleteWorkflow}
                >
                    초기화
                </button>
            </div>
        {/if}

        <!-- SvelteFlow Canvas -->
        <div class="flex-1">
            <SvelteFlow
                bind:nodes
                bind:edges
                {nodeTypes}
                fitView
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
                panOnScroll={true}
                zoomOnScroll={true}
                onnodeclick={handleNodeClick}
                onnodecontextmenu={handleNodeContextMenu}
                onpaneclick={handlePaneClick}
            >
                <Background />
                <Controls />
                <MiniMap />

                <!-- Custom SVG markers for arrows -->
                <svg>
                    <defs>
                        <marker id="loopback-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                            <path d="M0,0 L0,6 L9,3 z" fill="#EF4444" />
                        </marker>
                    </defs>
                </svg>
            </SvelteFlow>
        </div>

        <!-- Edit Panel -->
        {#if selectedNode && !readonly && workflow}
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-3 shadow-lg z-30 max-h-[250px] overflow-y-auto"
                on:click|stopPropagation
                on:mousedown|stopPropagation
            >
                <div class="flex items-center justify-between mb-3">
                    <h3 class="font-bold text-gray-800 text-sm flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                        노드 설정
                    </h3>
                    <button
                        class="text-gray-400 hover:text-gray-600"
                        on:click={() => (selectedNodeId = null)}
                    >
                        ✕
                    </button>
                </div>

                {#if selectedNode.type === "Phenomenon"}
                    <!-- Phenomenon node settings -->
                    <div class="space-y-3">
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">타입</label>
                            <div class="text-sm font-medium text-red-600">
                                {NODE_TYPE_NAMES[selectedNode.type]}
                            </div>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">현상 설명</label>
                            <textarea
                                class="w-full text-sm border rounded px-2 py-1.5 resize-none"
                                rows="2"
                                placeholder="발생한 현상을 설명하세요..."
                                value={selectedNode.description || ""}
                                on:change={(e) => updateNodeDescription(selectedNodeId, e.currentTarget.value)}
                            ></textarea>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-gray-500 mb-1">
                                캡처 영역 ({selectedNode.captures?.length || 0}개)
                            </label>
                            <p class="text-[10px] text-gray-400 mb-2">
                                캔버스에서 마우스 좌클릭+드래그로 캡처 영역을 지정하세요
                            </p>
                            {#if selectedNode.captures && selectedNode.captures.length > 0}
                                <div class="space-y-1.5 max-h-[100px] overflow-y-auto pr-1">
                                    {#each selectedNode.captures as capture, idx}
                                        {@const color = CAPTURE_COLORS[idx % CAPTURE_COLORS.length]}
                                        <div class="flex items-center gap-2 group">
                                            <div
                                                class="w-6 h-6 rounded border-2 flex items-center justify-center text-[10px] font-bold shrink-0"
                                                style="background-color: {color.bg}; border-color: {color.border}; color: {color.border};"
                                            >
                                                {idx + 1}
                                            </div>
                                            <div class="flex-1 text-[10px] text-gray-600 min-w-0">
                                                <span class="font-medium">슬라이드 {capture.slideIndex}</span>
                                                <span class="text-gray-400 ml-1">({capture.x}, {capture.y}) {capture.width}×{capture.height}</span>
                                            </div>
                                            <button
                                                class="w-5 h-5 bg-red-100 text-red-500 rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center hover:bg-red-200 shrink-0"
                                                on:click={() => removeCapture(selectedNodeId, idx)}
                                                title="캡처 삭제"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-xs text-gray-400 italic py-2">캡처된 영역이 없습니다</div>
                            {/if}
                        </div>
                    </div>
                {:else}
                    <!-- Other node types settings -->
                    <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-3">
                            <div>
                                <label class="block text-xs font-medium text-gray-500 mb-1">타입</label>
                                {#if selectedNodeId === workflow.rootId}
                                    <div class="text-sm font-medium">
                                        {NODE_TYPE_NAMES[selectedNode.type]}
                                    </div>
                                {:else}
                                    <select
                                        class="w-full text-sm border rounded px-2 py-1.5"
                                        value={selectedNode.type}
                                        on:change={(e) => updateNodeType(selectedNodeId, e.currentTarget.value)}
                                    >
                                        <option value="Sequence">원인 후보 분석 (Sequence)</option>
                                        <option value="Selector">원인 도출 (Selector)</option>
                                        <option value="Condition">분기 (Condition)</option>
                                        <option value="Action">액션 (Action)</option>
                                    </select>
                                {/if}
                            </div>

                            {#if selectedNode.type !== "Action"}
                                <div>
                                    <label class="block text-xs font-medium text-gray-500 mb-1">이름</label>
                                    <input
                                        type="text"
                                        class="w-full text-sm border rounded px-2 py-1.5"
                                        value={selectedNode.name || ""}
                                        on:change={(e) => updateNodeName(selectedNodeId, e.currentTarget.value)}
                                    />
                                </div>
                            {:else}
                                <div>
                                    <label class="block text-xs font-medium text-gray-500 mb-1">액션</label>
                                    <select
                                        class="w-full text-sm border rounded px-2 py-1.5"
                                        value={selectedNode.actionId || ""}
                                        on:change={(e) => updateNodeAction(selectedNodeId, e.currentTarget.value)}
                                    >
                                        {#each workflowActions as action}
                                            <option value={action.id}>{action.name}</option>
                                        {/each}
                                    </select>
                                </div>
                            {/if}
                        </div>

                        <div class="space-y-3">
                            {#if selectedNode.type === "Action" && selectedAction}
                                <div>
                                    <label class="block text-xs font-medium text-gray-500 mb-1">파라미터</label>
                                    <div class="space-y-2 max-h-[120px] overflow-y-auto pr-1">
                                        {#each selectedAction.params as param}
                                            <div class="flex flex-col gap-0.5">
                                                <span class="text-[10px] text-gray-400">
                                                    {param.name}{#if param.required}*{/if}
                                                </span>
                                                <input
                                                    type="text"
                                                    class="w-full text-xs border rounded px-2 py-1"
                                                    value={selectedNode.params?.[param.id] || ""}
                                                    on:change={(e) => updateNodeParam(selectedNodeId, param.id, e.currentTarget.value)}
                                                />
                                            </div>
                                        {/each}
                                    </div>
                                </div>
                            {:else if selectedNodeId !== workflow.rootId}
                                <div class="flex items-end h-full">
                                    <button
                                        class="w-full py-2 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded border border-red-200"
                                        on:click={() => deleteNode(selectedNodeId)}
                                    >
                                        노드 삭제
                                    </button>
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}
            </div>
        {/if}
    {/if}
</div>

<!-- Context Menu -->
{#if contextMenu.show && workflow}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="fixed inset-0 z-40" on:click={closeContextMenu}></div>
    <div
        class="fixed z-50 bg-white rounded shadow-lg border border-gray-200 py-1 min-w-[150px]"
        style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
    >
        {#if workflow.nodes[contextMenu.nodeId]?.type === "Phenomenon"}
            <button
                class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center gap-2"
                on:click={() => {
                    dispatch('requestCaptureMode');
                    closeContextMenu();
                }}
            >
                <span>📷</span> 현상 캡처하기
            </button>
        {/if}
        {#if workflow.nodes[contextMenu.nodeId]?.type !== "Action"}
            <button
                class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center gap-2"
                on:click={() => openAddModal(contextMenu.nodeId)}
            >
                <span>➕</span> 자식 노드 추가
            </button>
        {/if}
        {#if contextMenu.nodeId !== workflow.rootId}
            <button
                class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                on:click={() => deleteNode(contextMenu.nodeId)}
            >
                <span>🗑️</span> 삭제
            </button>
        {/if}
    </div>
{/if}

<!-- Add Node Modal -->
{#if showAddModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]"
        on:click={() => (showAddModal = false)}
    >
        <div
            class="bg-white rounded-lg shadow-xl p-6 w-80"
            on:click|stopPropagation
        >
            <h3 class="text-lg font-bold mb-4">노드 추가</h3>
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">타입</label>
                    <select bind:value={newNodeType} class="w-full border rounded px-3 py-2">
                        <option value="Sequence">원인 후보 분석</option>
                        <option value="Selector">원인 도출</option>
                        <option value="Condition">분기</option>
                        <option value="Action">액션</option>
                    </select>
                </div>
                {#if newNodeType === "Action"}
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">액션</label>
                        <select bind:value={newNodeActionId} class="w-full border rounded px-3 py-2">
                            {#each workflowActions as action}
                                <option value={action.id}>{action.name}</option>
                            {/each}
                        </select>
                    </div>
                {/if}
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <button
                    class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded"
                    on:click={() => (showAddModal = false)}
                >
                    취소
                </button>
                <button
                    class="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded"
                    on:click={confirmAddNode}
                >
                    추가
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .workflow-container {
        background-size: 40px 40px;
        background-image: linear-gradient(to right, rgba(0, 0, 0, 0.05) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
    }

    /* SvelteFlow custom styles */
    :global(.svelte-flow .svelte-flow__node) {
        padding: 0;
        border-radius: 8px;
        font-size: 12px;
    }

    :global(.svelte-flow .svelte-flow__handle) {
        width: 8px;
        height: 8px;
    }

    :global(.svelte-flow .svelte-flow__minimap) {
        background-color: #f3f4f6;
    }

    :global(.svelte-flow .svelte-flow__controls) {
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
</style>
