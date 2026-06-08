'use server'

import { revalidatePath } from 'next/cache'
import { createClient } from '@/utils/supabase/server'
import crypto from 'crypto'

export async function generateKey() {
  const supabase = await createClient()

  // 1. Get current user & workspace
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) throw new Error('Unauthorized')

  const { data: userData } = await supabase
    .from('users')
    .select('workspace_id')
    .eq('id', user.id)
    .single()

  if (!userData?.workspace_id) throw new Error('No workspace found')

  // 2. Generate secure random key (KCT-PRO-XXXX-XXXX)
  const generateSegment = () => crypto.randomBytes(2).toString('hex').toUpperCase()
  const cdkey = `KCT-PRO-${generateSegment()}-${generateSegment()}`

  // 3. Insert into database
  const { error } = await supabase
    .from('license_slots')
    .insert({
      workspace_id: userData.workspace_id,
      app: 'kerfcut',
      cdkey: cdkey,
      status: 'waiting',
      created_by: user.id
    })

  if (error) {
    console.error('Error generating key:', error)
    throw new Error('Failed to generate key')
  }

  // 4. Refresh dashboard data
  revalidatePath('/')
  return cdkey
}

export async function revokeKey(keyId: string) {
  const supabase = await createClient()
  
  const { error } = await supabase
    .from('license_slots')
    .update({ status: 'revoked' })
    .eq('id', keyId)

  if (error) {
    console.error('Error revoking key:', error)
    throw new Error('Failed to revoke key')
  }

  revalidatePath('/')
}
