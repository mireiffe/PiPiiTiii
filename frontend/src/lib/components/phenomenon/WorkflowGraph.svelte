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

    const EVIDENCE_X = 50;
    const CAUSE_X = 350;
    const HEADER_Y = 10;
    const NODE_START_Y = 50;
    const GAP_Y = 120;

    $: {
        updateGraph(phenomenon);
    }

    function updateGraph(data: PhenomenonData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        // Section Headers
        newNodes.push({
            id: "header-evidence",
            type: "default",
            data: { label: "발생현상" },
            position: { x: EVIDENCE_X, y: HEADER_Y },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "font-weight: 600; font-size: 13px; color: #374151; background: transparent; border: none; padding: 4px 8px;",
        });

        newNodes.push({
            id: "header-causes",
            type: "default",
            data: { label: "원인후보" },
            position: { x: CAUSE_X, y: HEADER_Y },
            draggable: false,
            selectable: false,
            connectable: false,
            style: "font-weight: 600; font-size: 13px; color: #1e40af; background: transparent; border: none; padding: 4px 8px;",
        });

        // 1. Evidence Nodes
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
                    position: { x: EVIDENCE_X, y: NODE_START_Y + index * GAP_Y },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });
            });
        }

        // 2. Candidate Cause Nodes
        if (data.candidateCauses) {
            data.candidateCauses.forEach((cause, index) => {
                newNodes.push({
                    id: cause.id,
                    type: "candidateCause",
                    data: {
                        label: cause.text,
                        todoList: cause.todoList || [],
                        linkedEvidenceCount: cause.evidenceLinks?.length || 0,
                    },
                    position: { x: CAUSE_X, y: NODE_START_Y + index * GAP_Y },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                });

                // Edges
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
