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
            <span class="link-count badge">{data.linkedEvidenceCount}개 근거</span>
        {/if}
    </div>

    {#if data.todoList && data.todoList.length > 0}
        <div class="todo-list">
            <div class="todo-header">행동 정의</div>
            {#each data.todoList.slice(0, 3) as todo}
                <div class="todo-block">
                    <div class="todo-item {todo.type} {todo.type === 'condition' && todo.conditionStatus === 'false' ? 'inactive' : ''}">
                        <span class="todo-type">
                            {todo.type === "condition" ? "C" : "A"}
                        </span>
                        <span class="todo-text" title={todo.text}>{todo.text}</span>
                        {#if todo.type === "condition" && todo.conditionStatus}
                            <span class="condition-status {todo.conditionStatus === 'true' ? 'active' : 'inactive'}">
                                {todo.conditionStatus === 'true' ? 'T' : 'F'}
                            </span>
                        {/if}
                    </div>

                    {#if todo.parameters && Object.keys(todo.parameters).length > 0}
                        <div class="todo-params">
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
        width: 280px;
        padding: 12px;
        border-radius: 8px;
        border: 2px solid #3b82f6;
        background: #ffffff;
        font-size: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid #e5e7eb;
    }
    .title {
        font-weight: 700;
        color: #1e40af;
        line-height: 1.3;
        font-size: 13px;
    }
    .badge {
        font-size: 10px;
        background: #eff6ff;
        color: #3b82f6;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
        white-space: nowrap;
    }

    .todo-list {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .todo-header {
        font-size: 10px;
        font-weight: bold;
        color: #64748b;
        margin-bottom: 2px;
    }

    .todo-block {
        display: flex;
        flex-direction: column;
        gap: 2px;
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
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: 800;
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
        color: #334155;
        font-weight: 500;
        line-height: 1.4;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .todo-params {
        margin-left: 22px;
        padding: 4px;
        background: #f8fafc;
        border-radius: 4px;
        border: 1px solid #f1f5f9;
    }
    .param-row {
        display: flex;
        gap: 4px;
        font-size: 10px;
        line-height: 1.4;
        color: #475569;
    }
    .param-key {
        color: #64748b;
        font-weight: 500;
    }
    .param-value {
        color: #0369a1;
        font-family: monospace;
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
        color: #94a3b8;
        font-style: italic;
        text-align: center;
        margin-top: 4px;
        text-align: center;
    }
</style>
