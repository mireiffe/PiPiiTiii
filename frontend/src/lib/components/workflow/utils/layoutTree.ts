// Tree layout calculation utilities for SvelteFlow

import type { WorkflowData, WorkflowNode } from "$lib/api/project";
import {
    NODE_WIDTH,
    NODE_HEIGHT,
    PHENOMENON_MIN_HEIGHT,
    H_SPACING,
    V_SPACING,
    CORE_NODE_H_SPACING,
    CORE_NODE_WIDTH,
    CORE_NODE_HEIGHT,
    CORE_NODE_IDS
} from "./constants";

export interface LayoutNode {
    id: string;
    node: WorkflowNode;
    x: number;
    y: number;
    width: number;
    height: number;
    children: LayoutNode[];
    parent: LayoutNode | null;
    isCoreNode?: boolean;  // core node 여부
}

export interface CoreNodeInfo {
    id: string;
    type: 'phenomenon' | 'candidateSearch' | 'causeDerivation';
    node: WorkflowNode;
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

// ========== Core Node Layout Functions ==========

/**
 * Check if workflow uses core node structure (has meta.coreNodes)
 */
export function isCoreNodeWorkflow(workflow: WorkflowData | null): boolean {
    return !!(workflow?.meta?.coreNodes && workflow.meta.coreNodes.length === 3);
}

/**
 * Identify core nodes from workflow
 */
export function identifyCoreNodes(workflow: WorkflowData): CoreNodeInfo[] {
    const coreNodes: CoreNodeInfo[] = [];
    const coreNodeIds = workflow.meta?.coreNodes || [
        CORE_NODE_IDS.PHENOMENON,
        CORE_NODE_IDS.CANDIDATE_SEARCH,
        CORE_NODE_IDS.CAUSE_DERIVATION
    ];

    for (const id of coreNodeIds) {
        const node = workflow.nodes[id];
        if (!node) continue;

        let type: CoreNodeInfo['type'];
        if (id === CORE_NODE_IDS.PHENOMENON || node.type === "Phenomenon") {
            type = 'phenomenon';
        } else if (id === CORE_NODE_IDS.CANDIDATE_SEARCH || (node.type === "Sequence" && node.name === "원인후보탐색")) {
            type = 'candidateSearch';
        } else if (id === CORE_NODE_IDS.CAUSE_DERIVATION || node.type === "Selector") {
            type = 'causeDerivation';
        } else {
            continue;
        }

        coreNodes.push({ id, type, node });
    }

    return coreNodes;
}

/**
 * Build layout tree for a single core node and its children
 */
function buildCoreNodeSubtree(
    workflow: WorkflowData,
    coreNodeId: string,
    coreNodeType: CoreNodeInfo['type']
): LayoutNode | null {
    const node = workflow.nodes[coreNodeId];
    if (!node) return null;

    const layoutNode: LayoutNode = {
        id: coreNodeId,
        node,
        x: 0,
        y: 0,
        width: CORE_NODE_WIDTH,
        height: CORE_NODE_HEIGHT,
        children: [],
        parent: null,
        isCoreNode: true
    };

    // Build children subtrees
    if (node.children) {
        for (const childId of node.children) {
            const child = buildLayoutTree(workflow, childId, layoutNode);
            if (child) {
                layoutNode.children.push(child);
            }
        }
    }

    return layoutNode;
}

/**
 * Position children of a core node vertically below it
 */
function positionCoreNodeChildren(
    coreNode: LayoutNode,
    startY: number
): void {
    if (coreNode.children.length === 0) return;

    const childrenStartY = startY + coreNode.height + V_SPACING;

    // Calculate total width needed for children
    const childWidths = coreNode.children.map(c => calculateSubtreeWidth(c));
    const totalChildrenWidth = childWidths.reduce((a, b) => a + b, 0) +
        (coreNode.children.length - 1) * H_SPACING;

    // Center children under the core node
    let childX = coreNode.x + (coreNode.width - totalChildrenWidth) / 2;

    for (let i = 0; i < coreNode.children.length; i++) {
        const childWidth = childWidths[i];
        positionNodes(coreNode.children[i], childrenStartY, childWidth, childX);
        childX += childWidth + H_SPACING;
    }
}

/**
 * Calculate core node layout - horizontal arrangement of core nodes with vertical children
 */
export function calculateCoreNodeLayout(workflow: WorkflowData | null): {
    coreNodes: LayoutNode[];
    allNodes: LayoutNode[];
    bounds: TreeBounds | null;
} {
    if (!workflow || !workflow.nodes) {
        return { coreNodes: [], allNodes: [], bounds: null };
    }

    const coreNodeInfos = identifyCoreNodes(workflow);
    if (coreNodeInfos.length === 0) {
        return { coreNodes: [], allNodes: [], bounds: null };
    }

    const coreNodes: LayoutNode[] = [];
    const startY = 50;
    let currentX = 50;

    // Build and position each core node
    for (const info of coreNodeInfos) {
        const layoutNode = buildCoreNodeSubtree(workflow, info.id, info.type);
        if (!layoutNode) continue;

        layoutNode.x = currentX;
        layoutNode.y = startY;

        // Position children below core node
        positionCoreNodeChildren(layoutNode, startY);

        coreNodes.push(layoutNode);
        currentX += CORE_NODE_WIDTH + CORE_NODE_H_SPACING;
    }

    // Flatten all nodes
    const allNodes: LayoutNode[] = [];
    for (const coreNode of coreNodes) {
        allNodes.push(coreNode);
        allNodes.push(...flattenTree(coreNode).filter(n => n.id !== coreNode.id));
    }

    // Calculate bounds
    if (allNodes.length === 0) {
        return { coreNodes, allNodes, bounds: null };
    }

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const node of allNodes) {
        minX = Math.min(minX, node.x);
        maxX = Math.max(maxX, node.x + node.width);
        minY = Math.min(minY, node.y);
        maxY = Math.max(maxY, node.y + node.height);
    }

    return {
        coreNodes,
        allNodes,
        bounds: { minX, maxX, minY, maxY }
    };
}
