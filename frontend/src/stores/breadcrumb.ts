import { computed, ref, watch } from 'vue'

import { defineStore } from 'pinia'
import type { RouteLocationNormalizedLoaded, RouteParamsRawGeneric } from 'vue-router'
import { useRoute } from 'vue-router'

export interface BreadcrumbItem {
  title: string
  titleKey?: string
  to?: string | { name: string; params?: RouteParamsRawGeneric }
  disabled?: boolean
  /**
   * When true, the mobile parent-link walker skips this item and looks
   * further up the chain. Useful for crumbs that represent the same
   * routed page as the current section (e.g. a event-detail root whose
   * sub-tabs are internal sections).
   */
  mobileSkip?: boolean
}

export const useBreadcrumbStore = defineStore('breadcrumb', () => {
  const dynamicBreadcrumbs = ref<BreadcrumbItem[]>([])
  const route = useRoute()

  const breadcrumbs = computed<BreadcrumbItem[]>(() => {
    if (dynamicBreadcrumbs.value.length > 0) {
      return dynamicBreadcrumbs.value
    }

    if (route.meta?.breadcrumbs) {
      return route.meta.breadcrumbs as BreadcrumbItem[]
    }

    return generateBreadcrumbsFromRoute(route)
  })

  const setBreadcrumbs = (items: BreadcrumbItem[]) => {
    dynamicBreadcrumbs.value = items
  }

  const clearBreadcrumbs = () => {
    dynamicBreadcrumbs.value = []
  }

  const addBreadcrumb = (item: BreadcrumbItem) => {
    dynamicBreadcrumbs.value.push(item)
  }

  const setDynamicTitle = (title: string) => {
    const items = breadcrumbs.value
    if (items.length > 0) {
      const updated = [...items]
      updated[updated.length - 1] = { ...updated[updated.length - 1], title, titleKey: undefined }
      dynamicBreadcrumbs.value = updated
    }
  }

  const generateBreadcrumbsFromRoute = (
    route: RouteLocationNormalizedLoaded,
  ): BreadcrumbItem[] => {
    const items: BreadcrumbItem[] = []
    const pathSegments = route.path.split('/').filter((segment) => segment !== '')

    if (route.path !== '/') {
      items.push({ title: 'Home', to: '/' })
    }

    let currentPath = ''
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`

      if (!segment.startsWith(':')) {
        const isLast = index === pathSegments.length - 1
        const title = segment.charAt(0).toUpperCase() + segment.slice(1).replace('-', ' ')

        items.push({
          title,
          to: isLast ? undefined : currentPath,
        })
      }
    })

    return items
  }

  // Clear dynamic breadcrumbs when the route name changes so top-level
  // navigation falls back to the new route's meta.breadcrumbs.
  // Param-only changes (e.g. section tabs on the same view) are preserved.
  watch(
    () => route.name,
    (newName, oldName) => {
      if (newName !== oldName && dynamicBreadcrumbs.value.length > 0) {
        dynamicBreadcrumbs.value = []
      }
    },
  )

  return {
    breadcrumbs,
    setBreadcrumbs,
    clearBreadcrumbs,
    addBreadcrumb,
    setDynamicTitle,
  }
})

declare module 'vue-router' {
  interface RouteMeta {
    breadcrumbs?: BreadcrumbItem[]
  }
}
