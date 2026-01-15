<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import type { WorkflowData, WorkflowNode, WorkflowAction, SlideCapture } from "$lib/api/project";
    import { CAPTURE_COLORS } from "$lib/api/project";
    import WorkflowTreeNode from "./WorkflowTreeNode.svelte";
    import WorkflowNodeSettingsPanel from "./WorkflowNodeSettingsPanel.svelte";
    import {
        type LayoutNode,
        type Transform,
        NODE_WIDTH,
        NODE_HEIGHT,
        MAX_HISTORY,
        NODE_TYPE_NAMES,
        NODE_TYPE_COLORS,
        calculateLayout,
        getTreeBounds,
        getConnectionPath,
        getLoopbackPath,
        getLoopbackConnections,
        isDescendant,
    } from "./workflowTreeLayout";

    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];
    export let readonly = false;

    const dispatch = createEventDispatcher();

    // State
    let containerRef: HTMLDivElement;
    let transform: Transform = { x: 0, y: 0, k: 1 };
    let isPanning = false;
    let panStart = { x: 0, y: 0 };

    // Selection & Dragging
    let selectedNodeId: string | null = null;
    let draggedNodeId: string | null = null;
    let dropTargetId: string | null = null;
    let dropPosition: "child" | "before" | "after" | null = null;
    let isDragging = false;
    let dragNodeOffset = { x: 0, y: 0 };
    let currentMousePos = { x: 0, y: 0 };

    // Context Menu
    let contextMenu = { show: false, x: 0, y: 0, nodeId: "" };

    // History
    let historyStack: WorkflowData[] = [];
    let historyIndex = -1;

    // Modal
    let showAddModal = false;
    let addModalParentId: string | null = null;
    let newNodeType: "Selector" | "Sequence" | "Condition" | "Action" = "Action";
    let newNodeActionId: string = "";

    // Layout
    let layoutRoot: LayoutNode | null = null;
    let allNodes: LayoutNode[] = [];

    // Reactivity
    $: if (workflow && historyStack.length === 0) pushHistory(workflow);
    $: if (workflow) {
        const result = calculateLayout(workflow);
        layoutRoot = result.layoutRoot;
        allNodes = result.allNodes;
        if (selectedNodeId && !workflow.nodes[selectedNodeId]) selectedNodeId = null;
    }

    $: selectedNode = selectedNodeId && workflow?.nodes?.[selectedNodeId] ? workflow.nodes[selectedNodeId] : null;
    $: if (typeof selectedNodeId !== "undefined") {
        dispatch("nodeSelect", { nodeId: selectedNodeId, isPhenomenon: selectedNode?.type === "Phenomenon" });
    }
    $: canUndo = historyIndex > 0;
    $: canRedo = historyIndex < historyStack.length - 1;
    $: loopbackConnections = getLoopbackConnections(workflow);

    // History Management
    function pushHistory(state: WorkflowData) {
        historyStack = historyStack.slice(0, historyIndex + 1);
        historyStack.push(JSON.parse(JSON.stringify(state)));
        if (historyStack.length > MAX_HISTORY) historyStack = historyStack.slice(1);
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

    // Viewport Interactions
    function handleWheel(e: WheelEvent) {
        if (contextMenu.show) return;
        e.preventDefault();
        const rect = containerRef.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;
        const delta = e.deltaY < 0 ? 1 : -1;
        let newK = Math.min(Math.max(0.2, transform.k + delta * 0.1), 3);
        const scaleRatio = newK / transform.k;
        transform = {
            x: offsetX - (offsetX - transform.x) * scaleRatio,
            y: offsetY - (offsetY - transform.y) * scaleRatio,
            k: newK,
        };
    }

    function handleMouseDown(e: MouseEvent) {
        if (e.button === 1 || (e.button === 0 && !isDragging)) {
            isPanning = true;
            panStart = { x: e.clientX - transform.x, y: e.clientY - transform.y };
            containerRef.style.cursor = "grabbing";
            contextMenu.show = false;
        }
    }

    function handleWindowMouseMove(e: MouseEvent) {
        if (isPanning) {
            e.preventDefault();
            transform.x = e.clientX - panStart.x;
            transform.y = e.clientY - panStart.y;
        } else if (isDragging && draggedNodeId) {
            handleDragMove(e);
        }
    }

    function handleWindowMouseUp() {
        if (isPanning) {
            isPanning = false;
            containerRef.style.cursor = "default";
        }
        if (isDragging) handleDragEnd();
    }

    function fitView() {
        if (!layoutRoot || !containerRef) return;
        const bounds = getTreeBounds(layoutRoot);
        const rect = containerRef.getBoundingClientRect();
        const treeW = bounds.maxX - bounds.minX + NODE_WIDTH;
        const treeH = bounds.maxY + NODE_HEIGHT;
        const padding = 100;
        let k = Math.min((rect.width - padding) / treeW, (rect.height - padding) / treeH, 1);
        k = Math.max(k, 0.2);
        const treeCenterX = bounds.minX + treeW / 2;
        transform = { x: rect.width / 2 - treeCenterX * k, y: 50, k };
    }

    onMount(() => {
        if (layoutRoot) setTimeout(fitView, 100);
    });

    // Drag & Drop
    function handleDragStart(e: MouseEvent, nodeId: string) {
        if (readonly || nodeId === workflow?.rootId) return;
        e.stopPropagation();
        e.preventDefault();
        contextMenu.show = false;
        selectedNodeId = nodeId;
        isDragging = true;
        draggedNodeId = nodeId;
        const rect = (e.target as Element).closest(".node-element")?.getBoundingClientRect();
        if (rect) dragNodeOffset = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        currentMousePos = { x: e.clientX, y: e.clientY };
    }

    function handleDragMove(e: MouseEvent) {
        currentMousePos = { x: e.clientX, y: e.clientY };
        const rect = containerRef.getBoundingClientRect();
        const worldX = (e.clientX - rect.left - transform.x) / transform.k;
        const worldY = (e.clientY - rect.top - transform.y) / transform.k;

        let targetId: string | null = null;
        let pos: "child" | "before" | "after" | null = null;

        for (const layoutNode of allNodes) {
            if (layoutNode.id === draggedNodeId || isDescendant(workflow, draggedNodeId!, layoutNode.id)) continue;
            const hitPadding = 20;
            if (worldX >= layoutNode.x - hitPadding && worldX <= layoutNode.x + NODE_WIDTH + hitPadding &&
                worldY >= layoutNode.y - hitPadding && worldY <= layoutNode.y + NODE_HEIGHT + hitPadding) {
                targetId = layoutNode.id;
                const relativeY = (worldY - layoutNode.y) / NODE_HEIGHT;
                const canHaveChildren = layoutNode.node.type !== "Action" && layoutNode.node.type !== "Condition";
                if (canHaveChildren) {
                    if (relativeY < 0.25) pos = "before";
                    else if (relativeY > 0.75) pos = "after";
                    else pos = "child";
                } else {
                    pos = relativeY < 0.5 ? "before" : "after";
                }
                break;
            }
        }
        dropTargetId = targetId;
        dropPosition = pos;
    }

    function handleDragEnd() {
        if (draggedNodeId && dropTargetId && dropPosition && workflow) {
            moveNode(draggedNodeId, dropTargetId, dropPosition);
        }
        isDragging = false;
        draggedNodeId = null;
        dropTargetId = null;
        dropPosition = null;
    }

    function moveNode(nodeId: string, targetId: string, position: "child" | "before" | "after") {
        const updated = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        Object.values(updated.nodes).forEach((node) => {
            if (node.children?.includes(nodeId)) node.children = node.children.filter((id) => id !== nodeId);
        });
        if (position === "child") {
            const target = updated.nodes[targetId];
            if (!target.children) target.children = [];
            target.children.push(nodeId);
        } else {
            let targetParentId: string | null = null;
            for (const [id, node] of Object.entries(updated.nodes)) {
                if (node.children?.includes(targetId)) { targetParentId = id; break; }
            }
            if (targetParentId) {
                const parent = updated.nodes[targetParentId];
                if (parent.children) {
                    const idx = parent.children.indexOf(targetId);
                    parent.children.splice(position === "before" ? idx : idx + 1, 0, nodeId);
                }
            }
        }
        updateWorkflow(updated);
    }

    // Context Menu
    function handleNodeContextMenu(e: MouseEvent, nodeId: string) {
        if (readonly) return;
        e.preventDefault();
        e.stopPropagation();
        selectedNodeId = nodeId;
        contextMenu = { show: true, x: e.clientX, y: e.clientY, nodeId };
    }

    function closeContextMenu() { contextMenu.show = false; }
    function handleCanvasClick() { selectedNodeId = null; closeContextMenu(); }

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
        const newId = `node_${Date.now()}`;
        const newNode: WorkflowNode = {
            type: newNodeType,
            children: newNodeType !== "Action" && newNodeType !== "Condition" ? [] : undefined,
        };
        if (newNodeType === "Action" && newNodeActionId) {
            newNode.actionId = newNodeActionId;
            const action = workflowActions.find((a) => a.id === newNodeActionId);
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
        Object.values(updated.nodes).forEach((n: any) => {
            if (n.children?.includes(nodeId)) n.children = n.children.filter((c: string) => c !== nodeId);
        });
        const toRemove = new Set<string>();
        const collect = (id: string) => { toRemove.add(id); updated.nodes[id]?.children?.forEach(collect); };
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
                phenomenon: { type: "Phenomenon", name: "발생 현상", description: "", captures: [], children: ["candidate_analysis", "root_cause_selector"] },
                candidate_analysis: { type: "Sequence", name: "원인 후보 분석", children: [] },
                root_cause_selector: { type: "Selector", name: "원인 도출", children: [] },
            },
            meta: { version: 1 },
        });
        setTimeout(fitView, 50);
        selectedNodeId = "phenomenon";
    }

    // Update handlers from settings panel
    function updateNodeName(nodeId: string, name: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]) { updated.nodes[nodeId].name = name; updateWorkflow(updated); }
    }

    function updateNodeDescription(nodeId: string, description: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        if (updated.nodes[nodeId]) { updated.nodes[nodeId].description = description; updateWorkflow(updated); }
    }

    function updateNodeType(nodeId: string, newType: any) {
        if (!workflow || nodeId === workflow.rootId) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (!node) return;
        node.type = newType;
        if (newType === "Action" || newType === "Condition") {
            if (node.children) {
                const collect = (id: string) => { const n = updated.nodes[id]; if (n?.children) n.children.forEach(collect); delete updated.nodes[id]; };
                node.children.forEach(collect);
                delete node.children;
            }
            if (newType === "Action") {
                node.actionId = workflowActions[0]?.id;
                const action = workflowActions.find((a) => a.id === node.actionId);
                if (action) { node.name = action.name; node.params = {}; action.params.forEach((p) => (node.params![p.id] = "")); }
            }
        } else if (!node.children) node.children = [];
        if (newType !== "Action") { delete node.actionId; delete node.params; node.name = NODE_TYPE_NAMES[newType]; }
        updateWorkflow(updated);
    }

    function updateNodeAction(nodeId: string, actionId: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Action") {
            node.actionId = actionId;
            const action = workflowActions.find((a) => a.id === actionId);
            if (action) { node.name = action.name; node.params = {}; action.params.forEach((p) => (node.params![p.id] = "")); }
            updateWorkflow(updated);
        }
    }

    function updateNodeParam(nodeId: string, paramId: string, value: string) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Action") { node.params = node.params || {}; node.params[paramId] = value; updateWorkflow(updated); }
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

    // Export functions
    export function addCaptureToNode(nodeId: string, capture: SlideCapture) {
        if (!workflow) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (node && node.type === "Phenomenon") {
            if (!node.captures) node.captures = [];
            node.captures.push(capture);
            updateWorkflow(updated);
        }
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
        return node.captures.map((capture, idx) => ({ ...capture, colorIndex: idx }));
    }

    export function isPhenomenonSelected(): boolean {
        if (!selectedNodeId || !workflow) return false;
        return workflow.nodes[selectedNodeId]?.type === "Phenomenon";
    }
</script>

<svelte:window
    on:mousemove={handleWindowMouseMove}
    on:mouseup={handleWindowMouseUp}
    on:keydown={(e) => {
        if (readonly) return;
        if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
        if (e.key === "Delete" && selectedNodeId && selectedNodeId !== workflow?.rootId) deleteNode(selectedNodeId);
        if (e.key === " " && !e.target.matches("input, textarea")) { e.preventDefault(); fitView(); }
    }}
/>

<div
    class="workflow-container flex flex-col h-full bg-gray-50 select-none overflow-hidden relative"
    bind:this={containerRef}
    on:mousedown={handleMouseDown}
    on:wheel={handleWheel}
    on:click={handleCanvasClick}
    role="application"
    tabindex="0"
>
    {#if !workflow || !workflow.nodes || Object.keys(workflow.nodes).length === 0}
        <div class="flex flex-col items-center justify-center h-full text-gray-400 z-10">
            <svg class="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            <p class="mb-4">워크플로우가 비어있습니다</p>
            {#if !readonly}
                <button class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition" on:click={createInitialWorkflow}>
                    워크플로우 생성
                </button>
            {/if}
        </div>
    {:else}
        <!-- Toolbar -->
        {#if !readonly}
            <div class="absolute top-2 left-2 right-2 z-20 flex justify-between pointer-events-none">
                <div class="bg-white/90 backdrop-blur border border-gray-200 rounded-lg shadow-sm p-1 flex items-center gap-1 pointer-events-auto">
                    <button class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30" on:click={undo} disabled={!canUndo} title="실행취소 (Ctrl+Z)">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                    </button>
                    <button class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30" on:click={redo} disabled={!canRedo} title="다시실행 (Ctrl+Shift+Z)">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" /></svg>
                    </button>
                    <div class="w-px h-4 bg-gray-300 mx-1"></div>
                    <button class="p-1.5 hover:bg-gray-100 rounded" on:click={fitView} title="화면 맞춤 (Space)">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
                    </button>
                </div>
                <button class="bg-white/90 text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm text-xs font-medium pointer-events-auto" on:click={deleteWorkflow}>
                    초기화
                </button>
            </div>
        {/if}

        <!-- Canvas -->
        <div class="absolute top-0 left-0 origin-top-left transition-transform duration-75 will-change-transform" style="transform: translate({transform.x}px, {transform.y}px) scale({transform.k});">
            <!-- SVG Connections -->
            <svg class="overflow-visible pointer-events-none" style="width: 1px; height: 1px;">
                <defs>
                    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#9CA3AF" /></marker>
                    <marker id="loopback-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#EF4444" /></marker>
                </defs>
                <g>
                    {#each allNodes as layoutNode}
                        {#each layoutNode.children as child}
                            <path d={getConnectionPath(layoutNode, child)} fill="none" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arrow)" />
                        {/each}
                    {/each}
                    {#each loopbackConnections as conn}
                        {@const from = allNodes.find((n) => n.id === conn.fromId)}
                        {@const to = allNodes.find((n) => n.id === conn.toId)}
                        {#if from && to}
                            <path d={getLoopbackPath(from, to)} fill="none" stroke="#EF4444" stroke-width="2" stroke-dasharray="5,5" marker-end="url(#loopback-arrow)" opacity="0.6" />
                        {/if}
                    {/each}
                    {#if dropTargetId && dropPosition}
                        {@const target = allNodes.find((n) => n.id === dropTargetId)}
                        {#if target}
                            {#if dropPosition === "child"}
                                <rect x={target.x - 4} y={target.y - 4} width={NODE_WIDTH + 8} height={NODE_HEIGHT + 8} rx="12" fill="none" stroke="#3B82F6" stroke-width="3" stroke-dasharray="4" />
                            {:else}
                                <line x1={target.x} y1={dropPosition === "before" ? target.y - 10 : target.y + NODE_HEIGHT + 10} x2={target.x + NODE_WIDTH} y2={dropPosition === "before" ? target.y - 10 : target.y + NODE_HEIGHT + 10} stroke="#3B82F6" stroke-width="4" stroke-linecap="round" />
                            {/if}
                        {/if}
                    {/if}
                </g>
            </svg>

            <!-- Nodes -->
            {#each allNodes as layoutNode (layoutNode.id)}
                <WorkflowTreeNode
                    {layoutNode}
                    {workflowActions}
                    isSelected={selectedNodeId === layoutNode.id}
                    isDraggingThis={draggedNodeId === layoutNode.id}
                    on:dragstart={(e) => handleDragStart(e.detail.event, e.detail.nodeId)}
                    on:contextmenu={(e) => handleNodeContextMenu(e.detail.event, e.detail.nodeId)}
                />
            {/each}
        </div>

        <!-- Drag Ghost -->
        {#if isDragging && draggedNodeId}
            {@const dragNode = allNodes.find((n) => n.id === draggedNodeId)}
            {#if dragNode}
                {@const colors = NODE_TYPE_COLORS[dragNode.node.type]}
                <div
                    class="fixed pointer-events-none z-50 rounded-lg border-2 shadow-xl opacity-90 {colors.bg} {colors.border} flex items-center justify-center"
                    style="width: {NODE_WIDTH}px; height: {NODE_HEIGHT}px; left: {currentMousePos.x - dragNodeOffset.x}px; top: {currentMousePos.y - dragNodeOffset.y}px;"
                >
                    <span class="font-bold {colors.text}">{dragNode.node.name || NODE_TYPE_NAMES[dragNode.node.type]}</span>
                </div>
            {/if}
        {/if}
    {/if}

    <!-- Settings Panel -->
    <WorkflowNodeSettingsPanel
        {selectedNode}
        {selectedNodeId}
        {workflow}
        {workflowActions}
        on:close={() => (selectedNodeId = null)}
        on:updateName={(e) => updateNodeName(e.detail.nodeId, e.detail.name)}
        on:updateDescription={(e) => updateNodeDescription(e.detail.nodeId, e.detail.description)}
        on:updateType={(e) => updateNodeType(e.detail.nodeId, e.detail.newType)}
        on:updateAction={(e) => updateNodeAction(e.detail.nodeId, e.detail.actionId)}
        on:updateParam={(e) => updateNodeParam(e.detail.nodeId, e.detail.paramId, e.detail.value)}
        on:removeCapture={(e) => removeCapture(e.detail.nodeId, e.detail.captureIndex)}
        on:deleteNode={(e) => deleteNode(e.detail.nodeId)}
    />
</div>

<!-- Context Menu -->
{#if contextMenu.show && workflow}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="fixed inset-0 z-40" on:click={closeContextMenu}></div>
    <div class="fixed z-50 bg-white rounded shadow-lg border border-gray-200 py-1 min-w-[150px]" style="left: {contextMenu.x}px; top: {contextMenu.y}px;">
        {#if workflow.nodes[contextMenu.nodeId]?.type === "Phenomenon"}
            <button class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center gap-2" on:click={() => { dispatch("requestCaptureMode"); closeContextMenu(); }}>
                <span>📷</span> 현상 캡처하기
            </button>
        {/if}
        {#if workflow.nodes[contextMenu.nodeId]?.type !== "Action"}
            <button class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center gap-2" on:click={() => openAddModal(contextMenu.nodeId)}>
                <span>➕</span> 자식 노드 추가
            </button>
        {/if}
        {#if contextMenu.nodeId !== workflow.rootId}
            <button class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2" on:click={() => deleteNode(contextMenu.nodeId)}>
                <span>🗑️</span> 삭제
            </button>
        {/if}
    </div>
{/if}

<!-- Add Node Modal -->
{#if showAddModal}
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" on:click={() => (showAddModal = false)}>
        <div class="bg-white rounded-lg shadow-xl p-6 w-80" on:click|stopPropagation>
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
                            {#each workflowActions as action}<option value={action.id}>{action.name}</option>{/each}
                        </select>
                    </div>
                {/if}
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <button class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded" on:click={() => (showAddModal = false)}>취소</button>
                <button class="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded" on:click={confirmAddNode}>추가</button>
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
</style>
