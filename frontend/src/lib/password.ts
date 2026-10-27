export const PASSWORD_MIN_LENGTH = 10

export type PasswordStrength = { score: 0 | 1 | 2 | 3 | 4; label: string }

const LABELS = ['Too short', 'Weak', 'Okay', 'Strong', 'Excellent'] as const

/** A quick, transparent heuristic for the strength meter; the server enforces the rules. */
export function scorePassword(password: string): PasswordStrength {
  if (password.length < PASSWORD_MIN_LENGTH) return { score: 0, label: LABELS[0] }
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(password)).length
  const repetitive = /^(.)\1+$/.test(password) || /^(?:0123|1234|abcd|qwer|pass)/i.test(password)
  let score = 1 + (password.length >= 14 ? 1 : 0) + (classes >= 3 ? 1 : 0) + (password.length >= 18 ? 1 : 0)
  if (repetitive) score = 1
  const clamped = Math.min(4, score) as PasswordStrength['score']
  return { score: clamped, label: LABELS[clamped] }
}

/** A random, typeable temporary password (used when an admin invites another admin). */
export function generateTemporaryPassword(length = 16): string {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(length))
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join('')
}
