<script lang="ts">
    import { writable } from "svelte/store";
    import {
        SvelteFlow,
        Background,
        Controls,
        Position,
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
    import TimelineNode from "./TimelineNode.svelte";

    export let workflowData: ProjectWorkflowData;
    export let workflowSteps: WorkflowSteps;
    export let onNodeClick: ((stepId: string) => void) | undefined = undefined;

    let nodes = writable<Node[]>([]);
    let edges = writable<Edge[]>([]);

    // Custom node types
    const nodeTypes = {
        timeline: TimelineNode,
    };

    // Layout constants
    const TIMELINE_X = 200;  // Center x position of timeline
    const NODE_WIDTH = 260;
    const NODE_GAP_Y = 140;
    const PADDING_TOP = 80;
    const TIMELINE_DOT_SIZE = 16;

    // Color palette for steps
    const STEP_COLORS = [
        { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af', line: '#3b82f6' },   // blue
        { bg: '#dcfce7', border: '#22c55e', text: '#166534', line: '#22c55e' },   // green
        { bg: '#f3e8ff', border: '#a855f7', text: '#6b21a8', line: '#a855f7' },   // purple
        { bg: '#ffedd5', border: '#f97316', text: '#c2410c', line: '#f97316' },   // orange
        { bg: '#fce7f3', border: '#ec4899', text: '#be185d', line: '#ec4899' },   // pink
        { bg: '#ccfbf1', border: '#14b8a6', text: '#0f766e', line: '#14b8a6' },   // teal
        { bg: '#fef9c3', border: '#eab308', text: '#a16207', line: '#eab308' },   // yellow
        { bg: '#fee2e2', border: '#ef4444', text: '#b91c1c', line: '#ef4444' },   // red
    ];

    // Get step definition by ID
    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find(r => r.id === stepId);
    }

    // Get step display info
    function getStepInfo(step: WorkflowStepInstance) {
        const def = getStepDefinition(step.stepId);
        if (!def) return { category: 'Unknown', purpose: '알 수 없는 스텝', system: '', target: '' };

        return {
            category: def.values["step_category"] || 'ETC',
            purpose: def.values["purpose"] || '목적 없음',
            system: def.values["system"] || '',
            target: def.values["access_target"] || '',
            expectedResult: def.values["expected_result"] || '',
        };
    }

    $: {
        updateGraph(workflowData);
    }

    function updateGraph(data: ProjectWorkflowData) {
        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        if (!data || !data.steps || data.steps.length === 0) {
            // Empty state
            newNodes.push({
                id: "empty",
                type: "default",
                position: { x: TIMELINE_X - 100, y: PADDING_TOP },
                data: { label: "워크플로우 스텝이 없습니다" },
                style: `
                    background: #f3f4f6;
                    border: 2px dashed #d1d5db;
                    border-radius: 8px;
                    padding: 20px;
                    color: #6b7280;
                    font-size: 14px;
                    width: 200px;
                    text-align: center;
                `,
                draggable: false,
                selectable: false,
            });
            nodes.set(newNodes);
            edges.set(newEdges);
            return;
        }

        // Create timeline backbone nodes (invisible anchor points)
        const timelineStartY = PADDING_TOP;
        const timelineEndY = PADDING_TOP + (data.steps.length - 1) * NODE_GAP_Y + 60;

        // Timeline start marker
        newNodes.push({
            id: "timeline-start",
            type: "default",
            position: { x: TIMELINE_X - 8, y: timelineStartY - 30 },
            data: { label: "▼" },
            style: `
                background: transparent;
                border: none;
                font-size: 16px;
                color: #374151;
                width: 16px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            `,
            draggable: false,
            selectable: false,
        });

        // Create step nodes alternating left and right
        data.steps.forEach((step, index) => {
            const color = STEP_COLORS[index % STEP_COLORS.length];
            const isLeft = index % 2 === 0;
            const y = PADDING_TOP + index * NODE_GAP_Y;
            const x = isLeft
                ? TIMELINE_X - NODE_WIDTH - 50  // Left side
                : TIMELINE_X + 50;               // Right side

            const info = getStepInfo(step);
            const captureCount = step.captures.length;
            const attachmentCount = step.attachments.length;

            // Timeline dot (anchor point on timeline)
            const dotId = `dot-${step.id}`;
            newNodes.push({
                id: dotId,
                type: "default",
                position: { x: TIMELINE_X - TIMELINE_DOT_SIZE / 2, y: y + 30 },
                data: { label: String(index + 1) },
                style: `
                    background: ${color.border};
                    border: 3px solid white;
                    border-radius: 50%;
                    width: ${TIMELINE_DOT_SIZE}px;
                    height: ${TIMELINE_DOT_SIZE}px;
                    font-size: 9px;
                    font-weight: 700;
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    z-index: 10;
                `,
                draggable: false,
                selectable: false,
            });

            // Step node
            newNodes.push({
                id: step.id,
                type: "timeline",
                position: { x, y },
                data: {
                    stepIndex: index,
                    category: info.category,
                    purpose: info.purpose,
                    system: info.system,
                    target: info.target,
                    expectedResult: info.expectedResult,
                    captureCount,
                    attachmentCount,
                    color,
                    isLeft,
                },
                sourcePosition: isLeft ? Position.Right : Position.Left,
                targetPosition: isLeft ? Position.Right : Position.Left,
                draggable: false,
            });

            // Edge from dot to step node
            newEdges.push({
                id: `e-dot-${step.id}`,
                source: dotId,
                target: step.id,
                type: "straight",
                sourceHandle: null,
                targetHandle: null,
                style: `stroke: ${color.border}; stroke-width: 2px;`,
            });

            // Connect dots vertically (timeline backbone)
            if (index > 0) {
                const prevDotId = `dot-${data.steps[index - 1].id}`;
                newEdges.push({
                    id: `e-timeline-${index}`,
                    source: prevDotId,
                    target: dotId,
                    type: "straight",
                    style: `stroke: #374151; stroke-width: 4px;`,
                });
            } else {
                // Connect start marker to first dot
                newEdges.push({
                    id: `e-timeline-start`,
                    source: "timeline-start",
                    target: dotId,
                    type: "straight",
                    style: `stroke: #374151; stroke-width: 4px;`,
                });
            }
        });

        // Timeline end marker
        const lastDotId = `dot-${data.steps[data.steps.length - 1].id}`;
        newNodes.push({
            id: "timeline-end",
            type: "default",
            position: { x: TIMELINE_X - 8, y: timelineEndY + 30 },
            data: { label: "●" },
            style: `
                background: transparent;
                border: none;
                font-size: 16px;
                color: #374151;
                width: 16px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            `,
            draggable: false,
            selectable: false,
        });

        // Connect last dot to end marker
        newEdges.push({
            id: `e-timeline-end`,
            source: lastDotId,
            target: "timeline-end",
            type: "straight",
            style: `stroke: #374151; stroke-width: 4px;`,
        });

        nodes.set(newNodes);
        edges.set(newEdges);
    }

    function handleNodeClick({ node }: { node: Node; event: MouseEvent | TouchEvent }) {
        if (node && node.type === 'timeline' && onNodeClick) {
            onNodeClick(node.id);
        }
    }
</script>

<div class="timeline-graph-container">
    <SvelteFlow
        nodes={$nodes}
        edges={$edges}
        {nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={2}
        onnodeclick={handleNodeClick}
    >
        <Background gap={20} size={1} bgColor="#f8fafc" />
        <Controls position="bottom-left" showLock={false} />
    </SvelteFlow>
</div>

<style>
    .timeline-graph-container {
        width: 100%;
        height: 100%;
        min-height: 400px;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        position: relative;
    }

    :global(.timeline-graph-container .svelte-flow__controls) {
        margin: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-radius: 6px;
        overflow: hidden;
        background: white;
    }

    :global(.timeline-graph-container .svelte-flow__controls button) {
        width: 28px;
        height: 28px;
        border: none;
        border-bottom: 1px solid #eee;
    }

    :global(.timeline-graph-container .svelte-flow__node) {
        cursor: default;
    }

    :global(.timeline-graph-container .svelte-flow__edge-path) {
        stroke-linecap: round;
    }
</style>
