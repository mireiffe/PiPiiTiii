<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        CoreStepDefinition,
        CoreStepPresetValue,
        CoreStepInputType
    } from "$lib/types/workflow";
    import { getInputTypeDisplayName } from "$lib/types/workflow";
    import { uploadAttachmentImage } from "$lib/api/project";
    import { generateAttachmentId } from "$lib/types/workflow";

    export let coreStepDef: CoreStepDefinition;
    export let projectId: string;

    const dispatch = createEventDispatcher<{
        confirm: { presetValues: CoreStepPresetValue[] };
        cancel: void;
        startCapture: { presetId: string };
    }>();

    // State for each preset value
    let presetInputs: Record<string, {
        type: CoreStepInputType | null;
        textValue: string;
        captureValue: {
            slideIndex: number;
            x: number;
            y: number;
            width: number;
            height: number;
            label?: string;
        } | null;
        imageId: string | null;
        imagePreview: string | null;  // for display
    }> = {};

    // Initialize inputs
    $: {
        if (coreStepDef) {
            coreStepDef.presets.forEach(preset => {
                if (!presetInputs[preset.id]) {
                    presetInputs[preset.id] = {
                        type: preset.allowedTypes[0] || null,
                        textValue: '',
                        captureValue: null,
                        imageId: null,
                        imagePreview: null
                    };
                }
            });
        }
    }

    let isUploading = false;
    let activeCapturingPresetId: string | null = null;

    // Validation: check if all presets have values
    $: isValid = coreStepDef.presets.every(preset => {
        const input = presetInputs[preset.id];
        if (!input || !input.type) return false;
        switch (input.type) {
            case 'text':
                return input.textValue.trim().length > 0;
            case 'capture':
                return input.captureValue !== null;
            case 'image_clipboard':
                return input.imageId !== null;
            default:
                return false;
        }
    });

    function selectInputType(presetId: string, type: CoreStepInputType) {
        if (presetInputs[presetId]) {
            presetInputs[presetId].type = type;
            presetInputs = { ...presetInputs };
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
        isUploading = true;
        try {
            const imageId = generateAttachmentId();
            const response = await uploadAttachmentImage(imageId, projectId, base64Data);

            if (!response.ok) throw new Error("Failed to upload image");

            if (presetInputs[presetId]) {
                presetInputs[presetId].imageId = imageId;
                presetInputs[presetId].imagePreview = base64Data;
                presetInputs = { ...presetInputs };
            }
        } catch (error) {
            console.error("Failed to upload image:", error);
            alert("이미지 업로드에 실패했습니다.");
        } finally {
            isUploading = false;
        }
    }

    function clearImage(presetId: string) {
        if (presetInputs[presetId]) {
            presetInputs[presetId].imageId = null;
            presetInputs[presetId].imagePreview = null;
            presetInputs = { ...presetInputs };
        }
    }

    function startCapture(presetId: string) {
        activeCapturingPresetId = presetId;
        dispatch('startCapture', { presetId });
    }

    // This function will be called from parent when capture is complete
    export function setCaptureValue(presetId: string, captureValue: {
        slideIndex: number;
        x: number;
        y: number;
        width: number;
        height: number;
        label?: string;
    }) {
        if (presetInputs[presetId]) {
            presetInputs[presetId].captureValue = captureValue;
            presetInputs = { ...presetInputs };
        }
        activeCapturingPresetId = null;
    }

    function clearCapture(presetId: string) {
        if (presetInputs[presetId]) {
            presetInputs[presetId].captureValue = null;
            presetInputs = { ...presetInputs };
        }
    }

    function handleConfirm() {
        if (!isValid) return;

        const presetValues: CoreStepPresetValue[] = coreStepDef.presets.map(preset => {
            const input = presetInputs[preset.id];
            const value: CoreStepPresetValue = {
                presetId: preset.id,
                type: input.type!
            };

            switch (input.type) {
                case 'text':
                    value.textValue = input.textValue.trim();
                    break;
                case 'capture':
                    value.captureValue = input.captureValue!;
                    break;
                case 'image_clipboard':
                    value.imageId = input.imageId!;
                    break;
            }

            return value;
        });

        dispatch('confirm', { presetValues });
    }

    function handleCancel() {
        dispatch('cancel');
    }
</script>

<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" on:click={handleCancel}>
    <div
        class="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col"
        on:click|stopPropagation
    >
        <!-- Header -->
        <div class="px-5 py-4 border-b border-gray-200 flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-sm">
                C
            </div>
            <div>
                <h2 class="text-lg font-semibold text-gray-800">{coreStepDef.name}</h2>
                <p class="text-xs text-gray-500">Core Step 입력</p>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {#each coreStepDef.presets.sort((a, b) => a.order - b.order) as preset (preset.id)}
                {@const input = presetInputs[preset.id]}
                <div class="border border-gray-200 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-3">
                        <label class="text-sm font-medium text-gray-700">
                            {preset.name}
                            <span class="text-red-500">*</span>
                        </label>

                        <!-- Input type selector (if multiple types allowed) -->
                        {#if preset.allowedTypes.length > 1 && input}
                            <div class="flex gap-1">
                                {#each preset.allowedTypes as type}
                                    <button
                                        class="px-2 py-1 text-xs rounded transition
                                            {input.type === type
                                                ? 'bg-purple-100 text-purple-700 border border-purple-400'
                                                : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'}"
                                        on:click={() => selectInputType(preset.id, type)}
                                    >
                                        {getInputTypeDisplayName(type)}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>

                    {#if input}
                        <!-- Text Input -->
                        {#if input.type === 'text'}
                            <textarea
                                bind:value={input.textValue}
                                placeholder="{preset.name} 입력..."
                                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                                rows="3"
                            ></textarea>

                        <!-- Capture Input -->
                        {:else if input.type === 'capture'}
                            {#if input.captureValue}
                                <div class="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                                    <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                    </svg>
                                    <span class="text-sm text-green-700">
                                        슬라이드 {input.captureValue.slideIndex + 1}에서 캡처됨
                                    </span>
                                    <button
                                        class="ml-auto text-xs text-red-500 hover:text-red-700"
                                        on:click={() => clearCapture(preset.id)}
                                    >
                                        삭제
                                    </button>
                                </div>
                            {:else if activeCapturingPresetId === preset.id}
                                <div class="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                    <div class="animate-pulse w-3 h-3 bg-blue-500 rounded-full"></div>
                                    <span class="text-sm text-blue-700">
                                        슬라이드에서 영역을 선택하세요...
                                    </span>
                                </div>
                            {:else}
                                <button
                                    class="w-full py-3 border border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-purple-400 hover:text-purple-500 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-2"
                                    on:click={() => startCapture(preset.id)}
                                >
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    캡처하기
                                </button>
                            {/if}

                        <!-- Image Clipboard Input -->
                        {:else if input.type === 'image_clipboard'}
                            {#if input.imagePreview}
                                <div class="relative">
                                    <img
                                        src={input.imagePreview}
                                        alt="붙여넣은 이미지"
                                        class="w-full max-h-40 object-contain rounded-lg border border-gray-200"
                                    />
                                    <button
                                        class="absolute top-2 right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition"
                                        on:click={() => clearImage(preset.id)}
                                    >
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            {:else}
                                <div
                                    class="w-full py-6 border border-dashed border-gray-300 rounded-lg text-gray-500 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-purple-400 hover:text-purple-500 hover:bg-purple-50/50 transition-all"
                                    contenteditable="true"
                                    on:paste={(e) => handlePaste(e, preset.id)}
                                    role="textbox"
                                    tabindex="0"
                                >
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <span class="text-xs">클릭 후 Ctrl+V로 이미지 붙여넣기</span>
                                </div>
                            {/if}
                        {/if}
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Footer -->
        <div class="px-5 py-4 border-t border-gray-200 flex justify-end gap-2">
            <button
                class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition"
                on:click={handleCancel}
                disabled={isUploading}
            >
                취소
            </button>
            <button
                class="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                on:click={handleConfirm}
                disabled={!isValid || isUploading}
            >
                {isUploading ? '업로드 중...' : '추가'}
            </button>
        </div>
    </div>
</div>
