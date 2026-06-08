'use client'

import { revokeKey } from './actions'
import styles from './page.module.css'

export default function RevokeButton({ licenseId }: { licenseId: string }) {
  return (
    <form action={async () => {
      await revokeKey(licenseId)
    }}>
      <button 
        type="submit" 
        className={styles.btnDanger}
        onClick={(e) => {
          if (!confirm('Revoke this key instantly? This will lock out the machine.')) {
            e.preventDefault();
          }
        }}
      >
        Revoke
      </button>
    </form>
  )
}
