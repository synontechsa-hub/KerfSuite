import styles from "./page.module.css";
import { createClient } from '@/utils/supabase/server';
import { generateKey } from './actions';
import { redirect } from 'next/navigation';
import RevokeButton from './RevokeButton';

export default async function Home() {
  const supabase = await createClient();

  // 1. Authenticate & get workspace
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { data: userData } = await supabase
    .from('users')
    .select('workspace_id, role, workspaces(name)')
    .eq('id', user.id)
    .single();

  const workspaceId = userData?.workspace_id;
  
  // 2. Fetch Dashboard Stats
  const { data: licenses } = await supabase
    .from('license_slots')
    .select('*')
    .eq('workspace_id', workspaceId)
    .order('created_at', { ascending: false });

  const { count: usersCount } = await supabase
    .from('users')
    .select('*', { count: 'exact', head: true })
    .eq('workspace_id', workspaceId);

  const activeMachines = licenses?.filter(l => l.status === 'active').length || 0;
  const totalUsers = usersCount || 0;
  const waitingSlots = licenses?.filter(l => l.status === 'waiting').length || 0;

  return (
    <div className={styles.container}>
      {/* Sidebar Placeholder */}
      <aside className={`${styles.sidebar} panel`}>
        <div className={styles.brand}>
          <h1 style={{ color: "var(--text-primary)", letterSpacing: "2px" }}>KERFCUT</h1>
          <p className="stencil-heading" style={{ marginTop: "0.2rem" }}>PORTAL</p>
        </div>
        
        <nav className={styles.nav}>
          <div className={`${styles.navItem} ${styles.active}`}>
            <span className="stencil-heading">Dashboard & Licenses</span>
          </div>
          <div className={styles.navItem}>
            <span className="stencil-heading">Users</span>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className={styles.main}>
        <header className={`${styles.header} panel`}>
          <h2 className="stencil-heading" style={{ fontSize: "1rem", color: "var(--text-primary)" }}>
            DASHBOARD
          </h2>
          <div className={styles.headerActions}>
            <form action={generateKey}>
              <button className="btn-primary" type="submit">+ Generate Key</button>
            </form>
          </div>
        </header>

        <div className={styles.grid}>
          {/* Stats Cards */}
          <div className="panel">
            <h3 className="stencil-heading">Active Machines</h3>
            <div className={styles.statValue}>{activeMachines}</div>
            <div className={styles.statMeta} style={{ color: "var(--status-running)" }}>Bound hardware</div>
          </div>
          
          <div className="panel">
            <h3 className="stencil-heading">Total Users</h3>
            <div className={styles.statValue}>{totalUsers}</div>
            <div className={styles.statMeta}>{userData?.role} privileges</div>
          </div>
          
          <div className="panel">
            <h3 className="stencil-heading">Waiting Keys</h3>
            <div className={styles.statValue}>{waitingSlots}</div>
            <div className={styles.statMeta} style={{ color: "var(--accent-orange)" }}>Ready to bind</div>
          </div>
        </div>

        {/* Licenses Data Grid */}
        <div className="panel" style={{ marginTop: "1rem", flex: 1 }}>
          <h3 className="stencil-heading" style={{ marginBottom: "1.5rem" }}>License Roster</h3>
          
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>CDKey</th>
                  <th>App</th>
                  <th>Status</th>
                  <th>Machine ID</th>
                  <th>Generated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {licenses?.map((license) => (
                  <tr key={license.id}>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--accent-orange)" }}>
                      {license.cdkey}
                    </td>
                    <td style={{ textTransform: "uppercase", fontSize: "0.85rem" }}>{license.app}</td>
                    <td>
                      <span className={`${styles.badge} ${styles['status-' + license.status]}`}>
                        {license.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                      {license.bound_machine_id || '—'}
                    </td>
                    <td style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                      {new Date(license.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      {license.status !== 'revoked' && (
                        <RevokeButton licenseId={license.id} />
                      )}
                    </td>
                  </tr>
                ))}
                {(!licenses || licenses.length === 0) && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>
                      No licenses generated yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
