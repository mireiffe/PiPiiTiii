<script lang="ts">
  import { onMount } from "svelte";
  import { fetchSettings, updateSettings } from "$lib/api/project";

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
  }

  let loading = true;
  let saving = false;
  let settings: Settings = {
    llm: {
      api_type: "openai",
      api_endpoint: "",
      model_name: ""
    },
    summary_fields: [],
    use_thumbnails: true
  };

  // Expanded field for editing prompts
  let expandedFieldId: string | null = null;

  onMount(async () => {
    try {
      const res = await fetchSettings();
      if (res.ok) {
        const data = await res.json();
        // Ensure llm has all required fields with defaults
        settings = {
          llm: {
            api_type: data.llm?.api_type || "openai",
            api_endpoint: data.llm?.api_endpoint || "",
            model_name: data.llm?.model_name || ""
          },
          summary_fields: (data.summary_fields || []).map(f => ({
            id: f.id,
            name: f.name,
            order: f.order,
            system_prompt: f.system_prompt || "",
            user_prompt: f.user_prompt || ""
          })),
          use_thumbnails: data.use_thumbnails ?? true
        };
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

  function addField() {
    const newId = `field_${Date.now()}`;
    const newOrder = settings.summary_fields.length;
    settings.summary_fields = [...settings.summary_fields, {
      id: newId,
      name: "새 필드",
      order: newOrder,
      system_prompt: "",
      user_prompt: ""
    }];
    // Auto-expand new field
    expandedFieldId = newId;
  }

  function removeField(index: number) {
    if (confirm("이 필드를 삭제하시겠습니까?")) {
      settings.summary_fields = settings.summary_fields.filter((_, i) => i !== index);
      // Reorder
      settings.summary_fields = settings.summary_fields.map((field, i) => ({
        ...field,
        order: i
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
      order: i
    }));
  }

  function moveFieldDown(index: number) {
    if (index === settings.summary_fields.length - 1) return;
    const temp = settings.summary_fields[index + 1];
    settings.summary_fields[index + 1] = settings.summary_fields[index];
    settings.summary_fields[index] = temp;
    settings.summary_fields = settings.summary_fields.map((field, i) => ({
      ...field,
      order: i
    }));
  }

  function toggleExpand(fieldId: string) {
    if (expandedFieldId === fieldId) {
      expandedFieldId = null;
    } else {
      expandedFieldId = fieldId;
    }
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
        <!-- LLM 설정 -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">LLM 설정</h2>
          <p class="text-sm text-gray-500 mb-4">
            자동 요약 생성에 사용할 LLM API를 설정합니다. API Key는 백엔드의 .env 파일에서 LLM_API_KEY로 설정해주세요.
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
                <option value="openai_compatible">OpenAI Compatible (직접 호출)</option>
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
                placeholder={settings.llm.api_type === "gemini" ? "https://generativelanguage.googleapis.com/v1beta" : "https://api.openai.com/v1"}
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
                placeholder={settings.llm.api_type === "gemini" ? "gemini-1.5-flash" : "gpt-4o"}
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
                <div class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
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
                        <label class="block text-xs text-gray-500 mb-1">필드명</label>
                        <input
                          type="text"
                          bind:value={field.name}
                          class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="필드 이름"
                        />
                      </div>
                      <div class="w-48">
                        <label class="block text-xs text-gray-500 mb-1">ID (읽기전용)</label>
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
                    <div class="border-t border-gray-200 p-4 bg-white space-y-4">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
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
                        <label class="block text-sm font-medium text-gray-700 mb-2">
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
      </div>
    {/if}
  </div>
</div>
