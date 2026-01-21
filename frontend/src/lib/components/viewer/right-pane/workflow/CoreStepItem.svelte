<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        CoreStepInstance,
        CoreStepDefinition,
        CoreStepPreset,
        CoreStepPresetValue,
        CoreStepInputType
    } from "$lib/types/workflow";
    import { getInputTypeDisplayName, generateAttachmentId } from "$lib/types/workflow";
    import { getAttachmentImageUrl, uploadAttachmentImage } from "$lib/api/project";

    export let instance: CoreStepInstance;
    export let definition: CoreStepDefinition;
    export let displayNumber: number;
    export let isExpanded = false;
    export let projectId: string = "";

    const dispatch = createEventDispatcher<{
        toggleExpand: void;
        remove: void;
        moveUp: void;
        moveDown: void;
        update: { instance: CoreStepInstance };
        startCapture: { presetId: string };
    }>();

    let isUploading = false;

    function getPresetDefinition(presetId: string): CoreStepPreset | undefined {
        return definition.presets.find(p => p.id === presetId);
    }

    function getPresetValue(presetId: string): CoreStepPresetValue | undefined {
        return instance.presetValues.find(pv => pv.presetId === presetId);
    }

    function getPreviewText(): string {
        const filledPresets = instance.presetValues.filter(pv => {
            if (pv.type === 'text') return pv.textValue && pv.textValue.trim().length > 0;
            if (pv.type === 'capture') return pv.captureValue !== null;
            if (pv.type === 'image_clipboard') return pv.imageId !== null;
            return false;
        });

        if (filledPresets.length === 0) {
            return '(입력 필요)';
        }

        return filledPresets.map(pv => {
            const preset = getPresetDefinition(pv.presetId);
            if (pv.type === 'text' && pv.textValue) {
                const truncated = pv.textValue.length > 15 ? pv.textValue.substring(0, 15) + '...' : pv.textValue;
                return `${preset?.name}: ${truncated}`;
            }
            if (pv.type === 'capture') return `${preset?.name}: 캡처`;
            if (pv.type === 'image_clipboard') return `${preset?.name}: 이미지`;
            return preset?.name;
        }).join(', ');
    }

    function selectInputType(presetId: string, type: CoreStepInputType) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx] = {
                ...instance.presetValues[idx],
                type,
                textValue: type === 'text' ? (instance.presetValues[idx].textValue || '') : undefined,
                captureValue: type === 'capture' ? instance.presetValues[idx].captureValue : undefined,
                imageId: type === 'image_clipboard' ? instance.presetValues[idx].imageId : undefined,
            };
        } else {
            instance.presetValues = [...instance.presetValues, {
                presetId,
                type,
                textValue: type === 'text' ? '' : undefined,
            }];
        }
        instance = { ...instance };
        dispatch('update', { instance });
    }

    function updateTextValue(presetId: string, value: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].textValue = value;
        } else {
            instance.presetValues = [...instance.presetValues, {
                presetId,
                type: 'text',
                textValue: value,
            }];
        }
        instance = { ...instance };
        dispatch('update', { instance });
    }

    function startCapture(presetId: string) {
        dispatch('startCapture', { presetId });
    }

    export function setCaptureValue(presetId: string, captureValue: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        label?: string;
    }) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].captureValue = captureValue;
        } else {
            instance.presetValues = [...instance.presetValues, {
                presetId,
                type: 'capture',
                captureValue,
            }];
        }
        instance = { ...instance };
        dispatch('update', { instance });
    }

    function clearCapture(presetId: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].captureValue = undefined;
            instance = { ...instance };
            dispatch('update', { instance });
        }
    }

    async function handlePaste(event: ClipboardEvent, presetId: string) {
        const items = event.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith("image/")) {
                event.preventDefault();
                const blob = item.getAsFile();
                if (!blob) continue;

                const reader = new FileReader();
                reader.onload = async () => {
                    const base64Data = reader.result as string;
                    await uploadImage(presetId, base64Data);
                };
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    async function uploadImage(presetId: string, base64Data: string) {
        if (!projectId) return;
        isUploading = true;
        try {
            const imageId = generateAttachmentId();
            const response = await uploadAttachmentImage(imageId, projectId, base64Data);

            if (!response.ok) throw new Error("Failed to upload image");

            const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
            if (idx >= 0) {
                instance.presetValues[idx].imageId = imageId;
            } else {
                instance.presetValues = [...instance.presetValues, {
                    presetId,
                    type: 'image_clipboard',
                    imageId,
                }];
            }
            instance = { ...instance };
            dispatch('update', { instance });
        } catch (error) {
            console.error("Failed to upload image:", error);
            alert("이미지 업로드에 실패했습니다.");
        } finally {
            isUploading = false;
        }
    }

    function clearImage(presetId: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].imageId = undefined;
            instance = { ...instance };
            dispatch('update', { instance });
        }
    }

    // Ensure all presets have values initialized
    $: {
        definition.presets.forEach(preset => {
            if (!instance.presetValues.find(pv => pv.presetId === preset.id)) {
                instance.presetValues = [...instance.presetValues, {
                    presetId: preset.id,
                    type: preset.allowedTypes[0] || 'text',
                }];
            }
        });
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
        class="ml-6 bg-white rounded-lg border border-purple-200 shadow-sm hover:shadow-md transition-shadow"
    >
        <!-- Header -->
        <div
            class="px-3 py-2 flex items-center gap-2 cursor-pointer"
            on:click={() => dispatch('toggleExpand')}
            role="button"
            tabindex="0"
            on:keydown={(e) => e.key === 'Enter' && dispatch('toggleExpand')}
        >
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded">
                        Core
                    </span>
                    <span class="text-sm font-medium text-gray-800 truncate">
                        {definition.name}
                    </span>
                </div>
                {#if !isExpanded}
                    <p class="text-xs text-gray-500 truncate mt-0.5">
                        {getPreviewText()}
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

        <!-- Expanded Content - Editable -->
        {#if isExpanded}
            <div class="px-3 pb-3 border-t border-purple-100 pt-2 space-y-3" on:click|stopPropagation>
                {#each definition.presets.sort((a, b) => a.order - b.order) as preset (preset.id)}
                    {@const presetValue = getPresetValue(preset.id)}
                    {@const currentType = presetValue?.type || preset.allowedTypes[0] || 'text'}

                    <div class="bg-purple-50/50 rounded-lg p-2 border border-purple-100">
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-medium text-purple-700">{preset.name}</span>

                            <!-- Type selector if multiple types allowed -->
                            {#if preset.allowedTypes.length > 1}
                                <div class="flex gap-1">
                                    {#each preset.allowedTypes as type}
                                        <button
                                            class="px-1.5 py-0.5 text-[10px] rounded transition
                                                {currentType === type
                                                    ? 'bg-purple-200 text-purple-700 border border-purple-400'
                                                    : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'}"
                                            on:click={() => selectInputType(preset.id, type)}
                                        >
                                            {getInputTypeDisplayName(type)}
                                        </button>
                                    {/each}
                                </div>
                            {/if}
                        </div>

                        <!-- Text Input -->
                        {#if currentType === 'text'}
                            <textarea
                                value={presetValue?.textValue || ''}
                                on:input={(e) => updateTextValue(preset.id, e.currentTarget.value)}
                                placeholder="{preset.name} 입력..."
                                class="w-full border border-gray-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none bg-white"
                                rows="2"
                            ></textarea>

                        <!-- Capture Input -->
                        {:else if currentType === 'capture'}
                            {#if presetValue?.captureValue}
                                <div class="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded">
                                    <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span class="text-xs text-green-700 flex-1">
                                        슬라이드 {presetValue.captureValue.slideIndex + 1}
                                    </span>
                                    <button
                                        class="text-xs text-red-500 hover:text-red-700"
                                        on:click={() => clearCapture(preset.id)}
                                    >
                                        삭제
                                    </button>
                                </div>
                            {:else}
                                <button
                                    class="w-full py-2 border border-dashed border-gray-300 rounded text-gray-500 hover:border-purple-400 hover:text-purple-500 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1 text-xs"
                                    on:click={() => startCapture(preset.id)}
                                >
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    캡처하기
                                </button>
                            {/if}

                        <!-- Image Clipboard Input -->
                        {:else if currentType === 'image_clipboard'}
                            {#if presetValue?.imageId}
                                <div class="relative">
                                    <img
                                        src={getAttachmentImageUrl(presetValue.imageId)}
                                        alt="붙여넣은 이미지"
                                        class="w-full max-h-24 object-contain rounded border border-gray-200"
                                    />
                                    <button
                                        class="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs"
                                        on:click={() => clearImage(preset.id)}
                                    >
                                        ×
                                    </button>
                                </div>
                            {:else}
                                <div
                                    class="w-full py-3 border border-dashed border-gray-300 rounded text-gray-500 flex flex-col items-center justify-center gap-1 cursor-text hover:border-purple-400 hover:bg-purple-50/50 transition-all"
                                    contenteditable="true"
                                    on:paste={(e) => handlePaste(e, preset.id)}
                                    role="textbox"
                                    tabindex="0"
                                >
                                    {#if isUploading}
                                        <span class="text-xs">업로드 중...</span>
                                    {:else}
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                        <span class="text-[10px]">Ctrl+V로 붙여넣기</span>
                                    {/if}
                                </div>
                            {/if}
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>
