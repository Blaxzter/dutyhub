# Vue 3 Frontend - Product Implementation Guide

## Overview

This guide provides comprehensive instructions for implementing new features in the Vue 3 frontend using Vue 3 Composition API, TypeScript, Pinia, and shadcn-vue components. The frontend is designed to work seamlessly with the FastAPI backend through auto-generated typed clients.

## Architecture Overview

```
Frontend Architecture:
├── Views (Pages)          → Route components & page layouts
├── Components             → Reusable UI components
│   ├── ui/               → shadcn-vue base components
│   ├── feature/          → Feature-specific components
│   ├── account/          → User account components
│   ├── navigation/       → Navigation components
│   └── utils/            → Utility components
├── Stores (Pinia)        → State management with proper typing
├── Composables           → Reusable logic & API interactions
├── Router                → Navigation & route definitions
├── Client (API)          → Auto-generated API client with types
├── Types                 → TypeScript type definitions
└── Locales               → Internationalization
```

## Tech Stack Reference

- **Vue 3** with Composition API
- **TypeScript** for complete type safety
- **Pinia** for state management
- **shadcn-vue** for ALL UI components (never use native HTML elements like `<input>` when shadcn component exists)
- **Tailwind CSS** for styling
- **Auth0** for authentication
- **Zod** for validation (auto-generated from backend schemas)
- **@hey-api/openapi-ts** for API client generation
- **Vue Router** for navigation
- **Vue I18n** for internationalization

## Implementation Steps

### 1. Generate API Client

Always ensure your backend changes are implemented first, then generate the TypeScript client:

```bash
# Ensure backend is running and generate TypeScript client
pnpm run generate-client
```

**Generated Files Structure:**

- `src/client/types.gen.ts` - TypeScript interfaces for all API schemas (e.g., `UserProfile`, `ExampleRequest`)
- `src/client/zod.gen.ts` - Zod validation schemas matching backend models (e.g., `zUserProfileUpdate`)
- `src/client/client.gen.ts` - HTTP client methods for all endpoints with proper typing
- `src/client/core/` - Core client functionality including auth and error handling
- `src/client/index.ts` - Main client exports

**Development Workflow:**

1. **Backend First** - Implement Pydantic models and API endpoints in backend
2. **Generate Types** - Run `pnpm run generate-client` after backend changes
3. **Never Manual Types** - Never manually create types that mirror backend schemas
4. **Use Generated Zod** - Always use generated validation schemas from `zod.gen.ts`
5. **Type Safety** - The generated client provides full end-to-end type safety

### 2. Define Frontend-Specific Types

**Location**: `src/types/`

Create separate files for each feature/domain. Only define frontend-specific types here.

```typescript
// ✅ Frontend-specific validation schemas
import { z } from 'zod'

// src/types/user.ts

// ✅ ONLY define frontend-specific types
export interface UserFilters {
  search?: string
  verified?: boolean
  dateRange?: {
    start: Date
    end: Date
  }
}

export interface UserTableState {
  page: number
  perPage: number
  sortBy?: string
  sortDirection: 'asc' | 'desc'
}
```

### 3. Create Properly Typed Pinia Store

**Location**: `src/stores/`

```typescript
// src/stores/user.ts
import { computed, ref } from 'vue'

import { defineStore } from 'pinia'

import { useAuthenticatedClient } from '@/composables/useAuthenticatedClient'

import type { UserFilters, UserProfile, UserProfileUpdate, UserTableState } from '@/types/user'

export const useUserStore = defineStore('user', () => {
  // State - always properly typed
  const users = ref<UserProfile[]>([])
  const currentUser = ref<UserProfile | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const tableState = ref<UserTableState>({
    page: 1,
    perPage: 20,
    sortBy: 'name',
    sortDirection: 'asc',
  })
  const filters = ref<UserFilters>({})

  // API client with full typing
  const { get, post, patch, delete: del } = useAuthenticatedClient()

  // Getters - computed properties with proper return types
  const verifiedUsers = computed((): UserProfile[] =>
    users.value.filter((user) => user.email_verified === true),
  )

  const totalUsers = computed((): number => users.value.length)

  const filteredUsers = computed((): UserProfile[] => {
    let filtered = users.value

    if (filters.value.search) {
      const search = filters.value.search.toLowerCase()
      filtered = filtered.filter(
        (user) =>
          user.name?.toLowerCase().includes(search) ||
          user.email?.toLowerCase().includes(search) ||
          user.nickname?.toLowerCase().includes(search),
      )
    }

    if (filters.value.verified !== undefined) {
      filtered = filtered.filter((user) => user.email_verified === filters.value.verified)
    }

    return filtered
  })

  // Actions - fully typed API calls
  const fetchUsers = async (): Promise<void> => {
    loading.value = true
    error.value = null

    try {
      const response = await get<UserProfile[]>({
        url: '/api/v1/users/',
      })
      users.value = response
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch users'
      console.error('Error fetching users:', err)
    } finally {
      loading.value = false
    }
  }

  const getCurrentUser = async (): Promise<UserProfile | null> => {
    loading.value = true
    error.value = null

    try {
      // Using properly typed generated endpoint
      const response = await get<UserProfile>({
        url: '/api/v1/users/me',
      })

      currentUser.value = response
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch current user'
      console.error('Error fetching current user:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateCurrentUser = async (userData: UserProfileUpdate): Promise<UserProfile | null> => {
    loading.value = true
    error.value = null

    try {
      // Patch with proper typing from generated client
      const response = await patch<UserProfile>({
        url: '/api/v1/users/me',
        body: userData,
      })

      currentUser.value = response

      // Update in users list if it exists
      const userIndex = users.value.findIndex((user) => user.sub === response.sub)
      if (userIndex !== -1) {
        users.value[userIndex] = response
      }

      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to update user'
      console.error('Error updating user:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteUser = async (userId: string): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      await del({ url: `/api/v1/users/${userId}` })

      // Remove from local state
      users.value = users.value.filter((user) => user.sub !== userId)

      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete user'
      console.error('Error deleting user:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Helper functions
  const setFilters = (newFilters: Partial<UserFilters>): void => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const clearFilters = (): void => {
    filters.value = {}
  }

  const clearError = (): void => {
    error.value = null
  }

  return {
    // State
    users: readonly(users),
    currentUser: readonly(currentUser),
    loading: readonly(loading),
    error: readonly(error),
    tableState,
    filters,

    // Getters
    verifiedUsers,
    totalUsers,
    filteredUsers,

    // Actions
    fetchUsers,
    getCurrentUser,
    updateCurrentUser,
    deleteUser,
    setFilters,
    clearFilters,
    clearError,
  }
})
```

### 4. Create Typed Composables

**Location**: `src/composables/`

Composables are for reusable logic in Vue components.
Dont create a composable if it doesnt make sense.
Splitting logic into composables should be done when it improves readability and reusability.

Nameing: useThing.ts.

### 5. Add Routes with breadcrump and auth0 auth guard information

**Location**: `src/router/index.ts`

```typescript
// Add to the routes configuration with proper meta typing
// Example route definitions with proper typing
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
  {
    // Public routes
    path: '/',
    name: 'preauth-layout',
    component: () => import('@/layout/PreAuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'landing',
        component: () => import('@/views/preauth/LandingView.vue'),
      },
      ... // Other public routes
    ],
  },
  {
    // Protected routes
    path: '/app',
    component: () => import('@/layout/PostAuthLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/views/account/ProfileView.vue'),
        beforeEnter: authGuard,
        meta: {
          breadcrumbs: [{ title: 'Home', to: { name: 'home' } }, { title: 'Profile' }],
        },
      },
      ... // Other protected routes
    ],
  },
]
```

### 8. Update Navigation with Type Safety

**Location**: `src/components/navigation/NavMain.vue`

```typescript
import { HomeIcon, SettingsIcon, UserIcon, UsersIcon } from '@lucide/vue'

// Properly typed navigation items
interface NavItem {
  title: string
  url: string
  icon: Component
  badge?: string | number
  children?: NavItem[]
}

const navigationItems: NavItem[] = [
  {
    title: 'Dashboard',
    url: '/app/home',
    icon: HomeIcon,
  },
  {
    title: 'Profile',
    url: '/app/profile',
    icon: UserIcon,
  },
  {
    title: 'Users',
    url: '/app/users',
    icon: UsersIcon,
    badge: '5', // Example badge
  },
  {
    title: 'Settings',
    url: '/app/settings',
    icon: SettingsIcon,
    children: [
      {
        title: 'General',
        url: '/app/settings/general',
        icon: SettingsIcon,
      },
      {
        title: 'Security',
        url: '/app/settings/security',
        icon: SettingsIcon,
      },
    ],
  },
]
```

**Naming Conventions:**

- **Components:** PascalCase (e.g., `UserProfileCard.vue`)
- **Composables:** camelCase with `use` prefix (e.g., `useUserForm.ts`)
- **Stores:** camelCase with Store suffix (e.g., `useUserStore`)
- **Types:** PascalCase for interfaces, camelCase for type aliases
- **Files:** kebab-case for files, PascalCase for Vue components

This comprehensive guide ensures type safety, maintainability, and consistency across your Vue 3 frontend application while leveraging the full power of the generated API client and modern Vue.js patterns.
