<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";

    export let data: {
        stepIndex: number;
        category: string;
        purpose: string;
        system: string;
        target: string;
        expectedResult: string;
        captureCount: number;
        attachmentCount: number;
        color: {
            bg: string;
            border: string;
            text: string;
            line: string;
        };
        isLeft: boolean;
    };

    $: hasMetadata = data.captureCount > 0 || data.attachmentCount > 0;
    $: hasDetails = data.system || data.target;
</script>

<div
    class="timeline-node"
    style="
        --node-bg: {data.color.bg};
        --node-border: {data.color.border};
        --node-text: {data.color.text};
    "
    class:is-left={data.isLeft}
>
    <!-- Connection handle -->
    <Handle
        type="target"
        position={data.isLeft ? Position.Right : Position.Left}
        style="background: {data.color.border}; width: 8px; height: 8px; border: 2px solid white;"
    />
    <Handle
        type="source"
        position={data.isLeft ? Position.Right : Position.Left}
        style="background: {data.color.border}; width: 8px; height: 8px; border: 2px solid white;"
    />

    <!-- Header with category badge and step number -->
    <div class="node-header">
        <span class="category-badge" style="background: {data.color.border};">
            {data.category}
        </span>
        <span class="step-number">#{data.stepIndex + 1}</span>
    </div>

    <!-- Purpose / Main content -->
    <div class="node-purpose">
        {data.purpose}
    </div>

    <!-- Details row -->
    {#if hasDetails}
        <div class="node-details">
            {#if data.system}
                <span class="detail-item system">
                    <svg class="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                        <line x1="8" y1="21" x2="16" y2="21"/>
                        <line x1="12" y1="17" x2="12" y2="21"/>
                    </svg>
                    {data.system}
                </span>
            {/if}
            {#if data.target}
                <span class="detail-item target">
                    <svg class="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <circle cx="12" cy="12" r="6"/>
                        <circle cx="12" cy="12" r="2"/>
                    </svg>
                    {data.target}
                </span>
            {/if}
        </div>
    {/if}

    <!-- Metadata badges (captures, attachments) -->
    {#if hasMetadata}
        <div class="node-metadata">
            {#if data.captureCount > 0}
                <span class="meta-badge capture">
                    <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21,15 16,10 5,21"/>
                    </svg>
                    {data.captureCount}
                </span>
            {/if}
            {#if data.attachmentCount > 0}
                <span class="meta-badge attachment">
                    <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                    </svg>
                    {data.attachmentCount}
                </span>
            {/if}
        </div>
    {/if}
</div>

<style>
    .timeline-node {
        background: var(--node-bg);
        border: 2px solid var(--node-border);
        border-radius: 12px;
        padding: 12px 14px;
        width: 260px;
        min-height: 80px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .timeline-node:hover {
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.06);
        transform: translateY(-2px);
    }

    .node-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .category-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
        color: white;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }

    .step-number {
        font-size: 11px;
        font-weight: 600;
        color: var(--node-text);
        opacity: 0.6;
    }

    .node-purpose {
        font-size: 13px;
        font-weight: 600;
        color: var(--node-text);
        line-height: 1.4;
        margin-bottom: 8px;
        word-break: keep-all;
    }

    .node-details {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 8px;
    }

    .detail-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        background: rgba(255, 255, 255, 0.6);
        border-radius: 4px;
        font-size: 10px;
        color: #64748b;
    }

    .detail-icon {
        width: 12px;
        height: 12px;
        flex-shrink: 0;
    }

    .node-metadata {
        display: flex;
        gap: 8px;
        padding-top: 8px;
        border-top: 1px solid rgba(0, 0, 0, 0.06);
    }

    .meta-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }

    .meta-badge.capture {
        background: rgba(59, 130, 246, 0.15);
        color: #2563eb;
    }

    .meta-badge.attachment {
        background: rgba(245, 158, 11, 0.15);
        color: #d97706;
    }

    .meta-icon {
        width: 12px;
        height: 12px;
        flex-shrink: 0;
    }

    /* Subtle arrow indicator pointing to timeline */
    .timeline-node::before {
        content: '';
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        width: 0;
        height: 0;
        border: 8px solid transparent;
    }

    .timeline-node.is-left::before {
        right: -16px;
        border-left-color: var(--node-border);
    }

    .timeline-node:not(.is-left)::before {
        left: -16px;
        border-right-color: var(--node-border);
    }
</style>
