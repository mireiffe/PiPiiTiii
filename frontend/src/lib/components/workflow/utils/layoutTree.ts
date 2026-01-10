// Tree layout calculation utilities for SvelteFlow

import type { WorkflowData, WorkflowNode } from "$lib/api/project";
import { NODE_WIDTH, NODE_HEIGHT, PHENOMENON_MIN_HEIGHT, H_SPACING, V_SPACING } from "./constants";

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

export interface TreeBounds {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
}

/**
 * Get the height for a node based on its type and content
 */
export function getNodeHeight(node: WorkflowNode): number {
    if (node.type === "Phenomenon") {
        // Base height for phenomenon nodes - will be dynamically adjusted by the component
        const captureCount = node.captures?.length || 0;
        const hasDescription = !!node.description;

        // Estimate height based on content
        let height = 60; // Base (type badge + padding)
        if (captureCount > 0) {
            height += Math.min(6, captureCount) * 20 + 20; // Capture badges
        }
        if (hasDescription) {
            height += 40; // Description area
        }

        return Math.max(PHENOMENON_MIN_HEIGHT, Math.min(height, 300));
    }
    return NODE_HEIGHT;
}

/**
 * Build a layout tree from workflow data
 */
export function buildLayoutTree(
    workflow: WorkflowData,
    nodeId: string,
    parent: LayoutNode | null = null
): LayoutNode | null {
    const node = workflow.nodes?.[nodeId];
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

/**
 * Calculate the width of a subtree
 */
export function calculateSubtreeWidth(node: LayoutNode): number {
    if (node.children.length === 0) return NODE_WIDTH;

    let totalWidth = 0;
    for (const child of node.children) {
        totalWidth += calculateSubtreeWidth(child);
    }
    totalWidth += (node.children.length - 1) * H_SPACING;

    return Math.max(NODE_WIDTH, totalWidth);
}

/**
 * Position nodes in the tree layout
 */
export function positionNodes(
    node: LayoutNode,
    currentY: number,
    availableWidth: number,
    startX: number = 50
): void {
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

/**
 * Get the bounds of the tree
 */
export function getTreeBounds(node: LayoutNode): TreeBounds {
    let minX = node.x;
    let maxX = node.x + node.width;
    let minY = node.y;
    let maxY = node.y + node.height;

    for (const child of node.children) {
        const b = getTreeBounds(child);
        minX = Math.min(minX, b.minX);
        maxX = Math.max(maxX, b.maxX);
        minY = Math.min(minY, b.minY);
        maxY = Math.max(maxY, b.maxY);
    }

    return { minX, maxX, minY, maxY };
}

/**
 * Flatten the tree into an array
 */
export function flattenTree(node: LayoutNode | null): LayoutNode[] {
    if (!node) return [];
    const result = [node];
    node.children.forEach((c) => result.push(...flattenTree(c)));
    return result;
}

/**
 * Calculate full tree layout and return positioned nodes
 */
export function calculateTreeLayout(workflow: WorkflowData | null): {
    layoutRoot: LayoutNode | null;
    allNodes: LayoutNode[];
    bounds: TreeBounds | null;
} {
    if (!workflow || !workflow.rootId || !workflow.nodes) {
        return { layoutRoot: null, allNodes: [], bounds: null };
    }

    const layoutRoot = buildLayoutTree(workflow, workflow.rootId);
    if (!layoutRoot) {
        return { layoutRoot: null, allNodes: [], bounds: null };
    }

    const treeWidth = calculateSubtreeWidth(layoutRoot);
    positionNodes(layoutRoot, 50, treeWidth);
    const bounds = getTreeBounds(layoutRoot);
    const allNodes = flattenTree(layoutRoot);

    return { layoutRoot, allNodes, bounds };
}
