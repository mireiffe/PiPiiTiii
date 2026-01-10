<script lang="ts">
    import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/svelte";

    // Edge props from SvelteFlow
    export let id: string;
    export let sourceX: number;
    export let sourceY: number;
    export let targetX: number;
    export let targetY: number;
    export let sourcePosition: any;
    export let targetPosition: any;
    export let data: { isLoopback?: boolean } | undefined;
    export let markerEnd: string = "";
    export let style: string = "";

    // Calculate custom loopback path
    // Loopback goes: source -> right -> up -> target
    $: loopbackPath = calculateLoopbackPath(sourceX, sourceY, targetX, targetY);

    function calculateLoopbackPath(
        sx: number,
        sy: number,
        tx: number,
        ty: number
    ): string {
        // Offset to the right
        const offsetX = 60;
        const controlOffset = 30;

        // Path: from source bottom, curve right, go up, curve to target top
        // M = move to, Q = quadratic curve, L = line to
        const midX = Math.max(sx, tx) + offsetX;

        return `
            M ${sx} ${sy}
            Q ${sx + controlOffset} ${sy + controlOffset}, ${midX} ${sy}
            L ${midX} ${ty}
            Q ${midX} ${ty - controlOffset}, ${tx + controlOffset} ${ty - controlOffset}
            L ${tx} ${ty}
        `;
    }
</script>

<g class="loopback-edge">
    <path
        {id}
        d={loopbackPath}
        fill="none"
        stroke="#ef4444"
        stroke-width="2"
        stroke-dasharray="5,5"
        marker-end="url(#loopback-arrow)"
        opacity="0.6"
        class="animated-dash"
    />
</g>

<style>
    .animated-dash {
        animation: dash-animation 1s linear infinite;
    }

    @keyframes dash-animation {
        from {
            stroke-dashoffset: 10;
        }
        to {
            stroke-dashoffset: 0;
        }
    }
</style>
