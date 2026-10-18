const floating = 'bg-muted rounded-lg shadow-(--shadow-elev)'

const field = {
  xs: { base: 'min-h-(--ctl-default) px-(--px-field) py-0 text-(length:--field-text) gap-1.5', leading: 'ps-(--px-field)', trailing: 'pe-(--px-field)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
  sm: { base: 'min-h-(--ctl-field-sm) px-(--px-field) py-0 text-(length:--field-text) gap-1.5', leading: 'ps-(--px-field)', trailing: 'pe-(--px-field)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
  md: { base: 'min-h-(--ctl-medium) px-(--px-field) py-0 text-(length:--field-text) gap-1.5', leading: 'ps-(--px-field)', trailing: 'pe-(--px-field)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
  lg: { base: 'min-h-(--ctl-large) px-(--px-field) py-0 text-(length:--field-text) gap-2', leading: 'ps-(--px-field)', trailing: 'pe-(--px-field)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
  xl: { base: 'min-h-(--ctl-touch) px-(--px-field) py-0 text-base gap-2', leading: 'ps-(--px-field)', trailing: 'pe-(--px-field)', leadingIcon: 'size-5', trailingIcon: 'size-5' }
}

const fieldPadding = [
  { leading: true, class: 'ps-(--ps-icon)' },
  { trailing: true, class: 'pe-(--ps-icon)' }
]

const fieldOutline = 'bg-muted hover:bg-muted disabled:bg-muted ring-default hover:ring-accented'

const menuRow = {
  item: 'min-h-(--row-menu) px-(--px-field) py-0 text-sm gap-2 items-center',
  label: 'min-h-(--row-menu) px-(--px-field) py-0 text-xs items-center',
  empty: 'p-2 text-sm',
  itemLeadingIcon: 'size-(--icon-ui)',
  itemTrailingIcon: 'size-(--icon-ui)'
}
const menuSizes = {
  xs: menuRow,
  sm: menuRow,
  md: menuRow,
  lg: menuRow,
  xl: menuRow
}
const fieldMenuSizes = {
  xs: { ...field.xs, ...menuRow },
  sm: { ...field.sm, ...menuRow },
  md: { ...field.md, ...menuRow },
  lg: { ...field.lg, ...menuRow },
  xl: { ...field.xl, ...menuRow }
}

const paletteRow = {
  input: '[&>input]:h-(--ctl-large)',
  empty: 'py-4 text-sm',
  label: 'min-h-(--row-menu) px-(--px-field) py-0 text-xs gap-1.5 items-center',
  item: 'min-h-(--row-menu) px-(--px-field) py-0 text-sm gap-2 items-center before:rounded-sm',
  itemLeadingIcon: 'size-(--icon-ui)',
  itemLeadingChip: 'size-(--icon-ui)',
  itemTrailing: 'gap-1.5',
  itemTrailingIcon: 'size-(--icon-ui)',
  itemTrailingHighlightedIcon: 'size-(--icon-ui)'
}
const paletteSizes = {
  xs: paletteRow,
  sm: paletteRow,
  md: paletteRow,
  lg: paletteRow,
  xl: paletteRow
}

export default defineAppConfig({
  ui: {
    colors: {
      primary: 'jade',
      info: 'blue',
      success: 'green',
      warning: 'yellow',
      error: 'red',
      neutral: 'forest'
    },

    button: {
      slots: { base: 'rounded-sm' },
      variants: {
        size: {
          xs: { base: 'min-h-(--ctl-compact) px-(--px-tight) py-0 text-xs gap-(--gap-ctl)', leadingIcon: 'size-(--icon-sm)', trailingIcon: 'size-(--icon-sm)' },
          sm: { base: 'min-h-(--ctl-default) px-(--px-tight) py-0 text-sm gap-(--gap-ctl)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
          md: { base: 'min-h-(--ctl-medium) px-(--px-normal) py-0 text-sm gap-(--gap-ctl)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
          lg: { base: 'min-h-(--ctl-large) px-(--px-normal) py-0 text-sm gap-(--gap-ctl)', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' },
          xl: { base: 'min-h-(--ctl-touch) px-3 py-0 text-base gap-2', leadingIcon: 'size-(--icon-ui)', trailingIcon: 'size-(--icon-ui)' }
        }
      },
      compoundVariants: [
        { size: 'xs', square: true, class: 'min-h-(--ctl-compact) min-w-(--ctl-compact) p-0 justify-center' },
        { size: 'sm', square: true, class: 'min-h-(--ctl-default) min-w-(--ctl-default) p-0 justify-center' },
        { size: 'md', square: true, class: 'min-h-(--ctl-medium) min-w-(--ctl-medium) p-0 justify-center' },
        { size: 'lg', square: true, class: 'min-h-(--ctl-large) min-w-(--ctl-large) p-0 justify-center' },
        { size: 'xl', square: true, class: 'min-h-(--ctl-touch) min-w-(--ctl-touch) p-0 justify-center' },
        { color: 'neutral', variant: 'soft', class: 'bg-muted hover:bg-elevated active:bg-accented disabled:bg-muted aria-disabled:bg-muted' },
        { color: 'neutral', variant: 'solid', class: 'bg-muted text-default hover:bg-elevated active:bg-accented disabled:bg-muted aria-disabled:bg-muted' },
        { color: 'neutral', variant: 'ghost', class: 'active:bg-accented' },
        { color: 'neutral', variant: 'outline', class: 'bg-transparent ring-default hover:ring-accented hover:bg-elevated active:bg-accented disabled:bg-transparent aria-disabled:bg-transparent' },
        { color: 'primary', variant: 'subtle', class: 'text-default' },
        { color: 'info', variant: 'subtle', class: 'text-default bg-(--ui-info-bg) ring-(color:--ui-info-border) hover:bg-(--ui-info-bg) active:bg-(--ui-info-bg) disabled:bg-(--ui-info-bg) aria-disabled:bg-(--ui-info-bg)' },
        { color: 'success', variant: 'subtle', class: 'text-default bg-(--ui-success-bg) ring-(color:--ui-success-border) hover:bg-(--ui-success-bg) active:bg-(--ui-success-bg) disabled:bg-(--ui-success-bg) aria-disabled:bg-(--ui-success-bg)' },
        { color: 'warning', variant: 'subtle', class: 'text-default bg-(--ui-warning-bg) ring-(color:--ui-warning-border) hover:bg-(--ui-warning-bg) active:bg-(--ui-warning-bg) disabled:bg-(--ui-warning-bg) aria-disabled:bg-(--ui-warning-bg)' },
        { color: 'error', variant: 'subtle', class: 'text-default bg-(--ui-error-bg) ring-(color:--ui-error-border) hover:bg-(--ui-error-bg) active:bg-(--ui-error-bg) disabled:bg-(--ui-error-bg) aria-disabled:bg-(--ui-error-bg)' },
        { color: 'primary', variant: 'solid', class: 'text-(color:--ui-on-primary)' }
      ],
      defaultVariants: { size: 'sm' }
    },

    input: {
      slots: { base: 'rounded-sm' },
      variants: {
        size: field,
        variant: { outline: fieldOutline }
      },
      compoundVariants: [
        ...fieldPadding,
        { fixed: false, size: 'xs', class: 'md:text-(length:--field-text)' },
        { fixed: false, size: 'sm', class: 'md:text-(length:--field-text)' }
      ],
      defaultVariants: { size: 'md' }
    },

    select: {
      slots: {
        base: 'rounded-sm',
        content: floating,
        item: 'before:rounded-sm data-highlighted:not-data-disabled:before:bg-elevated',
        label: 'text-muted'
      },
      variants: {
        size: fieldMenuSizes,
        variant: { outline: fieldOutline }
      },
      compoundVariants: fieldPadding,
      defaultVariants: { size: 'md' }
    },
    selectMenu: {
      slots: {
        base: 'rounded-sm',
        content: floating,
        item: 'before:rounded-sm data-highlighted:not-data-disabled:before:bg-elevated',
        label: 'text-muted'
      },
      variants: {
        size: fieldMenuSizes,
        variant: { outline: fieldOutline }
      },
      compoundVariants: fieldPadding,
      defaultVariants: { size: 'md' }
    },

    checkbox: {
      slots: { root: 'items-center', base: 'rounded-xs', indicator: 'text-primary', label: 'min-h-(--tap-min) flex items-center' },
      variants: {
        color: {
          primary: { indicator: 'bg-muted' },
          neutral: { indicator: 'bg-muted' }
        },
        size: {
          md: { base: 'size-(--cb-size)', icon: 'size-(--cb-icon)', container: 'h-(--cb-size)' }
        }
      }
    },

    radioGroup: {
      slots: { item: 'items-center', label: 'min-h-(--tap-min) flex items-center' },
      variants: {
        size: {
          md: { base: 'size-(--cb-size)', container: 'h-(--cb-size)', indicator: 'after:size-(--rd-dot)' }
        }
      }
    },

    switch: {
      slots: {
        root: 'items-center',
        base: 'data-[state=unchecked]:bg-muted ring ring-inset ring-accented',
        thumb: 'bg-(--ui-text) shadow-none data-[state=unchecked]:opacity-50',
        label: 'min-h-(--tap-min) flex items-center'
      },
      variants: {
        color: {
          primary: { base: 'data-[state=checked]:bg-primary/40 data-[state=checked]:ring-primary/20' }
        },
        size: {
          md: {
            base: 'w-(--sw-w) h-(--sw-h)',
            container: 'h-(--sw-h)',
            thumb: 'size-(--sw-thumb) ms-0.5 data-[state=checked]:translate-x-(--sw-shift) data-[state=checked]:rtl:-translate-x-(--sw-shift)'
          }
        }
      }
    },

    tabs: {
      slots: { trigger: 'rounded-none hover:data-[state=inactive]:not-disabled:bg-elevated' },
      variants: {
        variant: {
          pill: {
            list: 'bg-muted rounded-sm p-0 ring ring-default overflow-hidden',
            indicator: 'rounded-none shadow-none',
            trigger: 'rounded-none'
          }
        },
        size: {
          xs: { trigger: 'min-h-(--ctl-default) px-2 py-0 text-xs gap-1', leadingIcon: 'size-(--icon-sm)' },
          sm: { trigger: 'min-h-(--ctl-medium) px-(--px-tab) py-0 text-xs gap-1', leadingIcon: 'size-(--icon-ui)' },
          md: { trigger: 'min-h-(--ctl-large) px-(--px-tab) py-0 text-sm gap-1', leadingIcon: 'size-(--icon-ui)' },
          lg: { trigger: 'min-h-(--ctl-touch) px-(--px-tab) py-0 text-sm gap-2', leadingIcon: 'size-(--icon-ui)' }
        }
      },
      compoundVariants: [
        {
          color: 'neutral',
          variant: 'pill',
          class: {
            indicator: 'bg-default',
            trigger: 'data-[state=active]:text-default in-[[data-slot=list]:not(:has([data-slot=indicator]))]:data-[state=active]:before:bg-default in-[[data-slot=list]:not(:has([data-slot=indicator]))]:data-[state=active]:before:rounded-none in-[[data-slot=list]:not(:has([data-slot=indicator]))]:data-[state=active]:before:shadow-none'
          }
        },
        { orientation: 'horizontal', variant: 'pill', class: { indicator: 'inset-y-0' } }
      ],
      defaultVariants: { color: 'neutral' }
    },

    alert: {
      slots: { root: 'rounded-sm px-(--pad-alert-x) py-(--pad-alert-y) gap-2', icon: 'size-(--icon-ui) mt-0.5' },
      compoundVariants: [
        { color: 'info', variant: 'subtle', class: { root: 'text-default bg-(--ui-info-bg) ring-(color:--ui-info-border)', icon: 'text-info' } },
        { color: 'success', variant: 'subtle', class: { root: 'text-default bg-(--ui-success-bg) ring-(color:--ui-success-border)', icon: 'text-success' } },
        { color: 'warning', variant: 'subtle', class: { root: 'text-default bg-(--ui-warning-bg) ring-(color:--ui-warning-border)', icon: 'text-warning' } },
        { color: 'error', variant: 'subtle', class: { root: 'text-default bg-(--ui-error-bg) ring-(color:--ui-error-border)', icon: 'text-error' } }
      ],
      defaultVariants: { variant: 'subtle' }
    },

    badge: {
      variants: {
        size: {
          xs: { base: 'min-h-(--badge-h) min-w-(--badge-h) justify-center px-1 py-0 text-(length:--badge-text) leading-none rounded-full' },
          md: { base: 'px-1.5 py-0.5 rounded-sm' }
        }
      },
      compoundVariants: [
        { color: 'info', variant: 'subtle', class: 'bg-(--ui-info-bg) ring-(color:--ui-info-border)' },
        { color: 'success', variant: 'subtle', class: 'bg-(--ui-success-bg) ring-(color:--ui-success-border)' },
        { color: 'warning', variant: 'subtle', class: 'bg-(--ui-warning-bg) ring-(color:--ui-warning-border)' },
        { color: 'error', variant: 'subtle', class: 'bg-(--ui-error-bg) ring-(color:--ui-error-border)' }
      ],
      defaultVariants: { variant: 'subtle' }
    },

    card: {
      slots: {
        root: 'rounded-sm',
        header: 'p-(--pad-card) sm:px-(--pad-card)',
        body: 'p-(--pad-card) sm:p-(--pad-card)',
        footer: 'p-(--pad-card) sm:px-(--pad-card)'
      },
      variants: { variant: { outline: { root: 'bg-muted ring-default' } } }
    },

    table: {
      slots: {
        thead: 'border-b border-accented',
        th: 'h-(--row-head) px-(--px-field) py-0 text-xs bg-muted',
        td: 'h-(--row) p-0 px-(--px-field) text-sm text-default',
        tr: 'data-[selected=true]:bg-accented'
      }
    },

    dropdownMenu: {
      slots: { content: floating, item: 'before:rounded-sm' },
      variants: {
        active: { false: { item: 'data-highlighted:before:bg-elevated data-[state=open]:before:bg-elevated' } },
        size: menuSizes
      }
    },
    header: {
      slots: {
        root: 'bg-default backdrop-blur-none',
        left: 'min-w-0',
        right: 'shrink-0 gap-1',
        title: 'text-base font-semibold'
      }
    },
    popover: { slots: { content: floating } },
    tooltip: { slots: { content: 'bg-muted rounded-lg shadow-(--shadow-elev) px-2' } },
    toast: { slots: { root: 'bg-muted shadow-(--shadow-elev) p-1.5 ps-3 items-center', icon: 'size-(--icon-ui)' } },

    modal: {
      slots: {
        content: 'bg-muted',
        header: 'p-(--pad-modal) sm:px-4 min-h-0',
        body: 'p-(--pad-modal) sm:p-4',
        footer: 'p-(--pad-modal) sm:px-4'
      },
      variants: { fullscreen: { false: { content: 'shadow-(--shadow-modal)' } } }
    },

    progress: { slots: { base: 'bg-muted' } },

    kbd: {
      base: 'rounded-xs font-medium',
      variants: {
        size: {
          sm: 'h-3.5 min-w-3.5 text-[9px]',
          md: 'h-4 min-w-4 text-[10px]',
          lg: 'h-5 min-w-5 text-[11px]'
        }
      }
    },

    container: { base: 'px-3 sm:px-4 lg:px-6' },
    page: { slots: { root: 'lg:gap-6' } },
    pageBody: { base: 'mt-4 pb-12 space-y-6' },
    pageAside: { slots: { root: 'py-4 lg:pe-4' } },
    pageHeader: {
      slots: {
        root: 'py-4',
        headline: 'mb-1 text-xs',
        title: 'text-[1.43rem]/[1.6rem] sm:text-[1.43rem]/[1.6rem] font-semibold',
        description: 'text-sm'
      },
      variants: { title: { true: { description: 'mt-2' } } }
    },
    pageHero: {
      slots: {
        container: 'py-12 sm:py-16 lg:py-20 gap-8 sm:gap-y-12',
        title: 'text-3xl sm:text-5xl font-semibold',
        description: 'text-base sm:text-lg',
        body: 'mt-6',
        footer: 'mt-6',
        links: 'gap-x-3 gap-y-2 items-center'
      }
    },
    pageSection: {
      slots: {
        container: 'py-10 sm:py-14 lg:py-16 gap-6 sm:gap-10',
        leading: 'mb-3',
        leadingIcon: 'size-6',
        title: 'text-2xl sm:text-3xl lg:text-3xl font-semibold',
        description: 'text-sm sm:text-base',
        body: 'mt-6',
        links: 'gap-x-3 gap-y-2 items-center'
      }
    },
    pageCard: {
      slots: {
        root: 'rounded-md',
        container: 'p-(--pad-card) sm:p-(--pad-card) gap-y-2',
        header: 'mb-2',
        leading: 'mb-1.5',
        leadingIcon: 'size-(--icon-ui)',
        title: 'text-sm',
        description: 'text-sm'
      }
    },
    pageFeature: { slots: { title: 'text-sm', description: 'text-sm', leadingIcon: 'size-(--icon-ui)' } },
    pageLinks: {
      slots: {
        list: 'gap-1',
        title: 'text-xs',
        link: 'gap-2',
        linkLeadingIcon: 'size-(--icon-ui)'
      }
    },
    pageAnchors: {
      slots: {
        link: 'py-0.5 gap-2',
        linkLeading: 'rounded-sm p-0.5',
        linkLeadingIcon: 'size-(--icon-ui)'
      }
    },
    footer: {
      slots: {
        top: 'py-4 lg:py-6',
        bottom: 'py-4 lg:py-6',
        container: 'py-4 lg:py-2'
      }
    },
    navigationMenu: {
      slots: { link: 'text-sm before:rounded-sm', linkLeadingIcon: 'size-(--icon-ui)' },
      variants: {
        orientation: {
          horizontal: { link: 'min-h-(--row-menu) px-(--px-field) py-0' },
          vertical: { link: 'min-h-(--row-menu) px-(--px-field) py-0' }
        }
      }
    },
    contentNavigation: {
      slots: {
        list: '-mx-2 mt-0',
        listWithChildren: 'ms-2.5',
        itemWithChildren: 'data-[state=open]:mb-0.5',
        link: 'min-h-(--row-menu) px-(--px-field) py-0 gap-2 before:inset-y-0 before:rounded-sm',
        linkLeadingIcon: 'size-(--icon-ui)',
        linkTrailingIcon: 'size-(--icon-ui)'
      }
    },
    contentToc: {
      slots: {
        root: 'bg-default backdrop-blur-none',
        container: 'lg:py-4',
        trigger: 'text-xs',
        listWithChildren: 'ms-2.5',
        link: 'py-0.5'
      }
    },
    contentSurround: {
      slots: {
        root: 'gap-3',
        link: 'px-(--pad-card) py-(--pad-card) rounded-md',
        linkLeading: 'p-1 mb-2',
        linkLeadingIcon: 'size-(--icon-ui)',
        linkTitle: 'text-sm'
      }
    },

    commandPalette: { variants: { size: paletteSizes } },
    contentSearch: { variants: { fullscreen: { false: { modal: 'sm:max-w-xl sm:h-[24rem]' } } } },

    prose: {
      h1: { slots: { base: 'text-[1.43rem]/[1.6rem] font-semibold mb-4' } },
      h2: { slots: { base: 'text-[1.27rem]/[1.6rem] font-semibold mt-8 mb-3' } },
      h3: { slots: { base: 'text-[1.125rem]/[1.6rem] font-semibold mt-6 mb-2' } },
      h4: { slots: { base: 'text-base/[1.6rem] font-semibold mt-4 mb-1.5' } },
      p: { base: 'my-3 leading-[1.6]' },
      li: { base: 'my-1 ps-1 leading-[1.6]' },
      ul: { base: 'my-3 ps-5' },
      ol: { base: 'my-3 ps-5' },
      a: { base: 'font-normal' },
      hr: { base: 'my-6' },
      blockquote: { base: 'border-s-2 ps-3 not-italic' },
      code: { base: 'px-1 py-0 text-[0.9em] font-normal rounded-sm' },
      pre: {
        slots: {
          root: 'my-3',
          header: 'rounded-t-md px-3 py-1.5',
          base: 'rounded-md px-3 py-2 text-[13px]/[1.6]',
          copy: 'top-1.5 end-1.5'
        }
      },
      callout: {
        slots: { base: 'rounded-md px-(--pad-alert-x) py-(--pad-alert-y) my-3' },
        variants: {
          color: {
            info: { base: 'bg-(--ui-info-bg) border-(color:--ui-info-border) text-default dark:text-default' },
            success: { base: 'bg-(--ui-success-bg) border-(color:--ui-success-border) text-default dark:text-default' },
            warning: { base: 'bg-(--ui-warning-bg) border-(color:--ui-warning-border) text-default dark:text-default' },
            error: { base: 'bg-(--ui-error-bg) border-(color:--ui-error-border) text-default dark:text-default' },
            primary: { base: 'text-default dark:text-default' }
          }
        }
      },
      table: { slots: { root: 'my-3' } },
      th: { base: 'h-(--row-head) py-0 px-(--px-field) text-xs' },
      td: { base: 'h-(--row) py-1.5 px-(--px-field)' },
      card: {
        slots: {
          base: 'my-3 p-(--pad-card) sm:p-(--pad-card) bg-muted',
          icon: 'size-(--icon-ui) mb-1.5',
          description: 'text-sm'
        }
      },
      cardGroup: { base: 'gap-3 my-3' },
      accordion: { slots: { root: 'my-3', trigger: 'text-sm' } },
      accordionItem: { base: 'pb-3' },
      codeGroup: { slots: { root: 'my-3', list: 'p-1 gap-0.5', trigger: 'px-2 py-1 rounded-sm' } },
      codePreview: { slots: { root: 'my-3', preview: 'p-3' } },
      codeCollapse: { slots: { root: 'my-3' } },
      tabs: { slots: { root: 'my-3 gap-3' } },
      field: { slots: { root: 'my-3' } },
      fieldGroup: { base: 'my-3 *:not-last:pb-3' }
    }
  }
})
