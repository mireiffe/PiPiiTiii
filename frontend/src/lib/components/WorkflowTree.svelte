<script lang="ts">
    import { createEventDispatcher, onMount, tick } from 'svelte';
    import type { WorkflowData, WorkflowNode, WorkflowAction } from '$lib/api/project';

    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];
    export let readonly = false;

    const dispatch = createEventDispatcher();

    // Node type display names
    const NODE_TYPE_NAMES = {
        Selector: '탐색',
        Sequence: '정보 수집',
        Condition: '분기',
        Action: '액션'
    };

    const NODE_TYPE_COLORS = {
        Selector: { bg: 'bg-purple-100', border: 'border-purple-300', text: 'text-purple-700' },
        Sequence: { bg: 'bg-blue-100', border: 'border-blue-300', text: 'text-blue-700' },
        Condition: { bg: 'bg-yellow-100', border: 'border-yellow-300', text: 'text-yellow-700' },
        Action: { bg: 'bg-green-100', border: 'border-green-300', text: 'text-green-700' }
    };

    // UI state
    let selectedNodeId: string | null = null;
    let editingNodeId: string | null = null;
    let draggedNodeId: string | null = null;
    let dropTargetId: string | null = null;

    // Context menu
    let contextMenu = { show: false, x: 0, y: 0, nodeId: '' };

    // Add new node modal
    let showAddModal = false;
    let addModalParentId: string | null = null;
    let newNodeType: 'Selector' | 'Sequence' | 'Condition' | 'Action' = 'Action';
    let newNodeActionId: string = '';

    // Edit node modal
    let showEditModal = false;
    let editNodeId: string | null = null;
    let editNodeName: string = '';
    let editNodeParams: Record<string, string> = {};

    // Calculate tree layout
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

    const NODE_WIDTH = 140;
    const NODE_HEIGHT = 60;
    const H_SPACING = 30;
    const V_SPACING = 80;

    $: if (workflow) {
        calculateLayout();
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
            // Calculate positions
            const treeWidth = calculateSubtreeWidth(layoutRoot);
            positionNodes(layoutRoot, 0, treeWidth);

            // Calculate canvas size
            const bounds = getTreeBounds(layoutRoot);
            canvasWidth = Math.max(400, bounds.maxX + NODE_WIDTH + 40);
            canvasHeight = Math.max(200, bounds.maxY + NODE_HEIGHT + 40);
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

    function positionNodes(node: LayoutNode, depth: number, availableWidth: number, startX = 20) {
        node.y = depth * (NODE_HEIGHT + V_SPACING) + 20;

        if (node.children.length === 0) {
            node.x = startX + (availableWidth - NODE_WIDTH) / 2;
            return;
        }

        // Calculate width for each child subtree
        const childWidths = node.children.map(c => calculateSubtreeWidth(c));
        const totalChildrenWidth = childWidths.reduce((a, b) => a + b, 0) + (node.children.length - 1) * H_SPACING;

        // Center the node above its children
        node.x = startX + (availableWidth - NODE_WIDTH) / 2;

        // Position children
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

    // Get all layout nodes as flat array for rendering
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

    // Event handlers
    function handleNodeClick(nodeId: string, e: MouseEvent) {
        e.stopPropagation();
        selectedNodeId = nodeId;
    }

    function handleNodeDoubleClick(nodeId: string, e: MouseEvent) {
        if (readonly) return;
        e.stopPropagation();
        openEditModal(nodeId);
    }

    function handleCanvasClick() {
        selectedNodeId = null;
        contextMenu.show = false;
    }

    function handleContextMenu(nodeId: string, e: MouseEvent) {
        if (readonly) return;
        e.preventDefault();
        e.stopPropagation();
        selectedNodeId = nodeId;
        contextMenu = { show: true, x: e.clientX, y: e.clientY, nodeId };
    }

    function closeContextMenu() {
        contextMenu.show = false;
    }

    // Add child node
    function openAddModal(parentId: string) {
        closeContextMenu();
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

        // Add to workflow
        const updatedWorkflow = { ...workflow };
        updatedWorkflow.nodes = { ...workflow.nodes, [newId]: newNode };

        // Add as child to parent
        const parent = updatedWorkflow.nodes[addModalParentId];
        if (parent) {
            if (!parent.children) parent.children = [];
            parent.children = [...parent.children, newId];
        }

        dispatch('change', updatedWorkflow);
        showAddModal = false;
    }

    // Edit node
    function openEditModal(nodeId: string) {
        const node = workflow?.nodes?.[nodeId];
        if (!node) return;

        editNodeId = nodeId;
        editNodeName = node.name || '';
        editNodeParams = { ...(node.params || {}) };
        showEditModal = true;
        closeContextMenu();
    }

    function confirmEditNode() {
        if (!workflow || !editNodeId) return;

        const updatedWorkflow = { ...workflow };
        const node = { ...updatedWorkflow.nodes[editNodeId] };

        if (node.type === 'Action') {
            node.params = { ...editNodeParams };
        } else {
            node.name = editNodeName;
        }

        updatedWorkflow.nodes = { ...updatedWorkflow.nodes, [editNodeId]: node };
        dispatch('change', updatedWorkflow);
        showEditModal = false;
    }

    // Delete node
    function deleteNode(nodeId: string) {
        if (!workflow || nodeId === workflow.rootId) return;

        closeContextMenu();

        const updatedWorkflow = { ...workflow };

        // Remove from parent's children
        for (const [id, node] of Object.entries(updatedWorkflow.nodes)) {
            if (node.children?.includes(nodeId)) {
                node.children = node.children.filter(c => c !== nodeId);
            }
        }

        // Remove node and its descendants
        const toRemove = new Set<string>();
        collectDescendants(nodeId, toRemove);

        const newNodes: Record<string, WorkflowNode> = {};
        for (const [id, node] of Object.entries(updatedWorkflow.nodes)) {
            if (!toRemove.has(id)) {
                newNodes[id] = node;
            }
        }

        updatedWorkflow.nodes = newNodes;
        dispatch('change', updatedWorkflow);
    }

    function collectDescendants(nodeId: string, result: Set<string>) {
        result.add(nodeId);
        const node = workflow?.nodes?.[nodeId];
        if (node?.children) {
            for (const childId of node.children) {
                collectDescendants(childId, result);
            }
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
        dispatch('change', initialWorkflow);
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

    // Check for invalid params
    function hasInvalidParams(node: WorkflowNode): boolean {
        if (node.type !== 'Action' || !node.actionId || !node.params) return false;
        const action = getActionInfo(node.actionId);
        if (!action) return true;

        const validParamIds = new Set(action.params.map(p => p.id));
        for (const paramId of Object.keys(node.params)) {
            if (!validParamIds.has(paramId)) return true;
        }
        return false;
    }

    // Find loopback connections (from failed Selector children back to Selector)
    function getLoopbackConnections(): { fromId: string; toId: string }[] {
        const connections: { fromId: string; toId: string }[] = [];

        if (!workflow) return connections;

        for (const [nodeId, node] of Object.entries(workflow.nodes)) {
            if (node.type === 'Selector' && node.children && node.children.length > 1) {
                // Each child except the last can loop back to the selector
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

        // Draw a curved path that goes to the right and back
        const offset = 30;
        return `M ${startX} ${startY}
                C ${startX + offset} ${startY}, ${endX + offset} ${endY}, ${endX} ${endY}`;
    }
</script>

<div class="workflow-tree-container relative h-full bg-gray-50 rounded-lg overflow-auto"
     on:click={handleCanvasClick}
     on:keydown={(e) => e.key === 'Escape' && closeContextMenu()}
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
        <!-- Tree canvas -->
        <svg width={canvasWidth} height={canvasHeight} class="workflow-canvas">
            <!-- Draw connections first (behind nodes) -->
            <g class="connections">
                {#each allNodes as layoutNode}
                    {#each layoutNode.children as child}
                        <path
                            d={getConnectionPath(layoutNode, child)}
                            fill="none"
                            stroke="#9CA3AF"
                            stroke-width="2"
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
            </g>

            <!-- Arrow marker definition -->
            <defs>
                <marker id="loopback-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L9,3 z" fill="#EF4444" />
                </marker>
            </defs>
        </svg>

        <!-- Nodes (positioned absolutely over SVG) -->
        {#each allNodes as layoutNode (layoutNode.id)}
            {@const colors = NODE_TYPE_COLORS[layoutNode.node.type]}
            {@const isSelected = selectedNodeId === layoutNode.id}
            {@const isInvalid = isInvalidAction(layoutNode.node) || hasInvalidParams(layoutNode.node)}
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="absolute rounded-lg border-2 shadow-sm cursor-pointer transition-all duration-150
                       {colors.bg} {colors.border}
                       {isSelected ? 'ring-2 ring-blue-500 ring-offset-2 shadow-md' : 'hover:shadow-md'}
                       {isInvalid ? 'border-red-500 ring-2 ring-red-200' : ''}"
                style="left: {layoutNode.x}px; top: {layoutNode.y}px; width: {NODE_WIDTH}px; height: {NODE_HEIGHT}px;"
                on:click={(e) => handleNodeClick(layoutNode.id, e)}
                on:dblclick={(e) => handleNodeDoubleClick(layoutNode.id, e)}
                on:contextmenu={(e) => handleContextMenu(layoutNode.id, e)}
            >
                <div class="flex flex-col items-center justify-center h-full p-2 text-center">
                    <span class="text-[10px] font-medium {colors.text} opacity-70 uppercase tracking-wider">
                        {NODE_TYPE_NAMES[layoutNode.node.type]}
                    </span>
                    <span class="text-sm font-semibold {colors.text} truncate w-full mt-0.5">
                        {getNodeDisplayName(layoutNode.node)}
                    </span>
                    {#if isInvalid}
                        <span class="text-[9px] text-red-600 font-medium mt-0.5">유효하지 않음</span>
                    {/if}
                </div>
            </div>
        {/each}
    {/if}

    <!-- Context Menu -->
    {#if contextMenu.show}
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div
            class="fixed bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50 min-w-[140px]"
            style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
            on:click|stopPropagation
        >
            <button
                class="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
                on:click={() => openAddModal(contextMenu.nodeId)}
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                자식 추가
            </button>
            <button
                class="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2"
                on:click={() => openEditModal(contextMenu.nodeId)}
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                편집
            </button>
            {#if contextMenu.nodeId !== workflow?.rootId}
                <div class="border-t border-gray-100 my-1"></div>
                <button
                    class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                    on:click={() => deleteNode(contextMenu.nodeId)}
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    삭제
                </button>
            {/if}
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

<!-- Edit Node Modal -->
{#if showEditModal && editNodeId}
    {@const editNode = workflow?.nodes?.[editNodeId]}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" on:click={() => showEditModal = false}>
        <div class="bg-white rounded-lg shadow-xl p-6 w-80" on:click|stopPropagation>
            <h3 class="text-lg font-bold text-gray-800 mb-4">노드 편집</h3>

            {#if editNode}
                <div class="space-y-4">
                    {#if editNode.type !== 'Action'}
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">노드 이름</label>
                            <input
                                type="text"
                                bind:value={editNodeName}
                                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                                placeholder="노드 이름"
                            />
                        </div>
                    {:else}
                        {@const action = getActionInfo(editNode.actionId)}
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">액션</label>
                            <p class="text-sm text-gray-600 mb-3">{action?.name || '알 수 없는 액션'}</p>
                        </div>

                        {#if action?.params && action.params.length > 0}
                            <div class="space-y-3">
                                <label class="block text-sm font-medium text-gray-700">파라미터</label>
                                {#each action.params as param}
                                    <div>
                                        <label class="block text-xs text-gray-500 mb-1">
                                            {param.name}
                                            {#if param.required}
                                                <span class="text-red-500">*</span>
                                            {/if}
                                        </label>
                                        <input
                                            type="text"
                                            bind:value={editNodeParams[param.id]}
                                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                                            placeholder={param.name}
                                        />
                                    </div>
                                {/each}
                            </div>
                        {:else}
                            <p class="text-sm text-gray-400">이 액션에는 파라미터가 없습니다.</p>
                        {/if}
                    {/if}
                </div>
            {/if}

            <div class="flex justify-end gap-2 mt-6">
                <button
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                    on:click={() => showEditModal = false}
                >
                    취소
                </button>
                <button
                    class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                    on:click={confirmEditNode}
                >
                    저장
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .workflow-tree-container {
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
