// Adapter utilities to convert WorkflowData to SvelteFlow nodes/edges

import type { Node, Edge } from "@xyflow/svelte";
import type { WorkflowData, WorkflowNode } from "$lib/api/project";
import { calculateTreeLayout, type LayoutNode } from "./layoutTree";
import { NODE_TYPE_COLORS, NODE_WIDTH } from "./constants";

// Custom node data type
export interface WorkflowNodeData extends Record<string, unknown> {
    nodeId: string;
    workflowNode: WorkflowNode;
    label: string;
    isRoot?: boolean;
}

// Custom edge data type
export interface WorkflowEdgeData extends Record<string, unknown> {
    isLoopback?: boolean;
}

/**
 * Convert WorkflowData to SvelteFlow nodes array
 */
export function workflowToNodes(workflow: WorkflowData | null): Node<WorkflowNodeData>[] {
    if (!workflow || !workflow.rootId || !workflow.nodes) {
        return [];
    }

    const { allNodes } = calculateTreeLayout(workflow);

    return allNodes.map((layoutNode) => {
        const nodeType = layoutNode.node.type;

        return {
            id: layoutNode.id,
            type: nodeType, // Will map to custom node components
            position: { x: layoutNode.x, y: layoutNode.y },
            data: {
                nodeId: layoutNode.id,
                workflowNode: layoutNode.node,
                label: layoutNode.node.name || nodeType,
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

    // Normal parent-child edges
    for (const [nodeId, node] of Object.entries(workflow.nodes)) {
        if (node.children) {
            for (const childId of node.children) {
                edges.push({
                    id: `${nodeId}-${childId}`,
                    source: nodeId,
                    target: childId,
                    type: "smoothstep",
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
