<script lang="ts">
    import { writable } from "svelte/store";
    import {
        SvelteFlow,
        Background,
        Controls,
        useSvelteFlow,
        Position,
        MarkerType,
        type Node,
        type Edge,
    } from "@xyflow/svelte";
    import "@xyflow/svelte/dist/style.css";
    import type {
        PhenomenonData,
        Evidence,
        CandidateCause,
    } from "$lib/types/phenomenon";

    export let phenomenon: PhenomenonData;

    let nodes = writable<Node[]>([]);
    let edges = writable<Edge[]>([]);

    const EVIDENCE_X = 50;
    const CAUSE_X = 400;
    const NODE_WIDTH = 250;
    const GAP_Y = 100;

    $: {
        updateGraph(phenomenon);
    }

    function updateGraph(data: PhenomenonData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        // 1. Evidence Nodes (Level 1)
        if (data.evidences) {
            data.evidences.forEach((evidence, index) => {
                let label = "";
                if (evidence.type === "capture") {
                    label =
                        evidence.label || `Capture #${evidence.slideIndex + 1}`;
                } else {
                    label = evidence.name || evidence.key;
                }

                newNodes.push({
                    id: evidence.id,
                    type: "default",
                    data: { label: label },
                    position: { x: EVIDENCE_X, y: 50 + index * GAP_Y },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                    style: "width: 250px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; background: white; font-size: 12px;",
                });
            });
        }

        // 2. Candidate Cause Nodes (Level 2)
        if (data.candidateCauses) {
            data.candidateCauses.forEach((cause, index) => {
                newNodes.push({
                    id: cause.id,
                    type: "default",
                    data: { label: cause.text },
                    position: { x: CAUSE_X, y: 50 + index * GAP_Y },
                    sourcePosition: Position.Right,
                    targetPosition: Position.Left,
                    style: "width: 250px; border: 1px solid #3b82f6; border-radius: 8px; padding: 10px; background: #eff6ff; font-size: 12px;",
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
                            style: "stroke: #9ca3af;",
                        });
                    });
                }
            });
        }

        nodes.set(newNodes);
        edges.set(newEdges);
    }
</script>

<div class="w-full h-full min-h-[500px] bg-gray-50">
    <SvelteFlow
        nodes={$nodes}
        edges={$edges}
        fitView
        attributionPosition="bottom-right"
    >
        <Background gap={20} size={1} />
        <Controls />
    </SvelteFlow>
</div>
