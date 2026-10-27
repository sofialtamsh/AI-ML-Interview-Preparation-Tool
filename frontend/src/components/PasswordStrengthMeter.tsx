import { cn } from '../lib/cn'
import { PASSWORD_MIN_LENGTH, scorePassword } from '../lib/password'

const BAR_COLORS = ['bg-slate-200', 'bg-rose-500', 'bg-amber-500', 'bg-emerald-500', 'bg-brand-500']

export function PasswordStrengthMeter({ password }: { password: string }) {
  if (!password) {
    return (
      <p className="mt-1.5 text-xs text-slate-500">At least {PASSWORD_MIN_LENGTH} characters.</p>
    )
  }
  const { score, label } = scorePassword(password)
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1" aria-hidden>
        {[1, 2, 3, 4].map((step) => (
          <span
            key={step}
            className={cn(
              'h-1.5 flex-1 rounded-full transition-all duration-300',
              step <= score ? BAR_COLORS[score] : 'bg-slate-200',
            )}
          />
        ))}
      </div>
      <p className="mt-1 text-xs text-slate-600">
        Strength: <span className="font-semibold text-slate-800">{label}</span>
        {score === 0 && ` · ${PASSWORD_MIN_LENGTH - password.length} more character(s) needed`}
      </p>
    </div>
  )
}
