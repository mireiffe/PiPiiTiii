<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import type { StepAttachment } from '$lib/types/workflow';
	import { getAttachmentImageUrl } from '$lib/api/project';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher<{
		save: { caption: string; text: string };
		delete: void;
		close: void;
	}>();

	export let attachment: StepAttachment;
	export let caption: string = '';

	let textContent = attachment.data || '';

	// Get image URL: use API for imageId, fallback to base64 data for legacy
	$: imageUrl = attachment.imageId
		? getAttachmentImageUrl(attachment.imageId)
		: attachment.data || '';

	function handleSave() {
		dispatch('save', { caption, text: textContent });
	}

	function handleDelete() {
		dispatch('delete');
	}

	function handleClose() {
		dispatch('close');
	}
</script>

<div
	class="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4"
	transition:fade={{ duration: 150 }}
	on:click={handleClose}
>
	<div
		class="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col"
		transition:fly={{ y: 20, duration: 200 }}
		on:click|stopPropagation
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50/50"
		>
			<h3 class="text-sm font-semibold text-gray-800">
				{attachment.type === 'image' ? '이미지 첨부' : '텍스트 첨부'}
			</h3>
			<button
				class="p-1 hover:bg-gray-200 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
				on:click={handleClose}
			>
				<svg
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-4 space-y-4">
			{#if attachment.type === 'image'}
				<div class="rounded-lg overflow-hidden border border-gray-200 bg-gray-100">
					<img
						src={imageUrl}
						alt="Attachment"
						class="w-full max-h-[400px] object-contain"
					/>
				</div>
				<div class="space-y-1.5">
					<label class="block text-xs font-medium text-gray-600">캡션</label>
					<input
						type="text"
						bind:value={caption}
						placeholder="이미지에 대한 설명을 입력하세요"
						class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
					/>
				</div>
			{:else}
				<div class="space-y-1.5">
					<label class="block text-xs font-medium text-gray-600">내용</label>
					<textarea
						bind:value={textContent}
						placeholder="텍스트 내용"
						rows="6"
						class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 resize-none"
					></textarea>
				</div>
			{/if}

			<div class="text-[10px] text-gray-400">
				추가됨: {new Date(attachment.createdAt).toLocaleString('ko-KR')}
			</div>
		</div>

		<!-- Footer -->
		<div
			class="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50/50"
		>
			<button
				class="px-3 py-1.5 text-xs text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
				on:click={handleDelete}
			>
				삭제
			</button>
			<div class="flex gap-2">
				<button
					class="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
					on:click={handleClose}
				>
					취소
				</button>
				<button
					class="px-4 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
					on:click={handleSave}
				>
					저장
				</button>
			</div>
		</div>
	</div>
</div>