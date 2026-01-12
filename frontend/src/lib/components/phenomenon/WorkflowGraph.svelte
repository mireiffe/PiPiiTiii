<script lang="ts">
    import { writable } from "svelte/store";
    import {
        SvelteFlow,
        Background,
        Controls,
        Position,
        MarkerType,
        type Node,
        type Edge,
    } from "@xyflow/svelte";
    import "@xyflow/svelte/dist/style.css";
    import type { PhenomenonData } from "$lib/types/phenomenon";
    import { EVIDENCE_COLORS } from "$lib/types/phenomenon";
    import type { WorkflowAction, WorkflowCondition } from "$lib/types/workflow";
    import EvidenceNode from "./nodes/EvidenceNode.svelte";
    import CandidateCauseNode from "./nodes/CandidateCauseNode.svelte";

    export let phenomenon: PhenomenonData;
    export let workflowActions: WorkflowAction[] = [];
    export let workflowConditions: WorkflowCondition[] = [];

    let nodes = writable<Node[]>([]);
    let edges = writable<Edge[]>([]);

    const nodeTypes = {
        evidence: EvidenceNode,
        candidateCause: CandidateCauseNode,
    };

    const GROUP_PADDING_TOP = 60;
    const GROUP_PADDING_BOTTOM = 40;
    const GROUP_PADDING_X = 20;
    // Different gap for different node types
    const CAPTURE_NODE_GAP = 55;                // Capture nodes without description
    const CAPTURE_NODE_WITH_DESC_GAP = 95;      // Capture nodes with description (2 lines)
    const ATTR_NODE_GAP = 36;                   // Attribute nodes are compact (~28px)
    const CAUSE_NODE_BASE_HEIGHT = 90;   // Base height for cause node
    const CAUSE_NODE_TODO_HEIGHT = 50;   // Additional height per todo item (with params)
    const CAUSE_NODE_GAP = 16;           // Gap between cause nodes
    const EVIDENCE_GROUP_WIDTH = 300;
    const CAUSE_GROUP_WIDTH = 340;

    $: {
        updateGraph(phenomenon);
    }

    // Calculate height for a cause node based on todoList
    function calcCauseNodeHeight(todoList: any[]): number {
        const visibleTodos = Math.min(todoList?.length || 0, 3);
        return CAUSE_NODE_BASE_HEIGHT + visibleTodos * CAUSE_NODE_TODO_HEIGHT;
    }

    function updateGraph(data: PhenomenonData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        // Calculate evidence nodes total height
        let evidenceTotalHeight = 0;
        if (data.evidences) {
            data.evidences.forEach((ev) => {
                if (ev.type === "capture") {
                    evidenceTotalHeight += ev.description ? CAPTURE_NODE_WITH_DESC_GAP : CAPTURE_NODE_GAP;
                } else {
                    evidenceTotalHeight += ATTR_NODE_GAP;
                }
            });
        }
        evidenceTotalHeight = Math.max(evidenceTotalHeight, 100);

        // Calculate cause nodes total height dynamically
        let causeTotalHeight = 0;
        if (data.candidateCauses) {
            data.candidateCauses.forEach((cause) => {
                causeTotalHeight += calcCauseNodeHeight(cause.todoList || []) + CAUSE_NODE_GAP;
            });
        }
        causeTotalHeight = Math.max(causeTotalHeight, 100);

        const maxContentHeight = Math.max(evidenceTotalHeight, causeTotalHeight);
        const groupHeight = maxContentHeight + GROUP_PADDING_TOP + GROUP_PADDING_BOTTOM;

        newNodes.push({
            id: "group-evidence",
            type: "group",
            data: { label: "발생현상" },
            position: { x: 50, y: 50 },
            style: `
                width: ${EVIDENCE_GROUP_WIDTH}px;
                height: ${groupHeight}px;
                background: rgba(254, 226, 226, 0.7) !important;
                border: 3px solid #f87171;
                border-radius: 12px;
                box-shadow: 0 4px 12px -2px rgba(239, 68, 68, 0.25);
            `,
            draggable: false,
        });

        newNodes.push({
            id: "group-causes",
            type: "group",
            data: { label: "원인후보" },
            position: { x: 450, y: 50 },
            style: `
                width: ${CAUSE_GROUP_WIDTH}px;
                height: ${groupHeight}px;
                background: rgba(219, 234, 254, 0.7) !important;
                border: 3px solid #60a5fa;
                border-radius: 12px;
                box-shadow: 0 4px 12px -2px rgba(59, 130, 246, 0.25);
            `,
            draggable: false,
        });

        newNodes.push({
            id: "header-evidence",
            type: "default",
            parentId: "group-evidence",
            extent: "parent",
            data: { label: "발생현상" },
            position: { x: 20, y: 20 },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "width: auto; font-weight: 700; font-size: 16px; color: #dc2626; background: transparent; border: none; text-align: left; padding: 0;",
        });

        newNodes.push({
            id: "header-causes",
            type: "default",
            parentId: "group-causes",
            extent: "parent",
            data: { label: "원인후보" },
            position: { x: 20, y: 20 },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "width: auto; font-weight: 700; font-size: 16px; color: #2563eb; background: transparent; border: none; text-align: left; padding: 0;",
        });

        if (data.evidences) {
            let evidenceYOffset = GROUP_PADDING_TOP;
            data.evidences.forEach((evidence, index) => {
                const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length];
                let label =
                    evidence.type === "capture"
                        ? evidence.label || `캡처 #${evidence.slideIndex + 1}`
                        : evidence.name || evidence.key;

                newNodes.push({
                    id: evidence.id,
                    type: "evidence",
                    parentId: "group-evidence",
                    extent: "parent",
                    data: {
                        label,
                        index,
                        color,
                        evidenceType: evidence.type,
                        slideIndex:
                            evidence.type === "capture"
                                ? evidence.slideIndex
                                : undefined,
                        attributeValue:
                            evidence.type === "attribute"
                                ? evidence.value
                                : undefined,
                        description:
                            evidence.type === "capture"
                                ? evidence.description
                                : undefined,
                    },
                    position: {
                        x: GROUP_PADDING_X,
                        y: evidenceYOffset,
                    },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });

                // Use different gap based on node type and whether it has description
                if (evidence.type === "capture") {
                    evidenceYOffset += evidence.description ? CAPTURE_NODE_WITH_DESC_GAP : CAPTURE_NODE_GAP;
                } else {
                    evidenceYOffset += ATTR_NODE_GAP;
                }
            });
        }

        if (data.candidateCauses) {
            let causeYOffset = GROUP_PADDING_TOP;
            data.candidateCauses.forEach((cause) => {
                const todoList = cause.todoList || [];
                const nodeHeight = calcCauseNodeHeight(todoList);

                newNodes.push({
                    id: cause.id,
                    type: "candidateCause",
                    parentId: "group-causes",
                    extent: "parent",
                    data: {
                        label: cause.text,
                        todoList,
                        linkedEvidenceCount:
                            cause.evidenceLinks?.length || 0,
                        workflowActions,
                        workflowConditions,
                    },
                    position: {
                        x: GROUP_PADDING_X,
                        y: causeYOffset,
                    },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });

                // Move to next position based on actual node height
                causeYOffset += nodeHeight + CAUSE_NODE_GAP;

                if (cause.evidenceLinks) {
                    cause.evidenceLinks.forEach((link) => {
                        newEdges.push({
                            id: `e-${link.evidenceId}-${cause.id}`,
                            source: link.evidenceId,
                            target: cause.id,
                            markerEnd: {
                                type: MarkerType.ArrowClosed,
                                color: "#94a3b8",
                            },
                            style: "stroke: #94a3b8; stroke-width: 2px;",
                        });
                    });
                }
            });
        }

        nodes.set(newNodes);
        edges.set(newEdges);
    }
</script>

<div class="workflow-graph-container">
    <SvelteFlow
        nodes={$nodes}
        edges={$edges}
        {nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
    >
        <Background gap={20} size={1} color="#e2e8f0" />
        <Controls position="bottom-left" showLock={false} />
    </SvelteFlow>
</div>

<style>
    .workflow-graph-container {
        width: 100%;
        height: 100%;
        min-height: 500px;
        background: #ffffff;
        position: relative;
    }

    :global(.workflow-graph-container .svelte-flow__controls) {
        margin: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-radius: 6px;
        overflow: hidden;
        background: white;
    }

    :global(.workflow-graph-container .svelte-flow__controls button) {
        width: 28px;
        height: 28px;
        border: none;
        border-bottom: 1px solid #eee;
    }
</style>
