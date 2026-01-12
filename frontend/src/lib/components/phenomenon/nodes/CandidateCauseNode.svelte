<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import type { TodoItem } from "$lib/types/phenomenon";

    export let data: {
        label: string;
        todoList: (TodoItem & { parameters?: Record<string, unknown> })[];
        linkedEvidenceCount: number;
    };
</script>

<div class="cause-node">
    <Handle type="target" position={Position.Left} />

    <div class="header">
        <span class="title">{data.label}</span>
        {#if data.linkedEvidenceCount > 0}
            <span class="link-count">{data.linkedEvidenceCount}개 근거</span>
        {/if}
    </div>

    {#if data.todoList && data.todoList.length > 0}
        <div class="todo-list">
            <div class="todo-header">행동 정의</div>
            {#each data.todoList.slice(0, 3) as todo}
                <div class="todo-wrapper">
                    <div class="todo-item {todo.type} {todo.type === 'condition' && todo.conditionStatus === 'false' ? 'inactive' : ''}">
                        <span class="todo-type">
                            {todo.type === "condition" ? "C" : "A"}
                        </span>
                        <span class="todo-text">{todo.text}</span>
                        {#if todo.type === "condition" && todo.conditionStatus}
                            <span class="condition-status {todo.conditionStatus === 'true' ? 'active' : 'inactive'}">
                                {todo.conditionStatus === 'true' ? 'T' : 'F'}
                            </span>
                        {/if}
                    </div>

                    {#if todo.parameters && Object.keys(todo.parameters).length > 0}
                        <div class="parameters {todo.type === 'condition' && todo.conditionStatus === 'false' ? 'inactive' : ''}">
                            {#each Object.entries(todo.parameters) as [key, value]}
                                <div class="param-row">
                                    <span class="param-key">{key}:</span>
                                    <span class="param-value">{value}</span>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/each}
            {#if data.todoList.length > 3}
                <div class="more">+{data.todoList.length - 3}개 더</div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .cause-node {
        min-width: 260px;
        max-width: 300px;
        padding: 12px;
        border-radius: 8px;
        border: 2px solid #3b82f6;
        background: #eff6ff;
        font-size: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .header {
        display: flex;
        align-items: baseline;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 4px;
    }
    .title {
        font-weight: 600;
        color: #1e40af;
        line-height: 1.3;
    }
    .link-count {
        font-size: 10px;
        color: #6b7280;
        white-space: nowrap;
    }

    .todo-list {
        border-top: 1px solid #bfdbfe;
        padding-top: 8px;
        margin-top: 4px;
    }
    .todo-header {
        font-size: 10px;
        font-weight: bold;
        color: #6b7280;
        margin-bottom: 6px;
    }

    .todo-wrapper {
        margin-bottom: 8px;
        display: flex;
        flex-direction: column;
    }

    .todo-item {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        font-size: 11px;
    }
    .todo-type {
        flex-shrink: 0;
        width: 16px;
        height: 16px;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: bold;
    }
    .todo-item.action .todo-type {
        background: #dbeafe;
        color: #2563eb;
    }
    .todo-item.condition .todo-type {
        background: #ffedd5;
        color: #ea580c;
    }
    .todo-item.inactive {
        opacity: 0.5;
    }
    .todo-item.inactive .todo-text {
        text-decoration: line-through;
    }
    .todo-text {
        color: #374151;
        line-height: 1.3;
        font-weight: 500;
        flex: 1;
    }

    .parameters {
        margin-left: 22px;
        margin-top: 2px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 4px;
        padding: 2px 4px;
    }
    .parameters.inactive {
        opacity: 0.5;
    }
    .param-row {
        font-size: 10px;
        color: #4b5563;
        display: flex;
        gap: 4px;
        line-height: 1.4;
    }
    .param-key {
        color: #6b7280;
    }
    .param-value {
        font-family: monospace;
        color: #0369a1;
        font-weight: 500;
    }

    .condition-status {
        flex-shrink: 0;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 8px;
        font-weight: bold;
    }
    .condition-status.active {
        background: #22c55e;
        color: white;
    }
    .condition-status.inactive {
        background: #ef4444;
        color: white;
    }
    .more {
        font-size: 10px;
        color: #9ca3af;
        font-style: italic;
        margin-top: 4px;
        text-align: center;
    }
</style>
