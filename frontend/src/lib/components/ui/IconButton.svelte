<script lang="ts">
    import { createEventDispatcher } from 'svelte';

    export let variant: 'default' | 'danger' | 'success' | 'primary' | 'ghost' = 'default';
    export let size: 'xs' | 'sm' | 'md' = 'sm';
    export let disabled: boolean = false;
    export let title: string = '';
    export let ariaLabel: string = '';

    const dispatch = createEventDispatcher<{ click: MouseEvent }>();

    const baseClasses = 'inline-flex items-center justify-center rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed';

    const variants: Record<typeof variant, string> = {
        default: 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 focus:ring-gray-300',
        danger: 'text-gray-300 hover:text-red-500 hover:bg-red-50 focus:ring-red-300',
        success: 'text-gray-400 hover:text-green-500 hover:bg-green-50 focus:ring-green-300',
        primary: 'text-gray-400 hover:text-blue-500 hover:bg-blue-50 focus:ring-blue-300',
        ghost: 'text-gray-400 hover:text-gray-600 focus:ring-gray-200',
    };

    const sizes: Record<typeof size, string> = {
        xs: 'p-0.5',
        sm: 'p-1',
        md: 'p-1.5',
    };

    const iconSizes: Record<typeof size, string> = {
        xs: 'w-3 h-3',
        sm: 'w-3.5 h-3.5',
        md: 'w-4 h-4',
    };

    $: classes = `${baseClasses} ${variants[variant]} ${sizes[size]} ${$$props.class || ''}`;

    function handleClick(event: MouseEvent) {
        if (!disabled) {
            dispatch('click', event);
        }
    }
</script>

<button
    type="button"
    class={classes}
    {disabled}
    {title}
    aria-label={ariaLabel || title}
    on:click|stopPropagation={handleClick}
    {...$$restProps}
>
    <span class={iconSizes[size]}>
        <slot />
    </span>
</button>
