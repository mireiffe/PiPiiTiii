<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";

    export let data: {
        label: string;
        index: number;
        color: { bg: string; border: string; name: string };
        evidenceType: "capture" | "attribute";
        slideIndex?: number;
        attributeValue?: string;
    };
</script>

<div
    class="evidence-node"
    style="border-color: {data.color.border}; background: {data.color.bg};"
>
    <div class="flex items-center gap-2">
        <div class="badge" style="background-color: {data.color.border};">
            {data.index + 1}
        </div>
        <div class="content">
            <span class="label">{data.label}</span>
            {#if data.evidenceType === "capture" && data.slideIndex !== undefined}
                <span class="meta">슬라이드 {data.slideIndex + 1}</span>
            {:else if data.evidenceType === "attribute" && data.attributeValue}
                <span class="attr-value">{data.attributeValue}</span>
            {/if}
        </div>
    </div>
    <Handle type="source" position={Position.Right} />
</div>

<style>
    .evidence-node {
        min-width: 180px;
        max-width: 220px;
        padding: 10px 12px;
        border-radius: 8px;
        border: 2px solid;
        font-size: 12px;
        background: white;
    }
    .badge {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 10px;
        font-weight: bold;
    }
    .content {
        flex: 1;
        min-width: 0;
    }
    .label {
        font-weight: 500;
        color: #374151;
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .meta {
        font-size: 10px;
        color: #9ca3af;
        display: block;
        margin-top: 2px;
    }
    .attr-value {
        font-size: 11px;
        color: #0369a1;
        font-family: monospace;
        display: block;
        margin-top: 2px;
        background: rgba(255, 255, 255, 0.6);
        padding: 2px 4px;
        border-radius: 3px;
        word-break: break-all;
    }
</style>
