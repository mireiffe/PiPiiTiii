<script lang="ts">
    import { onMount, onDestroy, createEventDispatcher } from "svelte";
    import * as d3 from "d3";
    import type {
        ProjectWorkflowData,
        WorkflowSteps,
        WorkflowStepInstance,
        WorkflowStepRow,
        StepContainer,
        ContainerLayoutRow,
        PhaseType,
        SupportRelation,
    } from "$lib/types/workflow";
    import {
        getContainerLayoutRows,
        isStepSupporter,
        getSupportSteps,
        getPhaseById,
    } from "$lib/types/workflow";

    export let workflowData: ProjectWorkflowData;
    export let workflowSteps: WorkflowSteps;
    export let stepContainers: StepContainer[] = [];
    export let globalPhases: PhaseType[] = [];

    const dispatch = createEventDispatcher();

    let svgContainer: HTMLDivElement;
    let svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    let mainGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    let zoom: d3.ZoomBehavior<SVGSVGElement, unknown>;

    // State
    let expandedStepId: string | null = null;
    let hoveredStepId: string | null = null;
    let hoveredContainerId: string | null = null;
    let width = 0;
    let height = 0;

    // Layout constants
    const CONTAINER_MIN_WIDTH = 220;
    const CONTAINER_PADDING = 24;
    const CONTAINER_GAP = 80;
    const CONTAINER_HEADER_HEIGHT = 48;
    const STEP_NODE_WIDTH = 180;
    const STEP_NODE_HEIGHT = 80;
    const STEP_NODE_HEIGHT_EXPANDED = 200;
    const STEP_GAP = 20;
    const MARGIN = { top: 50, right: 50, bottom: 50, left: 50 };

    // Color palette for containers
    const CONTAINER_COLORS = [
        { bg: '#eff6ff', border: '#3b82f6', header: '#dbeafe', text: '#1d4ed8', glow: 'rgba(59, 130, 246, 0.4)' },
        { bg: '#f0fdf4', border: '#22c55e', header: '#dcfce7', text: '#15803d', glow: 'rgba(34, 197, 94, 0.4)' },
        { bg: '#faf5ff', border: '#a855f7', header: '#f3e8ff', text: '#7e22ce', glow: 'rgba(168, 85, 247, 0.4)' },
        { bg: '#fff7ed', border: '#f97316', header: '#ffedd5', text: '#c2410c', glow: 'rgba(249, 115, 22, 0.4)' },
        { bg: '#fdf2f8', border: '#ec4899', header: '#fce7f3', text: '#be185d', glow: 'rgba(236, 72, 153, 0.4)' },
        { bg: '#f0fdfa', border: '#14b8a6', header: '#ccfbf1', text: '#0f766e', glow: 'rgba(20, 184, 166, 0.4)' },
    ];

    const UNCATEGORIZED_COLOR = { bg: '#f9fafb', border: '#9ca3af', header: '#f3f4f6', text: '#4b5563', glow: 'rgba(156, 163, 175, 0.4)' };

    // Helpers
    function getStepDefinition(stepId: string): WorkflowStepRow | undefined {
        return workflowSteps.rows.find(r => r.id === stepId);
    }

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

    function getSortedContainers() {
        return [...stepContainers].sort((a, b) => a.order - b.order);
    }

    function getStepsByContainer() {
        const map: Record<string, WorkflowStepInstance[]> = { __uncategorized__: [] };
        getSortedContainers().forEach(c => { map[c.id] = []; });

        workflowData.steps.forEach(step => {
            const key = step.containerId ?? '__uncategorized__';
            if (map[key]) {
                map[key].push(step);
            } else {
                map.__uncategorized__.push(step);
            }
        });
        return map;
    }

    interface ContainerLayout {
        id: string;
        name: string;
        x: number;
        y: number;
        width: number;
        height: number;
        color: typeof CONTAINER_COLORS[0];
        steps: StepLayout[];
        colorIndex: number;
        supportGroups: SupportGroupLayout[];  // For phase-based support layout
    }

    interface SupportGroupLayout {
        mainStep: StepLayout;
        supporters: SupporterLayout[];
    }

    interface SupporterLayout {
        step: StepLayout;
        phaseId: string;
        phaseColor?: string;
        phaseName?: string;
    }

    interface StepLayout {
        id: string;
        step: WorkflowStepInstance;
        info: ReturnType<typeof getStepInfo>;
        x: number;
        y: number;
        width: number;
        height: number;
        isExpanded: boolean;
        globalIndex: number;
        isSupporter: boolean;  // Is this step supporting another?
        hideBadge: boolean;  // Hide step number badge
        supportTargetId?: string;  // ID of step being supported (if supporter)
        phaseColor?: string;  // Phase color (if supporter)
    }

    function calculateLayout(): { containers: ContainerLayout[], totalWidth: number, totalHeight: number } {
        const sortedContainers = getSortedContainers();
        const containers: ContainerLayout[] = [];

        let currentX = MARGIN.left;
        let maxHeight = 0;
        let globalStepIndex = 0;

        const SUPPORTER_INDENT = 30;  // Indentation for supporter steps
        const SUPPORTER_WIDTH = STEP_NODE_WIDTH - 20;  // Slightly narrower

        // Helper to build layout for a container using new phase system
        function buildContainerLayout(containerId: string | undefined): { supportGroups: SupportGroupLayout[], allSteps: StepLayout[], totalWidth: number, maxHeight: number } {
            const layoutRows = getContainerLayoutRows(
                containerId,
                workflowData.steps,
                workflowData.supportRelations,
                globalPhases
            );
            const supportGroups: SupportGroupLayout[] = [];
            const allSteps: StepLayout[] = [];

            if (layoutRows.length === 0) {
                return { supportGroups: [], allSteps: [], totalWidth: CONTAINER_MIN_WIDTH, maxHeight: 140 };
            }

            let currentY = CONTAINER_HEADER_HEIGHT + CONTAINER_PADDING;

            layoutRows.forEach((row) => {
                const mainStep = row.mainStep;
                const isExpanded = expandedStepId === mainStep.id;
                const mainH = isExpanded ? STEP_NODE_HEIGHT_EXPANDED : STEP_NODE_HEIGHT;

                const mainStepLayout: StepLayout = {
                    id: mainStep.id,
                    step: mainStep,
                    info: getStepInfo(mainStep),
                    x: CONTAINER_PADDING,
                    y: currentY,
                    width: STEP_NODE_WIDTH,
                    height: mainH,
                    isExpanded,
                    globalIndex: globalStepIndex++,
                    isSupporter: false,
                    hideBadge: false,
                };
                allSteps.push(mainStepLayout);

                currentY += mainH + STEP_GAP / 2;

                // Process supporters
                const supporterLayouts: SupporterLayout[] = [];
                row.supporters.forEach((supporter) => {
                    const supStep = supporter.step;
                    const supExpanded = expandedStepId === supStep.id;
                    const supH = supExpanded ? STEP_NODE_HEIGHT_EXPANDED : STEP_NODE_HEIGHT - 10;
                    const phase = supporter.phase;

                    const supStepLayout: StepLayout = {
                        id: supStep.id,
                        step: supStep,
                        info: getStepInfo(supStep),
                        x: CONTAINER_PADDING + SUPPORTER_INDENT,
                        y: currentY,
                        width: SUPPORTER_WIDTH,
                        height: supH,
                        isExpanded: supExpanded,
                        globalIndex: globalStepIndex++,
                        isSupporter: true,
                        hideBadge: true,
                        supportTargetId: mainStep.id,
                        phaseColor: phase?.color,
                    };
                    allSteps.push(supStepLayout);

                    supporterLayouts.push({
                        step: supStepLayout,
                        phaseId: supporter.relation.phaseId,
                        phaseColor: phase?.color,
                        phaseName: phase?.name,
                    });

                    currentY += supH + STEP_GAP / 2;
                });

                supportGroups.push({
                    mainStep: mainStepLayout,
                    supporters: supporterLayouts,
                });

                currentY += STEP_GAP / 2;
            });

            const totalHeight = currentY + CONTAINER_PADDING;
            const totalWidth = Math.max(CONTAINER_MIN_WIDTH, CONTAINER_PADDING * 2 + STEP_NODE_WIDTH);

            return { supportGroups, allSteps, totalWidth, maxHeight: totalHeight };
        }

        // Uncategorized steps (only show if there ARE defined containers AND uncategorized steps exist)
        const uncatRows = getContainerLayoutRows(
            undefined,
            workflowData.steps,
            workflowData.supportRelations,
            globalPhases
        );
        const hasUncategorized = uncatRows.length > 0;

        // Only show uncategorized container when:
        // 1. There are defined containers (sortedContainers.length > 0)
        // 2. AND there are uncategorized steps
        if (hasUncategorized && sortedContainers.length > 0) {
            const { supportGroups, allSteps, totalWidth, maxHeight: colMaxHeight } = buildContainerLayout(undefined);

            containers.push({
                id: '__uncategorized__',
                name: '미분류',
                x: currentX,
                y: MARGIN.top,
                width: totalWidth,
                height: Math.max(colMaxHeight, 140),
                color: UNCATEGORIZED_COLOR,
                steps: allSteps,
                colorIndex: -1,
                supportGroups,
            });

            currentX += totalWidth + CONTAINER_GAP;
            maxHeight = Math.max(maxHeight, colMaxHeight);
        }

        // Named containers
        sortedContainers.forEach((container, cIndex) => {
            const { supportGroups, allSteps, totalWidth, maxHeight: colMaxHeight } = buildContainerLayout(container.id);

            const containerHeight = allSteps.length > 0 ? colMaxHeight : 140;

            containers.push({
                id: container.id,
                name: container.name,
                x: currentX,
                y: MARGIN.top,
                width: totalWidth,
                height: containerHeight,
                color: CONTAINER_COLORS[cIndex % CONTAINER_COLORS.length],
                steps: allSteps,
                colorIndex: cIndex,
                supportGroups,
            });

            currentX += totalWidth + CONTAINER_GAP;
            maxHeight = Math.max(maxHeight, containerHeight);
        });

        // Align container heights
        containers.forEach(c => {
            c.height = Math.max(maxHeight, 140);
        });

        return {
            containers,
            totalWidth: currentX + MARGIN.right - CONTAINER_GAP,
            totalHeight: Math.max(maxHeight, 140) + MARGIN.top + MARGIN.bottom,
        };
    }

    function render() {
        if (!svg || !mainGroup) return;

        const { containers, totalWidth, totalHeight } = calculateLayout();

        // Clear previous content
        mainGroup.selectAll('*').remove();

        // Defs for gradients and filters
        const defs = mainGroup.append('defs');

        // Drop shadow filter
        const filter = defs.append('filter')
            .attr('id', 'drop-shadow')
            .attr('x', '-30%')
            .attr('y', '-30%')
            .attr('width', '160%')
            .attr('height', '160%');
        filter.append('feDropShadow')
            .attr('dx', '0')
            .attr('dy', '4')
            .attr('stdDeviation', '6')
            .attr('flood-opacity', '0.12');

        // Glow filters for each color
        containers.forEach((c, i) => {
            const glowFilter = defs.append('filter')
                .attr('id', `glow-${i}`)
                .attr('x', '-50%')
                .attr('y', '-50%')
                .attr('width', '200%')
                .attr('height', '200%');
            glowFilter.append('feGaussianBlur')
                .attr('stdDeviation', '4')
                .attr('result', 'coloredBlur');
            glowFilter.append('feFlood')
                .attr('flood-color', c.color.glow)
                .attr('result', 'glowColor');
            glowFilter.append('feComposite')
                .attr('in', 'glowColor')
                .attr('in2', 'coloredBlur')
                .attr('operator', 'in')
                .attr('result', 'softGlow');
            const feMerge = glowFilter.append('feMerge');
            feMerge.append('feMergeNode').attr('in', 'softGlow');
            feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
        });

        // Step hover glow
        const stepGlow = defs.append('filter')
            .attr('id', 'step-glow')
            .attr('x', '-30%')
            .attr('y', '-30%')
            .attr('width', '160%')
            .attr('height', '160%');
        stepGlow.append('feDropShadow')
            .attr('dx', '0')
            .attr('dy', '2')
            .attr('stdDeviation', '8')
            .attr('flood-color', 'rgba(59, 130, 246, 0.5)')
            .attr('flood-opacity', '0.5');

        // Draw animated background particles
        const particleGroup = mainGroup.append('g').attr('class', 'particles');
        for (let i = 0; i < 15; i++) {
            const cx = Math.random() * totalWidth;
            const cy = Math.random() * totalHeight;
            particleGroup.append('circle')
                .attr('cx', cx)
                .attr('cy', cy)
                .attr('r', Math.random() * 3 + 1)
                .attr('fill', '#e2e8f0')
                .attr('opacity', 0.5);
        }

        // Draw container connections (animated arrows between containers)
        if (containers.length > 1) {
            const connGroup = mainGroup.append('g').attr('class', 'container-connections');

            // Animated dash pattern
            defs.append('style').text(`
                @keyframes dashFlow {
                    from { stroke-dashoffset: 24; }
                    to { stroke-dashoffset: 0; }
                }
                .animated-dash {
                    animation: dashFlow 1s linear infinite;
                }
            `);

            for (let i = 0; i < containers.length - 1; i++) {
                const from = containers[i];
                const to = containers[i + 1];

                const x1 = from.x + from.width + 4;
                const y1 = from.y + from.height / 2;
                const x2 = to.x - 4;
                const y2 = to.y + to.height / 2;

                // Draw curved arrow with gradient
                const midX = (x1 + x2) / 2;
                const path = d3.path();
                path.moveTo(x1, y1);
                path.bezierCurveTo(midX, y1, midX, y2, x2 - 12, y2);

                // Gradient for connection
                const gradId = `conn-grad-${i}`;
                const grad = defs.append('linearGradient')
                    .attr('id', gradId)
                    .attr('x1', '0%')
                    .attr('y1', '0%')
                    .attr('x2', '100%')
                    .attr('y2', '0%');
                grad.append('stop').attr('offset', '0%').attr('stop-color', from.color.border);
                grad.append('stop').attr('offset', '100%').attr('stop-color', to.color.border);

                // Background line
                connGroup.append('path')
                    .attr('d', path.toString())
                    .attr('fill', 'none')
                    .attr('stroke', '#e2e8f0')
                    .attr('stroke-width', 6)
                    .attr('stroke-linecap', 'round');

                // Animated foreground line
                connGroup.append('path')
                    .attr('class', 'animated-dash')
                    .attr('d', path.toString())
                    .attr('fill', 'none')
                    .attr('stroke', `url(#${gradId})`)
                    .attr('stroke-width', 3)
                    .attr('stroke-dasharray', '12,12')
                    .attr('stroke-linecap', 'round')
                    .attr('marker-end', `url(#arrow-container-${i})`);

                // Arrow marker
                defs.append('marker')
                    .attr('id', `arrow-container-${i}`)
                    .attr('viewBox', '0 -6 12 12')
                    .attr('refX', 10)
                    .attr('refY', 0)
                    .attr('markerWidth', 8)
                    .attr('markerHeight', 8)
                    .attr('orient', 'auto')
                    .append('path')
                    .attr('d', 'M0,-6L12,0L0,6Z')
                    .attr('fill', to.color.border);
            }
        }

        // Draw containers
        const containerGroups = mainGroup.selectAll('.container-group')
            .data(containers)
            .enter()
            .append('g')
            .attr('class', 'container-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);

        // Container outer glow (subtle)
        containerGroups.append('rect')
            .attr('x', -4)
            .attr('y', -4)
            .attr('width', d => d.width + 8)
            .attr('height', d => d.height + 8)
            .attr('rx', 20)
            .attr('ry', 20)
            .attr('fill', 'none')
            .attr('stroke', d => d.color.border)
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.2);

        // Container background with animation
        containerGroups.append('rect')
            .attr('class', 'container-bg')
            .attr('width', d => d.width)
            .attr('height', d => d.height)
            .attr('rx', 16)
            .attr('ry', 16)
            .attr('fill', d => d.color.bg)
            .attr('stroke', d => d.color.border)
            .attr('stroke-width', 2)
            .attr('filter', 'url(#drop-shadow)')
            .style('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
                hoveredContainerId = d.id;
                const idx = containers.indexOf(d);
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('stroke-width', 3)
                    .attr('filter', `url(#glow-${idx})`);

                // Scale up slightly
                d3.select(this.parentNode as Element)
                    .transition()
                    .duration(200)
                    .attr('transform', `translate(${d.x - 2}, ${d.y - 2}) scale(1.01)`);
            })
            .on('mouseleave', function(event, d) {
                hoveredContainerId = null;
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('stroke-width', 2)
                    .attr('filter', 'url(#drop-shadow)');

                d3.select(this.parentNode as Element)
                    .transition()
                    .duration(200)
                    .attr('transform', `translate(${d.x}, ${d.y}) scale(1)`);
            });

        // Container header gradient
        containerGroups.each(function(d) {
            const group = d3.select(this);
            const gradId = `header-grad-${d.id.replace(/[^a-zA-Z0-9]/g, '')}`;

            defs.append('linearGradient')
                .attr('id', gradId)
                .attr('x1', '0%')
                .attr('y1', '0%')
                .attr('x2', '100%')
                .attr('y2', '0%')
                .selectAll('stop')
                .data([
                    { offset: '0%', color: d.color.header },
                    { offset: '100%', color: d.color.bg }
                ])
                .enter()
                .append('stop')
                .attr('offset', d => d.offset)
                .attr('stop-color', d => d.color);

            group.append('rect')
                .attr('class', 'container-header')
                .attr('width', d.width)
                .attr('height', CONTAINER_HEADER_HEIGHT)
                .attr('rx', 16)
                .attr('ry', 16)
                .attr('fill', `url(#${gradId})`);

            // Header bottom straight edge
            group.append('rect')
                .attr('y', CONTAINER_HEADER_HEIGHT - 16)
                .attr('width', d.width)
                .attr('height', 16)
                .attr('fill', d.color.header);
        });

        // Container icon
        containerGroups.append('text')
            .attr('x', 16)
            .attr('y', CONTAINER_HEADER_HEIGHT / 2 + 6)
            .attr('font-size', '18px')
            .text(d => d.id === '__uncategorized__' ? '📦' : '📁');

        // Container title
        containerGroups.append('text')
            .attr('x', 40)
            .attr('y', CONTAINER_HEADER_HEIGHT / 2 + 5)
            .attr('font-size', '14px')
            .attr('font-weight', '700')
            .attr('fill', d => d.color.text)
            .text(d => d.name.length > 12 ? d.name.substring(0, 10) + '...' : d.name);

        // Step count badge
        containerGroups.append('rect')
            .attr('x', d => d.width - 48)
            .attr('y', CONTAINER_HEADER_HEIGHT / 2 - 10)
            .attr('width', 36)
            .attr('height', 20)
            .attr('rx', 10)
            .attr('fill', d => d.color.border)
            .attr('opacity', 0.2);

        containerGroups.append('text')
            .attr('x', d => d.width - 30)
            .attr('y', CONTAINER_HEADER_HEIGHT / 2 + 5)
            .attr('text-anchor', 'middle')
            .attr('font-size', '11px')
            .attr('font-weight', '600')
            .attr('fill', d => d.color.text)
            .text(d => d.steps.length);

        // Draw step connections within containers (with support/phase system)
        containerGroups.each(function(containerData, containerIdx) {
            const group = d3.select(this);
            const supportGroups = containerData.supportGroups;
            const lineGroup = group.append('g').attr('class', 'step-connections');

            // Arrow marker for main flow
            defs.append('marker')
                .attr('id', `arrow-step-${containerIdx}`)
                .attr('viewBox', '0 -4 8 8')
                .attr('refX', 6)
                .attr('refY', 0)
                .attr('markerWidth', 5)
                .attr('markerHeight', 5)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-4L8,0L0,4Z')
                .attr('fill', containerData.color.border)
                .attr('fill-opacity', 0.5);

            // 1. Draw connections between main flow steps
            for (let i = 0; i < supportGroups.length - 1; i++) {
                const from = supportGroups[i].mainStep;
                const to = supportGroups[i + 1].mainStep;

                const x1 = from.x + from.width / 2;
                const y1 = from.y + from.height + 2;
                const x2 = to.x + to.width / 2;
                const y2 = to.y - 2;

                // Account for supporters between
                const hasSupport = supportGroups[i].supporters.length > 0;

                const path = d3.path();
                path.moveTo(x1, y1);
                if (hasSupport) {
                    // Curve around supporters
                    const midY = y2 - 10;
                    path.lineTo(x1, midY);
                    path.bezierCurveTo(x1, y2 - 5, x2, y2 - 5, x2, y2);
                } else {
                    const midY = (y1 + y2) / 2;
                    path.bezierCurveTo(x1, midY, x2, midY, x2, y2);
                }

                lineGroup.append('path')
                    .attr('d', path.toString())
                    .attr('fill', 'none')
                    .attr('stroke', containerData.color.border)
                    .attr('stroke-width', 2)
                    .attr('stroke-opacity', 0.4)
                    .attr('stroke-linecap', 'round')
                    .attr('marker-end', `url(#arrow-step-${containerIdx})`);
            }

            // 2. Draw support connections (from main step to each supporter)
            supportGroups.forEach(sg => {
                sg.supporters.forEach(supporter => {
                    const main = sg.mainStep;
                    const sup = supporter.step;
                    const phaseColor = supporter.phaseColor || '#a855f7';

                    const x1 = main.x + 10;
                    const y1 = main.y + main.height;
                    const x2 = sup.x - 2;
                    const y2 = sup.y + sup.height / 2;

                    // Horizontal dashed line with phase color
                    const path = d3.path();
                    path.moveTo(x1, y1);
                    path.lineTo(x1, y2);
                    path.lineTo(x2, y2);

                    lineGroup.append('path')
                        .attr('d', path.toString())
                        .attr('fill', 'none')
                        .attr('stroke', phaseColor)
                        .attr('stroke-width', 2)
                        .attr('stroke-opacity', 0.6)
                        .attr('stroke-dasharray', '4,3')
                        .attr('stroke-linecap', 'round');

                    // Small circle at connection point
                    lineGroup.append('circle')
                        .attr('cx', x1)
                        .attr('cy', y1)
                        .attr('r', 3)
                        .attr('fill', phaseColor)
                        .attr('opacity', 0.7);
                });
            });
        });

        // Draw step nodes
        containerGroups.each(function(containerData) {
            const group = d3.select(this);

            const stepGroups = group.selectAll('.step-node')
                .data(containerData.steps)
                .enter()
                .append('g')
                .attr('class', 'step-node')
                .attr('transform', d => `translate(${d.x}, ${d.y})`)
                .style('cursor', 'pointer');

            // Step card shadow
            stepGroups.append('rect')
                .attr('class', 'step-shadow')
                .attr('x', 2)
                .attr('y', 4)
                .attr('width', d => d.width)
                .attr('height', d => d.height)
                .attr('rx', 12)
                .attr('ry', 12)
                .attr('fill', '#000')
                .attr('opacity', 0.06);

            // Step card background
            stepGroups.append('rect')
                .attr('class', 'step-bg')
                .attr('width', d => d.width)
                .attr('height', d => d.height)
                .attr('rx', 12)
                .attr('ry', 12)
                .attr('fill', 'white')
                .attr('stroke', d => d.isExpanded ? containerData.color.border : '#e2e8f0')
                .attr('stroke-width', d => d.isExpanded ? 2.5 : 1.5)
                .on('mouseenter', function(event, d) {
                    hoveredStepId = d.id;
                    d3.select(this)
                        .transition()
                        .duration(150)
                        .attr('stroke', containerData.color.border)
                        .attr('stroke-width', 2.5)
                        .attr('filter', 'url(#step-glow)');

                    // Lift up effect
                    d3.select(this.parentNode as Element)
                        .transition()
                        .duration(150)
                        .attr('transform', `translate(${d.x}, ${d.y - 3})`);
                })
                .on('mouseleave', function(event, d) {
                    hoveredStepId = null;
                    d3.select(this)
                        .transition()
                        .duration(150)
                        .attr('stroke', d.isExpanded ? containerData.color.border : '#e2e8f0')
                        .attr('stroke-width', d.isExpanded ? 2.5 : 1.5)
                        .attr('filter', null);

                    d3.select(this.parentNode as Element)
                        .transition()
                        .duration(150)
                        .attr('transform', `translate(${d.x}, ${d.y})`);
                })
                .on('click', function(event, d) {
                    event.stopPropagation();

                    // Click pulse animation
                    const node = d3.select(this);
                    node.transition()
                        .duration(100)
                        .attr('stroke-width', 4)
                        .transition()
                        .duration(100)
                        .attr('stroke-width', 2.5);

                    toggleStepExpand(d.id);
                });

            // Step index badge with gradient (or support indicator)
            stepGroups.each(function(d) {
                const g = d3.select(this);

                if (d.isSupporter) {
                    // Support indicator - colored circle with + icon
                    g.append('circle')
                        .attr('cx', 18)
                        .attr('cy', 18)
                        .attr('r', 12)
                        .attr('fill', d.phaseColor || '#a855f7');

                    // Plus icon (+) for support
                    g.append('text')
                        .attr('x', 18)
                        .attr('y', 23)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '14px')
                        .attr('font-weight', '700')
                        .attr('fill', 'white')
                        .text('+');
                } else if (!d.hideBadge) {
                    // Normal step badge with gradient
                    const badgeGradId = `badge-${d.id.replace(/[^a-zA-Z0-9]/g, '')}`;

                    defs.append('radialGradient')
                        .attr('id', badgeGradId)
                        .selectAll('stop')
                        .data([
                            { offset: '0%', color: containerData.color.border },
                            { offset: '100%', color: d3.color(containerData.color.border)?.darker(0.3)?.toString() || containerData.color.border }
                        ])
                        .enter()
                        .append('stop')
                        .attr('offset', dd => dd.offset)
                        .attr('stop-color', dd => dd.color);

                    g.append('circle')
                        .attr('cx', 18)
                        .attr('cy', 18)
                        .attr('r', 12)
                        .attr('fill', `url(#${badgeGradId})`);

                    g.append('text')
                        .attr('x', 18)
                        .attr('y', 22)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '11px')
                        .attr('font-weight', '700')
                        .attr('fill', 'white')
                        .text(d.globalIndex + 1);
                }
            });

            // Category badge
            stepGroups.append('rect')
                .attr('x', 36)
                .attr('y', 10)
                .attr('width', d => Math.min(d.info.category.length * 7 + 16, d.width - 50))
                .attr('height', 18)
                .attr('rx', 9)
                .attr('fill', containerData.color.header);

            stepGroups.append('text')
                .attr('x', 44)
                .attr('y', 23)
                .attr('font-size', '10px')
                .attr('font-weight', '600')
                .attr('fill', containerData.color.text)
                .text(d => d.info.category.length > 10 ? d.info.category.substring(0, 8) + '..' : d.info.category);

            // Purpose (main text)
            stepGroups.append('text')
                .attr('x', 14)
                .attr('y', 48)
                .attr('font-size', '12px')
                .attr('font-weight', '600')
                .attr('fill', '#1e293b')
                .each(function(d) {
                    const text = d3.select(this);
                    let purpose = d.info.purpose;
                    if (purpose.length > 18) {
                        purpose = purpose.substring(0, 16) + '...';
                    }
                    text.text(purpose);
                });

            // Metadata badges (captures, attachments)
            stepGroups.append('g')
                .attr('class', 'step-metadata')
                .attr('transform', 'translate(14, 58)')
                .each(function(d) {
                    const g = d3.select(this);
                    let xOffset = 0;

                    if (d.step.captures.length > 0) {
                        g.append('rect')
                            .attr('x', xOffset)
                            .attr('y', 0)
                            .attr('width', 36)
                            .attr('height', 16)
                            .attr('rx', 8)
                            .attr('fill', '#dbeafe');
                        g.append('text')
                            .attr('x', xOffset + 18)
                            .attr('y', 12)
                            .attr('text-anchor', 'middle')
                            .attr('font-size', '10px')
                            .attr('fill', '#2563eb')
                            .text(`📷 ${d.step.captures.length}`);
                        xOffset += 42;
                    }

                    if (d.step.attachments.length > 0) {
                        g.append('rect')
                            .attr('x', xOffset)
                            .attr('y', 0)
                            .attr('width', 36)
                            .attr('height', 16)
                            .attr('rx', 8)
                            .attr('fill', '#fef3c7');
                        g.append('text')
                            .attr('x', xOffset + 18)
                            .attr('y', 12)
                            .attr('text-anchor', 'middle')
                            .attr('font-size', '10px')
                            .attr('fill', '#d97706')
                            .text(`📎 ${d.step.attachments.length}`);
                    }
                });

            // Expanded details
            stepGroups.filter(d => d.isExpanded)
                .each(function(d) {
                    const g = d3.select(this);

                    // Divider line
                    g.append('line')
                        .attr('x1', 14)
                        .attr('y1', 82)
                        .attr('x2', d.width - 14)
                        .attr('y2', 82)
                        .attr('stroke', '#e2e8f0')
                        .attr('stroke-width', 1);

                    // Expand icon
                    g.append('text')
                        .attr('x', d.width - 20)
                        .attr('y', 22)
                        .attr('font-size', '12px')
                        .attr('fill', containerData.color.text)
                        .attr('opacity', 0.6)
                        .text('▲');

                    let yPos = 96;

                    // Step ID / Global Index
                    g.append('text')
                        .attr('x', 14)
                        .attr('y', yPos)
                        .attr('font-size', '9px')
                        .attr('fill', '#94a3b8')
                        .text(`#${d.globalIndex + 1} · ${d.step.stepId.substring(0, 15)}`);
                    yPos += 16;

                    // System info
                    if (d.info.system) {
                        g.append('text')
                            .attr('x', 14)
                            .attr('y', yPos)
                            .attr('font-size', '10px')
                            .attr('fill', '#64748b')
                            .text(`🖥️ ${d.info.system.substring(0, 20)}${d.info.system.length > 20 ? '...' : ''}`);
                        yPos += 16;
                    }

                    // Target info
                    if (d.info.target) {
                        g.append('text')
                            .attr('x', 14)
                            .attr('y', yPos)
                            .attr('font-size', '10px')
                            .attr('fill', '#64748b')
                            .text(`🎯 ${d.info.target.substring(0, 20)}${d.info.target.length > 20 ? '...' : ''}`);
                        yPos += 16;
                    }

                    // Expected result
                    if (d.info.expectedResult) {
                        g.append('text')
                            .attr('x', 14)
                            .attr('y', yPos)
                            .attr('font-size', '10px')
                            .attr('fill', '#64748b')
                            .text(`✅ ${d.info.expectedResult.substring(0, 20)}${d.info.expectedResult.length > 20 ? '...' : ''}`);
                        yPos += 16;
                    }

                    // Captures and attachments summary at bottom
                    const captureCount = d.step.captures.length;
                    const attachmentCount = d.step.attachments.length;
                    if (captureCount > 0 || attachmentCount > 0) {
                        yPos = d.height - 20;
                        let xPos = 14;

                        if (captureCount > 0) {
                            g.append('rect')
                                .attr('x', xPos)
                                .attr('y', yPos - 12)
                                .attr('width', 50)
                                .attr('height', 16)
                                .attr('rx', 8)
                                .attr('fill', '#dbeafe');
                            g.append('text')
                                .attr('x', xPos + 25)
                                .attr('y', yPos)
                                .attr('text-anchor', 'middle')
                                .attr('font-size', '9px')
                                .attr('fill', '#2563eb')
                                .text(`📷 ${captureCount} 캡처`);
                            xPos += 56;
                        }

                        if (attachmentCount > 0) {
                            g.append('rect')
                                .attr('x', xPos)
                                .attr('y', yPos - 12)
                                .attr('width', 50)
                                .attr('height', 16)
                                .attr('rx', 8)
                                .attr('fill', '#fef3c7');
                            g.append('text')
                                .attr('x', xPos + 25)
                                .attr('y', yPos)
                                .attr('text-anchor', 'middle')
                                .attr('font-size', '9px')
                                .attr('fill', '#d97706')
                                .text(`📎 ${attachmentCount} 첨부`);
                        }
                    }

                    // Created time
                    if (d.step.createdAt) {
                        const date = new Date(d.step.createdAt);
                        const dateStr = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
                        g.append('text')
                            .attr('x', d.width - 14)
                            .attr('y', d.height - 8)
                            .attr('text-anchor', 'end')
                            .attr('font-size', '8px')
                            .attr('fill', '#cbd5e1')
                            .text(dateStr);
                    }
                });

            // Collapse indicator for non-expanded
            stepGroups.filter(d => !d.isExpanded)
                .append('text')
                .attr('x', d => d.width - 20)
                .attr('y', 22)
                .attr('font-size', '12px')
                .attr('fill', containerData.color.text)
                .attr('opacity', 0.3)
                .text('▼');
        });

        // Empty state with animation
        const hasNoContainers = getSortedContainers().length === 0;
        const hasSteps = workflowData.steps.length > 0;
        const showEmptyState = containers.length === 0 || (containers.length === 1 && containers[0].steps.length === 0 && !hasSteps);

        if (showEmptyState) {
            const emptyGroup = mainGroup.append('g')
                .attr('transform', `translate(${width / 2}, ${height / 2})`);

            if (hasNoContainers && hasSteps) {
                // No containers defined but steps exist
                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', -20)
                    .attr('font-size', '40px')
                    .text('📦');

                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', 20)
                    .attr('font-size', '14px')
                    .attr('fill', '#9ca3af')
                    .attr('font-weight', '500')
                    .text('Container가 정의되어 있지 않습니다');

                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', 45)
                    .attr('font-size', '11px')
                    .attr('fill', '#cbd5e1')
                    .text('설정에서 Container를 추가해주세요');
            } else {
                // No steps at all
                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', -20)
                    .attr('font-size', '40px')
                    .text('📋');

                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', 20)
                    .attr('font-size', '14px')
                    .attr('fill', '#9ca3af')
                    .attr('font-weight', '500')
                    .text('워크플로우 스텝이 없습니다');

                emptyGroup.append('text')
                    .attr('text-anchor', 'middle')
                    .attr('y', 45)
                    .attr('font-size', '11px')
                    .attr('fill', '#cbd5e1')
                    .text('List 뷰에서 스텝을 추가해보세요');
            }
        }

        // Fit view with smooth animation
        requestAnimationFrame(() => {
            const bounds = mainGroup.node()?.getBBox();
            if (bounds && bounds.width > 0 && bounds.height > 0) {
                const scale = Math.min(
                    (width - 40) / bounds.width,
                    (height - 40) / bounds.height,
                    1.2
                );
                const centerX = (width - bounds.width * scale) / 2 - bounds.x * scale;
                const centerY = (height - bounds.height * scale) / 2 - bounds.y * scale;

                svg.transition()
                    .duration(400)
                    .ease(d3.easeCubicOut)
                    .call(zoom.transform as any, d3.zoomIdentity.translate(centerX, centerY).scale(scale));
            }
        });
    }

    function toggleStepExpand(stepId: string) {
        if (expandedStepId === stepId) {
            expandedStepId = null;
        } else {
            expandedStepId = stepId;
        }
        render();
    }

    function initSvg() {
        if (!svgContainer) return;

        const rect = svgContainer.getBoundingClientRect();
        width = rect.width || 600;
        height = rect.height || 400;

        // Clear existing
        d3.select(svgContainer).selectAll('svg').remove();

        svg = d3.select(svgContainer)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`);

        // Add gradient background
        const bgGrad = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'bg-gradient')
            .attr('x1', '0%')
            .attr('y1', '0%')
            .attr('x2', '100%')
            .attr('y2', '100%');
        bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#f8fafc');
        bgGrad.append('stop').attr('offset', '50%').attr('stop-color', '#f1f5f9');
        bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#e2e8f0');

        svg.append('rect')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('fill', 'url(#bg-gradient)');

        mainGroup = svg.append('g');

        // Zoom behavior with smooth easing
        zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.2, 3])
            .on('zoom', (event) => {
                mainGroup.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Double click to reset zoom
        svg.on('dblclick.zoom', () => {
            svg.transition()
                .duration(600)
                .ease(d3.easeCubicInOut)
                .call(zoom.transform as any, d3.zoomIdentity);
            setTimeout(render, 100);
        });

        render();
    }

    function handleResize() {
        if (svgContainer) {
            const rect = svgContainer.getBoundingClientRect();
            width = rect.width || 600;
            height = rect.height || 400;

            if (svg) {
                svg.attr('viewBox', `0 0 ${width} ${height}`);
                svg.select('rect').attr('width', width).attr('height', height);
                render();
            }
        }
    }

    onMount(() => {
        initSvg();
        window.addEventListener('resize', handleResize);
    });

    onDestroy(() => {
        window.removeEventListener('resize', handleResize);
    });

    // Re-render when data changes
    $: if (svg && (workflowData || workflowSteps || stepContainers)) {
        render();
    }
</script>

<div class="container-graph" bind:this={svgContainer}>
    <div class="controls">
        <button
            class="control-btn"
            title="확대"
            on:click={() => svg?.transition().duration(300).ease(d3.easeCubicOut).call(zoom.scaleBy as any, 1.4)}
        >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
        </button>
        <button
            class="control-btn"
            title="축소"
            on:click={() => svg?.transition().duration(300).ease(d3.easeCubicOut).call(zoom.scaleBy as any, 0.7)}
        >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
        </button>
        <button
            class="control-btn"
            title="뷰 리셋 (더블클릭)"
            on:click={() => {
                svg?.transition().duration(600).ease(d3.easeCubicInOut).call(zoom.transform as any, d3.zoomIdentity);
                setTimeout(render, 100);
            }}
        >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                <path d="M3 3v5h5"/>
            </svg>
        </button>
    </div>
    <div class="hint">
        <span class="hint-item">🖱️ 클릭: 펼치기</span>
        <span class="hint-item">✋ 드래그: 이동</span>
        <span class="hint-item">🔍 스크롤: 확대</span>
    </div>
</div>

<style>
    .container-graph {
        width: 100%;
        height: 100%;
        min-height: 400px;
        position: relative;
        overflow: hidden;
        border-radius: 12px;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
    }

    .controls {
        position: absolute;
        bottom: 20px;
        left: 20px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        z-index: 10;
    }

    .control-btn {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .control-btn:hover {
        background: #f8fafc;
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }

    .control-btn:active {
        transform: scale(0.95) translateY(0);
    }

    .control-btn svg {
        width: 18px;
        height: 18px;
        color: #64748b;
        transition: color 0.2s;
    }

    .control-btn:hover svg {
        color: #3b82f6;
    }

    .hint {
        position: absolute;
        bottom: 12px;
        right: 16px;
        display: flex;
        gap: 12px;
        pointer-events: none;
    }

    .hint-item {
        font-size: 10px;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.8);
        padding: 4px 8px;
        border-radius: 6px;
        backdrop-filter: blur(4px);
    }

    :global(.container-graph svg) {
        display: block;
    }

    :global(.container-graph .step-node) {
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    :global(.container-graph .container-group) {
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
