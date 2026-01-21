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
                    await uploadImage(presetId, base64Data);
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
                        {#if currentType === 'text'}
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

                        <!-- Capture Input -->
                        {:else if currentType === 'capture'}
                            {#if presetValue?.captureValue}
                                <div class="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded">
                                    <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span class="text-xs text-green-700 flex-1">
                                        슬라이드 {presetValue.captureValue.slideIndex + 1} 캡처됨
                                    </span>
                                    <button
                                        class="text-xs text-gray-500 hover:text-green-600 px-2 py-0.5 border border-gray-200 rounded hover:border-green-300 transition"
                                        on:click={() => startCapture(preset.id)}
                                    >
                                        다시 캡처
                                    </button>
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
                                <div class="relative group">
                                    <img
                                        src={getAttachmentImageUrl(presetValue.imageId)}
                                        alt="첨부된 이미지"
                                        class="w-full max-h-32 object-contain rounded border border-gray-200 bg-gray-50"
                                    />
                                    <div class="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            class="w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs shadow"
                                            on:click={() => clearImage(preset.id)}
                                            title="이미지 삭제"
                                        >
                                            ×
                                        </button>
                                    </div>
                                </div>
                            {:else}
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    class="w-full py-4 border border-dashed border-gray-300 rounded text-gray-500 flex flex-col items-center justify-center gap-1.5 hover:border-purple-400 hover:bg-purple-50/50 transition-all cursor-pointer"
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
                                        <svg class="animate-spin w-5 h-5 text-purple-500" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-xs">업로드 중...</span>
                                    {:else}
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        <span class="text-xs">클릭 후 Ctrl+V로 이미지 붙여넣기</span>
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
