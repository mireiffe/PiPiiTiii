<script lang="ts">
  import { onMount } from "svelte";
  import { fetchSettings, updateSettings, fetchAllAttributes } from "$lib/api/project";
  import type { WorkflowStepColumn, WorkflowStepRow, WorkflowSteps } from "$lib/types/workflow";

  interface AttributeDefinition {
    key: string;
    display_name: string;
    attr_type: {
      variant: string;
    };
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
    workflow_prompts?: {
      system_prompt: string;
      user_prompt: string;
    };
    summary_fields: SummaryField[];
    use_thumbnails: boolean;
    phenomenon_attributes: string[];
    workflow_steps: WorkflowSteps;
  }

  let loading = true;
  let saving = false;
  let availableAttributes: AttributeDefinition[] = [];
  let settings: Settings = {
    llm: {
      api_type: "openai",
      api_endpoint: "",
      model_name: "",
    },
    workflow_llm: {
      api_type: "openai",
      api_endpoint: "",
      model_name: "",
    },
    workflow_prompts: {
      system_prompt: "",
      user_prompt: "",
    },
    summary_fields: [],
    use_thumbnails: true,
    phenomenon_attributes: [],
    workflow_steps: {
      columns: [],
      rows: [],
    },
  };

  // Expanded field for editing prompts
  let expandedFieldId: string | null = null;
  // Expanded row for editing
  let expandedRowId: string | null = null;
  // Adding new column mode
  let addingColumn = false;
  let newColumnName = "";

  const DEFAULT_COLUMNS: WorkflowStepColumn[] = [
    { id: "step_category", name: "스텝 구분", isDefault: true },
    { id: "system", name: "System", isDefault: true },
    { id: "access_target", name: "접근 Target", isDefault: true },
    { id: "purpose", name: "목적", isDefault: true },
    { id: "related_db_table", name: "연관 DB Table", isDefault: true },
  ];

  onMount(async () => {
    try {
      // Load settings and available attributes in parallel
      const [settingsRes, attrsRes] = await Promise.all([
        fetchSettings(),
        fetchAllAttributes()
      ]);

      if (attrsRes.ok) {
        availableAttributes = await attrsRes.json();
      }

      if (settingsRes.ok) {
        const data = await settingsRes.json();
        // Ensure llm has all required fields with defaults
        settings = {
          llm: {
            api_type: data.llm?.api_type || "openai",
            api_endpoint: data.llm?.api_endpoint || "",
            model_name: data.llm?.model_name || "",
          },
          workflow_llm: {
            api_type:
              data.workflow_llm?.api_type || data.llm?.api_type || "openai",
            api_endpoint:
              data.workflow_llm?.api_endpoint || data.llm?.api_endpoint || "",
            model_name:
              data.workflow_llm?.model_name || data.llm?.model_name || "",
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
          workflow_steps: data.workflow_steps || {
            columns: DEFAULT_COLUMNS,
            rows: [],
          },
        };

        // Ensure default columns exist
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
      // Clean up empty optional fields if needed, or backend handles it
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

  function addField() {
    const newId = `field_${Date.now()}`;
    const newOrder = settings.summary_fields.length;
    settings.summary_fields = [
      ...settings.summary_fields,
      {
        id: newId,
        name: "새 필드",
        order: newOrder,
        system_prompt: "",
        user_prompt: "",
      },
    ];
    // Auto-expand new field
    expandedFieldId = newId;
  }

  function removeField(index: number) {
    if (confirm("이 필드를 삭제하시겠습니까?")) {
      settings.summary_fields = settings.summary_fields.filter(
        (_, i) => i !== index,
      );
      // Reorder
      settings.summary_fields = settings.summary_fields.map((field, i) => ({
        ...field,
        order: i,
      }));
    }
  }

  function moveFieldUp(index: number) {
    if (index === 0) return;
    const temp = settings.summary_fields[index - 1];
    settings.summary_fields[index - 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i,
    }));
  }

  function moveFieldDown(index: number) {
    if (index === settings.summary_fields.length - 1) return;
    const temp = settings.summary_fields[index + 1];
    settings.summary_fields[index + 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i,
    }));
  }

  function toggleExpand(fieldId: string) {
    if (expandedFieldId === fieldId) {
      expandedFieldId = null;
    } else {
      expandedFieldId = fieldId;
    }
  }

  // ========== Phenomenon Attributes Management ==========

  function togglePhenomenonAttribute(key: string) {
    if (settings.phenomenon_attributes.includes(key)) {
      settings.phenomenon_attributes = settings.phenomenon_attributes.filter(k => k !== key);
    } else {
      settings.phenomenon_attributes = [...settings.phenomenon_attributes, key];
    }
  }

  // ========== Workflow Steps Management ==========

  function addWorkflowStepColumn() {
    if (!newColumnName.trim()) {
      alert("컬럼 이름을 입력해주세요.");
      return;
    }
    const newId = `col_${Date.now()}`;
    settings.workflow_steps.columns = [
      ...settings.workflow_steps.columns,
      {
        id: newId,
        name: newColumnName.trim(),
        isDefault: false,
      },
    ];
    newColumnName = "";
    addingColumn = false;
  }

  function removeWorkflowStepColumn(columnId: string) {
    const column = settings.workflow_steps.columns.find(c => c.id === columnId);
    if (column?.isDefault) {
      alert("기본 컬럼은 삭제할 수 없습니다.");
      return;
    }
    if (confirm("이 컬럼을 삭제하시겠습니까? 모든 row에서 해당 컬럼의 값이 삭제됩니다.")) {
      settings.workflow_steps.columns = settings.workflow_steps.columns.filter(c => c.id !== columnId);
      // Remove column from all rows
      settings.workflow_steps.rows = settings.workflow_steps.rows.map(row => {
        const newValues = { ...row.values };
        delete newValues[columnId];
        return { ...row, values: newValues };
      });
    }
  }

  function addWorkflowStepRow() {
    const newId = `row_${Date.now()}`;
    const newRow: WorkflowStepRow = {
      id: newId,
      values: {},
    };
    // Initialize with empty values for all columns
    settings.workflow_steps.columns.forEach(col => {
      newRow.values[col.id] = "";
    });
    settings.workflow_steps.rows = [...settings.workflow_steps.rows, newRow];
    expandedRowId = newId;
  }

  function removeWorkflowStepRow(rowId: string) {
    if (confirm("이 스텝을 삭제하시겠습니까?")) {
      settings.workflow_steps.rows = settings.workflow_steps.rows.filter(r => r.id !== rowId);
    }
  }

  function toggleRowExpand(rowId: string) {
    if (expandedRowId === rowId) {
      expandedRowId = null;
    } else {
      expandedRowId = rowId;
    }
  }

  function moveRowUp(index: number) {
    if (index === 0) return;
    const temp = settings.workflow_steps.rows[index - 1];
    settings.workflow_steps.rows[index - 1] = settings.workflow_steps.rows[index];
    settings.workflow_steps.rows[index] = temp;
    settings.workflow_steps.rows = [...settings.workflow_steps.rows];
  }

  function moveRowDown(index: number) {
    if (index === settings.workflow_steps.rows.length - 1) return;
    const temp = settings.workflow_steps.rows[index + 1];
    settings.workflow_steps.rows[index + 1] = settings.workflow_steps.rows[index];
    settings.workflow_steps.rows[index] = temp;
    settings.workflow_steps.rows = [...settings.workflow_steps.rows];
  }

  // Get display value for a row (first non-empty column value for preview)
  function getRowPreview(row: WorkflowStepRow): string {
    const stepCategory = row.values["step_category"];
    const system = row.values["system"];
    const purpose = row.values["purpose"];

    if (stepCategory && purpose) {
      return `[${stepCategory}] ${purpose}`;
    } else if (stepCategory) {
      return `[${stepCategory}]`;
    } else if (purpose) {
      return purpose;
    }
    return "(비어있음)";
  }
</script>

<div class="h-screen flex flex-col bg-gray-100">
  <div
    class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm"
  >
    <div>
      <h1 class="text-2xl font-bold text-gray-800">설정</h1>
      <a href="/" class="text-sm text-blue-600 hover:underline"
        >← 대시보드로 돌아가기</a
      >
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
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">
            요약 생성 LLM 설정
          </h2>
          <p class="text-sm text-gray-500 mb-4">
            자동 요약 생성에 사용할 LLM API를 설정합니다. API Key는 백엔드의
            .env 파일에서 LLM_API_KEY로 설정해주세요.
          </p>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API 연결 형식
              </label>
              <select
                bind:value={settings.llm.api_type}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="openai">OpenAI API</option>
                <option value="gemini">Google Gemini API</option>
                <option value="openai_compatible"
                  >OpenAI Compatible (직접 호출)</option
                >
              </select>
              <p class="text-xs text-gray-400 mt-1">
                {#if settings.llm.api_type === "openai"}
                  OpenAI 공식 SDK를 사용합니다.
                {:else if settings.llm.api_type === "gemini"}
                  Google Generative AI SDK를 사용합니다.
                {:else}
                  Bearer 토큰 인증으로 직접 API를 호출합니다.
                {/if}
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                API Endpoint
              </label>
              <input
                type="text"
                bind:value={settings.llm.api_endpoint}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={settings.llm.api_type === "gemini"
                  ? "https://generativelanguage.googleapis.com/v1beta"
                  : "https://api.openai.com/v1"}
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Model Name
              </label>
              <input
                type="text"
                bind:value={settings.llm.model_name}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={settings.llm.api_type === "gemini"
                  ? "gemini-1.5-flash"
                  : "gpt-4o"}
              />
            </div>
          </div>
        </div>

        <!-- PPT 요약 필드 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-800">PPT 요약 필드</h2>
              <p class="text-sm text-gray-500 mt-1">
                각 필드별로 LLM에 전달할 프롬프트를 설정합니다.
              </p>
            </div>
            <button
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
              on:click={addField}
            >
              + 필드 추가
            </button>
          </div>

          <div class="space-y-3">
            {#if settings.summary_fields.length === 0}
              <div class="text-center text-gray-400 py-8">
                필드가 없습니다. 필드를 추가해주세요.
              </div>
            {:else}
              {#each settings.summary_fields as field, index (field.id)}
                <div
                  class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden"
                >
                  <!-- Field Header -->
                  <div class="flex items-center gap-3 p-4">
                    <div class="flex flex-col gap-1">
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                        on:click={() => moveFieldUp(index)}
                        disabled={index === 0}
                        title="위로 이동"
                      >
                        ▲
                      </button>
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                        on:click={() => moveFieldDown(index)}
                        disabled={index === settings.summary_fields.length - 1}
                        title="아래로 이동"
                      >
                        ▼
                      </button>
                    </div>

                    <div class="flex-1 flex items-center gap-3">
                      <div class="flex-1">
                        <label class="block text-xs text-gray-500 mb-1"
                          >필드명</label
                        >
                        <input
                          type="text"
                          bind:value={field.name}
                          class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="필드 이름"
                        />
                      </div>
                      <div class="w-48">
                        <label class="block text-xs text-gray-500 mb-1"
                          >ID (읽기전용)</label
                        >
                        <input
                          type="text"
                          value={field.id}
                          readonly
                          class="w-full border border-gray-200 rounded px-3 py-2 bg-gray-100 text-gray-500 text-sm"
                        />
                      </div>
                    </div>

                    <button
                      class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                      on:click={() => toggleExpand(field.id)}
                      title="프롬프트 설정"
                    >
                      {expandedFieldId === field.id ? "▼ 접기" : "▶ 프롬프트"}
                    </button>

                    <button
                      class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                      on:click={() => removeField(index)}
                    >
                      삭제
                    </button>
                  </div>

                  <!-- Expanded Prompt Section -->
                  {#if expandedFieldId === field.id}
                    <div
                      class="border-t border-gray-200 p-4 bg-white space-y-4"
                    >
                      <div>
                        <label
                          class="block text-sm font-medium text-gray-700 mb-2"
                        >
                          System Prompt
                        </label>
                        <textarea
                          bind:value={field.system_prompt}
                          class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          rows="3"
                          placeholder="LLM의 역할과 행동 지침을 정의합니다. 예: 당신은 PPT 문서를 분석하는 전문가입니다."
                        ></textarea>
                      </div>

                      <div>
                        <label
                          class="block text-sm font-medium text-gray-700 mb-2"
                        >
                          User Query Prompt
                        </label>
                        <textarea
                          bind:value={field.user_prompt}
                          class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          rows="3"
                          placeholder="실제 요청 내용입니다. 예: 이 슬라이드들의 핵심 내용을 3줄로 요약해주세요."
                        ></textarea>
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- 발생현상 속성 설정 -->
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
                  class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors {settings.phenomenon_attributes.includes(attr.key)
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-gray-50 border-gray-200 hover:bg-gray-100'}"
                >
                  <input
                    type="checkbox"
                    checked={settings.phenomenon_attributes.includes(attr.key)}
                    on:change={() => togglePhenomenonAttribute(attr.key)}
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

        <!-- 워크플로우 스텝 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-800">워크플로우 스텝</h2>
              <p class="text-sm text-gray-500 mt-1">
                워크플로우에서 사용할 스텝들을 정의합니다. 기본 컬럼은 삭제할 수 없습니다.
              </p>
            </div>
            <div class="flex gap-2">
              {#if addingColumn}
                <div class="flex items-center gap-2">
                  <input
                    type="text"
                    bind:value={newColumnName}
                    placeholder="컬럼 이름"
                    class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    on:keypress={(e) => e.key === 'Enter' && addWorkflowStepColumn()}
                  />
                  <button
                    class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                    on:click={addWorkflowStepColumn}
                  >
                    추가
                  </button>
                  <button
                    class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                    on:click={() => { addingColumn = false; newColumnName = ""; }}
                  >
                    취소
                  </button>
                </div>
              {:else}
                <button
                  class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition text-sm font-medium"
                  on:click={() => addingColumn = true}
                >
                  + 컬럼 추가
                </button>
              {/if}
              <button
                class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
                on:click={addWorkflowStepRow}
              >
                + 스텝 추가
              </button>
            </div>
          </div>

          <!-- Column Headers -->
          <div class="mb-4 border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-100 px-4 py-3">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-700 mr-2">컬럼:</span>
                {#each settings.workflow_steps.columns as column (column.id)}
                  <div class="flex items-center gap-1 bg-white rounded px-2 py-1 border {column.isDefault ? 'border-blue-300' : 'border-gray-300'}">
                    <input
                      type="text"
                      bind:value={column.name}
                      class="border-none bg-transparent text-sm focus:outline-none w-24"
                      title={column.isDefault ? "기본 컬럼 (삭제 불가)" : "커스텀 컬럼"}
                    />
                    {#if column.isDefault}
                      <span class="text-blue-500 text-xs" title="기본 컬럼">★</span>
                    {:else}
                      <button
                        class="text-red-400 hover:text-red-600 text-xs"
                        on:click={() => removeWorkflowStepColumn(column.id)}
                        title="컬럼 삭제"
                      >
                        ✕
                      </button>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          </div>

          <!-- Rows -->
          <div class="space-y-3">
            {#if settings.workflow_steps.rows.length === 0}
              <div class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg">
                정의된 스텝이 없습니다. 스텝을 추가해주세요.
              </div>
            {:else}
              {#each settings.workflow_steps.rows as row, index (row.id)}
                <div class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
                  <!-- Row Header -->
                  <div class="flex items-center gap-3 p-4">
                    <div class="flex flex-col gap-1">
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                        on:click={() => moveRowUp(index)}
                        disabled={index === 0}
                        title="위로 이동"
                      >
                        ▲
                      </button>
                      <button
                        class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                        on:click={() => moveRowDown(index)}
                        disabled={index === settings.workflow_steps.rows.length - 1}
                        title="아래로 이동"
                      >
                        ▼
                      </button>
                    </div>

                    <div class="flex-1">
                      <span class="text-sm font-medium text-gray-800">
                        {getRowPreview(row)}
                      </span>
                      <span class="text-xs text-gray-400 ml-2">ID: {row.id}</span>
                    </div>

                    <button
                      class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                      on:click={() => toggleRowExpand(row.id)}
                      title="상세 편집"
                    >
                      {expandedRowId === row.id ? "▼ 접기" : "▶ 편집"}
                    </button>

                    <button
                      class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                      on:click={() => removeWorkflowStepRow(row.id)}
                    >
                      삭제
                    </button>
                  </div>

                  <!-- Expanded Row Section -->
                  {#if expandedRowId === row.id}
                    <div class="border-t border-gray-200 p-4 bg-white">
                      <div class="grid grid-cols-2 gap-4">
                        {#each settings.workflow_steps.columns as column (column.id)}
                          <div>
                            <label class="block text-xs font-medium text-gray-600 mb-1">
                              {column.name}
                              {#if column.isDefault}
                                <span class="text-blue-500">★</span>
                              {/if}
                            </label>
                            <input
                              type="text"
                              bind:value={row.values[column.id]}
                              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="{column.name} 입력"
                            />
                          </div>
                        {/each}
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
