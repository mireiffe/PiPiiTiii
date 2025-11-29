<script>
  import { onMount } from 'svelte';

  let projects = [];
  let loading = true;

  onMount(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/projects');
      if (res.ok) {
        projects = await res.json();
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });
</script>

<div class="min-h-screen bg-gray-100 p-8">
  <div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-gray-800">PiPiiTiii</h1>
      <a
        href="/upload"
        class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition shadow-md"
      >
        Upload New PPT
      </a>
    </div>

    {#if loading}
      <div class="text-center py-20">
        <p class="text-gray-500 text-lg">Loading projects...</p>
      </div>
    {:else if projects.length === 0}
      <div class="bg-white rounded-xl shadow-sm p-12 text-center">
        <p class="text-gray-500 text-lg mb-4">No projects found.</p>
        <a
          href="/upload"
          class="text-blue-600 hover:underline font-medium"
        >
          Upload your first PPT file
        </a>
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each projects as project}
          <a
            href={`/viewer/${project.id}`}
            class="block bg-white rounded-xl shadow-sm hover:shadow-md transition p-6 border border-gray-100"
          >
            <div class="flex justify-between items-start mb-4">
              <div class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                PPTX
              </div>
              <span class="text-gray-400 text-sm">
                {new Date(project.created_at).toLocaleDateString()}
              </span>
            </div>
            <h2 class="text-xl font-bold text-gray-800 mb-2 truncate" title={project.name}>
              {project.name}
            </h2>
            <div class="text-gray-500 text-sm">
              <p>Slides: {project.slide_count}</p>
              <p>Author: {project.author}</p>
            </div>
          </a>
        {/each}
      </div>
    {/if}
  </div>
</div>
