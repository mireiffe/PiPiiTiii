<script lang="ts">
    import { createEventDispatcher } from "svelte";

    interface AttributeDefinition {
        key: string;
        display_name: string;
        attr_type: {
            variant: string;
        };
    }

    export let availableAttributes: AttributeDefinition[] = [];
    export let selectedAttributes: string[] = [];

    const dispatch = createEventDispatcher<{
        toggle: { key: string };
    }>();
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="mb-4">
        <h2 class="text-xl font-bold text-gray-800">발생현상 속성</h2>
        <p class="text-sm text-gray-500 mt-1">
            발생현상 수집 시 자동으로 포함될 PPT 속성을 선택합니다.
        </p>
    </div>

    <div class="space-y-2">
        {#if availableAttributes.length === 0}
            <div class="text-center text-gray-400 py-8">
                정의된 속성이 없습니다.
            </div>
        {:else}
            {#each availableAttributes as attr (attr.key)}
                <label
                    class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors {selectedAttributes.includes(attr.key)
                        ? 'bg-blue-50 border-blue-300'
                        : 'bg-gray-50 border-gray-200 hover:bg-gray-100'}"
                >
                    <input
                        type="checkbox"
                        checked={selectedAttributes.includes(attr.key)}
                        on:change={() => dispatch("toggle", { key: attr.key })}
                        class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <div class="flex-1">
                        <div class="font-medium text-gray-800">{attr.display_name}</div>
                        <div class="text-xs text-gray-500">{attr.key}</div>
                    </div>
                    <span class="text-xs px-2 py-1 bg-gray-200 text-gray-600 rounded">
                        {attr.attr_type.variant}
                    </span>
                </label>
            {/each}
        {/if}
    </div>
</div>
