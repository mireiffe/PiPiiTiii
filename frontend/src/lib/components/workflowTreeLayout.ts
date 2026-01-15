// WorkflowTree Layout Utilities

import type { WorkflowData, WorkflowNode, WorkflowAction, SlideCapture } from "$lib/api/project";

// Constants
export const NODE_WIDTH = 180;
export const NODE_HEIGHT = 80;
export const PHENOMENON_NODE_HEIGHT = 140;
export const H_SPACING = 40;
export const V_SPACING = 80;
export const MAX_HISTORY = 50;

export const NODE_TYPE_NAMES: Record<string, string> = {
    Phenomenon: "발생 현상",
    Selector: "원인 도출",
    Sequence: "원인 후보 분석",
    Condition: "분기",
    Action: "액션",
};

export const NODE_TYPE_COLORS: Record<string, { bg: string; border: string; text: string; darkBg: string }> = {
    Phenomenon: { bg: "bg-red-100", border: "border-red-400", text: "text-red-700", darkBg: "bg-red-500" },
    Selector: { bg: "bg-purple-100", border: "border-purple-400", text: "text-purple-700", darkBg: "bg-purple-500" },
    Sequence: { bg: "bg-blue-100", border: "border-blue-400", text: "text-blue-700", darkBg: "bg-blue-500" },
    Condition: { bg: "bg-yellow-100", border: "border-yellow-400", text: "text-yellow-700", darkBg: "bg-yellow-500" },
    Action: { bg: "bg-green-100", border: "border-green-400", text: "text-green-700", darkBg: "bg-green-500" },
};

export interface LayoutNode {
    id: string;
    node: WorkflowNode;
    x: number;
    y: number;
    width: number;
    height: number;
    children: LayoutNode[];
    parent: LayoutNode | null;
}

export interface CanvasSize {
    w: number;
    h: number;
}

export interface Transform {
    x: number;
    y: number;
    k: number;
}

export function getNodeHeight(node: WorkflowNode): number {
    return node.type === "Phenomenon" ? PHENOMENON_NODE_HEIGHT : NODE_HEIGHT;
}

export function buildLayoutTree(
    workflow: WorkflowData | null,
    nodeId: string,
    parent: LayoutNode | null
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
            const child = buildLayoutTree(workflow, childId, layoutNode);
            if (child) layoutNode.children.push(child);
        }
    }
    return layoutNode;
}

export function calculateSubtreeWidth(node: LayoutNode): number {
    if (node.children.length === 0) return NODE_WIDTH;
    let totalWidth = 0;
    for (const child of node.children) {
        totalWidth += calculateSubtreeWidth(child);
    }
    totalWidth += (node.children.length - 1) * H_SPACING;
    return Math.max(NODE_WIDTH, totalWidth);
}

export function positionNodes(
    node: LayoutNode,
    currentY: number,
    availableWidth: number,
    startX = 50
): void {
    node.y = currentY;

    if (node.children.length === 0) {
        node.x = startX + (availableWidth - NODE_WIDTH) / 2;
        return;
    }

    const childWidths = node.children.map((c) => calculateSubtreeWidth(c));
    const totalChildrenWidth = childWidths.reduce((a, b) => a + b, 0) + (node.children.length - 1) * H_SPACING;

    node.x = startX + (availableWidth - NODE_WIDTH) / 2;

    const nextY = currentY + node.height + V_SPACING;
    let childX = startX + (availableWidth - totalChildrenWidth) / 2;
    for (let i = 0; i < node.children.length; i++) {
        const childWidth = childWidths[i];
        positionNodes(node.children[i], nextY, childWidth, childX);
        childX += childWidth + H_SPACING;
    }
}

export function getTreeBounds(node: LayoutNode): { minX: number; maxX: number; maxY: number } {
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

export function flattenTree(node: LayoutNode | null): LayoutNode[] {
    if (!node) return [];
    const result = [node];
    node.children.forEach((c) => result.push(...flattenTree(c)));
    return result;
}

export function calculateLayout(workflow: WorkflowData | null): { layoutRoot: LayoutNode | null; canvasSize: CanvasSize; allNodes: LayoutNode[] } {
    if (!workflow || !workflow.rootId || !workflow.nodes) {
        return { layoutRoot: null, canvasSize: { w: 0, h: 0 }, allNodes: [] };
    }

    const layoutRoot = buildLayoutTree(workflow, workflow.rootId, null);
    if (!layoutRoot) {
        return { layoutRoot: null, canvasSize: { w: 0, h: 0 }, allNodes: [] };
    }

    const treeWidth = calculateSubtreeWidth(layoutRoot);
    positionNodes(layoutRoot, 50, treeWidth);
    const bounds = getTreeBounds(layoutRoot);

    const canvasSize = {
        w: Math.max(800, bounds.maxX + NODE_WIDTH + 100),
        h: Math.max(600, bounds.maxY + NODE_HEIGHT + 100),
    };

    const allNodes = flattenTree(layoutRoot);

    return { layoutRoot, canvasSize, allNodes };
}

// SVG Path helpers
export function getConnectionPath(parent: LayoutNode, child: LayoutNode): string {
    const startX = parent.x + NODE_WIDTH / 2;
    const startY = parent.y + NODE_HEIGHT;
    const endX = child.x + NODE_WIDTH / 2;
    const endY = child.y;
    const midY = (startY + endY) / 2;
    return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
}

export function getLoopbackPath(fromNode: LayoutNode, toNode: LayoutNode): string {
    const startX = fromNode.x + NODE_WIDTH;
    const startY = fromNode.y + NODE_HEIGHT / 2;
    const endX = toNode.x + NODE_WIDTH;
    const endY = toNode.y + NODE_HEIGHT / 2;
    return `M ${startX} ${startY} C ${startX + 50} ${startY}, ${endX + 50} ${endY}, ${endX} ${endY}`;
}

export function getLoopbackConnections(workflow: WorkflowData | null): { fromId: string; toId: string }[] {
    if (!workflow) return [];
    const conns: { fromId: string; toId: string }[] = [];
    for (const [id, node] of Object.entries(workflow.nodes)) {
        if (node.type === "Selector" && node.children && node.children.length > 1) {
            for (let i = 0; i < node.children.length - 1; i++) {
                conns.push({ fromId: node.children[i], toId: id });
            }
        }
    }
    return conns;
}

// Node helpers
export function getNodeDisplayName(node: WorkflowNode, workflowActions: WorkflowAction[]): string {
    if (node.type === "Action") {
        const action = node.actionId ? workflowActions.find((a) => a.id === node.actionId) : undefined;
        return action ? action.name : node.name || "알 수 없는 액션";
    }
    return node.name || NODE_TYPE_NAMES[node.type];
}

export function getNodeParams(node: WorkflowNode, workflowActions: WorkflowAction[]): { name: string; value: string }[] {
    if (node.type !== "Action" || !node.params) return [];
    const action = node.actionId ? workflowActions.find((a) => a.id === node.actionId) : undefined;
    if (!action) return [];
    return action.params
        .map((p) => ({ name: p.name, value: node.params?.[p.id] || "" }))
        .filter((p) => p.value);
}

export function isDescendant(workflow: WorkflowData | null, ancestorId: string, nodeId: string): boolean {
    const ancestor = workflow?.nodes?.[ancestorId];
    if (!ancestor?.children) return false;
    for (const childId of ancestor.children) {
        if (childId === nodeId || isDescendant(workflow, childId, nodeId)) return true;
    }
    return false;
}
