<script>
  import { goto } from "$app/navigation";

  let files;
  let uploading = false;
  let error = null;
  let progress = 0;
  let statusMessage = "";

  async function handleUpload() {
    if (!files || files.length === 0) return;

    uploading = true;
    error = null;
    progress = 0;
    statusMessage = "Uploading...";

    const formData = new FormData();
    formData.append("file", files[0]);

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }

      const data = await res.json();
      const projectId = data.id;

      // Poll for status
      while (true) {
        const statusRes = await fetch(
          `http://localhost:8000/api/project/${projectId}/status`,
        );

        if (statusRes.ok) {
          const statusData = await statusRes.json();
          progress = statusData.percent ?? progress;
          statusMessage = statusData.message ?? statusMessage;

          if (statusData.status === "done") {
            progress = 100;
            statusMessage = statusData.message || "Processing complete";
            uploading = false;
            await goto("/");
            break;
          } else if (statusData.status === "error") {
            throw new Error(statusData.message || "Processing failed");
          }
        } else {
          statusMessage = "Waiting for parsing status...";
        }

        await new Promise((r) => setTimeout(r, 1000));
      }
    } catch (e) {
      error = e.message;
    } finally {
      uploading = false;
    }
  }
</script>

<div class="min-h-screen bg-gray-100 flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
    <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">
      Upload Presentation
    </h1>

    <div class="mb-6">
      <label
        for="file-upload"
        class="flex flex-col items-center justify-center w-full h-64 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition"
      >
        <div class="flex flex-col items-center justify-center pt-5 pb-6">
          <svg
            class="w-10 h-10 mb-3 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            ></path></svg
          >
          <p class="mb-2 text-sm text-gray-500">
            <span class="font-semibold">Click to upload</span> or drag and drop
          </p>
          <p class="text-xs text-gray-500">PPTX files only</p>
        </div>
        <input
          id="file-upload"
          type="file"
          class="hidden"
          accept=".pptx"
          bind:files
          on:change={handleUpload}
        />
      </label>
    </div>

    {#if uploading}
      <div class="text-center">
        <div class="mb-2 flex justify-between text-sm text-gray-600">
          <span>{statusMessage}</span>
          <span>{progress}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5 mb-4">
          <div
            class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            style="width: {progress}%"
          ></div>
        </div>
      </div>
    {/if}

    {#if error}
      <div class="bg-red-50 text-red-600 p-4 rounded-lg text-sm text-center">
        {error}
      </div>
    {/if}

    <div class="mt-6 text-center">
      <a href="/" class="text-gray-500 hover:text-gray-700 text-sm"
        >Cancel and go back</a
      >
    </div>
  </div>
</div>
