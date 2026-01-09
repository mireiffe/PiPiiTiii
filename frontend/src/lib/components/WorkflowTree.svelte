<script lang="ts">
    import { createEventDispatcher, onMount, tick } from 'svelte';
    import type { WorkflowData, WorkflowNode, WorkflowAction } from '$lib/api/project';

    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];
    export let readonly = false;

    const dispatch = createEventDispatcher();

    // Node type display names
    const NODE_TYPE_NAMES: Record<string, string> = {
        Selector: '탐색',
        Sequence: '정보 수집',
        Condition: '분기',
        Action: '액션'
    };

    const NODE_TYPE_COLORS: Record<string, { bg: string; border: string; text: string; darkBg: string }> = {
        Selector: { bg: 'bg-purple-100', border: 'border-purple-400', text: 'text-purple-700', darkBg: 'bg-purple-500' },
        Sequence: { bg: 'bg-blue-100', border: 'border-blue-400', text: 'text-blue-700', darkBg: 'bg-blue-500' },
        Condition: { bg: 'bg-yellow-100', border: 'border-yellow-400', text: 'text-yellow-700', darkBg: 'bg-yellow-500' },
        Action: { bg: 'bg-green-100', border: 'border-green-400', text: 'text-green-700', darkBg: 'bg-green-500' }
    };

    // UI state
    let selectedNodeId: string | null = null;
    let draggedNodeId: string | null = null;
    let dropTargetId: string | null = null;
    let dropPosition: 'child' | 'before' | 'after' | null = null;
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };
    let dragPosition = { x: 0, y: 0 };

    // Undo/Redo history
    let historyStack: WorkflowData[] = [];
    let historyIndex = -1;
    const MAX_HISTORY = 50;

    // Add new node modal
    let showAddModal = false;
    let addModalParentId: string | null = null;
    let newNodeType: 'Selector' | 'Sequence' | 'Condition' | 'Action' = 'Action';
    let newNodeActionId: string = '';

    // Container ref
    let containerRef: HTMLDivElement;

    // Layout calculation
    interface LayoutNode {
        id: string;
        node: WorkflowNode;
        x: number;
        y: number;
        width: number;
        height: number;
        children: LayoutNode[];
        parent: LayoutNode | null;
    }

    let layoutRoot: LayoutNode | null = null;
    let canvasWidth = 0;
    let canvasHeight = 0;

    const NODE_WIDTH = 180;
    const NODE_HEIGHT = 80;
    const H_SPACING = 25;
    const V_SPACING = 60;

    // Initialize history when workflow changes externally
    $: if (workflow && historyStack.length === 0) {
        pushHistory(workflow);
    }

    $: if (workflow) {
        calculateLayout();
    }

    function pushHistory(state: WorkflowData) {
        // Remove any states after current index (new branch)
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
            const state = JSON.parse(JSON.stringify(historyStack[historyIndex]));
            dispatch('change', state);
        }
    }

    function redo() {
        if (historyIndex < historyStack.length - 1) {
            historyIndex++;
            const state = JSON.parse(JSON.stringify(historyStack[historyIndex]));
            dispatch('change', state);
        }
    }

    function updateWorkflow(newWorkflow: WorkflowData) {
        pushHistory(newWorkflow);
        dispatch('change', newWorkflow);
    }

    function calculateLayout() {
        if (!workflow || !workflow.rootId || !workflow.nodes) {
            layoutRoot = null;
            canvasWidth = 400;
            canvasHeight = 200;
            return;
        }

        layoutRoot = buildLayoutTree(workflow.rootId, null);
        if (layoutRoot) {
            const treeWidth = calculateSubtreeWidth(layoutRoot);
            positionNodes(layoutRoot, 0, treeWidth);

            const bounds = getTreeBounds(layoutRoot);
            canvasWidth = Math.max(400, bounds.maxX + NODE_WIDTH + 60);
            canvasHeight = Math.max(200, bounds.maxY + NODE_HEIGHT + 60);
        }
    }

    function buildLayoutTree(nodeId: string, parent: LayoutNode | null): LayoutNode | null {
        const node = workflow?.nodes?.[nodeId];
        if (!node) return null;

        const layoutNode: LayoutNode = {
            id: nodeId,
            node,
            x: 0,
            y: 0,
            width: NODE_WIDTH,
            height: NODE_HEIGHT,
            children: [],
            parent
        };

        if (node.children) {
            for (const childId of node.children) {
                const child = buildLayoutTree(childId, layoutNode);
                if (child) {
                    layoutNode.children.push(child);
                }
            }
        }

        return layoutNode;
    }

    function calculateSubtreeWidth(node: LayoutNode): number {
        if (node.children.length === 0) {
            return NODE_WIDTH;
        }

        let totalWidth = 0;
        for (const child of node.children) {
            totalWidth += calculateSubtreeWidth(child);
        }
        totalWidth += (node.children.length - 1) * H_SPACING;

        return Math.max(NODE_WIDTH, totalWidth);
    }

    function positionNodes(node: LayoutNode, depth: number, availableWidth: number, startX = 30) {
        node.y = depth * (NODE_HEIGHT + V_SPACING) + 30;

        if (node.children.length === 0) {
            node.x = startX + (availableWidth - NODE_WIDTH) / 2;
            return;
        }

        const childWidths = node.children.map(c => calculateSubtreeWidth(c));
        const totalChildrenWidth = childWidths.reduce((a, b) => a + b, 0) + (node.children.length - 1) * H_SPACING;

        node.x = startX + (availableWidth - NODE_WIDTH) / 2;

        let childX = startX + (availableWidth - totalChildrenWidth) / 2;
        for (let i = 0; i < node.children.length; i++) {
            const child = node.children[i];
            const childWidth = childWidths[i];
            positionNodes(child, depth + 1, childWidth, childX);
            childX += childWidth + H_SPACING;
        }
    }

    function getTreeBounds(node: LayoutNode): { maxX: number; maxY: number } {
        let maxX = node.x;
        let maxY = node.y;

        for (const child of node.children) {
            const childBounds = getTreeBounds(child);
            maxX = Math.max(maxX, childBounds.maxX);
            maxY = Math.max(maxY, childBounds.maxY);
        }

        return { maxX, maxY };
    }

    function flattenTree(node: LayoutNode | null): LayoutNode[] {
        if (!node) return [];
        const result = [node];
        for (const child of node.children) {
            result.push(...flattenTree(child));
        }
        return result;
    }

    $: allNodes = flattenTree(layoutRoot);

    // Get action info
    function getActionInfo(actionId: string | undefined): WorkflowAction | undefined {
        if (!actionId) return undefined;
        return workflowActions.find(a => a.id === actionId);
    }

    // Get display name for node
    function getNodeDisplayName(node: WorkflowNode): string {
        if (node.type === 'Action') {
            const action = getActionInfo(node.actionId);
            return action ? action.name : (node.name || '알 수 없는 액션');
        }
        return node.name || NODE_TYPE_NAMES[node.type];
    }

    // Get parameter display for node
    function getNodeParams(node: WorkflowNode): { name: string; value: string }[] {
        if (node.type !== 'Action' || !node.params) return [];
        const action = getActionInfo(node.actionId);
        if (!action) return [];

        return action.params.map(p => ({
            name: p.name,
            value: node.params?.[p.id] || ''
        })).filter(p => p.value);
    }

    // Event handlers
    function handleNodeClick(nodeId: string, e: MouseEvent) {
        e.stopPropagation();
        selectedNodeId = nodeId;
    }

    function handleCanvasClick() {
        selectedNodeId = null;
    }

    // Drag and drop handlers
    function handleDragStart(nodeId: string, e: MouseEvent) {
        if (readonly || nodeId === workflow?.rootId) return;

        e.preventDefault();
        draggedNodeId = nodeId;
        isDragging = true;

        const node = allNodes.find(n => n.id === nodeId);
        if (node) {
            dragOffset = {
                x: e.clientX - node.x,
                y: e.clientY - node.y
            };
            dragPosition = { x: node.x, y: node.y };
        }

        window.addEventListener('mousemove', handleDragMove);
        window.addEventListener('mouseup', handleDragEnd);
    }

    function handleDragMove(e: MouseEvent) {
        if (!isDragging || !draggedNodeId) return;

        dragPosition = {
            x: e.clientX - dragOffset.x,
            y: e.clientY - dragOffset.y
        };

        // Find drop target
        const rect = containerRef.getBoundingClientRect();
        const x = e.clientX - rect.left + containerRef.scrollLeft;
        const y = e.clientY - rect.top + containerRef.scrollTop;

        let foundTarget: string | null = null;
        let foundPosition: 'child' | 'before' | 'after' | null = null;

        for (const node of allNodes) {
            if (node.id === draggedNodeId) continue;
            if (isDescendant(draggedNodeId, node.id)) continue;

            const nodeRect = {
                left: node.x,
                top: node.y,
                right: node.x + NODE_WIDTH,
                bottom: node.y + NODE_HEIGHT
            };

            if (x >= nodeRect.left - 20 && x <= nodeRect.right + 20 &&
                y >= nodeRect.top - 20 && y <= nodeRect.bottom + 20) {

                foundTarget = node.id;

                // Determine drop position
                const canHaveChildren = node.node.type !== 'Action' && node.node.type !== 'Condition';
                if (canHaveChildren && y >= nodeRect.top && y <= nodeRect.bottom) {
                    foundPosition = 'child';
                } else if (y < nodeRect.top + NODE_HEIGHT / 2) {
                    foundPosition = 'before';
                } else {
                    foundPosition = 'after';
                }
                break;
            }
        }

        dropTargetId = foundTarget;
        dropPosition = foundPosition;
    }

    function handleDragEnd(e: MouseEvent) {
        window.removeEventListener('mousemove', handleDragMove);
        window.removeEventListener('mouseup', handleDragEnd);

        if (draggedNodeId && dropTargetId && dropPosition) {
            moveNode(draggedNodeId, dropTargetId, dropPosition);
        }

        draggedNodeId = null;
        dropTargetId = null;
        dropPosition = null;
        isDragging = false;
    }

    function isDescendant(ancestorId: string, nodeId: string): boolean {
        const ancestor = workflow?.nodes?.[ancestorId];
        if (!ancestor || !ancestor.children) return false;

        for (const childId of ancestor.children) {
            if (childId === nodeId) return true;
            if (isDescendant(childId, nodeId)) return true;
        }
        return false;
    }

    function moveNode(nodeId: string, targetId: string, position: 'child' | 'before' | 'after') {
        if (!workflow) return;

        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;

        // Find current parent and remove from it
        let currentParentId: string | null = null;
        for (const [id, node] of Object.entries(updatedWorkflow.nodes)) {
            if (node.children?.includes(nodeId)) {
                currentParentId = id;
                node.children = node.children.filter(c => c !== nodeId);
                break;
            }
        }

        if (position === 'child') {
            // Add as child of target
            const target = updatedWorkflow.nodes[targetId];
            if (!target.children) target.children = [];
            target.children.push(nodeId);
        } else {
            // Add as sibling of target
            let targetParentId: string | null = null;
            for (const [id, node] of Object.entries(updatedWorkflow.nodes)) {
                if (node.children?.includes(targetId)) {
                    targetParentId = id;
                    break;
                }
            }

            if (targetParentId) {
                const parent = updatedWorkflow.nodes[targetParentId];
                if (parent.children) {
                    const targetIndex = parent.children.indexOf(targetId);
                    const insertIndex = position === 'before' ? targetIndex : targetIndex + 1;
                    parent.children.splice(insertIndex, 0, nodeId);
                }
            }
        }

        updateWorkflow(updatedWorkflow);
    }

    // Add child node
    function openAddModal(parentId: string) {
        addModalParentId = parentId;
        newNodeType = 'Action';
        newNodeActionId = workflowActions.length > 0 ? workflowActions[0].id : '';
        showAddModal = true;
    }

    function confirmAddNode() {
        if (!workflow || !addModalParentId) return;

        const newId = `node_${Date.now()}`;
        const newNode: WorkflowNode = {
            type: newNodeType,
            children: newNodeType !== 'Action' && newNodeType !== 'Condition' ? [] : undefined
        };

        if (newNodeType === 'Action' && newNodeActionId) {
            newNode.actionId = newNodeActionId;
            const action = getActionInfo(newNodeActionId);
            if (action) {
                newNode.name = action.name;
                newNode.params = {};
                for (const param of action.params) {
                    newNode.params[param.id] = '';
                }
            }
        } else {
            newNode.name = NODE_TYPE_NAMES[newNodeType];
        }

        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        updatedWorkflow.nodes[newId] = newNode;

        const parent = updatedWorkflow.nodes[addModalParentId];
        if (parent) {
            if (!parent.children) parent.children = [];
            parent.children.push(newId);
        }

        updateWorkflow(updatedWorkflow);
        showAddModal = false;
        selectedNodeId = newId;
    }

    // Delete node
    function deleteNode(nodeId: string) {
        if (!workflow || nodeId === workflow.rootId) return;

        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;

        // Remove from parent's children
        for (const node of Object.values(updatedWorkflow.nodes)) {
            if (node.children?.includes(nodeId)) {
                node.children = node.children.filter(c => c !== nodeId);
            }
        }

        // Remove node and its descendants
        const toRemove = new Set<string>();
        collectDescendants(nodeId, toRemove, updatedWorkflow);

        const newNodes: Record<string, WorkflowNode> = {};
        for (const [id, node] of Object.entries(updatedWorkflow.nodes)) {
            if (!toRemove.has(id)) {
                newNodes[id] = node;
            }
        }

        updatedWorkflow.nodes = newNodes;
        updateWorkflow(updatedWorkflow);
        selectedNodeId = null;
    }

    function collectDescendants(nodeId: string, result: Set<string>, wf: WorkflowData) {
        result.add(nodeId);
        const node = wf.nodes?.[nodeId];
        if (node?.children) {
            for (const childId of node.children) {
                collectDescendants(childId, result, wf);
            }
        }
    }

    // Delete entire workflow
    function deleteWorkflow() {
        if (confirm('워크플로우 전체를 삭제하시겠습니까?')) {
            dispatch('change', null);
            historyStack = [];
            historyIndex = -1;
        }
    }

    // Create initial workflow
    function createInitialWorkflow() {
        const initialWorkflow: WorkflowData = {
            rootId: 'root',
            nodes: {
                root: {
                    type: 'Sequence',
                    name: '시작',
                    children: []
                }
            },
            meta: { version: 1 }
        };
        updateWorkflow(initialWorkflow);
    }

    // Update node inline
    function updateNodeName(nodeId: string, name: string) {
        if (!workflow) return;
        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        if (updatedWorkflow.nodes[nodeId]) {
            updatedWorkflow.nodes[nodeId].name = name;
            updateWorkflow(updatedWorkflow);
        }
    }

    function updateNodeParam(nodeId: string, paramId: string, value: string) {
        if (!workflow) return;
        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        const node = updatedWorkflow.nodes[nodeId];
        if (node && node.type === 'Action') {
            if (!node.params) node.params = {};
            node.params[paramId] = value;
            updateWorkflow(updatedWorkflow);
        }
    }

    function updateNodeType(nodeId: string, newType: 'Selector' | 'Sequence' | 'Condition' | 'Action') {
        if (!workflow || nodeId === workflow.rootId) return;
        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        const node = updatedWorkflow.nodes[nodeId];
        if (node) {
            const oldType = node.type;
            node.type = newType;

            // Handle children based on type change
            if (newType === 'Action' || newType === 'Condition') {
                // These types can't have children
                if (node.children && node.children.length > 0) {
                    // Remove children
                    for (const childId of node.children) {
                        const toRemove = new Set<string>();
                        collectDescendants(childId, toRemove, updatedWorkflow);
                        for (const id of toRemove) {
                            delete updatedWorkflow.nodes[id];
                        }
                    }
                }
                delete node.children;
            } else if (!node.children) {
                node.children = [];
            }

            // Handle action-specific properties
            if (newType === 'Action') {
                if (!node.actionId && workflowActions.length > 0) {
                    node.actionId = workflowActions[0].id;
                    const action = getActionInfo(node.actionId);
                    if (action) {
                        node.name = action.name;
                        node.params = {};
                        for (const param of action.params) {
                            node.params[param.id] = '';
                        }
                    }
                }
            } else {
                delete node.actionId;
                delete node.params;
                if (!node.name) {
                    node.name = NODE_TYPE_NAMES[newType];
                }
            }

            updateWorkflow(updatedWorkflow);
        }
    }

    function updateNodeAction(nodeId: string, actionId: string) {
        if (!workflow) return;
        const updatedWorkflow = JSON.parse(JSON.stringify(workflow)) as WorkflowData;
        const node = updatedWorkflow.nodes[nodeId];
        if (node && node.type === 'Action') {
            node.actionId = actionId;
            const action = getActionInfo(actionId);
            if (action) {
                node.name = action.name;
                node.params = {};
                for (const param of action.params) {
                    node.params[param.id] = '';
                }
            }
            updateWorkflow(updatedWorkflow);
        }
    }

    // Draw connections
    function getConnectionPath(parent: LayoutNode, child: LayoutNode): string {
        const startX = parent.x + NODE_WIDTH / 2;
        const startY = parent.y + NODE_HEIGHT;
        const endX = child.x + NODE_WIDTH / 2;
        const endY = child.y;

        const midY = (startY + endY) / 2;

        return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
    }

    // Check if node uses invalid action
    function isInvalidAction(node: WorkflowNode): boolean {
        if (node.type !== 'Action' || !node.actionId) return false;
        return !workflowActions.some(a => a.id === node.actionId);
    }

    // Loopback connections for Selector
    function getLoopbackConnections(): { fromId: string; toId: string }[] {
        const connections: { fromId: string; toId: string }[] = [];

        if (!workflow) return connections;

        for (const [nodeId, node] of Object.entries(workflow.nodes)) {
            if (node.type === 'Selector' && node.children && node.children.length > 1) {
                for (let i = 0; i < node.children.length - 1; i++) {
                    connections.push({
                        fromId: node.children[i],
                        toId: nodeId
                    });
                }
            }
        }

        return connections;
    }

    $: loopbackConnections = getLoopbackConnections();

    function getLoopbackPath(fromNode: LayoutNode, toNode: LayoutNode): string {
        const startX = fromNode.x + NODE_WIDTH;
        const startY = fromNode.y + NODE_HEIGHT / 2;
        const endX = toNode.x + NODE_WIDTH;
        const endY = toNode.y + NODE_HEIGHT / 2;

        const offset = 30;
        return `M ${startX} ${startY}
                C ${startX + offset} ${startY}, ${endX + offset} ${endY}, ${endX} ${endY}`;
    }

    // Keyboard shortcuts
    function handleKeyDown(e: KeyboardEvent) {
        if (readonly) return;

        // Undo/Redo
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                undo();
            } else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
                e.preventDefault();
                redo();
            }
        }

        // Delete selected node
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
            if (selectedNodeId !== workflow?.rootId) {
                e.preventDefault();
                deleteNode(selectedNodeId);
            }
        }

        // Escape to deselect
        if (e.key === 'Escape') {
            selectedNodeId = null;
            showAddModal = false;
        }
    }

    $: selectedNode = selectedNodeId && workflow?.nodes?.[selectedNodeId] ? workflow.nodes[selectedNodeId] : null;
    $: selectedAction = selectedNode?.type === 'Action' ? getActionInfo(selectedNode.actionId) : null;
    $: canUndo = historyIndex > 0;
    $: canRedo = historyIndex < historyStack.length - 1;
</script>

<svelte:window on:keydown={handleKeyDown} />

<div class="workflow-container flex flex-col h-full" bind:this={containerRef}>
    <!-- Canvas area -->
    <div class="flex-1 relative bg-gray-50 rounded-lg overflow-auto min-h-[250px]"
         on:click={handleCanvasClick}
         role="application"
         tabindex="0">

        {#if !workflow || !workflow.nodes || Object.keys(workflow.nodes).length === 0}
            <!-- Empty state -->
            <div class="flex flex-col items-center justify-center h-full min-h-[200px] text-gray-400">
                <svg class="w-12 h-12 mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                <p class="text-sm mb-3">워크플로우가 없습니다</p>
                {#if !readonly}
                    <button
                        class="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                        on:click={createInitialWorkflow}
                    >
                        워크플로우 생성
                    </button>
                {/if}
            </div>
        {:else}
            <!-- Toolbar -->
            {#if !readonly}
                <div class="sticky top-0 left-0 right-0 z-20 bg-white/90 backdrop-blur border-b border-gray-200 px-3 py-2 flex items-center gap-2">
                    <button
                        class="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        on:click={undo}
                        disabled={!canUndo}
                        title="실행취소 (Ctrl+Z)"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                        </svg>
                    </button>
                    <button
                        class="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        on:click={redo}
                        disabled={!canRedo}
                        title="다시실행 (Ctrl+Y)"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                        </svg>
                    </button>

                    <div class="w-px h-5 bg-gray-300 mx-1"></div>

                    <button
                        class="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        on:click={() => selectedNodeId && deleteNode(selectedNodeId)}
                        disabled={!selectedNodeId || selectedNodeId === workflow?.rootId}
                        title="노드 삭제 (Delete)"
                    >
                        <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>

                    <div class="flex-1"></div>

                    <button
                        class="text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-2 py-1 rounded"
                        on:click={deleteWorkflow}
                        title="워크플로우 전체 삭제"
                    >
                        워크플로우 삭제
                    </button>
                </div>
            {/if}

            <!-- Tree canvas -->
            <svg width={canvasWidth} height={canvasHeight} class="workflow-canvas">
                <g class="connections">
                    {#each allNodes as layoutNode}
                        {#each layoutNode.children as child}
                            <path
                                d={getConnectionPath(layoutNode, child)}
                                fill="none"
                                stroke={dropTargetId === layoutNode.id && dropPosition === 'child' ? '#3B82F6' : '#9CA3AF'}
                                stroke-width={dropTargetId === layoutNode.id && dropPosition === 'child' ? 3 : 2}
                                class="transition-colors"
                            />
                        {/each}
                    {/each}

                    <!-- Loopback arrows -->
                    {#each loopbackConnections as conn}
                        {@const fromNode = allNodes.find(n => n.id === conn.fromId)}
                        {@const toNode = allNodes.find(n => n.id === conn.toId)}
                        {#if fromNode && toNode}
                            <path
                                d={getLoopbackPath(fromNode, toNode)}
                                fill="none"
                                stroke="#EF4444"
                                stroke-width="2"
                                stroke-dasharray="5,5"
                                marker-end="url(#loopback-arrow)"
                                class="transition-colors opacity-60"
                            />
                        {/if}
                    {/each}

                    <!-- Drop indicator line -->
                    {#if dropTargetId && (dropPosition === 'before' || dropPosition === 'after')}
                        {@const targetNode = allNodes.find(n => n.id === dropTargetId)}
                        {#if targetNode}
                            <line
                                x1={targetNode.x - 10}
                                y1={dropPosition === 'before' ? targetNode.y - 5 : targetNode.y + NODE_HEIGHT + 5}
                                x2={targetNode.x + NODE_WIDTH + 10}
                                y2={dropPosition === 'before' ? targetNode.y - 5 : targetNode.y + NODE_HEIGHT + 5}
                                stroke="#3B82F6"
                                stroke-width="3"
                                stroke-linecap="round"
                            />
                        {/if}
                    {/if}
                </g>

                <defs>
                    <marker id="loopback-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                        <path d="M0,0 L0,6 L9,3 z" fill="#EF4444" />
                    </marker>
                </defs>
            </svg>

            <!-- Nodes -->
            {#each allNodes as layoutNode (layoutNode.id)}
                {@const colors = NODE_TYPE_COLORS[layoutNode.node.type]}
                {@const isSelected = selectedNodeId === layoutNode.id}
                {@const isDragTarget = dropTargetId === layoutNode.id && dropPosition === 'child'}
                {@const isBeingDragged = draggedNodeId === layoutNode.id}
                {@const isInvalid = isInvalidAction(layoutNode.node)}
                {@const canHaveChildren = layoutNode.node.type !== 'Action' && layoutNode.node.type !== 'Condition'}
                {@const params = getNodeParams(layoutNode.node)}
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <div
                    class="absolute rounded-lg border-2 shadow-sm transition-all duration-150 group
                           {colors.bg} {colors.border}
                           {isSelected ? 'ring-2 ring-blue-500 ring-offset-1 shadow-lg z-10' : 'hover:shadow-md'}
                           {isDragTarget ? 'ring-2 ring-blue-400 ring-offset-2 scale-105' : ''}
                           {isBeingDragged ? 'opacity-50' : ''}
                           {isInvalid ? 'border-red-500 ring-2 ring-red-200' : ''}
                           {readonly ? 'cursor-default' : 'cursor-grab active:cursor-grabbing'}"
                    style="left: {layoutNode.x}px; top: {layoutNode.y}px; width: {NODE_WIDTH}px; min-height: {NODE_HEIGHT}px;"
                    on:click={(e) => handleNodeClick(layoutNode.id, e)}
                    on:mousedown={(e) => handleDragStart(layoutNode.id, e)}
                >
                    <!-- Node type badge -->
                    <div class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}">
                        {NODE_TYPE_NAMES[layoutNode.node.type]}
                    </div>

                    <div class="flex flex-col p-2 pt-3">
                        <!-- Node name -->
                        <span class="text-sm font-semibold {colors.text} truncate">
                            {getNodeDisplayName(layoutNode.node)}
                        </span>

                        <!-- Parameters (small text) -->
                        {#if params.length > 0}
                            <div class="mt-1 space-y-0.5">
                                {#each params.slice(0, 2) as param}
                                    <div class="text-[10px] text-gray-500 truncate">
                                        <span class="font-medium">{param.name}:</span> {param.value}
                                    </div>
                                {/each}
                                {#if params.length > 2}
                                    <div class="text-[10px] text-gray-400">+{params.length - 2} more...</div>
                                {/if}
                            </div>
                        {/if}

                        {#if isInvalid}
                            <span class="text-[9px] text-red-600 font-medium mt-1">유효하지 않음</span>
                        {/if}
                    </div>

                    <!-- Add Child Button -->
                    {#if canHaveChildren && !readonly}
                        <button
                            class="absolute -bottom-3 left-1/2 -translate-x-1/2 w-6 h-6 bg-blue-500 hover:bg-blue-600 text-white rounded-full shadow-md opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm font-bold z-10"
                            on:click|stopPropagation={() => openAddModal(layoutNode.id)}
                            title="자식 노드 추가"
                        >
                            +
                        </button>
                    {/if}
                </div>
            {/each}

            <!-- Drag ghost -->
            {#if isDragging && draggedNodeId}
                {@const dragNode = allNodes.find(n => n.id === draggedNodeId)}
                {#if dragNode}
                    {@const colors = NODE_TYPE_COLORS[dragNode.node.type]}
                    <div
                        class="fixed rounded-lg border-2 shadow-xl pointer-events-none z-50 opacity-80
                               {colors.bg} {colors.border}"
                        style="left: {dragPosition.x}px; top: {dragPosition.y}px; width: {NODE_WIDTH}px; min-height: {NODE_HEIGHT}px;"
                    >
                        <div class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}">
                            {NODE_TYPE_NAMES[dragNode.node.type]}
                        </div>
                        <div class="flex flex-col p-2 pt-3">
                            <span class="text-sm font-semibold {colors.text} truncate">
                                {getNodeDisplayName(dragNode.node)}
                            </span>
                        </div>
                    </div>
                {/if}
            {/if}
        {/if}
    </div>

    <!-- Node Editor Panel (shown when node is selected) - Bottom panel -->
    {#if selectedNode && !readonly && workflow}
        {@const selectedColors = NODE_TYPE_COLORS[selectedNode.type]}
        <div class="bg-white border-t border-gray-200 p-3 flex-shrink-0 max-h-[200px] overflow-y-auto">
            <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                    <div class="px-2 py-0.5 rounded text-[10px] font-bold text-white {selectedColors.darkBg}">
                        {NODE_TYPE_NAMES[selectedNode.type]}
                    </div>
                    <h3 class="font-semibold text-gray-800 text-sm">{getNodeDisplayName(selectedNode)}</h3>
                </div>
                <button
                    class="text-gray-400 hover:text-gray-600 p-1"
                    on:click={() => selectedNodeId = null}
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div class="grid grid-cols-2 gap-3">
                <!-- Left column: Type and Name/Action -->
                <div class="space-y-2">
                    <!-- Node Type -->
                    <div>
                        <label class="block text-[10px] font-medium text-gray-500 mb-0.5">타입</label>
                        {#if selectedNodeId === workflow.rootId}
                            <div class="text-xs text-gray-700 py-1">{NODE_TYPE_NAMES[selectedNode.type]}</div>
                        {:else}
                            <select
                                class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                value={selectedNode.type}
                                on:change={(e) => selectedNodeId && updateNodeType(selectedNodeId, e.currentTarget.value as any)}
                            >
                                <option value="Sequence">정보 수집 (Sequence)</option>
                                <option value="Selector">탐색 (Selector)</option>
                                <option value="Condition">분기 (Condition)</option>
                                <option value="Action">액션 (Action)</option>
                            </select>
                        {/if}
                    </div>

                    <!-- Node Name (for non-Action nodes) -->
                    {#if selectedNode.type !== 'Action'}
                        <div>
                            <label class="block text-[10px] font-medium text-gray-500 mb-0.5">이름</label>
                            <input
                                type="text"
                                class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                value={selectedNode.name || ''}
                                on:change={(e) => selectedNodeId && updateNodeName(selectedNodeId, e.currentTarget.value)}
                                placeholder="노드 이름"
                            />
                        </div>
                    {:else}
                        <!-- Action Selection -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-500 mb-0.5">액션</label>
                            {#if workflowActions.length === 0}
                                <p class="text-[10px] text-gray-400">정의된 액션이 없습니다</p>
                            {:else}
                                <select
                                    class="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    value={selectedNode.actionId || ''}
                                    on:change={(e) => selectedNodeId && updateNodeAction(selectedNodeId, e.currentTarget.value)}
                                >
                                    {#each workflowActions as action}
                                        <option value={action.id}>{action.name}</option>
                                    {/each}
                                </select>
                            {/if}
                        </div>
                    {/if}
                </div>

                <!-- Right column: Parameters or Delete -->
                <div class="space-y-2">
                    {#if selectedNode.type === 'Action' && selectedAction?.params && selectedAction.params.length > 0}
                        <!-- Action Parameters -->
                        <div class="space-y-1.5">
                            <label class="block text-[10px] font-medium text-gray-500">파라미터</label>
                            {#each selectedAction.params as param}
                                <div class="flex items-center gap-1">
                                    <label class="text-[10px] text-gray-400 w-16 truncate" title={param.name}>
                                        {param.name}{#if param.required}<span class="text-red-500">*</span>{/if}
                                    </label>
                                    <input
                                        type="text"
                                        class="flex-1 text-xs border border-gray-300 rounded px-2 py-0.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        value={selectedNode.params?.[param.id] || ''}
                                        on:change={(e) => selectedNodeId && updateNodeParam(selectedNodeId, param.id, e.currentTarget.value)}
                                        placeholder={param.name}
                                    />
                                </div>
                            {/each}
                        </div>
                    {:else if selectedNodeId !== workflow.rootId}
                        <!-- Delete Button -->
                        <div class="flex items-end h-full pb-1">
                            <button
                                class="text-xs text-red-600 hover:text-red-700 hover:bg-red-50 py-1.5 px-3 rounded flex items-center gap-1.5"
                                on:click={() => selectedNodeId && deleteNode(selectedNodeId)}
                            >
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                노드 삭제
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- Add Node Modal -->
{#if showAddModal}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" on:click={() => showAddModal = false}>
        <div class="bg-white rounded-lg shadow-xl p-6 w-80" on:click|stopPropagation>
            <h3 class="text-lg font-bold text-gray-800 mb-4">자식 노드 추가</h3>

            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">노드 타입</label>
                    <select
                        bind:value={newNodeType}
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="Sequence">정보 수집 (Sequence)</option>
                        <option value="Selector">탐색 (Selector)</option>
                        <option value="Condition">분기 (Condition)</option>
                        <option value="Action">액션 (Action)</option>
                    </select>
                </div>

                {#if newNodeType === 'Action'}
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">액션 선택</label>
                        {#if workflowActions.length === 0}
                            <p class="text-sm text-gray-400">정의된 액션이 없습니다. 설정에서 액션을 추가해주세요.</p>
                        {:else}
                            <select
                                bind:value={newNodeActionId}
                                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                            >
                                {#each workflowActions as action}
                                    <option value={action.id}>{action.name}</option>
                                {/each}
                            </select>
                        {/if}
                    </div>
                {/if}
            </div>

            <div class="flex justify-end gap-2 mt-6">
                <button
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                    on:click={() => showAddModal = false}
                >
                    취소
                </button>
                <button
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700
                           disabled:opacity-50 disabled:cursor-not-allowed"
                    on:click={confirmAddNode}
                    disabled={newNodeType === 'Action' && (!newNodeActionId || workflowActions.length === 0)}
                >
                    추가
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .workflow-container {
        position: relative;
        min-height: 200px;
    }

    .workflow-canvas {
        position: absolute;
        top: 0;
        left: 0;
        pointer-events: none;
    }
</style>
