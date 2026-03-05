import Link from "next/link"

export default function SignUpSuccessPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[#0c1222]">
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-sm text-center">
          <Link
            href="/"
            className="mb-10 inline-block text-3xl font-extrabold tracking-tight text-white"
          >
            biogate
          </Link>
          <h1 className="text-2xl font-bold text-white">Check your email</h1>
          <p className="mt-3 text-sm leading-relaxed text-white/50">
            {"We've sent a confirmation link to your email address. Click the link to activate your account and start your first audit."}
          </p>
          <Link
            href="/auth/login"
            className="mt-8 inline-block text-sm text-white/70 underline hover:text-white"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
