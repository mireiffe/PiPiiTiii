<script lang="ts">
    export let llm: { api_type: string; api_endpoint: string; model_name: string };
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-4">요약 생성 LLM 설정</h2>
    <p class="text-sm text-gray-500 mb-4">
        자동 요약 생성에 사용할 LLM API를 설정합니다. API Key는 백엔드의 .env 파일에서 LLM_API_KEY로 설정해주세요.
    </p>

    <div class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">API 연결 형식</label>
            <select
                bind:value={llm.api_type}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
                <option value="openai">OpenAI API</option>
                <option value="gemini">Google Gemini API</option>
                <option value="openai_compatible">OpenAI Compatible (직접 호출)</option>
            </select>
            <p class="text-xs text-gray-400 mt-1">
                {#if llm.api_type === "openai"}
                    OpenAI 공식 SDK를 사용합니다.
                {:else if llm.api_type === "gemini"}
                    Google Generative AI SDK를 사용합니다.
                {:else}
                    Bearer 토큰 인증으로 직접 API를 호출합니다.
                {/if}
            </p>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">API Endpoint</label>
            <input
                type="text"
                bind:value={llm.api_endpoint}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={llm.api_type === "gemini" ? "https://generativelanguage.googleapis.com/v1beta" : "https://api.openai.com/v1"}
            />
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Model Name</label>
            <input
                type="text"
                bind:value={llm.model_name}
                class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={llm.api_type === "gemini" ? "gemini-1.5-flash" : "gpt-4o"}
            />
        </div>
    </div>
</div>
