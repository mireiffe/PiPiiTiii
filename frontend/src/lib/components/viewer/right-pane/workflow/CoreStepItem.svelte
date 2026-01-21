<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        CoreStepInstance,
        CoreStepDefinition,
        CoreStepPreset
    } from "$lib/types/workflow";
    import { getInputTypeDisplayName } from "$lib/types/workflow";
    import { getAttachmentImageUrl } from "$lib/api/project";

    export let instance: CoreStepInstance;
    export let definition: CoreStepDefinition;
    export let displayNumber: number;
    export let isExpanded = false;

    const dispatch = createEventDispatcher<{
        toggleExpand: void;
        remove: void;
        moveUp: void;
        moveDown: void;
    }>();

    function getPresetDefinition(presetId: string): CoreStepPreset | undefined {
        return definition.presets.find(p => p.id === presetId);
    }

    function getPresetValueDisplay(presetValue: typeof instance.presetValues[0]): string {
        const presetDef = getPresetDefinition(presetValue.presetId);
        const name = presetDef?.name || '알 수 없음';

        switch (presetValue.type) {
            case 'text':
                return `${name}: ${presetValue.textValue || ''}`;
            case 'capture':
                if (presetValue.captureValue) {
                    return `${name}: 슬라이드 ${presetValue.captureValue.slideIndex + 1} 캡처`;
                }
                return `${name}: (캡처 없음)`;
            case 'image_clipboard':
                return `${name}: 이미지 첨부됨`;
            default:
                return name;
        }
    }
</script>

<div class="relative z-10 pl-4">
    <!-- Number Badge -->
    <div
        class="absolute left-0 top-3 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-md z-20 border-2 border-purple-300"
    >
        C{displayNumber}
    </div>

    <!-- Card -->
    <div
        class="ml-6 bg-white rounded-lg border border-purple-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        on:click={() => dispatch('toggleExpand')}
        role="button"
        tabindex="0"
        on:keydown={(e) => e.key === 'Enter' && dispatch('toggleExpand')}
    >
        <!-- Header -->
        <div class="px-3 py-2 flex items-center gap-2">
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded">
                        Core
                    </span>
                    <span class="text-sm font-medium text-gray-800 truncate">
                        {definition.name}
                    </span>
                </div>
                {#if !isExpanded && instance.presetValues.length > 0}
                    <p class="text-xs text-gray-500 truncate mt-0.5">
                        {instance.presetValues.map(pv => {
                            const preset = getPresetDefinition(pv.presetId);
                            if (pv.type === 'text') return `${preset?.name}: ${pv.textValue?.substring(0, 20)}...`;
                            return preset?.name;
                        }).join(', ')}
                    </p>
                {/if}
            </div>

            <div class="flex items-center gap-1">
                <button
                    class="p-1 text-gray-400 hover:text-gray-600 transition"
                    on:click|stopPropagation={() => dispatch('moveUp')}
                    title="위로 이동"
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                </button>
                <button
                    class="p-1 text-gray-400 hover:text-gray-600 transition"
                    on:click|stopPropagation={() => dispatch('moveDown')}
                    title="아래로 이동"
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
                <button
                    class="p-1 text-gray-400 hover:text-red-500 transition"
                    on:click|stopPropagation={() => dispatch('remove')}
                    title="삭제"
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                </button>
                <svg
                    class="w-4 h-4 text-gray-400 transition-transform {isExpanded ? 'rotate-180' : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
            </div>
        </div>

        <!-- Expanded Content -->
        {#if isExpanded}
            <div class="px-3 pb-3 border-t border-purple-100 pt-2 space-y-2">
                {#each instance.presetValues as presetValue (presetValue.presetId)}
                    {@const presetDef = getPresetDefinition(presetValue.presetId)}
                    <div class="bg-purple-50/50 rounded-lg p-2 border border-purple-100">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xs font-medium text-purple-700">{presetDef?.name || '알 수 없음'}</span>
                            <span class="text-xs text-gray-400">({getInputTypeDisplayName(presetValue.type)})</span>
                        </div>

                        {#if presetValue.type === 'text'}
                            <p class="text-xs text-gray-700 whitespace-pre-wrap break-words">
                                {presetValue.textValue || '(비어있음)'}
                            </p>
                        {:else if presetValue.type === 'capture' && presetValue.captureValue}
                            <div class="flex items-center gap-2 text-xs text-gray-600">
                                <svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span>슬라이드 {presetValue.captureValue.slideIndex + 1}</span>
                                <span class="text-gray-400">
                                    ({Math.round(presetValue.captureValue.width)}x{Math.round(presetValue.captureValue.height)})
                                </span>
                            </div>
                        {:else if presetValue.type === 'image_clipboard' && presetValue.imageId}
                            <img
                                src={getAttachmentImageUrl(presetValue.imageId)}
                                alt="첨부된 이미지"
                                class="w-full max-h-32 object-contain rounded border border-gray-200"
                            />
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>
