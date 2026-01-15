<script lang="ts">
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import type { TodoItem, ConditionStatus } from "$lib/types/phenomenon";

    export let todo: TodoItem;
    export let todoIndex: number;
    export let isDragging = false;
    export let isDragOver = false;
    export let isEditing = false;
    export let editingText = "";
    export let actionCaptureMode = false;
    export let actionCaptureTodoId: string | null = null;
    export let expandedCapturesTodoId: string | null = null;

    const dispatch = createEventDispatcher<{
        dragstart: { event: DragEvent; todoId: string };
        dragover: { event: DragEvent; todoId: string };
        dragleave: DragEvent;
        drop: { event: DragEvent; todoId: string };
        dragend: void;
        startEdit: TodoItem;
        saveEdit: void;
        cancelEdit: void;
        editKeydown: KeyboardEvent;
        editTextChange: string;
        remove: string;
        toggleConditionStatus: { todoId: string; status: ConditionStatus };
        toggleActionCapture: string;
        toggleCapturesExpand: string;
        removeCapture: { todoId: string; captureId: string };
    }>();

    function getCaptureCount(): number {
        return todo.captures?.length || 0;
    }
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="relative pl-4 border-l-2 {todo.type === 'condition' ? 'border-orange-300' : 'border-blue-300'} ml-1 transition-all duration-150
           {isDragging ? 'opacity-50' : ''}
           {isDragOver ? 'border-l-4 bg-blue-50' : ''}"
    draggable="true"
    on:dragstart={(e) => dispatch("dragstart", { event: e, todoId: todo.id })}
    on:dragover={(e) => dispatch("dragover", { event: e, todoId: todo.id })}
    on:dragleave={(e) => dispatch("dragleave", e)}
    on:drop={(e) => dispatch("drop", { event: e, todoId: todo.id })}
    on:dragend={() => dispatch("dragend")}
>
    <div class="flex items-start justify-between group">
        <!-- Drag handle -->
        <div class="flex-shrink-0 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 mr-1 mt-0.5">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <circle cx="9" cy="5" r="1.5" /><circle cx="15" cy="5" r="1.5" />
                <circle cx="9" cy="12" r="1.5" /><circle cx="15" cy="12" r="1.5" />
                <circle cx="9" cy="19" r="1.5" /><circle cx="15" cy="19" r="1.5" />
            </svg>
        </div>

        <div class="text-xs flex-1">
            <div class="flex items-center gap-1.5 mb-0.5">
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase {todo.type === 'condition' ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'}">
                    {todo.type === "condition" ? "Condition" : "Action"}
                </span>
            </div>

            {#if isEditing}
                <input
                    type="text"
                    value={editingText}
                    class="w-full text-xs border border-gray-300 rounded px-1 py-0.5 focus:border-purple-500 focus:outline-none"
                    on:keydown={(e) => dispatch("editKeydown", e)}
                    on:blur={() => dispatch("saveEdit")}
                    on:input={(e) => dispatch("editTextChange", e.currentTarget.value)}
                />
            {:else}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <div
                    class="text-gray-800 leading-snug cursor-pointer hover:bg-gray-100 rounded px-1 -mx-1"
                    on:click={() => dispatch("startEdit", todo)}
                    title="클릭하여 수정"
                >
                    {todo.text}
                </div>

                {#if todo.paramValues && Object.keys(todo.paramValues).length > 0}
                    <div class="mt-1 space-y-0.5 pl-1 border-l-2 border-gray-200">
                        {#each Object.entries(todo.paramValues) as [paramId, paramValue]}
                            {#if paramValue}
                                <div class="text-[10px] text-gray-600">
                                    <span class="font-medium">{paramId}:</span>
                                    <span class="text-gray-800">{paramValue}</span>
                                </div>
                            {/if}
                        {/each}
                    </div>
                {/if}
            {/if}

            <!-- Condition Status Toggle -->
            {#if todo.type === "condition"}
                <div class="mt-1.5 flex items-center gap-2">
                    <div class="flex items-center gap-1 bg-gray-100 rounded-full p-0.5">
                        <button
                            type="button"
                            class="px-2 py-0.5 text-[10px] font-bold rounded-full transition-all
                                   {todo.conditionStatus === 'true' ? 'bg-green-500 text-white shadow-sm' : 'text-gray-500 hover:text-green-600 hover:bg-green-50'}"
                            on:click|stopPropagation={() => dispatch("toggleConditionStatus", { todoId: todo.id, status: 'true' })}
                            title="True: 탐색 계속 (Active)"
                        >
                            True
                        </button>
                        <button
                            type="button"
                            class="px-2 py-0.5 text-[10px] font-bold rounded-full transition-all
                                   {todo.conditionStatus === 'false' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-500 hover:text-red-600 hover:bg-red-50'}"
                            on:click|stopPropagation={() => dispatch("toggleConditionStatus", { todoId: todo.id, status: 'false' })}
                            title="False: 탐색 종료 (Inactive)"
                        >
                            False
                        </button>
                    </div>
                    {#if todo.conditionStatus === 'true'}
                        <span class="text-[10px] text-green-600 font-medium">탐색중</span>
                    {:else if todo.conditionStatus === 'false'}
                        <span class="text-[10px] text-red-500 font-medium">탐색종료</span>
                    {:else}
                        <span class="text-[10px] text-gray-400">미설정</span>
                    {/if}
                </div>
            {/if}

            <!-- Action Captures -->
            {#if todo.type === "action"}
                <div class="mt-1.5 flex items-center gap-2 flex-wrap">
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded transition-colors
                               {actionCaptureMode && actionCaptureTodoId === todo.id
                            ? 'bg-gray-600 text-white ring-2 ring-gray-400'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
                        on:click|stopPropagation={() => dispatch("toggleActionCapture", todo.id)}
                        title={actionCaptureMode && actionCaptureTodoId === todo.id ? '캡처 모드 종료' : '캡처 모드 시작'}
                    >
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        {actionCaptureMode && actionCaptureTodoId === todo.id ? '캡처 중...' : '+ 캡처'}
                    </button>

                    {#if getCaptureCount() > 0}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
                            on:click|stopPropagation={() => dispatch("toggleCapturesExpand", todo.id)}
                            title="캡처 목록 보기"
                        >
                            캡처 {getCaptureCount()}개
                            <svg class="w-2.5 h-2.5 transition-transform {expandedCapturesTodoId === todo.id ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>
                    {/if}

                    <!-- Inline capture preview -->
                    {#if todo.captures && todo.captures.length > 0 && expandedCapturesTodoId !== todo.id}
                        {#each todo.captures.slice(0, 3) as capture, capIdx (capture.id)}
                            <span
                                class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] rounded bg-gray-200 text-gray-600 border border-gray-300"
                                title={capture.label || `슬라이드 ${capture.slideIndex + 1} - #${capIdx + 1}`}
                            >
                                <span class="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                                {capture.label || `S${capture.slideIndex + 1}-${capIdx + 1}`}
                            </span>
                        {/each}
                        {#if todo.captures.length > 3}
                            <span class="text-[9px] text-gray-400">+{todo.captures.length - 3}</span>
                        {/if}
                    {/if}
                </div>

                <!-- Expanded captures list -->
                {#if expandedCapturesTodoId === todo.id && todo.captures && todo.captures.length > 0}
                    <div class="mt-2 p-2 bg-gray-50 rounded border border-gray-200" transition:slide>
                        <div class="text-[9px] font-bold text-gray-500 uppercase mb-1.5">연관 캡처 목록</div>
                        <div class="flex flex-wrap gap-1">
                            {#each todo.captures as capture, idx (capture.id)}
                                <div class="inline-flex items-center gap-1 px-1.5 py-1 text-[10px] rounded bg-gray-200 border border-gray-300 text-gray-700 group">
                                    <span class="w-2 h-2 rounded-full bg-gray-500 shrink-0"></span>
                                    <span class="truncate max-w-[100px]" title={capture.label || `슬라이드 ${capture.slideIndex + 1} - 캡처 #${idx + 1}`}>
                                        {capture.label || `슬라이드 ${capture.slideIndex + 1} - 캡처 #${idx + 1}`}
                                    </span>
                                    <button
                                        type="button"
                                        class="ml-0.5 text-gray-400 hover:text-red-500 transition-colors"
                                        on:click|stopPropagation={() => dispatch("removeCapture", { todoId: todo.id, captureId: capture.id })}
                                        title="캡처 삭제"
                                    >
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Capture mode indicator -->
                {#if actionCaptureMode && actionCaptureTodoId === todo.id}
                    <div class="mt-2 p-2 bg-gray-100 border border-gray-300 rounded text-[10px] text-gray-600 flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full bg-gray-500 animate-pulse"></div>
                        슬라이드에서 캡처할 영역을 드래그하세요
                    </div>
                {/if}
            {/if}
        </div>

        <!-- Remove button -->
        <button
            class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
            on:click={() => dispatch("remove", todo.id)}
            aria-label="Remove todo item"
        >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    </div>
</div>
