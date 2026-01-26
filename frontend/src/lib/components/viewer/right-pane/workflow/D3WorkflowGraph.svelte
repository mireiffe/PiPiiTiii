<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import * as d3 from "d3";
    import type {
        ProjectWorkflowData,
        WorkflowSteps,
        WorkflowStepInstance,
        WorkflowStepRow,
        PhaseType,
        LayoutRow,
    } from "$lib/types/workflow";
    import {
        getLayoutRows,
    } from "$lib/types/workflow";

    export let workflowData: ProjectWorkflowData;
    export let workflowSteps: WorkflowSteps;
    export let globalPhases: PhaseType[] = [];
    export let unifiedDisplayMap: Map<string, number> = new Map();
    export let onNodeClick: ((stepId: string) => void) | undefined = undefined;

    let svgContainer: HTMLDivElement;
    let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    let mainGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    let zoom: d3.ZoomBehavior<SVGSVGElement, unknown>;

    // State
    let hoveredStepId: string | null = null;
    let selectedNodeId: string | null = null;
    let width = 0;
    let height = 0;
    let currentNodes: NodeLayout[] = [];

    // Layout constants - Horizontal flow (left to right)
    const NODE_WIDTH = 200;
    const NODE_HEIGHT = 90;
    const NODE_GAP_X = 60;  // Gap between main flow nodes
    const SUPPORT_GAP_Y = 100;  // Vertical gap for support nodes
    const MARGIN = { top: 80, right: 80, bottom: 80, left: 40 };
    const VISIBLE_NODES = 4;  // Number of nodes visible in initial view

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

    // Truncate text with ellipsis
    function truncate(text: string, maxLen: number): string {
        return text.length > maxLen ? text.substring(0, maxLen - 1) + '…' : text;
    }

    interface NodeLayout {
        id: string;
        step: WorkflowStepInstance;
        info: ReturnType<typeof getStepInfo>;
        x: number;
        y: number;
        width: number;
        height: number;
        color: typeof STEP_COLORS[0];
        stepIndex: number;
        isSupporter: boolean;
        phaseColor?: string;
        phaseName?: string;
        targetStepId?: string;
    }

    interface EdgeLayout {
        id: string;
        source: NodeLayout;
        target: NodeLayout;
        type: 'flow' | 'support';
        color: string;
        phaseColor?: string;
    }

    function calculateLayout(): { nodes: NodeLayout[], edges: EdgeLayout[], totalWidth: number, totalHeight: number } {
        const nodes: NodeLayout[] = [];
        const edges: EdgeLayout[] = [];

        const layoutRows = getLayoutRows(
            workflowData.steps,
            workflowData.supportRelations,
            globalPhases
        );

        if (layoutRows.length === 0) {
            return { nodes, edges, totalWidth: 400, totalHeight: 300 };
        }

        // Calculate main flow Y position (center)
        const mainFlowY = MARGIN.top + SUPPORT_GAP_Y;
        let currentX = MARGIN.left;

        // Track support positions per main step (above/below alternating)
        let supportAbove = true;

        layoutRows.forEach((row, rowIndex) => {
            const mainStep = row.mainStep;
            const color = STEP_COLORS[rowIndex % STEP_COLORS.length];

            // Main step node
            const mainNode: NodeLayout = {
                id: mainStep.id,
                step: mainStep,
                info: getStepInfo(mainStep),
                x: currentX,
                y: mainFlowY,
                width: NODE_WIDTH,
                height: NODE_HEIGHT,
                color,
                stepIndex: (unifiedDisplayMap.get(mainStep.id) ?? rowIndex + 1) - 1,
                isSupporter: false,
            };
            nodes.push(mainNode);

            // Support nodes for this main step
            if (row.supporters.length > 0) {
                row.supporters.forEach((supporter, supIndex) => {
                    const supStep = supporter.step;
                    const phase = supporter.phase;
                    const phaseColor = phase?.color || '#a855f7';

                    // Alternate supporters above and below
                    // If multiple supporters, spread them around the main node
                    let supY: number;
                    if (row.supporters.length === 1) {
                        supY = supportAbove ? mainFlowY - SUPPORT_GAP_Y : mainFlowY + SUPPORT_GAP_Y;
                    } else {
                        // Distribute above and below
                        const isAbove = supIndex % 2 === 0;
                        supY = isAbove ? mainFlowY - SUPPORT_GAP_Y : mainFlowY + SUPPORT_GAP_Y;
                    }

                    // Offset X slightly for visual separation
                    const supX = currentX + (supIndex * 30) - ((row.supporters.length - 1) * 15);

                    const supportNode: NodeLayout = {
                        id: supStep.id,
                        step: supStep,
                        info: getStepInfo(supStep),
                        x: supX,
                        y: supY,
                        width: NODE_WIDTH - 20,
                        height: NODE_HEIGHT - 10,
                        color: {
                            bg: '#f3e8ff',
                            border: phaseColor,
                            text: '#6b21a8',
                            line: phaseColor
                        },
                        stepIndex: -1,
                        isSupporter: true,
                        phaseColor,
                        phaseName: phase?.name || '위상',
                        targetStepId: mainStep.id,
                    };
                    nodes.push(supportNode);

                    // Edge from support to main
                    edges.push({
                        id: `support-${supStep.id}-${mainStep.id}`,
                        source: supportNode,
                        target: mainNode,
                        type: 'support',
                        color: phaseColor,
                        phaseColor,
                    });
                });

                // Alternate for next main step
                supportAbove = !supportAbove;
            }

            // Move to next position
            currentX += NODE_WIDTH + NODE_GAP_X;
        });

        // Add flow edges between consecutive main steps
        const mainNodes = nodes.filter(n => !n.isSupporter);
        for (let i = 0; i < mainNodes.length - 1; i++) {
            edges.push({
                id: `flow-${mainNodes[i].id}-${mainNodes[i + 1].id}`,
                source: mainNodes[i],
                target: mainNodes[i + 1],
                type: 'flow',
                color: '#374151',
            });
        }

        const totalWidth = currentX + MARGIN.right;
        const totalHeight = mainFlowY + SUPPORT_GAP_Y + NODE_HEIGHT + MARGIN.bottom;

        return { nodes, edges, totalWidth, totalHeight };
    }

    function render() {
        if (!svg || !mainGroup) return;

        const { nodes, edges, totalWidth, totalHeight } = calculateLayout();
        currentNodes = nodes;

        // Clear previous content
        mainGroup.selectAll('*').remove();

        if (nodes.length === 0) {
            // Empty state
            mainGroup.append('text')
                .attr('x', 200)
                .attr('y', 150)
                .attr('text-anchor', 'middle')
                .attr('font-size', '14px')
                .attr('fill', '#9ca3af')
                .text('워크플로우 스텝이 없습니다');
            return;
        }

        // Defs for gradients, filters, markers
        const defs = mainGroup.append('defs');

        // Drop shadow filter
        const dropShadow = defs.append('filter')
            .attr('id', 'drop-shadow')
            .attr('x', '-30%')
            .attr('y', '-30%')
            .attr('width', '160%')
            .attr('height', '160%');
        dropShadow.append('feDropShadow')
            .attr('dx', '0')
            .attr('dy', '3')
            .attr('stdDeviation', '4')
            .attr('flood-opacity', '0.1');

        // Hover glow filter
        const hoverGlow = defs.append('filter')
            .attr('id', 'hover-glow')
            .attr('x', '-30%')
            .attr('y', '-30%')
            .attr('width', '160%')
            .attr('height', '160%');
        hoverGlow.append('feDropShadow')
            .attr('dx', '0')
            .attr('dy', '2')
            .attr('stdDeviation', '6')
            .attr('flood-color', 'rgba(59, 130, 246, 0.4)')
            .attr('flood-opacity', '0.6');

        // Animated dash style for support edges
        defs.append('style').text(`
            @keyframes dashFlow {
                from { stroke-dashoffset: 20; }
                to { stroke-dashoffset: 0; }
            }
            .support-edge {
                animation: dashFlow 1s linear infinite;
            }
        `);

        // Arrow markers for flow edges
        defs.append('marker')
            .attr('id', 'flow-arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#374151');

        // Draw flow edges first (behind nodes)
        const flowEdges = edges.filter(e => e.type === 'flow');
        mainGroup.selectAll('.flow-edge')
            .data(flowEdges)
            .enter()
            .append('path')
            .attr('class', 'flow-edge')
            .attr('d', d => {
                const x1 = d.source.x + d.source.width;
                const y1 = d.source.y + d.source.height / 2;
                const x2 = d.target.x;
                const y2 = d.target.y + d.target.height / 2;
                return `M${x1},${y1} L${x2},${y2}`;
            })
            .attr('fill', 'none')
            .attr('stroke', '#94a3b8')
            .attr('stroke-width', 3)
            .attr('stroke-linecap', 'round')
            .attr('marker-end', 'url(#flow-arrow)');

        // Draw support edges
        const supportEdges = edges.filter(e => e.type === 'support');
        supportEdges.forEach((edge, i) => {
            // Create unique marker for this edge's color
            const markerId = `support-arrow-${i}`;
            defs.append('marker')
                .attr('id', markerId)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 8)
                .attr('refY', 0)
                .attr('markerWidth', 5)
                .attr('markerHeight', 5)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', edge.phaseColor || '#a855f7');

            const isAbove = edge.source.y < edge.target.y;
            const x1 = edge.source.x + edge.source.width / 2;
            const y1 = isAbove ? edge.source.y + edge.source.height : edge.source.y;
            const x2 = edge.target.x + edge.target.width / 2;
            const y2 = isAbove ? edge.target.y : edge.target.y + edge.target.height;

            // Curved path for support edge
            const midY = (y1 + y2) / 2;
            const path = `M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`;

            mainGroup.append('path')
                .attr('class', 'support-edge')
                .attr('d', path)
                .attr('fill', 'none')
                .attr('stroke', edge.phaseColor || '#a855f7')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '6,4')
                .attr('stroke-linecap', 'round')
                .attr('marker-end', `url(#${markerId})`);
        });

        // Draw nodes
        const nodeGroups = mainGroup.selectAll('.node-group')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`)
            .style('cursor', 'pointer');

        // Node shadow
        nodeGroups.append('rect')
            .attr('class', 'node-shadow')
            .attr('x', 2)
            .attr('y', 3)
            .attr('width', d => d.width)
            .attr('height', d => d.height)
            .attr('rx', 12)
            .attr('fill', '#000')
            .attr('opacity', 0.06);

        // Node background
        nodeGroups.append('rect')
            .attr('class', 'node-bg')
            .attr('width', d => d.width)
            .attr('height', d => d.height)
            .attr('rx', 12)
            .attr('fill', d => d.color.bg)
            .attr('stroke', d => d.color.border)
            .attr('stroke-width', d => d.isSupporter ? 2 : 2.5)
            .attr('stroke-dasharray', d => d.isSupporter ? '5,3' : 'none')
            .attr('filter', 'url(#drop-shadow)');

        // Phase badge for supporters
        nodeGroups.filter(d => d.isSupporter)
            .append('rect')
            .attr('class', 'phase-badge-bg')
            .attr('x', 8)
            .attr('y', -10)
            .attr('width', d => Math.max(60, (d.phaseName?.length || 4) * 8 + 24))
            .attr('height', 20)
            .attr('rx', 10)
            .attr('fill', d => d.phaseColor || '#a855f7');

        nodeGroups.filter(d => d.isSupporter)
            .append('text')
            .attr('class', 'phase-badge-text')
            .attr('x', 20)
            .attr('y', 4)
            .attr('font-size', '10px')
            .attr('font-weight', '700')
            .attr('fill', 'white')
            .text(d => `↓ ${d.phaseName || '위상'}`);

        // Step index badge (for main flow only)
        nodeGroups.filter(d => !d.isSupporter)
            .each(function(d) {
                const g = d3.select(this);

                g.append('circle')
                    .attr('cx', 18)
                    .attr('cy', 18)
                    .attr('r', 14)
                    .attr('fill', d.color.border);

                g.append('text')
                    .attr('x', 18)
                    .attr('y', 23)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '12px')
                    .attr('font-weight', '700')
                    .attr('fill', 'white')
                    .text(d.stepIndex + 1);
            });

        // Category badge
        nodeGroups.append('rect')
            .attr('x', d => d.isSupporter ? 8 : 38)
            .attr('y', 10)
            .attr('width', d => Math.min(truncate(d.info.category, 10).length * 7 + 12, d.width - 50))
            .attr('height', 18)
            .attr('rx', 4)
            .attr('fill', d => d.color.border)
            .attr('opacity', 0.9);

        nodeGroups.append('text')
            .attr('x', d => d.isSupporter ? 14 : 44)
            .attr('y', 23)
            .attr('font-size', '10px')
            .attr('font-weight', '700')
            .attr('fill', 'white')
            .text(d => truncate(d.info.category, 10));

        // Purpose text (main content)
        nodeGroups.append('text')
            .attr('x', 12)
            .attr('y', 48)
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .attr('fill', d => d.color.text)
            .text(d => truncate(d.info.purpose, d.isSupporter ? 20 : 24));

        // Metadata badges
        nodeGroups.each(function(d) {
            const g = d3.select(this);
            let xOffset = 12;
            const yOffset = d.height - 22;

            if (d.step.captures.length > 0) {
                g.append('rect')
                    .attr('x', xOffset)
                    .attr('y', yOffset)
                    .attr('width', 32)
                    .attr('height', 16)
                    .attr('rx', 8)
                    .attr('fill', '#dbeafe');
                g.append('text')
                    .attr('x', xOffset + 16)
                    .attr('y', yOffset + 12)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '10px')
                    .attr('fill', '#2563eb')
                    .text(`📷${d.step.captures.length}`);
                xOffset += 38;
            }

            if (d.step.attachments.length > 0) {
                g.append('rect')
                    .attr('x', xOffset)
                    .attr('y', yOffset)
                    .attr('width', 32)
                    .attr('height', 16)
                    .attr('rx', 8)
                    .attr('fill', '#fef3c7');
                g.append('text')
                    .attr('x', xOffset + 16)
                    .attr('y', yOffset + 12)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '10px')
                    .attr('fill', '#d97706')
                    .text(`📎${d.step.attachments.length}`);
            }
        });

        // Hover and click interactions
        nodeGroups
            .on('mouseenter', function(event, d) {
                hoveredStepId = d.id;
                d3.select(this).select('.node-bg')
                    .transition()
                    .duration(150)
                    .attr('stroke-width', 4)
                    .attr('filter', 'url(#hover-glow)');

                d3.select(this)
                    .transition()
                    .duration(150)
                    .attr('transform', `translate(${d.x}, ${d.y - 3})`);
            })
            .on('mouseleave', function(event, d) {
                hoveredStepId = null;
                d3.select(this).select('.node-bg')
                    .transition()
                    .duration(150)
                    .attr('stroke-width', d.isSupporter ? 2 : 2.5)
                    .attr('filter', 'url(#drop-shadow)');

                d3.select(this)
                    .transition()
                    .duration(150)
                    .attr('transform', `translate(${d.x}, ${d.y})`);
            })
            .on('click', function(event, d) {
                selectedNodeId = d.id;
                focusNode(d.id);
                if (onNodeClick) {
                    onNodeClick(d.id);
                }
            });
    }

    function initSvg() {
        if (!svgContainer) return;

        // Get container dimensions
        const rect = svgContainer.getBoundingClientRect();
        width = rect.width || 800;
        height = rect.height || 400;

        // Clear any existing SVG
        d3.select(svgContainer).selectAll('svg').remove();

        // Create SVG with fixed dimensions
        svg = d3.select(svgContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Main group for transforms
        mainGroup = svg.append('g').attr('class', 'main-group');

        // Setup zoom - only horizontal panning
        zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 2])
            .on('zoom', (event) => {
                // Get current transform
                const transform = event.transform;
                // Lock Y translation to center the graph vertically
                const { totalHeight } = calculateLayout();
                const fixedY = (height - totalHeight * transform.k) / 2;
                const constrainedTransform = d3.zoomIdentity
                    .translate(transform.x, fixedY)
                    .scale(transform.k);
                mainGroup.attr('transform', constrainedTransform.toString());
            });

        svg.call(zoom);

        // Initial render
        render();

        // Set initial view to show first ~4 nodes
        setInitialView();
    }

    function setInitialView() {
        if (!svg || !mainGroup || currentNodes.length === 0) return;

        const rect = svgContainer.getBoundingClientRect();
        const containerWidth = rect.width || 800;
        const containerHeight = rect.height || 400;

        // Calculate scale to show VISIBLE_NODES nodes
        const visibleWidth = VISIBLE_NODES * (NODE_WIDTH + NODE_GAP_X);
        const scale = Math.min(containerWidth / visibleWidth, 1.2);

        // Calculate Y to center main flow vertically
        const { totalHeight } = calculateLayout();
        const mainFlowY = MARGIN.top + SUPPORT_GAP_Y;
        const centerY = (containerHeight / 2) - (mainFlowY + NODE_HEIGHT / 2) * scale;

        // Start from the first node with some padding
        const startX = 20;

        svg.call(
            zoom.transform,
            d3.zoomIdentity.translate(startX, centerY).scale(scale)
        );
    }

    function focusNode(nodeId: string) {
        if (!svg || !mainGroup) return;

        const node = currentNodes.find(n => n.id === nodeId);
        if (!node) return;

        const rect = svgContainer.getBoundingClientRect();
        const containerWidth = rect.width || 800;
        const containerHeight = rect.height || 400;

        // Get current scale
        const currentTransform = d3.zoomTransform(svg.node()!);
        const scale = currentTransform.k;

        // Calculate X to center the node horizontally
        const nodeCenterX = node.x + node.width / 2;
        const targetX = (containerWidth / 2) - nodeCenterX * scale;

        // Keep Y fixed (centered on main flow)
        const { totalHeight } = calculateLayout();
        const mainFlowY = MARGIN.top + SUPPORT_GAP_Y;
        const targetY = (containerHeight / 2) - (mainFlowY + NODE_HEIGHT / 2) * scale;

        svg.transition()
            .duration(400)
            .ease(d3.easeCubicOut)
            .call(
                zoom.transform,
                d3.zoomIdentity.translate(targetX, targetY).scale(scale)
            );
    }

    function fitToView() {
        setInitialView();
    }

    // Reactive update when data changes
    $: if (svg && mainGroup && workflowData) {
        render();
        setInitialView();
    }

    onMount(() => {
        initSvg();

        // Handle resize
        const resizeObserver = new ResizeObserver((entries) => {
            if (svgContainer && svg) {
                const rect = entries[0].contentRect;
                width = rect.width;
                height = rect.height;
                svg.attr('width', width).attr('height', height);
                setInitialView();
            }
        });
        if (svgContainer) {
            resizeObserver.observe(svgContainer);
        }

        return () => {
            resizeObserver.disconnect();
        };
    });

    onDestroy(() => {
        if (svgContainer) {
            d3.select(svgContainer).selectAll('*').remove();
        }
    });
</script>

<div class="d3-workflow-graph" bind:this={svgContainer}>
    <!-- SVG will be inserted here by D3 -->
</div>

<!-- Controls -->
<div class="graph-controls">
    <button class="control-btn" on:click={fitToView} title="화면에 맞추기">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
        </svg>
    </button>
    <button class="control-btn" on:click={() => svg?.transition().call(zoom.scaleBy, 1.3)} title="확대">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
    </button>
    <button class="control-btn" on:click={() => svg?.transition().call(zoom.scaleBy, 0.7)} title="축소">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/>
        </svg>
    </button>
</div>

<!-- Usage hint -->
<div class="usage-hint">
    마우스 휠로 확대/축소 · 드래그로 이동
</div>

<style>
    .d3-workflow-graph {
        width: 100%;
        height: 100%;
        flex: 1;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        position: relative;
        overflow: hidden;
        border-radius: 8px;
    }

    .d3-workflow-graph :global(svg) {
        display: block;
    }

    .graph-controls {
        position: absolute;
        bottom: 12px;
        left: 12px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        background: white;
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .control-btn {
        width: 28px;
        height: 28px;
        border: none;
        background: transparent;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        transition: all 0.15s;
    }

    .control-btn:hover {
        background: #f1f5f9;
        color: #3b82f6;
    }

    .control-btn svg {
        width: 16px;
        height: 16px;
    }

    .usage-hint {
        position: absolute;
        bottom: 12px;
        right: 12px;
        font-size: 10px;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.8);
        padding: 4px 8px;
        border-radius: 4px;
    }
</style>
