<script lang="ts">
    import { createEventDispatcher, onMount, tick } from "svelte";
    import type {
        WorkflowData,
        WorkflowNode,
        WorkflowAction,
        SlideCapture,
    } from "$lib/api/project";
    // [수정됨] slide를 import 목록에 추가했습니다.
    import { fade, scale as scaleTransition, slide } from "svelte/transition";

    export let workflow: WorkflowData | null = null;
    export let workflowActions: WorkflowAction[] = [];
    export let readonly = false;

    const dispatch = createEventDispatcher();

    // --- Constants ---
    const NODE_TYPE_NAMES: Record<string, string> = {
        Phenomenon: "발생 현상",
        Selector: "원인 도출",
        Sequence: "원인 후보 분석",
        Condition: "분기",
        Action: "액션",
    };

    const NODE_TYPE_COLORS: Record<
        string,
        { bg: string; border: string; text: string; darkBg: string }
    > = {
        Phenomenon: {
            bg: "bg-red-100",
            border: "border-red-400",
            text: "text-red-700",
            darkBg: "bg-red-500",
        },
        Selector: {
            bg: "bg-purple-100",
            border: "border-purple-400",
            text: "text-purple-700",
            darkBg: "bg-purple-500",
        },
        Sequence: {
            bg: "bg-blue-100",
            border: "border-blue-400",
            text: "text-blue-700",
            darkBg: "bg-blue-500",
        },
        Condition: {
            bg: "bg-yellow-100",
            border: "border-yellow-400",
            text: "text-yellow-700",
            darkBg: "bg-yellow-500",
        },
        Action: {
            bg: "bg-green-100",
            border: "border-green-400",
            text: "text-green-700",
            darkBg: "bg-green-500",
        },
    };

    const NODE_WIDTH = 180;
    const NODE_HEIGHT = 80;
    const PHENOMENON_NODE_HEIGHT = 140; // Taller for captures
    const H_SPACING = 40;
    const V_SPACING = 80;
    const MAX_HISTORY = 50;

    // --- State ---
    let containerRef: HTMLDivElement;

    // Viewport State (Pan & Zoom)
    let transform = { x: 0, y: 0, k: 1 };
    let isPanning = false;
    let panStart = { x: 0, y: 0 };

    // Node Selection & Dragging
    let selectedNodeId: string | null = null;
    let draggedNodeId: string | null = null;
    let dropTargetId: string | null = null;
    let dropPosition: "child" | "before" | "after" | null = null;
    let isDragging = false;
    let dragStartPos = { x: 0, y: 0 }; // Mouse pos at drag start
    let dragNodeOffset = { x: 0, y: 0 }; // Offset within node
    let currentMousePos = { x: 0, y: 0 };

    // Context Menu
    let contextMenu = { show: false, x: 0, y: 0, nodeId: "" };

    // History
    let historyStack: WorkflowData[] = [];
    let historyIndex = -1;

    // Modal
    let showAddModal = false;
    let addModalParentId: string | null = null;
    let newNodeType: "Selector" | "Sequence" | "Condition" | "Action" =
        "Action";
    let newNodeActionId: string = "";

    // Layout
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
    let canvasSize = { w: 0, h: 0 };
    let allNodes: LayoutNode[] = [];

    // --- Reactivity ---
    $: if (workflow && historyStack.length === 0) {
        pushHistory(workflow);
    }

    $: if (workflow) {
        calculateLayout();
        // Reset selection if node no longer exists
        if (selectedNodeId && !workflow.nodes[selectedNodeId]) {
            selectedNodeId = null;
        }
    }

    $: selectedNode =
        selectedNodeId && workflow?.nodes?.[selectedNodeId]
            ? workflow.nodes[selectedNodeId]
            : null;
    $: selectedAction =
        selectedNode?.type === "Action"
            ? getActionInfo(selectedNode.actionId)
            : null;
    $: canUndo = historyIndex > 0;
    $: canRedo = historyIndex < historyStack.length - 1;

    $: loopbackConnections = getLoopbackConnections(workflow);

    // --- History Management ---
    function pushHistory(state: WorkflowData) {
        historyStack = historyStack.slice(0, historyIndex + 1);
        historyStack.push(JSON.parse(JSON.stringify(state)));
        if (historyStack.length > MAX_HISTORY)
            historyStack = historyStack.slice(1);
        historyIndex = historyStack.length - 1;
    }

    function undo() {
        if (historyIndex > 0) {
            historyIndex--;
            dispatch(
                "change",
                JSON.parse(JSON.stringify(historyStack[historyIndex])),
            );
        }
    }

    function redo() {
        if (historyIndex < historyStack.length - 1) {
            historyIndex++;
            dispatch(
                "change",
                JSON.parse(JSON.stringify(historyStack[historyIndex])),
            );
        }
    }

    function updateWorkflow(newWorkflow: WorkflowData) {
        pushHistory(newWorkflow);
        dispatch("change", newWorkflow);
    }

    // --- Layout Logic ---
    function calculateLayout() {
        if (!workflow || !workflow.rootId || !workflow.nodes) {
            layoutRoot = null;
            allNodes = [];
            return;
        }

        layoutRoot = buildLayoutTree(workflow.rootId, null);
        if (layoutRoot) {
            const treeWidth = calculateSubtreeWidth(layoutRoot);
            positionNodes(layoutRoot, 50, treeWidth); // Start at y=50
            const bounds = getTreeBounds(layoutRoot);

            // Canvas size covers the tree (plus padding)
            canvasSize = {
                w: Math.max(800, bounds.maxX + NODE_WIDTH + 100),
                h: Math.max(600, bounds.maxY + NODE_HEIGHT + 100),
            };

            allNodes = flattenTree(layoutRoot);
        }
    }

    function getNodeHeight(node: WorkflowNode): number {
        return node.type === "Phenomenon" ? PHENOMENON_NODE_HEIGHT : NODE_HEIGHT;
    }

    function buildLayoutTree(
        nodeId: string,
        parent: LayoutNode | null,
    ): LayoutNode | null {
        const node = workflow?.nodes?.[nodeId];
        if (!node) return null;

        const layoutNode: LayoutNode = {
            id: nodeId,
            node,
            x: 0,
            y: 0,
            width: NODE_WIDTH,
            height: getNodeHeight(node),
            children: [],
            parent,
        };

        if (node.children) {
            for (const childId of node.children) {
                const child = buildLayoutTree(childId, layoutNode);
                if (child) layoutNode.children.push(child);
            }
        }
        return layoutNode;
    }

    function calculateSubtreeWidth(node: LayoutNode): number {
        if (node.children.length === 0) return NODE_WIDTH;
        let totalWidth = 0;
        for (const child of node.children)
            totalWidth += calculateSubtreeWidth(child);
        totalWidth += (node.children.length - 1) * H_SPACING;
        return Math.max(NODE_WIDTH, totalWidth);
    }

    function positionNodes(
        node: LayoutNode,
        currentY: number,
        availableWidth: number,
        startX = 50,
    ) {
        node.y = currentY;

        if (node.children.length === 0) {
            node.x = startX + (availableWidth - NODE_WIDTH) / 2;
            return;
        }

        const childWidths = node.children.map((c) => calculateSubtreeWidth(c));
        const totalChildrenWidth =
            childWidths.reduce((a, b) => a + b, 0) +
            (node.children.length - 1) * H_SPACING;

        // Center parent relative to children
        node.x = startX + (availableWidth - NODE_WIDTH) / 2;

        const nextY = currentY + node.height + V_SPACING;
        let childX = startX + (availableWidth - totalChildrenWidth) / 2;
        for (let i = 0; i < node.children.length; i++) {
            const childWidth = childWidths[i];
            positionNodes(node.children[i], nextY, childWidth, childX);
            childX += childWidth + H_SPACING;
        }
    }

    function getTreeBounds(node: LayoutNode): {
        minX: number;
        maxX: number;
        maxY: number;
    } {
        let minX = node.x;
        let maxX = node.x;
        let maxY = node.y;
        for (const child of node.children) {
            const b = getTreeBounds(child);
            minX = Math.min(minX, b.minX);
            maxX = Math.max(maxX, b.maxX);
            maxY = Math.max(maxY, b.maxY);
        }
        return { minX, maxX, maxY };
    }

    function flattenTree(node: LayoutNode | null): LayoutNode[] {
        if (!node) return [];
        const result = [node];
        node.children.forEach((c) => result.push(...flattenTree(c)));
        return result;
    }

    // --- Viewport Interactions (Pan & Zoom) ---
    function handleWheel(e: WheelEvent) {
        if (contextMenu.show) return;
        e.preventDefault();

        const rect = containerRef.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;

        const delta = e.deltaY < 0 ? 1 : -1;
        const zoomFactor = 0.1;

        // Calculate new scale
        let newK = transform.k + delta * zoomFactor;
        newK = Math.min(Math.max(0.2, newK), 3); // Limit zoom 0.2x to 3x

        // Adjust position to zoom towards mouse
        const scaleRatio = newK / transform.k;
        const newX = offsetX - (offsetX - transform.x) * scaleRatio;
        const newY = offsetY - (offsetY - transform.y) * scaleRatio;

        transform = { x: newX, y: newY, k: newK };
    }

    function handleMouseDown(e: MouseEvent) {
        // Middle mouse or Left click on background
        if (e.button === 1 || (e.button === 0 && !isDragging)) {
            isPanning = true;
            panStart = {
                x: e.clientX - transform.x,
                y: e.clientY - transform.y,
            };
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
        if (isDragging) {
            handleDragEnd();
        }
    }

    function fitView() {
        if (!layoutRoot || !containerRef) return;
        const bounds = getTreeBounds(layoutRoot);
        const rect = containerRef.getBoundingClientRect();

        const treeW = bounds.maxX - bounds.minX + NODE_WIDTH;
        const treeH = bounds.maxY + NODE_HEIGHT;

        // Calculate scale to fit
        const padding = 100;
        const scaleX = (rect.width - padding) / treeW;
        const scaleY = (rect.height - padding) / treeH;
        let k = Math.min(scaleX, scaleY, 1); // Don't zoom in more than 1x initially
        k = Math.max(k, 0.2);

        // Center tree
        const treeCenterX = bounds.minX + treeW / 2;
        const treeCenterY = treeH / 2; // Center vertically slightly higher ideally, but this is fine

        const x = rect.width / 2 - treeCenterX * k;
        const y = 50; // Padding from top

        transform = { x, y, k };
    }

    onMount(() => {
        if (layoutRoot) setTimeout(fitView, 100);
    });

    // --- Drag & Drop ---
    function handleDragStart(e: MouseEvent, nodeId: string) {
        if (readonly || nodeId === workflow?.rootId) return;
        e.stopPropagation();
        e.preventDefault();

        // Close context menu
        contextMenu.show = false;
        // Select node
        selectedNodeId = nodeId;

        isDragging = true;
        draggedNodeId = nodeId;

        // Store offset for smooth dragging visual
        const node = allNodes.find((n) => n.id === nodeId);
        if (node) {
            // Convert mouse client to world space not needed for ghost,
            // but needed if we want to drag the actual node.
            // For now we just use a ghost element based on client coordinates.
            dragStartPos = { x: e.clientX, y: e.clientY };
            // Optional: calculate offset inside the node
            const rect = (e.target as Element)
                .closest(".node-element")
                ?.getBoundingClientRect();
            if (rect) {
                dragNodeOffset = {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                };
            }
        }

        currentMousePos = { x: e.clientX, y: e.clientY };
    }

    function handleDragMove(e: MouseEvent) {
        currentMousePos = { x: e.clientX, y: e.clientY };

        // Convert mouse position to World Coordinates
        const rect = containerRef.getBoundingClientRect();
        const worldX = (e.clientX - rect.left - transform.x) / transform.k;
        const worldY = (e.clientY - rect.top - transform.y) / transform.k;

        let targetId: string | null = null;
        let pos: "child" | "before" | "after" | null = null;
        let minDist = Infinity;

        // Find potential drop target
        for (const layoutNode of allNodes) {
            if (layoutNode.id === draggedNodeId) continue;
            if (isDescendant(draggedNodeId!, layoutNode.id)) continue;

            // Expand hit area slightly
            const hitPadding = 20;
            if (
                worldX >= layoutNode.x - hitPadding &&
                worldX <= layoutNode.x + NODE_WIDTH + hitPadding &&
                worldY >= layoutNode.y - hitPadding &&
                worldY <= layoutNode.y + NODE_HEIGHT + hitPadding
            ) {
                targetId = layoutNode.id;

                // Determine zone:
                // Node height = 80.
                // Top 25%: Before (Sibling)
                // Bottom 25%: After (Sibling)
                // Middle 50%: Child (if possible)

                const relativeY = (worldY - layoutNode.y) / NODE_HEIGHT;
                const canHaveChildren =
                    layoutNode.node.type !== "Action" &&
                    layoutNode.node.type !== "Condition";

                if (canHaveChildren) {
                    if (relativeY < 0.25) pos = "before";
                    else if (relativeY > 0.75) pos = "after";
                    else pos = "child";
                } else {
                    // Cannot have children
                    if (relativeY < 0.5) pos = "before";
                    else pos = "after";
                }
                break; // Found target
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

    function isDescendant(ancestorId: string, nodeId: string): boolean {
        const ancestor = workflow?.nodes?.[ancestorId];
        if (!ancestor?.children) return false;
        for (const childId of ancestor.children) {
            if (childId === nodeId || isDescendant(childId, nodeId))
                return true;
        }
        return false;
    }

    function moveNode(
        nodeId: string,
        targetId: string,
        position: "child" | "before" | "after",
    ) {
        const updatedWorkflow = JSON.parse(
            JSON.stringify(workflow),
        ) as WorkflowData;

        // 1. Remove from old parent
        Object.values(updatedWorkflow.nodes).forEach((node) => {
            if (node.children?.includes(nodeId)) {
                node.children = node.children.filter((id) => id !== nodeId);
            }
        });

        // 2. Add to new location
        if (position === "child") {
            const target = updatedWorkflow.nodes[targetId];
            if (!target.children) target.children = [];
            target.children.push(nodeId);
        } else {
            // Find parent of target
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
                    const idx = parent.children.indexOf(targetId);
                    const insertIdx = position === "before" ? idx : idx + 1;
                    parent.children.splice(insertIdx, 0, nodeId);
                }
            }
        }
        updateWorkflow(updatedWorkflow);
    }

    // --- Context Menu ---
    function handleNodeContextMenu(e: MouseEvent, nodeId: string) {
        if (readonly) return;
        e.preventDefault();
        e.stopPropagation();
        selectedNodeId = nodeId;
        contextMenu = {
            show: true,
            x: e.clientX,
            y: e.clientY,
            nodeId,
        };
    }

    function closeContextMenu() {
        contextMenu.show = false;
    }

    function handleCanvasClick() {
        selectedNodeId = null;
        closeContextMenu();
    }

    // --- Node Operations (Add/Delete/Edit) ---
    function openAddModal(parentId: string) {
        addModalParentId = parentId;
        newNodeType = "Action";
        newNodeActionId =
            workflowActions.length > 0 ? workflowActions[0].id : "";
        showAddModal = true;
        closeContextMenu();
    }

    function confirmAddNode() {
        if (!workflow || !addModalParentId) return;
        const newId = `node_${Date.now()}`;

        const newNode: WorkflowNode = {
            type: newNodeType,
            children:
                newNodeType !== "Action" && newNodeType !== "Condition"
                    ? []
                    : undefined,
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
        updated.nodes[addModalParentId].children =
            updated.nodes[addModalParentId].children || [];
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

        // Collect garbage
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
        // Create the workflow with 3-stage structure:
        // 1. Phenomenon (발생 현상) - Root
        // 2. Sequence (원인 후보 분석) - Left children for candidate analysis
        // 3. Selector (원인 도출) - Rightmost child for root cause finding
        updateWorkflow({
            rootId: "phenomenon",
            nodes: {
                "phenomenon": {
                    type: "Phenomenon",
                    name: "발생 현상",
                    description: "",
                    captures: [],
                    children: ["candidate_analysis", "root_cause_selector"]
                },
                "candidate_analysis": {
                    type: "Sequence",
                    name: "원인 후보 분석",
                    children: []
                },
                "root_cause_selector": {
                    type: "Selector",
                    name: "원인 도출",
                    children: []
                }
            },
            meta: { version: 1 },
        });
        setTimeout(fitView, 50);
        // Select the phenomenon node for editing
        selectedNodeId = "phenomenon";
    }

    // --- Helpers ---
    function getActionInfo(actionId: string | undefined) {
        return actionId
            ? workflowActions.find((a) => a.id === actionId)
            : undefined;
    }

    function getNodeDisplayName(node: WorkflowNode): string {
        if (node.type === "Action") {
            const action = getActionInfo(node.actionId);
            return action ? action.name : node.name || "알 수 없는 액션";
        }
        return node.name || NODE_TYPE_NAMES[node.type];
    }

    function getNodeParams(node: WorkflowNode) {
        if (node.type !== "Action" || !node.params) return [];
        const action = getActionInfo(node.actionId);
        if (!action) return [];
        return action.params
            .map((p) => ({
                name: p.name,
                value: node.params?.[p.id] || "",
            }))
            .filter((p) => p.value);
    }

    function getConnectionPath(parent: LayoutNode, child: LayoutNode): string {
        const startX = parent.x + NODE_WIDTH / 2;
        const startY = parent.y + NODE_HEIGHT;
        const endX = child.x + NODE_WIDTH / 2;
        const endY = child.y;
        const midY = (startY + endY) / 2;
        return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
    }

    function getLoopbackConnections(wf: WorkflowData | null) {
        if (!wf) return [];
        const conns: { fromId: string; toId: string }[] = [];
        for (const [id, node] of Object.entries(wf.nodes)) {
            if (
                node.type === "Selector" &&
                node.children &&
                node.children.length > 1
            ) {
                for (let i = 0; i < node.children.length - 1; i++) {
                    conns.push({ fromId: node.children[i], toId: id });
                }
            }
        }
        return conns;
    }

    function getLoopbackPath(fromNode: LayoutNode, toNode: LayoutNode): string {
        const startX = fromNode.x + NODE_WIDTH;
        const startY = fromNode.y + NODE_HEIGHT / 2;
        const endX = toNode.x + NODE_WIDTH;
        const endY = toNode.y + NODE_HEIGHT / 2;
        return `M ${startX} ${startY} C ${startX + 50} ${startY}, ${endX + 50} ${endY}, ${endX} ${endY}`;
    }

    // --- Inline Updates (Name, Params, Type, Description, Captures) ---
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

    // Export function to add capture from external component
    export function addCaptureToNode(nodeId: string, capture: SlideCapture) {
        addCapture(nodeId, capture);
    }

    // Get the current phenomenon node ID (for external components to add captures)
    export function getPhenomenonNodeId(): string | null {
        if (!workflow) return null;
        // Find the phenomenon node
        for (const [id, node] of Object.entries(workflow.nodes)) {
            if (node.type === "Phenomenon") return id;
        }
        return null;
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
    function updateNodeType(nodeId: string, newType: any) {
        if (!workflow || nodeId === workflow.rootId) return;
        const updated = JSON.parse(JSON.stringify(workflow));
        const node = updated.nodes[nodeId];
        if (!node) return;

        // Type change logic (clearing children if incompatible etc.)
        node.type = newType;
        if (newType === "Action" || newType === "Condition") {
            // Clean children
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
</script>

<svelte:window
    on:mousemove={handleWindowMouseMove}
    on:mouseup={handleWindowMouseUp}
    on:keydown={(e) => {
        if (readonly) return;
        if ((e.ctrlKey || e.metaKey) && e.key === "z") {
            e.preventDefault();
            e.shiftKey ? redo() : undo();
        }
        if (
            e.key === "Delete" &&
            selectedNodeId &&
            selectedNodeId !== workflow?.rootId
        )
            deleteNode(selectedNodeId);
        if (e.key === " " && !e.target.matches("input, textarea")) {
            e.preventDefault();
            fitView();
        }
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
        <div
            class="flex flex-col items-center justify-center h-full text-gray-400 z-10"
        >
            <svg
                class="w-16 h-16 mb-4 opacity-30"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
                />
            </svg>
            <p class="mb-4">워크플로우가 비어있습니다</p>
            {#if !readonly}
                <button
                    class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                    on:click={createInitialWorkflow}>워크플로우 생성</button
                >
            {/if}
        </div>
    {:else}
        {#if !readonly}
            <div
                class="absolute top-2 left-2 right-2 z-20 flex justify-between pointer-events-none"
            >
                <div
                    class="bg-white/90 backdrop-blur border border-gray-200 rounded-lg shadow-sm p-1 flex items-center gap-1 pointer-events-auto"
                >
                    <button
                        class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
                        on:click={undo}
                        disabled={!canUndo}
                        title="실행취소 (Ctrl+Z)"
                    >
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
                            /></svg
                        >
                    </button>
                    <button
                        class="p-1.5 hover:bg-gray-100 rounded disabled:opacity-30"
                        on:click={redo}
                        disabled={!canRedo}
                        title="다시실행 (Ctrl+Shift+Z)"
                    >
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6"
                            /></svg
                        >
                    </button>
                    <div class="w-px h-4 bg-gray-300 mx-1"></div>
                    <button
                        class="p-1.5 hover:bg-gray-100 rounded"
                        on:click={fitView}
                        title="화면 맞춤 (Space)"
                    >
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                            /></svg
                        >
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

        <div
            class="absolute top-0 left-0 origin-top-left transition-transform duration-75 will-change-transform"
            style="transform: translate({transform.x}px, {transform.y}px) scale({transform.k});"
        >
            <svg
                class="overflow-visible pointer-events-none"
                style="width: 1px; height: 1px;"
            >
                <defs>
                    <marker
                        id="arrow"
                        markerWidth="10"
                        markerHeight="10"
                        refX="9"
                        refY="3"
                        orient="auto"
                        ><path d="M0,0 L0,6 L9,3 z" fill="#9CA3AF" /></marker
                    >
                    <marker
                        id="arrow-blue"
                        markerWidth="10"
                        markerHeight="10"
                        refX="9"
                        refY="3"
                        orient="auto"
                        ><path d="M0,0 L0,6 L9,3 z" fill="#3B82F6" /></marker
                    >
                    <marker
                        id="loopback-arrow"
                        markerWidth="10"
                        markerHeight="10"
                        refX="9"
                        refY="3"
                        orient="auto"
                        ><path d="M0,0 L0,6 L9,3 z" fill="#EF4444" /></marker
                    >
                </defs>
                <g>
                    {#each allNodes as layoutNode}
                        {#each layoutNode.children as child}
                            <path
                                d={getConnectionPath(layoutNode, child)}
                                fill="none"
                                stroke="#9CA3AF"
                                stroke-width="2"
                                marker-end="url(#arrow)"
                            />
                        {/each}
                    {/each}

                    {#each loopbackConnections as conn}
                        {@const from = allNodes.find(
                            (n) => n.id === conn.fromId,
                        )}
                        {@const to = allNodes.find((n) => n.id === conn.toId)}
                        {#if from && to}
                            <path
                                d={getLoopbackPath(from, to)}
                                fill="none"
                                stroke="#EF4444"
                                stroke-width="2"
                                stroke-dasharray="5,5"
                                marker-end="url(#loopback-arrow)"
                                opacity="0.6"
                            />
                        {/if}
                    {/each}

                    {#if dropTargetId && dropPosition}
                        {@const target = allNodes.find(
                            (n) => n.id === dropTargetId,
                        )}
                        {#if target}
                            {#if dropPosition === "child"}
                                <rect
                                    x={target.x - 4}
                                    y={target.y - 4}
                                    width={NODE_WIDTH + 8}
                                    height={NODE_HEIGHT + 8}
                                    rx="12"
                                    fill="none"
                                    stroke="#3B82F6"
                                    stroke-width="3"
                                    stroke-dasharray="4"
                                />
                            {:else}
                                <line
                                    x1={target.x}
                                    y1={dropPosition === "before"
                                        ? target.y - 10
                                        : target.y + NODE_HEIGHT + 10}
                                    x2={target.x + NODE_WIDTH}
                                    y2={dropPosition === "before"
                                        ? target.y - 10
                                        : target.y + NODE_HEIGHT + 10}
                                    stroke="#3B82F6"
                                    stroke-width="4"
                                    stroke-linecap="round"
                                />
                            {/if}
                        {/if}
                    {/if}
                </g>
            </svg>

            {#each allNodes as layoutNode (layoutNode.id)}
                {@const colors = NODE_TYPE_COLORS[layoutNode.node.type]}
                {@const isSelected = selectedNodeId === layoutNode.id}
                {@const isDraggingThis = draggedNodeId === layoutNode.id}
                <div
                    class="absolute rounded-lg border-2 shadow-sm transition-shadow duration-150 group node-element
                           {colors.bg} {colors.border}
                           {isSelected
                        ? 'ring-2 ring-blue-500 z-10 shadow-lg'
                        : 'hover:shadow-md'}
                           {isDraggingThis ? 'opacity-40' : ''}"
                    style="left: {layoutNode.x}px; top: {layoutNode.y}px; width: {NODE_WIDTH}px; height: {NODE_HEIGHT}px;"
                    on:mousedown={(e) => handleDragStart(e, layoutNode.id)}
                    on:contextmenu={(e) =>
                        handleNodeContextMenu(e, layoutNode.id)}
                >
                    <div
                        class="absolute -top-2.5 left-2 px-1.5 py-0.5 rounded text-[9px] font-bold text-white {colors.darkBg}"
                    >
                        {NODE_TYPE_NAMES[layoutNode.node.type]}
                    </div>

                    <div class="flex flex-col p-2 pt-3 h-full justify-between overflow-hidden">
                        <span
                            class="text-sm font-semibold {colors.text} truncate"
                            title={getNodeDisplayName(layoutNode.node)}
                        >
                            {getNodeDisplayName(layoutNode.node)}
                        </span>

                        {#if layoutNode.node.type === "Phenomenon"}
                            <!-- Phenomenon node: show captures and description -->
                            <div class="flex-1 flex flex-col gap-1 mt-1 overflow-hidden">
                                {#if layoutNode.node.captures && layoutNode.node.captures.length > 0}
                                    <div class="flex gap-1 flex-wrap max-h-[50px] overflow-hidden">
                                        {#each layoutNode.node.captures.slice(0, 4) as capture, idx}
                                            <div class="w-10 h-8 bg-gray-200 rounded border border-gray-300 flex items-center justify-center text-[8px] text-gray-500 overflow-hidden">
                                                {#if capture.thumbnailDataUrl}
                                                    <img src={capture.thumbnailDataUrl} alt="캡처 {idx + 1}" class="w-full h-full object-cover" />
                                                {:else}
                                                    S{capture.slideIndex}
                                                {/if}
                                            </div>
                                        {/each}
                                        {#if layoutNode.node.captures.length > 4}
                                            <div class="w-10 h-8 bg-gray-100 rounded border border-gray-300 flex items-center justify-center text-[8px] text-gray-500">
                                                +{layoutNode.node.captures.length - 4}
                                            </div>
                                        {/if}
                                    </div>
                                {:else}
                                    <div class="text-[9px] text-gray-400 italic">
                                        캡처 이미지 없음
                                    </div>
                                {/if}
                                {#if layoutNode.node.description}
                                    <div class="text-[9px] text-gray-600 truncate" title={layoutNode.node.description}>
                                        {layoutNode.node.description}
                                    </div>
                                {/if}
                            </div>
                        {:else if layoutNode.node.type === "Action"}
                            {@const params = getNodeParams(layoutNode.node)}
                            <div
                                class="text-[9px] text-gray-500 overflow-hidden"
                            >
                                {#each params.slice(0, 2) as p}
                                    <div class="truncate">
                                        <span class="font-bold">{p.name}:</span>
                                        {p.value}
                                    </div>
                                {/each}
                                {#if params.length > 2}<div>
                                        +{params.length - 2} more
                                    </div>{/if}
                            </div>
                        {/if}
                    </div>

                    {#if isDragging && draggedNodeId !== layoutNode.id && !isDescendant(draggedNodeId, layoutNode.id)}{/if}
                </div>
            {/each}
        </div>

        {#if isDragging && draggedNodeId}
            {@const dragNode = allNodes.find((n) => n.id === draggedNodeId)}
            {#if dragNode}
                {@const colors = NODE_TYPE_COLORS[dragNode.node.type]}
                <div
                    class="fixed pointer-events-none z-50 rounded-lg border-2 shadow-xl opacity-90 {colors.bg} {colors.border} flex items-center justify-center"
                    style="width: {NODE_WIDTH}px; height: {NODE_HEIGHT}px; left: {currentMousePos.x -
                        dragNodeOffset.x}px; top: {currentMousePos.y -
                        dragNodeOffset.y}px;"
                >
                    <span class="font-bold {colors.text}"
                        >{getNodeDisplayName(dragNode.node)}</span
                    >
                </div>
            {/if}
        {/if}
    {/if}

    {#if selectedNode && !readonly && workflow}
        <div
            class="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-3 shadow-lg z-30 max-h-[250px] overflow-y-auto"
            transition:slide={{ duration: 200 }}
        >
            <div class="flex items-center justify-between mb-3">
                <h3
                    class="font-bold text-gray-800 text-sm flex items-center gap-2"
                >
                    <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                    노드 설정
                </h3>
                <button
                    class="text-gray-400 hover:text-gray-600"
                    on:click={() => (selectedNodeId = null)}>✕</button
                >
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
                            캡처 이미지 ({selectedNode.captures?.length || 0}개)
                        </label>
                        <p class="text-[10px] text-gray-400 mb-2">
                            캔버스에서 마우스 우클릭+드래그로 캡처 영역을 지정하세요
                        </p>
                        {#if selectedNode.captures && selectedNode.captures.length > 0}
                            <div class="flex gap-2 flex-wrap max-h-[80px] overflow-y-auto">
                                {#each selectedNode.captures as capture, idx}
                                    <div class="relative group">
                                        <div class="w-14 h-12 bg-gray-200 rounded border border-gray-300 flex items-center justify-center text-[10px] text-gray-500 overflow-hidden">
                                            {#if capture.thumbnailDataUrl}
                                                <img src={capture.thumbnailDataUrl} alt="캡처 {idx + 1}" class="w-full h-full object-cover" />
                                            {:else}
                                                슬라이드 {capture.slideIndex}
                                            {/if}
                                        </div>
                                        <button
                                            class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                                            on:click={() => removeCapture(selectedNodeId, idx)}
                                            title="캡처 삭제"
                                        >×</button>
                                    </div>
                                {/each}
                            </div>
                        {:else}
                            <div class="text-xs text-gray-400 italic py-2">캡처된 이미지가 없습니다</div>
                        {/if}
                    </div>
                </div>
            {:else}
                <!-- Other node types settings -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="space-y-3">
                        <div>
                            <label
                                class="block text-xs font-medium text-gray-500 mb-1"
                                >타입</label
                            >
                            {#if selectedNodeId === workflow.rootId}
                                <div class="text-sm font-medium">
                                    {NODE_TYPE_NAMES[selectedNode.type]}
                                </div>
                            {:else}
                                <select
                                    class="w-full text-sm border rounded px-2 py-1.5"
                                    value={selectedNode.type}
                                    on:change={(e) =>
                                        updateNodeType(
                                            selectedNodeId,
                                            e.currentTarget.value,
                                        )}
                                >
                                    <option value="Sequence"
                                        >원인 후보 분석 (Sequence)</option
                                    >
                                    <option value="Selector">원인 도출 (Selector)</option
                                    >
                                    <option value="Condition"
                                        >분기 (Condition)</option
                                    >
                                    <option value="Action">액션 (Action)</option>
                                </select>
                            {/if}
                        </div>

                        {#if selectedNode.type !== "Action"}
                            <div>
                                <label
                                    class="block text-xs font-medium text-gray-500 mb-1"
                                    >이름</label
                                >
                                <input
                                    type="text"
                                    class="w-full text-sm border rounded px-2 py-1.5"
                                    value={selectedNode.name || ""}
                                    on:change={(e) =>
                                        updateNodeName(
                                            selectedNodeId,
                                            e.currentTarget.value,
                                        )}
                                />
                            </div>
                        {:else}
                            <div>
                                <label
                                    class="block text-xs font-medium text-gray-500 mb-1"
                                    >액션</label
                                >
                                <select
                                    class="w-full text-sm border rounded px-2 py-1.5"
                                    value={selectedNode.actionId || ""}
                                    on:change={(e) =>
                                        updateNodeAction(
                                            selectedNodeId,
                                            e.currentTarget.value,
                                        )}
                                >
                                    {#each workflowActions as action}
                                        <option value={action.id}
                                            >{action.name}</option
                                        >
                                    {/each}
                                </select>
                            </div>
                        {/if}
                    </div>

                    <div class="space-y-3">
                        {#if selectedNode.type === "Action" && selectedAction}
                            <div>
                                <label
                                    class="block text-xs font-medium text-gray-500 mb-1"
                                    >파라미터</label
                                >
                                <div
                                    class="space-y-2 max-h-[120px] overflow-y-auto pr-1"
                                >
                                    {#each selectedAction.params as param}
                                        <div class="flex flex-col gap-0.5">
                                            <span class="text-[10px] text-gray-400"
                                                >{param.name}{#if param.required}*{/if}</span
                                            >
                                            <input
                                                type="text"
                                                class="w-full text-xs border rounded px-2 py-1"
                                                value={selectedNode.params?.[
                                                    param.id
                                                ] || ""}
                                                on:change={(e) =>
                                                    updateNodeParam(
                                                        selectedNodeId,
                                                        param.id,
                                                        e.currentTarget.value,
                                                    )}
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
                                    >노드 삭제</button
                                >
                            </div>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</div>

{#if contextMenu.show}
    <div class="fixed inset-0 z-40" on:click={closeContextMenu}></div>
    <div
        class="fixed z-50 bg-white rounded shadow-lg border border-gray-200 py-1 min-w-[150px]"
        style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
    >
        {#if workflow.nodes[contextMenu.nodeId].type !== "Action"}
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

{#if showAddModal}
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
                    <label class="block text-sm font-medium text-gray-700 mb-1"
                        >타입</label
                    >
                    <select
                        bind:value={newNodeType}
                        class="w-full border rounded px-3 py-2"
                    >
                        <option value="Sequence">원인 후보 분석</option>
                        <option value="Selector">원인 도출</option>
                        <option value="Condition">분기</option>
                        <option value="Action">액션</option>
                    </select>
                </div>
                {#if newNodeType === "Action"}
                    <div>
                        <label
                            class="block text-sm font-medium text-gray-700 mb-1"
                            >액션</label
                        >
                        <select
                            bind:value={newNodeActionId}
                            class="w-full border rounded px-3 py-2"
                        >
                            {#each workflowActions as action}<option
                                    value={action.id}>{action.name}</option
                                >{/each}
                        </select>
                    </div>
                {/if}
            </div>
            <div class="flex justify-end gap-2 mt-6">
                <button
                    class="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded"
                    on:click={() => (showAddModal = false)}>취소</button
                >
                <button
                    class="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded"
                    on:click={confirmAddNode}>추가</button
                >
            </div>
        </div>
    </div>
{/if}

<style>
    .workflow-container {
        /* Grid pattern background */
        background-size: 40px 40px;
        background-image: linear-gradient(
                to right,
                rgba(0, 0, 0, 0.05) 1px,
                transparent 1px
            ),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
    }
</style>
