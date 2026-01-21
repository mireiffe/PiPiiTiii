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
        imagePaste: { presetId: string; imageData: string };
        imageClick: { presetId: string; imageId: string; caption?: string };
    }>();

    let isUploading = false;
    // Track which preset is in edit mode (for text input)
    let editingPresetId: string | null = null;

    function getPresetDefinition(presetId: string): CoreStepPreset | undefined {
        return definition.presets.find(p => p.id === presetId);
    }

    function getPresetValue(presetId: string): CoreStepPresetValue | undefined {
        return instance.presetValues.find(pv => pv.presetId === presetId);
    }

    function getPreviewText(): string {
        const filledPresets = instance.presetValues.filter(pv => {
            if (pv.type === 'text') return pv.textValue && pv.textValue.trim().length > 0;
            if (pv.type === 'capture') return pv.captureValue !== null && pv.captureValue !== undefined;
            if (pv.type === 'image_clipboard') return pv.imageId !== null && pv.imageId !== undefined;
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

    function startEditing(presetId: string) {
        editingPresetId = presetId;
    }

    function stopEditing() {
        editingPresetId = null;
    }

    function handleTextKeydown(event: KeyboardEvent, presetId: string) {
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            stopEditing();
        }
    }

    function startCapture(presetId: string) {
        dispatch('startCapture', { presetId });
    }

    function clearCapture(presetId: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].captureValue = undefined;
            instance = { ...instance };
            dispatch('update', { instance });
        }
    }

    async function handleImagePaste(event: ClipboardEvent, presetId: string) {
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
                    // Dispatch event to open modal instead of direct upload
                    dispatch('imagePaste', { presetId, imageData: base64Data });
                };
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    // Trigger paste from global clipboard (for click to paste)
    function handleImageAreaClick(presetId: string) {
        // Create a temporary input to trigger paste
        const input = document.createElement('input');
        input.style.position = 'fixed';
        input.style.left = '-9999px';
        document.body.appendChild(input);
        input.focus();

        const handlePaste = async (e: ClipboardEvent) => {
            await handleImagePaste(e, presetId);
            document.removeEventListener('paste', handlePaste);
            document.body.removeChild(input);
        };

        document.addEventListener('paste', handlePaste);

        // Show hint
        alert('이미지를 복사한 후 Ctrl+V를 눌러주세요.');
    }

    // Set image for a preset (called from parent after modal confirm)
    export function setImage(presetId: string, imageId: string, caption?: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].imageId = imageId;
            instance.presetValues[idx].imageCaption = caption;
        } else {
            instance.presetValues = [...instance.presetValues, {
                presetId,
                type: 'image_clipboard',
                imageId,
                imageCaption: caption,
            }];
        }
        instance = { ...instance };
        dispatch('update', { instance });
    }

    // Update image caption (called from parent when editing existing image)
    export function updateImageCaption(presetId: string, caption?: string) {
        const idx = instance.presetValues.findIndex(pv => pv.presetId === presetId);
        if (idx >= 0) {
            instance.presetValues[idx].imageCaption = caption;
            instance = { ...instance };
            dispatch('update', { instance });
        }
    }

    function handleImageClick(presetId: string) {
        const presetValue = getPresetValue(presetId);
        if (presetValue?.imageId) {
            dispatch('imageClick', {
                presetId,
                imageId: presetValue.imageId,
                caption: presetValue.imageCaption,
            });
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

    // Handle global paste for image clipboard type
    function setupGlobalPaste(presetId: string) {
        const handleGlobalPaste = (e: ClipboardEvent) => {
            // Only process if this preset is focused
            const target = e.target as HTMLElement;
            if (target.closest(`[data-preset-id="${presetId}"]`)) {
                handleImagePaste(e, presetId);
            }
        };
        return {
            destroy() {
                // cleanup if needed
            }
        };
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
            class="p-2 flex items-start justify-between gap-2 cursor-pointer hover:bg-gray-50/50 group"
            on:click={() => dispatch('toggleExpand')}
            role="button"
            tabindex="0"
            on:keydown={(e) => e.key === 'Enter' && dispatch('toggleExpand')}
        >
            <!-- Drag Handle -->
            <div
                class="flex items-center pr-1 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity self-center"
            >
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="9" cy="6" r="2" /><circle cx="15" cy="6" r="2" />
                    <circle cx="9" cy="12" r="2" /><circle cx="15" cy="12" r="2" />
                    <circle cx="9" cy="18" r="2" /><circle cx="15" cy="18" r="2" />
                </svg>
            </div>

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

            <!-- Up/Down Buttons -->
            <div class="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity {isExpanded ? 'opacity-100' : ''}">
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500"
                    on:click|stopPropagation={() => dispatch('moveUp')}
                    title="위로 이동"
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                    </svg>
                </button>
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500"
                    on:click|stopPropagation={() => dispatch('moveDown')}
                    title="아래로 이동"
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Expanded Content - Editable -->
        {#if isExpanded}
            {@const sortedPresets = definition.presets.sort((a, b) => a.order - b.order)}
            {@const textPresets = sortedPresets.filter(p => {
                const pv = getPresetValue(p.id);
                const type = pv?.type || p.allowedTypes[0] || 'text';
                return type === 'text';
            })}
            {@const mediaPresets = sortedPresets.filter(p => {
                const pv = getPresetValue(p.id);
                const type = pv?.type || p.allowedTypes[0] || 'text';
                return type === 'capture' || type === 'image_clipboard';
            })}

            <div class="px-3 pb-3 border-t border-purple-100 pt-2 space-y-3" on:click|stopPropagation>
                <!-- Text Presets (Full Width) -->
                {#each textPresets as preset (preset.id)}
                    {@const presetValue = getPresetValue(preset.id)}
                    {@const currentType = presetValue?.type || preset.allowedTypes[0] || 'text'}
                    {@const isEditingThis = editingPresetId === preset.id}

                    <div class="bg-purple-50/50 rounded-lg p-2 border border-purple-100" data-preset-id={preset.id}>
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

                        <!-- Text Input (click to edit, Ctrl+S to save) -->
                        {#if isEditingThis}
                            <textarea
                                value={presetValue?.textValue || ''}
                                on:input={(e) => updateTextValue(preset.id, e.currentTarget.value)}
                                on:blur={stopEditing}
                                on:keydown={(e) => handleTextKeydown(e, preset.id)}
                                placeholder="{preset.name} 입력... (Ctrl+S로 저장)"
                                class="w-full border border-purple-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white"
                                rows="3"
                                autofocus
                            ></textarea>
                        {:else}
                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                            <div
                                class="w-full min-h-[40px] border border-gray-200 rounded px-2 py-1.5 text-xs bg-white cursor-pointer hover:border-purple-300 hover:bg-purple-50/30 transition-all"
                                on:click={() => startEditing(preset.id)}
                                title="클릭하여 편집"
                            >
                                {#if presetValue?.textValue && presetValue.textValue.trim()}
                                    <p class="text-gray-700 whitespace-pre-wrap break-words">{presetValue.textValue}</p>
                                {:else}
                                    <p class="text-gray-400 italic">클릭하여 입력...</p>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/each}

                <!-- Media Presets (Capture & Image - 2 Column Grid) -->
                {#if mediaPresets.length > 0}
                    <div class="grid grid-cols-2 gap-2">
                        {#each mediaPresets as preset, idx (preset.id)}
                            {@const presetValue = getPresetValue(preset.id)}
                            {@const currentType = presetValue?.type || preset.allowedTypes[0] || 'text'}
                            {@const isLastOdd = mediaPresets.length % 2 === 1 && idx === mediaPresets.length - 1}

                            <div
                                class="bg-purple-50/50 rounded-lg p-2 border border-purple-100 {isLastOdd ? 'col-span-2' : ''}"
                                data-preset-id={preset.id}
                            >
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

                                <!-- Capture Input -->
                                {#if currentType === 'capture'}
                                    {#if presetValue?.captureValue}
                                        <div class="flex flex-col gap-1 p-2 bg-green-50 border border-green-200 rounded">
                                            <div class="flex items-center gap-1">
                                                <svg class="w-3 h-3 text-green-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                                </svg>
                                                <span class="text-[10px] text-green-700">
                                                    슬라이드 {presetValue.captureValue.slideIndex + 1}
                                                </span>
                                            </div>
                                            <div class="flex gap-1">
                                                <button
                                                    class="text-[10px] text-gray-500 hover:text-green-600 px-1.5 py-0.5 border border-gray-200 rounded hover:border-green-300 transition flex-1"
                                                    on:click={() => startCapture(preset.id)}
                                                >
                                                    다시 캡처
                                                </button>
                                                <button
                                                    class="text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5"
                                                    on:click={() => clearCapture(preset.id)}
                                                >
                                                    삭제
                                                </button>
                                            </div>
                                        </div>
                                    {:else}
                                        <button
                                            class="w-full py-3 border border-dashed border-gray-300 rounded text-gray-500 hover:border-purple-400 hover:text-purple-500 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1 text-xs"
                                            on:click={() => startCapture(preset.id)}
                                        >
                                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                            </svg>
                                            캡처
                                        </button>
                                    {/if}

                                <!-- Image Clipboard Input -->
                                {:else if currentType === 'image_clipboard'}
                                    {#if presetValue?.imageId}
                                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                                        <div
                                            class="relative group cursor-pointer"
                                            on:click={() => handleImageClick(preset.id)}
                                            title="클릭하여 캡션 편집"
                                        >
                                            <img
                                                src={getAttachmentImageUrl(presetValue.imageId)}
                                                alt="첨부된 이미지"
                                                class="w-full max-h-24 object-contain rounded border border-gray-200 bg-gray-50 hover:border-purple-300 transition"
                                            />
                                            {#if presetValue.imageCaption}
                                                <div class="mt-1 px-1.5 py-0.5 bg-gray-50 rounded border border-gray-200 text-[10px] text-gray-600 truncate">
                                                    {presetValue.imageCaption}
                                                </div>
                                            {/if}
                                            <div class="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    class="w-5 h-5 bg-purple-500 text-white rounded-full flex items-center justify-center hover:bg-purple-600 transition text-xs shadow"
                                                    on:click|stopPropagation={() => handleImageClick(preset.id)}
                                                    title="캡션 편집"
                                                >
                                                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                                    </svg>
                                                </button>
                                                <button
                                                    class="w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs shadow"
                                                    on:click|stopPropagation={() => clearImage(preset.id)}
                                                    title="이미지 삭제"
                                                >
                                                    ×
                                                </button>
                                            </div>
                                        </div>
                                    {:else}
                                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                                        <div
                                            class="w-full py-3 border border-dashed border-gray-300 rounded text-gray-500 flex flex-col items-center justify-center gap-1 hover:border-purple-400 hover:bg-purple-50/50 transition-all cursor-pointer"
                                            on:paste={(e) => handleImagePaste(e, preset.id)}
                                            on:click={() => {
                                                // Focus this element to receive paste events
                                                const el = document.querySelector(`[data-preset-id="${preset.id}"]`);
                                                if (el) (el as HTMLElement).focus();
                                            }}
                                            tabindex="0"
                                            role="button"
                                        >
                                            {#if isUploading}
                                                <svg class="animate-spin w-4 h-4 text-purple-500" viewBox="0 0 24 24">
                                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                <span class="text-[10px]">업로드 중...</span>
                                            {:else}
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                </svg>
                                                <span class="text-[10px]">Ctrl+V 붙여넣기</span>
                                            {/if}
                                        </div>
                                    {/if}
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}

                <!-- Delete Button -->
                <div class="pt-1 border-t border-purple-50 flex justify-end">
                    <button
                        class="text-[10px] text-red-300 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors"
                        on:click={() => dispatch('remove')}
                    >
                        삭제
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
