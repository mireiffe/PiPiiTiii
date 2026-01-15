<script lang="ts">
    import { onMount } from "svelte";
    import { fetchSettings, updateSettings, fetchAllAttributes } from "$lib/api/project";
    import type { WorkflowSteps, StepContainer } from "$lib/types/workflow";
    import LLMSettingsSection from "$lib/components/settings/LLMSettingsSection.svelte";
    import SummaryFieldsSection from "$lib/components/settings/SummaryFieldsSection.svelte";
    import PhenomenonAttributesSection from "$lib/components/settings/PhenomenonAttributesSection.svelte";
    import WorkflowStepsSection from "$lib/components/settings/WorkflowStepsSection.svelte";
    import StepContainersSection from "$lib/components/settings/StepContainersSection.svelte";

    interface AttributeDefinition {
        key: string;
        display_name: string;
        attr_type: { variant: string };
    }

    interface SummaryField {
        id: string;
        name: string;
        order: number;
        system_prompt: string;
        user_prompt: string;
    }

    interface LLMConfig {
        api_type: string;
        api_endpoint: string;
        model_name: string;
    }

    interface Settings {
        llm: LLMConfig;
        workflow_llm?: LLMConfig;
        workflow_prompts?: { system_prompt: string; user_prompt: string };
        summary_fields: SummaryField[];
        use_thumbnails: boolean;
        phenomenon_attributes: string[];
        workflow_steps: WorkflowSteps;
        step_containers: StepContainer[];
    }

    const DEFAULT_COLUMNS = [
        { id: "step_category", name: "스텝 구분", isDefault: true },
        { id: "system", name: "System", isDefault: true },
        { id: "access_target", name: "접근 Target", isDefault: true },
        { id: "purpose", name: "목적", isDefault: true },
        { id: "related_db_table", name: "연관 DB Table", isDefault: true },
    ];

    let loading = true;
    let saving = false;
    let availableAttributes: AttributeDefinition[] = [];
    let expandedFieldId: string | null = null;
    let expandedRowId: string | null = null;

    let settings: Settings = {
        llm: { api_type: "openai", api_endpoint: "", model_name: "" },
        workflow_llm: { api_type: "openai", api_endpoint: "", model_name: "" },
        workflow_prompts: { system_prompt: "", user_prompt: "" },
        summary_fields: [],
        use_thumbnails: true,
        phenomenon_attributes: [],
        workflow_steps: { columns: [], rows: [] },
        step_containers: [],
    };

    onMount(async () => {
        try {
            const [settingsRes, attrsRes] = await Promise.all([
                fetchSettings(),
                fetchAllAttributes()
            ]);

            if (attrsRes.ok) {
                availableAttributes = await attrsRes.json();
            }

            if (settingsRes.ok) {
                const data = await settingsRes.json();
                settings = {
                    llm: {
                        api_type: data.llm?.api_type || "openai",
                        api_endpoint: data.llm?.api_endpoint || "",
                        model_name: data.llm?.model_name || "",
                    },
                    workflow_llm: {
                        api_type: data.workflow_llm?.api_type || data.llm?.api_type || "openai",
                        api_endpoint: data.workflow_llm?.api_endpoint || data.llm?.api_endpoint || "",
                        model_name: data.workflow_llm?.model_name || data.llm?.model_name || "",
                    },
                    workflow_prompts: {
                        system_prompt: data.workflow_prompts?.system_prompt || "",
                        user_prompt: data.workflow_prompts?.user_prompt || "",
                    },
                    summary_fields: (data.summary_fields || []).map((f: any) => ({
                        id: f.id,
                        name: f.name,
                        order: f.order,
                        system_prompt: f.system_prompt || "",
                        user_prompt: f.user_prompt || "",
                    })),
                    use_thumbnails: data.use_thumbnails ?? true,
                    phenomenon_attributes: data.phenomenon_attributes || [],
                    workflow_steps: data.workflow_steps || { columns: DEFAULT_COLUMNS, rows: [] },
                    step_containers: data.step_containers || [],
                };

                if (!settings.workflow_steps.columns || settings.workflow_steps.columns.length === 0) {
                    settings.workflow_steps.columns = DEFAULT_COLUMNS;
                }
            }
        } catch (e) {
            console.error("Failed to load settings", e);
        } finally {
            loading = false;
        }
    });

    async function handleSave() {
        saving = true;
        try {
            const res = await updateSettings(settings);
            if (res.ok) {
                alert("설정이 저장되었습니다.");
            } else {
                alert("설정 저장에 실패했습니다.");
            }
        } catch (e) {
            console.error("Failed to save settings", e);
            alert("설정 저장 중 오류가 발생했습니다.");
        } finally {
            saving = false;
        }
    }

    // Summary fields handlers
    function handleAddField() {
        const newId = `field_${Date.now()}`;
        settings.summary_fields = [
            ...settings.summary_fields,
            { id: newId, name: "새 필드", order: settings.summary_fields.length, system_prompt: "", user_prompt: "" },
        ];
        expandedFieldId = newId;
    }

    function handleRemoveField(e: CustomEvent<{ index: number }>) {
        if (confirm("이 필드를 삭제하시겠습니까?")) {
            settings.summary_fields = settings.summary_fields
                .filter((_, i) => i !== e.detail.index)
                .map((field, i) => ({ ...field, order: i }));
        }
    }

    function handleMoveFieldUp(e: CustomEvent<{ index: number }>) {
        const index = e.detail.index;
        if (index === 0) return;
        const temp = settings.summary_fields[index - 1];
        settings.summary_fields[index - 1] = settings.summary_fields[index];
        settings.summary_fields[index] = temp;
        settings.summary_fields = settings.summary_fields.map((field, i) => ({ ...field, order: i }));
    }

    function handleMoveFieldDown(e: CustomEvent<{ index: number }>) {
        const index = e.detail.index;
        if (index === settings.summary_fields.length - 1) return;
        const temp = settings.summary_fields[index + 1];
        settings.summary_fields[index + 1] = settings.summary_fields[index];
        settings.summary_fields[index] = temp;
        settings.summary_fields = settings.summary_fields.map((field, i) => ({ ...field, order: i }));
    }

    function handleToggleFieldExpand(e: CustomEvent<{ fieldId: string }>) {
        expandedFieldId = expandedFieldId === e.detail.fieldId ? null : e.detail.fieldId;
    }

    function handleFieldsUpdate(e: CustomEvent<{ fields: SummaryField[] }>) {
        settings.summary_fields = e.detail.fields;
    }

    // Phenomenon attributes handler
    function handleTogglePhenomenonAttribute(e: CustomEvent<{ key: string }>) {
        const key = e.detail.key;
        if (settings.phenomenon_attributes.includes(key)) {
            settings.phenomenon_attributes = settings.phenomenon_attributes.filter(k => k !== key);
        } else {
            settings.phenomenon_attributes = [...settings.phenomenon_attributes, key];
        }
    }

    // Workflow steps handlers
    function handleWorkflowStepsUpdate(e: CustomEvent<{ workflowSteps: WorkflowSteps }>) {
        settings.workflow_steps = e.detail.workflowSteps;
    }

    function handleToggleRowExpand(e: CustomEvent<{ rowId: string }>) {
        expandedRowId = expandedRowId === e.detail.rowId ? null : e.detail.rowId;
    }

    // Step containers handlers
    function handleStepContainersUpdate(e: CustomEvent<{ containers: StepContainer[] }>) {
        settings.step_containers = e.detail.containers;
    }
</script>

<div class="h-screen flex flex-col bg-gray-100">
    <div class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm">
        <div>
            <h1 class="text-2xl font-bold text-gray-800">설정</h1>
            <a href="/" class="text-sm text-blue-600 hover:underline">← 대시보드로 돌아가기</a>
        </div>
        <button
            class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm font-medium disabled:opacity-50"
            on:click={handleSave}
            disabled={saving}
        >
            {saving ? "저장 중..." : "저장"}
        </button>
    </div>

    <div class="flex-1 overflow-y-auto p-8">
        {#if loading}
            <div class="text-center text-gray-500">로딩 중...</div>
        {:else}
            <div class="max-w-4xl mx-auto space-y-8">
                <!-- LLM 설정 (요약) -->
                <LLMSettingsSection bind:llm={settings.llm} />

                <!-- PPT 요약 필드 -->
                <SummaryFieldsSection
                    fields={settings.summary_fields}
                    {expandedFieldId}
                    on:add={handleAddField}
                    on:remove={handleRemoveField}
                    on:moveUp={handleMoveFieldUp}
                    on:moveDown={handleMoveFieldDown}
                    on:toggleExpand={handleToggleFieldExpand}
                    on:update={handleFieldsUpdate}
                />

                <!-- 발생현상 속성 설정 -->
                <PhenomenonAttributesSection
                    {availableAttributes}
                    selectedAttributes={settings.phenomenon_attributes}
                    on:toggle={handleTogglePhenomenonAttribute}
                />

                <!-- 워크플로우 스텝 설정 -->
                <WorkflowStepsSection
                    workflowSteps={settings.workflow_steps}
                    {expandedRowId}
                    on:update={handleWorkflowStepsUpdate}
                    on:toggleRowExpand={handleToggleRowExpand}
                />

                <!-- Step Containers 설정 -->
                <StepContainersSection
                    containers={settings.step_containers}
                    on:update={handleStepContainersUpdate}
                />
            </div>
        {/if}
    </div>
</div>
