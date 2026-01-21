<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        CoreStepDefinition,
        CoreStepPreset,
        CoreStepInputType,
        CoreStepsSettings,
    } from "$lib/types/workflow";
    import {
        createCoreStepDefinition,
        createCoreStepPreset,
        getInputTypeDisplayName,
    } from "$lib/types/workflow";

    export let coreSteps: CoreStepsSettings = { definitions: [] };
    export let expandedStepId: string | null = null;

    let addingStep = false;
    let newStepName = "";
    let editingPresetStepId: string | null = null;
    let newPresetName = "";
    let newPresetTypes: CoreStepInputType[] = ["text"];

    const ALL_INPUT_TYPES: CoreStepInputType[] = [
        "capture",
        "text",
        "image_clipboard",
    ];

    const dispatch = createEventDispatcher<{
        update: { coreSteps: CoreStepsSettings };
        toggleStepExpand: { stepId: string };
    }>();

    function addStep() {
        if (!newStepName.trim()) {
            alert("Core Step 이름을 입력해주세요.");
            return;
        }
        const newDef = createCoreStepDefinition(newStepName.trim());
        coreSteps.definitions = [...coreSteps.definitions, newDef];
        newStepName = "";
        addingStep = false;
        dispatch("update", { coreSteps });
        dispatch("toggleStepExpand", { stepId: newDef.id });
    }

    function removeStep(stepId: string) {
        if (confirm("이 Core Step을 삭제하시겠습니까?")) {
            coreSteps.definitions = coreSteps.definitions.filter(
                (d) => d.id !== stepId,
            );
            if (expandedStepId === stepId) {
                expandedStepId = null;
            }
            dispatch("update", { coreSteps });
        }
    }

    function moveStepUp(index: number) {
        if (index === 0) return;
        const temp = coreSteps.definitions[index - 1];
        coreSteps.definitions[index - 1] = coreSteps.definitions[index];
        coreSteps.definitions[index] = temp;
        coreSteps.definitions = [...coreSteps.definitions];
        dispatch("update", { coreSteps });
    }

    function moveStepDown(index: number) {
        if (index === coreSteps.definitions.length - 1) return;
        const temp = coreSteps.definitions[index + 1];
        coreSteps.definitions[index + 1] = coreSteps.definitions[index];
        coreSteps.definitions[index] = temp;
        coreSteps.definitions = [...coreSteps.definitions];
        dispatch("update", { coreSteps });
    }

    function handleStepNameChange(stepId: string, name: string) {
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            step.name = name;
            coreSteps.definitions = [...coreSteps.definitions];
            dispatch("update", { coreSteps });
        }
    }

    function addPreset(stepId: string) {
        if (!newPresetName.trim()) {
            alert("Preset 이름을 입력해주세요.");
            return;
        }
        if (newPresetTypes.length === 0) {
            alert("허용 형식을 최소 하나 선택해주세요.");
            return;
        }

        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            const order = step.presets.length;
            const newPreset = createCoreStepPreset(
                newPresetName.trim(),
                newPresetTypes,
                order,
            );
            step.presets = [...step.presets, newPreset];
            coreSteps.definitions = [...coreSteps.definitions];
            newPresetName = "";
            newPresetTypes = ["text"];
            editingPresetStepId = null;
            dispatch("update", { coreSteps });
        }
    }

    function removePreset(stepId: string, presetId: string) {
        if (confirm("이 Preset을 삭제하시겠습니까?")) {
            const step = coreSteps.definitions.find((d) => d.id === stepId);
            if (step) {
                step.presets = step.presets.filter((p) => p.id !== presetId);
                // Reorder
                step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
                coreSteps.definitions = [...coreSteps.definitions];
                dispatch("update", { coreSteps });
            }
        }
    }

    function movePresetUp(stepId: string, presetIndex: number) {
        if (presetIndex === 0) return;
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            const temp = step.presets[presetIndex - 1];
            step.presets[presetIndex - 1] = step.presets[presetIndex];
            step.presets[presetIndex] = temp;
            step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
            coreSteps.definitions = [...coreSteps.definitions];
            dispatch("update", { coreSteps });
        }
    }

    function movePresetDown(stepId: string, presetIndex: number) {
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step && presetIndex < step.presets.length - 1) {
            const temp = step.presets[presetIndex + 1];
            step.presets[presetIndex + 1] = step.presets[presetIndex];
            step.presets[presetIndex] = temp;
            step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
            coreSteps.definitions = [...coreSteps.definitions];
            dispatch("update", { coreSteps });
        }
    }

    function handlePresetNameChange(
        stepId: string,
        presetId: string,
        name: string,
    ) {
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            const preset = step.presets.find((p) => p.id === presetId);
            if (preset) {
                preset.name = name;
                coreSteps.definitions = [...coreSteps.definitions];
                dispatch("update", { coreSteps });
            }
        }
    }

    function togglePresetType(
        stepId: string,
        presetId: string,
        type: CoreStepInputType,
    ) {
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            const preset = step.presets.find((p) => p.id === presetId);
            if (preset) {
                if (preset.allowedTypes.includes(type)) {
                    // Don't allow removing last type
                    if (preset.allowedTypes.length > 1) {
                        preset.allowedTypes = preset.allowedTypes.filter(
                            (t) => t !== type,
                        );
                    }
                } else {
                    preset.allowedTypes = [...preset.allowedTypes, type];
                }
                coreSteps.definitions = [...coreSteps.definitions];
                dispatch("update", { coreSteps });
            }
        }
    }

    function toggleNewPresetType(type: CoreStepInputType) {
        if (newPresetTypes.includes(type)) {
            if (newPresetTypes.length > 1) {
                newPresetTypes = newPresetTypes.filter((t) => t !== type);
            }
        } else {
            newPresetTypes = [...newPresetTypes, type];
        }
    }

    function toggleRequiresKeyStepLinking(stepId: string) {
        const step = coreSteps.definitions.find((d) => d.id === stepId);
        if (step) {
            step.requiresKeyStepLinking = !step.requiresKeyStepLinking;
            coreSteps.definitions = [...coreSteps.definitions];
            dispatch("update", { coreSteps });
        }
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">Core Step 정의</h2>
            <p class="text-sm text-gray-500 mt-1">
                Core Step은 Global Step과 독립적으로 관리됩니다. 각 Core
                Step에는 필수 입력 필드(Preset)를 정의할 수 있습니다.
            </p>
        </div>
        <div class="flex gap-2">
            {#if addingStep}
                <div class="flex items-center gap-2">
                    <input
                        type="text"
                        bind:value={newStepName}
                        placeholder="Core Step 이름"
                        class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        on:keydown={(e) => e.key === "Enter" && addStep()}
                    />
                    <button
                        class="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700"
                        on:click={addStep}
                    >
                        추가
                    </button>
                    <button
                        class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                        on:click={() => {
                            addingStep = false;
                            newStepName = "";
                        }}
                    >
                        취소
                    </button>
                </div>
            {:else}
                <button
                    class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition text-sm font-medium"
                    on:click={() => (addingStep = true)}
                >
                    + Core Step 추가
                </button>
            {/if}
        </div>
    </div>

    <!-- Core Step List -->
    <div class="space-y-3">
        {#if coreSteps.definitions.length === 0}
            <div
                class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg"
            >
                정의된 Core Step이 없습니다. Core Step을 추가해주세요.
            </div>
        {:else}
            {#each coreSteps.definitions as step, index (step.id)}
                <div
                    class="border border-purple-200 rounded-lg bg-purple-50/50 overflow-hidden"
                >
                    <!-- Step Header -->
                    <div class="flex items-center gap-3 p-4">
                        <div class="flex flex-col gap-1">
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveStepUp(index)}
                                disabled={index === 0}
                                title="위로 이동"
                            >
                                ▲
                            </button>
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveStepDown(index)}
                                disabled={index ===
                                    coreSteps.definitions.length - 1}
                                title="아래로 이동"
                            >
                                ▼
                            </button>
                        </div>

                        <div
                            class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-sm"
                        >
                            C
                        </div>

                        <div class="flex-1">
                            <div class="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={step.name}
                                    on:input={(e) =>
                                        handleStepNameChange(
                                            step.id,
                                            e.currentTarget.value,
                                        )}
                                    class="bg-transparent border-none text-lg font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-purple-500 rounded px-1"
                                />
                                <span class="text-xs text-gray-400">
                                    Preset {step.presets.length}개
                                </span>
                            </div>
                            <label
                                class="flex items-center gap-1.5 mt-1 cursor-pointer group"
                            >
                                <input
                                    type="checkbox"
                                    checked={step.requiresKeyStepLinking ??
                                        false}
                                    on:change={() =>
                                        toggleRequiresKeyStepLinking(step.id)}
                                    class="w-3.5 h-3.5 text-purple-600 rounded border-gray-300 focus:ring-purple-500 cursor-pointer"
                                />
                                <span
                                    class="text-xs text-gray-500 group-hover:text-gray-700"
                                    >핵심 step 연결 필요</span
                                >
                                <span
                                    class="text-[10px] text-gray-400 cursor-help"
                                    title="이 옵션을 켜면 워크플로우 확정 시 이 Core Step에 대해 핵심적인 역할을 한 이전 스텝들을 연결해야 합니다."
                                >
                                    (?)
                                </span>
                            </label>
                        </div>

                        <button
                            class="text-gray-500 hover:text-purple-600 px-3 py-2 rounded transition text-sm"
                            on:click={() =>
                                dispatch("toggleStepExpand", {
                                    stepId: step.id,
                                })}
                            title="상세 편집"
                        >
                            {expandedStepId === step.id ? "▼ 접기" : "▶ 편집"}
                        </button>

                        <button
                            class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                            on:click={() => removeStep(step.id)}
                        >
                            삭제
                        </button>
                    </div>

                    <!-- Expanded Section -->
                    {#if expandedStepId === step.id}
                        <div class="border-t border-purple-200 p-4 bg-white">
                            <div class="mb-4">
                                <h4
                                    class="text-sm font-semibold text-gray-700 mb-3"
                                >
                                    Preset 필드 (필수 입력 항목)
                                </h4>

                                <!-- Preset List -->
                                <div class="space-y-2 mb-4">
                                    {#if step.presets.length === 0}
                                        <div
                                            class="text-sm text-gray-400 py-4 text-center border border-dashed border-gray-300 rounded"
                                        >
                                            정의된 Preset이 없습니다.
                                        </div>
                                    {:else}
                                        {#each step.presets as preset, pIndex (preset.id)}
                                            <div
                                                class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
                                            >
                                                <div
                                                    class="flex flex-col gap-0.5"
                                                >
                                                    <button
                                                        class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs"
                                                        on:click={() =>
                                                            movePresetUp(
                                                                step.id,
                                                                pIndex,
                                                            )}
                                                        disabled={pIndex === 0}
                                                    >
                                                        ▲
                                                    </button>
                                                    <button
                                                        class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs"
                                                        on:click={() =>
                                                            movePresetDown(
                                                                step.id,
                                                                pIndex,
                                                            )}
                                                        disabled={pIndex ===
                                                            step.presets
                                                                .length -
                                                                1}
                                                    >
                                                        ▼
                                                    </button>
                                                </div>

                                                <span
                                                    class="text-xs text-gray-400 w-6"
                                                    >{pIndex + 1}.</span
                                                >

                                                <input
                                                    type="text"
                                                    value={preset.name}
                                                    on:input={(e) =>
                                                        handlePresetNameChange(
                                                            step.id,
                                                            preset.id,
                                                            e.currentTarget
                                                                .value,
                                                        )}
                                                    class="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                    placeholder="Preset 이름"
                                                />

                                                <div class="flex gap-1">
                                                    {#each ALL_INPUT_TYPES as type}
                                                        <button
                                                            class="px-2 py-1 text-xs rounded border transition
                                                                {preset.allowedTypes.includes(
                                                                type,
                                                            )
                                                                ? 'bg-purple-100 border-purple-400 text-purple-700'
                                                                : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'}"
                                                            on:click={() =>
                                                                togglePresetType(
                                                                    step.id,
                                                                    preset.id,
                                                                    type,
                                                                )}
                                                            title="{getInputTypeDisplayName(
                                                                type,
                                                            )} {preset.allowedTypes.includes(
                                                                type,
                                                            )
                                                                ? '비활성화'
                                                                : '활성화'}"
                                                        >
                                                            {getInputTypeDisplayName(
                                                                type,
                                                            )}
                                                        </button>
                                                    {/each}
                                                </div>

                                                <button
                                                    class="text-red-400 hover:text-red-600 px-2 py-1"
                                                    on:click={() =>
                                                        removePreset(
                                                            step.id,
                                                            preset.id,
                                                        )}
                                                    title="Preset 삭제"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        {/each}
                                    {/if}
                                </div>

                                <!-- Add New Preset -->
                                {#if editingPresetStepId === step.id}
                                    <div
                                        class="p-3 bg-purple-50 rounded-lg border border-purple-200"
                                    >
                                        <div class="flex items-center gap-3">
                                            <input
                                                type="text"
                                                bind:value={newPresetName}
                                                placeholder="Preset 이름 (예: 유사문서)"
                                                class="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                on:keydown={(e) =>
                                                    e.key === "Enter" &&
                                                    addPreset(step.id)}
                                            />
                                        </div>
                                        <div
                                            class="mt-2 flex items-center gap-2"
                                        >
                                            <span class="text-xs text-gray-600"
                                                >허용 형식:</span
                                            >
                                            {#each ALL_INPUT_TYPES as type}
                                                <button
                                                    class="px-2 py-1 text-xs rounded border transition
                                                        {newPresetTypes.includes(
                                                        type,
                                                    )
                                                        ? 'bg-purple-100 border-purple-400 text-purple-700'
                                                        : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'}"
                                                    on:click={() =>
                                                        toggleNewPresetType(
                                                            type,
                                                        )}
                                                >
                                                    {getInputTypeDisplayName(
                                                        type,
                                                    )}
                                                </button>
                                            {/each}
                                            <div class="flex-1"></div>
                                            <button
                                                class="bg-purple-600 text-white px-3 py-1 rounded text-sm hover:bg-purple-700"
                                                on:click={() =>
                                                    addPreset(step.id)}
                                            >
                                                추가
                                            </button>
                                            <button
                                                class="text-gray-500 px-2 py-1 text-sm hover:text-gray-700"
                                                on:click={() => {
                                                    editingPresetStepId = null;
                                                    newPresetName = "";
                                                    newPresetTypes = ["text"];
                                                }}
                                            >
                                                취소
                                            </button>
                                        </div>
                                    </div>
                                {:else}
                                    <button
                                        class="w-full py-2 border border-dashed border-purple-300 rounded-lg text-purple-600 hover:bg-purple-50 transition text-sm"
                                        on:click={() => {
                                            editingPresetStepId = step.id;
                                            newPresetName = "";
                                            newPresetTypes = ["text"];
                                        }}
                                    >
                                        + Preset 추가
                                    </button>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</div>
