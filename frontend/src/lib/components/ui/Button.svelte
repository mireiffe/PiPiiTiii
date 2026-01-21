<script lang="ts">
    import { createEventDispatcher } from 'svelte';

    export let variant: 'primary' | 'secondary' | 'destructive' | 'ghost' | 'outline' | 'success' = 'primary';
    export let size: 'xs' | 'sm' | 'md' | 'lg' = 'md';
    export let disabled: boolean = false;
    export let loading: boolean = false;
    export let type: 'button' | 'submit' | 'reset' = 'button';
    export let title: string = '';
    export let href: string = '';

    const dispatch = createEventDispatcher<{ click: MouseEvent }>();

    const baseClasses =
        'inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg active:scale-[0.98]';

    const variants: Record<typeof variant, string> = {
        primary:
            'bg-indigo-600 hover:bg-indigo-700 text-white shadow-md hover:shadow-lg focus:ring-indigo-500',
        secondary:
            'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 shadow-sm hover:shadow-md focus:ring-gray-200',
        destructive:
            'bg-white hover:bg-red-50 text-red-600 border border-red-200 shadow-sm hover:shadow-md focus:ring-red-200',
        ghost: 'bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-900',
        outline:
            'bg-transparent border border-gray-300 text-gray-700 hover:bg-gray-50 hover:text-gray-900',
        success:
            'bg-emerald-100 hover:bg-emerald-200 text-emerald-700 border border-transparent shadow-sm hover:shadow-md',
    };

    const sizes: Record<typeof size, string> = {
        xs: 'text-[10px] px-2 py-1',
        sm: 'text-xs px-2.5 py-1.5',
        md: 'text-sm px-4 py-2',
        lg: 'text-base px-6 py-3',
    };

    $: classes = `${baseClasses} ${variants[variant]} ${sizes[size]} ${$$props.class || ''}`;

    function handleClick(event: MouseEvent) {
        if (!disabled && !loading) {
            dispatch('click', event);
        }
    }
</script>

{#if href}
    <a {href} class={classes} {title} {...$$restProps}>
        <slot />
    </a>
{:else}
    <button {type} class={classes} disabled={disabled || loading} {title} on:click={handleClick} {...$$restProps}>
        {#if loading}
            <svg
                class="animate-spin -ml-1 mr-2 h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
            >
                <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                ></circle>
                <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
            </svg>
        {/if}
        <slot />
    </button>
{/if}
