import { computed } from 'vue'

import { ShieldIcon } from '@lucide/vue'
import { siAuth0, siFacebook, siGithub, siGoogle } from 'simple-icons'

export interface AuthProvider {
  name: string
  variant: 'default' | 'secondary' | 'outline'
  icon: object
  isAuth0: boolean
}

export const useAuthProvider = (user: { sub?: string } | undefined | null) => {
  return computed((): AuthProvider => {
    const sub = user?.sub || ''

    if (sub.startsWith('auth0|')) {
      return {
        name: 'Auth0',
        variant: 'default',
        icon: siAuth0,
        isAuth0: true,
      }
    } else if (sub.startsWith('google-oauth2|')) {
      return {
        name: 'Google',
        variant: 'secondary',
        icon: siGoogle,
        isAuth0: false,
      }
    } else if (sub.startsWith('github|')) {
      return {
        name: 'GitHub',
        variant: 'secondary',
        icon: siGithub,
        isAuth0: false,
      }
    } else if (sub.startsWith('facebook|')) {
      return {
        name: 'Facebook',
        variant: 'secondary',
        icon: siFacebook,
        isAuth0: false,
      }
    } else {
      return {
        name: 'Unknown',
        variant: 'outline',
        icon: ShieldIcon,
        isAuth0: false,
      }
    }
  })
}
