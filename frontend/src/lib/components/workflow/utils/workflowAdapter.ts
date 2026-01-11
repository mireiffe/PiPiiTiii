// Adapter utilities to convert WorkflowData to SvelteFlow nodes/edges

import type { Node, Edge } from "@xyflow/svelte";
import type { WorkflowData, WorkflowNode } from "$lib/api/project";
import {
    calculateTreeLayout,
    calculateCoreNodeLayout,
    isCoreNodeWorkflow,
    type LayoutNode
} from "./layoutTree";
import { NODE_TYPE_COLORS, NODE_WIDTH, CORE_NODE_IDS } from "./constants";

// Custom node data type
export interface WorkflowNodeData extends Record<string, unknown> {
    nodeId: string;
    workflowNode: WorkflowNode;
    label: string;
    isRoot?: boolean;
    isCoreNode?: boolean;
    coreNodeType?: 'phenomenon' | 'candidateSearch' | 'causeDerivation';
}

// Custom edge data type
export interface WorkflowEdgeData extends Record<string, unknown> {
    isLoopback?: boolean;
}

/**
 * Get core node type for a given node ID
 */
function getCoreNodeType(nodeId: string, workflow: WorkflowData): WorkflowNodeData['coreNodeType'] | undefined {
    const coreNodes = workflow.meta?.coreNodes || [
        CORE_NODE_IDS.PHENOMENON,
        CORE_NODE_IDS.CANDIDATE_SEARCH,
        CORE_NODE_IDS.CAUSE_DERIVATION
    ];

    if (nodeId === CORE_NODE_IDS.PHENOMENON || (coreNodes[0] === nodeId)) {
        return 'phenomenon';
    }
    if (nodeId === CORE_NODE_IDS.CANDIDATE_SEARCH || (coreNodes[1] === nodeId)) {
        return 'candidateSearch';
    }
    if (nodeId === CORE_NODE_IDS.CAUSE_DERIVATION || (coreNodes[2] === nodeId)) {
        return 'causeDerivation';
    }
    return undefined;
}

/**
 * Convert WorkflowData to SvelteFlow nodes array
 */
export function workflowToNodes(workflow: WorkflowData | null): Node<WorkflowNodeData>[] {
    if (!workflow || !workflow.rootId || !workflow.nodes) {
        return [];
    }

    // Use core node layout if workflow has meta.coreNodes
    const useCoreLayout = isCoreNodeWorkflow(workflow);
    const { allNodes } = useCoreLayout
        ? calculateCoreNodeLayout(workflow)
        : calculateTreeLayout(workflow);

    return allNodes.map((layoutNode) => {
        const nodeType = layoutNode.node.type;
        const isCoreNode = layoutNode.isCoreNode || false;
        const coreNodeType = isCoreNode ? getCoreNodeType(layoutNode.id, workflow) : undefined;

        return {
            id: layoutNode.id,
            type: isCoreNode ? "CoreNode" : nodeType, // Use CoreNode type for core nodes
            position: { x: layoutNode.x, y: layoutNode.y },
            data: {
                nodeId: layoutNode.id,
                workflowNode: layoutNode.node,
                label: layoutNode.node.name || nodeType,
                isCoreNode,
                coreNodeType,
            },
            draggable: false, // Auto-layout only
            selectable: true,
            width: layoutNode.width,
            height: layoutNode.height,
        };
    });
}

/**
 * Get all edges including normal parent-child and loopback connections
 */
export function workflowToEdges(workflow: WorkflowData | null): Edge<WorkflowEdgeData>[] {
    if (!workflow || !workflow.nodes) {
        return [];
    }

    const edges: Edge<WorkflowEdgeData>[] = [];
    const useCoreLayout = isCoreNodeWorkflow(workflow);

    // Add core node horizontal connections if using core layout
    if (useCoreLayout) {
        const coreNodeIds = workflow.meta?.coreNodes || [
            CORE_NODE_IDS.PHENOMENON,
            CORE_NODE_IDS.CANDIDATE_SEARCH,
            CORE_NODE_IDS.CAUSE_DERIVATION
        ];

        // Connect core nodes horizontally: phenomenon -> candidate_search -> cause_derivation
        for (let i = 0; i < coreNodeIds.length - 1; i++) {
            const sourceId = coreNodeIds[i];
            const targetId = coreNodeIds[i + 1];

            if (workflow.nodes[sourceId] && workflow.nodes[targetId]) {
                edges.push({
                    id: `core-${sourceId}-${targetId}`,
                    source: sourceId,
                    target: targetId,
                    type: "smoothstep",
                    sourceHandle: "right",
                    targetHandle: "left",
                    animated: false,
                    style: "stroke: #374151; stroke-width: 3px;", // Thicker line for core connections
                    data: { isCoreConnection: true },
                });
            }
        }
    }

    // Normal parent-child edges (for non-core nodes)
    for (const [nodeId, node] of Object.entries(workflow.nodes)) {
        if (node.children) {
            // Skip core node children connections as they go vertically
            const isCoreNode = useCoreLayout && (
                nodeId === CORE_NODE_IDS.PHENOMENON ||
                nodeId === CORE_NODE_IDS.CANDIDATE_SEARCH ||
                nodeId === CORE_NODE_IDS.CAUSE_DERIVATION ||
                workflow.meta?.coreNodes?.includes(nodeId)
            );

            for (const childId of node.children) {
                edges.push({
                    id: `${nodeId}-${childId}`,
                    source: nodeId,
                    target: childId,
                    type: "smoothstep",
                    sourceHandle: isCoreNode ? "bottom" : undefined,
                    targetHandle: isCoreNode ? "top" : undefined,
                    animated: false,
                    style: "stroke: #94a3b8; stroke-width: 2px;",
                });
            }
        }
    }

    // Loopback edges for Selector nodes
    const loopbackEdges = getLoopbackEdges(workflow);
    edges.push(...loopbackEdges);

    return edges;
}

/**
 * Get loopback edges for Selector nodes
 * Loopback: From any descendant Action back to the Selector's parent (or itself if root)
 */
function getLoopbackEdges(workflow: WorkflowData): Edge<WorkflowEdgeData>[] {
    const edges: Edge<WorkflowEdgeData>[] = [];

    // Find all Selector nodes
    for (const [nodeId, node] of Object.entries(workflow.nodes)) {
        if (node.type === "Selector") {
            // Find the parent of this Selector
            const parentId = findParent(workflow, nodeId);

            // Find all Action descendants
            const actionDescendants = findDescendantsByType(workflow, nodeId, "Action");

            for (const actionId of actionDescendants) {
                // Create loopback edge from Action to Selector's parent (or Selector itself)
                const targetId = parentId || nodeId;

                edges.push({
                    id: `loopback-${actionId}-${targetId}`,
                    source: actionId,
                    target: targetId,
                    type: "smoothstep",
                    animated: true,
                    data: { isLoopback: true },
                    style: "stroke: #ef4444; stroke-width: 2px; stroke-dasharray: 5,5;",
                });
            }
        }
    }

    return edges;
}

/**
 * Find the parent node of a given node
 */
function findParent(workflow: WorkflowData, nodeId: string): string | null {
    for (const [id, node] of Object.entries(workflow.nodes)) {
        if (node.children?.includes(nodeId)) {
            return id;
        }
    }
    return null;
}

/**
 * Find all descendants of a specific type
 */
function findDescendantsByType(
    workflow: WorkflowData,
    nodeId: string,
    targetType: string
): string[] {
    const result: string[] = [];
    const node = workflow.nodes[nodeId];

    if (!node) return result;

    if (node.type === targetType) {
        result.push(nodeId);
    }

    if (node.children) {
        for (const childId of node.children) {
            result.push(...findDescendantsByType(workflow, childId, targetType));
        }
    }

    return result;
}

/**
 * Check if a node is a descendant of another
 */
export function isDescendant(
    workflow: WorkflowData,
    ancestorId: string,
    nodeId: string
): boolean {
    const ancestor = workflow.nodes?.[ancestorId];
    if (!ancestor?.children) return false;

    for (const childId of ancestor.children) {
        if (childId === nodeId || isDescendant(workflow, childId, nodeId)) {
            return true;
        }
    }
    return false;
}

/**
 * Generate a unique node ID
 */
export function generateNodeId(): string {
    return `node_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Get viewport settings for fitting the view
 */
export function getFitViewOptions(padding: number = 0.1) {
    return {
        padding,
        includeHiddenNodes: false,
        maxZoom: 1,
        minZoom: 0.2,
    };
}
