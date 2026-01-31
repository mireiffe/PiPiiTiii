<script lang="ts">
    import { onMount } from "svelte";
    import { fetchSettings, updateSettings, fetchAllAttributes } from "$lib/api/project";
    import type { KeyInfoSettings } from "$lib/types/keyInfo";
    import LLMSettingsSection from "$lib/components/settings/LLMSettingsSection.svelte";
    import SummaryFieldsSection from "$lib/components/settings/SummaryFieldsSection.svelte";
    import PhenomenonAttributesSection from "$lib/components/settings/PhenomenonAttributesSection.svelte";
    import KeyInfoSettingsSection from "$lib/components/settings/KeyInfoSettingsSection.svelte";
    import TutorialSettingsSection from "$lib/components/settings/TutorialSettingsSection.svelte";

    // Navigation sections
    type SectionId = "keyinfo" | "llm" | "summary" | "phenomenon" | "tutorial";

    interface NavSection {
        id: SectionId;
        label: string;
        icon: string;
    }

    const navSections: NavSection[] = [
        { id: "keyinfo", label: "핵심정보 설정", icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" },
        { id: "llm", label: "LLM 설정", icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
        { id: "summary", label: "PPT 요약 필드", icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
        { id: "phenomenon", label: "발생현상 속성", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" },
        { id: "tutorial", label: "Tutorial", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
    ];

    let activeSection: SectionId = "keyinfo";

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
        summary_fields: SummaryField[];
        use_thumbnails: boolean;
        phenomenon_attributes: string[];
        key_info_settings?: KeyInfoSettings;
        tutorial_project_id?: string;
    }

    let loading = true;
    let saving = false;
    let availableAttributes: AttributeDefinition[] = [];
    let expandedFieldId: string | null = null;
    let expandedKeyInfoCategoryId: string | null = null;

    let settings: Settings = {
        llm: { api_type: "openai", api_endpoint: "", model_name: "" },
        summary_fields: [],
        use_thumbnails: true,
        phenomenon_attributes: [],
        key_info_settings: {
            categories: [],
        },
        tutorial_project_id: undefined,
    };

    function scrollToSection(sectionId: SectionId) {
        activeSection = sectionId;
        const element = document.getElementById(`section-${sectionId}`);
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

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
                    summary_fields: (data.summary_fields || []).map((f: any) => ({
                        id: f.id,
                        name: f.name,
                        order: f.order,
                        system_prompt: f.system_prompt || "",
                        user_prompt: f.user_prompt || "",
                    })),
                    use_thumbnails: data.use_thumbnails ?? true,
                    phenomenon_attributes: data.phenomenon_attributes || [],
                    key_info_settings: data.key_info_settings || {
                        categories: [],
                    },
                    tutorial_project_id: data.tutorial_project_id || undefined,
                };

                // Ensure key_info_settings has categories array
                if (!settings.key_info_settings?.categories) {
                    settings.key_info_settings = {
                        categories: [],
                    };
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

    // Tutorial settings handler
    function handleTutorialUpdate(e: CustomEvent<{ tutorialProjectId: string | undefined }>) {
        settings.tutorial_project_id = e.detail.tutorialProjectId;
    }

    // Key Info settings handlers
    function handleKeyInfoUpdate(e: CustomEvent<{ keyInfoSettings: KeyInfoSettings }>) {
        settings.key_info_settings = e.detail.keyInfoSettings;
    }

    function handleToggleKeyInfoCategoryExpand(e: CustomEvent<{ categoryId: string }>) {
        expandedKeyInfoCategoryId = expandedKeyInfoCategoryId === e.detail.categoryId ? null : e.detail.categoryId;
    }

</script>

<div class="h-screen flex flex-col bg-gray-100">
    <!-- Header -->
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

    <!-- Main Content with Navigation -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Navigation Pane -->
        <nav class="w-64 bg-white border-r border-gray-200 flex-shrink-0 overflow-y-auto">
            <div class="p-4">
                <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">설정 메뉴</h2>
                <ul class="space-y-1">
                    {#each navSections as section}
                        <li>
                            <button
                                class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors
                                    {activeSection === section.id
                                        ? 'bg-blue-50 text-blue-700 font-medium'
                                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}"
                                on:click={() => scrollToSection(section.id)}
                            >
                                <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d={section.icon} />
                                </svg>
                                <span class="text-sm">{section.label}</span>
                            </button>
                        </li>
                    {/each}
                </ul>
            </div>
        </nav>

        <!-- Content Area -->
        <div class="flex-1 overflow-y-auto p-8">
            {#if loading}
                <div class="text-center text-gray-500">로딩 중...</div>
            {:else}
                <div class="max-w-4xl mx-auto space-y-8">
                    <!-- 핵심정보 설정 -->
                    <div id="section-keyinfo">
                        <KeyInfoSettingsSection
                            keyInfoSettings={settings.key_info_settings || { categories: [] }}
                            expandedCategoryId={expandedKeyInfoCategoryId}
                            on:update={handleKeyInfoUpdate}
                            on:toggleCategoryExpand={handleToggleKeyInfoCategoryExpand}
                        />
                    </div>

                    <!-- LLM 설정 (요약) -->
                    <div id="section-llm">
                        <LLMSettingsSection bind:llm={settings.llm} />
                    </div>

                    <!-- PPT 요약 필드 -->
                    <div id="section-summary">
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
                    </div>

                    <!-- 발생현상 속성 설정 -->
                    <div id="section-phenomenon">
                        <PhenomenonAttributesSection
                            {availableAttributes}
                            selectedAttributes={settings.phenomenon_attributes}
                            on:toggle={handleTogglePhenomenonAttribute}
                        />
                    </div>

                    <!-- Tutorial 설정 -->
                    <div id="section-tutorial">
                        <TutorialSettingsSection
                            tutorialProjectId={settings.tutorial_project_id}
                            on:update={handleTutorialUpdate}
                        />
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>
