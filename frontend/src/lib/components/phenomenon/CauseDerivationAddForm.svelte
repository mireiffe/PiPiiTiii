<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { TodoType } from "$lib/types/phenomenon";

    export let isAddingTodo = false;
    export let newTodoType: TodoType = "action";
    export let newTodoText = "";
    export let predefinedItems: { id: string; name: string; params: any[] }[] = [];
    export let selectedPredefinedItem: { id: string; name: string; params: any[] } | null = null;
    export let paramValues: Record<string, string> = {};

    const dispatch = createEventDispatcher<{
        startAdd: TodoType;
        cancel: void;
        save: void;
        selectItem: { id: string; name: string; params: any[] };
        textChange: string;
        paramChange: { paramId: string; value: string };
    }>();

    function handleKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            dispatch("save");
        } else if (e.key === "Escape") {
            dispatch("cancel");
        }
    }
</script>

{#if isAddingTodo}
    <div class="bg-white border border-gray-300 rounded p-2 shadow-sm animate-fadeIn">
        <div class="text-[10px] font-bold mb-1 {newTodoType === 'condition' ? 'text-orange-600' : 'text-blue-600'}">
            {newTodoType === "condition" ? "새 조건 (Condition) 추가" : "새 행동 (Action) 추가"}
        </div>

        <!-- Predefined options -->
        {#if predefinedItems.length > 0}
            <div class="mb-2">
                <div class="text-[10px] text-gray-500 mb-1">미리 정의된 항목:</div>
                <div class="flex flex-wrap gap-1">
                    {#each predefinedItems as item}
                        <button
                            type="button"
                            class="px-2 py-0.5 text-[10px] rounded border transition-colors
                                {newTodoText === item.name
                                    ? (newTodoType === 'condition'
                                        ? 'bg-orange-100 border-orange-400 text-orange-700'
                                        : 'bg-blue-100 border-blue-400 text-blue-700')
                                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'}"
                            on:click={() => dispatch("selectItem", item)}
                        >
                            {item.name}
                        </button>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Parameter inputs -->
        {#if selectedPredefinedItem && selectedPredefinedItem.params && selectedPredefinedItem.params.length > 0}
            <div class="mb-2 space-y-2 border-t border-gray-200 pt-2">
                <div class="text-[10px] text-gray-500 font-medium">파라미터:</div>
                {#each selectedPredefinedItem.params as param}
                    <div class="space-y-1">
                        <label class="text-[10px] text-gray-600 flex items-center gap-1">
                            {param.name}
                            {#if param.required}<span class="text-red-500">*</span>{/if}
                        </label>
                        {#if param.param_type === 'selection' && param.selection_values && param.selection_values.length > 0}
                            <select
                                value={paramValues[param.id] || ""}
                                class="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:border-purple-500 focus:outline-none"
                                on:change={(e) => dispatch("paramChange", { paramId: param.id, value: e.currentTarget.value })}
                            >
                                <option value="">선택하세요...</option>
                                {#each param.selection_values as value}
                                    <option value={value}>{value}</option>
                                {/each}
                            </select>
                        {:else}
                            <input
                                type="text"
                                value={paramValues[param.id] || ""}
                                class="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:border-purple-500 focus:outline-none"
                                placeholder="값을 입력하세요..."
                                on:input={(e) => dispatch("paramChange", { paramId: param.id, value: e.currentTarget.value })}
                            />
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}

        <!-- Text input -->
        <div class="text-[10px] text-gray-500 mb-1">
            {predefinedItems.length > 0 && !selectedPredefinedItem ? "또는 직접 입력:" : selectedPredefinedItem ? "이름 (수정 가능):" : ""}
        </div>
        <input
            type="text"
            value={newTodoText}
            class="w-full text-xs border-b border-gray-200 focus:border-purple-500 focus:outline-none py-1 mb-2"
            placeholder={newTodoType === "condition" ? "예: 전압이 5V 이상인가?" : "예: 보드를 재부팅한다."}
            on:keydown={handleKeyDown}
            on:input={(e) => dispatch("textChange", e.currentTarget.value)}
        />

        <div class="flex justify-end gap-2 text-[10px]">
            <button class="px-2 py-1 text-gray-500 hover:text-gray-700" on:click={() => dispatch("cancel")}>
                취소
            </button>
            <button class="px-2 py-1 bg-purple-500 text-white rounded hover:bg-purple-600" on:click={() => dispatch("save")}>
                추가
            </button>
        </div>
    </div>
{:else}
    <div class="flex gap-2 mt-2">
        <button
            class="flex-1 py-1.5 border border-dashed border-blue-300 text-blue-600 hover:bg-blue-50 rounded text-xs gap-1 flex items-center justify-center transition-colors"
            on:click={() => dispatch("startAdd", "action")}
        >
            <span class="font-bold">+</span> Action
        </button>
        <button
            class="flex-1 py-1.5 border border-dashed border-orange-300 text-orange-600 hover:bg-orange-50 rounded text-xs gap-1 flex items-center justify-center transition-colors"
            on:click={() => dispatch("startAdd", "condition")}
        >
            <span class="font-bold">+</span> Condition
        </button>
    </div>
{/if}

<style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-fadeIn {
        animation: fadeIn 0.15s ease-out forwards;
    }
</style>
