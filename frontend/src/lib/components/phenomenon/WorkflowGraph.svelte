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
    import type {
        ProjectWorkflowData,
        WorkflowSteps,
        WorkflowStepInstance,
        WorkflowStepRow,
    } from "$lib/types/workflow";

    export let workflowData: ProjectWorkflowData;
    export let workflowSteps: WorkflowSteps;

    let nodes = writable<Node[]>([]);
    let edges = writable<Edge[]>([]);

    // Color palette for steps
    const STEP_COLORS = [
        { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },   // blue
        { bg: '#dcfce7', border: '#22c55e', text: '#166534' },   // green
        { bg: '#f3e8ff', border: '#a855f7', text: '#6b21a8' },   // purple
        { bg: '#ffedd5', border: '#f97316', text: '#c2410c' },   // orange
        { bg: '#fce7f3', border: '#ec4899', text: '#be185d' },   // pink
        { bg: '#ccfbf1', border: '#14b8a6', text: '#0f766e' },   // teal
        { bg: '#fef9c3', border: '#eab308', text: '#a16207' },   // yellow
        { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c' },   // red
    ];

    const NODE_WIDTH = 280;
    const NODE_HEIGHT = 80;
    const NODE_GAP_Y = 100;
    const NODE_GAP_X = 60;
    const PADDING_TOP = 50;
    const PADDING_LEFT = 50;

    // Get step definition by ID
    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find(r => r.id === stepId);
    }

    // Get step display text
    function getStepDisplayText(step: WorkflowStepInstance): string {
        const def = getStepDefinition(step.stepId);
        if (!def) return "(알 수 없는 스텝)";
        const category = def.values["step_category"];
        const purpose = def.values["purpose"];
        if (category && purpose) return `[${category}] ${purpose}`;
        if (category) return `[${category}]`;
        if (purpose) return purpose;
        return def.id;
    }

    // Get step details text
    function getStepDetails(step: WorkflowStepInstance): string {
        const def = getStepDefinition(step.stepId);
        if (!def) return "";
        const system = def.values["system"];
        const target = def.values["access_target"];
        return [system, target].filter(Boolean).join(" → ");
    }

    $: {
        updateGraph(workflowData);
    }

    function updateGraph(data: ProjectWorkflowData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        if (!data || !data.steps || data.steps.length === 0) {
            // Show empty state
            newNodes.push({
                id: "empty",
                type: "default",
                position: { x: PADDING_LEFT, y: PADDING_TOP },
                data: { label: "워크플로우 스텝이 없습니다" },
                style: `
                    background: #f3f4f6;
                    border: 2px dashed #d1d5db;
                    border-radius: 8px;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 14px;
                    width: ${NODE_WIDTH}px;
                `,
                draggable: false,
                selectable: false,
            });
            nodes.set(newNodes);
            edges.set(newEdges);
            return;
        }

        // Create nodes for each step
        data.steps.forEach((step, index) => {
            const color = STEP_COLORS[index % STEP_COLORS.length];
            const x = PADDING_LEFT;
            const y = PADDING_TOP + index * NODE_GAP_Y;

            const displayText = getStepDisplayText(step);
            const details = getStepDetails(step);
            const captureCount = step.captures.length;
            const attachmentCount = step.attachments.length;

            // Build label with metadata
            let metaText = "";
            if (captureCount > 0 || attachmentCount > 0) {
                const parts = [];
                if (captureCount > 0) parts.push(`📷 ${captureCount}`);
                if (attachmentCount > 0) parts.push(`📎 ${attachmentCount}`);
                metaText = parts.join(" | ");
            }

            newNodes.push({
                id: step.id,
                type: "default",
                position: { x, y },
                data: {
                    label: displayText,
                },
                style: `
                    background: ${color.bg};
                    border: 2px solid ${color.border};
                    border-radius: 10px;
                    padding: 12px 16px;
                    width: ${NODE_WIDTH}px;
                    min-height: ${NODE_HEIGHT}px;
                    font-size: 13px;
                    font-weight: 500;
                    color: ${color.text};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                `,
                sourcePosition: Position.Bottom,
                targetPosition: Position.Top,
            });

            // Create edge to next step
            if (index < data.steps.length - 1) {
                const nextStep = data.steps[index + 1];
                newEdges.push({
                    id: `e-${step.id}-${nextStep.id}`,
                    source: step.id,
                    target: nextStep.id,
                    type: "smoothstep",
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        color: "#94a3b8",
                    },
                    style: "stroke: #94a3b8; stroke-width: 2px;",
                });
            }
        });

        nodes.set(newNodes);
        edges.set(newEdges);
    }
</script>

<div class="workflow-graph-container">
    <SvelteFlow
        nodes={$nodes}
        edges={$edges}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={2}
    >
        <Background gap={20} size={1} color="#e2e8f0" />
        <Controls position="bottom-left" showLock={false} />
    </SvelteFlow>
</div>

<style>
    .workflow-graph-container {
        width: 100%;
        height: 100%;
        min-height: 400px;
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

    :global(.workflow-graph-container .svelte-flow__node) {
        cursor: default;
    }
</style>
