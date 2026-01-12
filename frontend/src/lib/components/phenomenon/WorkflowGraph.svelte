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
    import EvidenceNode from "./nodes/EvidenceNode.svelte";
    import CandidateCauseNode from "./nodes/CandidateCauseNode.svelte";

    export let phenomenon: PhenomenonData;

    let nodes = writable<Node[]>([]);
    let edges = writable<Edge[]>([]);

    const nodeTypes = {
        evidence: EvidenceNode,
        candidateCause: CandidateCauseNode,
    };

    const GROUP_PADDING = 20;
    const HEADER_HEIGHT = 40;
    const GAP_Y = 140;
    const EVIDENCE_GROUP_WIDTH = 280;
    const CAUSE_GROUP_WIDTH = 320;

    $: {
        updateGraph(phenomenon);
    }

    function updateGraph(data: PhenomenonData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        const evidenceCount = data.evidences?.length || 0;
        const causeCount = data.candidateCauses?.length || 0;
        const maxItems = Math.max(evidenceCount, causeCount, 3);

        const groupHeight =
            maxItems * GAP_Y + HEADER_HEIGHT + GROUP_PADDING * 2;

        newNodes.push({
            id: "group-evidence",
            type: "group",
            data: { label: "발생현상" },
            position: { x: 50, y: 50 },
            style: `width: ${EVIDENCE_GROUP_WIDTH}px; height: ${groupHeight}px; background-color: rgba(240, 240, 245, 0.5); border: 2px dashed #cbd5e1; border-radius: 12px;`,
            draggable: false,
        });

        newNodes.push({
            id: "group-causes",
            type: "group",
            data: { label: "원인후보" },
            position: { x: 400, y: 50 },
            style: `width: ${CAUSE_GROUP_WIDTH}px; height: ${groupHeight}px; background-color: rgba(239, 246, 255, 0.5); border: 2px dashed #bfdbfe; border-radius: 12px;`,
            draggable: false,
        });

        newNodes.push({
            id: "header-evidence",
            type: "default",
            parentId: "group-evidence",
            extent: "parent",
            data: { label: "발생현상" },
            position: { x: GROUP_PADDING, y: GROUP_PADDING },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "width: 100px; font-weight: 700; font-size: 14px; color: #374151; background: transparent; border: none; text-align: left; padding: 0;",
        });

        newNodes.push({
            id: "header-causes",
            type: "default",
            parentId: "group-causes",
            extent: "parent",
            data: { label: "원인후보" },
            position: { x: GROUP_PADDING, y: GROUP_PADDING },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "width: 100px; font-weight: 700; font-size: 14px; color: #1e40af; background: transparent; border: none; text-align: left; padding: 0;",
        });

        if (data.evidences) {
            data.evidences.forEach((evidence, index) => {
                const color = EVIDENCE_COLORS[index % EVIDENCE_COLORS.length];
                let label = "";
                if (evidence.type === "capture") {
                    label =
                        evidence.label || `캡처 #${evidence.slideIndex + 1}`;
                } else {
                    label = evidence.name || evidence.key;
                }

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
                    },
                    position: {
                        x: GROUP_PADDING,
                        y: HEADER_HEIGHT + GROUP_PADDING + index * GAP_Y,
                    },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });
            });
        }

        if (data.candidateCauses) {
            data.candidateCauses.forEach((cause, index) => {
                newNodes.push({
                    id: cause.id,
                    type: "candidateCause",
                    parentId: "group-causes",
                    extent: "parent",
                    data: {
                        label: cause.text,
                        todoList: cause.todoList || [],
                        linkedEvidenceCount:
                            cause.evidenceLinks?.length || 0,
                    },
                    position: {
                        x: GROUP_PADDING,
                        y: HEADER_HEIGHT + GROUP_PADDING + index * GAP_Y,
                    },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });

                if (cause.evidenceLinks) {
                    cause.evidenceLinks.forEach((link) => {
                        newEdges.push({
                            id: `e-${link.evidenceId}-${cause.id}`,
                            source: link.evidenceId,
                            target: cause.id,
                            markerEnd: {
                                type: MarkerType.ArrowClosed,
                                color: "#9ca3af",
                            },
                            style: "stroke: #9ca3af; stroke-width: 1.5px;",
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
        <Background gap={20} size={1} />
        <Controls position="bottom-left" showLock={false} />
    </SvelteFlow>
</div>

<style>
    .workflow-graph-container {
        width: 100%;
        height: 100%;
        min-height: 400px;
        background: #f9fafb;
        position: relative;
    }

    :global(.workflow-graph-container .svelte-flow__controls) {
        margin: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-radius: 6px;
        overflow: hidden;
    }

    :global(.workflow-graph-container .svelte-flow__controls button) {
        width: 26px;
        height: 26px;
        border: none;
    }
</style>
