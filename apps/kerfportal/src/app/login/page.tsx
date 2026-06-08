import { login } from './actions'
import styles from './login.module.css'

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ message: string }>
}) {
  const params = await searchParams

  return (
    <div className={styles.container}>
      <div className={`${styles.loginCard} panel`}>
        <div className={styles.header}>
          <h1 style={{ color: "var(--text-primary)", letterSpacing: "2px", fontSize: "1.5rem" }}>
            KERFCUT <span style={{ color: "var(--accent-orange)" }}>PORTAL</span>
          </h1>
          <p className="stencil-heading" style={{ marginTop: "0.5rem" }}>Admin Authentication</p>
        </div>

        <form className={styles.form}>
          <div className={styles.inputGroup}>
            <label className="stencil-heading" htmlFor="email">Email Address</label>
            <input 
              className={styles.input} 
              id="email" 
              name="email" 
              type="email" 
              placeholder="admin@workshop.com" 
              required 
            />
          </div>

          <div className={styles.inputGroup}>
            <label className="stencil-heading" htmlFor="password">Security Code</label>
            <input 
              className={styles.input} 
              id="password" 
              name="password" 
              type="password" 
              placeholder="••••••••" 
              required 
            />
          </div>

          {params?.message && (
            <div className={styles.errorAlert}>
              {params.message}
            </div>
          )}

          <div className={styles.actions}>
            <button className="btn-primary" style={{ width: "100%", padding: "0.8rem" }} formAction={login}>
              Initialize Session
            </button>
          </div>
        </form>
        
        <div className={styles.footer}>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", textAlign: "center" }}>
            Authorized Personnel Only
          </p>
        </div>
      </div>
    </div>
  )
}
