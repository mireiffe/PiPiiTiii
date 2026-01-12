<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";

    export let data: {
        label: string;
        index: number;
        color: { bg: string; border: string; name: string };
        evidenceType: "capture" | "attribute";
        slideIndex?: number;
        attributeValue?: string;
        description?: string;
    };

    // Capture: use colorful palette, Attribute: unified slate color
    $: isCapture = data.evidenceType === "capture";
    $: nodeStyle = isCapture
        ? `border-color: ${data.color.border}; background: ${data.color.bg};`
        : `border-color: #94a3b8; background: rgba(241, 245, 249, 0.9);`;
    $: badgeColor = isCapture ? data.color.border : "#64748b";
</script>

{#if isCapture}
    <!-- Capture Node: Full card style -->
    <div class="evidence-node capture-node" style={nodeStyle}>
        <div class="flex items-center gap-2">
            <div class="badge" style="background-color: {badgeColor};">
                {data.index + 1}
            </div>
            <div class="content">
                <span class="label">{data.label}</span>
                {#if data.slideIndex !== undefined}
                    <span class="meta">슬라이드 {data.slideIndex + 1}</span>
                {/if}
                {#if data.description}
                    <span class="description">{data.description}</span>
                {/if}
            </div>
        </div>
        <Handle type="source" position={Position.Right} />
    </div>
{:else}
    <!-- Attribute Node: Compact list-style -->
    <div class="evidence-node attr-node" style={nodeStyle}>
        <div class="attr-content">
            <svg
                class="w-3.5 h-3.5 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                ></path></svg
            >
            <span class="attr-label">{data.label}</span>
            {#if data.attributeValue}
                <span class="attr-value">{data.attributeValue}</span>
            {/if}
        </div>
        <Handle type="source" position={Position.Right} />
    </div>
{/if}

<style>
    .evidence-node {
        min-width: 180px;
        max-width: 240px;
        border-radius: 8px;
        border: 2px solid;
        font-size: 12px;
        background: white;
    }

    /* Capture Node: Full card */
    .capture-node {
        padding: 10px 12px;
    }
    .capture-node .badge {
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
    .capture-node .content {
        flex: 1;
        min-width: 0;
    }
    .capture-node .label {
        font-weight: 500;
        color: #374151;
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .capture-node .meta {
        font-size: 10px;
        color: #6b7280;
        display: block;
        margin-top: 2px;
    }
    .capture-node .description {
        font-size: 10px;
        color: #4b5563;
        display: block;
        margin-top: 4px;
        padding-top: 4px;
        border-top: 1px dashed #d1d5db;
        line-height: 1.3;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    /* Attribute Node: Compact list-style */
    .attr-node {
        padding: 6px 10px;
        border-radius: 6px;
        border-width: 1.5px;
        background: rgba(241, 245, 249, 0.95);
    }
    .attr-content {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .attr-icon {
        font-size: 12px;
        flex-shrink: 0;
    }
    .attr-label {
        font-weight: 500;
        color: #475569;
        font-size: 11px;
        flex-shrink: 0;
    }
    .attr-value {
        font-size: 11px;
        color: #0f766e;
        font-family: monospace;
        background: rgba(255, 255, 255, 0.8);
        padding: 1px 5px;
        border-radius: 3px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 120px;
    }
</style>
