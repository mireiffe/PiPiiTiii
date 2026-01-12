<script lang="ts">
    import { Handle, Position } from "@xyflow/svelte";
    import type { TodoItem } from "$lib/types/phenomenon";

    export let data: {
        label: string;
        todoList: TodoItem[];
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
            {/each}
            {#if data.todoList.length > 3}
                <div class="more">+{data.todoList.length - 3}개 더</div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .cause-node {
        min-width: 200px;
        max-width: 250px;
        padding: 12px;
        border-radius: 8px;
        border: 2px solid #3b82f6;
        background: #eff6ff;
        font-size: 12px;
    }
    .header {
        display: flex;
        align-items: baseline;
        gap: 8px;
        flex-wrap: wrap;
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
        margin-top: 8px;
    }
    .todo-header {
        font-size: 10px;
        font-weight: bold;
        color: #6b7280;
        margin-bottom: 6px;
    }
    .todo-item {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        margin-bottom: 4px;
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
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        flex: 1;
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
    }
</style>
