<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        CoreStepInstance,
        CoreStepDefinition,
        CoreStepPreset,
        CoreStepPresetValue,
        CoreStepInputType,
        KeyStepLinkingData,
        UnifiedStepItem,
        WorkflowStepRow,
    } from "$lib/types/workflow";
    import { getInputTypeDisplayName } from "$lib/types/workflow";
    import { generateTextStream } from "$lib/api/project";
    import CaptureCard from "./CaptureCard.svelte";
    import ImageAttachmentCard from "./ImageAttachmentCard.svelte";

    export let instance: CoreStepInstance;
    export let definition: CoreStepDefinition;
    export let displayNumber: number;
    export let isExpanded = false;
    export let projectId: string = "";
    export let slideWidth: number = 960; // Original slide width
    export let slideHeight: number = 540; // Original slide height
    // Key step linking props (optional)
    export let keyStepLinks: KeyStepLinkingData[] = [];
    export let allSteps: UnifiedStepItem[] = [];
    export let coreStepDefinitions: CoreStepDefinition[] = [];
    export let workflowSteps: { rows: WorkflowStepRow[] } | null = null;
    export let phenomenonAttributes: string[] = [];
    export let availableAttributes: { key: string; display_name: string; attr_type: { variant: string } }[] = [];
    export let projectAttributeValues: Record<string, string> = {};
    export let selectedSlideIndices: number[] = [];

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

    // Track which preset is in caption edit mode
    let editingCaptionPresetId: string | null = null;
    // Tooltip hover state
    let showLinkedStepsTooltip = false;

    // Check if this Core Step requires key step linking
    $: requiresKeyStepLinking = definition.requiresKeyStepLinking ?? false;

    // Get linked steps for this Core Step
    $: linkedStepsData = keyStepLinks.find(
        (l) => l.coreStepInstanceId === instance.id,
    );
    $: hasLinkedSteps =
        linkedStepsData && linkedStepsData.linkedSteps.length > 0;

    // Group linked steps by priority
    $: linkedStepsByPriority = (() => {
        if (!linkedStepsData) return [];
        const groups: {
            priority: number;
            steps: { step: UnifiedStepItem; name: string }[];
        }[] = [];

        linkedStepsData.linkedSteps.forEach((link) => {
            const step = allSteps.find((s) => s.id === link.stepId);
            if (!step) return;

            const name = getLinkedStepName(step);
            let group = groups.find((g) => g.priority === link.priority);
            if (!group) {
                group = { priority: link.priority, steps: [] };
                groups.push(group);
            }
            group.steps.push({ step, name });
        });

        return groups.sort((a, b) => a.priority - b.priority);
    })();

    function getLinkedStepName(step: UnifiedStepItem): string {
        if (step.type === "core") {
            const def = coreStepDefinitions.find(
                (d) => d.id === step.coreStepId,
            );
            return def?.name || "Core Step";
        } else {
            if (workflowSteps) {
                const row = workflowSteps.rows.find(
                    (r) => r.id === step.stepId,
                );
                if (row) {
                    const category = row.values["step_category"];
                    const purpose = row.values["purpose"];
                    if (category && purpose) return `[${category}] ${purpose}`;
                    if (category) return `[${category}]`;
                    if (purpose) return purpose;
                }
            }
            return "스텝";
        }
    }

    function getPresetDefinition(presetId: string): CoreStepPreset | undefined {
        return definition.presets.find((p) => p.id === presetId);
    }

    // Get the default caption value for a preset from project metadata
    function getDefaultCaptionValue(preset: CoreStepPreset): string | undefined {
        if (!preset.defaultMetadataKey) return undefined;
        const val = projectAttributeValues[preset.defaultMetadataKey];
        return val != null ? String(val) : undefined;
    }

    function getPresetValue(presetId: string): CoreStepPresetValue | undefined {
        return instance.presetValues.find((pv) => pv.presetId === presetId);
    }

    function getPreviewText(): string {
        const filledPresets = instance.presetValues.filter((pv) => {
            if (pv.type === "text")
                return pv.imageCaption && pv.imageCaption.trim().length > 0;
            if (pv.type === "capture")
                return (
                    pv.captureValue !== null && pv.captureValue !== undefined
                );
            if (pv.type === "image_clipboard")
                return pv.imageId !== null && pv.imageId !== undefined;
            return false;
        });

        if (filledPresets.length === 0) {
            return "(입력 필요)";
        }

        return filledPresets
            .map((pv) => {
                const preset = getPresetDefinition(pv.presetId);
                if (pv.type === "text" && pv.imageCaption) {
                    const truncated =
                        pv.imageCaption.length > 15
                            ? pv.imageCaption.substring(0, 15) + "..."
                            : pv.imageCaption;
                    return `${preset?.name}: ${truncated}`;
                }
                if (pv.type === "capture") return `${preset?.name}: 캡처`;
                if (pv.type === "image_clipboard")
                    return `${preset?.name}: 이미지`;
                return preset?.name;
            })
            .join(", ");
    }

    function selectInputType(presetId: string, type: CoreStepInputType) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx] = {
                ...instance.presetValues[idx],
                type,
                captureValue:
                    type === "capture"
                        ? instance.presetValues[idx].captureValue
                        : undefined,
                imageId:
                    type === "image_clipboard"
                        ? instance.presetValues[idx].imageId
                        : undefined,
                // Preserve caption across type changes
                imageCaption: instance.presetValues[idx].imageCaption,
            };
        } else {
            // Initialize caption with metadata default if available
            const presetDef = getPresetDefinition(presetId);
            const defaultCaption = presetDef ? getDefaultCaptionValue(presetDef) : undefined;
            instance.presetValues = [
                ...instance.presetValues,
                {
                    presetId,
                    type,
                    imageCaption: defaultCaption || undefined,
                },
            ];
        }
        instance = { ...instance };
        dispatch("update", { instance });
    }

    function updateTextValue(presetId: string, value: string) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].textValue = value;
        } else {
            instance.presetValues = [
                ...instance.presetValues,
                {
                    presetId,
                    type: "text",
                    textValue: value,
                },
            ];
        }
        instance = { ...instance };
        dispatch("update", { instance });
    }

    function startEditing(presetId: string) {
        editingPresetId = presetId;
    }

    function stopEditing() {
        editingPresetId = null;
    }

    function handleTextKeydown(event: KeyboardEvent, presetId: string) {
        if ((event.ctrlKey || event.metaKey) && event.key === "s") {
            event.preventDefault();
            stopEditing();
        }
    }

    // Caption editing (for capture and image_clipboard presets)
    function startEditingCaption(presetId: string) {
        editingCaptionPresetId = presetId;
    }

    function stopEditingCaption() {
        editingCaptionPresetId = null;
    }

    function handleCaptionKeydown(event: KeyboardEvent) {
        if ((event.ctrlKey || event.metaKey) && event.key === "s") {
            event.preventDefault();
            stopEditingCaption();
        }
    }

    function updateCaption(presetId: string, value: string) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].imageCaption = value || undefined;
        }
        instance = { ...instance };
        dispatch("update", { instance });
    }

    function handleCaptionInput(event: Event, presetId: string) {
        const textarea = event.currentTarget as HTMLTextAreaElement;
        updateCaption(presetId, textarea.value);
    }

    // Auto-resize textarea action - resizes on mount and input
    function autoResizeTextarea(textarea: HTMLTextAreaElement) {
        const resize = () => {
            textarea.style.height = "auto";
            textarea.style.height = textarea.scrollHeight + "px";
        };

        // Initial resize
        resize();

        // Resize on input
        textarea.addEventListener("input", resize);

        return {
            destroy() {
                textarea.removeEventListener("input", resize);
            },
        };
    }

    // LLM auto-generation state
    let generatingPresetIds: Set<string> = new Set();

    async function generateTextForPreset(presetId: string) {
        if (generatingPresetIds.has(presetId)) return;

        const preset = getPresetDefinition(presetId);
        if (!preset?.llmAutoGen?.enabled) return;

        const systemPrompt = definition.llmSystemPrompt || "당신은 PPT 프레젠테이션을 분석하는 전문가입니다.";
        const userPrompt = preset.llmAutoGen.userPrompt || "이 슬라이드의 내용을 분석해주세요.";

        generatingPresetIds.add(presetId);
        generatingPresetIds = generatingPresetIds;

        // Close editing mode so streaming text shows in preview area
        if (editingCaptionPresetId === presetId) {
            editingCaptionPresetId = null;
        }

        let generatedContent = "";

        try {
            const stream = await generateTextStream(
                projectId,
                systemPrompt,
                userPrompt,
                selectedSlideIndices,
            );
            if (!stream) throw new Error("No stream returned");

            const reader = stream.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                generatedContent += chunk;
                updateCaption(presetId, generatedContent);
            }
        } catch (e) {
            console.error("Failed to generate text for preset", e);
        } finally {
            generatingPresetIds.delete(presetId);
            generatingPresetIds = generatingPresetIds;
        }
    }

    function handleTextareaInput(event: Event, presetId: string) {
        const textarea = event.currentTarget as HTMLTextAreaElement;
        updateTextValue(presetId, textarea.value);
    }

    function startCapture(presetId: string) {
        dispatch("startCapture", { presetId });
    }

    function clearCapture(presetId: string) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].captureValue = undefined;
            instance = { ...instance };
            dispatch("update", { instance });
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
                    dispatch("imagePaste", { presetId, imageData: base64Data });
                };
                reader.readAsDataURL(blob);
                return;
            }
        }
    }

    // Trigger paste from global clipboard (for click to paste)
    function handleImageAreaClick(presetId: string) {
        // Create a temporary input to trigger paste
        const input = document.createElement("input");
        input.style.position = "fixed";
        input.style.left = "-9999px";
        document.body.appendChild(input);
        input.focus();

        const handlePaste = async (e: ClipboardEvent) => {
            await handleImagePaste(e, presetId);
            document.removeEventListener("paste", handlePaste);
            document.body.removeChild(input);
        };

        document.addEventListener("paste", handlePaste);

        // Show hint
        alert("이미지를 복사한 후 Ctrl+V를 눌러주세요.");
    }

    // Set image for a preset (called from parent after modal confirm)
    export function setImage(
        presetId: string,
        imageId: string,
        caption?: string,
    ) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].imageId = imageId;
            instance.presetValues[idx].imageCaption = caption;
        } else {
            instance.presetValues = [
                ...instance.presetValues,
                {
                    presetId,
                    type: "image_clipboard",
                    imageId,
                    imageCaption: caption,
                },
            ];
        }
        instance = { ...instance };
        dispatch("update", { instance });
    }

    // Update image caption (called from parent when editing existing image)
    export function updateImageCaption(presetId: string, caption?: string) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].imageCaption = caption;
            instance = { ...instance };
            dispatch("update", { instance });
        }
    }

    function handleImageClick(presetId: string) {
        const presetValue = getPresetValue(presetId);
        if (presetValue?.imageId) {
            dispatch("imageClick", {
                presetId,
                imageId: presetValue.imageId,
                caption: presetValue.imageCaption,
            });
        }
    }

    function clearImage(presetId: string) {
        const idx = instance.presetValues.findIndex(
            (pv) => pv.presetId === presetId,
        );
        if (idx >= 0) {
            instance.presetValues[idx].imageId = undefined;
            instance = { ...instance };
            dispatch("update", { instance });
        }
    }

    // Ensure all presets have values initialized
    $: {
        definition.presets.forEach((preset) => {
            const existingIdx = instance.presetValues.findIndex((pv) => pv.presetId === preset.id);
            if (existingIdx < 0) {
                const initType = preset.allowedTypes[0] || "text";
                const defaultCaption = getDefaultCaptionValue(preset);
                instance.presetValues = [
                    ...instance.presetValues,
                    {
                        presetId: preset.id,
                        type: initType,
                        imageCaption: defaultCaption || undefined,
                    },
                ];
            } else {
                const pv = instance.presetValues[existingIdx];
                // Migrate legacy 'metadata' type to 'text', and
                // migrate legacy textValue → imageCaption for text type
                if ((pv.type as string) === "metadata" || (pv.type === "text" && pv.textValue && !pv.imageCaption)) {
                    instance.presetValues[existingIdx] = {
                        ...pv,
                        type: "text",
                        imageCaption: pv.imageCaption || pv.textValue || undefined,
                        textValue: undefined,
                    };
                }
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
            },
        };
    }
</script>

<div
    class="relative pl-6"
    class:z-50={showLinkedStepsTooltip}
    class:z-10={!showLinkedStepsTooltip}
>
    <!-- Number Badge -->
    <div
        class="absolute left-0 top-2.5 w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center text-white text-[9px] font-bold shadow-sm z-20"
    >
        C{displayNumber}
    </div>

    <!-- Card -->
    <div
        class="bg-white rounded-lg border border-purple-200 shadow-sm hover:shadow-md transition-shadow"
    >
        <!-- Header -->
        <div
            class="p-2 flex items-start justify-between gap-2 cursor-pointer hover:bg-gray-50/50 group"
            on:click={() => dispatch("toggleExpand")}
            role="button"
            tabindex="0"
            on:keydown={(e) => e.key === "Enter" && dispatch("toggleExpand")}
        >
            <!-- Drag Handle -->
            <div
                class="flex items-center pr-1 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity self-center"
            >
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="9" cy="6" r="2" /><circle
                        cx="15"
                        cy="6"
                        r="2"
                    />
                    <circle cx="9" cy="12" r="2" /><circle
                        cx="15"
                        cy="12"
                        r="2"
                    />
                    <circle cx="9" cy="18" r="2" /><circle
                        cx="15"
                        cy="18"
                        r="2"
                    />
                </svg>
            </div>

            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span
                        class="text-xs font-medium text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded"
                    >
                        Core
                    </span>
                    <span class="text-sm font-medium text-gray-800 truncate">
                        {definition.name}
                    </span>
                    <!-- Key Step Linking Indicator -->
                    {#if requiresKeyStepLinking}
                        <div
                            class="relative"
                            on:mouseenter={() =>
                                (showLinkedStepsTooltip = true)}
                            on:mouseleave={() =>
                                (showLinkedStepsTooltip = false)}
                        >
                            {#if hasLinkedSteps}
                                <span
                                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-green-100 text-green-600 text-[10px] font-medium cursor-help"
                                    title="연결된 핵심 스텝"
                                >
                                    <svg
                                        class="w-3 h-3"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                                        />
                                    </svg>
                                    {linkedStepsData?.linkedSteps.length}
                                </span>
                            {:else}
                                <span
                                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 text-[10px] font-medium cursor-help"
                                    title="핵심 step 연결 필요"
                                >
                                    <svg
                                        class="w-3 h-3"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                                        />
                                    </svg>
                                </span>
                            {/if}

                            <!-- Tooltip -->
                            {#if showLinkedStepsTooltip && hasLinkedSteps}
                                <div
                                    class="absolute left-0 top-full mt-1 z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[200px] max-w-[280px]"
                                    on:click|stopPropagation
                                >
                                    <div
                                        class="px-3 py-1 text-xs font-semibold text-gray-700 border-b border-gray-100 flex items-center gap-1.5"
                                    >
                                        <svg
                                            class="w-3.5 h-3.5 text-purple-500"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                                            />
                                        </svg>
                                        연결된 핵심 스텝
                                    </div>
                                    <div class="py-1">
                                        {#each linkedStepsByPriority as group (group.priority)}
                                            <div class="px-3 py-1">
                                                <div
                                                    class="text-[10px] font-medium text-purple-600 mb-1"
                                                >
                                                    [{group.priority}순위]
                                                </div>
                                                {#each group.steps as { step, name } (step.id)}
                                                    <div
                                                        class="flex items-center gap-1.5 text-xs text-gray-600 py-0.5"
                                                    >
                                                        <span
                                                            class="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0
                                                            {step.type ===
                                                            'core'
                                                                ? 'bg-purple-100 text-purple-600'
                                                                : 'bg-blue-100 text-blue-600'}"
                                                        >
                                                            {step.type ===
                                                            "core"
                                                                ? "C"
                                                                : allSteps.findIndex(
                                                                      (s) =>
                                                                          s.id ===
                                                                          step.id,
                                                                  ) + 1}
                                                        </span>
                                                        <span class="truncate"
                                                            >{name.length > 30
                                                                ? name.slice(
                                                                      0,
                                                                      30,
                                                                  ) + "..."
                                                                : name}</span
                                                        >
                                                    </div>
                                                {/each}
                                            </div>
                                        {/each}
                                    </div>
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
                {#if !isExpanded}
                    <p class="text-xs text-gray-500 truncate mt-0.5">
                        {getPreviewText()}
                    </p>
                {/if}
            </div>

            <!-- Up/Down Buttons -->
            <div
                class="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity {isExpanded
                    ? 'opacity-100'
                    : ''}"
            >
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500"
                    on:click|stopPropagation={() => dispatch("moveUp")}
                    title="위로 이동"
                >
                    <svg
                        class="w-2.5 h-2.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M5 15l7-7 7 7"
                        />
                    </svg>
                </button>
                <button
                    class="p-0.5 hover:bg-gray-100 rounded text-gray-300 hover:text-gray-500"
                    on:click|stopPropagation={() => dispatch("moveDown")}
                    title="아래로 이동"
                >
                    <svg
                        class="w-2.5 h-2.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 9l-7 7-7-7"
                        />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Expanded Content - Editable -->
        {#if isExpanded}
            {@const sortedPresets = [...definition.presets].sort(
                (a, b) => a.order - b.order,
            )}

            <div
                class="px-3 pb-3 border-t border-purple-100 pt-2 grid grid-cols-2 gap-2"
                on:click|stopPropagation
            >
                <!-- All Presets in order -->
                {#each sortedPresets as preset (preset.id)}
                    {@const presetValue = getPresetValue(preset.id)}
                    {@const currentType =
                        presetValue?.type || preset.allowedTypes[0] || "text"}
                    {@const isEditingThis = editingPresetId === preset.id}

                    <div
                        class="bg-purple-50/50 rounded-lg p-2 border border-purple-100 {currentType === 'text'
                            ? 'col-span-2'
                            : ''}"
                        data-preset-id={preset.id}
                    >
                        <div class="flex items-center justify-between mb-2">
                            <span class="text-xs font-medium text-purple-700"
                                >{preset.name}</span
                            >

                            <div class="flex items-center gap-1.5">
                                <!-- LLM Auto-gen button -->
                                {#if preset.llmAutoGen?.enabled}
                                    <button
                                        class="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-bold rounded
                                            bg-white border border-indigo-100 text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200
                                            shadow-sm hover:shadow transition-all duration-200
                                            disabled:opacity-50 disabled:cursor-not-allowed"
                                        on:click|stopPropagation={() =>
                                            generateTextForPreset(preset.id)}
                                        disabled={generatingPresetIds.has(preset.id)}
                                        title="LLM으로 자동 생성"
                                    >
                                        {#if generatingPresetIds.has(preset.id)}
                                            <svg class="animate-spin w-2.5 h-2.5" viewBox="0 0 24 24">
                                                <circle
                                                    class="opacity-25"
                                                    cx="12" cy="12" r="10"
                                                    stroke="currentColor" stroke-width="4" fill="none"
                                                ></circle>
                                                <path
                                                    class="opacity-75"
                                                    fill="currentColor"
                                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                ></path>
                                            </svg>
                                        {:else}
                                            <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path
                                                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                    d="M13 10V3L4 14h7v7l9-11h-7z"
                                                />
                                            </svg>
                                        {/if}
                                        <span>자동 생성</span>
                                    </button>
                                {/if}

                                <!-- Type selector if multiple types allowed -->
                                {#if preset.allowedTypes.length > 1}
                                    <div class="flex gap-1">
                                        {#each preset.allowedTypes as type}
                                            <button
                                                class="px-1.5 py-0.5 text-[10px] rounded transition
                                                    {currentType === type
                                                    ? 'bg-purple-200 text-purple-700 border border-purple-400'
                                                    : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'}"
                                                on:click={() =>
                                                    selectInputType(
                                                        preset.id,
                                                        type,
                                                    )}
                                            >
                                                {getInputTypeDisplayName(type)}
                                            </button>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        </div>

                        <!-- Text Input (caption only) -->
                        {#if currentType === "text"}
                            {#if editingCaptionPresetId === preset.id}
                                <textarea
                                    value={presetValue?.imageCaption || ""}
                                    on:input={(e) => handleCaptionInput(e, preset.id)}
                                    on:blur={stopEditingCaption}
                                    on:keydown={handleCaptionKeydown}
                                    placeholder="캡션 입력... (Ctrl+S로 저장)"
                                    class="w-full min-h-[60px] border border-purple-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white overflow-hidden"
                                    use:autoResizeTextarea
                                    autofocus
                                ></textarea>
                            {:else}
                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    class="w-full min-h-[40px] border rounded px-2 py-1.5 text-xs bg-white transition-all
                                        {generatingPresetIds.has(preset.id)
                                        ? 'border-indigo-300 bg-indigo-50/30'
                                        : 'border-gray-200 cursor-pointer hover:border-purple-300 hover:bg-purple-50/30'}"
                                    on:click={() => {
                                        if (!generatingPresetIds.has(preset.id)) {
                                            startEditingCaption(preset.id);
                                        }
                                    }}
                                    title={generatingPresetIds.has(preset.id) ? "생성 중..." : "클릭하여 편집"}
                                >
                                    {#if presetValue?.imageCaption && presetValue.imageCaption.trim()}
                                        <p class="text-gray-700 whitespace-pre-wrap break-words">{presetValue.imageCaption}</p>
                                    {:else if generatingPresetIds.has(preset.id)}
                                        <p class="text-indigo-400 italic">생성 중...</p>
                                    {:else}
                                        <p class="text-gray-400 italic">클릭하여 입력...</p>
                                    {/if}
                                </div>
                            {/if}
                            {#if preset.defaultMetadataKey}
                                {@const defaultCaptionVal = projectAttributeValues[preset.defaultMetadataKey]}
                                {#if defaultCaptionVal != null && presetValue?.imageCaption !== String(defaultCaptionVal)}
                                    <button
                                        class="mt-1 text-[10px] text-gray-400 hover:text-purple-600 transition-colors"
                                        on:click={() => updateCaption(preset.id, String(defaultCaptionVal))}
                                        title="캡션 기본값: {defaultCaptionVal}"
                                    >
                                        캡션 기본값으로 돌리기
                                    </button>
                                {/if}
                            {/if}

                            <!-- Capture Input -->
                        {:else if currentType === "capture"}
                            {#if presetValue?.captureValue}
                                <CaptureCard
                                    capture={presetValue.captureValue}
                                    {projectId}
                                    {slideWidth}
                                    {slideHeight}
                                    showRecaptureButton={true}
                                    on:recapture={() => startCapture(preset.id)}
                                    on:remove={() => clearCapture(preset.id)}
                                />
                                <!-- Caption for capture -->
                                {#if editingCaptionPresetId === preset.id}
                                    <textarea
                                        value={presetValue?.imageCaption || ""}
                                        on:input={(e) => handleCaptionInput(e, preset.id)}
                                        on:blur={stopEditingCaption}
                                        on:keydown={handleCaptionKeydown}
                                        placeholder="캡션 입력... (Ctrl+S로 저장)"
                                        class="w-full mt-1.5 min-h-[36px] border border-purple-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white overflow-hidden"
                                        use:autoResizeTextarea
                                        autofocus
                                    ></textarea>
                                {:else}
                                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                                    <div
                                        class="w-full mt-1.5 min-h-[24px] border rounded px-2 py-1 text-xs bg-white transition-all
                                            {generatingPresetIds.has(preset.id)
                                            ? 'border-indigo-300 bg-indigo-50/30'
                                            : 'border-gray-200 cursor-pointer hover:border-purple-300 hover:bg-purple-50/30'}"
                                        on:click={() => {
                                            if (!generatingPresetIds.has(preset.id)) {
                                                startEditingCaption(preset.id);
                                            }
                                        }}
                                        title={generatingPresetIds.has(preset.id) ? "생성 중..." : "클릭하여 캡션 편집"}
                                    >
                                        {#if presetValue?.imageCaption && presetValue.imageCaption.trim()}
                                            <p class="text-gray-700 whitespace-pre-wrap break-words">{presetValue.imageCaption}</p>
                                        {:else if generatingPresetIds.has(preset.id)}
                                            <p class="text-indigo-400 italic">생성 중...</p>
                                        {:else}
                                            <p class="text-gray-400 italic">캡션 입력...</p>
                                        {/if}
                                    </div>
                                {/if}
                                {#if preset.defaultMetadataKey}
                                    {@const defaultCaptionVal = projectAttributeValues[preset.defaultMetadataKey]}
                                    {#if defaultCaptionVal != null && presetValue?.imageCaption !== String(defaultCaptionVal)}
                                        <button
                                            class="mt-1 text-[10px] text-gray-400 hover:text-purple-600 transition-colors"
                                            on:click={() => updateCaption(preset.id, String(defaultCaptionVal))}
                                            title="캡션 기본값: {defaultCaptionVal}"
                                        >
                                            캡션 기본값으로 돌리기
                                        </button>
                                    {/if}
                                {/if}
                            {:else}
                                <button
                                    class="w-full py-3 border border-dashed border-gray-300 rounded text-gray-500 hover:border-purple-400 hover:text-purple-500 hover:bg-purple-50/50 transition-all flex items-center justify-center gap-1 text-xs"
                                    on:click={() => startCapture(preset.id)}
                                >
                                    <svg
                                        class="w-3 h-3"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                        />
                                    </svg>
                                    캡처
                                </button>
                            {/if}

                            <!-- Image Clipboard Input -->
                        {:else if currentType === "image_clipboard"}
                            {#if presetValue?.imageId}
                                <ImageAttachmentCard
                                    imageId={presetValue.imageId}
                                    on:click={() => handleImageClick(preset.id)}
                                    on:remove={() => clearImage(preset.id)}
                                />
                                <!-- Caption for image (inline text editing) -->
                                {#if editingCaptionPresetId === preset.id}
                                    <textarea
                                        value={presetValue?.imageCaption || ""}
                                        on:input={(e) => handleCaptionInput(e, preset.id)}
                                        on:blur={stopEditingCaption}
                                        on:keydown={handleCaptionKeydown}
                                        placeholder="캡션 입력... (Ctrl+S로 저장)"
                                        class="w-full mt-1.5 min-h-[36px] border border-purple-300 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white overflow-hidden"
                                        use:autoResizeTextarea
                                        autofocus
                                    ></textarea>
                                {:else}
                                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                                    <div
                                        class="w-full mt-1.5 min-h-[24px] border rounded px-2 py-1 text-xs bg-white transition-all
                                            {generatingPresetIds.has(preset.id)
                                            ? 'border-indigo-300 bg-indigo-50/30'
                                            : 'border-gray-200 cursor-pointer hover:border-purple-300 hover:bg-purple-50/30'}"
                                        on:click={() => {
                                            if (!generatingPresetIds.has(preset.id)) {
                                                startEditingCaption(preset.id);
                                            }
                                        }}
                                        title={generatingPresetIds.has(preset.id) ? "생성 중..." : "클릭하여 캡션 편집"}
                                    >
                                        {#if presetValue?.imageCaption && presetValue.imageCaption.trim()}
                                            <p class="text-gray-700 whitespace-pre-wrap break-words">{presetValue.imageCaption}</p>
                                        {:else if generatingPresetIds.has(preset.id)}
                                            <p class="text-indigo-400 italic">생성 중...</p>
                                        {:else}
                                            <p class="text-gray-400 italic">캡션 입력...</p>
                                        {/if}
                                    </div>
                                {/if}
                                {#if preset.defaultMetadataKey}
                                    {@const defaultCaptionVal = projectAttributeValues[preset.defaultMetadataKey]}
                                    {#if defaultCaptionVal != null && presetValue?.imageCaption !== String(defaultCaptionVal)}
                                        <button
                                            class="mt-1 text-[10px] text-gray-400 hover:text-purple-600 transition-colors"
                                            on:click={() => updateCaption(preset.id, String(defaultCaptionVal))}
                                            title="캡션 기본값: {defaultCaptionVal}"
                                        >
                                            캡션 기본값으로 돌리기
                                        </button>
                                    {/if}
                                {/if}
                            {:else}
                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                <div
                                    class="w-full py-3 border border-dashed border-gray-300 rounded text-gray-500 flex flex-col items-center justify-center gap-1 hover:border-purple-400 hover:bg-purple-50/50 transition-all cursor-pointer"
                                    on:paste={(e) =>
                                        handleImagePaste(e, preset.id)}
                                    on:click={() => {
                                        // Focus this element to receive paste events
                                        const el = document.querySelector(
                                            `[data-preset-id="${preset.id}"]`,
                                        );
                                        if (el) (el as HTMLElement).focus();
                                    }}
                                    tabindex="0"
                                    role="button"
                                >
                                    {#if isUploading}
                                        <svg
                                            class="animate-spin w-4 h-4 text-purple-500"
                                            viewBox="0 0 24 24"
                                        >
                                            <circle
                                                class="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                stroke-width="4"
                                                fill="none"
                                            ></circle>
                                            <path
                                                class="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            ></path>
                                        </svg>
                                        <span class="text-[10px]"
                                            >업로드 중...</span
                                        >
                                    {:else}
                                        <svg
                                            class="w-4 h-4"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                            />
                                        </svg>
                                        <span class="text-[10px]"
                                            >Ctrl+V 붙여넣기</span
                                        >
                                    {/if}
                                </div>
                            {/if}
                        {/if}
                    </div>
                {/each}

                <!-- Delete Button -->
                <div
                    class="col-span-2 pt-1 border-t border-purple-50 flex justify-end"
                >
                    <button
                        class="text-[10px] text-red-300 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors"
                        on:click={() => dispatch("remove")}
                    >
                        삭제
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
