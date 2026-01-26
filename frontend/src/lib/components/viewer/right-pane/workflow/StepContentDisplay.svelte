<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { StepCapture, StepAttachment } from "$lib/types/workflow";
    import CaptureCard from "./CaptureCard.svelte";
    import ImageAttachmentCard from "./ImageAttachmentCard.svelte";
    import TextAttachmentCard from "./TextAttachmentCard.svelte";

    export let captures: StepCapture[] = [];
    export let attachments: StepAttachment[] = [];
    export let projectId: string = "";
    export let slideWidth: number = 960;
    export let slideHeight: number = 540;
    export let showRecaptureButton = false;

    const dispatch = createEventDispatcher<{
        removeCapture: { captureId: string };
        recapture: { captureId: string };
        openAttachment: { attachment: StepAttachment };
        updateAttachment: { attachmentId: string; data: string };
        removeAttachment: { attachmentId: string };
    }>();

    $: imageAttachments = attachments.filter(
        (a) => a.type === "image" && a.imageId,
    );
    $: textAttachments = attachments.filter(
        (a) => a.type !== "image" || !a.imageId,
    );
</script>

{#if captures.length > 0 || attachments.length > 0}
    <div class="flex flex-col gap-2">
        <!-- Captures -->
        {#if captures.length > 0}
            <div class="grid {captures.length >= 2 ? 'grid-cols-2' : 'grid-cols-1'} gap-2">
                {#each captures as capture (capture.id)}
                    <CaptureCard
                        {capture}
                        {projectId}
                        {slideWidth}
                        {slideHeight}
                        {showRecaptureButton}
                        on:remove={() =>
                            dispatch("removeCapture", {
                                captureId: capture.id,
                            })}
                        on:recapture={() =>
                            dispatch("recapture", { captureId: capture.id })}
                    />
                {/each}
            </div>
        {/if}

        <!-- Image Attachments -->
        {#if imageAttachments.length > 0}
            <div class="grid {imageAttachments.length >= 2 ? 'grid-cols-2' : 'grid-cols-1'} gap-2">
                {#each imageAttachments as attachment (attachment.id)}
                    <ImageAttachmentCard
                        imageId={attachment.imageId || ""}
                        caption={attachment.caption}
                        on:click={() =>
                            dispatch("openAttachment", { attachment })}
                        on:remove={() =>
                            dispatch("removeAttachment", {
                                attachmentId: attachment.id,
                            })}
                    />
                {/each}
            </div>
        {/if}

        <!-- Text Attachments -->
        {#if textAttachments.length > 0}
            <div class="flex flex-col gap-1.5">
                {#each textAttachments as attachment (attachment.id)}
                    <TextAttachmentCard
                        {attachment}
                        on:update={(e) =>
                            dispatch("updateAttachment", {
                                attachmentId: attachment.id,
                                data: e.detail.data,
                            })}
                        on:remove={() =>
                            dispatch("removeAttachment", {
                                attachmentId: attachment.id,
                            })}
                    />
                {/each}
            </div>
        {/if}
    </div>
{/if}
