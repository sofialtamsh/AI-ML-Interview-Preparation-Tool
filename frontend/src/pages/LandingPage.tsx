import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router'

import { BRAND } from '../brand'
import { GradientDescentHero } from '../components/GradientDescentHero'
import { Logo } from '../components/Logo'
import { ButtonLink } from '../components/ui/Button'
import { useStudentMe } from '../student/api'

export default function LandingPage() {
  const me = useStudentMe()
  const signedIn = !!me.data

  return (
    <div className="relative min-h-dvh overflow-hidden bg-gradient-to-br from-brand-950 via-[#1d0b4d] to-slate-950 text-white">
      <div aria-hidden className="absolute -top-32 right-0 size-[28rem] animate-float rounded-full bg-fuchsia-500/25 blur-3xl" />
      <div aria-hidden className="absolute -bottom-40 -left-20 size-[30rem] animate-float rounded-full bg-brand-500/30 blur-3xl [animation-delay:-4s]" />
      <div
        aria-hidden
        className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:48px_48px]"
      />

      <div className="relative mx-auto flex min-h-dvh max-w-6xl flex-col px-5 sm:px-8">
        <header className="flex items-center justify-between py-6">
          <Logo tone="light" />
          {!signedIn && (
            <Link to="/login" className="rounded-xl px-4 py-2 text-sm font-semibold text-white/90 transition hover:bg-white/10">
              Sign in
            </Link>
          )}
        </header>

        <main className="grid flex-1 items-center gap-12 py-10 lg:grid-cols-2">
          <div className="animate-fade-up">
            <p className="inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-semibold tracking-wide text-lime-300 ring-1 ring-white/15">
              For ML, AI, data science, NLP, CV, GenAI & MLOps roles
            </p>
            <h1 className="mt-6 font-display text-5xl leading-[1.05] font-bold tracking-tight sm:text-6xl">
              {BRAND.tagline.replace('.', '')}
              <span className="text-lime-300">.</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg text-violet-100/80">
              Understand concepts by playing with them, practise the questions interviews actually
              ask, and track your progress across every device.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              {signedIn ? (
                <ButtonLink to="/app" variant="glow" size="lg">
                  Go to your dashboard <ArrowRight className="size-4" />
                </ButtonLink>
              ) : (
                <>
                  <ButtonLink to="/register" variant="glow" size="lg">
                    Create a free account <ArrowRight className="size-4" />
                  </ButtonLink>
                  <ButtonLink to="/login" size="lg" className="bg-white/10 text-white shadow-none ring-1 ring-white/20 hover:bg-white/20">
                    I have an account
                  </ButtonLink>
                </>
              )}
            </div>
          </div>
          <div className="animate-fade-up rounded-3xl bg-white/[0.06] p-6 ring-1 ring-white/10 backdrop-blur [animation-delay:120ms] sm:p-8">
            <p className="mb-3 text-xs font-semibold tracking-widest text-violet-200/70 uppercase">
              This is gradient descent. Live.
            </p>
            <GradientDescentHero />
          </div>
        </main>

        <footer className="flex flex-wrap items-center justify-between gap-3 py-6 text-xs text-white/50">
          <span>© {new Date().getFullYear()} {BRAND.name}</span>
          <Link to="/admin/login" className="hover:text-white/80">
            Staff sign in
          </Link>
        </footer>
      </div>
    </div>
  )
}
